#!/usr/bin/env python3
"""Build a standalone promo Short for the 2026-05-10 space-body episode."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from classes.Tts import TTS  # noqa: E402
from config import get_tts_edge_thai_rate, get_tts_edge_thai_voice  # noqa: E402


EPISODE = ROOT / ".mp" / "podcast_v2_20260510_232355"
OUT = EPISODE / "short_promo_space_body_v2"
DURATION_PER_SHOT = 3.0
W, H, FPS = 1080, 1920, 30

SCRIPT = (
    "ถ้าเราจะไปอยู่บนดาวอังคารจริง ๆ คำถามไม่ใช่แค่ว่า ยานไปถึงไหม "
    "แต่คือร่างกายมนุษย์จะจ่ายราคาอะไรระหว่างทาง "
    "ในอวกาศ ดวงตาอาจเปลี่ยนโดยแทบไม่รู้ตัว กระดูกเริ่มบาง กล้ามเนื้อค่อย ๆ หายแรง "
    "รังสีลึก ๆ สะสมในร่างกาย และความโดดเดี่ยวบีบสมองมากกว่าที่เราชอบยอมรับ "
    "นี่ไม่ใช่คลิปขายฝันเรื่องอวกาศสวย ๆ แต่มันคือด้านที่เงียบที่สุดของการออกจากโลก "
    "ดูคลิปหลัก แล้วลองตอบตัวเองว่า ถ้าเราไปถึงดาวอังคารได้จริง "
    "เรายังจะกลับมาเป็นมนุษย์แบบเดิมได้แค่ไหน"
)

CAPTIONS = [
    "คำถามไม่ใช่แค่ว่า\\Nยานไปถึงไหม",
    "แต่ร่างกายมนุษย์\\Nต้องจ่ายราคาอะไร",
    "ในอวกาศ\\Nดวงตาอาจเปลี่ยนเงียบ ๆ",
    "กระดูกเริ่มบาง\\Nกล้ามเนื้อค่อย ๆ หายแรง",
    "รังสีลึก ๆ\\Nสะสมในร่างกาย",
    "และความโดดเดี่ยว\\Nบีบสมองมากกว่าที่คิด",
    "นี่ไม่ใช่คลิปขายฝัน\\Nเรื่องอวกาศสวย ๆ",
    "แต่มันคือด้านที่เงียบที่สุด\\Nของการออกจากโลก",
    "ถ้าเราไปถึงดาวอังคารได้จริง",
    "เรายังจะกลับมาเป็นมนุษย์\\Nแบบเดิมได้แค่ไหน",
]

PEXELS_QUERIES = [
    "astronaut space station",
    "rocket launch night",
    "earth from space",
    "astronaut floating space station",
    "medical laboratory human body",
    "bone scan medical",
    "radiation warning science",
    "mars landscape",
    "isolated astronaut",
    "spacecraft control room",
    "deep space stars",
    "astronaut helmet reflection",
    "red planet mars",
    "space station earth window",
    "futuristic medical scan",
    "astronaut walking",
    "space mission control",
    "planet earth orbit",
]


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print("[promo]", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def capture(cmd: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def audio_duration(path: Path) -> float:
    raw = capture([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(path),
    ]).strip()
    return float(raw)


def ass_time(seconds: float) -> str:
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(path: Path, duration: float) -> None:
    title_end = min(5.5, duration)
    caption_start = 0.35
    usable = max(1.0, duration - caption_start - 0.2)
    per = usable / len(CAPTIONS)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        (
            "Style: Caption,Leelawadee UI,72,&H00FFFFFF,&H000000FF,&H00101010,"
            "&H99000000,-1,0,0,0,100,100,0,0,1,5,1,2,70,70,245,1"
        ),
        (
            "Style: Title,Leelawadee UI,78,&H00F7FBFF,&H000000FF,&H00101010,"
            "&H88000000,-1,0,0,0,100,100,0,0,1,5,0,8,70,70,145,1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,{ass_time(0)},{ass_time(title_end)},Title,,0,0,0,,ร่างกายมนุษย์\\Nไม่ได้ถูกสร้างมาเพื่ออวกาศ",
    ]
    for i, text in enumerate(CAPTIONS):
        start = caption_start + i * per
        end = min(duration, caption_start + (i + 1) * per)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def synthesize_voice(path: Path) -> None:
    if path.is_file() and path.stat().st_size > 10_000:
        return
    try:
        TTS().synthesize_gemini(SCRIPT, str(path), scene_index=0, total_scenes=1)
    except Exception as exc:  # noqa: BLE001
        print(f"[promo] Gemini TTS failed, using Edge Thai fallback: {exc}")
        TTS().synthesize(
            SCRIPT,
            output_file=str(path),
            voice=get_tts_edge_thai_voice(),
            rate=get_tts_edge_thai_rate(),
        )


def pexels_video_url(api_key: str, query: str, index: int) -> tuple[str, int | None] | None:
    if not api_key:
        return None
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": 8,
            "orientation": "portrait",
            "min_duration": 3,
            "max_duration": 90,
        },
        timeout=30,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos") or []
    if not videos:
        return None
    video = videos[index % len(videos)]
    files = video.get("video_files") or []
    candidates = [f for f in files if f.get("link") and (f.get("height") or 0) >= 720]
    candidates = candidates or [f for f in files if f.get("link")]
    if not candidates:
        return None
    candidates.sort(
        key=lambda f: (
            1 if (f.get("height") or 0) > (f.get("width") or 0) else 0,
            (f.get("width") or 0) * (f.get("height") or 0),
        ),
        reverse=True,
    )
    return candidates[0]["link"], video.get("id")


def download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_content(1024 * 256):
                if chunk:
                    f.write(chunk)


def fallback_assets() -> list[Path]:
    assets = []
    for ext in ("*.mp4", "*.png", "*.jpg", "*.jpeg"):
        assets.extend(sorted(EPISODE.glob(f"scene_*_{ext[1:]}")))
    return [p for p in assets if p.is_file()]


def render_segment_from_video(src: Path, dest: Path) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},fps={FPS},format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{DURATION_PER_SHOT:.3f}", "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(dest),
    ])


def render_segment_from_image(src: Path, dest: Path) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},zoompan=z='min(zoom+0.0010,1.08)':d={int(DURATION_PER_SHOT * FPS)}:"
        f"s={W}x{H}:fps={FPS},format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(src),
        "-t", f"{DURATION_PER_SHOT:.3f}", "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(dest),
    ])


def make_segments(count: int, api_key: str) -> list[Path]:
    assets_dir = OUT / "assets"
    segments_dir = OUT / "segments"
    assets_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(segments_dir.glob("seg_*.mp4"))
    if len(existing) >= count:
        return existing[:count]

    fallback = fallback_assets()
    manifest = []
    segments = []
    for i in range(count):
        segment = segments_dir / f"seg_{i + 1:02d}.mp4"
        if segment.is_file() and segment.stat().st_size > 10_000:
            segments.append(segment)
            continue

        query = PEXELS_QUERIES[i % len(PEXELS_QUERIES)]
        source_path: Path | None = None
        source_kind = "fallback"
        source_id = None
        try:
            found = pexels_video_url(api_key, query, i)
            if found:
                url, source_id = found
                suffix = Path(urlparse(url).path).suffix or ".mp4"
                source_path = assets_dir / f"pexels_{i + 1:02d}{suffix}"
                if not source_path.is_file() or source_path.stat().st_size < 10_000:
                    download(url, source_path)
                source_kind = "pexels"
        except Exception as exc:  # noqa: BLE001
            print(f"[promo] Pexels failed for '{query}': {exc}")

        if source_path is None:
            source_path = fallback[i % len(fallback)]

        if source_path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
            render_segment_from_video(source_path, segment)
        else:
            render_segment_from_image(source_path, segment)

        manifest.append({
            "segment": segment.name,
            "query": query,
            "source": source_kind,
            "source_id": source_id,
            "source_path": str(source_path),
        })
        segments.append(segment)

    (OUT / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return segments


def concat_segments(segments: list[Path], dest: Path) -> None:
    concat = OUT / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(dest)])


def burn_subtitles(base: Path, audio: Path, ass: Path, dest: Path, duration: float) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        local_base = tmp_path / "base.mp4"
        local_audio = tmp_path / "voice.wav"
        local_ass = tmp_path / "promo.ass"
        shutil.copy2(base, local_base)
        shutil.copy2(audio, local_audio)
        shutil.copy2(ass, local_ass)
        local_out = tmp_path / "rendered.mp4"
        run([
            "ffmpeg", "-y",
            "-i", str(local_base),
            "-i", str(local_audio),
            "-t", f"{duration:.3f}",
            "-vf", "ass=promo.ass",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(local_out),
        ], cwd=tmp_path)
        shutil.copy2(local_out, dest)


def write_upload_pack(video: Path, preview: Path, thumbnail: Path, ass: Path) -> None:
    pack = OUT / "upload_pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True)
    shutil.copy2(video, pack / "video.mp4")
    shutil.copy2(preview, pack / "preview.jpg")
    shutil.copy2(thumbnail, pack / "thumbnail.jpg")
    shutil.copy2(ass, pack / "subtitle.ass")
    (pack / "title.txt").write_text(
        "ร่างกายมนุษย์ไม่ได้ถูกสร้างมาเพื่ออวกาศ #Shorts\n",
        encoding="utf-8",
    )
    (pack / "description.txt").write_text(
        "Promo จากคลิปหลัก: ร่างกายมนุษย์จ่ายราคาอะไร เมื่อออกไปใช้ชีวิตในอวกาศ\n\n"
        "ดูคลิปเต็มในช่อง\n\n"
        "#Shorts #อวกาศ #ดาวอังคาร #นักบินอวกาศ #วิทยาศาสตร์ #ร่างกายมนุษย์\n",
        encoding="utf-8",
    )
    (pack / "hashtags.txt").write_text(
        "#Shorts #อวกาศ #ดาวอังคาร #นักบินอวกาศ #วิทยาศาสตร์ #ร่างกายมนุษย์\n",
        encoding="utf-8",
    )
    (pack / "keywords.txt").write_text(
        "อวกาศ\nดาวอังคาร\nร่างกายมนุษย์\nนักบินอวกาศ\nกระดูก\nรังสี\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "script.txt").write_text(SCRIPT + "\n", encoding="utf-8")

    voice = OUT / "voice.wav"
    synthesize_voice(voice)
    duration = audio_duration(voice)
    shot_count = max(1, math.ceil(duration / DURATION_PER_SHOT))

    ass = OUT / "subtitle.ass"
    write_ass(ass, duration)

    api_key = str(load_config().get("pexels_api_key", "") or "").strip()
    segments = make_segments(shot_count, api_key)
    base = OUT / "promo_base.mp4"
    concat_segments(segments, base)

    final = OUT / "short_promo_space_body_v2.mp4"
    burn_subtitles(base, voice, ass, final, duration)

    preview = OUT / "preview_12s.jpg"
    thumbnail = OUT / "thumbnail.jpg"
    run(["ffmpeg", "-y", "-ss", "00:00:12", "-i", str(final), "-frames:v", "1", "-update", "1", str(preview)])
    run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(final), "-frames:v", "1", "-update", "1", str(thumbnail)])

    write_upload_pack(final, preview, thumbnail, ass)
    probe = capture([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration,size",
        "-of", "default=nw=1", str(final),
    ])
    (OUT / "ffprobe.txt").write_text(probe, encoding="utf-8")
    print("\n[promo] DONE")
    print(f"video={final}")
    print(f"preview={preview}")
    print(f"pack={OUT / 'upload_pack'}")
    print(probe)


if __name__ == "__main__":
    main()
