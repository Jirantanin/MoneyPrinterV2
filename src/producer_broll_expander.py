"""B-roll timeline expansion for PodcastV2 Producer Mode.

This stage fixes the pacing problem where a long scene gets only one visual
asset. It expands each scene into 5-8 second visual slots and creates local
reframed stills from the existing verified/generated source assets.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from producer_visual_policy import (
    can_add_visual_entry,
    policy_review_warnings,
    policy_warnings,
    visual_policy_report,
)


BROLL_TIMELINE_VERSION = 1
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
LOCAL_REFRAME_PROVIDER = "local_reframe"
LOCAL_GRAPHIC_PROVIDER = "local_graphic_broll"
RUNWARE_BROLL_PROVIDER = "runware_flux1"
FRESH_OFFICIAL_ROLE = "fresh_official_broll"
STOCK_VIDEO_ROLE = "stock_video_broll"
GENERATED_IMAGE_ROLE = "generated_image_broll"
FRESH_OFFICIAL_MAX_BYTES = 25 * 1024 * 1024
MAX_FRESH_OFFICIAL_PER_SCENE = 2
MAX_FRESH_OFFICIAL_PER_SECTION = 5
VOYAGER_MAX_FRESH_OFFICIAL_PER_SCENE = 8
VOYAGER_MAX_FRESH_OFFICIAL_PER_SECTION = 16
DOWNLOAD_TIMEOUT = (10, 60)
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False

OFFICIAL_RELEVANCE_MARKERS = {
    "moon",
    "lunar",
    "apollo",
    "artemis",
    "lro",
    "lroc",
    "selene",
    "clementine",
    "grail",
    "sofia",
    "earth-moon",
    "earth moon",
    "tide",
    "tides",
    "tidal",
    "ocean tides",
    "retroreflector",
    "laser ranging",
    "crater",
    "craters",
}
OFFICIAL_BLOCKED_MARKERS = {
    "budget request",
    "this week @nasa",
    "festival",
    "wapakoneta",
    "commemorative",
    "moon to mars",
    "psyche",
    "mars",
    "martian",
    "jupiter",
    "saturn",
    "plant experiment",
    "iss",
    "international space station",
    "space station",
    "exoplanet",
}

VOYAGER_OFFICIAL_RELEVANCE_MARKERS = {
    "voyager",
    "golden record",
    "pale blue dot",
    "interstellar mission",
    "titan-centaur",
    "titan centaur",
    "carl sagan",
    "ann druyan",
}
VOYAGER_OFFICIAL_BLOCKED_MARKERS = {
    "budget request",
    "this week @nasa",
    "festival",
    "commemorative",
    "artemis",
    "apollo program",
    "mars perseverance",
    "mars curiosity",
    "international space station",
    "space station",
    "psyche mission",
}
VOYAGER_OFFICIAL_QUERIES = (
    "Voyager 1 interstellar space",
    "Voyager 1 spacecraft",
    "Voyager 2 spacecraft",
    "Voyager mission control",
    "Voyager Deep Space Network",
    "Voyager Golden Record",
    "Voyager launch 1977 Titan Centaur",
    "Voyager Jupiter encounter",
    "Voyager Saturn encounter",
    "Voyager Uranus encounter",
    "Voyager Neptune encounter",
    "Voyager Golden Record preparation",
    "Voyager Golden Record cover",
    "Voyager Pale Blue Dot",
    "Voyager trajectory",
    "Voyager Carter message",
)
VOYAGER_OFFICIAL_QUERY_HINTS_BY_ASSET_ID = {
    "VGR-01": ("interstellar", "mission control", "deep space network", "golden record"),
    "VGR-02": ("golden record", "spacecraft", "interstellar"),
    "VGR-03": ("launch 1977", "jupiter encounter", "saturn encounter", "uranus encounter", "neptune encounter"),
    "VGR-04": ("golden record preparation", "golden record"),
    "VGR-05": ("golden record",),
    "VGR-06": ("golden record", "pale blue dot"),
    "VGR-07": ("golden record preparation", "golden record cover", "golden record"),
    "VGR-08": ("golden record cover", "golden record"),
    "VGR-09": ("golden record cover", "golden record"),
    "VGR-10": ("trajectory", "interstellar", "spacecraft"),
    "VGR-11": ("carter message", "golden record"),
    "VGR-12": ("interstellar", "mission control", "deep space network", "pale blue dot", "spacecraft"),
}
DENISOVAN_OFFICIAL_RELEVANCE_MARKERS = {
    "denisovan",
    "denisova cave",
    "penghu",
    "baishiya",
    "xiahe",
    "archaic hominin",
    "ancient protein",
    "paleoproteomic",
    "paleoprotein",
}
DENISOVAN_OFFICIAL_BLOCKED_MARKERS = {
    "mars",
    "moon",
    "lunar",
    "apollo",
    "artemis",
    "international space station",
    "space station",
}
DENISOVAN_OFFICIAL_QUERIES = (
    "Denisova Cave archaeological excavation",
    "Denisovan ancient protein research",
    "Penghu Taiwan archaeology fossil",
    "Baishiya Karst Cave archaeology",
    "Tibetan Plateau archaeological cave",
)
VOYAGER_STOCK_KEYWORDS_BY_ASSET_ID = {
    "VGR-01": ["deep space star field", "space mission control", "radio telescope control room", "deep space antenna", "satellite signal screen", "space probe silhouette", "gold record disc", "earth horizon space", "vintage rocket launch"],
    "VGR-02": ["small satellite stars", "record player close up", "radio telescope night", "deep space stars", "space antenna", "space probe animation", "vinyl record macro", "earth from space", "night sky telescope"],
    "VGR-03": ["rocket launch night", "spacecraft engineering", "solar system planets", "jupiter planet", "saturn planet", "uranus planet", "neptune planet", "space mission control", "rocket preparation", "space probe animation"],
    "VGR-04": ["vinyl record archive", "1970s typewriter", "research team archive", "team selecting photos", "photo contact sheet", "old documents table", "record pressing", "world map table", "people discussion table", "archive filing cabinet"],
    "VGR-05": ["ocean waves", "wind through trees", "thunderstorm clouds", "birds flying", "whale underwater", "heartbeat monitor", "train moving landscape", "diverse children", "people greeting camera", "world culture people"],
    "VGR-06": ["diverse people portraits", "earth from space", "family together", "people working", "world map close up", "people looking at stars", "crowd city", "ocean earth", "mountain landscape", "team selecting photos"],
    "VGR-07": ["vinyl record macro", "record player stylus", "metal workshop hands", "copper sheet metal", "record pressing", "engraving metal hands", "audio record grooves", "laboratory metal work", "aluminum sheet", "gold vinyl record"],
    "VGR-08": ["record player stylus", "vinyl record groove", "hydrogen atom animation", "audio waveform screen", "calibration circle", "binary code close up", "scientific diagram hand", "record needle macro"],
    "VGR-09": ["radio telescope stars", "observatory night sky", "pulsar astronomy", "star map astronomy", "radio telescope night", "deep space star field", "atomic clock laboratory", "scientist astronomy screen", "solar system stars"],
    "VGR-10": ["deep space stars", "star field timelapse", "radio telescope night", "tiny satellite space", "ocean bottle message", "calendar pages time", "earth horizon space", "night sky long exposure", "space probe animation"],
    "VGR-11": ["1970s typewriter letter", "paper document close up", "earth horizon space", "hands writing letter", "vintage office desk", "peaceful crowd 1970s", "planet earth space", "old paper archive"],
    "VGR-12": ["earth from deep space", "stars deep space", "people looking at night sky", "ocean waves sunrise", "weather clouds timelapse", "diverse people portraits", "children playing earth", "radio telescope night", "space mission control", "blue planet darkness", "city people life", "night sky stars"],
}
VOYAGER_RUNWARE_PROMPTS_BY_ASSET_ID = {
    "VGR-01": "A faint radio signal dissolving into deep interstellar darkness, symbolic documentary illustration, no identifiable spacecraft, no real people.",
    "VGR-02": "A tiny anonymous human-made probe silhouette crossing a vast dark star field, symbolic scale image, no alien beings, no readable markings.",
    "VGR-03": "A restrained solar-system journey illustration with distant giant planets and a small unlabeled probe path, no mission logos, not presented as archival footage.",
    "VGR-04": "An archival-style tabletop with an unlabeled blank vinyl record, photographic contact sheets, and selection notes with no readable text, no identifiable historical people.",
    "VGR-05": "A poetic but realistic natural-sound tableau of ocean surf, a whale beneath water, wind through leaves, and distant rail motion, no text, no fantasy creatures.",
    "VGR-06": "Anonymous diverse human silhouettes reflected in a view of Earth, symbolic representation and self-portrait theme, no identifiable real people.",
    "VGR-07": "Extreme macro photograph of a gold-plated copper disc and record grooves under restrained laboratory light, no label, no readable engraving.",
    "VGR-08": "Macro view of abstract etched playback symbols and a record groove, clearly illustrative, no readable language, no invented NASA markings.",
    "VGR-09": "A clean scientific illustration of radial pulsar beams around a central point in deep space, no labels, no decorative clutter.",
    "VGR-10": "A solitary sealed bottle-like object drifting through an immense dark cosmic ocean, visual metaphor only, no aliens, no destination planet.",
    "VGR-11": "An unsigned paper letter beside the blue glow of Earth seen from darkness, no readable text, no portrait of any president.",
    "VGR-12": "A single tiny blue point suspended in immense black space, symbolic closing image, restrained and contemplative, no added spacecraft or text.",
}

NO_FIRE_MARKERS = (
    "homo raw",
    "wonderwerk",
    "\u0e01\u0e2d\u0e07\u0e44\u0e1f",
    "\u0e21\u0e32\u0e21\u0e48\u0e32",
    "\u0e2b\u0e21\u0e39\u0e01\u0e23\u0e30\u0e17\u0e30",
)

NO_FIRE_STOCK_KEYWORDS_BY_ASSET_ID = {
    "S01B02": ["dark city night", "abandoned shopping mall", "empty factory interior"],
    "S04B02": ["stone tools hands", "flint knapping", "primitive stone tools"],
    "S05B01": ["nomadic people forest", "temporary shelter forest", "tropical river crossing"],
    "S05B03": ["woven baskets forest", "temporary shelter forest", "foraging forest"],
}

NO_FIRE_LOCAL_ONLY_ASSET_IDS = {
    "S02B03",
    "S03B01",
    "S03B02",
    "S06B01",
}

NO_FIRE_RUNWARE_PROMPTS_BY_ASSET_ID = {
    "S01B01": "Bangkok in 2026 reclaimed by tropical forest, no electricity, no neon, small human hunters with stone spears moving through wet streets, documentary realism, cinematic wide shot.",
    "S01B02": "A dark modern room after technology never happened: unlit glass, silent metal frame, raw materials replacing devices, no readable brand, documentary symbolic still.",
    "S01B03": "Archaeological cave floor with ash-colored sediment layers and stone fragments, evidence-focused documentary still, no modern labels, restrained lighting.",
    "S02B01": "Hands gathering raw wild fruit, roots, leaves, and insects in a tropical forest, no cooking, no fire, realistic survival documentary close shot.",
    "S02B02": "Human body energy comparison without text: stomach, jaw, and brain represented by subtle anatomical silhouettes and warm energy paths, clean documentary infographic still.",
    "S02B03": "Counterfactual human evolutionary reconstruction in a tropical forest: upright human-like hominin, human face, strong jaw, rugged body, no fur, not an ape, not a chimpanzee, not a monkey, museum-quality documentary realism.",
    "S03B01": "Pitch-black tropical forest after sunset, hidden human silhouettes under branches, distant predator eyes, cold blue-green darkness, no orange glow, no flame, no smoke, tense documentary atmosphere.",
    "S03B02": "Small human band sleeping apart under branches at night, empty unlit center, cold darkness, quiet fear, no orange glow, no flame, no smoke, realistic prehistoric survival scene.",
    "S03B03": "Frozen northern landscape empty of people, wind over tundra and dark tree line, showing where humans struggle without portable heat, documentary realism.",
    "S04B01": "Technology domino chain without fire: unbaked clay, stone tool, copper ore, glass shard, and dark electric bulb as a clean no-text explanatory graphic.",
    "S04B02": "Close-up of hands shaping stone and bone tools beside wood fibers, no metal, no fire, tactile documentary realism.",
    "S04B03": "Bangkok market transformed into a forest camp with stone tools, woven baskets, no metal, no plastic, no cooked food, documentary counterfactual realism.",
    "S05B01": "Small nomadic human band moving through tropical forest with simple shelters and woven baskets, no permanent city, documentary wide shot.",
    "S05B02": "No-text population scale visualization: dark world map silhouette with sparse human dots near the equator and empty cold regions, clean documentary graphic.",
    "S05B03": "Temporary shelter near a river with woven baskets, raw stored food, gourds and bark containers, no pottery, no smoke, documentary realism.",
    "S06B01": "Empty dark clearing with an unlit cold center, people separated in shadows instead of gathering together, no orange glow, no flame, no smoke, restrained cinematic documentary still.",
    "S06B02": "Three vanished modern comforts shown symbolically without brands: blank instant noodles cup, black smartphone glass, cold unlit grill, clean no-text comparison graphic.",
    "S06B03": "A single controlled flame transforming into rocket exhaust and abstract AI light, symbolic documentary image, no text, not fantasy clutter.",
}

NO_FIRE_THEMES_BY_ASSET_ID = {
    "S01B01": "city",
    "S01B02": "modern",
    "S01B03": "evidence",
    "S02B01": "food",
    "S02B02": "energy",
    "S02B03": "body",
    "S03B01": "night",
    "S03B02": "shelter_night",
    "S03B03": "cold",
    "S04B01": "tech",
    "S04B02": "tools",
    "S04B03": "city",
    "S05B01": "settlement",
    "S05B02": "population",
    "S05B03": "storage",
    "S06B01": "culture",
    "S06B02": "vanished",
    "S06B03": "future",
}

VOLCANO_MARKERS = (
    "volcano",
    "volcanic",
    "mayon",
    "villarrica",
    "sakurajima",
    "rainier",
    "popocatepetl",
    "mount fuji",
    "merapi",
    "\u0e20\u0e39\u0e40\u0e02\u0e32\u0e44\u0e1f",
    "\u0e40\u0e21\u0e22\u0e2d\u0e19",
    "\u0e27\u0e34\u0e25\u0e25\u0e32\u0e23\u0e4c\u0e23\u0e34\u0e01\u0e32",
    "\u0e0b\u0e32\u0e01\u0e38\u0e23\u0e30\u0e08\u0e34\u0e21\u0e30",
    "\u0e40\u0e23\u0e19\u0e40\u0e19\u0e35\u0e22\u0e23\u0e4c",
    "\u0e42\u0e1b\u0e42\u0e1b\u0e01\u0e32\u0e40\u0e15\u0e40\u0e1b\u0e15\u0e25\u0e4c",
    "\u0e1f\u0e39\u0e08\u0e34",
    "\u0e40\u0e21\u0e23\u0e32\u0e1b\u0e35",
)

VOLCANO_STOCK_KEYWORDS_BY_ASSET_ID = {
    "S01B01": ["Mayon volcano Philippines", "Philippines volcano evacuation", "volcano monitoring Philippines"],
    "S02B01": ["Villarrica volcano Chile", "Pucon Chile volcano", "snow volcano Chile"],
    "S03B01": ["Sakurajima volcano Japan", "Kagoshima volcano ash", "Japan volcano eruption"],
    "S04B01": ["Mount Rainier Washington", "volcano evacuation drill", "mudflow river valley"],
    "S05B01": ["Popocatepetl volcano Mexico", "volcanic ash Mexico", "Mexico City airport runway"],
    "S06B01": ["Mount Fuji Japan", "Tokyo train station", "volcanic ash city"],
    "S07B01": ["Merapi volcano Indonesia", "volcano evacuation Indonesia", "pyroclastic flow volcano"],
    "S07B02": ["volcano observatory monitoring", "volcano evacuation drill", "seismograph monitoring"],
}

VOLCANO_RUNWARE_PROMPTS_BY_ASSET_ID = {
    "S01B01": "Mayon Volcano in the Philippines above nearby communities, steep symmetrical cone with an active ash plume, real-world documentary reconstruction, no exaggerated disaster.",
    "S02B01": "Villarrica Volcano in Chile above Pucon, snow and glacier on the cone with a restrained lava glow at the crater, realistic geography, documentary reconstruction.",
    "S03B01": "Sakurajima Volcano across the bay from Kagoshima, Japan, a modest ash plume near a lived-in city, grounded news-documentary reconstruction.",
    "S04B01": "Mount Rainier in Washington with glacier-covered slopes and populated river valleys below, emphasizing realistic lahar exposure, documentary reconstruction.",
    "S05B01": "Popocatepetl Volcano in Mexico with a gray ash plume and dense settlements in the wider region, grounded scale, documentary reconstruction.",
    "S06B01": "Mount Fuji above the Tokyo region as a calm hazard-planning scene, subtle volcanic ash affecting transport infrastructure, not an imminent apocalypse, documentary reconstruction.",
    "S07B01": "Mount Merapi in Indonesia with a collapsing lava dome and a ground-hugging pyroclastic flow kept distant from a village, realistic volcanology, documentary reconstruction.",
    "S07B02": "A modern volcano observatory combining seismic monitoring, hazard maps, and an organized evacuation drill, realistic public-safety documentary scene.",
}

HIROSHIMA_STOCK_KEYWORDS_BY_SECTION = {
    "S01": [
        "scientist microscope laboratory", "materials science laboratory", "research paper close up",
        "microscope metal sample", "x ray laboratory equipment", "scientist analyzing sample",
        "laboratory glass slide macro", "metal particle macro", "forensic science laboratory",
        "researcher writing notes laboratory",
    ],
    "S02": [
        "beach sand macro", "coastal sand grains", "mineral microscope laboratory",
        "scientist sorting mineral samples", "mass spectrometer laboratory", "laboratory sample tray",
        "glass fragments macro", "coastal field research", "isotope laboratory equipment",
        "sand sample microscope",
    ],
    "S03": [
        "molten metal foundry", "metal casting sparks", "industrial smoke particles",
        "hot metal cooling", "foundry furnace close up", "metal droplets slow motion",
        "industrial vapor steam", "molten glass workshop", "scanning electron microscope",
        "laboratory thermal experiment",
    ],
    "S04": [
        "electron microscope laboratory", "scientist analyzing microscope image", "x ray crystallography laboratory",
        "microprobe laboratory", "metal sample tweezers", "laboratory monitor microscopy",
        "scientist measuring tiny sample", "materials characterization laboratory", "crystal sample microscope",
        "laboratory instrument close up",
    ],
    "S05": [
        "crystal materials laboratory", "metal tensile testing", "scientist reviewing research paper",
        "microscopic crystal close up", "materials scientist laboratory", "metal alloy sample macro",
        "laboratory data analysis", "scientist peer review desk", "crystal growth laboratory",
        "precision metal testing",
    ],
    "S06": [
        "desert storm clouds", "lightning over landscape", "molten glass cooling",
        "desert sand glass", "archive conservation gloves", "historical artifact archive",
        "memorial flowers", "museum object conservation", "storm lightning slow motion",
        "glass sample laboratory",
    ],
    "S07": [
        "forensic microscope laboratory", "evidence sample laboratory", "scientist examining particles",
        "3d printer machine", "metal additive manufacturing", "museum archive conservation",
        "laboratory sample catalog", "peace memorial flowers", "scientist documenting evidence",
        "microscope slide forensic",
    ],
}

RUNWARE_CAMERA_VARIANTS = (
    "wide establishing frame",
    "medium observational frame",
    "low angle detail frame",
    "overhead composition",
    "close documentary insert",
    "slow-cinema atmospheric frame",
)


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    return HTTP_SESSION.get(url, **kwargs)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _scene_asset_id(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> str:
    for container in (scene, source):
        if not isinstance(container, dict):
            continue
        for key in ("producer_asset_plan_id", "asset_plan_id"):
            value = str(container.get(key) or "").strip().upper()
            match = re.match(r"^((?:S\d+B\d+)|(?:VGR-\d+))", value)
            if match:
                return match.group(1)
    return ""


def _scene_context_text(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> str:
    parts: list[str] = []
    for container in (scene, source):
        if not isinstance(container, dict):
            continue
        for key in ("section_title", "scene_title", "narration", "prompt", "keyword"):
            parts.append(_clean_text(container.get(key)))
    return " ".join(part for part in parts if part).lower()


def _is_no_fire_scene(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> bool:
    text = _scene_context_text(scene, source)
    return any(marker in text for marker in NO_FIRE_MARKERS)


def _is_volcano_scene(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> bool:
    text = _scene_context_text(scene, source)
    return any(marker in text for marker in VOLCANO_MARKERS)


def _no_fire_theme(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> str:
    asset_id = _scene_asset_id(scene, source)
    if asset_id in NO_FIRE_THEMES_BY_ASSET_ID:
        return NO_FIRE_THEMES_BY_ASSET_ID[asset_id]
    text = _scene_context_text(scene, source)
    if "homo raw" in text:
        return "body"
    if "wonderwerk" in text:
        return "evidence"
    return "night" if _is_no_fire_scene(scene, source) else "abstract"


def _allow_runware_for_scene(scene: dict[str, Any] | None, source: dict[str, Any] | None = None) -> bool:
    return _scene_asset_id(scene, source) not in NO_FIRE_LOCAL_ONLY_ASSET_IDS


def _runware_broll_prompt(
    scene: dict[str, Any],
    source: dict[str, Any],
    *,
    scene_index: int,
    slot_index: int,
) -> str:
    asset_id = _scene_asset_id(scene, source)
    base = ""
    if asset_id.startswith("VGR-"):
        base = VOYAGER_RUNWARE_PROMPTS_BY_ASSET_ID.get(asset_id, "")
    if _is_volcano_scene(scene, source):
        base = VOLCANO_RUNWARE_PROMPTS_BY_ASSET_ID.get(asset_id, "")
    # The asset-plan IDs are reused across episodes (S01B01, S02B01, ...).
    # Only use the legacy no-fire prompt table when this scene actually belongs
    # to that topic; otherwise an unrelated episode can leak into Runware b-roll.
    if not base and _is_no_fire_scene(scene, source):
        base = NO_FIRE_RUNWARE_PROMPTS_BY_ASSET_ID.get(asset_id, "")
    if not base:
        scene_title = _clean_text(scene.get("scene_title") or source.get("scene_title"))
        scene_prompt = _clean_text(
            scene.get("image_prompt")
            or scene.get("prompt")
            or source.get("selected_prompt")
            or source.get("prompt")
        )
        narration = _clean_text(scene.get("narration"))[:360]
        base = (
            f"Documentary b-roll still for scene {scene_index + 1}: {scene_title}. "
            f"Visual direction: {scene_prompt}. "
            f"Visualize the narration faithfully without embedded text: {narration}"
        )
    camera = RUNWARE_CAMERA_VARIANTS[slot_index % len(RUNWARE_CAMERA_VARIANTS)]
    palette = (
        "natural documentary color, restrained contrast, realistic textures, "
        "no subtitles, no captions, no logos, no watermark, no UI, no readable text, "
        "16:9 landscape composition"
    )
    return f"{base} Variation: {camera}. {palette}."


def _config_value(key: str, fallback: str = "") -> str:
    try:
        import config

        value = config._load_config().get(key, fallback)  # type: ignore[attr-defined]
        return str(value or fallback)
    except Exception:  # noqa: BLE001
        return fallback


def _asset_section_key(entry: dict[str, Any]) -> str:
    asset_id = str(entry.get("asset_plan_id") or "")
    match = re.match(r"^(S\d+)", asset_id)
    return match.group(1) if match else ""


def _scene_section_number(scene: dict[str, Any], scene_index: int) -> int:
    asset_id = str(scene.get("producer_asset_plan_id") or "")
    match = re.match(r"^S(\d+)", asset_id)
    if match:
        return int(match.group(1))
    try:
        section_index = int(scene.get("section_index") or 0)
        if section_index > 0:
            return section_index
    except (TypeError, ValueError):
        pass
    return scene_index // 4 + 1


def _scene_duration_from_wav(episode_dir: Path, scene_index: int) -> float:
    path = episode_dir / f"scene_{scene_index:02d}.wav"
    if not path.exists() or path.stat().st_size <= 44:
        return 0.0
    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            return round(wav.getnframes() / sample_rate, 3) if sample_rate else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _scene_durations(
    *,
    episode_dir: Path,
    script: list[Any],
    tts_manifest: dict[str, Any] | None,
) -> list[float]:
    durations = [0.0 for _ in script]
    entries = (
        tts_manifest.get("entries", [])
        if isinstance(tts_manifest, dict) and isinstance(tts_manifest.get("entries"), list)
        else []
    )
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            scene_index = int(entry.get("scene_index"))
        except (TypeError, ValueError):
            continue
        if 0 <= scene_index < len(durations):
            try:
                durations[scene_index] = float(entry.get("duration_seconds") or 0.0)
            except (TypeError, ValueError):
                durations[scene_index] = 0.0

    for scene_index, duration in enumerate(durations):
        if duration <= 0:
            durations[scene_index] = _scene_duration_from_wav(episode_dir, scene_index)
    return [round(max(0.0, duration), 3) for duration in durations]


def _slot_count(duration: float, target_seconds: float, min_seconds: float, max_seconds: float) -> int:
    if duration <= 0:
        return 1
    count = max(1, int(round(duration / max(0.1, target_seconds))))
    while duration / count > max_seconds:
        count += 1
    while count > 1 and duration / count < min_seconds:
        count -= 1
    return max(1, count)


def _slot_durations(duration: float, count: int) -> list[float]:
    if count <= 1:
        return [round(duration, 3)]
    base = duration / count if count else duration
    slots = [round(base, 3) for _ in range(count)]
    delta = round(duration - sum(slots), 3)
    slots[-1] = round(slots[-1] + delta, 3)
    return slots


def _is_source_entry(entry: dict[str, Any]) -> bool:
    if str(entry.get("provider") or "") == LOCAL_REFRAME_PROVIDER:
        return False
    try:
        asset_index = int(entry.get("asset_index", 0) or 0)
    except (TypeError, ValueError):
        asset_index = 0
    if asset_index != 0:
        return False
    path = Path(str(entry.get("local_path") or ""))
    return path.suffix.lower() in (IMAGE_EXTENSIONS | VIDEO_EXTENSIONS) and path.exists() and path.stat().st_size > 1024


def _base_sources(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = [entry for entry in entries if _is_source_entry(entry)]
    return sorted(
        sources,
        key=lambda entry: (
            int(entry.get("scene_index") or 0),
            str(entry.get("asset_plan_id") or ""),
        ),
    )


def _select_source(
    *,
    scene_index: int,
    slot_index: int,
    scene_key: str,
    source_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    same_scene = [
        entry for entry in source_entries if int(entry.get("scene_index") or -1) == scene_index
    ]
    same_section = [
        entry for entry in source_entries if scene_key and _asset_section_key(entry) == scene_key
    ]
    near = [
        entry
        for entry in source_entries
        if abs(int(entry.get("scene_index") or 0) - scene_index) <= 2
    ]
    pools = [same_scene, same_section, near, source_entries] if slot_index == 0 else [same_section, near, source_entries]
    pool = next((items for items in pools if items), [])
    if not pool:
        return None
    if slot_index == 0 and same_scene:
        return same_scene[0]
    return pool[(scene_index + slot_index * 2) % len(pool)]


def _source_visual_key(entry: dict[str, Any]) -> str:
    provider = str(entry.get("provider") or "").strip().lower()
    # Generated scene anchors can legitimately cite the same research URL.
    # Their identity is the approved beat, not that shared evidence page;
    # otherwise the repeat guard replaces every later graphic/imagegen anchor
    # with a generic fallback even though the rendered files are different.
    if provider in {"codex_imagegen", "remotion_graphic", "runware_flux1"}:
        asset_plan_id = str(entry.get("asset_plan_id") or "").strip().lower()
        if asset_plan_id:
            return f"{provider}:{asset_plan_id}"
    title_key = _normalized_visual_title(entry.get("title"))
    if title_key:
        return title_key
    # A locally rendered explanatory graphic often has no external source URL
    # and shares a generic prompt with neighbouring graphics.  Its beat ID is
    # therefore a safer identity than that generic prompt; otherwise distinct
    # graphics are incorrectly treated as one repeated visual.
    for key in ("source_url", "download_url", "preview_url", "asset_plan_id", "prompt", "local_path"):
        value = str(entry.get(key) or "").strip().lower()
        if value:
            return value
    return ""


def _fresh_visual_key(candidate: dict[str, Any]) -> str:
    title_key = _normalized_visual_title(candidate.get("title"))
    if title_key:
        return title_key
    for key in ("fresh_image_url", "download_url", "preview_url", "source_url", "id"):
        value = str(candidate.get(key) or "").strip().lower()
        if value:
            return value
    return ""


def _normalized_visual_title(value: Any) -> str:
    text = _clean_text(value).lower()
    if not text:
        return ""
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9ก-๙]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 8:
        return ""
    generic = {
        "moon",
        "earth moon",
        "lunar surface",
        "apollo moon",
        "moon nasa",
    }
    if text in generic:
        return ""
    return f"title:{text}"


def _stock_visual_key(provider: str, keyword: str) -> str:
    return f"{provider}:{_clean_text(keyword).lower()}"


def _image_dhash(image: Image.Image, size: int = 9) -> int:
    gray = image.convert("L").resize((size, size - 1), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    value = 0
    for y in range(size - 1):
        row = pixels[y * size : (y + 1) * size]
        for x in range(size - 1):
            value = (value << 1) | (1 if row[x] > row[x + 1] else 0)
    return value


def _image_ahash(image: Image.Image, size: int = 8) -> int:
    gray = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    average = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | (1 if pixel > average else 0)
    return value


def _image_fingerprint(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() not in IMAGE_EXTENSIONS or not path.exists():
        return None
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            average = rgb.resize((1, 1), Image.Resampling.BILINEAR).getpixel((0, 0))
            return {
                "dhash": _image_dhash(rgb),
                "ahash": _image_ahash(rgb),
                "average_rgb": tuple(int(channel) for channel in average),
                "path": path.name,
            }
    except Exception:  # noqa: BLE001
        return None


def _hash_distance(left: int, right: int) -> int:
    return (int(left) ^ int(right)).bit_count()


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum(abs(int(left[index]) - int(right[index])) for index in range(3))


def _is_low_color_gray(value: tuple[int, int, int]) -> bool:
    return max(value) - min(value) <= 14


def _is_similar_image_fingerprint(
    fingerprint: dict[str, Any] | None,
    used_fingerprints: list[dict[str, Any]],
) -> bool:
    if not fingerprint:
        return False
    for used in used_fingerprints:
        dhash_distance = _hash_distance(fingerprint["dhash"], used["dhash"])
        ahash_distance = _hash_distance(fingerprint["ahash"], used["ahash"])
        color_distance = _color_distance(fingerprint["average_rgb"], used["average_rgb"])
        if dhash_distance <= 8 and ahash_distance <= 10:
            return True
        if dhash_distance <= 4 and color_distance <= 110:
            return True
        if ahash_distance <= 4 and color_distance <= 110:
            return True
        if (
            _is_low_color_gray(fingerprint["average_rgb"])
            and _is_low_color_gray(used["average_rgb"])
            and color_distance <= 30
        ):
            return True
    return False


def _can_use_visual_key(
    visual_key: str,
    *,
    section_number: int,
    visual_usage: dict[str, dict[str, Any]],
    max_repeats: int,
    scene_visual_keys: set[str] | None = None,
    section_visual_keys: set[str] | None = None,
    last_visual_key: str = "",
) -> bool:
    if not visual_key:
        return False
    if visual_key == last_visual_key:
        return False
    if scene_visual_keys and visual_key in scene_visual_keys:
        return False
    if section_visual_keys and visual_key in section_visual_keys:
        return False
    state = visual_usage.get(visual_key, {})
    if int(state.get("count", 0) or 0) >= max_repeats:
        return False
    used_sections = set(state.get("sections", set()) or set())
    if section_number not in used_sections and any(
        abs(section_number - int(used_section)) == 1 for used_section in used_sections
    ):
        return False
    return True


def _record_visual_key(
    visual_key: str,
    *,
    section_number: int,
    visual_usage: dict[str, dict[str, Any]],
) -> int:
    if not visual_key:
        return 0
    state = visual_usage.setdefault(visual_key, {"count": 0, "sections": set()})
    state["count"] = int(state.get("count", 0) or 0) + 1
    sections = state.setdefault("sections", set())
    if not isinstance(sections, set):
        sections = set(sections or [])
        state["sections"] = sections
    sections.add(section_number)
    return int(state["count"])


def _select_allowed_source(
    *,
    scene_index: int,
    slot_index: int,
    scene_key: str,
    section_number: int,
    source_entries: list[dict[str, Any]],
    visual_usage: dict[str, dict[str, Any]],
    max_repeats: int,
    scene_visual_keys: set[str] | None = None,
    section_visual_keys: set[str] | None = None,
    last_visual_key: str = "",
) -> dict[str, Any] | None:
    past_sources = [
        entry
        for entry in source_entries
        if int(entry.get("scene_index") or 0) <= scene_index
    ]
    same_section = [
        entry for entry in past_sources if scene_key and _asset_section_key(entry) == scene_key
    ]
    near = [
        entry
        for entry in past_sources
        if scene_index - int(entry.get("scene_index") or 0) <= 2
    ]
    pools = [same_section, near, past_sources]
    candidates: list[dict[str, Any]] = []
    for pool in pools:
        for entry in pool:
            if entry not in candidates:
                candidates.append(entry)
    if not candidates:
        return None
    offset = (scene_index + slot_index * 2) % len(candidates)
    ordered = candidates[offset:] + candidates[:offset]
    for entry in ordered:
        if _can_use_visual_key(
            _source_visual_key(entry),
            section_number=section_number,
            visual_usage=visual_usage,
            max_repeats=max_repeats,
            scene_visual_keys=scene_visual_keys,
            section_visual_keys=section_visual_keys,
            last_visual_key=last_visual_key,
        ):
            return entry
    return None


def _cover_crop_box(
    *,
    width: int,
    height: int,
    target_ratio: float,
    zoom: float,
    x_bias: float,
    y_bias: float,
) -> tuple[int, int, int, int]:
    crop_width = width
    crop_height = int(round(crop_width / target_ratio))
    if crop_height > height:
        crop_height = height
        crop_width = int(round(crop_height * target_ratio))

    crop_width = max(1, int(round(crop_width / zoom)))
    crop_height = max(1, int(round(crop_height / zoom)))
    max_left = max(0, width - crop_width)
    max_top = max(0, height - crop_height)
    left = int(round(max_left * min(1.0, max(0.0, x_bias))))
    top = int(round(max_top * min(1.0, max(0.0, y_bias))))
    return left, top, left + crop_width, top + crop_height


def _vignette(image: Image.Image, strength: float) -> Image.Image:
    if strength <= 0:
        return image
    mask_size = (320, 180)
    mask = Image.new("L", mask_size, 0)
    pixels = mask.load()
    width, height = mask_size
    for y in range(height):
        ny = (y - height / 2) / (height / 2)
        for x in range(width):
            nx = (x - width / 2) / (width / 2)
            distance = min(1.0, math.sqrt(nx * nx + ny * ny))
            pixels[x, y] = int(255 * max(0.0, (distance - 0.45) / 0.55) * strength)
    mask = mask.resize(image.size, Image.Resampling.BICUBIC)
    dark = Image.new("RGB", image.size, (0, 0, 0))
    return Image.composite(dark, image, mask.filter(ImageFilter.GaussianBlur(28)))


def _render_reframe(source_path: Path, output_path: Path, *, scene_index: int, slot_index: int) -> int:
    frame_path: Path | None = None
    image_source = source_path
    if source_path.suffix.lower() in VIDEO_EXTENSIONS:
        frame_path = output_path.with_name(f".{output_path.stem}_source_frame.jpg")
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        extracted = False
        for seek_seconds in (max(0.5, slot_index * 1.7), 0.5, 0.0):
            frame_path.unlink(missing_ok=True)
            result = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", str(seek_seconds), "-i", str(source_path),
                    "-frames:v", "1", str(frame_path),
                ],
                capture_output=True,
                timeout=45,
            )
            if result.returncode == 0 and frame_path.exists() and frame_path.stat().st_size > 1024:
                extracted = True
                break
        if not extracted:
            raise RuntimeError(f"failed to extract b-roll frame from {source_path}")
        image_source = frame_path
    try:
        with Image.open(image_source) as src:
            image = src.convert("RGB")
    finally:
        if frame_path is not None:
            frame_path.unlink(missing_ok=True)
    width, height = image.size
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    phase = (scene_index * 17 + slot_index * 31) % 100
    zoom = 1.02 + ((phase % 9) * 0.018)
    x_bias = ((phase * 37) % 100) / 100
    y_bias = ((phase * 53) % 100) / 100
    crop = _cover_crop_box(
        width=width,
        height=height,
        target_ratio=target_ratio,
        zoom=zoom,
        x_bias=x_bias,
        y_bias=y_bias,
    )
    image = image.crop(crop).resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    contrast = 1.02 + ((slot_index % 3) * 0.015)
    color = 1.0 + (((scene_index + slot_index) % 3) - 1) * 0.025
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(color)
    image = _vignette(image, 0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".png":
        image.save(output_path, format="PNG", optimize=True)
    else:
        image.save(output_path, format="JPEG", quality=91, optimize=True, progressive=True)
    return output_path.stat().st_size


def _render_local_graphic(
    output_path: Path,
    *,
    scene_index: int,
    slot_index: int,
    scene: dict[str, Any] | None = None,
    source: dict[str, Any] | None = None,
) -> int:
    phase = scene_index * 41 + slot_index * 17
    theme = _no_fire_theme(scene, source)
    palettes = {
        "city": ((8, 18, 15), (20, 54, 42), (74, 174, 122)),
        "modern": ((10, 12, 16), (31, 35, 42), (126, 154, 166)),
        "evidence": ((25, 18, 14), (72, 50, 34), (196, 145, 84)),
        "food": ((14, 31, 19), (55, 83, 42), (210, 150, 70)),
        "energy": ((14, 19, 28), (45, 42, 56), (237, 164, 68)),
        "body": ((18, 19, 20), (64, 43, 32), (216, 136, 86)),
        "night": ((3, 9, 13), (9, 29, 32), (77, 136, 118)),
        "shelter_night": ((5, 10, 13), (16, 35, 32), (111, 136, 94)),
        "cold": ((10, 16, 23), (37, 58, 75), (170, 210, 220)),
        "tech": ((12, 16, 18), (38, 41, 37), (220, 149, 72)),
        "tools": ((21, 18, 14), (66, 55, 39), (180, 151, 98)),
        "settlement": ((14, 28, 18), (54, 70, 40), (188, 142, 76)),
        "population": ((8, 15, 20), (28, 46, 54), (104, 184, 172)),
        "storage": ((19, 25, 17), (61, 61, 36), (201, 160, 88)),
        "culture": ((4, 8, 12), (17, 22, 28), (126, 120, 100)),
        "vanished": ((15, 16, 18), (48, 45, 40), (223, 126, 84)),
        "future": ((8, 13, 20), (27, 42, 52), (236, 162, 67)),
        "abstract": ((9, 15, 19), (30, 43, 48), (120, 166, 142)),
    }
    base_a, base_b, accent = palettes.get(theme, palettes["abstract"])
    image = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), base_a)
    draw = ImageDraw.Draw(image, "RGBA")

    for y in range(TARGET_HEIGHT):
        t = y / max(1, TARGET_HEIGHT - 1)
        row = tuple(int(base_a[i] * (1 - t) + base_b[i] * t) for i in range(3))
        draw.line([(0, y), (TARGET_WIDTH, y)], fill=row)

    for particle in range(95):
        x = (particle * 149 + phase * 23) % TARGET_WIDTH
        y = (particle * 83 + phase * 19) % TARGET_HEIGHT
        alpha = 18 + ((particle + phase) % 54)
        radius = 1 + ((particle + phase) % 4 == 0)
        draw.ellipse((x, y, x + radius, y + radius), fill=(*accent, alpha))

    def person(cx: int, feet_y: int, scale: float, fill=(14, 18, 18, 220)) -> None:
        head_r = int(18 * scale)
        body_h = int(72 * scale)
        draw.ellipse((cx - head_r, feet_y - body_h - head_r * 2, cx + head_r, feet_y - body_h), fill=fill)
        draw.polygon(
            [
                (cx - int(20 * scale), feet_y - body_h),
                (cx + int(20 * scale), feet_y - body_h),
                (cx + int(28 * scale), feet_y - int(14 * scale)),
                (cx - int(28 * scale), feet_y - int(14 * scale)),
            ],
            fill=fill,
        )
        draw.line((cx - int(38 * scale), feet_y - int(58 * scale), cx + int(38 * scale), feet_y - int(50 * scale)), fill=fill, width=max(2, int(5 * scale)))

    def tree(x: int, base_y: int, height: int, alpha: int = 180) -> None:
        trunk = max(8, height // 22)
        draw.rectangle((x - trunk, base_y - height, x + trunk, base_y), fill=(7, 18, 14, alpha))
        for layer in range(4):
            y = base_y - int(height * (0.28 + layer * 0.18))
            w = int(height * (0.28 - layer * 0.035))
            draw.polygon((x, y - w, x - w, y + w // 2, x + w, y + w // 2), fill=(18, 48, 34, alpha - layer * 18))

    horizon = int(TARGET_HEIGHT * 0.72)
    draw.rectangle((0, horizon, TARGET_WIDTH, TARGET_HEIGHT), fill=(2, 8, 8, 105))

    if theme in {"city", "modern"}:
        for i in range(13):
            w = 70 + ((i * 37 + phase) % 90)
            h = 150 + ((i * 53 + phase) % 360)
            x = 90 + i * 145
            draw.rectangle((x, horizon - h, x + w, horizon), fill=(12, 16, 16, 170))
            if theme == "city":
                tree(x + w // 2, TARGET_HEIGHT, 330 + (i % 4) * 70, 130)
        for i in range(9):
            x = 160 + i * 190
            y = horizon - 40 - (i % 3) * 24
            draw.arc((x, y, x + 120, y + 90), 190, 320, fill=(*accent, 76), width=8)
        person(440, horizon + 72, 1.0)
        person(520, horizon + 74, 0.8)
    elif theme == "evidence":
        cave = (180, 180, TARGET_WIDTH - 180, TARGET_HEIGHT - 150)
        draw.rounded_rectangle(cave, radius=42, fill=(42, 31, 24, 185), outline=(*accent, 70), width=4)
        for layer in range(8):
            y = cave[1] + 70 + layer * 82 + int(math.sin(layer + phase) * 10)
            draw.line((cave[0] + 55, y, cave[2] - 55, y + int(math.sin(layer * 2) * 18)), fill=(177, 116, 67, 62), width=7)
        for chip in range(70):
            x = cave[0] + 70 + ((chip * 71 + phase) % (cave[2] - cave[0] - 140))
            y = cave[1] + 80 + ((chip * 43 + phase) % (cave[3] - cave[1] - 160))
            r = 4 + (chip % 9)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(22, 18, 14, 80 + chip % 90))
    elif theme in {"food", "storage"}:
        for i in range(12):
            cx = 220 + (i % 6) * 280 + ((phase + i * 19) % 42)
            cy = 250 + (i // 6) * 300 + ((phase + i * 23) % 50)
            draw.ellipse((cx - 52, cy - 34, cx + 52, cy + 34), fill=(66, 105, 48, 150))
            draw.line((cx - 65, cy + 48, cx + 65, cy - 48), fill=(189, 129, 74, 120), width=9)
            draw.ellipse((cx + 36, cy + 48, cx + 78, cy + 88), fill=(172, 91, 57, 165))
        if theme == "storage":
            for i in range(5):
                x = 470 + i * 200
                draw.ellipse((x - 62, horizon - 160, x + 62, horizon - 30), outline=(*accent, 150), width=8)
                draw.arc((x - 65, horizon - 205, x + 65, horizon - 85), 190, 350, fill=(*accent, 80), width=5)
    elif theme == "body":
        panel_y = 260
        centers = (470, 960, 1450)
        for cx_panel in centers:
            draw.ellipse((cx_panel - 170, panel_y - 70, cx_panel + 170, panel_y + 270), fill=(18, 22, 24, 165), outline=(*accent, 95), width=6)
        # Jaw and teeth.
        cx_panel = centers[0]
        draw.arc((cx_panel - 92, panel_y + 10, cx_panel + 92, panel_y + 190), 30, 150, fill=(*accent, 170), width=12)
        draw.arc((cx_panel - 118, panel_y + 58, cx_panel + 118, panel_y + 250), 205, 335, fill=(218, 126, 78, 150), width=16)
        for tooth in range(9):
            x = cx_panel - 72 + tooth * 18
            draw.rounded_rectangle((x, panel_y + 158, x + 11, panel_y + 214), radius=4, fill=(220, 194, 150, 170))
        # Long gut path.
        cx_panel = centers[1]
        for loop in range(5):
            inset = loop * 24
            draw.arc((cx_panel - 110 + inset, panel_y + 35 + inset, cx_panel + 110 - inset, panel_y + 245 - inset), 20, 330, fill=(220, 138, 82, 150), width=13)
        draw.arc((cx_panel - 130, panel_y + 40, cx_panel + 130, panel_y + 250), 210, 35, fill=(*accent, 120), width=9)
        # Smaller brain reserve.
        cx_panel = centers[2]
        draw.ellipse((cx_panel - 115, panel_y + 45, cx_panel + 115, panel_y + 205), outline=(*accent, 170), width=10)
        for fold in range(6):
            y = panel_y + 78 + fold * 21
            draw.arc((cx_panel - 92, y - 32, cx_panel + 92, y + 48), 190, 350, fill=(220, 170, 98, 105), width=6)
        draw.ellipse((cx_panel + 25, panel_y + 95, cx_panel + 68, panel_y + 136), fill=(220, 110, 72, 100))
        person(960, horizon + 90, 1.1, fill=(10, 13, 13, 170))
    elif theme == "energy":
        center_x = TARGET_WIDTH // 2
        person(center_x - 340, horizon + 80, 2.0, fill=(14, 14, 13, 210))
        draw.ellipse((center_x + 160, 240, center_x + 410, 490), outline=(*accent, 155), width=10)
        draw.arc((center_x + 210, 325, center_x + 540, 655), 90, 270, fill=(229, 160, 72, 140), width=14)
        draw.arc((center_x + 80, 545, center_x + 460, 875), 250, 70, fill=(206, 112, 77, 115), width=12)
        for step in range(5):
            x1 = center_x - 130 + step * 90
            y1 = 540 + int(math.sin(step + phase) * 38)
            draw.line((x1, y1, x1 + 75, y1 - 48), fill=(*accent, 108), width=8)
            draw.ellipse((x1 + 68, y1 - 56, x1 + 88, y1 - 36), fill=(*accent, 185))
    elif theme in {"night", "shelter_night", "culture"}:
        for i in range(15):
            tree(70 + i * 135 + ((phase + i * 13) % 35), TARGET_HEIGHT, 430 + (i % 5) * 80, 150)
        for i in range(8):
            x = 250 + i * 190
            y = 390 + (i % 3) * 44
            draw.ellipse((x, y, x + 14, y + 8), fill=(210, 170, 84, 95))
            draw.ellipse((x + 30, y, x + 44, y + 8), fill=(210, 170, 84, 95))
        if theme == "culture":
            draw.ellipse((730, 470, 1190, 860), outline=(140, 125, 92, 85), width=7)
            for i, angle in enumerate((205, 240, 300, 335)):
                rad = math.radians(angle)
                person(960 + int(math.cos(rad) * 330), 690 + int(math.sin(rad) * 135), 0.95)
        else:
            for i in range(5):
                person(610 + i * 105, horizon + 70 + (i % 2) * 18, 0.75)
            draw.polygon((420, horizon, 640, horizon - 120, 860, horizon), fill=(30, 45, 34, 145))
    elif theme == "cold":
        for i in range(5):
            x = i * 430 - 90
            peak = 300 + (i % 3) * 70
            draw.polygon((x, horizon, x + 250, peak, x + 560, horizon), fill=(42, 58, 68, 178))
            draw.polygon((x + 250, peak, x + 190, peak + 95, x + 325, peak + 105), fill=(185, 214, 222, 142))
        for streak in range(45):
            x = (streak * 101 + phase * 7) % TARGET_WIDTH
            y = 130 + (streak * 43) % 720
            draw.line((x, y, x + 85, y + 16), fill=(210, 238, 240, 55), width=3)
    elif theme in {"tech", "tools", "vanished"}:
        baseline = int(TARGET_HEIGHT * 0.68)
        for i in range(6):
            x = 330 + i * 230
            angle = -18 if theme == "tech" and i > 1 else 0
            box = Image.new("RGBA", (120, 210), (0, 0, 0, 0))
            bd = ImageDraw.Draw(box, "RGBA")
            bd.rounded_rectangle((18, 18, 102, 192), radius=10, fill=(*accent, 95), outline=(*accent, 180), width=5)
            rotated = box.rotate(angle, expand=True)
            image.paste(rotated, (x, baseline - rotated.height), rotated)
        if theme == "tools":
            for i in range(5):
                x = 450 + i * 230
                draw.polygon((x, 375, x + 145, 305, x + 112, 470), fill=(120, 116, 101, 185))
                draw.line((x + 38, 470, x - 40, 710), fill=(116, 76, 48, 160), width=18)
        if theme == "vanished":
            icons = [(470, 420, 670, 690), (840, 360, 1040, 700), (1210, 440, 1450, 680)]
            for box in icons:
                draw.rounded_rectangle(box, radius=32, outline=(*accent, 145), width=9)
                draw.line((box[0] - 35, box[3] + 35, box[2] + 35, box[1] - 35), fill=(220, 82, 64, 140), width=12)
    elif theme in {"settlement", "population"}:
        if theme == "population":
            draw.ellipse((260, 270, 1660, 820), outline=(*accent, 75), width=8)
            draw.rectangle((250, 508, 1670, 580), fill=(152, 122, 72, 35))
            for dot in range(42):
                x = 380 + (dot * 83 + phase) % 1120
                y = 520 + ((dot * 37 + phase) % 95) - 42
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(*accent, 180))
        else:
            for i in range(6):
                x = 270 + i * 250
                draw.polygon((x, horizon, x + 100, horizon - 140, x + 205, horizon), fill=(86, 72, 44, 165))
                draw.line((x + 100, horizon - 140, x + 100, horizon + 20), fill=(48, 35, 22, 160), width=6)
            for i in range(7):
                person(390 + i * 170, horizon + 78, 0.62)
    elif theme == "future":
        points = [(430, 650), (730, 540), (1010, 475), (1310, 385), (1550, 310)]
        draw.line(points, fill=(*accent, 110), width=10)
        for i, (x, y) in enumerate(points):
            r = 34 + i * 5
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*accent, 70 + i * 18), outline=(*accent, 170), width=4)
        draw.polygon((390, 675, 430, 560, 470, 675), fill=(237, 126, 55, 175))
        draw.polygon((1260, 525, 1375, 305, 1450, 525), outline=(*accent, 170), fill=(80, 98, 105, 90))
        for node in range(9):
            x = 1480 + int(math.cos(node * 0.7) * (70 + node * 7))
            y = 300 + int(math.sin(node * 0.7) * (54 + node * 6))
            draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(120, 210, 210, 165))
            draw.line((1550, 310, x, y), fill=(120, 210, 210, 50), width=3)

    image = _vignette(image, 0.22)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".png":
        image.save(output_path, format="PNG", optimize=True)
    else:
        image.save(output_path, format="JPEG", quality=90, optimize=True, progressive=True)
    return output_path.stat().st_size


def _url_extension(url: str) -> str:
    path = urlparse(str(url or "")).path.lower()
    match = re.search(r"\.([a-z0-9]+)$", path)
    return f".{match.group(1)}" if match else ""


def _download_temp_image(url: str, *, max_bytes: int) -> Path | None:
    if not url:
        return None
    suffix = _url_extension(url)
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = Path(tmp.name)
    tmp.close()
    written = 0
    try:
        with _http_get(url, stream=True, headers=HTTP_HEADERS, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length") or 0)
            if content_length and content_length > max_bytes:
                raise RuntimeError(f"download exceeds cap: {content_length} > {max_bytes}")
            with tmp_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if written > max_bytes:
                        raise RuntimeError(f"download exceeds cap: {written} > {max_bytes}")
        if written <= 1024:
            raise RuntimeError("downloaded image is too small")
        return tmp_path
    except Exception:  # noqa: BLE001
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def _image_url_from_official(result: dict[str, Any]) -> str:
    media_type = str(result.get("media_type") or "").lower()
    download_url = str(result.get("download_url") or "")
    preview_url = str(result.get("preview_url") or "")
    if media_type == "image" and download_url:
        return download_url
    for url in (preview_url, download_url):
        if _url_extension(url) in IMAGE_EXTENSIONS:
            return url
    return ""


def _official_relevance_text(result: dict[str, Any]) -> str:
    keywords = " ".join(str(item) for item in result.get("keywords", []) if str(item).strip())
    return " ".join(
        str(value or "")
        for value in (
            result.get("title"),
            result.get("description"),
            keywords,
            result.get("source_url"),
            result.get("download_url"),
            result.get("preview_url"),
            result.get("fresh_image_url"),
        )
    ).lower()


def _is_voyager_official_profile(scenes: list[dict[str, Any]]) -> bool:
    text = " ".join(_scene_context_text(scene) for scene in scenes)
    return any(
        marker in text
        for marker in (
            "voyager",
            "วอยเอเจอร์",
            "golden record",
            "โกลเดนเรคคอร์ด",
        )
    )


def _is_denisovan_profile(scenes: list[dict[str, Any]]) -> bool:
    """Identify the archaeological-human-evolution cut before applying defaults.

    The original b-roll fallback was deliberately lunar-specific.  Returning a
    positive profile here prevents unrelated Moon imagery from entering a
    Denisovan timeline when no stock provider has been configured.
    """
    text = " ".join(_scene_context_text(scene) for scene in scenes).lower()
    return any(
        marker in text
        for marker in (
            "denisovan",
            "denisova",
            "penghu",
            "ไต้หวัน",
            "ถ้ำเดนิโซวา",
            "โปรตีนโบราณ",
        )
    )


def _is_relevant_official_result(
    result: dict[str, Any],
    *,
    relevance_markers: set[str] | None = None,
    blocked_markers: set[str] | None = None,
) -> bool:
    text = _official_relevance_text(result)
    required = relevance_markers or OFFICIAL_RELEVANCE_MARKERS
    blocked = blocked_markers or OFFICIAL_BLOCKED_MARKERS
    if not any(marker in text for marker in required):
        return False
    if any(marker in text for marker in blocked):
        return False
    return True


def _build_official_queries(scenes: list[dict[str, Any]]) -> list[str]:
    episode_queries = next((s["_episode_official_queries"] for s in scenes if s.get("_episode_official_queries")), None)
    if episode_queries:
        queries = list(episode_queries)
    elif _is_voyager_official_profile(scenes):
        queries = list(VOYAGER_OFFICIAL_QUERIES)
    elif _is_denisovan_profile(scenes):
        # The provider may have no matching archive, but it must never fall
        # through to the generic lunar query set for this science topic.
        queries = list(DENISOVAN_OFFICIAL_QUERIES)
    else:
        queries = [
        "Moon",
        "lunar surface",
        "Moon craters",
        "lunar laser ranging",
        "Apollo Moon",
        "Earth Moon",
        "Moon NASA lunar surface",
        "Moon Earth NASA",
        "Lunar Reconnaissance Orbiter Moon NASA",
        "Apollo lunar laser ranging retroreflector Moon NASA",
        "Moon craters NASA LRO",
        "Earth Moon tides NASA visualization",
        "Moon orbit Earth NASA visualization",
        "Earth from Moon NASA",
        ]
        for scene in scenes:
            section_title = _clean_text(scene.get("section_title"))
            scene_title = _clean_text(scene.get("scene_title"))
            narration = _clean_text(scene.get("narration"))[:260]
            if section_title:
                queries.append(f"{section_title} NASA Moon")
            haystack = f"{section_title} {scene_title} {narration}".lower()
            if any(token in haystack for token in ("laser", "retroreflector", "apollo", "วัดระยะ")):
                queries.append("Apollo lunar laser ranging retroreflector NASA")
            if any(token in haystack for token in ("tidal", "tide", "น้ำขึ้น", "แรงดึง")):
                queries.append("Earth Moon tides NASA")
                queries.append("tidal bulge Moon Earth NASA visualization")
            if any(token in haystack for token in ("geolog", "ธรณี", "past", "อดีต")):
                queries.append("Moon geology lunar samples NASA")
            if any(token in haystack for token in ("reconnaissance", "lro", "evidence", "ข้อมูล")):
                queries.append("Lunar Reconnaissance Orbiter Moon surface NASA")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        key = query.lower()
        if query and key not in seen:
            seen.add(key)
            deduped.append(query)
    return deduped


def _fresh_official_candidates(
    *,
    scenes: list[dict[str, Any]],
    limit: int,
    search: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not search or limit <= 0:
        return [], []
    warnings: list[str] = []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        from official_media_provider import search_official_media
    except Exception as exc:  # noqa: BLE001
        return [], [f"official media provider unavailable: {exc}"]

    voyager_profile = _is_voyager_official_profile(scenes)
    denisovan_profile = _is_denisovan_profile(scenes)
    relevance_markers = (
        VOYAGER_OFFICIAL_RELEVANCE_MARKERS
        if voyager_profile
        else DENISOVAN_OFFICIAL_RELEVANCE_MARKERS
        if denisovan_profile
        else OFFICIAL_RELEVANCE_MARKERS
    )
    blocked_markers = (
        VOYAGER_OFFICIAL_BLOCKED_MARKERS
        if voyager_profile
        else DENISOVAN_OFFICIAL_BLOCKED_MARKERS
        if denisovan_profile
        else OFFICIAL_BLOCKED_MARKERS
    )
    episode_scene = next((s for s in scenes if s.get("_episode_official_queries")), None)
    if episode_scene is not None:
        relevance_markers = set(episode_scene.get("_episode_official_markers") or [])
        blocked_markers = set(episode_scene.get("_episode_official_blocked") or [])
    queries = _build_official_queries(scenes)
    per_query_limit = 15
    for query in queries:
        if len(candidates) >= limit:
            break
        try:
            results = search_official_media(
                query,
                limit=per_query_limit,
                media_types=("image", "video"),
                include_nasa_images=True,
                include_svs=True,
                include_jpl=True,
                resolve_downloads=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"official search failed for {query!r}: {exc}")
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            image_url = _image_url_from_official(result)
            key = (image_url or str(result.get("source_url") or result.get("id") or "")).lower()
            if not image_url or not key or key in seen:
                continue
            item = dict(result)
            item["fresh_image_url"] = image_url
            item["fresh_query"] = query
            if not _is_relevant_official_result(
                item,
                relevance_markers=relevance_markers,
                blocked_markers=blocked_markers,
            ):
                continue
            seen.add(key)
            candidates.append(item)
            if len(candidates) >= limit:
                break
    return candidates, warnings


def _existing_fresh_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("timeline_role") != FRESH_OFFICIAL_ROLE:
            continue
        local_path = Path(str(entry.get("local_path") or ""))
        if not local_path.exists() or local_path.stat().st_size <= 1024:
            continue
        candidate = {
            "provider": entry.get("provider"),
            "title": entry.get("title"),
            "source_url": entry.get("source_url"),
            "download_url": entry.get("download_url"),
            "preview_url": entry.get("preview_url"),
            "fresh_image_url": entry.get("fresh_image_url")
            or entry.get("download_url")
            or entry.get("preview_url")
            or entry.get("source_url"),
            "fresh_query": entry.get("keyword"),
            "credit": entry.get("credit"),
            "license_note": entry.get("license_note"),
            "license_url": entry.get("license_url"),
            "local_path": str(local_path),
        }
        visual_key = _fresh_visual_key(candidate)
        if not visual_key or visual_key in seen:
            continue
        seen.add(visual_key)
        candidates.append(candidate)
    return candidates


def _select_fresh_official(
    *,
    scene: dict[str, Any],
    scene_index: int,
    slot_index: int,
    section_number: int,
    candidates: list[dict[str, Any]],
    visual_usage: dict[str, dict[str, Any]],
    max_repeats: int,
    scene_visual_keys: set[str] | None = None,
    section_visual_keys: set[str] | None = None,
    last_visual_key: str = "",
    exclude_keys: set[str] | None = None,
) -> dict[str, Any] | None:
    if not candidates:
        return None
    excluded = exclude_keys or set()
    asset_id = _scene_asset_id(scene)
    ordered_candidates = candidates
    if asset_id.startswith("VGR-"):
        query_hints = VOYAGER_OFFICIAL_QUERY_HINTS_BY_ASSET_ID.get(asset_id, ())
        ordered_candidates = [
            candidate
            for candidate in candidates
            if any(
                hint in _clean_text(candidate.get("fresh_query")).lower()
                for hint in query_hints
            )
        ]
    if not ordered_candidates:
        return None
    offset = (scene_index * 11 + slot_index * 3) % len(ordered_candidates)
    ordered = ordered_candidates[offset:] + ordered_candidates[:offset]
    for candidate in ordered:
        visual_key = _fresh_visual_key(candidate)
        if visual_key in excluded:
            continue
        if _can_use_visual_key(
            visual_key,
            section_number=section_number,
            visual_usage=visual_usage,
            max_repeats=max_repeats,
            scene_visual_keys=scene_visual_keys,
            section_visual_keys=section_visual_keys,
            last_visual_key=last_visual_key,
        ):
            return candidate
    return None


def _entry_for_fresh_official(
    *,
    candidate: dict[str, Any],
    source: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    output_path: Path,
    bytes_written: int,
) -> dict[str, Any]:
    return {
        "asset_plan_id": f"{source.get('asset_plan_id') or f'SC{scene_index:02d}'}O{slot_index:02d}",
        "scene_index": scene_index,
        "asset_index": slot_index,
        "scene_title": source.get("scene_title", ""),
        "provider": candidate.get("provider") or "official_media",
        "media_type": "image",
        "local_path": str(output_path),
        "bytes": bytes_written,
        "status": "downloaded",
        "timeline_role": FRESH_OFFICIAL_ROLE,
        "slot_duration_seconds": slot_duration,
        "source_url": candidate.get("source_url"),
        "download_url": candidate.get("download_url"),
        "preview_url": candidate.get("preview_url"),
        "fresh_image_url": candidate.get("fresh_image_url"),
        "credit": candidate.get("credit"),
        "license_note": candidate.get("license_note"),
        "license_url": candidate.get("license_url"),
        "prompt": source.get("prompt"),
        "keyword": candidate.get("fresh_query") or source.get("keyword"),
        "title": candidate.get("title"),
        "selected_reason": "Fresh official b-roll image added to avoid repeating the same visual source.",
        "generated_or_illustrative": False,
        "derived_from_asset_plan_id": source.get("asset_plan_id"),
        "derived_from_provider": source.get("provider"),
        "accessed_date": _utc_now()[:10],
    }


def _entry_for_original(
    *,
    source: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
) -> dict[str, Any]:
    entry = dict(source)
    entry["scene_index"] = scene_index
    entry["asset_index"] = slot_index
    entry["timeline_role"] = "scene_anchor" if slot_index == 0 else "source"
    entry["slot_duration_seconds"] = slot_duration
    entry["status"] = entry.get("status") or "generated"
    return entry


def _entry_for_reframe(
    *,
    source: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    output_path: Path,
    bytes_written: int,
) -> dict[str, Any]:
    generated_from_provider = str(source.get("provider") or "") in {
        "codex_imagegen",
        "runware_flux1",
        "remotion_graphic",
    }
    return {
        "asset_plan_id": f"{source.get('asset_plan_id') or f'SC{scene_index:02d}'}R{slot_index:02d}",
        "scene_index": scene_index,
        "asset_index": slot_index,
        "scene_title": source.get("scene_title", ""),
        "provider": LOCAL_REFRAME_PROVIDER,
        "media_type": "image",
        "local_path": str(output_path),
        "bytes": bytes_written,
        "status": "generated",
        "timeline_role": "derived_broll",
        "slot_duration_seconds": slot_duration,
        "source_url": source.get("source_url"),
        "download_url": source.get("download_url"),
        "preview_url": source.get("preview_url"),
        "credit": source.get("credit"),
        "license_note": source.get("license_note"),
        "prompt": source.get("prompt"),
        "keyword": source.get("keyword"),
        "selected_reason": "Local visual pacing reframe from an existing sourced Producer Mode asset.",
        "generated_or_illustrative": bool(generated_from_provider),
        "derived_from_asset_plan_id": source.get("asset_plan_id"),
        "derived_from_provider": source.get("provider"),
        "derived_from_local_path": source.get("local_path"),
        "accessed_date": _utc_now()[:10],
    }


def _entry_for_local_graphic(
    *,
    source: dict[str, Any],
    scene: dict[str, Any] | None = None,
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    output_path: Path,
    bytes_written: int,
) -> dict[str, Any]:
    asset_id = _scene_asset_id(scene, source) or f"SC{scene_index:02d}"
    return {
        "asset_plan_id": f"{asset_id}G{slot_index:02d}",
        "scene_index": scene_index,
        "asset_index": slot_index,
        "scene_title": source.get("scene_title", ""),
        "provider": LOCAL_GRAPHIC_PROVIDER,
        "media_type": "image",
        "local_path": str(output_path),
        "bytes": bytes_written,
        "status": "generated",
        "timeline_role": "local_graphic_broll",
        "slot_duration_seconds": slot_duration,
        "source_url": source.get("source_url"),
        "credit": "Producer Mode local graphic",
        "license_note": "Generated locally from code; no external media rights.",
        "prompt": source.get("prompt"),
        "keyword": source.get("keyword"),
        "selected_reason": "Unique local explanatory b-roll graphic used after repeat limits exhausted.",
        "generated_or_illustrative": True,
        "derived_from_asset_plan_id": source.get("asset_plan_id"),
        "derived_from_provider": source.get("provider"),
        "accessed_date": _utc_now()[:10],
    }


def _entry_for_runware_broll(
    *,
    source: dict[str, Any],
    scene: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    output_path: Path,
    bytes_written: int,
    prompt: str,
) -> dict[str, Any]:
    asset_id = _scene_asset_id(scene, source) or f"SC{scene_index:02d}"
    return {
        "asset_plan_id": f"{asset_id}R{slot_index:02d}",
        "scene_index": scene_index,
        "asset_index": slot_index,
        "scene_title": source.get("scene_title", "") or scene.get("scene_title", ""),
        "provider": RUNWARE_BROLL_PROVIDER,
        "media_type": "image",
        "local_path": str(output_path),
        "bytes": bytes_written,
        "status": "generated",
        "timeline_role": GENERATED_IMAGE_ROLE,
        "slot_duration_seconds": slot_duration,
        "source_url": "runware://flux1",
        "credit": "Runware FLUX.1 generated image",
        "license_note": "Generated image for Producer Mode b-roll; no external footage rights.",
        "prompt": prompt,
        "keyword": source.get("keyword"),
        "selected_reason": "Topic-specific generated b-roll used where stock footage was weak or too repetitive.",
        "generated_or_illustrative": True,
        "derived_from_asset_plan_id": source.get("asset_plan_id"),
        "derived_from_provider": source.get("provider"),
        "accessed_date": _utc_now()[:10],
    }


def _entry_for_policy_blocked(
    *,
    source: dict[str, Any],
    scene: dict[str, Any] | None,
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    provider: str,
    category: str,
    planned_total_count: int,
) -> dict[str, Any]:
    asset_id = _scene_asset_id(scene, source) or f"SC{scene_index:02d}"
    return {
        "asset_plan_id": f"{asset_id}P{slot_index:02d}",
        "scene_index": scene_index,
        "asset_index": slot_index,
        "scene_title": source.get("scene_title", "") or (scene or {}).get("scene_title", ""),
        "provider": provider,
        "media_type": "none",
        "local_path": "",
        "bytes": 0,
        "status": "failed",
        "timeline_role": "policy_blocked",
        "slot_duration_seconds": slot_duration,
        "source_url": source.get("source_url"),
        "credit": "",
        "license_note": "",
        "prompt": source.get("prompt"),
        "keyword": source.get("keyword"),
        "selected_reason": (
            f"Visual source policy blocked {category} fallback before generation; "
            f"planned timeline slots={planned_total_count}."
        ),
        "generated_or_illustrative": category in {"graphic", "generated_image"},
        "derived_from_asset_plan_id": source.get("asset_plan_id"),
        "derived_from_provider": source.get("provider"),
        "issue": (
            f"visual source policy blocked {category} fallback; replace with real footage, "
            "approved reframe, or revise the timeline."
        ),
        "accessed_date": _utc_now()[:10],
    }


def _try_runware_broll(
    *,
    episode_path: Path,
    scene: dict[str, Any],
    source: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    allow_runware: bool,
) -> dict[str, Any] | None:
    if not allow_runware:
        return None
    prompt = _runware_broll_prompt(
        scene,
        source,
        scene_index=scene_index,
        slot_index=slot_index,
    )
    output_path = episode_path / f"scene_{scene_index:02d}_{slot_index}_runware.png"
    try:
        from runware_provider import generate_flux1_image

        result = generate_flux1_image(prompt, str(output_path))
    except Exception:  # noqa: BLE001
        result = None
    if result and output_path.exists() and output_path.stat().st_size > 1024:
        return _entry_for_runware_broll(
            source=source,
            scene=scene,
            scene_index=scene_index,
            slot_index=slot_index,
            slot_duration=slot_duration,
            output_path=output_path,
            bytes_written=output_path.stat().st_size,
            prompt=prompt,
        )
    return None


EPISODE_BROLL_KEYWORDS_FILE = "broll_keywords.json"


def _apply_episode_broll_keywords(episode_path: Path, scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach producer-written search terms from ``broll_keywords.json`` to scene copies.

    The built-in keyword/query tables were written for earlier episodes and are
    picked by matching Thai words in the narration, so a new topic can silently
    inherit another episode's footage (or the lunar default). An episode file
    takes precedence over those tables::

        {"official_queries": [...], "official_markers": [...], "official_blocked": [...],
         "stock_default": [...], "stock_by_section": {"1": [...]}, "stock_by_asset_id": {"S01B00": [...]}}
    """
    path = episode_path / EPISODE_BROLL_KEYWORDS_FILE
    if not path.exists():
        return scenes
    config = json.loads(path.read_text(encoding="utf-8"))
    by_asset = config.get("stock_by_asset_id") or {}
    by_section = config.get("stock_by_section") or {}
    patched: list[dict[str, Any]] = []
    for scene in scenes:
        scene = dict(scene)
        keywords = (
            by_asset.get(_scene_asset_id(scene))
            or by_section.get(str(scene.get("section_index") or ""))
            or config.get("stock_default")
        )
        if keywords:
            scene["_episode_stock_keywords"] = [str(item) for item in keywords if str(item).strip()]
        if config.get("official_queries"):
            scene["_episode_official_queries"] = list(config["official_queries"])
            scene["_episode_official_markers"] = [str(m).lower() for m in config.get("official_markers") or []]
            scene["_episode_official_blocked"] = [str(m).lower() for m in config.get("official_blocked") or []]
        patched.append(scene)
    return patched


