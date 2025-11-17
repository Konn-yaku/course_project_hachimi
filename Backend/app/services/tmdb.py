# app/services/tmdb.py

import os
import requests
from guessit import guessit
from app.core.config import settings

# 配置
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
LANGUAGE = "zh-CN"

# 常见的视频后缀，用于判断是否需要触发识别
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}


def is_video_file(filename: str) -> bool:
    """检查文件扩展名是否为视频"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


def get_tmdb_info(title, year=None):
    """根据标题和年份向 TMDB 查询信息"""
    if not settings.TMDB_API_KEY:
        print("⚠️ 警告: 未配置 TMDB_API_KEY")
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

        # --- 智能匹配逻辑 ---
        best_match = None

        # 1. 优先匹配年份
        if year:
            for item in results:
                release_date = item.get("release_date") or item.get("first_air_date")
                if release_date and str(year) in release_date:
                    best_match = item
                    break

                    # 2. 如果没匹配到年份，取第一个 Movie 或 TV
        if not best_match:
            media_results = [r for r in results if r.get('media_type') in ('movie', 'tv')]
            if media_results:
                best_match = media_results[0]
            else:
                return None

        return best_match

    except Exception as e:
        print(f"TMDB 连接错误: {e}")
        return None


def download_poster(poster_path: str, save_dir: str):
    """下载海报并保存为 poster.jpg"""
    if not poster_path:
        return

    url = f"{IMAGE_BASE_URL}{poster_path}"
    save_path = os.path.join(save_dir, "poster.jpg")

    # 如果海报已经存在，就不重复下载了
    if os.path.exists(save_path):
        return

    try:
        print(f"正在下载海报: {url}")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print("海报下载成功")
    except Exception as e:
        print(f"海报下载失败: {e}")


def analyze_filename(filename: str):
    """
    分析文件名，返回 (官方标题, 媒体类型, 海报路径, 原始Guessit信息)
    如果识别失败，返回 (None, None, None, guess_info)
    """
    guess = guessit(filename)
    clean_title = guess.get('title')
    guess_year = guess.get('year')

    if not clean_title:
        return None, None, None, guess

    tmdb_result = get_tmdb_info(clean_title, guess_year)

    if tmdb_result:
        official_title = tmdb_result.get('title') or tmdb_result.get('name')
        media_type = tmdb_result.get('media_type')  # 'movie' or 'tv'
        poster_path = tmdb_result.get('poster_path')
        return official_title, media_type, poster_path, guess

    return None, None, None, guess