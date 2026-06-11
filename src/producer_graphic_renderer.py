"""Local still-graphic renderer for Producer Mode visual tasks.

The renderer creates no-text 16:9 PNG diagrams for ``remotion_graphic`` beats
and, when requested, temporary no-text opener placeholders that unblock render
preflight without pretending Codex imagegen has been fulfilled.
"""

from __future__ import annotations

import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


GRAPHIC_RENDER_VERSION = 1
WIDTH = 1920
HEIGHT = 1080
MIN_GRAPHIC_BYTES = 10_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _scene_title(scene: dict[str, Any], fallback: str) -> str:
    return _clean_text(scene.get("scene_title") or scene.get("section_title"), fallback)


def _background(seed: int) -> Image.Image:
    rng = random.Random(seed)
    image = Image.new("RGB", (WIDTH, HEIGHT), "#101318")
    pixels = image.load()
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        r = int(12 + 14 * t)
        g = int(17 + 21 * t)
        b = int(23 + 28 * t)
        for x in range(WIDTH):
            vignette = ((x - WIDTH / 2) ** 2 / (WIDTH / 1.1) ** 2) + ((y - HEIGHT / 2) ** 2 / (HEIGHT / 1.1) ** 2)
            shade = max(0.62, 1.0 - vignette * 0.28)
            pixels[x, y] = (int(r * shade), int(g * shade), int(b * shade))

    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(260):
        x = rng.randrange(0, WIDTH)
        y = rng.randrange(0, HEIGHT)
        alpha = rng.randrange(55, 155)
        radius = 1 if rng.random() < 0.86 else 2
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(220, 235, 255, alpha))
    return image


def _soft_glow(image: Image.Image, bbox: tuple[int, int, int, int], color: tuple[int, int, int], blur: int = 42) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    draw.ellipse(bbox, fill=(*color, 95))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    image.paste(Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB"))


def _earth(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
    x, y = center
    draw.ellipse((x - radius - 26, y - radius - 26, x + radius + 26, y + radius + 26), fill=(74, 165, 218, 30))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(28, 89, 145, 255))
    draw.pieslice((x - radius, y - radius, x + radius, y + radius), 250, 45, fill=(40, 124, 183, 255))
    draw.polygon(
        [
            (x - radius * 0.52, y - radius * 0.12),
            (x - radius * 0.18, y - radius * 0.34),
            (x + radius * 0.22, y - radius * 0.24),
            (x + radius * 0.10, y + radius * 0.06),
            (x - radius * 0.24, y + radius * 0.14),
        ],
        fill=(53, 152, 106, 230),
    )
    draw.polygon(
        [
            (x + radius * 0.08, y + radius * 0.18),
            (x + radius * 0.43, y + radius * 0.05),
            (x + radius * 0.54, y + radius * 0.35),
            (x + radius * 0.20, y + radius * 0.46),
        ],
        fill=(64, 166, 112, 220),
    )
    draw.arc((x - radius * 0.9, y - radius * 0.72, x + radius * 0.92, y + radius * 0.82), 196, 340, fill=(230, 245, 255, 68), width=7)


def _moon(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, *, alpha: int = 255) -> None:
    x, y = center
    draw.ellipse((x - radius - 18, y - radius - 18, x + radius + 18, y + radius + 18), fill=(210, 220, 225, 28))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(178, 183, 187, alpha))
    for dx, dy, rr in [(-0.30, -0.18, 0.12), (0.28, -0.16, 0.09), (-0.10, 0.28, 0.08), (0.18, 0.22, 0.05)]:
        cr = int(radius * rr)
        cx = int(x + radius * dx)
        cy = int(y + radius * dy)
        draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), outline=(118, 123, 128, int(alpha * 0.65)), width=max(2, radius // 45))
    draw.pieslice((x - radius, y - radius, x + radius, y + radius), 112, 292, fill=(120, 124, 128, int(alpha * 0.20)))


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int, int], width: int = 8) -> None:
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = width * 4.5
    points = [
        end,
        (
            int(end[0] - math.cos(angle - 0.46) * size),
            int(end[1] - math.sin(angle - 0.46) * size),
        ),
        (
            int(end[0] - math.cos(angle + 0.46) * size),
            int(end[1] - math.sin(angle + 0.46) * size),
        ),
    ]
    draw.polygon(points, fill=color)


def _dashed_ellipse(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], color: tuple[int, int, int, int], width: int = 4) -> None:
    for start in range(0, 360, 18):
        draw.arc(bbox, start, start + 10, fill=color, width=width)