def _stock_keyword_pool(scene: dict[str, Any]) -> list[str]:
    if scene.get("_episode_stock_keywords"):
        return list(scene["_episode_stock_keywords"])
    text = " ".join(
        _clean_text(value)
        for value in (scene.get("section_title"), scene.get("scene_title"), scene.get("narration"))
    ).lower()
    asset_id = _scene_asset_id(scene)
    if any(
        token in text
        for token in (
            "hiroshimaite", "hiroshima", "ฮิโรชิมา", "atomic blast", "atomic airburst",
            "multicomponent alloy", "alau4", "p2₁3", "p213",
            "หลักฐานหนึ่งเม็ด", "ทรายที่ไม่ธรรมดา", "ไม่กี่วินาทีใน fireball",
            "อ่านอะตอมจากเกรนจิ๋ว", "ใหม่แค่ไหน", "ญาติไกลจาก trinity",
            "สิ่งที่เศษซากจำได้",
        )
    ):
        section_key = asset_id[:3]
        return list(HIROSHIMA_STOCK_KEYWORDS_BY_SECTION.get(section_key, []))
    if asset_id.startswith("VGR-"):
        return list(VOYAGER_STOCK_KEYWORDS_BY_ASSET_ID.get(asset_id, []))
    if any(token in text for token in ("denisovan", "denisova", "penghu", "โปรตีนโบราณ")):
        # These are atmospheres and real research contexts, never a synthetic
        # reconstruction standing in for an identified Denisovan individual.
        if any(token in text for token in ("dna", "โปรตีน", "peptide", "proteomics", "จีโนม")):
            return [
                "ancient DNA laboratory hands gloves",
                "archaeology laboratory bone analysis",
                "mass spectrometry laboratory close up",
                "scientist measuring fossil bone calipers",
            ]
        if any(token in text for token in ("penghu", "ไต้หวัน", "ชายฝั่ง", "ทะเล")):
            return [
                "Taiwan rocky coastline aerial",
                "coastal archaeology fieldwork",
                "Taiwan sea cliffs landscape",
                "fossil collection laboratory tray",
            ]
        if any(token in text for token in ("ทิเบต", "สูง", "epas1", "ออกซิเจน", "baishiya")):
            return [
                "Tibetan plateau mountain landscape",
                "high altitude mountain valley clouds",
                "mountain cave archaeology",
                "scientific fieldwork plateau",
            ]
        if any(token in text for token in ("อาหาร", "เนื้อ", "สัตว์", "ไขกระดูก", "หนัง")):
            return [
                "archaeological animal bones museum",
                "stone tool archaeology close up",
                "ice age steppe landscape",
                "mountain cave excavation",
            ]
        return [
            "archaeology cave excavation",
            "fossil bone laboratory tray",
            "scientist measuring fossil bone calipers",
            "ancient cave entrance mountain",
        ]
    if _is_volcano_scene(scene):
        return list(VOLCANO_STOCK_KEYWORDS_BY_ASSET_ID.get(asset_id, ["active volcano", "volcano monitoring"]))
    if _is_no_fire_scene(scene):
        return list(NO_FIRE_STOCK_KEYWORDS_BY_ASSET_ID.get(asset_id, []))
    contextual: list[str] = []
    if any(
        token in text
        for token in (
            "นอน",
            "หลับ",
            "ตื่น",
            "ห้องนอน",
            "เตียง",
            "ความทรงจำ",
            "ตัวตน",
            "ตัวคุณ",
            "สิบปีก่อน",
            "วัยเด็ก",
            "อดีต",
            "เมื่อวาน",
            "ร่างกาย",
            "พยาน",
            "เช้า",
            "คืน",
            "เงา",
            "ประตู",
            "เส้นด้าย",
            "sleep",
            "wake",
            "bed",
            "memory",
            "identity",
            "shadow",
            "room",
        )
    ):
        return [
            "person sleeping bedroom night",
            "person waking up bed morning",
            "empty bedroom night window",
            "alarm clock bedroom night",
            "old photographs table memory",
            "person writing journal night",
            "silhouette bedroom window",
            "person sitting on bed dawn",
            "empty room doorway night",
            "bedroom window rain night",
        ]
    if any(token in text for token in ("กรุงเทพ", "เมือง", "ไฟฟ้า", "แสงนีออน", "ป่าร้อนชื้น")):
        contextual.extend(["abandoned city jungle", "jungle ruins", "tropical urban jungle"])
    if any(token in text for token in ("กลางคืน", "พระอาทิตย์ตก", "สัตว์นักล่า", "ซ่อน", "เงียบ")):
        contextual.extend(["dark jungle night", "moonlit forest", "night forest"])
    if any(token in text for token in ("wonderwerk", "gesher", "โบราณคดี", "หลักฐาน", "ถ้ำ")):
        contextual.extend(["archaeology cave", "ancient cave", "stone age cave"])
    if any(token in text for token in ("อาหารดิบ", "รากไม้", "ผลไม้", "แมลง", "เคี้ยว", "ย่อย")):
        contextual.extend(["raw food forest", "foraging wild fruit", "hands preparing roots"])
    if any(token in text for token in ("homo raw", "กราม", "ฟัน", "ลำไส้", "ร่างกาย")):
        contextual.extend(["ancient human forest", "prehistoric human portrait", "stone age people forest"])
    if any(token in text for token in ("หนาว", "ยุโรปเหนือ", "เอเชียเหนือ", "แคนาดา", "หิมะ")):
        contextual.extend(["snow tundra winter", "frozen landscape", "ice age steppe"])
    if any(token in text for token in ("โลหะ", "หิน", "กระดูก", "เครื่องมือ", "ยุคหิน")):
        contextual.extend(["stone tools hands", "flint knapping", "primitive stone tools"])
    if any(token in text for token in ("ภาชนะ", "ตะกร้า", "เก็บอาหาร", "เพิง", "ชุมชน")):
        contextual.extend(["woven baskets forest", "temporary shelter forest", "hunter gatherer camp"])
    if any(token in text for token in ("นิทาน", "เล่าเรื่อง", "วัฒนธรรม", "ความเชื่อ", "วงล้อม")):
        contextual.extend(["dark forest clearing", "people sitting in shadows", "night forest clearing"])
    if any(token in text for token in ("มาม่า", "มือถือ", "หมูกระทะ", "โรงงาน", "กระทะ")):
        contextual.extend(["factory machinery", "smartphone close up", "noodles package production"])
    if contextual:
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in contextual:
            key = _clean_text(keyword).lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(keyword)
        return deduped
    if any(token in text for token in ("tidal", "tide", "น้ำขึ้น", "แรงดึง")):
        contextual.extend(["ocean tide waves", "sea waves moon night", "coastline waves night"])
    if any(token in text for token in ("laser", "retroreflector", "apollo", "วัดระยะ", "ทดลอง")):
        contextual.extend(["telescope moon night", "science laboratory dark", "observatory telescope stars"])
    if any(token in text for token in ("geolog", "ธรณี", "crater", "อดีต")):
        contextual.extend(["rocky desert crater", "moon crater telescope", "barren rocky landscape"])
    if any(token in text for token in ("future", "อนาคต", "ระยะยาว")):
        contextual.extend(["night sky moon timelapse", "earth from space", "stars space"])
    contextual.extend(
        [
            "moon night sky",
            "full moon clouds",
            "telescope moon",
            "night sky stars",
            "space stars",
            "ocean waves night",
            "scientist laboratory",
            "observatory telescope",
        ]
    )
    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in contextual:
        key = _clean_text(keyword).lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(keyword)
    return deduped


