"""
visual_planner.py - deterministic visual planning for PodcastV2 assets.

The planner creates an inspectable visual_plan.json before secondary visual
assets are generated. It keeps stock-search keywords separate from AI image
prompts so chart/diagram-heavy image prompts no longer suppress stock search.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone


VISUAL_PLAN_VERSION = 1
VISUAL_PLAN_FILENAME = "visual_plan.json"
STOCK_QUERY_REPORT_FILENAME = "stock_query_report.json"


_STYLE_PREFIX_RE = re.compile(r"^scene-faithful documentary still,.*?--\s*", flags=re.I | re.S)

_BOILERPLATE_WORDS = {
    "scene", "faithful", "documentary", "still", "natural", "grounded",
    "composition", "concrete", "subject", "setting", "narration", "beat",
    "realistic", "physical", "texture", "frame", "wide", "angle", "view",
    "visual", "supporting", "moment", "scale", "camera", "distance",
    "effects", "logos", "text", "overlay", "title", "section", "asset",
    "clean", "style", "lighting", "background", "foreground",
}

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "are",
    "but", "not", "you", "your", "can", "will", "would", "could", "one",
    "two", "three", "there", "their", "they", "them", "was", "were",
}

_GENERIC_WORDS = {
    "science", "technology", "hypothesis", "giant", "subscribe",
    "documentary", "cinematic", "data", "future", "premium",
}

_KEYWORD_RULES: list[tuple[tuple[str, ...], list[str], str]] = [
    (
        ("starlink", "internet", "satellite internet", "ground station", "telecom", "receiver", "antenna"),
        ["satellite orbit", "ground station antenna", "space technology"],
        "orbital_network",
    ),
    (
        ("rocket", "falcon", "launch pad", "launch provider", "spacex", "electron", "blue origin", "new shepard"),
        ["rocket launch", "space rocket launch", "launch pad"],
        "launch_hardware",
    ),
    (
        ("space station", "international space station", "iss", "axiom", "orbital mission", "astronaut"),
        ["space station", "astronaut space station", "astronaut training"],
        "human_spaceflight",
    ),
    (
        ("asteroid", "psyche", "mining", "platinum", "metallic", "mineral", "robotic arm"),
        ["asteroid space", "spacecraft close up", "rocky planet surface"],
        "space_mining",
    ),
    (
        ("microgravity", "crystal", "pharmaceutical", "drug", "medicine", "vial", "laboratory", "lab"),
        ["laboratory scientist", "pharmaceutical laboratory", "crystal laboratory"],
        "space_biotech",
    ),
    (
        ("stock", "market", "etf", "investor", "portfolio", "financial", "economy", "revenue", "dollar", "spreadsheet"),
        ["stock market chart", "financial analyst", "business finance city"],
        "market_reality",
    ),
    (
        ("capsule", "re-entry", "reentry", "utah", "desert", "landing", "parachute", "varda"),
        ["space capsule desert", "desert capsule", "spacecraft landing"],
        "space_capsule",
    ),
    (
        ("factory", "manufacturing", "production", "industrial", "workshop"),
        ["factory laboratory", "manufacturing technology", "industrial laboratory"],
        "orbital_factory",
    ),
    (
        ("earth", "orbit", "planet", "space", "horizon"),
        ["earth from space", "satellite orbit", "space technology"],
        "space_context",
    ),
    (
        ("moon", "lunar", "apollo"),
        ["moon night sky", "moon surface", "lunar landscape"],
        "lunar",
    ),
    (
        ("mars",),
        ["mars planet space", "mars landscape", "red planet"],
        "mars",
    ),
    (
        ("office", "worker", "career", "company", "desk", "report"),
        ["modern office workers", "business office", "financial analyst"],
        "workplace",
    ),
    (
        ("forest", "trees", "rocky landscape", "cliff", "horizon"),
        ["wide landscape nature", "rocky landscape", "mountain landscape"],
        "landscape",
    ),
]

_ROLE_DIRECTIONS = {
    "object_closeup": (
        "Create a close documentary view of one concrete object, instrument, "
        "surface, material, or piece of hardware from this beat."
    ),
    "process_detail": (
        "Show the physical process or evidence in action, with a clear subject "
        "and no infographic labels."
    ),
    "environment_wide": (
        "Create a wider setting shot that establishes place, scale, and context "
        "without becoming a generic landscape."
    ),
    "human_context": (
        "Use a human-scale documentary anchor such as a lab bench, analyst desk, "
        "control room, observatory, or worker interacting with real objects."
    ),
    "texture_insert": (
        "Create a material or atmospheric insert that feels specific to the beat: "
        "metal, crystal, rock, spacecraft surface, market documents, or instrument detail."
    ),
}

_FAMILY_AVOIDS = {
    "orbital_network": ["generic Earth horizon", "random night sky", "unbranded white astronaut"],
    "launch_hardware": ["generic Earth horizon", "office desk", "abstract galaxy"],
    "human_spaceflight": ["generic rocket launch", "celebrity likeness", "tourism poster"],
    "space_mining": ["office desk", "generic galaxy", "Earth horizon as the main subject"],
    "space_biotech": ["generic microscope only", "random space backdrop", "readable brand labels"],
    "market_reality": ["rocket launch as default", "generic business handshake", "fake readable logos"],
    "space_capsule": ["generic Mars surface", "city skyline", "unrelated laboratory"],
    "orbital_factory": ["generic factory smoke", "unrelated car assembly line", "brand logos"],
    "space_context": ["same Earth horizon repeatedly", "empty star field only", "generic galaxy"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_text(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _strip_style_prefix(prompt: str) -> str:
    text = str(prompt or "").strip()
    text = _STYLE_PREFIX_RE.sub("", text).strip()
    if " -- " in text:
        text = text.split(" -- ", 1)[1].strip()
    return text


def _keyword(value: str) -> str:
    text = re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()[:60]


def _unique(items: list[str], limit: int = 3) -> list[str]:
    seen = set()
    output = []
    for item in items:
        clean = _keyword(item)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        output.append(clean)
        if len(output) >= limit:
            break
    return output


def _first_ascii_phrase(text: str, max_words: int = 3) -> str:
    words = re.findall(r"\b[a-z][a-z0-9]{2,}\b", str(text or "").lower())
    useful = [
        word for word in words
        if word not in _STOPWORDS and word not in _BOILERPLATE_WORDS and word not in _GENERIC_WORDS
    ]
    if len(useful) < 2:
        return ""
    return " ".join(useful[:max_words])


def _scene_text(scene: dict, narration_chunk: str) -> str:
    return "\n".join(
        str(part or "")
        for part in (
            scene.get("scene_title", ""),
            scene.get("section_title", ""),
            _strip_style_prefix(scene.get("image_prompt", "")),
            narration_chunk,
        )
    )


def _needle_matches(text: str, needle: str) -> bool:
    clean = str(needle or "").lower().strip()
    if not clean:
        return False
    if re.fullmatch(r"[a-z0-9]+", clean):
        return re.search(rf"\b{re.escape(clean)}\b", text) is not None
    return clean in text


def _keyword_candidates(scene: dict, narration_chunk: str) -> tuple[list[str], str]:
    text = _scene_text(scene, narration_chunk).lower()
    candidates: list[str] = []
    family = "general_documentary"
    for needles, keywords, matched_family in _KEYWORD_RULES:
        if any(_needle_matches(text, needle) for needle in needles):
            candidates.extend(keywords)
            if family == "general_documentary":
                family = matched_family

    ascii_phrase = _first_ascii_phrase(text)
    if ascii_phrase:
        candidates.append(ascii_phrase)
    if not candidates:
        candidates.extend(["documentary science", "technology research", "wide landscape nature"])

    return _unique(candidates, limit=3), family


def _camera_role(family: str, asset_idx: int) -> str:
    family_roles = {
        "market_reality": ["human_context", "process_detail", "object_closeup", "texture_insert"],
        "space_biotech": ["object_closeup", "human_context", "process_detail", "texture_insert"],
        "space_mining": ["object_closeup", "process_detail", "environment_wide", "texture_insert"],
        "orbital_network": ["environment_wide", "object_closeup", "human_context", "process_detail"],
        "launch_hardware": ["environment_wide", "object_closeup", "process_detail", "human_context"],
    }
    roles = family_roles.get(
        family,
        ["object_closeup", "process_detail", "environment_wide", "human_context", "texture_insert"],
    )
    return roles[(asset_idx - 1) % len(roles)]


def _fallback_prompt(scene: dict, narration_chunk: str, family: str, camera_role: str, keywords: list[str]) -> str:
    scene_context = _compact_text(_strip_style_prefix(scene.get("image_prompt", "")), 520)
    chunk = _compact_text(narration_chunk, 220)
    role_direction = _ROLE_DIRECTIONS.get(camera_role, _ROLE_DIRECTIONS["object_closeup"])
    avoid = ", ".join(_FAMILY_AVOIDS.get(family, ["generic symbolic landscape", "repeated main composition"]))
    keyword_hint = ", ".join(keywords)
    prompt = (
        "Documentary supporting visual, 16:9 widescreen frame.\n\n"
        f"Visual family: {family}.\n"
        f"Camera role: {camera_role}.\n"
        f"{role_direction}\n"
        f"Stock/search concept hints: {keyword_hint}.\n"
        f"Scene context: {scene_context}\n"
    )
    if chunk and chunk.isascii():
        prompt += f"Narration moment: {chunk}\n"
    prompt += (
        "Make the image visibly different from the anchor by changing camera distance, "
        "subject scale, and composition. Use concrete physical details from this beat. "
        f"Avoid: {avoid}. No text overlays, no logos, no watermarks."
    )
    return prompt


def _asset_plan(scene: dict, scene_index: int, asset_idx: int, narration_chunk: str) -> dict:
    if asset_idx <= 0:
        return {
            "asset_index": 0,
            "source_preference": "anchor_ai",
            "use_existing_prompt": True,
        }

    keywords, family = _keyword_candidates(scene, narration_chunk)
    role = _camera_role(family, asset_idx)
    return {
        "asset_index": asset_idx,
        "source_preference": "stock_first" if keywords else "ai_first",
        "visual_family": family,
        "camera_role": role,
        "stock_keywords": keywords,
        "ai_fallback_prompt": _fallback_prompt(scene, narration_chunk, family, role, keywords),
        "fallback_policy": "try_stock_candidates_then_ai",
        "avoid_repeats": _FAMILY_AVOIDS.get(family, ["generic symbolic landscape", "repeated main composition"]),
        "confidence": 0.78 if family != "general_documentary" else 0.56,
        "why": (
            "Matched deterministic visual vocabulary from scene title, image prompt, and narration chunk."
            if family != "general_documentary"
            else "No strong domain match; using generic documentary search candidates."
        ),
    }


def visual_plan_path(episode_dir: str) -> str:
    return os.path.join(episode_dir, VISUAL_PLAN_FILENAME)


def stock_query_report_path(episode_dir: str) -> str:
    return os.path.join(episode_dir, STOCK_QUERY_REPORT_FILENAME)


def load_visual_plan(episode_dir: str) -> dict:
    path = visual_plan_path(episode_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            if isinstance(plan, dict):
                plan.setdefault("scenes", [])
                return plan
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "version": VISUAL_PLAN_VERSION,
        "episode_id": os.path.basename(os.path.abspath(episode_dir)),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "planning_mode": "deterministic-v1",
        "rules": {
            "anchor_asset": "keep existing AI image prompt",
            "secondary_assets": "stock-first, AI fallback",
            "stock_chain": ["pexels", "pixabay"],
            "ai_fallback": "runware_flux1_image",
            "no_ascii_only_context_gate": True,
        },
        "scenes": [],
    }


def save_visual_plan(episode_dir: str, plan: dict) -> None:
    os.makedirs(episode_dir, exist_ok=True)
    plan["updated_at"] = _utc_now()
    with open(visual_plan_path(episode_dir), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def upsert_scene_visual_plan(
    episode_dir: str,
    scenes: list[dict],
    scene_index: int,
    n_assets: int,
    narration_chunks: list[str],
) -> dict:
    plan = load_visual_plan(episode_dir)
    plan["scene_count"] = len(scenes or [])
    scene = scenes[scene_index]
    assets = []
    for asset_idx in range(max(1, int(n_assets or 1))):
        chunk = narration_chunks[asset_idx] if asset_idx < len(narration_chunks) else ""
        assets.append(_asset_plan(scene, scene_index, asset_idx, chunk))

    scene_plan = {
        "scene_index": scene_index,
        "scene_number": scene_index + 1,
        "scene_title": scene.get("scene_title", ""),
        "section_title": scene.get("section_title", ""),
        "visual_goal": _compact_text(_strip_style_prefix(scene.get("image_prompt", "")), 220),
        "planned_asset_count": len(assets),
        "assets": assets,
    }
    existing = [item for item in plan.get("scenes", []) if item.get("scene_index") != scene_index]
    existing.append(scene_plan)
    existing.sort(key=lambda item: int(item.get("scene_index", 0)))
    plan["scenes"] = existing
    save_visual_plan(episode_dir, plan)
    return scene_plan


def get_asset_plan(scene_plan: dict, asset_idx: int) -> dict:
    for asset in scene_plan.get("assets", []):
        if int(asset.get("asset_index", -1)) == asset_idx:
            return asset
    return {}


def append_stock_query_report(episode_dir: str, record: dict) -> None:
    path = stock_query_report_path(episode_dir)
    items = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                items = loaded
        except (OSError, json.JSONDecodeError):
            items = []
    row = {
        "ts": _utc_now(),
        **record,
    }
    items.append(row)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items[-500:], f, ensure_ascii=False, indent=2)