def _draw_recession_scale(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    _earth(draw, (475, 565), 145)
    _moon(draw, (1280, 430), 82)
    _moon(draw, (1465, 430), 82, alpha=125)
    _dashed_ellipse(draw, (205, 260, 1595, 870), (112, 211, 203, 105), width=5)
    _arrow(draw, (1345, 430), (1412, 430), (125, 219, 210, 215), width=9)
    draw.line((620, 565, 1190, 445), fill=(235, 238, 223, 95), width=4)
    for offset in [0, 80, 160]:
        draw.arc((248 + offset, 330, 1640 + offset, 850), 196, 328, fill=(250, 245, 210, 42), width=3)


def _draw_past_present(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    _earth(draw, (430, 540), 136)
    for idx, (x, radius, alpha) in enumerate([(820, 68, 105), (1110, 76, 170), (1415, 88, 255)]):
        _moon(draw, (x, 540), radius, alpha=alpha)
        draw.line((430, 540, x, 540), fill=(235, 238, 223, 40 + idx * 35), width=3 + idx)
    _arrow(draw, (865, 705), (1385, 705), (125, 219, 210, 180), width=7)
    for x in [820, 1110, 1415]:
        draw.line((x, 640, x, 735), fill=(235, 238, 223, 82), width=3)


def _draw_tidal_transfer(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    _earth(draw, (650, 560), 155)
    _moon(draw, (1340, 390), 82)
    draw.ellipse((410, 512, 890, 608), outline=(106, 201, 224, 130), width=12)
    draw.ellipse((470, 462, 830, 658), outline=(106, 201, 224, 74), width=6)
    _arrow(draw, (760, 430), (1195, 382), (244, 204, 115, 205), width=8)
    _arrow(draw, (610, 720), (710, 720), (125, 219, 210, 170), width=8)
    _dashed_ellipse(draw, (355, 270, 1540, 845), (112, 211, 203, 85), width=5)


def _draw_laser_ranging(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    _earth(draw, (370, 785), 145)
    _moon(draw, (1390, 335), 105)
    dish = [(455, 665), (555, 616), (575, 656), (485, 720)]
    draw.polygon(dish, fill=(190, 205, 210, 210))
    draw.line((525, 648, 1345, 355), fill=(114, 219, 211, 215), width=5)
    draw.line((535, 665, 1362, 380), fill=(114, 219, 211, 110), width=12)
    draw.rectangle((1360, 350, 1442, 404), outline=(236, 238, 220, 170), width=4)
    for x in range(1368, 1438, 18):
        draw.line((x, 352, x + 18, 404), fill=(236, 238, 220, 95), width=2)
    _arrow(draw, (845, 545), (975, 500), (244, 204, 115, 180), width=6)


def _draw_generic_orbital(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    _earth(draw, (610, 570), 145)
    _moon(draw, (1285, 465), 90)
    _dashed_ellipse(draw, (270, 280, 1510, 840), (112, 211, 203, 95), width=5)
    _arrow(draw, (1185, 472), (1335, 452), (125, 219, 210, 190), width=8)
    draw.line((750, 568, 1198, 478), fill=(235, 238, 223, 75), width=4)


def _draw_graphic(scene_index: int, scene_title: str) -> Image.Image:
    image = _background(scene_index + 700)
    _soft_glow(image, (1120, 170, 1660, 710), (88, 189, 206), blur=55)
    draw = ImageDraw.Draw(image, "RGBA")
    lowered = scene_title.lower()
    if scene_index == 3 or "เส้นทาง" in scene_title:
        _draw_recession_scale(draw, scene_index)
    elif scene_index == 7 or "อดีต" in scene_title:
        _draw_past_present(draw, scene_index)
    elif scene_index == 11 or "สรุป" in scene_title:
        _draw_tidal_transfer(draw, scene_index)
    elif scene_index == 13 or "laser" in lowered or "ทดลอง" in scene_title:
        _draw_laser_ranging(draw, scene_index)
    else:
        _draw_generic_orbital(draw, scene_index)
    return image


def _draw_placeholder(scene_index: int, prompt: str) -> Image.Image:
    image = _background(scene_index + 1100)
    draw = ImageDraw.Draw(image, "RGBA")
    prompt_lower = prompt.lower()
    if "thermal" in prompt_lower or "surface" in prompt_lower:
        _moon(draw, (960, 540), 245)
        draw.rectangle((0, 760, WIDTH, HEIGHT), fill=(18, 28, 32, 160))
    elif "tidal" in prompt_lower:
        _draw_tidal_transfer(draw, scene_index)
    elif "future" in prompt_lower or "trajectory" in prompt_lower:
        _earth(draw, (520, 580), 155)
        _moon(draw, (1330, 455), 95)
        _dashed_ellipse(draw, (245, 250, 1620, 870), (112, 211, 203, 120), width=5)
        _arrow(draw, (1315, 455), (1475, 405), (244, 204, 115, 200), width=8)
    else:
        _earth(draw, (620, 600), 175)
        _moon(draw, (1320, 410), 112)
        _dashed_ellipse(draw, (250, 260, 1550, 870), (112, 211, 203, 110), width=5)
    return image


def _save_png(image: Image.Image, path: Path) -> int:
    _ensure_dir(path.parent)
    image.save(path, format="PNG", optimize=True)
    return path.stat().st_size if path.exists() else 0


def render_graphic_assets(
    *,
    episode_dir: str | Path,
    asset_manifest: dict[str, Any],
    script: list[Any],
    placeholder_openers: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    scenes = [scene for scene in script if isinstance(scene, dict)]
    entries = asset_manifest.get("entries") if isinstance(asset_manifest.get("entries"), list) else []
    updated_entries: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    warnings: list[str] = list(asset_manifest.get("warnings", []) or [])

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        provider = str(entry.get("provider") or "")
        scene_index = int(entry.get("scene_index") or 0)
        scene = scenes[scene_index] if 0 <= scene_index < len(scenes) else {}
        output_path = Path(str(entry.get("local_path") or episode_path / f"scene_{scene_index:02d}_0.png")).with_suffix(".png")

        if provider == "remotion_graphic":
            if output_path.exists() and output_path.stat().st_size >= MIN_GRAPHIC_BYTES and not force:
                bytes_written = output_path.stat().st_size
                action = "skipped_existing"
            else:
                image = _draw_graphic(scene_index, _scene_title(scene, str(entry.get("scene_title") or "")))
                bytes_written = _save_png(image, output_path)
                action = "rendered"
            if bytes_written < MIN_GRAPHIC_BYTES:
                entry["status"] = "failed"
                entry["issue"] = f"rendered graphic is too small ({bytes_written} bytes)"
                warnings.append(f"scene {scene_index:02d}: graphic output too small")
            else:
                entry["status"] = "generated"
                entry["local_path"] = str(output_path)
                entry["bytes"] = bytes_written
                entry["issue"] = ""
                entry["result_source_path"] = str(output_path)
                entry["result_applied_at"] = _utc_now()
                entry["local_generation"] = {
                    "renderer": "producer_graphic_renderer",
                    "production_ready": True,
                    "text_embedded": False,
                }
            results.append(
                {
                    "scene_index": scene_index,
                    "provider": provider,
                    "status": entry.get("status"),
                    "action": action,
                    "path": str(output_path),
                    "bytes": bytes_written,
                    "production_ready": True,
                }
            )

        elif provider == "codex_imagegen" and placeholder_openers:
            placeholder_path = output_path
            if placeholder_path.exists() and placeholder_path.stat().st_size >= MIN_GRAPHIC_BYTES and not force:
                bytes_written = placeholder_path.stat().st_size
                action = "skipped_existing_placeholder"
            else:
                image = _draw_placeholder(scene_index, str(entry.get("prompt") or ""))
                bytes_written = _save_png(image, placeholder_path)
                action = "rendered_placeholder"
            entry["preflight_placeholder_path"] = str(placeholder_path)
            entry["preflight_placeholder_only"] = True
            results.append(
                {
                    "scene_index": scene_index,
                    "provider": provider,
                    "status": "placeholder",
                    "action": action,
                    "path": str(placeholder_path),
                    "bytes": bytes_written,
                    "production_ready": False,
                }
            )

        updated_entries.append(entry)

    status = "complete"
    if any(entry.get("status") == "failed" for entry in updated_entries):
        status = "blocked"
    elif any(entry.get("status") == "task_pending" for entry in updated_entries):
        status = "needs_tasks"
    elif any(entry.get("status") == "planned" for entry in updated_entries):
        status = "planned"

    generated_count = sum(1 for result in results if result.get("status") == "generated")
    placeholder_count = sum(1 for result in results if result.get("status") == "placeholder")
    failed_count = sum(1 for result in results if result.get("status") == "failed")
    report_status = "blocked" if failed_count else ("review" if placeholder_count else "pass")

    manifest = dict(asset_manifest)
    manifest["status"] = status
    manifest["updated_at"] = _utc_now()
    manifest["entries"] = updated_entries
    manifest["warnings"] = warnings
    manifest["local_graphics"] = {
        "rendered_at": _utc_now(),
        "placeholder_openers": bool(placeholder_openers),
        "generated_count": generated_count,
        "placeholder_count": placeholder_count,
    }

    return {
        "asset_manifest": manifest,
        "graphic_report": {
            "schema_version": GRAPHIC_RENDER_VERSION,
            "stage": "local_graphic_render",
            "created_at": _utc_now(),
            "status": report_status,
            "episode_dir": str(episode_path),
            "placeholder_openers": bool(placeholder_openers),
            "generated_count": generated_count,
            "placeholder_count": placeholder_count,
            "failed_count": failed_count,
            "summary": (
                f"Rendered/applied {generated_count} production graphics and "
                f"{placeholder_count} preflight-only opener placeholders."
            ),
            "warnings": warnings,
            "results": results,
        },
    }