def _stock_keyword(scene: dict[str, Any], scene_index: int, slot_index: int) -> str:
    contextual = _stock_keyword_pool(scene)
    return contextual[(scene_index * 5 + slot_index) % len(contextual)] if contextual else ""


def _try_stock_video(
    *,
    episode_path: Path,
    scene: dict[str, Any],
    source: dict[str, Any],
    scene_index: int,
    slot_index: int,
    slot_duration: float,
    section_number: int,
    visual_usage: dict[str, dict[str, Any]],
    max_repeats: int,
    scene_visual_keys: set[str] | None = None,
    section_visual_keys: set[str] | None = None,
    last_visual_key: str = "",
) -> dict[str, Any] | None:
    context = " ".join(
        _clean_text(value)
        for value in (
            scene.get("scene_title"),
            scene.get("section_title"),
            scene.get("narration"),
        )
    )
    keywords = _stock_keyword_pool(scene)
    if not keywords:
        return None
    offset = (scene_index * 5 + slot_index) % len(keywords)
    ordered_keywords = keywords[offset:] + keywords[:offset]
    for keyword in ordered_keywords:
        providers = ("pexels", "pixabay") if (scene_index + slot_index) % 2 == 0 else ("pixabay", "pexels")
        for provider in providers:
            stock_key = _stock_visual_key(provider, keyword)
            if not _can_use_visual_key(
                stock_key,
                section_number=section_number,
                visual_usage=visual_usage,
                max_repeats=max_repeats,
                scene_visual_keys=scene_visual_keys,
                section_visual_keys=section_visual_keys,
                last_visual_key=last_visual_key,
            ):
                continue
            output_path = episode_path / f"scene_{scene_index:02d}_{slot_index}.mp4"
            asset_index = scene_index * 17 + slot_index * 3
            selection: dict[str, Any] = {}
            try:
                if provider == "pexels":
                    api_key = _config_value("pexels_api_key")
                    if not api_key:
                        continue
                    from pexels_provider import search_pexels_video

                    result = search_pexels_video(
                        f"{context} {keyword}",
                        api_key,
                        str(output_path),
                        max(5.0, slot_duration),
                        asset_index=asset_index,
                        keyword=keyword,
                        selection=selection,
                    )
                else:
                    api_key = _config_value("pixabay_api_key")
                    if not api_key:
                        continue
                    from pixabay_provider import search_pixabay_video

                    result = search_pixabay_video(
                        f"{context} {keyword}",
                        api_key,
                        str(output_path),
                        max(5.0, slot_duration),
                        asset_index=asset_index,
                        keyword=keyword,
                    )
            except Exception:  # noqa: BLE001
                result = None
            if result and Path(result).is_file() and Path(result).stat().st_size > 10_000:
                path = Path(result)
                return {
                    "asset_plan_id": f"{source.get('asset_plan_id') or f'SC{scene_index:02d}'}V{slot_index:02d}",
                    "scene_index": scene_index,
                    "asset_index": slot_index,
                    "scene_title": source.get("scene_title", "") or scene.get("scene_title", ""),
                    "provider": provider,
                    "media_type": "video",
                    "local_path": str(path),
                    "bytes": path.stat().st_size,
                    "status": "downloaded",
                    "timeline_role": STOCK_VIDEO_ROLE,
                    "slot_duration_seconds": slot_duration,
                    "source_url": selection.get("source_url") or (
                        f"https://www.pexels.com/search/videos/{quote_plus(keyword)}/"
                        if provider == "pexels"
                        else f"https://pixabay.com/videos/search/{quote_plus(keyword)}/"
                    ),
                    "download_url": selection.get("download_url") or str(path),
                    **({"credit": selection["credit"], "license_note": "Pexels License"} if selection.get("credit") else {}),
                    "prompt": f"{context} {keyword}",
                    "keyword": keyword,
                    "selected_reason": "Stock video b-roll added to avoid repeated still-image pacing.",
                    "generated_or_illustrative": False,
                    "derived_from_asset_plan_id": source.get("asset_plan_id"),
                    "derived_from_provider": source.get("provider"),
                    "visual_repeat_key": stock_key,
                    "accessed_date": _utc_now()[:10],
                }
    return None


