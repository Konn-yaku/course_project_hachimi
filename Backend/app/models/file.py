# app/models/file.py
from pydantic import BaseModel
from datetime import datetime


class FileItem(BaseModel):
    name: str
    is_dir: bool  # 告诉前端这是文件还是文件夹 (用于显示 📁 或 📄)
    modified: datetime
    size: int  # (对于文件夹，我们可以设为 0)


class DirectoryListing(BaseModel):
    path: str  # 当前浏览的相对路径
    items: list[FileItem]


class MediaItem(BaseModel):
    title: str
    poster_url: str


class PhotoItem(BaseModel):
    src_url: str
    thumbnail_url: str


class Token(BaseModel):
    access_token: str
    token_type: str
