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

from producer_visual_policy import (
    policy_warnings,
    visual_policy_report,
)


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


def _particle(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int, color: tuple[int, int, int, int]) -> None:
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(245, 248, 250, 75), width=3)


def _draw_micrometer_scale(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    draw.line((230, 750, 1690, 750), fill=(232, 238, 240, 170), width=8)
    for x in range(260, 1691, 130):
        draw.line((x, 715, x, 785), fill=(232, 238, 240, 150), width=5)
    draw.ellipse((780, 405, 1040, 665), fill=(235, 156, 77, 205), outline=(255, 225, 185, 210), width=8)
    for x, y, r in [(835, 478, 14), (925, 535, 19), (988, 458, 11), (865, 595, 9)]:
        _particle(draw, x, y, r, (83, 105, 119, 190))
    _arrow(draw, (780, 350), (1040, 350), (112, 211, 203, 220), width=7)
    _arrow(draw, (1040, 350), (780, 350), (112, 211, 203, 220), width=7)


def _draw_condensation(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    colors = [(235, 92, 82, 210), (91, 168, 222, 210), (244, 199, 91, 210), (113, 205, 156, 210)]
    for idx in range(34):
        x = 210 + (idx * 83) % 760
        y = 260 + (idx * 137) % 510
        _particle(draw, x, y, 8 + idx % 6, colors[idx % len(colors)])
    _arrow(draw, (980, 525), (1240, 525), (232, 238, 240, 170), width=8)
    for cx, cy, mix in [(1390, 370, (0, 1)), (1530, 560, (1, 3)), (1325, 700, (0, 2))]:
        draw.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=(218, 225, 226, 35), outline=(218, 225, 226, 135), width=5)
        for j in range(12):
            angle = j * math.tau / 12
            _particle(draw, int(cx + math.cos(angle) * 52), int(cy + math.sin(angle) * 52), 13, colors[mix[j % 2]])


def _draw_cooling_timeline(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    draw.line((250, 690, 1660, 690), fill=(228, 235, 238, 155), width=7)
    _arrow(draw, (250, 690), (1660, 690), (228, 235, 238, 155), width=7)
    for idx, (x, radius, color) in enumerate([(330, 180, (255, 128, 47, 230)), (760, 140, (243, 178, 73, 220)), (1160, 105, (140, 188, 205, 215)), (1510, 72, (93, 132, 161, 210))]):
        _soft_glow(draw._image, (x - radius - 45, 340 - radius - 45, x + radius + 45, 340 + radius + 45), color[:3], blur=35)
        draw.ellipse((x - radius, 340 - radius, x + radius, 340 + radius), fill=color)
        draw.line((x, 675, x, 720), fill=(228, 235, 238, 120), width=4)


def _draw_quench(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    draw.line((960, 210, 960, 870), fill=(232, 238, 240, 80), width=5)
    palette = [(239, 105, 91, 230), (91, 173, 224, 230), (242, 196, 81, 230)]
    for row in range(5):
        for col in range(5):
            _particle(draw, 330 + col * 105, 310 + row * 105, 24, palette[(row + col) % 3])
    rng = random.Random(scene_index + 802)
    for idx in range(25):
        _particle(draw, 1130 + rng.randrange(0, 520), 280 + rng.randrange(0, 520), 18 + idx % 8, palette[idx % 3])
    _arrow(draw, (540, 220), (540, 310), (244, 199, 91, 210), width=8)
    _arrow(draw, (1400, 220), (1400, 310), (112, 211, 203, 220), width=14)


def _draw_composition(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    values = [315, 245, 170, 128, 92, 55, 34]
    colors = [(224, 94, 82, 220), (235, 151, 66, 220), (239, 199, 91, 220), (110, 194, 149, 220), (84, 161, 214, 220), (139, 119, 201, 220), (194, 118, 169, 220)]
    baseline = 835
    for idx, value in enumerate(values):
        x0 = 300 + idx * 190
        draw.rounded_rectangle((x0, baseline - value, x0 + 105, baseline), radius=18, fill=colors[idx])
    draw.line((235, baseline, 1690, baseline), fill=(235, 239, 240, 145), width=6)


def _draw_hea_boundary(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    colors = [(224, 94, 82, 230), (235, 151, 66, 230), (239, 199, 91, 230), (110, 194, 149, 230), (84, 161, 214, 230)]
    for side, cx in [(0, 560), (1, 1360)]:
        for row in range(5):
            for col in range(5):
                if side == 0:
                    color = colors[(row * 5 + col) % len(colors)]
                else:
                    color = colors[0] if row * 5 + col < 14 else colors[(row + col) % len(colors)]
                _particle(draw, cx - 180 + col * 90, 355 + row * 90, 31, color)
    draw.line((960, 245, 960, 825), fill=(235, 239, 240, 75), width=5)


def _draw_blast_geometry(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    ground_y = 790
    draw.line((160, ground_y, 1760, ground_y), fill=(212, 218, 220, 160), width=8)
    draw.line((960, 235, 960, 885), fill=(235, 239, 240, 70), width=4)
    _soft_glow(draw._image, (350, 560, 690, 900), (239, 111, 61), blur=50)
    draw.ellipse((445, 655, 595, 805), fill=(242, 133, 63, 225))
    _soft_glow(draw._image, (1180, 210, 1580, 610), (239, 111, 61), blur=55)
    draw.ellipse((1300, 330, 1460, 490), fill=(242, 133, 63, 225))
    for cx, cy in [(520, 730), (1380, 410)]:
        for radius in (110, 180, 255):
            draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), 190, 350, fill=(244, 199, 91, max(45, 175 - radius // 2)), width=6)


def _draw_sleep_continuity(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Show sleep as a continuous biological process, not a death metaphor."""
    draw.ellipse((250, 360, 690, 650), outline=(160, 205, 216, 150), width=8)
    draw.arc((300, 410, 640, 600), 205, 335, fill=(236, 238, 220, 220), width=10)
    draw.arc((330, 430, 610, 590), 25, 155, fill=(120, 219, 210, 100), width=5)
    draw.ellipse((470, 500, 500, 530), fill=(236, 238, 220, 180))
    points = [(820, 560), (910, 560), (960, 510), (1010, 610), (1060, 535), (1115, 560), (1230, 560)]
    draw.line(points, fill=(125, 219, 210, 215), width=8, joint="curve")
    _arrow(draw, (1185, 560), (1325, 560), (244, 204, 115, 205), width=7)
    draw.ellipse((1390, 400, 1640, 650), fill=(244, 219, 153, 28), outline=(244, 219, 153, 145), width=6)
    draw.arc((1430, 440, 1600, 610), 205, 335, fill=(236, 238, 220, 190), width=8)


def _draw_sleep_cycle(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Use a clean ring to explain recurring sleep stages without slide-like text."""
    center = (960, 545)
    rings = [260, 205, 150]
    colors = [(78, 151, 204, 190), (111, 211, 203, 190), (244, 204, 115, 180)]
    for radius, color in zip(rings, colors):
        draw.ellipse(
            (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
            outline=color,
            width=12,
        )
    for start, color in zip([205, 305, 35, 125], [(78, 151, 204, 220), (111, 211, 203, 220), (244, 204, 115, 210), (155, 170, 185, 180)]):
        draw.arc((700, 285, 1220, 805), start, start + 62, fill=color, width=30)
    draw.ellipse((895, 480, 1025, 610), fill=(236, 238, 220, 36), outline=(236, 238, 220, 155), width=5)
    draw.line((960, 545, 1200, 545), fill=(236, 238, 220, 90), width=4)
    draw.ellipse((1185, 530, 1215, 560), fill=(125, 219, 210, 220))


def _draw_tno_planetesimal(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Show outer-disk material stopping at the planetesimal stage."""
    ice = [(90, 180, 208, 205), (121, 215, 207, 205), (235, 204, 126, 190), (170, 143, 215, 180)]
    _soft_glow(draw._image, (190, 315, 560, 685), (75, 160, 190), blur=55)
    draw.ellipse((295, 430, 455, 590), fill=(228, 238, 236, 215), outline=(120, 215, 210, 180), width=7)
    for particle in range(40):
        x = 165 + (particle * 79 + scene_index * 23) % 450
        y = 300 + (particle * 113 + scene_index * 17) % 370
        _particle(draw, x, y, 7 + particle % 6, ice[particle % len(ice)])
    _arrow(draw, (585, 510), (805, 510), (127, 219, 210, 205), width=9)

    _soft_glow(draw._image, (760, 310, 1180, 730), (75, 160, 190), blur=60)
    draw.ellipse((840, 395, 1080, 635), fill=(163, 195, 201, 180), outline=(226, 239, 232, 205), width=8)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        cx = int(960 + math.cos(rad) * 116)
        cy = int(515 + math.sin(rad) * 116)
        _particle(draw, cx, cy, 17, ice[(angle // 45) % len(ice)])
    draw.arc((760, 245, 1160, 785), 195, 345, fill=(105, 210, 210, 120), width=5)

    _arrow(draw, (1195, 510), (1390, 510), (127, 219, 210, 205), width=9)
    _soft_glow(draw._image, (1320, 300, 1700, 700), (75, 160, 190), blur=55)
    draw.ellipse((1430, 410, 1600, 580), fill=(137, 177, 191, 195), outline=(225, 240, 238, 210), width=7)
    draw.ellipse((1590, 480, 1665, 555), fill=(184, 207, 205, 185), outline=(225, 240, 238, 160), width=5)
    for cx, cy, radius, color in [
        (1470, 455, 13, ice[0]),
        (1530, 525, 15, ice[1]),
        (1495, 555, 10, ice[2]),
        (1622, 508, 8, ice[3]),
    ]:
        _particle(draw, cx, cy, radius, color)
    _dashed_ellipse(draw, (1260, 255, 1750, 735), (105, 204, 213, 90), width=4)


def _draw_tno_shift_stack(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Show a moving faint point becoming visible after alignment."""
    panel_boxes = [(95, 190, 595, 570), (715, 190, 1215, 570), (1335, 190, 1825, 570)]
    for frame, box in enumerate(panel_boxes):
        draw.rounded_rectangle(box, radius=22, outline=(154, 194, 209, 115), width=5, fill=(5, 13, 22, 95))
        rng = random.Random(1400 + scene_index * 17 + frame)
        for _ in range(18):
            x = rng.randint(box[0] + 35, box[2] - 35)
            y = rng.randint(box[1] + 35, box[3] - 35)
            radius = 2 if rng.random() > 0.2 else 3
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(212, 231, 244, 130))
        point_x = box[0] + 190 + frame * 72
        point_y = box[1] + 290 - frame * 42
        _soft_glow(draw._image, (point_x - 38, point_y - 38, point_x + 38, point_y + 38), (79, 205, 217), blur=26)
        draw.ellipse((point_x - 8, point_y - 8, point_x + 8, point_y + 8), fill=(126, 231, 224, 245))
    for start, end in [((345, 605), (345, 660)), ((965, 605), (965, 660)), ((1580, 605), (1580, 660))]:
        _arrow(draw, start, end, (127, 219, 210, 165), width=7)

    result_box = (385, 700, 1535, 965)
    draw.rounded_rectangle(result_box, radius=24, outline=(154, 194, 209, 145), width=6, fill=(5, 13, 22, 120))
    rng = random.Random(1700 + scene_index)
    for _ in range(25):
        x = rng.randint(result_box[0] + 40, result_box[2] - 40)
        y = rng.randint(result_box[1] + 35, result_box[3] - 35)
        radius = 2 if rng.random() > 0.25 else 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(150, 177, 196, 85))
    point_x, point_y = 960, 830
    _soft_glow(draw._image, (point_x - 95, point_y - 95, point_x + 95, point_y + 95), (75, 210, 220), blur=45)
    for offset in (-38, -19, 0, 19, 38):
        draw.ellipse((point_x + offset - 9, point_y - 9, point_x + offset + 9, point_y + 9), fill=(127, 232, 224, 150))
    draw.ellipse((point_x - 15, point_y - 15, point_x + 15, point_y + 15), outline=(235, 247, 238, 220), width=5)


def _draw_tno_color_size(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Show small and large objects following the same color families."""
    palette = [(82, 168, 224, 220), (242, 194, 92, 220), (224, 103, 104, 220)]
    draw.line((220, 855, 1700, 855), fill=(226, 237, 238, 150), width=5)
    draw.line((250, 230, 250, 855), fill=(226, 237, 238, 120), width=5)
    for family, color in enumerate(palette):
        points = []
        for idx in range(8):
            x = 330 + idx * 175
            y = 430 + family * 130 + int(math.sin(idx * 0.9 + family) * 25)
            points.append((x, y))
            radius = 11 + idx * 4
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=(240, 245, 242, 160), width=3)
        draw.line(points, fill=(*color[:3], 95), width=5, joint="curve")
    for idx in range(12):
        x = 305 + idx * 112
        y = 920
        draw.line((x, y - 13, x, y + 13), fill=(226, 237, 238, 105), width=3)
    _arrow(draw, (305, 930), (1675, 930), (127, 219, 210, 125), width=6)
    _soft_glow(draw._image, (260, 340, 650, 760), (86, 179, 220), blur=45)


def _draw_tno_collision_hypotheses(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    """Visualize the two live explanations without declaring either proven."""
    divider = 960
    draw.line((divider, 210, divider, 900), fill=(229, 237, 235, 100), width=5)
    icy = (146, 190, 203, 210)
    blue = (87, 184, 220, 220)
    orange = (239, 172, 91, 220)
    red = (220, 101, 100, 210)
    for center_x in (510, 1410):
        _soft_glow(draw._image, (center_x - 190, 320, center_x + 190, 700), (75, 171, 196), blur=48)
    draw.ellipse((365, 395, 655, 685), fill=icy, outline=(226, 242, 237, 200), width=8)
    for cx, cy, color in [(455, 470, blue), (535, 505, orange), (500, 590, red), (585, 610, blue), (420, 595, orange)]:
        _particle(draw, cx, cy, 17, color)
    draw.arc((230, 300, 790, 790), 205, 325, fill=(118, 211, 213, 100), width=6)

    draw.ellipse((1265, 395, 1555, 685), fill=icy, outline=(226, 242, 237, 200), width=8)
    for cx, cy, color in [(1355, 470, blue), (1435, 505, orange), (1400, 590, red), (1485, 610, blue), (1320, 595, orange)]:
        _particle(draw, cx, cy, 17, color)
    draw.ellipse((1125, 315, 1245, 435), fill=(174, 203, 205, 170), outline=(226, 242, 237, 165), width=5)
    _arrow(draw, (1210, 380), (1290, 440), (239, 172, 91, 185), width=7)
    for angle in range(0, 360, 60):
        rad = math.radians(angle)
        cx = int(1410 + math.cos(rad) * 250)
        cy = int(540 + math.sin(rad) * 250)
        draw.line((1410 + int(math.cos(rad) * 170), 540 + int(math.sin(rad) * 170), cx, cy), fill=(239, 172, 91, 120), width=4)
        draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(239, 172, 91, 185))
    draw.arc((1190, 255, 1630, 825), 215, 325, fill=(118, 211, 213, 100), width=6)


def _draw_graphic(
    scene_index: int,
    scene_title: str,
    prompt: str = "",
    scene_context: str = "",
) -> Image.Image:
    image = _background(scene_index + 700)
    _soft_glow(image, (1120, 170, 1660, 710), (88, 189, 206), blur=55)
    draw = ImageDraw.Draw(image, "RGBA")
    lowered = f"{scene_title} {prompt} {scene_context}".lower()
    tno_context = any(
        marker in lowered
        for marker in (
            "trans-neptunian",
            "tno",
            "kuiper belt",
            "planetesimal",
            "shift-and-stack",
            "cold classical",
            "color-size",
            "collision",
        )
    )
    if tno_context and scene_index == 4:
        _draw_tno_planetesimal(draw, scene_index)
    elif tno_context and scene_index == 7:
        _draw_tno_shift_stack(draw, scene_index)
    elif tno_context and scene_index == 14:
        _draw_tno_color_size(draw, scene_index)
    elif tno_context and scene_index == 17:
        _draw_tno_collision_hypotheses(draw, scene_index)
    elif "graphic:micrometer_scale" in lowered:
        _draw_micrometer_scale(draw, scene_index)
        _draw_micrometer_scale(draw, scene_index)
    elif "graphic:multicomponent_condensation" in lowered:
        _draw_condensation(draw, scene_index)
    elif "graphic:cooling_timeline" in lowered:
        _draw_cooling_timeline(draw, scene_index)
    elif "graphic:rapid_quench" in lowered:
        _draw_quench(draw, scene_index)
    elif "graphic:composition_bars" in lowered:
        _draw_composition(draw, scene_index)
    elif "graphic:hea_boundary" in lowered:
        _draw_hea_boundary(draw, scene_index)
    elif "graphic:blast_geometry" in lowered:
        _draw_blast_geometry(draw, scene_index)
    elif scene_index == 2 or "นอนไม่ใช่ความตาย" in scene_title:
        _draw_sleep_continuity(draw, scene_index)
    elif scene_index == 3 or "ความมืดไม่ได้ว่างเปล่า" in scene_title:
        _draw_sleep_cycle(draw, scene_index)
    elif "เส้นทาง" in scene_title:
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
                image = _draw_graphic(
                    scene_index,
                    _scene_title(scene, str(entry.get("scene_title") or "")),
                    str(entry.get("prompt") or ""),
                    str(scene.get("narration") or ""),
                )
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
    policy_report = visual_policy_report(updated_entries)
    warnings.extend(policy_warnings(policy_report))
    if policy_report.get("status") == "blocked":
        status = "blocked"

    generated_count = sum(1 for result in results if result.get("status") == "generated")
    placeholder_count = sum(1 for result in results if result.get("status") == "placeholder")
    failed_count = sum(1 for result in results if result.get("status") == "failed")
    report_status = "blocked" if failed_count else ("review" if placeholder_count else "pass")

    manifest = dict(asset_manifest)
    manifest["status"] = status
    manifest["updated_at"] = _utc_now()
    manifest["entries"] = updated_entries
    manifest["warnings"] = warnings
    manifest["visual_policy"] = policy_report
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