def expand_broll_timeline(
    *,
    episode_dir: str | Path,
    script: list[Any],
    asset_manifest: dict[str, Any],
    tts_manifest: dict[str, Any] | None = None,
    target_seconds: float = 6.5,
    min_seconds: float = 5.0,
    max_seconds: float = 8.0,
    last_scene_extra_seconds: float = 0.0,
    fresh_official: bool = False,
    fresh_official_limit: int = 64,
    fresh_official_max_download_mb: int = 25,
    allow_stock: bool = False,
    stock_max_slots: int = 40,
    allow_runware: bool = False,
    runware_max_slots: int = 40,
    max_visual_repeats: int = 2,
    force: bool = False,
    legacy_keyword_tables: bool = False,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    if (allow_stock or fresh_official) and not legacy_keyword_tables             and not (episode_path / EPISODE_BROLL_KEYWORDS_FILE).exists():
        raise ValueError(
            f"{EPISODE_BROLL_KEYWORDS_FILE} is missing in {episode_path}; write episode search terms first "
            "(the built-in keyword tables belong to past episodes), or pass --legacy-keyword-tables "
            "to reproduce an older episode."
        )
    # Keep derived pacing assets away from approved scene anchors.  Earlier
    # versions wrote both to ``scene_XX_N.*`` in the episode root, so a slot-0
    # fallback could silently overwrite ``scene_XX_0.png`` and corrupt the
    # source manifest for every subsequent expansion.
    expanded_path = episode_path / "expanded_broll"
    expanded_path.mkdir(parents=True, exist_ok=True)
    scenes = _apply_episode_broll_keywords(
        episode_path, [scene for scene in script if isinstance(scene, dict)]
    )
    voyager_profile = _is_voyager_official_profile(scenes)
    fresh_official_per_scene_cap = (
        VOYAGER_MAX_FRESH_OFFICIAL_PER_SCENE
        if voyager_profile
        else MAX_FRESH_OFFICIAL_PER_SCENE
    )
    fresh_official_per_section_cap = (
        VOYAGER_MAX_FRESH_OFFICIAL_PER_SECTION
        if voyager_profile
        else MAX_FRESH_OFFICIAL_PER_SECTION
    )
    original_entries = [
        entry
        for entry in (
            asset_manifest.get("entries", [])
            if isinstance(asset_manifest.get("entries"), list)
            else []
        )
        if isinstance(entry, dict)
    ]
    sources = _base_sources(original_entries)
    durations = _scene_durations(
        episode_dir=episode_path,
        script=scenes,
        tts_manifest=tts_manifest,
    )
    if durations and last_scene_extra_seconds > 0:
        durations[-1] = round(durations[-1] + last_scene_extra_seconds, 3)
    planned_slot_count = sum(
        _slot_count(duration, target_seconds, min_seconds, max_seconds)
        for duration in durations[: len(scenes)]
    )
    warnings: list[str] = [
        str(warning)
        for warning in (asset_manifest.get("warnings", []) or [])
        if "visual repeat guard violations detected" not in str(warning)
    ]
    errors: list[str] = []
    expanded_entries: list[dict[str, Any]] = []
    timeline_scenes: list[dict[str, Any]] = []
    existing_fresh_candidates = _existing_fresh_candidates(original_entries)
    searched_fresh_candidates, fresh_warnings = _fresh_official_candidates(
        scenes=scenes,
        limit=max(0, int(fresh_official_limit)),
        search=fresh_official,
    )
    fresh_candidates: list[dict[str, Any]] = []
    seen_fresh_keys: set[str] = set()
    for candidate in existing_fresh_candidates + searched_fresh_candidates:
        visual_key = _fresh_visual_key(candidate)
        if not visual_key or visual_key in seen_fresh_keys:
            continue
        seen_fresh_keys.add(visual_key)
        fresh_candidates.append(candidate)
    warnings.extend(fresh_warnings)
    if fresh_official and not fresh_candidates:
        warnings.append("fresh official b-roll search returned no usable image candidates")
    used_fresh_urls: set[str] = set()
    fresh_download_count = 0
    fresh_download_fail_count = 0
    section_fresh_counts: dict[int, int] = {}
    max_fresh_bytes = max(1, int(fresh_official_max_download_mb)) * 1024 * 1024
    max_repeats = max(1, int(max_visual_repeats))
    visual_usage: dict[str, dict[str, Any]] = {}
    section_image_fingerprints_by_section: dict[int, list[dict[str, Any]]] = {}
    global_image_fingerprints: list[dict[str, Any]] = []
    repeat_guard_fallback_count = 0
    local_graphic_count = 0
    stock_video_count = 0
    stock_video_fail_count = 0
    stock_slot_cap = max(0, int(stock_max_slots))
    runware_image_count = 0
    runware_image_fail_count = 0
    runware_slot_cap = max(0, int(runware_max_slots))
    last_visual_key = ""
    section_visual_keys_by_section: dict[int, set[str]] = {}
    policy_entries: list[dict[str, Any]] = []

    def policy_can_add(provider: str, *, timeline_role: str = "", media_type: str = "image") -> bool:
        return can_add_visual_entry(
            policy_entries,
            {
                "provider": provider,
                "timeline_role": timeline_role,
                "media_type": media_type,
            },
            planned_total_count=planned_slot_count,
        )

    def policy_blocked_entry(
        *,
        source: dict[str, Any],
        scene: dict[str, Any],
        scene_index: int,
        slot_index: int,
        slot_duration: float,
        provider: str,
        category: str,
    ) -> dict[str, Any]:
        entry = _entry_for_policy_blocked(
            source=source,
            scene=scene,
            scene_index=scene_index,
            slot_index=slot_index,
            slot_duration=slot_duration,
            provider=provider,
            category=category,
            planned_total_count=planned_slot_count,
        )
        errors.append(str(entry.get("issue") or "visual source policy blocked fallback"))
        return entry

    for scene_index, scene in enumerate(scenes):
        duration = durations[scene_index] if scene_index < len(durations) else 0.0
        count = _slot_count(duration, target_seconds, min_seconds, max_seconds)
        slot_durations = _slot_durations(duration, count)
        scene_asset_id = str(scene.get("producer_asset_plan_id") or "")
        scene_key = scene_asset_id[:3] if scene_asset_id.startswith("S") else ""
        section_number = _scene_section_number(scene, scene_index)
        slots: list[dict[str, Any]] = []
        scene_visual_keys: set[str] = set()
        section_visual_keys = section_visual_keys_by_section.setdefault(section_number, set())
        section_image_fingerprints = section_image_fingerprints_by_section.setdefault(
            section_number, []
        )
        scene_fresh_count = 0
        # Every narration beat has an approved anchor asset.  When no *other*
        # source survives the repeat guard, keep using that anchor as a distinct
        # crop/reframe candidate instead of falling through to an unrelated
        # local graphic.  The derived entry retains the original provenance.
        anchor_source = _select_source(
            scene_index=scene_index,
            slot_index=0,
            scene_key=scene_key,
            source_entries=sources,
        )

        for slot_index, slot_duration in enumerate(slot_durations):
            # A beat's approved anchor remains the relevant source for its
            # pacing crops.  Borrowing a past beat's asset here is both less
            # relevant and makes fingerprint matching turn valid reframes into
            # arbitrary local-graphic fallbacks.
            source = anchor_source
            if not source:
                source = {
                    "asset_plan_id": scene_asset_id or f"SC{scene_index:02d}",
                    "scene_index": scene_index,
                    "scene_title": scene.get("scene_title", ""),
                    "provider": "local_graphic_seed",
                    "prompt": scene.get("scene_title", ""),
                }
            source_path = Path(str(source.get("local_path") or ""))
            if slot_index == 0:
                visual_key = _source_visual_key(source)
                output_path = Path(str(source.get("local_path") or ""))
                if not output_path.is_absolute():
                    output_path = Path.cwd() / output_path
                candidate_fingerprint = _image_fingerprint(output_path)
                if (
                    output_path.is_file()
                    and output_path.stat().st_size > 1024
                    and _can_use_visual_key(
                    visual_key,
                    section_number=section_number,
                    visual_usage=visual_usage,
                    max_repeats=max_repeats,
                    scene_visual_keys=scene_visual_keys,
                    section_visual_keys=section_visual_keys,
                    last_visual_key=last_visual_key,
                    )
                ):
                    entry = _entry_for_original(
                        source=source,
                        scene_index=scene_index,
                        slot_index=slot_index,
                        slot_duration=slot_duration,
                    )
                    output_path = Path(str(entry.get("local_path") or source_path))
                    bytes_written = output_path.stat().st_size if output_path.exists() else 0
                    entry["visual_repeat_key"] = visual_key
                    entry["visual_repeat_count"] = _record_visual_key(
                        visual_key,
                        section_number=section_number,
                        visual_usage=visual_usage,
                    )
                    scene_visual_keys.add(visual_key)
                    section_visual_keys.add(visual_key)
                    if candidate_fingerprint:
                        section_image_fingerprints.append(candidate_fingerprint)
                        global_image_fingerprints.append(candidate_fingerprint)
                    last_visual_key = visual_key
                else:
                    entry = None
                    if (
                        allow_runware
                        and runware_image_count < runware_slot_cap
                        and _allow_runware_for_scene(scene, source)
                        and policy_can_add(
                            RUNWARE_BROLL_PROVIDER,
                            timeline_role=GENERATED_IMAGE_ROLE,
                        )
                    ):
                        entry = _try_runware_broll(
                            episode_path=expanded_path,
                            scene=scene,
                            source=source,
                            scene_index=scene_index,
                            slot_index=slot_index,
                            slot_duration=slot_duration,
                            allow_runware=allow_runware,
                        )
                        if entry:
                            runware_image_count += 1
                        else:
                            runware_image_fail_count += 1
                    if entry:
                        output_path = Path(str(entry.get("local_path")))
                        bytes_written = int(entry.get("bytes") or output_path.stat().st_size)
                        replacement_key = f"{RUNWARE_BROLL_PROVIDER}:{entry.get('asset_plan_id')}"
                    else:
                        output_path = (
                            source_path
                            if source_path.suffix.lower() in IMAGE_EXTENSIONS
                            else expanded_path / f"scene_{scene_index:02d}_0.jpg"
                        )
                        if policy_can_add(
                            LOCAL_GRAPHIC_PROVIDER,
                            timeline_role=LOCAL_GRAPHIC_PROVIDER,
                        ):
                            bytes_written = _render_local_graphic(
                                output_path,
                                scene_index=scene_index,
                                slot_index=slot_index,
                                scene=scene,
                                source=source,
                            )
                            entry = _entry_for_local_graphic(
                                source=source,
                                scene=scene,
                                scene_index=scene_index,
                                slot_index=slot_index,
                                slot_duration=slot_duration,
                                output_path=output_path,
                                bytes_written=bytes_written,
                            )
                            replacement_key = f"{LOCAL_GRAPHIC_PROVIDER}:{output_path.name.lower()}"
                            local_graphic_count += 1
                        else:
                            output_path = expanded_path / f"scene_{scene_index:02d}_{slot_index}_policy_blocked.png"
                            bytes_written = 0
                            entry = policy_blocked_entry(
                                source=source,
                                scene=scene,
                                scene_index=scene_index,
                                slot_index=slot_index,
                                slot_duration=slot_duration,
                                provider=LOCAL_GRAPHIC_PROVIDER,
                                category="graphic",
                            )
                            replacement_key = f"policy_blocked:{entry.get('asset_plan_id')}"
                    entry["visual_repeat_key"] = replacement_key
                    entry["visual_repeat_count"] = _record_visual_key(
                        replacement_key,
                        section_number=section_number,
                        visual_usage=visual_usage,
                    )
                    scene_visual_keys.add(replacement_key)
                    section_visual_keys.add(replacement_key)
                    replacement_fingerprint = _image_fingerprint(output_path)
                    if replacement_fingerprint:
                        section_image_fingerprints.append(replacement_fingerprint)
                        global_image_fingerprints.append(replacement_fingerprint)
                    last_visual_key = replacement_key
                    repeat_guard_fallback_count += 1
            else:
                output_path = expanded_path / f"scene_{scene_index:02d}_{slot_index}.jpg"
                entry = None
                bytes_written = 0
                rejected_fresh: set[str] = set()
                while (
                    scene_fresh_count < fresh_official_per_scene_cap
                    and section_fresh_counts.get(section_number, 0) < fresh_official_per_section_cap
                ):
                    fresh_candidate = _select_fresh_official(
                        scene=scene,
                        scene_index=scene_index,
                        slot_index=slot_index,
                        section_number=section_number,
                        candidates=fresh_candidates,
                        visual_usage=visual_usage,
                        max_repeats=max_repeats,
                        scene_visual_keys=scene_visual_keys,
                        section_visual_keys=section_visual_keys,
                        last_visual_key=last_visual_key,
                        exclude_keys=rejected_fresh,
                    )
                    if not fresh_candidate:
                        break
                    fresh_key = _fresh_visual_key(fresh_candidate)
                    candidate_local_path = Path(str(fresh_candidate.get("local_path") or ""))
                    temp_download = (
                        candidate_local_path
                        if candidate_local_path.is_file() and candidate_local_path.stat().st_size > 1024
                        else _download_temp_image(
                            str(fresh_candidate.get("fresh_image_url") or ""),
                            max_bytes=max_fresh_bytes,
                        )
                    )
                    should_cleanup_temp = temp_download is not None and temp_download != candidate_local_path
                    if not temp_download:
                        fresh_download_fail_count += 1
                        rejected_fresh.add(fresh_key)
                        continue
                    try:
                        bytes_written = _render_reframe(
                            temp_download,
                            output_path,
                            scene_index=scene_index,
                            slot_index=slot_index,
                        )
                        candidate_fingerprint = _image_fingerprint(output_path)
                        is_anchor_reframe = (
                            str(source.get("asset_plan_id") or "")
                            == str(anchor_source.get("asset_plan_id") or "")
                        )
                        if not is_anchor_reframe and _is_similar_image_fingerprint(
                            candidate_fingerprint,
                            global_image_fingerprints,
                        ):
                            rejected_fresh.add(fresh_key)
                            continue
                        entry = _entry_for_fresh_official(
                            candidate=fresh_candidate,
                            source=source,
                            scene_index=scene_index,
                            slot_index=slot_index,
                            slot_duration=slot_duration,
                            output_path=output_path,
                            bytes_written=bytes_written,
                        )
                        entry["visual_repeat_key"] = fresh_key
                        entry["visual_repeat_count"] = _record_visual_key(
                            fresh_key,
                            section_number=section_number,
                            visual_usage=visual_usage,
                        )
                        scene_visual_keys.add(fresh_key)
                        section_visual_keys.add(fresh_key)
                        if candidate_fingerprint:
                            section_image_fingerprints.append(candidate_fingerprint)
                            global_image_fingerprints.append(candidate_fingerprint)
                        last_visual_key = fresh_key
                        used_fresh_urls.add(fresh_key)
                        fresh_download_count += 1
                        scene_fresh_count += 1
                        section_fresh_counts[section_number] = (
                            section_fresh_counts.get(section_number, 0) + 1
                        )
                        break
                    finally:
                        if should_cleanup_temp:
                            try:
                                temp_download.unlink(missing_ok=True)
                            except OSError:
                                pass

                if entry is None and source_path.is_file():
                    stock_entry = None
                    if allow_stock and stock_video_count < stock_slot_cap:
                        stock_entry = _try_stock_video(
                            episode_path=expanded_path,
                            scene=scene,
                            source=source,
                            scene_index=scene_index,
                            slot_index=slot_index,
                            slot_duration=slot_duration,
                            section_number=section_number,
                            visual_usage=visual_usage,
                            max_repeats=max_repeats,
                            scene_visual_keys=scene_visual_keys,
                            section_visual_keys=section_visual_keys,
                            last_visual_key=last_visual_key,
                        )
                    if stock_entry:
                        entry = stock_entry
                        output_path = Path(str(entry.get("local_path")))
                        bytes_written = int(entry.get("bytes") or output_path.stat().st_size)
                        visual_key = str(entry.get("visual_repeat_key") or output_path.name.lower())
                        entry["visual_repeat_count"] = _record_visual_key(
                            visual_key,
                            section_number=section_number,
                            visual_usage=visual_usage,
                        )
                        scene_visual_keys.add(visual_key)
                        section_visual_keys.add(visual_key)
                        stock_fingerprint = _image_fingerprint(output_path)
                        if stock_fingerprint:
                            section_image_fingerprints.append(stock_fingerprint)
                            global_image_fingerprints.append(stock_fingerprint)
                        last_visual_key = visual_key
                        stock_video_count += 1
                    else:
                        if allow_stock and stock_video_count < stock_slot_cap:
                            stock_video_fail_count += 1
                        if output_path.exists() and output_path.stat().st_size > 1024 and not force:
                            bytes_written = output_path.stat().st_size
                        else:
                            bytes_written = _render_reframe(
                                source_path,
                                output_path,
                                scene_index=scene_index,
                                slot_index=slot_index,
                        )
                        visual_key = _source_visual_key(source)
                        candidate_fingerprint = _image_fingerprint(output_path)
                        is_anchor_reframe = (
                            str(source.get("asset_plan_id") or "")
                            == str(anchor_source.get("asset_plan_id") or "")
                        )
                        if not is_anchor_reframe and _is_similar_image_fingerprint(
                            candidate_fingerprint,
                            global_image_fingerprints,
                        ):
                            entry = None
                            if (
                                allow_runware
                                and runware_image_count < runware_slot_cap
                                and _allow_runware_for_scene(scene, source)
                                and policy_can_add(
                                    RUNWARE_BROLL_PROVIDER,
                                    timeline_role=GENERATED_IMAGE_ROLE,
                                )
                            ):
                                entry = _try_runware_broll(
                                    episode_path=expanded_path,
                                    scene=scene,
                                    source=source,
                                    scene_index=scene_index,
                                    slot_index=slot_index,
                                    slot_duration=slot_duration,
                                    allow_runware=allow_runware,
                                )
                                if entry:
                                    output_path = Path(str(entry.get("local_path")))
                                    bytes_written = int(entry.get("bytes") or output_path.stat().st_size)
                                    visual_key = f"{RUNWARE_BROLL_PROVIDER}:{entry.get('asset_plan_id')}"
                                    runware_image_count += 1
                                else:
                                    runware_image_fail_count += 1
                            if entry is None:
                                if policy_can_add(
                                    LOCAL_GRAPHIC_PROVIDER,
                                    timeline_role=LOCAL_GRAPHIC_PROVIDER,
                                ):
                                    bytes_written = _render_local_graphic(
                                        output_path,
                                        scene_index=scene_index,
                                        slot_index=slot_index,
                                        scene=scene,
                                        source=source,
                                    )
                                    entry = _entry_for_local_graphic(
                                        source=source,
                                        scene=scene,
                                        scene_index=scene_index,
                                        slot_index=slot_index,
                                        slot_duration=slot_duration,
                                        output_path=output_path,
                                        bytes_written=bytes_written,
                                    )
                                    visual_key = f"{LOCAL_GRAPHIC_PROVIDER}:{output_path.name.lower()}"
                                    local_graphic_count += 1
                                else:
                                    output_path = expanded_path / f"scene_{scene_index:02d}_{slot_index}_policy_blocked.png"
                                    bytes_written = 0
                                    entry = policy_blocked_entry(
                                        source=source,
                                        scene=scene,
                                        scene_index=scene_index,
                                        slot_index=slot_index,
                                        slot_duration=slot_duration,
                                        provider=LOCAL_GRAPHIC_PROVIDER,
                                        category="graphic",
                                    )
                                    visual_key = f"policy_blocked:{entry.get('asset_plan_id')}"
                        else:
                            entry = _entry_for_reframe(
                                source=source,
                                scene_index=scene_index,
                                slot_index=slot_index,
                                slot_duration=slot_duration,
                                output_path=output_path,
                                bytes_written=bytes_written,
                            )
                            if is_anchor_reframe:
                                visual_key = (
                                    f"reframe:{_source_visual_key(source)}:"
                                    f"{scene_index}:{slot_index}"
                                )
                        entry["visual_repeat_key"] = visual_key
                        entry["visual_repeat_count"] = _record_visual_key(
                            visual_key,
                            section_number=section_number,
                            visual_usage=visual_usage,
                        )
                        scene_visual_keys.add(visual_key)
                        section_visual_keys.add(visual_key)
                        candidate_fingerprint = _image_fingerprint(output_path)
                        if candidate_fingerprint:
                            section_image_fingerprints.append(candidate_fingerprint)
                            global_image_fingerprints.append(candidate_fingerprint)
                        last_visual_key = visual_key
                        repeat_guard_fallback_count += 1

                if entry is None:
                    stock_entry = None
                    if allow_stock and stock_video_count < stock_slot_cap:
                        stock_entry = _try_stock_video(
                            episode_path=expanded_path,
                            scene=scene,
                            source=source,
                            scene_index=scene_index,
                            slot_index=slot_index,
                            slot_duration=slot_duration,
                            section_number=section_number,
                            visual_usage=visual_usage,
                            max_repeats=max_repeats,
                            scene_visual_keys=scene_visual_keys,
                            section_visual_keys=section_visual_keys,
                            last_visual_key=last_visual_key,
                        )
                    if stock_entry:
                        entry = stock_entry
                        output_path = Path(str(entry.get("local_path")))
                        bytes_written = int(entry.get("bytes") or output_path.stat().st_size)
                        visual_key = str(entry.get("visual_repeat_key") or output_path.name.lower())
                        entry["visual_repeat_count"] = _record_visual_key(
                            visual_key,
                            section_number=section_number,
                            visual_usage=visual_usage,
                        )
                        scene_visual_keys.add(visual_key)
                        section_visual_keys.add(visual_key)
                        stock_fingerprint = _image_fingerprint(output_path)
                        if stock_fingerprint:
                            section_image_fingerprints.append(stock_fingerprint)
                            global_image_fingerprints.append(stock_fingerprint)
                        last_visual_key = visual_key
                        stock_video_count += 1
                    else:
                        if allow_stock and stock_video_count < stock_slot_cap:
                            stock_video_fail_count += 1
                        if (
                            allow_runware
                            and runware_image_count < runware_slot_cap
                            and _allow_runware_for_scene(scene, source)
                            and policy_can_add(
                                RUNWARE_BROLL_PROVIDER,
                                timeline_role=GENERATED_IMAGE_ROLE,
                            )
                        ):
                            entry = _try_runware_broll(
                                episode_path=expanded_path,
                                scene=scene,
                                source=source,
                                scene_index=scene_index,
                                slot_index=slot_index,
                                slot_duration=slot_duration,
                                allow_runware=allow_runware,
                            )
                            if entry:
                                output_path = Path(str(entry.get("local_path")))
                                bytes_written = int(entry.get("bytes") or output_path.stat().st_size)
                                visual_key = f"{RUNWARE_BROLL_PROVIDER}:{entry.get('asset_plan_id')}"
                                runware_image_count += 1
                            else:
                                runware_image_fail_count += 1
                        if entry is None:
                            if policy_can_add(
                                LOCAL_GRAPHIC_PROVIDER,
                                timeline_role=LOCAL_GRAPHIC_PROVIDER,
                            ):
                                bytes_written = _render_local_graphic(
                                    output_path,
                                    scene_index=scene_index,
                                    slot_index=slot_index,
                                    scene=scene,
                                    source=source,
                                )
                                entry = _entry_for_local_graphic(
                                    source=source,
                                    scene=scene,
                                    scene_index=scene_index,
                                    slot_index=slot_index,
                                    slot_duration=slot_duration,
                                    output_path=output_path,
                                    bytes_written=bytes_written,
                                )
                                visual_key = f"{LOCAL_GRAPHIC_PROVIDER}:{output_path.name.lower()}"
                                local_graphic_count += 1
                            else:
                                output_path = expanded_path / f"scene_{scene_index:02d}_{slot_index}_policy_blocked.png"
                                bytes_written = 0
                                entry = policy_blocked_entry(
                                    source=source,
                                    scene=scene,
                                    scene_index=scene_index,
                                    slot_index=slot_index,
                                    slot_duration=slot_duration,
                                    provider=LOCAL_GRAPHIC_PROVIDER,
                                    category="graphic",
                                )
                                visual_key = f"policy_blocked:{entry.get('asset_plan_id')}"
                        entry["visual_repeat_key"] = visual_key
                        entry["visual_repeat_count"] = _record_visual_key(
                            visual_key,
                            section_number=section_number,
                            visual_usage=visual_usage,
                        )
                        scene_visual_keys.add(visual_key)
                        section_visual_keys.add(visual_key)
                        local_fingerprint = _image_fingerprint(output_path)
                        if local_fingerprint:
                            section_image_fingerprints.append(local_fingerprint)
                            global_image_fingerprints.append(local_fingerprint)
                        last_visual_key = visual_key
                        repeat_guard_fallback_count += 1
            policy_entries.append(entry)
            expanded_entries.append(entry)
            slots.append(
                {
                    "scene_index": scene_index,
                    "asset_index": slot_index,
                    "duration_seconds": slot_duration,
                    "local_path": str(output_path),
                    "source_asset_plan_id": source.get("asset_plan_id"),
                    "source_provider": source.get("provider"),
                    "provider": entry.get("provider"),
                    "timeline_role": entry.get("timeline_role"),
                    "visual_repeat_key": entry.get("visual_repeat_key"),
                    "visual_repeat_count": entry.get("visual_repeat_count"),
                    "bytes": bytes_written,
                }
            )

        timeline_scenes.append(
            {
                "scene_index": scene_index,
                "section_number": section_number,
                "scene_title": scene.get("scene_title", ""),
                "duration_seconds": round(duration, 3),
                "asset_count": len(slots),
                "slot_duration_seconds": slot_durations,
                "slots": slots,
            }
        )

    provider_counts: dict[str, int] = {}
    for entry in expanded_entries:
        provider = str(entry.get("provider") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
    policy_report = visual_policy_report(expanded_entries)
    policy_messages = policy_warnings(policy_report)
    policy_review_messages = policy_review_warnings(policy_report)
    warnings.extend(policy_messages)
    warnings.extend(policy_review_messages)
    if policy_report.get("status") == "blocked":
        errors.extend(policy_messages)
    elif policy_report.get("status") == "review":
        status = "review"
    else:
        status = "complete"
    if errors:
        status = "blocked"
    repeat_violations = []
    for visual_key, state in visual_usage.items():
        count = int(state.get("count", 0) or 0)
        sections = sorted(int(section) for section in (state.get("sections", set()) or set()))
        has_adjacent_sections = any(
            abs(sections[index] - sections[index - 1]) == 1 for index in range(1, len(sections))
        )
        if count > max_repeats or has_adjacent_sections:
            repeat_violations.append(
                {
                    "visual_key": visual_key,
                    "count": count,
                    "sections": sections,
                    "has_adjacent_sections": has_adjacent_sections,
                }
            )
    if repeat_violations:
        warnings.append(f"{len(repeat_violations)} visual repeat guard violations detected")
    repeat_guard = {
        "max_repeats_per_visual": max_repeats,
        "no_adjacent_sections": True,
        "no_consecutive_reuse": True,
        "no_same_scene_reuse": True,
        "no_same_section_reuse": True,
        "visual_key_strategy": "normalized-title, source-url fallback, stock-provider-keyword",
        "unique_visual_count": len(visual_usage),
        "max_observed_repeats": max(
            [int(state.get("count", 0) or 0) for state in visual_usage.values()] or [0]
        ),
        "violation_count": len(repeat_violations),
        "violations": repeat_violations[:20],
        "fallback_count": repeat_guard_fallback_count,
    }

    manifest = dict(asset_manifest)
    manifest["stage"] = "asset_production_expanded_broll"
    manifest["status"] = status
    manifest["updated_at"] = _utc_now()
    manifest["entries"] = expanded_entries
    manifest["warnings"] = warnings
    manifest["broll_expansion"] = {
        "created_at": _utc_now(),
        "target_seconds": target_seconds,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "last_scene_extra_seconds": last_scene_extra_seconds,
        "scene_count": len(timeline_scenes),
        "asset_count": len(expanded_entries),
        "source_asset_count": len(sources),
        "derived_asset_count": sum(1 for entry in expanded_entries if entry.get("provider") == LOCAL_REFRAME_PROVIDER),
        "local_graphic_count": local_graphic_count,
        "stock_video_enabled": allow_stock,
        "stock_video_count": stock_video_count,
        "stock_video_fail_count": stock_video_fail_count,
        "stock_video_slot_cap": stock_slot_cap,
        "runware_broll_enabled": allow_runware,
        "runware_broll_count": runware_image_count,
        "runware_broll_fail_count": runware_image_fail_count,
        "runware_broll_slot_cap": runware_slot_cap,
        "fresh_official_enabled": fresh_official,
        "existing_fresh_candidate_count": len(existing_fresh_candidates),
        "fresh_official_candidate_count": len(fresh_candidates),
        "fresh_official_download_count": fresh_download_count,
        "fresh_official_download_fail_count": fresh_download_fail_count,
        "fresh_official_per_scene_cap": fresh_official_per_scene_cap,
        "fresh_official_per_section_cap": fresh_official_per_section_cap,
        "repeat_guard": repeat_guard,
        "visual_policy": policy_report,
        "provider_counts": provider_counts,
    }

    timeline = {
        "schema_version": BROLL_TIMELINE_VERSION,
        "stage": "broll_timeline",
        "created_at": _utc_now(),
        "status": status,
        "episode_dir": str(episode_path),
        "target_seconds": target_seconds,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "last_scene_extra_seconds": last_scene_extra_seconds,
        "scene_count": len(timeline_scenes),
        "asset_count": len(expanded_entries),
        "source_asset_count": len(sources),
        "derived_asset_count": sum(1 for entry in expanded_entries if entry.get("provider") == LOCAL_REFRAME_PROVIDER),
        "local_graphic_count": local_graphic_count,
        "stock_video_enabled": allow_stock,
        "stock_video_count": stock_video_count,
        "stock_video_fail_count": stock_video_fail_count,
        "stock_video_slot_cap": stock_slot_cap,
        "runware_broll_enabled": allow_runware,
        "runware_broll_count": runware_image_count,
        "runware_broll_fail_count": runware_image_fail_count,
        "runware_broll_slot_cap": runware_slot_cap,
        "fresh_official_enabled": fresh_official,
        "existing_fresh_candidate_count": len(existing_fresh_candidates),
        "fresh_official_candidate_count": len(fresh_candidates),
        "fresh_official_download_count": fresh_download_count,
        "fresh_official_download_fail_count": fresh_download_fail_count,
        "fresh_official_per_scene_cap": fresh_official_per_scene_cap,
        "fresh_official_per_section_cap": fresh_official_per_section_cap,
        "repeat_guard": repeat_guard,
        "visual_policy": policy_report,
        "provider_counts": provider_counts,
        "scenes": timeline_scenes,
        "warnings": warnings,
        "errors": errors,
    }

    return {
        "asset_manifest": manifest,
        "broll_timeline": timeline,
    }
