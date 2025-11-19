import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.file import MediaItem

router = APIRouter()

# Allowed file extensions for posters/covers
# Using a set allows for O(1) lookup speed
ALLOWED_POSTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_media_path(media_type: str) -> Path:
    """
    Safely retrieve the absolute path for a specific media subdirectory (e.g., 'Anime', 'Movies').
    Ensures the directory exists and is securely located within the MEDIA_ROOT_PATH.
    """
    media_dir = settings.MEDIA_ROOT_PATH.joinpath(media_type).resolve()

    # Security check: Prevent path traversal to ensure we stay inside the media root
    if not str(media_dir).startswith(str(settings.MEDIA_ROOT_PATH.resolve())):
        raise HTTPException(status_code=500, detail="Media directory configuration error")

    # Automatically create the directory if it doesn't exist
    os.makedirs(media_dir, exist_ok=True)
    return media_dir


@router.get("/anime", response_model=list[MediaItem])
async def get_anime_library():
    """
    Scans the 'Anime' directory to build a library of available titles.
    Each subdirectory in 'Anime' is treated as a distinct title.
    The API looks for any image file inside the subdirectory to serve as the poster.
    """
    anime_dir = get_media_path("Anime")  # Resolve path to my_media_files/Anime
    library = []

    try:
        # Iterate through all entries in the "Anime" directory (e.g., "Frieren", "SPYxFamily")
        for entry in os.scandir(anime_dir):
            # We only care about directories (which represent Titles)
            if not entry.is_dir():
                continue

            item_title = entry.name
            poster_url = None

            # --- Image Discovery Logic ---
            # Scan files inside this title's folder to find a valid poster image
            try:
                for item_in_folder in os.scandir(entry.path):
                    # Ensure it is a file
                    if not item_in_folder.is_file():
                        continue

                    # Check the file extension
                    file_ext = Path(item_in_folder.name).suffix.lower()

                    if file_ext in ALLOWED_POSTER_EXTENSIONS:
                        # Found a valid image! This will be our poster.
                        # (e.g., "poster.webp" or "cover.jpg")
                        poster_name = item_in_folder.name

                        # Construct the static URL: /static_media/Anime/Title/image.jpg
                        poster_url = f"/static_media/Anime/{item_title}/{poster_name}"

                        # Stop searching after finding the first valid image
                        break

            except Exception:
                # Skip this folder if an error occurs during scanning
                continue
            # --- End Discovery Logic ---

            # If no image was found in the folder, skip adding this title to the library
            if poster_url is None:
                continue

            library.append(MediaItem(
                title=item_title,
                poster_url=poster_url
            ))

    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading Anime directory")

    # Sort the library alphabetically by title
    library.sort(key=lambda x: x.title)
    return library


@router.get("/movies", response_model=list[MediaItem])
async def get_movie_library():
    """
    Scans the 'Movies' directory to build a library of available titles.
    Logic is identical to get_anime_library, but targets the 'Movies' folder.
    """
    movie_dir = get_media_path("Movies")  # Scan "Movies" directory
    library = []

    try:
        # Iterate through all entries in the "Movies" directory
        for entry in os.scandir(movie_dir):
            if not entry.is_dir():
                continue

            item_title = entry.name
            poster_url = None

            try:
                # Scan inside the folder for an image
                for item_in_folder in os.scandir(entry.path):
                    if not item_in_folder.is_file():
                        continue

                    file_ext = Path(item_in_folder.name).suffix.lower()

                    if file_ext in ALLOWED_POSTER_EXTENSIONS:
                        poster_name = item_in_folder.name
                        # Construct URL: /static_media/Movies/Movie Title/poster.jpg
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
        raise HTTPException(status_code=403, detail="Permission denied reading Movies directory")

    library.sort(key=lambda x: x.title)
    return library