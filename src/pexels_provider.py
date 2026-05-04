"""
pexels_provider.py — Pexels Video search and download helper.

search_pexels_video() fetches a B-roll clip from Pexels based on narration text,
generates keywords automatically, and trims the clip to the required duration.
Returns None on any failure so callers can fall back to AI-generated images.
"""

import os
import re
import subprocess
import tempfile

import requests

from llm_provider import generate_text
from runtime_trace import append_api_usage


def search_pexels_video(
    narration_chunk: str,
    api_key: str,
    output_path: str,
    time_per_asset: float,
    asset_index: int = 0,
) -> str | None:
    """Search Pexels for a B-roll video clip, download and trim it.

    Generates English keywords from narration_chunk, searches Pexels,
    downloads the clip to a temp file, trims to time_per_asset+1s via ffmpeg,
    then deletes the temp file.

    Returns:
        output_path on success, None if no clip found or any error occurs.
    """
    if not api_key or not narration_chunk:
        return None

    try:
        raw_kw = generate_text(
            "Extract a 2-3 word English keyword phrase for a B-roll video search.\n"
            "The phrase must be generic enough to find stock footage.\n"
            "Examples: 'city traffic night', 'ocean waves', 'forest fog', 'scientist lab'\n"
            "Return ONLY the keyword phrase, no punctuation, no explanation.\n\n"
            f"NARRATION:\n{narration_chunk}"
        )
        keyword = re.sub(r"[^a-z0-9 ]", "", raw_kw.strip().lower()).strip()[:60]
        if not keyword:
            return None

        search_url = "https://api.pexels.com/videos/search"
        params = {
            "query": keyword,
            "per_page": 10,
            "orientation": "landscape",
            "min_duration": max(3, int(time_per_asset)),
            "max_duration": 120,
        }
        headers = {"Authorization": api_key}

        resp = requests.get(search_url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        append_api_usage(
            "pexels_video",
            "requests",
            1,
            endpoint=search_url,
            keyword=keyword,
        )
        data = resp.json()

        videos = data.get("videos") or []
        if not videos:
            return None

        video = videos[asset_index % len(videos)]
        files = video.get("video_files") or []

        # Only keep landscape files (width > height)
        landscape = [f for f in files if (f.get("width") or 0) > (f.get("height") or 0)]
        if not landscape:
            landscape = files

        hd_files = [f for f in landscape if f.get("quality") == "hd"]
        sd_files = [f for f in landscape if f.get("quality") == "sd"]
        candidates = hd_files or sd_files
        if not candidates:
            return None

        candidates.sort(
            key=lambda f: (f.get("width") or 0) * (f.get("height") or 0),
            reverse=True,
        )
        chosen_url = candidates[0].get("link")
        if not chosen_url:
            return None

        # Download to a temp file, then trim to output_path
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        suffix = os.path.splitext(output_path)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

        try:
            dl_resp = requests.get(chosen_url, stream=True, timeout=120)
            dl_resp.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in dl_resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            if os.path.getsize(tmp_path) < 10_000:
                return None

            # Trim to time_per_asset + 1s buffer so Remotion only decodes what's needed
            trim_result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-t", str(time_per_asset + 1),
                    "-c:v", "copy", "-c:a", "copy",
                    output_path,
                ],
                capture_output=True,
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
        print(f"  Warning: Pexels video search failed: {exc}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
