import os
import shutil
from pathlib import Path
from typing import Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form

from pydantic import BaseModel

from app.core.config import settings
from app.models.file import DirectoryListing, FileItem
from app.services.tmdb import is_video_file, analyze_filename, download_poster

router = APIRouter()


class MkdirRequest(BaseModel):
    """
    Request model for creating a new directory.
    """
    path: str = "."   # The relative path where the new folder will be created
    folder_name: str  # The name of the new folder


class DeleteRequest(BaseModel):
    """
    Request model for deleting a file or directory.
    """
    path: str           # Current directory relative to MEDIA_ROOT_PATH (e.g., '.' or 'Anime/Frieren')
    name: str           # The name of the file or folder to delete
    is_dir: bool = False


class MoveCopyRequest(BaseModel):
    """
    Request model for moving or copying files/directories.
    """
    src_path: str       # Source directory (relative path)
    dst_path: str       # Destination directory (relative path)
    name: str           # Name of the file or folder
    is_dir: bool = False
    mode: Literal["copy", "cut"] = "copy"   # copy = Duplicate, cut = Move


def get_real_path(user_path: str) -> Path:
    """
    Safely convert a user-provided relative path to an absolute server path.
    Includes critical security checks to prevent Path Traversal attacks.

    Args:
        user_path (str): The relative path requested by the user (e.g., "Movies/Action").

    Returns:
        Path: The resolved absolute path on the filesystem.

    Raises:
        HTTPException: If path is invalid, out of bounds, or does not exist.
    """
    # 1. Normalize the path to remove redundant separators or ".."
    # e.g., "Photos/../Anime" becomes "Anime"
    safe_path = Path(os.path.normpath(user_path))

    # 2. Security Check: Prevent paths starting with ".." or absolute paths
    if safe_path.is_absolute() or str(safe_path).startswith(".."):
        raise HTTPException(status_code=400, detail="Invalid path request")

    # 3. Construct the full path by joining with MEDIA_ROOT_PATH
    # e.g., /path/to/my_media_files + Anime
    full_path = settings.MEDIA_ROOT_PATH.joinpath(safe_path).resolve()

    # 4. Critical Security Check: Ensure the resolved path is still within MEDIA_ROOT_PATH
    # This prevents accessing system files like /etc/passwd
    if not str(full_path).startswith(str(settings.MEDIA_ROOT_PATH.resolve())):
        raise HTTPException(status_code=403, detail="Access Denied: Path traversal detected")

    # 5. Verify existence
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")

    return full_path


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(
    # Query parameter default is "." (Root directory)
    path: str = Query(default=".", description="Relative path to browse")
):
    """
    List files and directories within a specific path in the media root.
    """
    try:
        real_path = get_real_path(path)
    except HTTPException as e:
        # Re-raise exceptions from the helper function
        raise e

    if not real_path.is_dir():
        raise HTTPException(status_code=400, detail="Requested path is not a directory")

    file_items = []
    try:
        # Iterate through directory entries
        for entry in os.scandir(real_path):
            stat = entry.stat()
            file_items.append(FileItem(
                name=entry.name,
                is_dir=entry.is_dir(),
                modified=datetime.fromtimestamp(stat.st_mtime),
                size=stat.st_size if not entry.is_dir() else 0
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading directory")

    # Sort items: Directories first, then files (alphabetical order)
    file_items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    return DirectoryListing(
        path=path,  # Return the requested relative path for UI context
        items=file_items
    )


@router.post("/upload")
async def upload_files(
        path: str = Form(default=".", description="Target relative path for upload"),
        files: list[UploadFile] = File(description="List of files to upload"),
):
    """
    Smart Upload: Automatically detects video files, queries TMDB for metadata,
    creates a dedicated folder, and downloads the poster.
    """
    uploaded_details = []

    try:
        base_destination_dir = get_real_path(path)
        if not base_destination_dir.is_dir():
            raise HTTPException(status_code=400, detail="Target path is not a directory")

        for file in files:
            # === Smart Recognition Logic Start ===
            final_folder = base_destination_dir
            poster_path_from_tmdb = None
            recognition_status = "Unrecognized/Standard File"

            # 1. Check if it is a video file
            if is_video_file(file.filename):
                print(f"Analyzing video: {file.filename} ...")

                # 2. Call TMDB service to analyze filename
                official_title, media_type, poster_ext, _ = analyze_filename(file.filename)

                if official_title:
                    # 3. Recognition Success!
                    # Determine new folder name. Sanitize title to remove illegal characters.
                    safe_title = "".join([c for c in official_title if c not in r'\/:*?"<>|'])

                    # Create subdirectory for the media
                    new_sub_folder = base_destination_dir.joinpath(safe_title)
                    if not new_sub_folder.exists():
                        os.makedirs(new_sub_folder)

                    # Update save destination
                    final_folder = new_sub_folder
                    poster_path_from_tmdb = poster_ext
                    recognition_status = f"Recognized: {safe_title} ({media_type})"
                else:
                    print("No match found on TMDB")

            # === Smart Recognition Logic End ===

            # 4. Save the file (to final_folder)
            file_path = final_folder.joinpath(file.filename)

            if file_path.exists():
                # Simple handling: Skip if file exists
                uploaded_details.append(f"{file.filename} (Skipped: Already exists)")
                continue

            try:
                # Write file content asynchronously
                with open(file_path, "wb") as buffer:
                    while contents := await file.read(1024 * 1024): # Read in 1MB chunks
                        buffer.write(contents)

                # 5. Download poster if available
                if poster_path_from_tmdb:
                    download_poster(poster_path_from_tmdb, str(final_folder))

                uploaded_details.append(f"{file.filename} -> {recognition_status}")

            except Exception as e:
                uploaded_details.append(f"{file.filename} (Failed: {str(e)})")
            finally:
                await file.close() # Ensure file handle is closed

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during upload: {e}")

    return {
        "message": "Upload processing complete",
        "details": uploaded_details
    }


@router.post("/mkdir")
async def create_directory(
    request: MkdirRequest
):
    """
    Create a new directory at the specified relative path.
    """

    # 1. Validate directory name safety
    # Ensure name does not contain traversal characters
    if ".." in request.folder_name or "/" in request.folder_name or "\\" in request.folder_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid folder name"
        )

    try:
        # 2. Get the real path of the *parent* directory
        parent_dir = get_real_path(request.path)
    except HTTPException as e:
        raise e

    # 3. Ensure parent is a directory
    if not parent_dir.is_dir():
        raise HTTPException(status_code=400, detail="Target path is not a directory")

    # 4. Construct full path for the new folder
    new_folder_path = parent_dir.joinpath(request.folder_name)

    # 5. Check if it already exists
    if new_folder_path.exists():
        raise HTTPException(
            status_code=409,
            detail="Folder or file with this name already exists"
        )

    try:
        # 6. Create the directory
        os.makedirs(new_folder_path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to create folder here")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {e}")

    return {
        "message": "Folder created successfully",
        "new_folder_path": f"{request.path}/{request.folder_name}"
    }

@router.post("/delete")
async def delete_entry(req: DeleteRequest):
    """
    Delete a specific file or directory.
    Recursive deletion is performed if the target is a directory.
    """
    base_root: Path = settings.MEDIA_ROOT_PATH.resolve()

    # Normalize path
    rel = (req.path or ".").strip().strip("/")
    real_dir = (base_root / rel).resolve()

    # Security Check: Must be within MEDIA_ROOT_PATH
    if base_root not in real_dir.parents and real_dir != base_root:
        raise HTTPException(status_code=400, detail="Invalid path")

    target = real_dir / req.name

    if not target.exists():
        raise HTTPException(status_code=404, detail="Target does not exist")

    # Type consistency check
    if req.is_dir and not target.is_dir():
        raise HTTPException(status_code=400, detail="Target is not a directory")
    if not req.is_dir and not target.is_file():
        raise HTTPException(status_code=400, detail="Target is not a file")

    try:
        if target.is_dir():
            shutil.rmtree(target) # Recursive delete
        else:
            target.unlink() # Delete file
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")

    return {"message": "Delete successful"}

@router.post("/move_copy")
async def move_or_copy(req: MoveCopyRequest):
    """
    Copy or Move files/folders between directories.
    """
    base_root: Path = settings.MEDIA_ROOT_PATH.resolve()

    def resolve_sub(path_str: str) -> Path:
        """Helper to resolve and validate sub-paths"""
        rel = (path_str or ".").strip().strip("/")
        p = (base_root / rel).resolve()
        if base_root not in p.parents and p != base_root:
            raise HTTPException(status_code=400, detail="Invalid path detected")
        return p

    try:
        src_dir = resolve_sub(req.src_path)
        dst_dir = resolve_sub(req.dst_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Path error: {e}")

    src = src_dir / req.name
    dst = dst_dir / req.name

    if not src.exists():
        raise HTTPException(status_code=404, detail="Source file does not exist")

    # Type Check
    if req.is_dir and not src.is_dir():
        raise HTTPException(status_code=400, detail="Source is not a directory")
    if not req.is_dir and not src.is_file():
        raise HTTPException(status_code=400, detail="Source is not a file")

    if dst.exists():
        raise HTTPException(status_code=400, detail="Destination already exists (Overwrite not supported)")

    try:
        if req.mode == "copy":
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        else:  # cut -> move
            shutil.move(str(src), str(dst))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied during copy/move")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copy/Move failed: {e}")

    return {"message": "Operation successful"}