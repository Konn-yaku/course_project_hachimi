# app/api/v1/media.py
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends

from app.core.config import settings
from app.core.security import get_current_user
from app.models.file import MediaItem, PhotoItem

router = APIRouter()

# 允许的海报/封面文件扩展名
# 我们使用 set (集合) 是为了更快的查找
ALLOWED_POSTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_media_path(media_type: str) -> Path:
    """安全地获取媒体子目录的路径"""
    media_dir = settings.MEDIA_ROOT_PATH.joinpath(media_type).resolve()

    if not str(media_dir).startswith(str(settings.MEDIA_ROOT_PATH.resolve())):
        raise HTTPException(status_code=500, detail="媒体目录配置错误")

    os.makedirs(media_dir, exist_ok=True)
    return media_dir


@router.get("/anime", response_model=list[MediaItem])
async def get_anime_library(user: dict = Depends(get_current_user)):
    """
    扫描 Anime 目录，查找子文件夹和海报。
    (新逻辑：查找子文件夹中的 *任何* 图像文件)
    """
    anime_dir = get_media_path("Anime")  # 获取 my_media_files/Anime 路径
    library = []

    try:
        # 遍历 "Anime" 目录下的所有条目 (e.g., "Frieren", "SPYxFamily")
        for entry in os.scandir(anime_dir):
            # 我们只关心子文件夹
            if not entry.is_dir():
                continue

            item_title = entry.name
            poster_url = None

            # --- 这是修改后的新逻辑 ---
            #
            # 遍历这个子文件夹 ("Frieren") 内部的所有文件
            try:
                for item_in_folder in os.scandir(entry.path):
                    # 确保它是一个文件
                    if not item_in_folder.is_file():
                        continue

                    # 检查文件的扩展名
                    file_ext = Path(item_in_folder.name).suffix.lower()

                    if file_ext in ALLOWED_POSTER_EXTENSIONS:
                        # 找到了! 这就是我们的海报
                        # (e.g., "Alma-chan Wants to Have a family!.webp")
                        poster_name = item_in_folder.name

                        # 构建 URL: /static_media/Anime/Frieren/poster.jpg
                        poster_url = f"/static_media/Anime/{item_title}/{poster_name}"

                        # 找到第一个就停止，不再查找
                        break

            except Exception:
                # 扫描子文件夹出错，跳过
                continue
            # --- 新逻辑结束 ---

            # 如果这个子文件夹里一张图片都找不到，就跳过
            if poster_url is None:
                continue

            library.append(MediaItem(
                title=item_title,
                poster_url=poster_url
            ))

    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限读取 Anime 目录")

    library.sort(key=lambda x: x.title)
    return library


@router.get("/movies", response_model=list[MediaItem])
async def get_movie_library(user: dict = Depends(get_current_user)):
    """
    扫描 Movies 目录，查找子文件夹和海报。
    (逻辑与 get_anime_library 完全相同)
    """
    movie_dir = get_media_path("Movies")  # <-- 唯一的区别：扫描 "Movies"
    library = []

    try:
        # 遍历 "Movies" 目录下的所有条目
        for entry in os.scandir(movie_dir):
            if not entry.is_dir():
                continue

            item_title = entry.name
            poster_url = None

            try:
                # 遍历这个子文件夹内部的所有文件
                for item_in_folder in os.scandir(entry.path):
                    if not item_in_folder.is_file():
                        continue

                    file_ext = Path(item_in_folder.name).suffix.lower()

                    if file_ext in ALLOWED_POSTER_EXTENSIONS:
                        poster_name = item_in_folder.name
                        # 构建 URL: /static_media/Movies/Movie Title/poster.jpg
                        poster_url = f"/static_media/Movies/{item_title}/{poster_name}"
                        break

            except Exception:
                continue

            if poster_url is None:
                continue

            library.append(MediaItem(
                title=item_title,
                poster_url=poster_url
            ))

    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限读取 Movies 目录")

    library.sort(key=lambda x: x.title)
    return library

@router.get("/photos", response_model=list[PhotoItem])
async def get_photo_library(user: dict = Depends(get_current_user)):
    """
    扫描 Photos 目录，查找所有图片文件。
    (与 Anime/Movies 不同，这个是平铺的)
    """
    photos_dir = get_media_path("Photos") # 扫描 my_media_files/Photos
    photos = []

    try:
        # 遍历 "Photos" 目录下的所有条目
        for entry in os.scandir(photos_dir):
            # 这次我们只关心文件
            if not entry.is_file():
                continue

            file_ext = Path(entry.name).suffix.lower()

            # 检查是否是图片
            if file_ext in ALLOWED_POSTER_EXTENSIONS:
                photo_name = entry.name

                # 构建 URL: /static_media/Photos/my_image.jpg
                photo_url = f"/static_media/Photos/{photo_name}"

                photos.append(PhotoItem(
                    src_url=photo_url,
                    thumbnail_url=photo_url # 目前缩略图和原图使用同一个
                ))

    except PermissionError:
        raise HTTPException(status_code=403, detail="没有权限读取 Photos 目录")

    return photos