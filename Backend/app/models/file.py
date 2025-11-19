from pydantic import BaseModel
from datetime import datetime


class FileItem(BaseModel):
    """
    Represents a single file or directory in the file manager.
    """
    name: str
    is_dir: bool  # Indicates if the item is a directory (True) or a file (False)
    modified: datetime
    size: int  # File size in bytes (typically 0 for directories)


class DirectoryListing(BaseModel):
    """
    Represents the contents of a directory for API responses.
    """
    path: str  # The relative path currently being browsed (e.g., "Movies/Action")
    items: list[FileItem]


class MediaItem(BaseModel):
    """
    Represents a media entry (Movie or Anime) for the visual library.
    """
    title: str
    poster_url: str # URL path to the poster image (e.g., /static_media/...)