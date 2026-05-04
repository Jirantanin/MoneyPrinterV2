from __future__ import annotations

import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

try:
    from space_automation.config import SpaceAutomationConfig
    from space_automation.models import SpaceControlMetadata
    from space_automation.subtitles import SubtitleSegment
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config import SpaceAutomationConfig
    from models import SpaceControlMetadata
    from subtitles import SubtitleSegment


@dataclass(slots=True)
class RenderOutput:
    output_path: str
    template_used: str
    width: int
    height: int
    duration_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


def _default_font_file() -> str:
    return Path("C:/Windows/Fonts/arial.ttf").resolve().as_posix().replace(":", r"\:")


def _ffmpeg_escape_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\xa0": " ",
    }
    normalized = "".join(replacements.get(ch, ch) for ch in text)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")

    escaped = normalized.replace("\\", "\\\\")
    escaped = escaped.replace(":", r"\:")
    escaped = escaped.replace("'", r"\'")
    escaped = escaped.replace("%", r"\%")
    escaped = escaped.replace(",", r"\,")
    escaped = escaped.replace("[", r"\[")
    escaped = escaped.replace("]", r"\]")
    escaped = escaped.replace("\n", r"\n")
    return escaped


def _safe_zone_position(safe_zone: str) -> tuple[str, str]:
    mapping = {
        "top_left": ("60", "120"),
        "top_center": ("(w-text_w)/2", "120"),
        "top_right": ("w-text_w-60", "120"),
        "center": ("(w-text_w)/2", "(h-text_h)/2"),
        "bottom_left": ("60", "h-text_h-220"),
        "bottom_center": ("(w-text_w)/2", "h-text_h-220"),
        "bottom_right": ("w-text_w-60", "h-text_h-220"),
    }
    return mapping.get(safe_zone, ("60", "120"))


def _wrap_caption(text: str, width: int = 30) -> str:
    words = text.split()
    if not words:
        return ""

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return "\n".join(lines[:3])


def _caption_filters(
    segments: list[SubtitleSegment],
    font_file: str,
    caption_dir: Path,
) -> str:
    filters: list[str] = []
    caption_dir.mkdir(parents=True, exist_ok=True)
    for segment in segments:
        wrapped = _wrap_caption(segment.text)
        if not wrapped:
            continue
        caption_file = caption_dir / f"caption_{segment.index:02d}.txt"
        caption_file.write_text(wrapped, encoding="utf-8")
        caption_file_arg = str(caption_file.resolve()).replace("\\", "/").replace(":", r"\:")
        filters.append(
            "drawtext="
            f"fontfile='{font_file}':"
            f"textfile='{caption_file_arg}':"
            "fontcolor=white:fontsize=52:borderw=3:bordercolor=black@0.78:"
            "box=1:boxcolor=black@0.20:boxborderw=18:"
            "x=(w-text_w)/2:y=h-text_h-140:"
            f"enable='between(t\\,{segment.start_seconds:.3f}\\,{segment.end_seconds:.3f})'"
        )
    return ",".join(filters)


def _build_video_filter(
    *,
    overlay_text: str,
    safe_zone: str,
    duration_seconds: float,
    config: SpaceAutomationConfig,
    template: str,
    subtitle_segments: list[SubtitleSegment],
    caption_dir: Path,
) -> str:
    overlay_x, overlay_y = _safe_zone_position(safe_zone)
    font_file = _default_font_file()
    overlay_filter = (
        "drawtext="
        f"fontfile='{font_file}':"
        f"text='{_ffmpeg_escape_text(overlay_text)}':"
        "fontcolor=white:fontsize=54:borderw=3:bordercolor=black@0.65:"
        "box=1:boxcolor=black@0.25:boxborderw=18:"
        f"x={overlay_x}:y={overlay_y}"
    )
    caption_filter = _caption_filters(subtitle_segments, font_file, caption_dir)
    text_filters = ",".join(filter(None, [overlay_filter, caption_filter]))

    if template == "portrait_ken_burns":
        total_frames = max(1, int(duration_seconds * config.target_fps))
        return (
            f"[0:v]scale={config.target_width}:{config.target_height}:force_original_aspect_ratio=increase,"
            f"crop={config.target_width}:{config.target_height},"
            f"zoompan=z='min(zoom+0.0008,1.12)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={config.target_width}x{config.target_height}:fps={config.target_fps},"
            f"{text_filters}[vout]"
        )

    return (
        f"[0:v]scale={config.target_width}:{config.target_height}:force_original_aspect_ratio=increase,"
        f"crop={config.target_width}:{config.target_height},boxblur=25:10[bg];"
        f"[0:v]scale={config.target_width}:{config.target_height}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{text_filters}[vout]"
    )


def render_short_video(
    *,
    config: SpaceAutomationConfig,
    image_path: Path,
    audio_path: Path,
    control: SpaceControlMetadata,
    subtitle_segments: list[SubtitleSegment],
    duration_seconds: float,
    output_path: Path,
) -> RenderOutput:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as image:
        width, height = image.size

    template = control.template
    if height >= width:
        template = "portrait_ken_burns"
    elif template not in {"landscape_blur", "portrait_ken_burns"}:
        template = "landscape_blur"

    filter_complex = _build_video_filter(
        overlay_text=control.overlay_text,
        safe_zone=control.safe_zone,
        duration_seconds=duration_seconds,
        config=config,
        template=template,
        subtitle_segments=subtitle_segments,
        caption_dir=output_path.parent / "caption_text",
    )

    command = [
        config.ffmpeg_path,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(config.target_fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg render failed: "
            f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        )

    return RenderOutput(
        output_path=str(output_path),
        template_used=template,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )
