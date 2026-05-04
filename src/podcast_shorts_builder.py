"""
podcast_shorts_builder.py - Build a vertical YouTube Short from a podcast scene.

Supports both legacy single-image scenes and podcast_v2 multi-asset scenes.
"""

import json
import os
import subprocess
from pathlib import Path

from status import error, info, success

# Target dimensions for vertical Shorts (9:16)
_OUT_W = 1080
_OUT_H = 1920


def _find_scene_visual_assets(episode_dir: str, scene_id: str) -> list[str]:
    """
    Return visual assets for one scene, supporting both legacy and podcast_v2 layouts.

    Supported patterns:
      - legacy: scene_XX.png
      - podcast_v2: scene_XX_0.png / scene_XX_1.mp4 / ...
    """
    episode_path = Path(episode_dir)
    legacy_png = episode_path / f"{scene_id}.png"
    if legacy_png.is_file():
        return [str(legacy_png)]

    exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}
    assets = []
    for entry in sorted(episode_path.glob(f"{scene_id}_*")):
        if entry.is_file() and entry.suffix.lower() in exts:
            assets.append(str(entry))
    return assets


def _extract_video_poster_frame(src_video_path: str, dst_png_path: str) -> str:
    """Extract a poster frame from a video asset to a PNG for the short slideshow."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0.5",
            "-i",
            src_video_path,
            "-frames:v",
            "1",
            dst_png_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dst_png_path


def _center_crop_to_portrait(src_path: str, dst_path: str) -> str:
    """
    Center-crop a landscape image to portrait 1080x1920.
    """
    from PIL import Image as PILImage  # lazy import to match project convention

    img = PILImage.open(src_path).convert("RGB")
    src_w, src_h = img.size

    crop_w = int(src_h * 9 / 16)
    crop_w = min(crop_w, src_w)
    x_offset = (src_w - crop_w) // 2

    cropped = img.crop((x_offset, 0, x_offset + crop_w, src_h))
    cropped = cropped.resize((_OUT_W, _OUT_H), PILImage.LANCZOS)
    cropped.save(dst_path, "PNG")
    return dst_path


def build_short(episode_dir: str, scene_index: int, output_path: str) -> str:
    """
    Build a vertical YouTube Short from a single podcast scene.

    Assets are read from episode_dir:
      - Legacy visual: scene_{scene_index:02d}.png
      - podcast_v2 visual: scene_{scene_index:02d}_*.png/mp4/...
      - Audio: scene_{scene_index:02d}.wav

    Steps:
      1. Resolve all scene visual assets
      2. Convert video assets to poster PNGs, then center-crop each to 9:16
      3. Generate SRT subtitles from WAV via Whisper
      4. Invoke Remotion VideoShort renderer
      5. Return output MP4 path
    """
    if os.path.isfile(output_path):
        info(f"Short for scene {scene_index:02d} already exists - skipping build.")
        return output_path

    scene_id = f"scene_{scene_index:02d}"
    audio_path = os.path.join(episode_dir, f"{scene_id}.wav")
    visual_assets = _find_scene_visual_assets(episode_dir, scene_id)

    if not visual_assets:
        raise FileNotFoundError(
            f"Missing visual assets for {scene_id}. Expected {scene_id}.png or {scene_id}_* files."
        )
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Missing WAV asset: {audio_path}")

    # 1-2. Normalize all scene assets into portrait PNGs for VideoShort slideshow
    cropped_paths: list[str] = []
    info(f"Preparing {len(visual_assets)} visual asset(s) for {scene_id}...")
    for idx, asset_path in enumerate(visual_assets):
        asset_ext = Path(asset_path).suffix.lower()
        source_for_crop = asset_path

        if asset_ext in {".mp4", ".mov", ".webm"}:
            poster_path = os.path.join(episode_dir, f"{scene_id}_asset_{idx:02d}_poster.png")
            _extract_video_poster_frame(asset_path, poster_path)
            source_for_crop = poster_path

        cropped_path = os.path.join(episode_dir, f"{scene_id}_asset_{idx:02d}_cropped.png")
        _center_crop_to_portrait(source_for_crop, cropped_path)
        cropped_paths.append(cropped_path)

    # 3. Generate SRT subtitles
    info(f"Generating subtitles for {scene_id}.wav...")
    from classes.YouTube import YouTube  # lazy import avoids heavy MoviePy startup

    yt = YouTube("", "", "", "", run_dir=episode_dir)
    srt_path = yt.generate_subtitles(audio_path)

    # 4. Measure audio duration
    from moviepy.editor import AudioFileClip

    _audio_clip = AudioFileClip(audio_path)
    duration = _audio_clip.duration
    _audio_clip.close()

    # 5. Read scene metadata (topic + narration) from script.json
    script_path = os.path.join(episode_dir, "script.json")
    scene_title = ""
    narration = ""
    if os.path.isfile(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as fh:
                scenes = json.load(fh)
            if 0 <= scene_index < len(scenes):
                scene_title = scenes[scene_index].get("scene_title", "")
                narration = scenes[scene_index].get("narration", "")
        except Exception as exc:  # noqa: BLE001
            error(f"Could not read script.json for scene metadata: {exc}")

    # 6. Build Remotion VideoShort props
    from config import ROOT_DIR

    props = {
        "topic": scene_title,
        "script": narration,
        "category": "default",
        "imagePaths": [os.path.abspath(path) for path in cropped_paths],
        "audioPath": os.path.abspath(audio_path),
        "srtPath": os.path.abspath(srt_path) if srt_path else None,
        "bgmPath": None,
        "durationInSeconds": duration,
        "outputPath": os.path.abspath(output_path),
    }

    remotion_dir = Path(ROOT_DIR) / "remotion"
    props_file = remotion_dir / ".render-props-clip.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    info(f"Rendering Short for {scene_id} via Remotion...")

    subprocess.run(
        ["node", "scripts/render.mjs", str(props_file.resolve())],
        cwd=str(remotion_dir),
        check=True,
        timeout=900,
    )

    success(f"Short rendered: {output_path}")
    return output_path
