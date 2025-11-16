# app/api/v1/files.py
import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel

from app.core.config import settings  # 导入我们的根路径
from app.models.file import DirectoryListing, FileItem

router = APIRouter()


class MkdirRequest(BaseModel):
    path: str = "."  # 将在新文件夹创建在哪个相对路径下
    folder_name: str  # 新文件夹的名称


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