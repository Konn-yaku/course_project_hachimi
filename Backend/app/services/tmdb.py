import os
import requests
from guessit import guessit
from app.core.config import settings

# TMDB API Configuration
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
LANGUAGE = "zh-CN"  # Request results in Chinese (Change to 'en-US' for English)

# Common video file extensions used to determine if smart recognition should be triggered
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}


def is_video_file(filename: str) -> bool:
    """
    Check if the file extension corresponds to a video file.
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


def get_tmdb_info(title, year=None):
    """
    Query The Movie Database (TMDB) for media information based on title and optional year.

    Args:
        title (str): The cleaned title extracted from the filename.
        year (int, optional): The release year extracted from the filename.

    Returns:
        dict: The best matching result dictionary from TMDB, or None if no match found.
    """
    if not settings.TMDB_API_KEY:
        print("⚠️ Warning: TMDB_API_KEY is not configured.")
        return None

    endpoint = f"{BASE_URL}/search/multi"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "query": title,
        "language": LANGUAGE,
        "page": 1
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            return None

        # --- Smart Matching Logic ---
        best_match = None

        # 1. Priority: Match by Year
        if year:
            for item in results:
                # Movies use 'release_date', TV shows use 'first_air_date'
                release_date = item.get("release_date") or item.get("first_air_date")
                if release_date and str(year) in release_date:
                    best_match = item
                    break

        # 2. Fallback: If no year match or year not provided, take the first Movie or TV result
        if not best_match:
            # Filter results to include only 'movie' or 'tv' types (exclude 'person')
            media_results = [r for r in results if r.get('media_type') in ('movie', 'tv')]
            if media_results:
                best_match = media_results[0]
            else:
                return None

        return best_match

    except Exception as e:
        print(f"TMDB Connection Error: {e}")
        return None


def download_poster(poster_path: str, save_dir: str):
    """
    Download the poster image from TMDB and save it as 'poster.jpg' in the target directory.
    """
    if not poster_path:
        return

    url = f"{IMAGE_BASE_URL}{poster_path}"
    save_path = os.path.join(save_dir, "poster.jpg")

    # If poster already exists, skip downloading to save bandwidth
    if os.path.exists(save_path):
        return

    try:
        print(f"Downloading poster: {url}")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print("Poster download successful")
    except Exception as e:
        print(f"Poster download failed: {e}")


def analyze_filename(filename: str):
    """
    Analyze the filename to extract metadata and query TMDB.

    Args:
        filename (str): The name of the uploaded file.

    Returns:
        tuple: (official_title, media_type, poster_path, raw_guessit_info)
               Returns (None, None, None, guess_info) if recognition fails.
    """
    # Use 'guessit' library to parse the filename (extracts title, year, episode, etc.)
    guess = guessit(filename)
    clean_title = guess.get('title')
    guess_year = guess.get('year')

    if not clean_title:
        return None, None, None, guess

    # Query TMDB with extracted info
    tmdb_result = get_tmdb_info(clean_title, guess_year)

    if tmdb_result:
        official_title = tmdb_result.get('title') or tmdb_result.get('name')
        media_type = tmdb_result.get('media_type')  # 'movie' or 'tv'
        poster_path = tmdb_result.get('poster_path')
        return official_title, media_type, poster_path, guess

    return None, None, None, guess