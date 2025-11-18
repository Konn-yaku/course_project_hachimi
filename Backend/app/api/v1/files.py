# app/api/v1/files.py
import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form

from pydantic import BaseModel
import shutil

from app.core.config import settings
from app.models.file import DirectoryListing, FileItem
from app.services.tmdb import is_video_file, analyze_filename, download_poster

router = APIRouter()


class MkdirRequest(BaseModel):
    path: str = "."  # 将在新文件夹创建在哪个相对路径下
    folder_name: str  # 新文件夹的名称

class DeleteRequest(BaseModel):
    path: str  # 要删除的文件或文件夹的相对路径


def get_real_path(user_path: str) -> Path:
    """
    安全地将用户请求的相对路径转换为服务器上的绝对路径。
    包含关键的安全检查。
    """
    # 1. 将用户路径规范化，去除 ".." 或 "."
    # e.g., "Photos/../Anime" -> "Anime"
    safe_path = Path(os.path.normpath(user_path))

    # 2. 禁止以 ".." 或 "/" 开头的路径
    if safe_path.is_absolute() or str(safe_path).startswith(".."):
        raise HTTPException(status_code=400, detail="非法的路径请求")

    # 3. 拼接我们的媒体根目录和用户请求的路径
    # e.g., /path/to/my_media_files + Anime
    full_path = settings.MEDIA_ROOT_PATH.joinpath(safe_path).resolve()

    # 4. 关键安全检查：确保解析后的路径仍在我们的根目录内
    if not str(full_path).startswith(str(settings.MEDIA_ROOT_PATH.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问：路径越界")

    # 5. 检查路径是否存在
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="路径不存在")

    return full_path


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(
    # Query() 定义了一个查询参数, 默认值是 "." (代表根目录)
    path: str = Query(default=".", description="要浏览的相对路径")
):
    """
    浏览媒体根目录下的文件和文件夹。
    """
    try:
        real_path = get_real_path(path)
    except HTTPException as e:
        # 将 get_real_path 抛出的异常直接返回给用户
        raise e

    if not real_path.is_dir():
        raise HTTPException(status_code=400, detail="请求的路径不是一个目录")

    file_items = []
    try:
        for entry in os.scandir(real_path):
            stat = entry.stat()
            file_items.append(FileItem(
                name=entry.name,
                is_dir=entry.is_dir(),
                modified=datetime.fromtimestamp(stat.st_mtime),
                size=stat.st_size if not entry.is_dir() else 0
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限读取该目录")

    # 按类型（文件夹在前）和名称排序
    file_items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    return DirectoryListing(
        path=path,  # 返回用户请求的相对路径
        items=file_items
    )


@router.post("/upload")
async def upload_files(
        path: str = Form(default=".", description="文件上传的目标相对路径"),
        files: list[UploadFile] = File(description="要上传的文件列表"),
        # user: dict = Depends(get_current_user) # <-- 之前让你删掉了鉴权，这里不需要加回来
):
    """
    智能上传：自动识别视频文件，创建对应文件夹并下载海报。
    """
    uploaded_details = []

    try:
        base_destination_dir = get_real_path(path)
        if not base_destination_dir.is_dir():
            raise HTTPException(status_code=400, detail="目标路径不是一个目录")

        for file in files:
            # === 智能识别逻辑开始 ===
            final_folder = base_destination_dir
            poster_path_from_tmdb = None
            recognition_status = "未识别/普通文件"

            # 1. 检查是否是视频
            if is_video_file(file.filename):
                print(f"正在识别视频: {file.filename} ...")

                # 2. 调用我们的 TMDB 服务
                official_title, media_type, poster_ext, _ = analyze_filename(file.filename)

                if official_title:
                    # 3. 识别成功！
                    # 决定新文件夹的名字。例如: "Avatar (2009)" 或者只是 "Avatar"
                    # 为了简单，我们直接用官方标题。
                    # 注意：我们要处理非法字符 (比如 Windows 不允许文件名包含 : ? 等)
                    safe_title = "".join([c for c in official_title if c not in r'\/:*?"<>|'])

                    # 创建子目录
                    new_sub_folder = base_destination_dir.joinpath(safe_title)
                    if not new_sub_folder.exists():
                        os.makedirs(new_sub_folder)

                    # 更新保存路径
                    final_folder = new_sub_folder
                    poster_path_from_tmdb = poster_ext
                    recognition_status = f"识别成功: {safe_title} ({media_type})"
                else:
                    print("TMDB 未找到匹配项")

            # === 智能识别逻辑结束 ===

            # 4. 保存文件 (存到 final_folder)
            file_path = final_folder.joinpath(file.filename)

            if file_path.exists():
                # 简单处理：如果文件已存在，跳过 (或者你可以改为覆盖/重命名)
                uploaded_details.append(f"{file.filename} (跳过: 已存在)")
                continue

            try:
                with open(file_path, "wb") as buffer:
                    while contents := await file.read(1024 * 1024):
                        buffer.write(contents)

                # 5. 如果有海报，下载海报 (保存到 final_folder)
                if poster_path_from_tmdb:
                    download_poster(poster_path_from_tmdb, str(final_folder))

                uploaded_details.append(f"{file.filename} -> {recognition_status}")

            except Exception as e:
                uploaded_details.append(f"{file.filename} (失败: {str(e)})")
            finally:
                await file.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传过程中发生错误: {e}")

    return {
        "message": "上传处理完成",
        "details": uploaded_details
    }


@router.delete("/delete")
async def delete_item(
        request: DeleteRequest
):
    """
    删除指定的文件或文件夹。
    如果是文件夹，将递归删除其所有内容。
    """
    try:
        # 1. 获取真实路径 (这会自动检查路径越界和是否存在)
        target_path = get_real_path(request.path)
    except HTTPException as e:
        raise e

    # 2. 安全检查：禁止删除根目录本身
    # 我们比较一下 target_path 和 MEDIA_ROOT_PATH
    if target_path == settings.MEDIA_ROOT_PATH.resolve():
        raise HTTPException(status_code=400, detail="禁止删除根目录")

    try:
        # 3. 执行删除
        if target_path.is_file():
            # 如果是文件，直接删除
            os.remove(target_path)
        elif target_path.is_dir():
            # 如果是文件夹，使用 shutil.rmtree 递归删除 (连同里面的东西一起删)
            shutil.rmtree(target_path)

    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限删除该项目")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")

    return {
        "message": "删除成功",
        "deleted_path": request.path
    }


@router.post("/mkdir")
async def create_directory(
    request: MkdirRequest
):
    """
    在指定的相对路径下创建一个新文件夹。
    """

    # 1. 验证新文件夹名称的安全性
    # 确保名称中不含 ".." 或 "/"
    if ".." in request.folder_name or "/" in request.folder_name or "\\" in request.folder_name:
        raise HTTPException(
            status_code=400,
            detail="非法的文件夹名称"
        )

    try:
        # 2. 获取 *父* 目录的真实路径
        parent_dir = get_real_path(request.path)
    except HTTPException as e:
        # 如果 get_real_path 失败 (例如, 越界或路径非法)
        raise e

    # 3. 确保父目录是一个目录
    if not parent_dir.is_dir():
        raise HTTPException(status_code=400, detail="目标路径不是一个目录")

    # 4. 构建新文件夹的完整路径
    new_folder_path = parent_dir.joinpath(request.folder_name)

    # 5. 检查文件夹是否已存在
    if new_folder_path.exists():
        raise HTTPException(
            status_code=409,  # 409 Conflict 是一个很合适的状态码
            detail="该名称的文件夹或文件已存在"
        )

    try:
        # 6. 创建目录
        os.makedirs(new_folder_path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限在此位置创建文件夹")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文件夹时出错: {e}")

    return {
        "message": "文件夹创建成功",
        "new_folder_path": f"{request.path}/{request.folder_name}"
    }