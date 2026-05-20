"""
pixabay_provider.py - Pixabay video search and download helper.

search_pixabay_video() fetches a B-roll clip from Pixabay based on narration
text, downloads it locally, and trims it to the requested duration.
Returns None on failure so callers can continue to the AI image fallback.
"""

import os
import re
import subprocess
import tempfile
import time

import requests

from pexels_provider import _keyword_from_narration
from runtime_trace import append_api_usage


PIXABAY_SEARCH_TIMEOUT = (10, 25)
PIXABAY_DOWNLOAD_TIMEOUT = (10, 45)
PIXABAY_DOWNLOAD_WALL_TIMEOUT_SECONDS = 75
PIXABAY_MAX_DOWNLOAD_BYTES = 90 * 1024 * 1024
PIXABAY_FFMPEG_TIMEOUT_SECONDS = 45


def _best_pixabay_video_file(hit: dict) -> dict | None:
    videos = hit.get("videos") or {}
    candidates = []
    for quality in ("medium", "small", "large", "tiny"):
        item = videos.get(quality) or {}
        url = item.get("url")
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        size = int(item.get("size") or 0)
        if not url or width <= 0 or height <= 0:
            continue
        if width <= height:
            continue
        if size and size > PIXABAY_MAX_DOWNLOAD_BYTES:
            continue
        candidates.append({
            "quality": quality,
            "url": url,
            "width": width,
            "height": height,
            "size": size,
        })
    if not candidates:
        return None

    preferred = [c for c in candidates if c["quality"] in {"medium", "small"}]
    pool = preferred or candidates
    pool.sort(key=lambda item: item["width"] * item["height"], reverse=True)
    return pool[0]


def search_pixabay_video(
    narration_chunk: str,
    api_key: str,
    output_path: str,
    time_per_asset: float,
    asset_index: int = 0,
    keyword: str | None = None,
) -> str | None:
    """Search Pixabay for a B-roll video clip, download and trim it."""
    if not api_key or not narration_chunk:
        return None

    try:
        keyword = re.sub(r"[^a-z0-9 ]", " ", str(keyword or "").lower()).strip()[:60]
        keyword = re.sub(r"\s+", " ", keyword).strip() or _keyword_from_narration(narration_chunk)
        if not keyword:
            return None
        print(f"  Pixabay keyword: {keyword}")

        search_url = "https://pixabay.com/api/videos/"
        params = {
            "key": api_key,
            "q": keyword,
            "lang": "en",
            "video_type": "film",
            "safesearch": "true",
            "order": "popular",
            "per_page": 20,
            "min_width": 640,
            "min_height": 360,
        }

        resp = requests.get(search_url, params=params, timeout=PIXABAY_SEARCH_TIMEOUT)
        resp.raise_for_status()
        append_api_usage(
            "pixabay_video",
            "requests",
            1,
            endpoint=search_url,
            keyword=keyword,
        )
        data = resp.json()

        hits = data.get("hits") or []
        min_duration = max(3, int(time_per_asset))
        usable = []
        for hit in hits:
            duration = int(hit.get("duration") or 0)
            if duration and duration < min_duration:
                continue
            video_file = _best_pixabay_video_file(hit)
            if video_file:
                usable.append((hit, video_file))
        if not usable:
            return None

        _, chosen = usable[asset_index % len(usable)]
        chosen_url = chosen.get("url")
        if not chosen_url:
            return None

        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        suffix = os.path.splitext(output_path)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

        try:
            started_at = time.monotonic()
            bytes_written = 0
            dl_resp = requests.get(chosen_url, stream=True, timeout=PIXABAY_DOWNLOAD_TIMEOUT)
            dl_resp.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in dl_resp.iter_content(chunk_size=1024 * 256):
                    if time.monotonic() - started_at > PIXABAY_DOWNLOAD_WALL_TIMEOUT_SECONDS:
                        raise TimeoutError("Pixabay video download exceeded wall-clock timeout.")
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
                        if bytes_written > PIXABAY_MAX_DOWNLOAD_BYTES:
                            raise RuntimeError("Pixabay video download exceeded max size.")

            if os.path.getsize(tmp_path) < 10_000:
                return None

            trim_result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-t", str(time_per_asset + 1),
                    "-c:v", "copy", "-c:a", "copy",
                    output_path,
                ],
                capture_output=True,
                timeout=PIXABAY_FFMPEG_TIMEOUT_SECONDS,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if trim_result.returncode != 0:
            if os.path.exists(output_path):
                os.remove(output_path)
            return None

        if os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
            return output_path

        if os.path.exists(output_path):
            os.remove(output_path)
        return None

    except Exception as exc:
        print(f"  Warning: Pixabay video search failed: {exc}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
