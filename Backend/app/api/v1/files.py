# app/api/v1/files.py
import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings  # 导入我们的根路径
from app.models.file import DirectoryListing, FileItem

router = APIRouter()


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