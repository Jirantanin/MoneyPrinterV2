"""Producer Mode planning and checkpoint helpers for PodcastV2.

This module covers the first implementation slice: a stable
``producer_plan.json`` shape, mandatory research checkpoint, official media
candidates, and a read-only ``checkpoint.html`` renderer. It does not synthesize
audio or render video yet.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

from producer_visual_policy import default_visual_source_policy, explainer_visual_source_policy
from producer_contract import THAI_MIN, THAI_MAX, default_episode_spec, episode_spec, require_production_review


PRODUCER_PLAN_VERSION = 1
PRODUCER_PLAN_FILENAME = "producer_plan.json"
CHECKPOINT_FILENAME = "checkpoint.html"
RESEARCH_BRIEF_FILENAME = "research_brief.json"
VISUAL_SOURCE_STRATEGY_FILENAME = "visual_source_strategy.json"
VISUAL_ASSET_PLAN_FILENAME = "visual_asset_plan.json"
ASSET_QC_FILENAME = "asset_qc.json"
ASSET_MANIFEST_FILENAME = "asset_manifest.json"
VISUAL_TIMELINE_FILENAME = "visual_timeline.json"
BROLL_EXPANSION_REPORT_FILENAME = "broll_expansion_report.json"
IMAGEGEN_TASKS_FILENAME = "imagegen_tasks.json"
REMOTION_GRAPHIC_TASKS_FILENAME = "remotion_graphic_tasks.json"
GRAPHIC_RENDER_REPORT_FILENAME = "graphic_render_report.json"
TTS_MANIFEST_FILENAME = "tts_manifest.json"
TTS_QC_FILENAME = "tts_qc.json"
AUDIO_QC_FILENAME = "audio_qc.json"
RENDER_PREFLIGHT_FILENAME = "render_preflight.json"
RENDER_PROPS_PREVIEW_FILENAME = "render_props_preview.json"
RENDER_MANIFEST_FILENAME = "render_manifest.json"
RENDER_PROPS_FILENAME = "render_props.json"
FINAL_QC_FILENAME = "final_qc.json"
COST_REPORT_FILENAME = "cost_report.json"
FINAL_REPORT_FILENAME = "final_report.html"
UPLOAD_PACK_DIRNAME = "upload_pack"
UPLOAD_PACK_MANIFEST_FILENAME = "upload_pack_manifest.json"
SMOKE_GATE_FILENAME = "smoke_gate.json"
PROVIDER_SMOKE_DIRNAME = "provider_smoke"
PROVIDER_SMOKE_MANIFEST_FILENAME = "provider_smoke_manifest.json"
SCRIPT_FILENAME = "script.json"
SCRIPT_QC_FILENAME = "script_qc.json"
FACT_CHECK_REPORT_FILENAME = "fact_check_report.json"
PRONUNCIATION_GUIDE_FILENAME = "pronunciation_guide.md"

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT_DIR / ".mp"

THAI_CHARS_NO_SPACE_MIN = THAI_MIN
THAI_CHARS_NO_SPACE_TARGET_MIN = THAI_MIN
THAI_CHARS_NO_SPACE_TARGET_MAX = THAI_MAX
THAI_CHARS_NO_SPACE_MAX = THAI_MAX

VISUAL_BEAT_SECONDS_MIN = 5
VISUAL_BEAT_SECONDS_MAX = 8

BUDGET_WARN_USD = 3.0
BUDGET_STOP_USD = 5.0

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    return HTTP_SESSION.get(url, **kwargs)

OFFICIAL_DOMAIN_HINTS = (
    "nasa.gov",
    "jpl.nasa.gov",
    "esa.int",
    "noaa.gov",
    "usgs.gov",
    "nih.gov",
    "cdc.gov",
    "who.int",
    "loc.gov",
    "archives.gov",
    "si.edu",
    "worldbank.org",
    "imf.org",
    "federalreserve.gov",
)

REPUTABLE_DOMAIN_HINTS = (
    ".edu",
    "nature.com",
    "science.org",
    "scientificamerican.com",
    "britannica.com",
    "wikipedia.org",
    "wikimedia.org",
    "reuters.com",
    "apnews.com",
    "bbc.com",
)

TOPIC_TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "official",
    "source",
    "sources",
    "facts",
    "research",
    "paper",
    "explanation",
    "documentary",
    "evidence",
    "analysis",
    "youtube",
    "title",
    "thumbnail",
    "explained",
}

ASTROLOGY_RESULT_MARKERS = (
    "horoscope",
    "zodiac",
    "astrology",
    "ดูดวง",
    "ดวงวันนี้",
    "ราศี",
    "ไพ่ยิปซี",
    "ทำนายฝัน",
)


PRODUCER_PLAN_SCHEMA: dict[str, Any] = {
    "schema_version": PRODUCER_PLAN_VERSION,
    "required_top_level": [
        "schema_version",
        "mode",
        "status",
        "created_at",
        "updated_at",
        "episode",
        "approval",
        "topic_profile",
        "research",
        "sections",
        "visual_rules",
        "asset_qc_rules",
        "audio_rules",
        "render_rules",
        "seo_packaging",
        "budget",
        "stop_rules",
        "artifacts",
    ],
    "status_values": [
        "checkpoint_pending",
        "checkpoint_approved",
        "in_progress",
        "complete",
        "blocked",
    ],
    "section_required_keys": [
        "section_index",
        "title",
        "narrative_goal",
        "source_ids",
        "visual_direction",
        "beats",
    ],
    "beat_required_keys": [
        "beat_index",
        "role",
        "beat_type",
        "visual_type",
        "intent",
        "source_preference",
        "duration_seconds",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _slugify(value: str, fallback: str = "episode") -> str:
    text = str(value or "").lower()
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return (text or fallback)[:80].strip("-") or fallback


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _path_for_display(path: Any) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve())
    except (OSError, TypeError, ValueError):
        return str(path)


def _domain(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _source_type(url: str) -> str:
    domain = _domain(url)
    if any(domain == hint or domain.endswith("." + hint) for hint in OFFICIAL_DOMAIN_HINTS):
        return "official"
    if domain.endswith(".gov"):
        return "official"
    if domain.endswith(".edu") or any(hint in domain for hint in REPUTABLE_DOMAIN_HINTS):
        return "reputable"
    return "search_result"


def _dedupe_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    path = parsed.path.rstrip("/") or "/"
    return parsed._replace(fragment="", path=path).geturl()


def _compact(value: Any, limit: int = 480) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _strip_tags(value: str) -> str:
    return _clean_text(re.sub(r"<[^>]+>", " ", html.unescape(str(value or ""))))


def _english_tokens(value: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", str(value or "").lower())
    return [word for word in words if word not in TOPIC_TOKEN_STOPWORDS]


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    lower = str(value or "").lower()
    return any(needle in lower for needle in needles)


def _topic_search_profile(topic: str) -> dict[str, Any]:
    clean = _clean_text(topic)
    lower = clean.lower()
    aliases: list[str] = []
    required_terms: list[str] = []
    banned_markers: list[str] = []
    source_seeds: list[str] = []

    is_lunar_topic = _has_any(lower, ("ดวงจันทร์", "พระจันทร์", "moon", "lunar"))
    is_recession_topic = _has_any(lower, ("ถอยห่าง", "ห่างจากโลก", "reced", "drift", "moving away"))
    if is_lunar_topic and is_recession_topic:
        aliases.extend(
            [
                "Moon drifting away from Earth",
                "lunar recession",
                "Moon moves away from Earth 3.8 cm per year",
                "tidal acceleration Earth Moon distance",
            ]
        )
        required_terms.extend(["moon", "lunar", "earth", "recession", "tidal", "distance"])
        banned_markers.extend(ASTROLOGY_RESULT_MARKERS)
        specific_markers = [
            "lunar recession",
            "receding",
            "recedes",
            "moving away",
            "moves away",
            "drifting away",
            "drifts away",
            "tidal acceleration",
            "laser ranging",
            "centimeters per year",
            "centimetres per year",
            "3.8 cm",
            "3.78 cm",
            "distance from earth",
        ]
        source_seeds.extend(
            [
                "https://science.nasa.gov/moon/facts/",
                "https://science.nasa.gov/solar-system/moon/five-things-to-know-about-the-moon/",
                "https://www.nasa.gov/?p=51635",
                "https://en.wikipedia.org/wiki/Tidal_acceleration",
                "https://en.wikipedia.org/wiki/Lunar_Laser_Ranging_experiments",
                "https://en.wikipedia.org/wiki/Lunar_distance",
                "https://www.astronomy.com/science/our-moon-has-been-slowly-drifting-away-from-earth-over-the-past-2-5-billion-years/",
                "https://www.space.com/astronomy/moon/the-moon-is-getting-slightly-farther-away-from-the-earth-each-year-a-physicist-explains-why",
            ]
        )
        visual_relevance_topic = "Moon lunar Earth"
    elif is_lunar_topic:
        aliases.extend(["Moon", "lunar science", "Earth Moon system"])
        required_terms.extend(["moon", "lunar", "earth"])
        banned_markers.extend(ASTROLOGY_RESULT_MARKERS)
        specific_markers = []
        visual_relevance_topic = "Moon lunar Earth"
    else:
        specific_markers = []
        visual_relevance_topic = clean

    if not aliases:
        english = " ".join(_english_tokens(clean))
        aliases.append(english or clean)
        required_terms.extend(_english_tokens(clean))

    focus = aliases[0]
    return {
        "original_topic": clean,
        "focus": focus,
        "aliases": list(dict.fromkeys(alias for alias in aliases if alias)),
        "required_terms": list(dict.fromkeys(required_terms or _english_tokens(focus))),
        "banned_markers": list(dict.fromkeys(banned_markers)),
        "specific_markers": list(dict.fromkeys(specific_markers)),
        "source_seeds": list(dict.fromkeys(source_seeds)),
        "visual_relevance_topic": visual_relevance_topic,
    }


def _topic_tokens(topic: str) -> list[str]:
    tokens = _english_tokens(topic)
    if tokens:
        return tokens
    return [str(token) for token in _topic_search_profile(topic).get("required_terms", []) if str(token).strip()]


def _result_relevance_score(topic: str, result: dict[str, Any]) -> int:
    tokens = _topic_tokens(topic)
    if not tokens:
        return 1
    haystack = " ".join(
        str(result.get(key, "") or "").lower()
        for key in ("title", "snippet", "summary", "searchable_text", "url", "publisher")
    )
    score = sum(1 for token in tokens if token in haystack)
    normalized_topic = re.sub(r"\s+", " ", str(topic or "").lower()).strip()
    if normalized_topic and normalized_topic in haystack:
        score += 2
    return score


def _is_relevant_result(topic: str, result: dict[str, Any]) -> bool:
    profile = _topic_search_profile(topic)
    haystack = " ".join(
        str(result.get(key, "") or "").lower()
        for key in ("title", "snippet", "summary", "searchable_text", "url", "publisher")
    )
    if any(marker in haystack for marker in profile.get("banned_markers", [])):
        return False
    specific_markers = [str(marker) for marker in profile.get("specific_markers", [])]
    if specific_markers and not any(marker in haystack for marker in specific_markers):
        return False
    tokens = _topic_tokens(topic)
    if not tokens:
        return True
    required = 1 if len(tokens) == 1 else 2
    return _result_relevance_score(topic, result) >= required


def count_chars_no_space(text: str) -> int:
    """Count non-whitespace characters, matching the Thai script length gate."""

    return len(re.sub(r"\s+", "", str(text or "")))


def producer_plan_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / PRODUCER_PLAN_FILENAME


def checkpoint_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / CHECKPOINT_FILENAME


def research_brief_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / RESEARCH_BRIEF_FILENAME


def visual_source_strategy_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / VISUAL_SOURCE_STRATEGY_FILENAME


def visual_asset_plan_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / VISUAL_ASSET_PLAN_FILENAME


def asset_qc_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / ASSET_QC_FILENAME


def asset_manifest_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / ASSET_MANIFEST_FILENAME


def visual_timeline_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / VISUAL_TIMELINE_FILENAME


def broll_expansion_report_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / BROLL_EXPANSION_REPORT_FILENAME


def imagegen_tasks_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / IMAGEGEN_TASKS_FILENAME


def remotion_graphic_tasks_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / REMOTION_GRAPHIC_TASKS_FILENAME


def graphic_render_report_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / GRAPHIC_RENDER_REPORT_FILENAME


def tts_manifest_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / TTS_MANIFEST_FILENAME


def tts_qc_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / TTS_QC_FILENAME


def audio_qc_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / AUDIO_QC_FILENAME


def render_preflight_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / RENDER_PREFLIGHT_FILENAME


def render_props_preview_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / RENDER_PROPS_PREVIEW_FILENAME


def render_manifest_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / RENDER_MANIFEST_FILENAME


def render_props_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / RENDER_PROPS_FILENAME


def final_qc_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / FINAL_QC_FILENAME


def cost_report_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / COST_REPORT_FILENAME


def final_report_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / FINAL_REPORT_FILENAME


def upload_pack_dir(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / UPLOAD_PACK_DIRNAME


def upload_pack_manifest_path(episode_dir: str | Path) -> Path:
    return upload_pack_dir(episode_dir) / UPLOAD_PACK_MANIFEST_FILENAME


def smoke_gate_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / SMOKE_GATE_FILENAME


def provider_smoke_dir(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / PROVIDER_SMOKE_DIRNAME


def provider_smoke_manifest_path(episode_dir: str | Path) -> Path:
    return provider_smoke_dir(episode_dir) / PROVIDER_SMOKE_MANIFEST_FILENAME


def script_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / SCRIPT_FILENAME


def script_qc_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / SCRIPT_QC_FILENAME


def fact_check_report_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / FACT_CHECK_REPORT_FILENAME


def pronunciation_guide_path(episode_dir: str | Path) -> Path:
    return Path(episode_dir) / PRONUNCIATION_GUIDE_FILENAME


def make_episode_dir(topic: str, output_root: str | Path | None = None, slug: str | None = None) -> Path:
    root = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    episode_slug = _slugify(slug or topic)
    return root / f"podcast_v2_{episode_slug}_{_timestamp()}"


def default_producer_plan(
    topic: str,
    episode_dir: str | Path,
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    """Create a skeleton Producer Mode plan for the checkpoint stage."""

    clean_topic = _clean_text(topic, "Untitled topic")
    episode_path = Path(episode_dir)
    episode_slug = _slugify(slug or clean_topic)
    now = _utc_now()
    visual_policy = explainer_visual_source_policy()
    return {
        "schema_version": PRODUCER_PLAN_VERSION,
        "mode": "podcastv2_producer",
        "status": "checkpoint_pending",
        "created_at": now,
        "updated_at": now,
        "episode_spec": default_episode_spec(),
        # Documentary look used since the Chariklo episode; Remotion VideoPodcast stays opt-in.
        "render_settings": {"renderer": "minimal_doc"},
        "episode": {
            "topic": clean_topic,
            "slug": episode_slug,
            "episode_id": episode_path.name,
            "episode_dir": str(episode_path),
            "output_format": "youtube_16x9",
            "language": "th",
            "renderer": "podcastv2_remotion",
            "visual_beat_seconds": {
                "min": VISUAL_BEAT_SECONDS_MIN,
                "max": VISUAL_BEAT_SECONDS_MAX,
            },
            "subtitles": {
                "enabled": False,
                "policy": "no_subtitles_by_default_keep_podcastv2_titles_and_chapters",
            },
        },
        "approval": {
            "required": True,
            "approved": False,
            "approved_at": None,
            "approval_source": None,
            "accepted_phrases": ["OK", "do it", "continue", "go ahead"],
        },
        "topic_profile": {
            "selected_angle": "",
            "angle_rationale": "",
            "target_audience": "",
            "viewer_promise": "",
            "central_question": "",
            "why_now_or_why_care": "",
            "anti_clickbait_boundary": "",
        },
        "research": {
            "status": "pending",
            "minimum_sources": 3,
            "researched_at": None,
            "preferred_sources": [
                "official_sources",
                "primary_sources",
                "papers_or_universities",
                "reputable_publications",
            ],
            "competitor_market": "global_english_primary_thai_if_available",
            "sources": [],
            "section_source_map": [],
            "research_summary": "",
            "research_queries": [],
            "official_media_results": [],
            "competitor_results": [],
            "competitor_patterns": [],
            "risks": [],
            "conflict_policy": (
                "Prefer primary or official sources; qualify uncertain claims; "
                "remove unsupported major claims."
            ),
        },
        "sections": [],
        "visual_rules": {
            "source_strategy_artifact": str(visual_source_strategy_path(episode_path)),
            "source_policy": visual_policy,
            "section_count_default": {"min": 4, "max": 7},
            # This episode's own look, chosen to differ from the last three (doc_renderer/gfx_kit/LIBRARY.md).
            "art_direction": {"palette": "", "background": "", "recurring_metaphor": "", "camera_motion": "",
                              "topic_characters": []},
            "section_opener": {
                "required": True,
                "provider": "flat_explainer_graphic_in_the_episode_motif",
                "variants": 2,
                "retry_rounds": 1,
                "embedded_text": False,
                "style_consistency": True,
            },
            "source_order": [
                "flat_explainer_graphic_gfx_kit_around_one_recurring_metaphor",
                "official_verified_real_media_where_the_evidence_itself_is_the_point",
                "stock_video_only_when_specific_and_not_misleading",
                "generated_image_rarely_and_qualified_on_screen",
                "manual_review_when_caps_would_be_exceeded",
            ],
            "source_caps": [
                "graphics_max_80_percent",
                "runware_plus_codex_imagegen_max_50_percent",
                "real_footage_unlimited_when_relevant",
            ],
            "official_provider_registry": {
                "space": [
                    "nasa_image_and_video_library",
                    "jpl_photojournal",
                    "nasa_svs",
                    "esa",
                ],
                "earth_weather": ["nasa", "noaa", "usgs"],
                "history": [
                    "library_of_congress",
                    "national_archives",
                    "wikimedia_commons_license_clear",
                ],
                "health": ["cdc", "who", "nih"],
                "economics": ["fed", "world_bank", "imf"],
            },
            "no_go": [
                "ai_generated_likeness_of_real_people_by_default",
                "fake_document_or_screenshot_as_evidence",
                "fake_scientific_graph_without_data_source",
                "misleading_stock_footage",
                "watermark_logo_or_brand_distraction",
                "generated_visual_presented_as_real_evidence",
            ],
        },
        "asset_qc_rules": {
            "normal_pass_minimum": "3_of_4",
            "criteria": [
                "subject_matches_beat",
                "mood_matches_story",
                "not_misleading_as_broll",
                "not_obviously_repetitive_nearby",
            ],
            "specific_subjects_require_direct_match": True,
            "retry_rounds_per_beat": 2,
            "factual_accuracy_beats_visual_drama": True,
        },
        "visual_asset_plan": {
            "status": "pending",
            "planned_at": None,
            "artifact": None,
            "qc_artifact": None,
            "beat_count": 0,
            "provider_counts": {},
            "qc_status_counts": {},
            "warnings": [],
            "beat_plan_preview": [],
        },
        "script_draft": {
            "status": "pending",
            "drafted_at": None,
            "script_artifact": None,
            "script_qc_artifact": None,
            "fact_check_artifact": None,
            "pronunciation_guide_artifact": None,
            "scene_count": 0,
            "chars_no_space": 0,
            "length_status": None,
            "fact_check_status": None,
            "warnings": [],
        },
        "asset_production": {
            "status": "pending",
            "produced_at": None,
            "asset_manifest_artifact": None,
            "asset_qc_artifact": None,
            "visual_timeline_artifact": None,
            "broll_expansion_report_artifact": None,
            "imagegen_tasks_artifact": None,
            "remotion_graphic_tasks_artifact": None,
            "graphic_render_report_artifact": None,
            "entry_count": 0,
            "visual_slot_count": 0,
            "derived_broll_count": 0,
            "average_slot_seconds": 0,
            "downloaded_count": 0,
            "generated_count": 0,
            "pending_task_count": 0,
            "failed_count": 0,
            "warnings": [],
        },
        "audio_production": {
            "status": "pending",
            "produced_at": None,
            "tts_manifest_artifact": None,
            "tts_qc_artifact": None,
            "audio_qc_artifact": None,
            "audio_qc_status": None,
            "audio_qc_checked_at": None,
            "audio_qc_pass_count": 0,
            "audio_qc_review_count": 0,
            "audio_qc_blocked_count": 0,
            "scene_count": 0,
            "generated_count": 0,
            "skipped_existing_count": 0,
            "planned_count": 0,
            "failed_count": 0,
            "total_duration_seconds": 0,
            "estimated_cost_usd": 0.0,
            "warnings": [],
        },
        "render_preflight": {
            "status": "pending",
            "checked_at": None,
            "render_preflight_artifact": None,
            "render_props_preview_artifact": None,
            "scene_count": 0,
            "ready_scene_count": 0,
            "missing_audio_count": 0,
            "missing_asset_count": 0,
            "asset_count": 0,
            "render_duration_seconds": 0,
            "estimated_frames": 0,
            "warnings": [],
            "errors": [],
        },
        "render": {
            "status": "pending",
            "rendered_at": None,
            "render_manifest_artifact": None,
            "render_props_artifact": None,
            "log_artifact": None,
            "final_video_path": None,
            "raw_video_path": None,
            "scene_count": 0,
            "render_duration_seconds": 0,
            "final_video_bytes": 0,
            "warnings": [],
            "errors": [],
        },
        "final_qc": {
            "status": "pending",
            "checked_at": None,
            "final_qc_artifact": None,
            "final_video_path": None,
            "duration_seconds": 0,
            "resolution": "",
            "fps": 0,
            "has_audio": False,
            "file_bytes": 0,
            "warnings": [],
            "errors": [],
        },
        "cost_report": {
            "status": "pending",
            "reported_at": None,
            "cost_report_artifact": None,
            "estimated_total_cost_usd": 0.0,
            "new_cost_this_run_usd": 0.0,
            "remaining_estimated_cost_usd": 0.0,
            "unknown_cost_item_count": 0,
            "budget_status": "pending",
            "warnings": [],
            "errors": [],
        },
        "final_report": {
            "status": "pending",
            "reported_at": None,
            "final_report_artifact": None,
            "final_video_path": None,
            "final_qc_status": "pending",
            "budget_status": "pending",
            "warnings": [],
            "errors": [],
        },
        "upload_pack": {
            "status": "pending",
            "created_at": None,
            "upload_pack_dir": None,
            "manifest_artifact": None,
            "metadata_artifact": None,
            "root_metadata_artifact": None,
            "thumbnail_brief_artifact": None,
            "warnings": [],
            "errors": [],
        },
        "smoke_gate": {
            "status": "pending",
            "checked_at": None,
            "smoke_gate_artifact": None,
            "overall_score": 0,
            "blocking_gate_count": 0,
            "review_gate_count": 0,
            "next_actions": [],
            "warnings": [],
            "errors": [],
        },
        "provider_smoke": {
            "status": "pending",
            "checked_at": None,
            "provider_smoke_dir": None,
            "manifest_artifact": None,
            "live_pass_count": 0,
            "allow_network": False,
            "allow_gemini_tts": False,
            "warnings": [],
            "errors": [],
        },
        "audio_rules": {
            "tts_provider": "gemini_tts",
            "language": "th",
            "narrator": "single",
            "tone": "host_led_dry",
            "tone_preset": "host_dry",
            "music": "use_existing_podcastv2_behavior",
            "sfx": "optional_experimental",
            "required_artifacts": [
                "pronunciation_guide",
                "tts_manifest.json",
                "tts_qc.json",
                "audio_qc.json",
            ],
        },
        "render_rules": {
            "engine": "existing_podcastv2_remotion",
            "format": "16x9",
            "subtitle_default": False,
            "title_chapter_overlay": True,
            "chapter_timestamps": "from_real_durations",
        },
        "seo_packaging": {
            "competitor_research_required": True,
            "market": "global_english_primary_thai_if_available",
            "title_option_roles": [
                "curiosity_question",
                "concrete_stakes",
                "documentary_trust",
            ],
            "title_options": [],
            "recommended_title": "",
            "recommended_title_rationale": "",
            "upload_description": "",
            "thumbnail_concepts": 3,
            "thumbnail_concept_options": [],
            "thumbnail_language": "thai_primary",
            "generate_thumbnail_by_default": False,
        },
        "budget": {
            "currency": "USD",
            "warning_at": BUDGET_WARN_USD,
            "stop_at": BUDGET_STOP_USD,
            "estimated_cost": 0.0,
            "estimated_runtime_minutes": None,
        },
        "stop_rules": [
            "cost_reaches_stop_cap",
            "major_topic_pivot_needed",
            "major_structure_rewrite_needed_after_approval",
            "misleading_or_high_risk_fact_issue",
            "provider_outage_requires_material_flow_change",
            "license_or_provenance_cannot_be_verified",
        ],
        "artifacts": {
            "checkpoint": [
                "producer_plan.json",
                "checkpoint.html",
                "research_brief.json",
                "visual_source_strategy.json",
                "visual_asset_plan.json",
                "asset_qc.json",
                "asset_manifest.json",
                "visual_timeline.json",
                "broll_expansion_report.json",
                "imagegen_tasks.json",
                "remotion_graphic_tasks.json",
                "graphic_render_report.json",
                "tts_manifest.json",
                "tts_qc.json",
                "audio_qc.json",
                "render_preflight.json",
                "render_props_preview.json",
                "render_manifest.json",
                "render_props.json",
                "final_qc.json",
                "cost_report.json",
                "final_report.html",
                "metadata.json",
                "upload_pack/upload_pack_manifest.json",
                "smoke_gate.json",
                "provider_smoke/provider_smoke_manifest.json",
                "script.json",
                "script_qc.json",
                "fact_check_report.json",
                "pronunciation_guide.md",
            ],
            "required_final": [
                "final.mp4",
                "script.json",
                "sources",
                "script_qc.json",
                "fact_check_report.json",
                "asset_manifest.json",
                "asset_qc.json",
                "visual_timeline.json",
                "tts_manifest.json",
                "tts_qc.json",
                "audio_qc.json",
                "cost_report.json",
                "final_report.html",
                "upload_pack",
            ],
        },
        "notes": [],
    }


def validate_producer_plan(plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return blocking errors and non-blocking warnings for a plan."""

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"], warnings

    for key in PRODUCER_PLAN_SCHEMA["required_top_level"]:
        if key not in plan:
            errors.append(f"missing required top-level key: {key}")

    if plan.get("schema_version") != PRODUCER_PLAN_VERSION:
        errors.append(
            f"schema_version must be {PRODUCER_PLAN_VERSION}, got {plan.get('schema_version')!r}"
        )

    if plan.get("mode") != "podcastv2_producer":
        errors.append("mode must be podcastv2_producer")

    if plan.get("status") not in PRODUCER_PLAN_SCHEMA["status_values"]:
        errors.append(f"invalid status: {plan.get('status')!r}")

    episode = plan.get("episode") if isinstance(plan.get("episode"), dict) else {}
    if not _clean_text(episode.get("topic")):
        errors.append("episode.topic is required")

    try:
        episode_spec(plan)
    except (ValueError, TypeError, KeyError) as exc:
        errors.append(f"Invalid episode_spec: {exc}")
    if "episode_spec" not in plan:
        warnings.append("Legacy plan: default Thai Unicode bounds apply; explicitly migrate episode_spec before production.")

    sections = plan.get("sections")
    if sections is None:
        errors.append("sections must be present")
    elif not isinstance(sections, list):
        errors.append("sections must be a list")
    elif sections:
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                errors.append(f"sections[{index}] must be an object")
                continue
            for key in PRODUCER_PLAN_SCHEMA["section_required_keys"]:
                if key not in section:
                    errors.append(f"sections[{index}] missing {key}")
            beats = section.get("beats", [])
            if not isinstance(beats, list):
                errors.append(f"sections[{index}].beats must be a list")
                continue
            has_opener = any(str(beat.get("role", "")).lower() == "opener" for beat in beats if isinstance(beat, dict))
            if not has_opener:
                warnings.append(f"sections[{index}] has no opener beat yet")
            for beat_index, beat in enumerate(beats):
                if not isinstance(beat, dict):
                    errors.append(f"sections[{index}].beats[{beat_index}] must be an object")
                    continue
                for key in PRODUCER_PLAN_SCHEMA["beat_required_keys"]:
                    if key not in beat:
                        errors.append(f"sections[{index}].beats[{beat_index}] missing {key}")

    research = plan.get("research") if isinstance(plan.get("research"), dict) else {}
    sources = research.get("sources", [])
    minimum_sources = int(research.get("minimum_sources", 3) or 3)
    if not sources:
        warnings.append("research.sources is empty; checkpoint is a skeleton or research has not run")
    elif len(sources) < minimum_sources:
        warnings.append(
            f"research.sources has {len(sources)} items; minimum is {minimum_sources}"
        )

    topic_profile = plan.get("topic_profile") if isinstance(plan.get("topic_profile"), dict) else {}
    if not topic_profile.get("selected_angle"):
        warnings.append("topic_profile.selected_angle is empty")

    seo = plan.get("seo_packaging") if isinstance(plan.get("seo_packaging"), dict) else {}
    title_options = seo.get("title_options", [])
    if title_options and len(title_options) < 3:
        warnings.append("seo_packaging.title_options should contain 3 title angles")
    thumbnail_options = seo.get("thumbnail_concept_options", [])
    if thumbnail_options and len(thumbnail_options) < 3:
        warnings.append("seo_packaging.thumbnail_concept_options should contain 3 concepts")

    visual_asset_plan = (
        plan.get("visual_asset_plan") if isinstance(plan.get("visual_asset_plan"), dict) else {}
    )
    visual_status = str(visual_asset_plan.get("status") or "pending")
    research_status = str(research.get("status") or "")
    if sections and research_status == "complete" and visual_status == "pending":
        warnings.append("visual_asset_plan is pending; run plan-assets before production")
    if visual_status in {"needs_review", "blocked"}:
        warnings.append(f"visual_asset_plan status is {visual_status}")

    script_draft = plan.get("script_draft") if isinstance(plan.get("script_draft"), dict) else {}
    script_status = str(script_draft.get("status") or "pending")
    if visual_status == "ready" and script_status == "pending":
        warnings.append("script_draft is pending; run draft-script before audio/assets production")
    if script_status in {"blocked", "review"}:
        warnings.append(f"script_draft status is {script_status}")

    asset_production = (
        plan.get("asset_production") if isinstance(plan.get("asset_production"), dict) else {}
    )
    asset_status = str(asset_production.get("status") or "pending")
    if script_status == "pass" and asset_status == "pending":
        warnings.append("asset_production is pending; run produce-assets before TTS/render")
    if asset_status in {"blocked", "needs_tasks", "planned", "dry_run"}:
        warnings.append(f"asset_production status is {asset_status}")

    audio_production = (
        plan.get("audio_production") if isinstance(plan.get("audio_production"), dict) else {}
    )
    audio_status = str(audio_production.get("status") or "pending")
    if script_status == "pass" and audio_status == "pending":
        warnings.append("audio_production is pending; run produce-tts before render")
    if audio_status in {"blocked", "planned"}:
        warnings.append(f"audio_production status is {audio_status}")

    render_preflight = (
        plan.get("render_preflight") if isinstance(plan.get("render_preflight"), dict) else {}
    )
    render_status = str(render_preflight.get("status") or "pending")
    if asset_status == "complete" and audio_status == "complete" and render_status == "pending":
        warnings.append("render_preflight is pending; run render-preflight before render")
    if render_status in {"blocked", "needs_audio", "needs_assets"}:
        warnings.append(f"render_preflight status is {render_status}")

    render = plan.get("render") if isinstance(plan.get("render"), dict) else {}
    render_status_actual = str(render.get("status") or "pending")
    if render_status == "ready" and render_status_actual == "pending":
        warnings.append("render is pending; run render-video when ready")
    if render_status_actual in {"blocked", "prepared"}:
        warnings.append(f"render status is {render_status_actual}")

    final_qc = plan.get("final_qc") if isinstance(plan.get("final_qc"), dict) else {}
    final_qc_status = str(final_qc.get("status") or "pending")
    if render_status_actual == "complete" and final_qc_status == "pending":
        warnings.append("final_qc is pending; run final-qc after render")
    if final_qc_status in {"blocked", "review"}:
        warnings.append(f"final_qc status is {final_qc_status}")

    cost_report = plan.get("cost_report") if isinstance(plan.get("cost_report"), dict) else {}
    cost_status = str(cost_report.get("status") or "pending")
    if final_qc_status in {"pass", "review"} and cost_status == "pending":
        warnings.append("cost_report is pending; run cost-report after final QC")
    if cost_status in {"blocked", "review", "warn", "stop_required"}:
        warnings.append(f"cost_report status is {cost_status}")

    final_report = plan.get("final_report") if isinstance(plan.get("final_report"), dict) else {}
    final_report_status = str(final_report.get("status") or "pending")
    if cost_status in {"pass", "review"} and final_report_status == "pending":
        warnings.append("final_report is pending; run final-report for handoff")
    if final_report_status in {"blocked", "review"}:
        warnings.append(f"final_report status is {final_report_status}")

    upload_pack = plan.get("upload_pack") if isinstance(plan.get("upload_pack"), dict) else {}
    upload_status = str(upload_pack.get("status") or "pending")
    if final_report_status in {"ready", "review"} and upload_status == "pending":
        warnings.append("upload_pack is pending; run upload-pack for YouTube handoff metadata")
    if upload_status in {"blocked", "review"}:
        warnings.append(f"upload_pack status is {upload_status}")

    smoke_gate = plan.get("smoke_gate") if isinstance(plan.get("smoke_gate"), dict) else {}
    smoke_status = str(smoke_gate.get("status") or "pending")
    if upload_status in {"ready", "review"} and smoke_status == "pending":
        warnings.append("smoke_gate is pending; run smoke-gate before production live run")
    if smoke_status in {"blocked", "review"}:
        warnings.append(f"smoke_gate status is {smoke_status}")

    provider_smoke = plan.get("provider_smoke") if isinstance(plan.get("provider_smoke"), dict) else {}
    provider_status = str(provider_smoke.get("status") or "pending")
    if smoke_status in {"blocked", "review", "ready"} and provider_status == "pending":
        warnings.append("provider_smoke is pending; run provider-smoke before live provider fulfillment")
    if provider_status in {"blocked", "review"}:
        warnings.append(f"provider_smoke status is {provider_status}")

    return errors, warnings


def load_producer_plan(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as f:
        loaded = json.load(f)
    if not isinstance(loaded, dict):
        raise ValueError("producer plan must be a JSON object")
    return loaded


def save_producer_plan(episode_dir: str | Path, plan: dict[str, Any]) -> Path:
    path = producer_plan_path(episode_dir)
    _ensure_dir(path.parent)
    plan["updated_at"] = _utc_now()
    with path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


class _BingResultParser(HTMLParser):
    """Small parser for Bing result pages.

    Bing does not expose a keyless JSON search API. This parser only extracts
    top-level organic results from the public HTML page, then the research stage
    fetches source pages separately for a light summary.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._li_depth = 0
        self._h2_depth = 0
        self._p_depth = 0
        self._capture_title = False
        self._current: dict[str, Any] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        if tag == "li" and "b_algo" in attrs_dict.get("class", "").split() and not self._in_result:
            self._in_result = True
            self._li_depth = 1
            self._current = {"title_parts": [], "snippet_parts": []}
            return

        if not self._in_result:
            return

        if tag == "li":
            self._li_depth += 1
        elif tag == "h2":
            self._h2_depth += 1
        elif tag == "p":
            self._p_depth += 1
        elif tag == "a" and self._h2_depth and not self._current.get("url"):
            self._current["url"] = attrs_dict.get("href", "")
            self._capture_title = True

    def handle_endtag(self, tag: str) -> None:
        if not self._in_result:
            return

        if tag == "a":
            self._capture_title = False
        elif tag == "h2":
            self._h2_depth = max(0, self._h2_depth - 1)
        elif tag == "p":
            self._p_depth = max(0, self._p_depth - 1)
        elif tag == "li":
            self._li_depth -= 1
            if self._li_depth <= 0:
                self._finish_result()

    def handle_data(self, data: str) -> None:
        if not self._in_result:
            return
        if self._capture_title:
            self._current.setdefault("title_parts", []).append(data)
        elif self._p_depth:
            self._current.setdefault("snippet_parts", []).append(data)

    def _finish_result(self) -> None:
        title = _clean_text(" ".join(self._current.get("title_parts", [])))
        url = _decode_bing_url(str(self._current.get("url", "")))
        snippet = _clean_text(" ".join(self._current.get("snippet_parts", [])))
        if title and url and url.startswith(("http://", "https://")):
            self.results.append({"title": title, "url": url, "snippet": snippet})
        self._in_result = False
        self._li_depth = 0
        self._h2_depth = 0
        self._p_depth = 0
        self._capture_title = False
        self._current = {}


class _PageSummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.description = ""
        self.paragraphs: list[str] = []
        self._in_title = False
        self._p_depth = 0
        self._current_p: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.description = self.description or _clean_text(attrs_dict.get("content", ""))
        elif tag == "p":
            self._p_depth += 1
            self._current_p = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "p" and self._p_depth:
            self._p_depth -= 1
            text = _clean_text(" ".join(self._current_p))
            if len(text) >= 40 and len(self.paragraphs) < 24:
                self.paragraphs.append(text)
            self._current_p = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        elif self._p_depth:
            self._current_p.append(data)

    @property
    def title(self) -> str:
        return _clean_text(" ".join(self.title_parts))

    @property
    def summary(self) -> str:
        parts = []
        if self.description:
            parts.append(self.description)
        parts.extend(self.paragraphs[:2])
        return _compact(" ".join(parts), 900)

    @property
    def searchable_text(self) -> str:
        parts = []
        if self.description:
            parts.append(self.description)
        parts.extend(self.paragraphs)
        return _compact(" ".join(parts), 6000)


def _decode_bing_url(url: str) -> str:
    parsed = urlparse(html.unescape(str(url or "")))
    if "bing.com" not in parsed.netloc:
        return parsed.geturl()

    query = parse_qs(parsed.query)
    encoded = (query.get("u") or [""])[0]
    if encoded.startswith("a1"):
        payload = encoded[2:]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        try:
            return base64.urlsafe_b64decode(payload).decode("utf-8", "replace")
        except (ValueError, UnicodeDecodeError):
            return parsed.geturl()
    if encoded:
        return unquote(encoded)
    return parsed.geturl()


def bing_search(query: str, max_results: int = 6) -> list[dict[str, str]]:
    url = (
        "https://www.bing.com/search?"
        f"q={quote_plus(query)}&mkt=en-US&setlang=en-US&count={max(1, min(max_results, 10))}"
    )
    response = _http_get(url, headers=HTTP_HEADERS, timeout=(5, 20))
    response.raise_for_status()
    parser = _BingResultParser()
    parser.feed(response.text)
    parsed_results = parser.results or _parse_bing_results_fallback(response.text)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in parsed_results:
        clean_url = _dedupe_url(result["url"])
        key = clean_url.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "title": _compact(result.get("title", ""), 180),
                "url": clean_url,
                "snippet": _compact(result.get("snippet", ""), 500),
                "query": query,
            }
        )
        if len(results) >= max_results:
            break
    return results


def _parse_bing_results_fallback(markup: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for block in re.findall(r'<li class="b_algo".*?</li>', markup, flags=re.S):
        anchor = re.search(r'<h2.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        if not anchor:
            continue
        para = re.search(r"<p>(.*?)</p>", block, flags=re.S)
        results.append(
            {
                "title": _strip_tags(anchor.group(2)),
                "url": _decode_bing_url(anchor.group(1)),
                "snippet": _strip_tags(para.group(1) if para else ""),
            }
        )
    return results


def youtube_search(query: str, max_results: int = 6) -> list[dict[str, str]]:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    response = _http_get(url, headers=HTTP_HEADERS, timeout=(5, 25))
    response.raise_for_status()
    matches = re.findall(
        r'"videoRenderer":\{.*?"videoId":"([^"]+)".*?"title":\{"runs":\[\{"text":"([^"]+)"',
        response.text,
        flags=re.S,
    )
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for video_id, raw_title in matches:
        if video_id in seen:
            continue
        seen.add(video_id)
        title_text = raw_title
        if "\\u" in title_text:
            title_text = title_text.encode("utf-8").decode("unicode_escape", "replace")
        title = _compact(html.unescape(title_text), 180)
        result = {
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "snippet": "",
            "query": query,
            "publisher": "youtube.com",
        }
        if not _is_relevant_result(query, result):
            continue
        results.append(result)
        if len(results) >= max_results:
            break
    return results


def bing_video_search(query: str, max_results: int = 6) -> list[dict[str, str]]:
    response = _http_get(
        "https://www.bing.com/videos/search",
        params={"q": query, "FORM": "HDRSC3"},
        headers=HTTP_HEADERS,
        timeout=(8, 25),
    )
    response.raise_for_status()
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'mmeta="(?P<meta>[^"]+)".{0,6000}?<a[^>]+aria-label="(?P<label>[^"]+)"[^>]+href="(?P<href>[^"]+)"',
        flags=re.S,
    )
    for match in pattern.finditer(response.text):
        try:
            metadata = json.loads(html.unescape(match.group("meta")))
        except (TypeError, ValueError, json.JSONDecodeError):
            metadata = {}
        raw_url = metadata.get("murl") or metadata.get("pgurl") or html.unescape(match.group("href"))
        clean_url = _dedupe_url(str(raw_url or ""))
        if not clean_url:
            continue
        key = clean_url.lower()
        if key in seen:
            continue
        label = _strip_tags(html.unescape(match.group("label")))
        title = re.split(r"\s+from\s+|\s+·\s+", label, maxsplit=1, flags=re.I)[0]
        publisher = _domain(clean_url)
        snippet = label
        result = {
            "title": _compact(title or clean_url, 180),
            "url": clean_url,
            "snippet": _compact(snippet, 500),
            "query": query,
            "publisher": publisher,
        }
        if not _is_relevant_result(query, result):
            continue
        seen.add(key)
        results.append(result)
        if len(results) >= max_results:
            break
    return results


def fetch_page_summary(url: str) -> dict[str, Any]:
    result = {
        "fetched": False,
        "final_url": url,
        "title": "",
        "summary": "",
        "error": "",
    }
    try:
        response = _http_get(url, headers=HTTP_HEADERS, timeout=(5, 20), stream=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        result["final_url"] = response.url
        if "text/html" not in content_type.lower():
            result["error"] = f"unsupported content type: {content_type or 'unknown'}"
            return result
        content = response.content[:350_000]
        text = content.decode(response.encoding or "utf-8", "replace")
        parser = _PageSummaryParser()
        parser.feed(text)
        result.update(
            {
                "fetched": True,
                "title": parser.title,
                "summary": parser.summary,
                "searchable_text": parser.searchable_text,
                "error": "",
            }
        )
    except requests.RequestException as exc:
        result["error"] = str(exc)
    return result


def _topic_queries(topic: str) -> list[str]:
    clean = _clean_text(topic)
    profile = _topic_search_profile(clean)
    aliases = [str(alias) for alias in profile.get("aliases", []) if str(alias).strip()]
    focus = str(profile.get("focus") or clean)
    queries = []
    if "lunar recession" in aliases:
        queries.extend(
            [
                '"lunar recession" "Moon" "Earth"',
                '"Moon moving away from Earth"',
                '"Moon is moving away from Earth" NASA',
                '"tidal acceleration" "Moon"',
                '"laser ranging" "Moon" "Earth"',
            ]
        )
    for alias in aliases[:3]:
        queries.extend(
            [
                f"{alias} official source facts",
                f"{alias} research paper explanation",
                f"{alias} documentary evidence analysis",
            ]
        )
    queries.extend(
        [
            f"site:nasa.gov {focus}",
            f"site:jpl.nasa.gov {focus}",
            f"site:esa.int {focus}",
        ]
    )
    if "ดวงจันทร์" in clean and "ถอยห่าง" in clean:
        queries.append('"ดวงจันทร์" "ถอยห่าง" โลก วิทยาศาสตร์')
    return list(dict.fromkeys(query for query in queries if query.strip()))


def _competitor_queries(topic: str) -> list[str]:
    clean = _clean_text(topic)
    profile = _topic_search_profile(clean)
    focus = str(profile.get("focus") or clean)
    queries = [
        f"site:youtube.com/watch {focus} documentary",
        f"site:youtube.com/watch {focus} explained",
        f"{focus} YouTube documentary title thumbnail",
    ]
    if "lunar recession" in profile.get("aliases", []):
        queries.extend(
            [
                'site:youtube.com/watch "Moon moving away from Earth"',
                'site:youtube.com/watch "lunar recession"',
            ]
        )
    return list(dict.fromkeys(queries))


def _youtube_competitor_queries(topic: str) -> list[str]:
    clean = _clean_text(topic)
    profile = _topic_search_profile(clean)
    focus = str(profile.get("focus") or clean)
    return [
        f"{focus} documentary",
        f"{focus} explained",
        focus,
    ]


def collect_research_inputs(
    topic: str,
    *,
    max_sources: int = 8,
    max_competitors: int = 6,
    fetch_pages: bool = True,
) -> dict[str, Any]:
    now = _utc_now()
    search_profile = _topic_search_profile(topic)
    source_candidates: list[dict[str, Any]] = []
    competitor_candidates: list[dict[str, Any]] = []
    official_media_results: list[dict[str, Any]] = []
    errors: list[str] = []

    for seed_url in search_profile.get("source_seeds", []):
        clean_url = _dedupe_url(str(seed_url or ""))
        if not clean_url:
            continue
        source_candidates.append(
            {
                "title": clean_url,
                "url": clean_url,
                "snippet": "",
                "query": "profile_source_seed",
            }
        )

    try:
        from official_media_provider import search_official_media

        seen_media_urls: set[str] = set()
        visual_relevance_topic = str(search_profile.get("visual_relevance_topic") or topic)
        media_queries = [str(value) for value in search_profile.get("aliases", [])[:2]]
        if visual_relevance_topic and visual_relevance_topic not in media_queries:
            media_queries.append(visual_relevance_topic)
        if visual_relevance_topic == "Moon lunar Earth":
            media_queries.extend(["Moon", "Earth Moon"])
        for media_query in list(dict.fromkeys(query for query in media_queries if query.strip())):
            for media in search_official_media(
                media_query,
                limit=min(6, max(3, max_sources)),
                media_types=("image", "video"),
                resolve_downloads=True,
            ):
                if not isinstance(media, dict):
                    continue
                key = str(media.get("source_url") or media.get("download_url") or media.get("id") or "").lower()
                if key and key in seen_media_urls:
                    continue
                if key:
                    seen_media_urls.add(key)
                media_combined = {
                    "title": media.get("title", ""),
                    "summary": media.get("description") or media.get("selected_reason") or "",
                    "url": media.get("source_url") or media.get("download_url") or "",
                    "publisher": media.get("provider") or media.get("credit") or "",
                }
                if not _is_relevant_result(visual_relevance_topic, media_combined):
                    continue
                official_media_results.append(media)
                if len(official_media_results) >= min(8, max(3, max_sources)):
                    break
            if len(official_media_results) >= min(8, max(3, max_sources)):
                break
    except Exception as exc:  # noqa: BLE001
        errors.append(f"official media search failed: {exc}")

    for query in _topic_queries(topic):
        try:
            source_candidates.extend(
                result for result in bing_search(query, max_results=6)
                if _is_relevant_result(topic, result)
            )
        except requests.RequestException as exc:
            errors.append(f"search failed for {query!r}: {exc}")

    for query in _youtube_competitor_queries(topic):
        try:
            competitor_candidates.extend(
                result for result in youtube_search(query, max_results=max_competitors)
                if _is_relevant_result(topic, result)
            )
        except requests.RequestException as exc:
            errors.append(f"youtube competitor search failed for {query!r}: {exc}")

    for query in _youtube_competitor_queries(topic):
        try:
            competitor_candidates.extend(
                result for result in bing_video_search(query, max_results=max_competitors)
                if _is_relevant_result(topic, result)
            )
        except requests.RequestException as exc:
            errors.append(f"video competitor search failed for {query!r}: {exc}")

    for query in _competitor_queries(topic):
        try:
            competitor_candidates.extend(
                result for result in bing_search(query, max_results=6)
                if _is_relevant_result(topic, result)
            )
        except requests.RequestException as exc:
            errors.append(f"competitor search failed for {query!r}: {exc}")

    sources: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for candidate in source_candidates:
        clean_url = _dedupe_url(str(candidate.get("url", "")))
        if not clean_url or clean_url.lower() in seen_urls:
            continue
        is_profile_seed = candidate.get("query") == "profile_source_seed"
        if not is_profile_seed and not _is_relevant_result(topic, candidate):
            continue
        seen_urls.add(clean_url.lower())
        page = fetch_page_summary(clean_url) if fetch_pages else {}
        title = page.get("title") or candidate.get("title") or clean_url
        summary = page.get("summary") or candidate.get("snippet") or ""
        combined = {
            **candidate,
            "title": title,
            "summary": summary,
            "searchable_text": page.get("searchable_text", ""),
            "publisher": _domain(clean_url),
        }
        if not _is_relevant_result(topic, combined):
            continue
        sources.append(
            {
                "id": f"S{len(sources) + 1}",
                "title": _compact(title, 180),
                "publisher": _domain(clean_url),
                "url": clean_url,
                "source_type": _source_type(clean_url),
                "query": candidate.get("query", ""),
                "snippet": _compact(candidate.get("snippet", ""), 500),
                "summary": _compact(summary, 900),
                "fetched": bool(page.get("fetched")),
                "fetch_error": page.get("error", ""),
                "accessed_date": now[:10],
            }
        )
        if len(sources) >= max_sources:
            break

    for media in official_media_results:
        if len(sources) >= max_sources:
            break
        if not isinstance(media, dict):
            continue
        clean_url = _dedupe_url(str(media.get("source_url") or ""))
        if not clean_url or clean_url.lower() in seen_urls:
            continue
        title = _clean_text(media.get("title"), clean_url)
        summary = _clean_text(media.get("description") or media.get("selected_reason"))
        if not title and not summary:
            continue
        combined = {
            "title": title,
            "summary": summary,
            "url": clean_url,
            "publisher": _domain(clean_url) or media.get("provider", ""),
        }
        if not _is_relevant_result(topic, combined):
            continue
        seen_urls.add(clean_url.lower())
        sources.append(
            {
                "id": f"S{len(sources) + 1}",
                "title": _compact(title, 180),
                "publisher": _domain(clean_url) or str(media.get("provider") or ""),
                "url": clean_url,
                "source_type": "official",
                "query": f"official_media_provider:{media.get('provider', '')}",
                "snippet": _compact(summary, 500),
                "summary": _compact(f"Official media source/caption: {summary}", 900),
                "fetched": False,
                "fetch_error": "",
                "accessed_date": now[:10],
                "media_provider": media.get("provider", ""),
                "media_id": media.get("id", ""),
            }
        )

    competitors: list[dict[str, Any]] = []
    seen_competitors: set[str] = set()
    for candidate in competitor_candidates:
        clean_url = _dedupe_url(str(candidate.get("url", "")))
        if not clean_url or clean_url.lower() in seen_competitors:
            continue
        if "youtube.com" not in _domain(clean_url) and "youtu.be" not in _domain(clean_url):
            continue
        if not _is_relevant_result(topic, candidate):
            continue
        seen_competitors.add(clean_url.lower())
        competitors.append(
            {
                "id": f"C{len(competitors) + 1}",
                "title": _compact(candidate.get("title", ""), 180),
                "url": clean_url,
                "publisher": _domain(clean_url),
                "query": candidate.get("query", ""),
                "snippet": _compact(candidate.get("snippet", ""), 500),
                "accessed_date": now[:10],
            }
        )
        if len(competitors) >= max_competitors:
            break

    return {
        "topic": topic,
        "researched_at": now,
        "search_profile": search_profile,
        "queries": _topic_queries(topic),
        "youtube_competitor_queries": _youtube_competitor_queries(topic),
        "competitor_queries": _competitor_queries(topic),
        "sources": sources,
        "official_media_results": official_media_results,
        "competitors": competitors,
        "errors": errors,
    }


def _producer_research_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "topic_profile": {
                "type": "object",
                "properties": {
                    "selected_angle": {"type": "string"},
                    "angle_rationale": {"type": "string"},
                    "target_audience": {"type": "string"},
                    "viewer_promise": {"type": "string"},
                    "central_question": {"type": "string"},
                    "why_now_or_why_care": {"type": "string"},
                    "anti_clickbait_boundary": {"type": "string"},
                },
                "required": [
                    "selected_angle",
                    "angle_rationale",
                    "target_audience",
                    "viewer_promise",
                    "central_question",
                    "why_now_or_why_care",
                    "anti_clickbait_boundary",
                ],
            },
            "research_summary": {"type": "string"},
            "section_source_map": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section_index": {"type": "integer"},
                        "source_ids": {"type": "array", "items": {"type": "string"}},
                        "key_claims": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["section_index", "source_ids", "key_claims"],
                },
            },
            "sections": {
                "type": "array",
                "minItems": 4,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "section_index": {"type": "integer"},
                        "title": {"type": "string"},
                        "narrative_goal": {"type": "string"},
                        "source_ids": {"type": "array", "items": {"type": "string"}},
                        "visual_direction": {"type": "string"},
                        "beats": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "beat_index": {"type": "integer"},
                                    "role": {"type": "string"},
                                    "beat_type": {"type": "string"},
                                    "visual_type": {"type": "string"},
                                    "intent": {"type": "string"},
                                    "source_preference": {"type": "string"},
                                    "duration_seconds": {"type": "number"},
                                },
                                "required": [
                                    "beat_index",
                                    "role",
                                    "beat_type",
                                    "visual_type",
                                    "intent",
                                    "source_preference",
                                    "duration_seconds",
                                ],
                            },
                        },
                    },
                    "required": [
                        "section_index",
                        "title",
                        "narrative_goal",
                        "source_ids",
                        "visual_direction",
                        "beats",
                    ],
                },
            },
            "competitor_patterns": {"type": "array", "items": {"type": "string"}},
            "title_options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "title": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["role", "title", "rationale"],
                },
            },
            "recommended_title": {"type": "string"},
            "recommended_title_rationale": {"type": "string"},
            "upload_description": {"type": "string"},
            "thumbnail_concept_options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string"},
                        "composition": {"type": "string"},
                        "text_overlay": {"type": "string"},
                        "avoid": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["concept", "composition", "text_overlay", "avoid"],
                },
            },
            "risks": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "topic_profile",
            "research_summary",
            "section_source_map",
            "sections",
            "competitor_patterns",
            "title_options",
            "recommended_title",
            "recommended_title_rationale",
            "upload_description",
            "thumbnail_concept_options",
            "risks",
        ],
    }


def _json_loads_loose(raw: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip(), flags=re.MULTILINE)
    return json.loads(text)


def _build_research_prompt(topic: str, research_inputs: dict[str, Any]) -> str:
    compact_payload = {
        "topic": topic,
        "sources": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "source_type": item.get("source_type"),
                "url": item.get("url"),
                "summary": item.get("summary") or item.get("snippet"),
            }
            for item in research_inputs.get("sources", [])
        ],
        "competitors": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "url": item.get("url"),
                "snippet": item.get("snippet"),
            }
            for item in research_inputs.get("competitors", [])
        ],
        "official_media": [
            {
                "provider": item.get("provider"),
                "title": item.get("title"),
                "media_type": item.get("media_type"),
                "source_url": item.get("source_url"),
                "download_url": item.get("download_url"),
                "credit": item.get("credit"),
                "description": item.get("description"),
                "selected_reason": item.get("selected_reason"),
            }
            for item in research_inputs.get("official_media_results", [])
        ],
    }
    return (
        "Create the first checkpoint plan for a Thai YouTube 16:9 documentary episode.\n"
        "Use the provided research snippets only. Do not invent facts beyond the snippets.\n"
        "Optimize the angle for clickability first, then substance, factual honesty, and visual feasibility.\n"
        "Write all viewer-facing titles, section titles, and thumbnail text in Thai.\n"
        "Write upload_description as two short Thai public-facing paragraphs (roughly 220-600 characters): "
        "no title, chapter timestamps, hashtags, links, or internal planning language.\n"
        "Sections must be 4-7 total. Every section must include an opener beat; use codex_imagegen only "
        "when the total Runware plus Codex imagegen share stays at or below 50 percent.\n"
        "Official media candidates are visual candidates, not factual citations unless they also appear as sources.\n"
        "Use source IDs in each section. If evidence is thin, call that out in risks.\n\n"
        f"INPUT DATA:\n{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
    )


def synthesize_research_plan(
    topic: str,
    research_inputs: dict[str, Any],
    *,
    use_llm: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if use_llm:
        try:
            from llm_provider import generate_text_structured

            raw = generate_text_structured(
                _build_research_prompt(topic, research_inputs),
                system_prompt=(
                    "You are a factual Thai documentary producer. Return only valid JSON. "
                    "Be direct about source gaps and avoid clickbait."
                ),
                schema=_producer_research_schema(),
            )
            parsed = _json_loads_loose(raw)
            if isinstance(parsed, dict):
                return parsed, warnings
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"LLM synthesis failed, used heuristic fallback: {exc}")

    return _heuristic_research_plan(topic, research_inputs), warnings


def _source_ids_for_section(sources: list[dict[str, Any]], offset: int) -> list[str]:
    if not sources:
        return []
    ids = [str(item.get("id")) for item in sources if item.get("id")]
    if not ids:
        return []
    first = ids[offset % len(ids)]
    second = ids[(offset + 1) % len(ids)] if len(ids) > 1 else first
    return list(dict.fromkeys([first, second]))


def _heuristic_research_plan(topic: str, research_inputs: dict[str, Any]) -> dict[str, Any]:
    sources = research_inputs.get("sources", [])
    competitors = research_inputs.get("competitors", [])
    official_media = research_inputs.get("official_media_results", [])
    official = [item for item in sources if item.get("source_type") == "official"]
    source_basis = official or sources
    title_topic = _clean_text(topic)
    sections = []
    section_specs = [
        ("Clickable central question", "Set up the central mystery and why viewers should care.", "hook"),
        ("Essential context", "Give the essential context without slowing down the story.", "explanation"),
        ("What the evidence actually says", "Separate sourced evidence from assumptions.", "evidence"),
        ("What people often misunderstand", "Create contrast and prevent misleading simplification.", "contrast"),
        ("Why it matters", "Bring the implications back to the viewer.", "human_impact"),
        ("Grounded closing", "Close with a grounded takeaway and light CTA.", "transition"),
    ]
    for idx, (title, goal, role) in enumerate(section_specs, start=1):
        source_ids = []  # Heuristic structure is not evidence mapping.
        sections.append(
            {
                "section_index": idx,
                "title": title,
                "narrative_goal": goal,
                "source_ids": source_ids,
                "visual_direction": (
                    "Open on a flat explainer graphic in the episode motif; carry mechanisms, scale and "
                    "what-if beats with flat graphics around one recurring metaphor, and use "
                    "official/verified media wherever the evidence itself is the point. Stay within "
                    "the plan's visual_rules.source_policy caps."
                ),
                "beats": [
                    {
                        "beat_index": 0,
                        "role": "opener",
                        "beat_type": "section_opener",
                        "visual_type": "codex_imagegen",
                        "intent": f"Create a clean no-text visual opener for section {idx}.",
                        "source_preference": "codex_imagegen_if_within_generated_cap",
                        "duration_seconds": 6,
                    },
                    {
                        "beat_index": 1,
                        "role": role,
                        "beat_type": "b_roll",
                        "visual_type": "official_or_stock_video",
                        "intent": goal,
                        "source_preference": "official_verified_then_pexels_pixabay",
                        "duration_seconds": 7,
                    },
                ],
            }
        )

    competitor_patterns = _competitor_patterns(competitors)
    return {
        "topic_profile": {
            "selected_angle": f"Why {title_topic} still feels unresolved",
            "angle_rationale": (
                "Heuristic fallback used available search results to frame the topic as a "
                "clickable factual mystery without overclaiming."
            ),
            "target_audience": "Thai viewers who like clear documentary explainers.",
            "viewer_promise": f"Explain {title_topic} from sourced evidence rather than guesswork.",
            "central_question": f"What makes {title_topic} more important than it first appears?",
            "why_now_or_why_care": "The topic connects to a large question and common misunderstandings.",
            "anti_clickbait_boundary": "Do not overclaim; clearly separate evidence from speculation.",
        },
        "research_summary": (
            f"Collected {len(sources)} source candidates, {len(official_media)} official media candidates, "
            f"and {len(competitors)} competitor/SEO candidates. "
            "This fallback outline should be reviewed by a stronger LLM synthesis pass before production."
        ),
        "section_source_map": [
            {
                "section_index": section["section_index"],
                "source_ids": section["source_ids"],
                "key_claims": ["Claims pending detailed source review in the next pass."],
            }
            for section in sections
        ],
        "sections": sections,
        "competitor_patterns": competitor_patterns,
        "title_options": [
            {
                "role": "curiosity_question",
                "title": f"Why Is {title_topic} Still Unresolved?",
                "rationale": "Uses a question-driven curiosity gap.",
            },
            {
                "role": "concrete_stakes",
                "title": f"{title_topic}: The Part That Changes How We See It",
                "rationale": "Frames the topic around stakes and impact.",
            },
            {
                "role": "documentary_trust",
                "title": f"{title_topic}, Explained Without Hype",
                "rationale": "Signals grounded documentary tone.",
            },
        ],
        "recommended_title": f"Why Is {title_topic} Still Unresolved?",
        "recommended_title_rationale": "Most clickable fallback title while staying non-sensational.",
        "upload_description": "",
        "thumbnail_concept_options": [
            {
                "concept": "curiosity",
                "composition": "One strong focal object, deep contrast, empty space for short Thai text.",
                "text_overlay": "THAI QUESTION TEXT",
                "avoid": ["fake evidence", "overcrowded text", "misleading official logos"],
            },
            {
                "concept": "stakes",
                "composition": "Show scale or consequence visually, with a clear before/after contrast.",
                "text_overlay": "THAI STAKES TEXT",
                "avoid": ["fearmongering", "red alert styling", "brand logos"],
            },
            {
                "concept": "documentary",
                "composition": "Calm cinematic frame with one factual visual anchor.",
                "text_overlay": "THAI DOCUMENTARY TEXT",
                "avoid": ["sensational expression", "fake document", "busy collage"],
            },
        ],
        "risks": [
            "Heuristic fallback cannot fully verify narrative quality.",
            "Review source summaries before moving into script production.",
        ],
    }


def _competitor_patterns(competitors: list[dict[str, Any]]) -> list[str]:
    if not competitors:
        return ["No competitor results found; use factual curiosity instead of copied patterns."]
    patterns: list[str] = []
    titles = " ".join(str(item.get("title", "")) for item in competitors).lower()
    if "?" in titles or "why" in titles:
        patterns.append("Question-led curiosity titles appear in competitor results.")
    if any(word in titles for word in ("mystery", "paradox", "secret", "unknown")):
        patterns.append("Mystery framing appears common; avoid unsupported overclaiming.")
    if any(word in titles for word in ("explained", "documentary", "history")):
        patterns.append("Explainer/documentary framing appears viable.")
    if not patterns:
        patterns.append("Competitor titles vary; prefer a clear Thai curiosity angle.")
    return patterns[:4]


def _normalize_synthesized_plan(payload: dict[str, Any]) -> dict[str, Any]:
    sections = []
    for section_idx, section in enumerate(payload.get("sections") or [], start=1):
        if not isinstance(section, dict):
            continue
        beats = []
        for beat_idx, beat in enumerate(section.get("beats") or [], start=0):
            if not isinstance(beat, dict):
                continue
            beats.append(
                {
                    "beat_index": int(beat.get("beat_index", beat_idx) or beat_idx),
                    "role": _clean_text(beat.get("role"), "explanation"),
                    "beat_type": _clean_text(beat.get("beat_type"), "b_roll"),
                    "visual_type": _clean_text(beat.get("visual_type"), "official_or_stock_video"),
                    "intent": _clean_text(beat.get("intent"), "Support the section narration."),
                    "source_preference": _clean_text(
                        beat.get("source_preference"),
                        "official_verified_then_pexels_pixabay",
                    ),
                    "duration_seconds": float(beat.get("duration_seconds", 7) or 7),
                }
            )
        if not any(str(beat.get("role", "")).lower() == "opener" for beat in beats):
            beats.insert(
                0,
                {
                    "beat_index": 0,
                    "role": "opener",
                    "beat_type": "section_opener",
                    "visual_type": "codex_imagegen",
                    "intent": "Create a clean no-text section opener.",
                    "source_preference": "codex_imagegen_if_within_generated_cap",
                    "duration_seconds": 6,
                },
            )
        sections.append(
            {
                "section_index": section_idx,
                "title": _clean_text(section.get("title"), f"Section {section_idx}"),
                "narrative_goal": _clean_text(section.get("narrative_goal"), "Advance the story."),
                "source_ids": [
                    str(item) for item in (section.get("source_ids") or []) if str(item).strip()
                ],
                "visual_direction": _clean_text(
                    section.get("visual_direction"),
                    "Use opener plus factual/stock supporting visuals.",
                ),
                "beats": beats,
            }
        )
    payload["sections"] = sections
    payload["title_options"] = _ensure_title_options(payload)
    payload["thumbnail_concept_options"] = _ensure_thumbnail_concepts(payload)
    return payload


def _ensure_title_options(payload: dict[str, Any]) -> list[dict[str, str]]:
    topic = _clean_text(payload.get("topic_profile", {}).get("selected_angle"), "the topic")
    roles = ["curiosity_question", "concrete_stakes", "documentary_trust"]
    defaults = {
        "curiosity_question": {
            "title": topic,
            "rationale": "Curiosity-led title based on the selected angle.",
        },
        "concrete_stakes": {
            "title": f"What {topic} changes",
            "rationale": "Stakes-led fallback title.",
        },
        "documentary_trust": {
            "title": f"{topic}, explained without hype",
            "rationale": "Documentary/trust fallback title.",
        },
    }
    by_role: dict[str, dict[str, str]] = {}
    for item in payload.get("title_options") or []:
        if not isinstance(item, dict):
            continue
        role = _clean_text(item.get("role"), "curiosity_question")
        if role not in roles:
            role = roles[len(by_role) % len(roles)]
        by_role.setdefault(
            role,
            {
                "role": role,
                "title": _clean_text(item.get("title"), defaults[role]["title"]),
                "rationale": _clean_text(item.get("rationale"), defaults[role]["rationale"]),
            },
        )
    for role in roles:
        if role not in by_role:
            by_role[role] = {
                "role": role,
                "title": defaults[role]["title"],
                "rationale": defaults[role]["rationale"],
            }
    return [by_role[role] for role in roles]


def _ensure_thumbnail_concepts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = [
        {
            "concept": "curiosity",
            "composition": "One strong focal object, high contrast, short Thai text area.",
            "text_overlay": "THAI QUESTION TEXT",
            "avoid": ["fake evidence", "overcrowded text", "misleading official logos"],
        },
        {
            "concept": "stakes",
            "composition": "A clear scale or consequence contrast with one visual anchor.",
            "text_overlay": "THAI STAKES TEXT",
            "avoid": ["fearmongering", "red alert styling", "brand logos"],
        },
        {
            "concept": "documentary",
            "composition": "Calm cinematic frame with one factual visual anchor.",
            "text_overlay": "THAI DOCUMENTARY TEXT",
            "avoid": ["sensational expression", "fake document", "busy collage"],
        },
    ]
    concepts = []
    for item in payload.get("thumbnail_concept_options") or []:
        if not isinstance(item, dict):
            continue
        concepts.append(
            {
                "concept": _clean_text(item.get("concept"), defaults[len(concepts) % 3]["concept"]),
                "composition": _clean_text(
                    item.get("composition"),
                    defaults[len(concepts) % 3]["composition"],
                ),
                "text_overlay": _clean_text(
                    item.get("text_overlay"),
                    defaults[len(concepts) % 3]["text_overlay"],
                ),
                "avoid": [
                    str(value) for value in (item.get("avoid") or []) if str(value).strip()
                ] or defaults[len(concepts) % 3]["avoid"],
            }
        )
        if len(concepts) >= 3:
            break
    while len(concepts) < 3:
        concepts.append(defaults[len(concepts)])
    return concepts


def apply_research_to_plan(
    plan: dict[str, Any],
    research_inputs: dict[str, Any],
    synthesis: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    synthesis = _normalize_synthesized_plan(synthesis)
    sources = research_inputs.get("sources", []) or []
    valid_source_ids = {str(item.get("id")) for item in sources if isinstance(item, dict) and item.get("id")}
    dropped_source_ids: set[str] = set()
    for section_idx, section in enumerate(synthesis.get("sections", []) or [], start=1):
        if not isinstance(section, dict):
            continue
        section["section_index"] = section_idx
        kept_source_ids = []
        for source_id in section.get("source_ids") or []:
            source_id = str(source_id)
            if source_id in valid_source_ids:
                kept_source_ids.append(source_id)
            else:
                dropped_source_ids.add(source_id)
        section["source_ids"] = kept_source_ids
        if not kept_source_ids:
            warnings.append(f"Section {section_idx} has no valid mapped sources; research review required.")
        beats = section.get("beats") if isinstance(section.get("beats"), list) else []
        opener = [beat for beat in beats if isinstance(beat, dict) and str(beat.get("role", "")).lower() == "opener"]
        others = [beat for beat in beats if isinstance(beat, dict) and str(beat.get("role", "")).lower() != "opener"]
        section["beats"] = (opener[:1] or [
            {
                "role": "opener",
                "beat_type": "section_opener",
                "visual_type": "codex_imagegen",
                "intent": "Create a clean no-text section opener.",
                "source_preference": "codex_imagegen_if_within_generated_cap",
                "duration_seconds": 6,
            }
        ]) + others
        for beat_idx, beat in enumerate(section["beats"]):
            beat["beat_index"] = beat_idx
    if dropped_source_ids:
        warnings.append(
            "Dropped synthesized source ids not present in research inputs: "
            + ", ".join(sorted(dropped_source_ids)[:12])
        )
    synthesis["section_source_map"] = [
        {
            "section_index": section.get("section_index"),
            "source_ids": section.get("source_ids", []),
            "key_claims": ["Use only claims supported by these source IDs."],
        }
        for section in synthesis.get("sections", [])
        if isinstance(section, dict)
    ]
    research = plan.setdefault("research", {})
    minimum_sources = int(research.get("minimum_sources", 3) or 3)
    source_count = len(research_inputs.get("sources", []) or [])
    research.update(
        {
            "status": "complete" if source_count >= minimum_sources else "partial",
            "researched_at": research_inputs.get("researched_at") or _utc_now(),
            "search_profile": research_inputs.get("search_profile", {}),
            "sources": research_inputs.get("sources", []),
            "research_queries": research_inputs.get("queries", []),
            "official_media_results": research_inputs.get("official_media_results", []),
            "youtube_competitor_queries": research_inputs.get("youtube_competitor_queries", []),
            "competitor_queries": research_inputs.get("competitor_queries", []),
            "competitor_results": research_inputs.get("competitors", []),
            "research_summary": synthesis.get("research_summary", ""),
            "section_source_map": synthesis.get("section_source_map", []),
            "competitor_patterns": synthesis.get("competitor_patterns", []),
            "risks": synthesis.get("risks", []),
            "errors": research_inputs.get("errors", []),
            "warnings": warnings,
        }
    )
    plan["topic_profile"] = synthesis.get("topic_profile", plan.get("topic_profile", {}))
    plan["sections"] = synthesis.get("sections", [])

    seo = plan.setdefault("seo_packaging", {})
    seo["competitor_results"] = research_inputs.get("competitors", [])
    seo["competitor_patterns"] = synthesis.get("competitor_patterns", [])
    seo["title_options"] = synthesis.get("title_options", [])
    seo["recommended_title"] = synthesis.get("recommended_title", "")
    seo["recommended_title_rationale"] = synthesis.get("recommended_title_rationale", "")
    seo["upload_description"] = str(synthesis.get("upload_description") or "").strip()
    seo["thumbnail_concept_options"] = synthesis.get("thumbnail_concept_options", [])

    notes = plan.setdefault("notes", [])
    for warning in warnings:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})
    plan["status"] = "checkpoint_pending"
    return plan


def write_research_brief(episode_dir: str | Path, payload: dict[str, Any]) -> Path:
    path = research_brief_path(episode_dir)
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def _write_json_artifact(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    _ensure_dir(target.parent)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return target


def run_research_checkpoint(
    plan_path: str | Path,
    *,
    use_llm: bool = True,
    max_sources: int = 8,
    max_competitors: int = 6,
    fetch_pages: bool = True,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode = plan.get("episode") if isinstance(plan.get("episode"), dict) else {}
    topic = _clean_text(episode.get("topic"))
    if not topic:
        raise ValueError("episode.topic is required before research")
    episode_dir = plan_file.parent

    research_inputs = collect_research_inputs(
        topic,
        max_sources=max_sources,
        max_competitors=max_competitors,
        fetch_pages=fetch_pages,
    )
    synthesis, warnings = synthesize_research_plan(topic, research_inputs, use_llm=use_llm)
    plan = apply_research_to_plan(plan, research_inputs, synthesis, warnings)
    research_brief = {
        "topic": topic,
        "created_at": _utc_now(),
        "inputs": research_inputs,
        "synthesis": synthesis,
        "warnings": warnings,
    }
    brief_path = write_research_brief(episode_dir, research_brief)
    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "checkpoint": html_path,
        "research_brief": brief_path,
    }


def _visual_asset_preview(beat_plans: list[dict[str, Any]], limit: int = 14) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for beat_plan in beat_plans[:limit]:
        qc = beat_plan.get("qc") if isinstance(beat_plan.get("qc"), dict) else {}
        preview.append(
            {
                "asset_plan_id": beat_plan.get("asset_plan_id"),
                "title": (
                    f"{beat_plan.get('asset_plan_id')} - "
                    f"{beat_plan.get('selected_provider')} / {beat_plan.get('selected_media_type')}"
                ),
                "summary": (
                    f"{beat_plan.get('section_title', '')} | "
                    f"{beat_plan.get('role', '')}: {beat_plan.get('selected_title', '')}. "
                    f"QC: {qc.get('status', 'unknown')}."
                ),
                "selected_provider": beat_plan.get("selected_provider"),
                "selected_source_url": beat_plan.get("selected_source_url"),
            }
        )
    return preview


def run_asset_planning_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent
    sections = plan.get("sections") if isinstance(plan.get("sections"), list) else []
    if not sections:
        raise ValueError("sections are required before asset planning; run research first")

    from producer_asset_planner import build_visual_asset_plan

    visual_rules = plan.setdefault("visual_rules", {})
    source_policy = (
        visual_rules.get("source_policy")
        if isinstance(visual_rules.get("source_policy"), dict)
        else default_visual_source_policy()
    )
    visual_rules["source_policy"] = source_policy
    strategy_path = _write_json_artifact(visual_source_strategy_path(episode_dir), source_policy)
    visual_rules["source_strategy_artifact"] = str(strategy_path)

    visual_asset_plan, asset_qc = build_visual_asset_plan(plan)
    visual_path = _write_json_artifact(visual_asset_plan_path(episode_dir), visual_asset_plan)
    qc_path = _write_json_artifact(asset_qc_path(episode_dir), asset_qc)

    summary = visual_asset_plan.get("summary") if isinstance(visual_asset_plan.get("summary"), dict) else {}
    plan["visual_asset_plan"] = {
        "status": visual_asset_plan.get("status", "pending"),
        "planned_at": visual_asset_plan.get("created_at"),
        "artifact": str(visual_path),
        "qc_artifact": str(qc_path),
        "beat_count": summary.get("beat_count", 0),
        "provider_counts": summary.get("provider_counts", {}),
        "qc_status_counts": summary.get("qc_status_counts", {}),
        "visual_policy": summary.get("visual_policy", {}),
        "warnings": summary.get("warnings", []),
        "beat_plan_preview": _visual_asset_preview(visual_asset_plan.get("beat_plans", [])),
    }
    notes = plan.setdefault("notes", [])
    for warning in summary.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "visual_source_strategy": strategy_path,
        "visual_asset_plan": visual_path,
        "asset_qc": qc_path,
        "checkpoint": html_path,
    }


def run_script_draft_checkpoint(
    plan_path: str | Path,
    *,
    use_llm: bool = True,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent
    sections = plan.get("sections") if isinstance(plan.get("sections"), list) else []
    if not sections:
        raise ValueError("sections are required before script drafting; run research first")

    from producer_script_writer import draft_script_package

    package = draft_script_package(plan, use_llm=use_llm)
    script_file = _write_json_artifact(script_path(episode_dir), package.get("scenes", []))
    script_qc_file = _write_json_artifact(script_qc_path(episode_dir), package.get("script_qc", {}))
    fact_file = _write_json_artifact(
        fact_check_report_path(episode_dir),
        package.get("fact_check_report", {}),
    )
    guide_file = pronunciation_guide_path(episode_dir)
    _ensure_dir(guide_file.parent)
    guide_file.write_text(str(package.get("pronunciation_guide_md", "")), encoding="utf-8")

    script_qc = package.get("script_qc") if isinstance(package.get("script_qc"), dict) else {}
    fact_report = (
        package.get("fact_check_report")
        if isinstance(package.get("fact_check_report"), dict)
        else {}
    )
    plan["script_draft"] = {
        "status": script_qc.get("status", "pending"),
        "drafted_at": package.get("created_at") or _utc_now(),
        "script_artifact": str(script_file),
        "script_qc_artifact": str(script_qc_file),
        "fact_check_artifact": str(fact_file),
        "pronunciation_guide_artifact": str(guide_file),
        "scene_count": script_qc.get("scene_count", len(package.get("scenes", []))),
        "chars_no_space": script_qc.get("chars_no_space", 0),
        "length_status": script_qc.get("length_status"),
        "fact_check_status": fact_report.get("status"),
        "warnings": package.get("warnings", []),
    }
    notes = plan.setdefault("notes", [])
    for warning in package.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "script": script_file,
        "script_qc": script_qc_file,
        "fact_check_report": fact_file,
        "pronunciation_guide": guide_file,
        "checkpoint": html_path,
    }


def run_script_expand_checkpoint(
    plan_path: str | Path,
    *,
    target_min: int | None = None,
    target_max: int | None = None,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent
    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")
    with script_file.open("r", encoding="utf-8-sig") as f:
        scenes = json.load(f)
    if not isinstance(scenes, list):
        raise ValueError("script.json must be a list of scene objects")

    from producer_script_writer import expand_script_package

    package = expand_script_package(
        plan,
        scenes,
        target_min=target_min,
        target_max=target_max,
    )
    plan["episode_spec"] = package["episode_spec"]
    script_file = _write_json_artifact(script_path(episode_dir), package.get("scenes", []))
    script_qc_file = _write_json_artifact(script_qc_path(episode_dir), package.get("script_qc", {}))
    fact_file = _write_json_artifact(
        fact_check_report_path(episode_dir),
        package.get("fact_check_report", {}),
    )
    guide_file = pronunciation_guide_path(episode_dir)
    _ensure_dir(guide_file.parent)
    guide_file.write_text(str(package.get("pronunciation_guide_md", "")), encoding="utf-8")

    script_qc = package.get("script_qc") if isinstance(package.get("script_qc"), dict) else {}
    fact_report = (
        package.get("fact_check_report")
        if isinstance(package.get("fact_check_report"), dict)
        else {}
    )
    plan["script_draft"] = {
        "status": script_qc.get("status", "pending"),
        "drafted_at": package.get("created_at") or _utc_now(),
        "script_artifact": str(script_file),
        "script_qc_artifact": str(script_qc_file),
        "fact_check_artifact": str(fact_file),
        "pronunciation_guide_artifact": str(guide_file),
        "scene_count": script_qc.get("scene_count", len(package.get("scenes", []))),
        "chars_no_space": script_qc.get("chars_no_space", 0),
        "length_status": script_qc.get("length_status"),
        "fact_check_status": fact_report.get("status"),
        "warnings": package.get("warnings", []),
        "expanded_from_existing": True,
    }
    notes = plan.setdefault("notes", [])
    for warning in package.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "script": script_file,
        "script_qc": script_qc_file,
        "fact_check_report": fact_file,
        "pronunciation_guide": guide_file,
        "checkpoint": html_path,
    }


def _asset_production_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "entry_count": len(entries),
        "downloaded_count": sum(1 for entry in entries if entry.get("status") == "downloaded"),
        "generated_count": sum(1 for entry in entries if entry.get("status") == "generated"),
        "pending_task_count": sum(1 for entry in entries if entry.get("status") == "task_pending"),
        "failed_count": sum(1 for entry in entries if entry.get("status") == "failed"),
    }


def run_asset_production_checkpoint(
    plan_path: str | Path,
    *,
    dry_run: bool = False,
    allow_stock: bool = False,
    allow_runware: bool = False,
    max_download_mb: int = 80,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    visual_path = Path(plan.get("visual_asset_plan", {}).get("artifact") or visual_asset_plan_path(episode_dir))
    if not visual_path.exists():
        raise FileNotFoundError(f"visual_asset_plan.json not found at {visual_path}; run plan-assets first")
    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")

    visual_asset_plan = load_producer_plan(visual_path)
    with script_file.open("r", encoding="utf-8-sig") as f:
        script = json.load(f)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scene objects")

    if not dry_run:
        require_production_review(plan, script)

    from producer_asset_producer import produce_assets

    package = produce_assets(
        episode_dir=episode_dir,
        visual_asset_plan=visual_asset_plan,
        script=script,
        dry_run=dry_run,
        allow_stock=allow_stock,
        allow_runware=allow_runware,
        max_download_mb=max_download_mb,
    )
    manifest = package.get("asset_manifest", {})
    asset_qc = package.get("asset_qc", {})
    manifest_file = _write_json_artifact(asset_manifest_path(episode_dir), manifest)
    asset_qc_file = _write_json_artifact(asset_qc_path(episode_dir), asset_qc)
    imagegen_file = _write_json_artifact(
        imagegen_tasks_path(episode_dir),
        {"created_at": _utc_now(), "tasks": package.get("imagegen_tasks", [])},
    )
    remotion_file = _write_json_artifact(
        remotion_graphic_tasks_path(episode_dir),
        {"created_at": _utc_now(), "tasks": package.get("remotion_graphic_tasks", [])},
    )

    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    counts = _asset_production_counts(entries)
    plan["asset_production"] = {
        "status": manifest.get("status", "pending"),
        "produced_at": manifest.get("created_at") or _utc_now(),
        "asset_manifest_artifact": str(manifest_file),
        "asset_qc_artifact": str(asset_qc_file),
        "imagegen_tasks_artifact": str(imagegen_file),
        "remotion_graphic_tasks_artifact": str(remotion_file),
        **counts,
        "warnings": manifest.get("warnings", []),
    }
    notes = plan.setdefault("notes", [])
    for warning in manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "asset_manifest": manifest_file,
        "asset_qc": asset_qc_file,
        "imagegen_tasks": imagegen_file,
        "remotion_graphic_tasks": remotion_file,
        "checkpoint": html_path,
    }


def run_asset_results_checkpoint(
    plan_path: str | Path,
    *,
    source_dir: str | Path | None = None,
    force: bool = False,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"asset_manifest.json not found at {manifest_file}; run produce-assets first"
        )
    manifest = load_producer_plan(manifest_file)

    from producer_asset_producer import apply_asset_results

    package = apply_asset_results(
        episode_dir=episode_dir,
        asset_manifest=manifest,
        source_dir=source_dir,
        force=force,
    )
    updated_manifest = package.get("asset_manifest", {})
    asset_qc = package.get("asset_qc", {})
    manifest_file = _write_json_artifact(asset_manifest_path(episode_dir), updated_manifest)
    asset_qc_file = _write_json_artifact(asset_qc_path(episode_dir), asset_qc)

    entries = updated_manifest.get("entries") if isinstance(updated_manifest.get("entries"), list) else []
    counts = _asset_production_counts(entries)
    plan["asset_production"] = {
        "status": updated_manifest.get("status", "pending"),
        "produced_at": updated_manifest.get("updated_at")
        or updated_manifest.get("created_at")
        or _utc_now(),
        "asset_manifest_artifact": str(manifest_file),
        "asset_qc_artifact": str(asset_qc_file),
        "imagegen_tasks_artifact": plan.get("asset_production", {}).get("imagegen_tasks_artifact"),
        "remotion_graphic_tasks_artifact": plan.get("asset_production", {}).get(
            "remotion_graphic_tasks_artifact"
        ),
        **counts,
        "warnings": updated_manifest.get("warnings", []),
    }
    notes = plan.setdefault("notes", [])
    result_application = updated_manifest.get("result_application", {})
    notes.append(
        {
            "ts": _utc_now(),
            "level": "info",
            "message": (
                "asset result application: "
                f"{result_application.get('applied_count', 0)} applied, "
                f"{result_application.get('missing_count', 0)} missing"
            ),
        }
    )
    for warning in updated_manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "asset_manifest": manifest_file,
        "asset_qc": asset_qc_file,
        "checkpoint": html_path,
    }


def run_graphic_render_checkpoint(
    plan_path: str | Path,
    *,
    placeholder_openers: bool = False,
    force: bool = False,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")
    with script_file.open("r", encoding="utf-8-sig") as f:
        script = json.load(f)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scene objects")

    manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"asset_manifest.json not found at {manifest_file}; run produce-assets first"
        )
    asset_manifest = load_producer_plan(manifest_file)

    from producer_asset_producer import _asset_qc
    from producer_graphic_renderer import render_graphic_assets

    package = render_graphic_assets(
        episode_dir=episode_dir,
        asset_manifest=asset_manifest,
        script=script,
        placeholder_openers=placeholder_openers,
        force=force,
    )
    updated_manifest = package.get("asset_manifest", {})
    graphic_report = package.get("graphic_report", {})
    asset_qc = _asset_qc(
        updated_manifest.get("entries", []) if isinstance(updated_manifest, dict) else [],
        updated_manifest.get("warnings", []) if isinstance(updated_manifest, dict) else [],
    )

    manifest_file = _write_json_artifact(asset_manifest_path(episode_dir), updated_manifest)
    asset_qc_file = _write_json_artifact(asset_qc_path(episode_dir), asset_qc)
    report_file = _write_json_artifact(graphic_render_report_path(episode_dir), graphic_report)

    entries = updated_manifest.get("entries") if isinstance(updated_manifest.get("entries"), list) else []
    plan["asset_production"] = {
        **(
            plan.get("asset_production")
            if isinstance(plan.get("asset_production"), dict)
            else {}
        ),
        "status": updated_manifest.get("status", "pending"),
        "produced_at": updated_manifest.get("updated_at") or _utc_now(),
        "asset_manifest_artifact": str(manifest_file),
        "asset_qc_artifact": str(asset_qc_file),
        "graphic_render_report_artifact": str(report_file),
        "entry_count": len(entries),
        "downloaded_count": sum(1 for entry in entries if entry.get("status") == "downloaded"),
        "generated_count": sum(1 for entry in entries if entry.get("status") == "generated"),
        "pending_task_count": sum(1 for entry in entries if entry.get("status") == "task_pending"),
        "failed_count": sum(1 for entry in entries if entry.get("status") == "failed"),
        "warnings": updated_manifest.get("warnings", []),
    }
    notes = plan.setdefault("notes", [])
    for warning in graphic_report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "asset_manifest": manifest_file,
        "asset_qc": asset_qc_file,
        "graphic_render_report": report_file,
        "checkpoint": html_path,
    }


def _audio_production_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "scene_count": len(entries),
        "generated_count": sum(1 for entry in entries if entry.get("status") == "generated"),
        "skipped_existing_count": sum(
            1 for entry in entries if entry.get("status") == "skipped_existing"
        ),
        "planned_count": sum(1 for entry in entries if entry.get("status") == "planned"),
        "failed_count": sum(1 for entry in entries if entry.get("status") == "failed"),
    }


def run_tts_production_checkpoint(
    plan_path: str | Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    tone_preset: str | None = None,
    limit: int | None = None,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")
    with script_file.open("r", encoding="utf-8-sig") as f:
        script = json.load(f)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scene objects")

    if not dry_run:
        require_production_review(plan, script)

    audio_rules = plan.get("audio_rules") if isinstance(plan.get("audio_rules"), dict) else {}
    requested_tone = (
        tone_preset
        or audio_rules.get("tone_preset")
        or audio_rules.get("gemini_tts_tone_preset")
        or "natural_storyteller"
    )
    guide_path = pronunciation_guide_path(episode_dir)

    from producer_tts import produce_tts

    package = produce_tts(
        episode_dir=episode_dir,
        script=script,
        pronunciation_guide_path=guide_path if guide_path.exists() else None,
        dry_run=dry_run,
        force=force,
        tone_preset=str(requested_tone),
        limit=limit,
    )
    manifest = package.get("tts_manifest", {})
    tts_qc = package.get("tts_qc", {})
    manifest_file = _write_json_artifact(tts_manifest_path(episode_dir), manifest)
    tts_qc_file = _write_json_artifact(tts_qc_path(episode_dir), tts_qc)

    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    counts = _audio_production_counts(entries)
    plan["audio_production"] = {
        "status": manifest.get("status", "pending"),
        "produced_at": manifest.get("created_at") or _utc_now(),
        "tts_manifest_artifact": str(manifest_file),
        "tts_qc_artifact": str(tts_qc_file),
        **counts,
        "total_duration_seconds": manifest.get("total_duration_seconds", 0),
        "estimated_cost_usd": manifest.get("estimated_cost_usd", 0.0),
        "warnings": manifest.get("warnings", []),
    }
    notes = plan.setdefault("notes", [])
    for warning in manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "tts_manifest": manifest_file,
        "tts_qc": tts_qc_file,
        "checkpoint": html_path,
    }


def run_audio_qc_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_file = script_path(episode_dir)
    script: list[Any] = []
    if script_file.exists():
        with script_file.open("r", encoding="utf-8-sig") as f:
            loaded_script = json.load(f)
        if isinstance(loaded_script, list):
            script = loaded_script

    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}

    from producer_audio_qc import build_audio_qc

    report = build_audio_qc(
        episode_dir=episode_dir,
        script=script,
        tts_manifest=tts_manifest,
    )
    report_file = _write_json_artifact(audio_qc_path(episode_dir), report)

    audio_production = (
        plan.get("audio_production")
        if isinstance(plan.get("audio_production"), dict)
        else {}
    )
    counts = report.get("status_counts") if isinstance(report.get("status_counts"), dict) else {}
    status = str(report.get("status") or "blocked")
    audio_production.update(
        {
            "audio_qc_artifact": str(report_file),
            "audio_qc_status": status,
            "audio_qc_checked_at": report.get("created_at") or _utc_now(),
            "audio_qc_pass_count": int(counts.get("pass", 0) or 0),
            "audio_qc_review_count": int(counts.get("review", 0) or 0),
            "audio_qc_blocked_count": int(counts.get("blocked", 0) or 0),
        }
    )
    if status == "blocked":
        audio_production["status"] = "blocked"
    plan["audio_production"] = audio_production

    notes = plan.setdefault("notes", [])
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "audio_qc": report_file,
        "checkpoint": html_path,
    }


def run_broll_expansion_checkpoint(
    plan_path: str | Path,
    *,
    target_seconds: float = 6.5,
    min_seconds: float = VISUAL_BEAT_SECONDS_MIN,
    max_seconds: float = VISUAL_BEAT_SECONDS_MAX,
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
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")
    with script_file.open("r", encoding="utf-8-sig") as f:
        script = json.load(f)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scene objects")

    manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"asset_manifest.json not found at {manifest_file}; run produce-assets first"
        )
    asset_manifest = load_producer_plan(manifest_file)

    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}

    from producer_asset_producer import _asset_qc
    from producer_broll_expander import expand_broll_timeline

    try:
        from config import get_podcast_outro_hold_seconds

        last_scene_extra_seconds = max(0.0, float(get_podcast_outro_hold_seconds()))
    except Exception:  # noqa: BLE001
        last_scene_extra_seconds = 0.0

    package = expand_broll_timeline(
        episode_dir=episode_dir,
        script=script,
        asset_manifest=asset_manifest,
        tts_manifest=tts_manifest,
        target_seconds=target_seconds,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
        last_scene_extra_seconds=last_scene_extra_seconds,
        fresh_official=fresh_official,
        fresh_official_limit=fresh_official_limit,
        fresh_official_max_download_mb=fresh_official_max_download_mb,
        allow_stock=allow_stock,
        stock_max_slots=stock_max_slots,
        allow_runware=allow_runware,
        runware_max_slots=runware_max_slots,
        max_visual_repeats=max_visual_repeats,
        force=force,
        legacy_keyword_tables=legacy_keyword_tables,
    )
    updated_manifest = package.get("asset_manifest", {})
    visual_timeline = package.get("broll_timeline", {})
    entries = (
        updated_manifest.get("entries", [])
        if isinstance(updated_manifest.get("entries"), list)
        else []
    )
    asset_qc = _asset_qc(
        entries,
        updated_manifest.get("warnings", []) if isinstance(updated_manifest, dict) else [],
    )
    expansion_summary = (
        updated_manifest.get("broll_expansion", {})
        if isinstance(updated_manifest.get("broll_expansion"), dict)
        else {}
    )
    slot_durations = [
        float(slot.get("duration_seconds") or 0.0)
        for scene in visual_timeline.get("scenes", [])
        if isinstance(scene, dict)
        for slot in scene.get("slots", [])
        if isinstance(slot, dict)
    ]
    average_slot_seconds = (
        round(sum(slot_durations) / len(slot_durations), 3) if slot_durations else 0.0
    )

    manifest_file = _write_json_artifact(asset_manifest_path(episode_dir), updated_manifest)
    asset_qc_file = _write_json_artifact(asset_qc_path(episode_dir), asset_qc)
    visual_timeline_file = _write_json_artifact(visual_timeline_path(episode_dir), visual_timeline)
    report_file = _write_json_artifact(
        broll_expansion_report_path(episode_dir),
        {
            "created_at": _utc_now(),
            "status": visual_timeline.get("status", "blocked"),
            "summary": expansion_summary,
            "scene_count": visual_timeline.get("scene_count", 0),
            "asset_count": visual_timeline.get("asset_count", 0),
            "source_asset_count": visual_timeline.get("source_asset_count", 0),
            "derived_asset_count": visual_timeline.get("derived_asset_count", 0),
            "fresh_official_candidate_count": visual_timeline.get("fresh_official_candidate_count", 0),
            "fresh_official_download_count": visual_timeline.get("fresh_official_download_count", 0),
            "fresh_official_download_fail_count": visual_timeline.get("fresh_official_download_fail_count", 0),
            "local_graphic_count": visual_timeline.get("local_graphic_count", 0),
            "stock_video_count": visual_timeline.get("stock_video_count", 0),
            "stock_video_fail_count": visual_timeline.get("stock_video_fail_count", 0),
            "runware_broll_count": visual_timeline.get("runware_broll_count", 0),
            "runware_broll_fail_count": visual_timeline.get("runware_broll_fail_count", 0),
            "repeat_guard": visual_timeline.get("repeat_guard", {}),
            "visual_policy": visual_timeline.get("visual_policy", {}),
            "average_slot_seconds": average_slot_seconds,
            "warnings": visual_timeline.get("warnings", []),
            "errors": visual_timeline.get("errors", []),
            "visual_timeline_artifact": str(visual_timeline_file),
        },
    )

    counts = _asset_production_counts(entries)
    plan["asset_production"] = {
        **(
            plan.get("asset_production")
            if isinstance(plan.get("asset_production"), dict)
            else {}
        ),
        "status": visual_timeline.get("status", "blocked"),
        "produced_at": updated_manifest.get("updated_at") or _utc_now(),
        "asset_manifest_artifact": str(manifest_file),
        "asset_qc_artifact": str(asset_qc_file),
        "visual_timeline_artifact": str(visual_timeline_file),
        "broll_expansion_report_artifact": str(report_file),
        "visual_slot_count": visual_timeline.get("asset_count", len(entries)),
        "derived_broll_count": visual_timeline.get("derived_asset_count", 0),
        "fresh_official_candidate_count": visual_timeline.get("fresh_official_candidate_count", 0),
        "fresh_official_download_count": visual_timeline.get("fresh_official_download_count", 0),
        "fresh_official_download_fail_count": visual_timeline.get("fresh_official_download_fail_count", 0),
        "local_graphic_count": visual_timeline.get("local_graphic_count", 0),
        "stock_video_count": visual_timeline.get("stock_video_count", 0),
        "stock_video_fail_count": visual_timeline.get("stock_video_fail_count", 0),
        "runware_broll_count": visual_timeline.get("runware_broll_count", 0),
        "runware_broll_fail_count": visual_timeline.get("runware_broll_fail_count", 0),
        "repeat_guard": visual_timeline.get("repeat_guard", {}),
        "visual_policy": visual_timeline.get("visual_policy", {}),
        "average_slot_seconds": average_slot_seconds,
        **counts,
        "warnings": visual_timeline.get("warnings", []),
    }

    stale_message = "stale after b-roll expansion; rerun this stage"
    for stage_name in (
        "render_preflight",
        "render",
        "final_qc",
        "cost_report",
        "final_report",
        "upload_pack",
        "smoke_gate",
    ):
        stage = plan.get(stage_name) if isinstance(plan.get(stage_name), dict) else {}
        stage["status"] = "pending"
        stage["warnings"] = [stale_message]
        plan[stage_name] = stage

    notes = plan.setdefault("notes", [])
    notes.append(
        {
            "ts": _utc_now(),
            "level": "info",
            "message": (
                "expanded b-roll timeline to "
                f"{visual_timeline.get('asset_count', len(entries))} visual slots "
                f"(avg {average_slot_seconds}s)"
            ),
        }
    )
    for error in visual_timeline.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "asset_manifest": manifest_file,
        "asset_qc": asset_qc_file,
        "visual_timeline": visual_timeline_file,
        "broll_expansion_report": report_file,
        "checkpoint": html_path,
    }


def run_render_preflight_checkpoint(
    plan_path: str | Path,
    *,
    render_image_only: bool = False,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_file = script_path(episode_dir)
    if not script_file.exists():
        raise FileNotFoundError(f"script.json not found at {script_file}; run draft-script first")
    with script_file.open("r", encoding="utf-8-sig") as f:
        script = json.load(f)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scene objects")

    asset_manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    asset_manifest = load_producer_plan(asset_manifest_file) if asset_manifest_file.exists() else {}
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}

    from producer_render_preflight import build_render_preflight

    report = build_render_preflight(
        root_dir=ROOT_DIR,
        episode_dir=episode_dir,
        script=script,
        asset_manifest=asset_manifest,
        tts_manifest=tts_manifest,
        render_image_only=render_image_only,
    )
    preflight_file = _write_json_artifact(render_preflight_path(episode_dir), report)
    props_file = _write_json_artifact(
        render_props_preview_path(episode_dir),
        report.get("props_preview", {}),
    )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    plan["render_preflight"] = {
        "status": report.get("status", "pending"),
        "checked_at": report.get("created_at") or _utc_now(),
        "render_preflight_artifact": str(preflight_file),
        "render_props_preview_artifact": str(props_file),
        "scene_count": summary.get("scene_count", 0),
        "ready_scene_count": summary.get("ready_scene_count", 0),
        "missing_audio_count": summary.get("missing_audio_count", 0),
        "missing_asset_count": summary.get("missing_asset_count", 0),
        "asset_count": summary.get("asset_count", 0),
        "render_duration_seconds": summary.get("render_duration_seconds", 0),
        "estimated_frames": summary.get("estimated_frames", 0),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }
    notes = plan.setdefault("notes", [])
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "render_preflight": preflight_file,
        "render_props_preview": props_file,
        "checkpoint": html_path,
    }


def run_render_video_checkpoint(
    plan_path: str | Path,
    *,
    no_render: bool = False,
    force: bool = False,
    timeout_seconds: int = 7200,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    preflight_file = Path(
        plan.get("render_preflight", {}).get("render_preflight_artifact")
        or render_preflight_path(episode_dir)
    )
    if not preflight_file.exists():
        preflight_outputs = run_render_preflight_checkpoint(plan_file)
        preflight_file = preflight_outputs["render_preflight"]
        plan = load_producer_plan(plan_file)
    preflight = load_producer_plan(preflight_file)

    from producer_renderer import orchestrate_render

    manifest = orchestrate_render(
        root_dir=ROOT_DIR,
        episode_dir=episode_dir,
        preflight=preflight,
        no_render=no_render,
        force=force,
        timeout_seconds=timeout_seconds,
    )
    manifest_file = _write_json_artifact(render_manifest_path(episode_dir), manifest)

    props_source = Path(str(manifest.get("render_props_path") or render_props_path(episode_dir)))
    if props_source.exists() and props_source.resolve() != render_props_path(episode_dir).resolve():
        props_payload = load_producer_plan(props_source)
        props_file = _write_json_artifact(render_props_path(episode_dir), props_payload)
    else:
        props_file = props_source if props_source.exists() else render_props_path(episode_dir)

    # A render can run for an hour; re-read so plan edits made meanwhile (seo_packaging) survive.
    plan = load_producer_plan(plan_file)
    plan["render"] = {
        "status": manifest.get("status", "pending"),
        "rendered_at": manifest.get("completed_at") or manifest.get("created_at") or _utc_now(),
        "render_manifest_artifact": str(manifest_file),
        "render_props_artifact": str(props_file),
        "log_artifact": str(manifest.get("log_path") or episode_dir / "producer_render.log"),
        "final_video_path": manifest.get("final_video_path"),
        "raw_video_path": manifest.get("raw_video_path"),
        "scene_count": manifest.get("scene_count", 0),
        "render_duration_seconds": manifest.get("render_duration_seconds", 0),
        "final_video_bytes": manifest.get("final_video_bytes", 0),
        "warnings": manifest.get("warnings", []),
        "errors": manifest.get("errors", []),
    }
    notes = plan.setdefault("notes", [])
    for error in manifest.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "render_manifest": manifest_file,
        "render_props": props_file,
        "checkpoint": html_path,
    }


def run_final_qc_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    render_manifest_file = Path(
        plan.get("render", {}).get("render_manifest_artifact")
        or render_manifest_path(episode_dir)
    )
    asset_manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    preflight_file = Path(
        plan.get("render_preflight", {}).get("render_preflight_artifact")
        or render_preflight_path(episode_dir)
    )
    render_manifest = load_producer_plan(render_manifest_file) if render_manifest_file.exists() else {}
    asset_manifest = load_producer_plan(asset_manifest_file) if asset_manifest_file.exists() else {}
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}
    preflight = load_producer_plan(preflight_file) if preflight_file.exists() else {}

    from producer_final_qc import build_final_qc

    report = build_final_qc(
        episode_dir=episode_dir,
        render_manifest=render_manifest,
        asset_manifest=asset_manifest,
        tts_manifest=tts_manifest,
        render_preflight=preflight,
    )
    qc_file = _write_json_artifact(final_qc_path(episode_dir), report)
    fmt = report.get("format") if isinstance(report.get("format"), dict) else {}
    video = report.get("video") if isinstance(report.get("video"), dict) else {}
    audio = report.get("audio") if isinstance(report.get("audio"), dict) else {}
    plan["final_qc"] = {
        "status": report.get("status", "pending"),
        "checked_at": report.get("created_at") or _utc_now(),
        "final_qc_artifact": str(qc_file),
        "final_video_path": report.get("final_video_path"),
        "duration_seconds": fmt.get("duration_seconds", 0),
        "resolution": (
            f"{video.get('width')}x{video.get('height')}"
            if video.get("width") and video.get("height")
            else ""
        ),
        "fps": video.get("fps", 0),
        "has_audio": bool(audio.get("codec_name")),
        "file_bytes": report.get("file_bytes", 0),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }
    notes = plan.setdefault("notes", [])
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "final_qc": qc_file,
        "checkpoint": html_path,
    }


def run_cost_report_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    asset_manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    render_manifest_file = Path(
        plan.get("render", {}).get("render_manifest_artifact")
        or render_manifest_path(episode_dir)
    )
    final_qc_file = Path(
        plan.get("final_qc", {}).get("final_qc_artifact")
        or final_qc_path(episode_dir)
    )
    preflight_file = Path(
        plan.get("render_preflight", {}).get("render_preflight_artifact")
        or render_preflight_path(episode_dir)
    )

    asset_manifest = load_producer_plan(asset_manifest_file) if asset_manifest_file.exists() else {}
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}
    render_manifest = load_producer_plan(render_manifest_file) if render_manifest_file.exists() else {}
    final_qc = load_producer_plan(final_qc_file) if final_qc_file.exists() else {}
    preflight = load_producer_plan(preflight_file) if preflight_file.exists() else {}

    from producer_cost_report import build_cost_report

    report = build_cost_report(
        episode_dir=episode_dir,
        plan=plan,
        tts_manifest=tts_manifest,
        asset_manifest=asset_manifest,
        render_manifest=render_manifest,
        final_qc=final_qc,
        render_preflight=preflight,
    )
    report_file = _write_json_artifact(cost_report_path(episode_dir), report)
    totals = report.get("totals") if isinstance(report.get("totals"), dict) else {}
    budget_state = report.get("budget") if isinstance(report.get("budget"), dict) else {}
    plan["cost_report"] = {
        "status": report.get("status", "pending"),
        "reported_at": report.get("created_at") or _utc_now(),
        "cost_report_artifact": str(report_file),
        "estimated_total_cost_usd": totals.get("estimated_total_cost_usd", 0),
        "new_cost_this_run_usd": totals.get("new_cost_this_run_usd", 0),
        "remaining_estimated_cost_usd": totals.get("remaining_estimated_cost_usd", 0),
        "unknown_cost_item_count": totals.get("unknown_cost_item_count", 0),
        "budget_status": budget_state.get("status", "pending"),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }
    budget = plan.setdefault("budget", {})
    budget["estimated_cost"] = totals.get("estimated_total_cost_usd", 0)
    runtime = report.get("runtime") if isinstance(report.get("runtime"), dict) else {}
    runtime_seconds = float(runtime.get("planned_duration_seconds") or runtime.get("final_duration_seconds") or 0)
    budget["estimated_runtime_minutes"] = round(runtime_seconds / 60, 2) if runtime_seconds else None

    notes = plan.setdefault("notes", [])
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "cost_report": report_file,
        "checkpoint": html_path,
    }


def run_final_report_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    cost_file = Path(
        plan.get("cost_report", {}).get("cost_report_artifact")
        or cost_report_path(episode_dir)
    )
    if not cost_file.exists():
        run_cost_report_checkpoint(plan_file)
        plan = load_producer_plan(plan_file)
        cost_file = Path(
            plan.get("cost_report", {}).get("cost_report_artifact")
            or cost_report_path(episode_dir)
        )

    asset_manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    render_manifest_file = Path(
        plan.get("render", {}).get("render_manifest_artifact")
        or render_manifest_path(episode_dir)
    )
    final_qc_file = Path(
        plan.get("final_qc", {}).get("final_qc_artifact")
        or final_qc_path(episode_dir)
    )

    cost_report = load_producer_plan(cost_file) if cost_file.exists() else {}
    asset_manifest = load_producer_plan(asset_manifest_file) if asset_manifest_file.exists() else {}
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}
    render_manifest = load_producer_plan(render_manifest_file) if render_manifest_file.exists() else {}
    final_qc = load_producer_plan(final_qc_file) if final_qc_file.exists() else {}

    from producer_final_report import build_final_report

    report = build_final_report(
        episode_dir=episode_dir,
        plan=plan,
        cost_report=cost_report,
        final_qc=final_qc,
        asset_manifest=asset_manifest,
        tts_manifest=tts_manifest,
        render_manifest=render_manifest,
    )
    output_path = final_report_path(episode_dir)
    _ensure_dir(output_path.parent)
    output_path.write_text(str(report.get("html") or ""), encoding="utf-8")

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    plan["final_report"] = {
        "status": report.get("status", "pending"),
        "reported_at": report.get("created_at") or _utc_now(),
        "final_report_artifact": str(output_path),
        "final_video_path": summary.get("final_video_path"),
        "final_qc_status": summary.get("final_qc_status", "pending"),
        "budget_status": summary.get("budget_status", "pending"),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }

    notes = plan.setdefault("notes", [])
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "final_report": output_path,
        "checkpoint": html_path,
    }


def run_upload_pack_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    final_qc_file = Path(
        plan.get("final_qc", {}).get("final_qc_artifact")
        or final_qc_path(episode_dir)
    )
    cost_file = Path(
        plan.get("cost_report", {}).get("cost_report_artifact")
        or cost_report_path(episode_dir)
    )
    final_report_file = Path(
        plan.get("final_report", {}).get("final_report_artifact")
        or final_report_path(episode_dir)
    )
    if not cost_file.exists():
        run_cost_report_checkpoint(plan_file)
        plan = load_producer_plan(plan_file)
        cost_file = Path(
            plan.get("cost_report", {}).get("cost_report_artifact")
            or cost_report_path(episode_dir)
        )
    if not final_report_file.exists():
        run_final_report_checkpoint(plan_file)
        plan = load_producer_plan(plan_file)
        final_report_file = Path(
            plan.get("final_report", {}).get("final_report_artifact")
            or final_report_path(episode_dir)
        )

    final_qc = load_producer_plan(final_qc_file) if final_qc_file.exists() else {}
    cost_report = load_producer_plan(cost_file) if cost_file.exists() else {}
    render_state = plan.get("render") if isinstance(plan.get("render"), dict) else {}
    render_props_file = Path(
        str(render_state.get("render_props_artifact") or render_props_path(episode_dir))
    )
    if not render_props_file.exists():
        render_props_file = render_props_path(episode_dir)
    render_props = load_producer_plan(render_props_file) if render_props_file.exists() else {}

    from producer_upload_pack import write_upload_pack

    manifest = write_upload_pack(
        episode_dir=episode_dir,
        plan=plan,
        final_qc=final_qc,
        cost_report=cost_report,
        final_report_path=final_report_file,
        render_props=render_props,
    )
    manifest_file = upload_pack_manifest_path(episode_dir)
    files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    plan["upload_pack"] = {
        "status": manifest.get("status", "pending"),
        "created_at": manifest.get("created_at") or _utc_now(),
        "upload_pack_dir": files.get("upload_pack_dir") or str(upload_pack_dir(episode_dir)),
        "manifest_artifact": files.get("manifest") or str(manifest_file),
        "metadata_artifact": files.get("metadata"),
        "root_metadata_artifact": files.get("root_metadata"),
        "thumbnail_brief_artifact": files.get("thumbnail_brief_html"),
        "timestamps_artifact": files.get("timestamps"),
        "description_source": (
            manifest.get("description_review", {}).get("source")
            if isinstance(manifest.get("description_review"), dict)
            else None
        ),
        "chapter_count": (
            manifest.get("description_review", {}).get("chapter_count")
            if isinstance(manifest.get("description_review"), dict)
            else 0
        ),
        "warnings": manifest.get("warnings", []),
        "errors": manifest.get("errors", []),
    }

    notes = plan.setdefault("notes", [])
    for error in manifest.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    # Refresh final_report.html so its artifact checklist sees upload_pack/.
    run_final_report_checkpoint(saved_plan)
    plan = load_producer_plan(saved_plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "upload_pack_manifest": manifest_file,
        "upload_pack_dir": upload_pack_dir(episode_dir),
        "checkpoint": html_path,
    }


def run_smoke_gate_checkpoint(plan_path: str | Path) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent

    script_qc_file = Path(
        plan.get("script_draft", {}).get("script_qc_artifact")
        or script_qc_path(episode_dir)
    )
    asset_manifest_file = Path(
        plan.get("asset_production", {}).get("asset_manifest_artifact")
        or asset_manifest_path(episode_dir)
    )
    asset_qc_file = Path(
        plan.get("asset_production", {}).get("asset_qc_artifact")
        or asset_qc_path(episode_dir)
    )
    tts_manifest_file = Path(
        plan.get("audio_production", {}).get("tts_manifest_artifact")
        or tts_manifest_path(episode_dir)
    )
    tts_qc_file = Path(
        plan.get("audio_production", {}).get("tts_qc_artifact")
        or tts_qc_path(episode_dir)
    )
    render_preflight_file = Path(
        plan.get("render_preflight", {}).get("render_preflight_artifact")
        or render_preflight_path(episode_dir)
    )
    render_manifest_file = Path(
        plan.get("render", {}).get("render_manifest_artifact")
        or render_manifest_path(episode_dir)
    )
    final_qc_file = Path(
        plan.get("final_qc", {}).get("final_qc_artifact")
        or final_qc_path(episode_dir)
    )
    cost_file = Path(
        plan.get("cost_report", {}).get("cost_report_artifact")
        or cost_report_path(episode_dir)
    )
    final_report_file = Path(
        plan.get("final_report", {}).get("final_report_artifact")
        or final_report_path(episode_dir)
    )
    upload_manifest_file = Path(
        plan.get("upload_pack", {}).get("manifest_artifact")
        or upload_pack_manifest_path(episode_dir)
    )

    script_qc = load_producer_plan(script_qc_file) if script_qc_file.exists() else {}
    asset_manifest = load_producer_plan(asset_manifest_file) if asset_manifest_file.exists() else {}
    asset_qc = load_producer_plan(asset_qc_file) if asset_qc_file.exists() else {}
    tts_manifest = load_producer_plan(tts_manifest_file) if tts_manifest_file.exists() else {}
    tts_qc = load_producer_plan(tts_qc_file) if tts_qc_file.exists() else {}
    render_preflight = (
        load_producer_plan(render_preflight_file) if render_preflight_file.exists() else {}
    )
    render_manifest = (
        load_producer_plan(render_manifest_file) if render_manifest_file.exists() else {}
    )
    final_qc = load_producer_plan(final_qc_file) if final_qc_file.exists() else {}
    cost_report = load_producer_plan(cost_file) if cost_file.exists() else {}
    final_report = (
        {"status": plan.get("final_report", {}).get("status", "pending")}
        if final_report_file.exists()
        else {}
    )
    upload_pack = load_producer_plan(upload_manifest_file) if upload_manifest_file.exists() else {}

    from producer_smoke_gate import build_smoke_gate

    report = build_smoke_gate(
        episode_dir=episode_dir,
        plan=plan,
        script_qc=script_qc,
        asset_manifest=asset_manifest,
        asset_qc=asset_qc,
        tts_manifest=tts_manifest,
        tts_qc=tts_qc,
        render_preflight=render_preflight,
        render_manifest=render_manifest,
        final_qc=final_qc,
        cost_report=cost_report,
        final_report=final_report,
        upload_pack=upload_pack,
    )
    report_file = _write_json_artifact(smoke_gate_path(episode_dir), report)
    gates = report.get("gates") if isinstance(report.get("gates"), list) else []
    plan["smoke_gate"] = {
        "status": report.get("status", "pending"),
        "checked_at": report.get("created_at") or _utc_now(),
        "smoke_gate_artifact": str(report_file),
        "overall_score": report.get("overall_score", 0),
        "blocking_gate_count": sum(1 for gate in gates if isinstance(gate, dict) and gate.get("blocking")),
        "review_gate_count": sum(1 for gate in gates if isinstance(gate, dict) and gate.get("status") == "review"),
        "next_actions": report.get("next_actions", []),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
    }

    notes = plan.setdefault("notes", [])
    for error in report.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in report.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "smoke_gate": report_file,
        "checkpoint": html_path,
    }


def run_provider_smoke_checkpoint(
    plan_path: str | Path,
    *,
    topic: str | None = None,
    allow_network: bool = False,
    allow_gemini_tts: bool = False,
    timeout_seconds: int = 60,
) -> dict[str, Path]:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    episode_dir = plan_file.parent
    episode = plan.get("episode") if isinstance(plan.get("episode"), dict) else {}
    smoke_topic = topic or str(episode.get("topic") or "Mars rover")

    from producer_provider_smoke import run_provider_smoke

    manifest = run_provider_smoke(
        episode_dir=episode_dir,
        topic=smoke_topic,
        allow_network=allow_network,
        allow_gemini_tts=allow_gemini_tts,
        timeout_seconds=timeout_seconds,
    )
    manifest_file = provider_smoke_manifest_path(episode_dir)
    plan["provider_smoke"] = {
        "status": manifest.get("status", "pending"),
        "checked_at": manifest.get("created_at") or _utc_now(),
        "provider_smoke_dir": str(provider_smoke_dir(episode_dir)),
        "manifest_artifact": str(manifest_file),
        "live_pass_count": manifest.get("live_pass_count", 0),
        "allow_network": bool(manifest.get("allow_network")),
        "allow_gemini_tts": bool(manifest.get("allow_gemini_tts")),
        "warnings": manifest.get("warnings", []),
        "errors": manifest.get("errors", []),
    }

    notes = plan.setdefault("notes", [])
    for error in manifest.get("errors", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "error", "message": error})
    for warning in manifest.get("warnings", [])[:10]:
        notes.append({"ts": _utc_now(), "level": "warning", "message": warning})

    saved_plan = save_producer_plan(episode_dir, plan)
    html_path = write_checkpoint_html(episode_dir, plan)
    return {
        "plan": saved_plan,
        "provider_smoke_manifest": manifest_file,
        "provider_smoke_dir": provider_smoke_dir(episode_dir),
        "checkpoint": html_path,
    }


def _status_class(value: str) -> str:
    if value in {"complete", "checkpoint_approved", "ready", "pass"}:
        return "ok"
    if value in {"blocked"}:
        return "bad"
    if value in {"in_progress", "needs_audio", "needs_assets", "planned", "needs_tasks"}:
        return "warn"
    return "muted"


def _badge(value: Any, label: str | None = None) -> str:
    text = _html(label or value)
    cls = _status_class(str(value or "").lower())
    return f'<span class="badge {cls}">{text}</span>'


def _render_items(items: list[Any], empty: str = "Pending") -> str:
    if not items:
        return f'<p class="empty">{_html(empty)}</p>'
    lines = []
    for item in items:
        if isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("name")
                or item.get("id")
                or item.get("provider")
                or item.get("role")
                or item.get("concept")
                or "item"
            )
            detail = (
                item.get("summary")
                or item.get("description")
                or item.get("rationale")
                or item.get("composition")
                or item.get("snippet")
                or item.get("source_url")
                or item.get("url")
                or item.get("note")
                or ""
            )
            lines.append(
                "<li>"
                f"<strong>{_html(title)}</strong>"
                f"{f'<span>{_html(detail)}</span>' if detail else ''}"
                "</li>"
            )
        else:
            lines.append(f"<li>{_html(item)}</li>")
    return "<ul>" + "".join(lines) + "</ul>"


def _render_kv(items: dict[str, Any]) -> str:
    rows = []
    for key, value in items.items():
        if isinstance(value, (list, dict)):
            value_text = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            value_text = str(value or "")
        rows.append(
            f"<dt>{_html(key.replace('_', ' ').title())}</dt>"
            f"<dd>{_html(value_text)}</dd>"
        )
    return "<dl>" + "".join(rows) + "</dl>"


def _render_sections(sections: list[dict[str, Any]]) -> str:
    if not sections:
        return '<p class="empty">Sections are pending research and angle approval.</p>'

    cards = []
    for section in sections:
        beats = section.get("beats") if isinstance(section.get("beats"), list) else []
        beat_rows = []
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            beat_rows.append(
                "<tr>"
                f"<td>{_html(beat.get('beat_index'))}</td>"
                f"<td>{_html(beat.get('role'))}</td>"
                f"<td>{_html(beat.get('visual_type'))}</td>"
                f"<td>{_html(beat.get('source_preference'))}</td>"
                f"<td>{_html(beat.get('intent'))}</td>"
                "</tr>"
            )
        beat_table = (
            '<table><thead><tr><th>#</th><th>Role</th><th>Visual</th>'
            '<th>Source</th><th>Intent</th></tr></thead><tbody>'
            + "".join(beat_rows)
            + "</tbody></table>"
            if beat_rows
            else '<p class="empty">Beats pending.</p>'
        )
        cards.append(
            '<article class="section-card">'
            f"<h3>{_html(section.get('section_index', ''))}. {_html(section.get('title', 'Untitled section'))}</h3>"
            f"<p>{_html(section.get('narrative_goal', ''))}</p>"
            f"<p><strong>Visual direction:</strong> {_html(section.get('visual_direction', ''))}</p>"
            f"<p><strong>Source ids:</strong> {_html(', '.join(section.get('source_ids', []) or []))}</p>"
            f"{beat_table}"
            "</article>"
        )
    return "".join(cards)


def render_checkpoint_html(plan: dict[str, Any]) -> str:
    errors, warnings = validate_producer_plan(plan)
    episode = plan.get("episode", {}) if isinstance(plan.get("episode"), dict) else {}
    topic_profile = plan.get("topic_profile", {}) if isinstance(plan.get("topic_profile"), dict) else {}
    research = plan.get("research", {}) if isinstance(plan.get("research"), dict) else {}
    visual_rules = plan.get("visual_rules", {}) if isinstance(plan.get("visual_rules"), dict) else {}
    visual_asset_plan = (
        plan.get("visual_asset_plan", {})
        if isinstance(plan.get("visual_asset_plan"), dict)
        else {}
    )
    script_draft = (
        plan.get("script_draft", {})
        if isinstance(plan.get("script_draft"), dict)
        else {}
    )
    asset_production = (
        plan.get("asset_production", {})
        if isinstance(plan.get("asset_production"), dict)
        else {}
    )
    audio_production = (
        plan.get("audio_production", {})
        if isinstance(plan.get("audio_production"), dict)
        else {}
    )
    render_preflight = (
        plan.get("render_preflight", {})
        if isinstance(plan.get("render_preflight"), dict)
        else {}
    )
    render = (
        plan.get("render", {})
        if isinstance(plan.get("render"), dict)
        else {}
    )
    final_qc = (
        plan.get("final_qc", {})
        if isinstance(plan.get("final_qc"), dict)
        else {}
    )
    cost_report = (
        plan.get("cost_report", {})
        if isinstance(plan.get("cost_report"), dict)
        else {}
    )
    final_report = (
        plan.get("final_report", {})
        if isinstance(plan.get("final_report"), dict)
        else {}
    )
    upload_pack = (
        plan.get("upload_pack", {})
        if isinstance(plan.get("upload_pack"), dict)
        else {}
    )
    smoke_gate = (
        plan.get("smoke_gate", {})
        if isinstance(plan.get("smoke_gate"), dict)
        else {}
    )
    provider_smoke = (
        plan.get("provider_smoke", {})
        if isinstance(plan.get("provider_smoke"), dict)
        else {}
    )
    budget = plan.get("budget", {}) if isinstance(plan.get("budget"), dict) else {}
    seo = plan.get("seo_packaging", {}) if isinstance(plan.get("seo_packaging"), dict) else {}
    approval = plan.get("approval", {}) if isinstance(plan.get("approval"), dict) else {}
    sections = plan.get("sections", []) if isinstance(plan.get("sections"), list) else []

    title = f"Producer Mode Checkpoint - {episode.get('topic', 'Untitled')}"
    status = str(plan.get("status", "unknown"))
    approved = "Approved" if approval.get("approved") else "Waiting for user OK"
    source_order = visual_rules.get("source_order", [])
    no_go = visual_rules.get("no_go", [])

    issue_items = [{"title": "Error", "summary": item} for item in errors]
    issue_items.extend({"title": "Warning", "summary": item} for item in warnings)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111316;
      --panel: #191d22;
      --panel-2: #20262d;
      --line: #313944;
      --text: #eef2f4;
      --muted: #9ca8b4;
      --accent: #77d1c5;
      --warn: #f1c36a;
      --bad: #ee7d7d;
      --ok: #93d58d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.55 "Segoe UI", Arial, sans-serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 44px;
    }}
    header {{
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 20px;
    }}
    h1, h2, h3 {{ margin: 0; line-height: 1.2; }}
    h1 {{ font-size: 30px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    h3 {{ font-size: 16px; margin-bottom: 8px; }}
    p {{ margin: 0 0 10px; }}
    .meta {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--muted);
      font-size: 13px;
    }}
    .badge.ok {{ color: var(--ok); border-color: rgba(147, 213, 141, .45); }}
    .badge.warn {{ color: var(--warn); border-color: rgba(241, 195, 106, .45); }}
    .badge.bad {{ color: var(--bad); border-color: rgba(238, 125, 125, .45); }}
    .badge.muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      grid-column: span 6;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .panel.full {{ grid-column: 1 / -1; }}
    .panel.third {{ grid-column: span 4; }}
    dl {{
      display: grid;
      grid-template-columns: minmax(140px, 220px) 1fr;
      gap: 8px 14px;
      margin: 0;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 7px 0; }}
    li span {{ display: block; color: var(--muted); margin-top: 2px; }}
    .empty {{ color: var(--muted); }}
    .section-card {{
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      margin: 12px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    @media (max-width: 820px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 18px; }}
      .panel, .panel.third {{ grid-column: 1 / -1; }}
      dl {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{_html(episode.get("topic", "Untitled topic"))}</h1>
      <div class="meta">
        {_badge(status, status.replace("_", " ").title())}
        {_badge("ok" if approval.get("approved") else "muted", approved)}
        {_badge(episode.get("output_format", "youtube_16x9"))}
        {_badge(f'Cost stop ${budget.get("stop_at", BUDGET_STOP_USD)}')}
      </div>
    </header>

    <section class="grid">
      <div class="panel full">
        <h2>Topic Profile</h2>
        {_render_kv(topic_profile)}
      </div>

      <div class="panel">
        <h2>Episode Rules</h2>
        {_render_kv({
            "episode_dir": _path_for_display(episode.get("episode_dir")),
            "language": episode.get("language"),
            "renderer": episode.get("renderer"),
            "episode_spec": episode_spec(plan),
            "visual_beat_seconds": episode.get("visual_beat_seconds"),
            "subtitles": episode.get("subtitles"),
        })}
      </div>

      <div class="panel">
        <h2>Research Gate</h2>
        {_render_kv({
            "status": research.get("status"),
            "researched_at": research.get("researched_at"),
            "research_summary": research.get("research_summary"),
            "minimum_sources": research.get("minimum_sources"),
            "official_media_candidates": len(research.get("official_media_results", []) or []),
            "competitor_market": research.get("competitor_market"),
            "conflict_policy": research.get("conflict_policy"),
        })}
      </div>

      <div class="panel full">
        <h2>Sections And Visual Beats</h2>
        {_render_sections(sections)}
      </div>

      <div class="panel">
        <h2>Visual Asset Plan</h2>
        {_render_kv({
            "status": visual_asset_plan.get("status"),
            "planned_at": visual_asset_plan.get("planned_at"),
            "beat_count": visual_asset_plan.get("beat_count"),
            "provider_counts": visual_asset_plan.get("provider_counts"),
            "qc_status_counts": visual_asset_plan.get("qc_status_counts"),
            "artifact": _path_for_display(visual_asset_plan.get("artifact")),
            "qc_artifact": _path_for_display(visual_asset_plan.get("qc_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Asset Plan Preview</h2>
        {_render_items(visual_asset_plan.get("beat_plan_preview", []), "Run plan-assets to create beat-level asset choices.")}
      </div>

      <div class="panel">
        <h2>Script Draft</h2>
        {_render_kv({
            "status": script_draft.get("status"),
            "drafted_at": script_draft.get("drafted_at"),
            "scene_count": script_draft.get("scene_count"),
            "chars_no_space": script_draft.get("chars_no_space"),
            "length_status": script_draft.get("length_status"),
            "fact_check_status": script_draft.get("fact_check_status"),
            "script_artifact": _path_for_display(script_draft.get("script_artifact")),
            "script_qc_artifact": _path_for_display(script_draft.get("script_qc_artifact")),
            "fact_check_artifact": _path_for_display(script_draft.get("fact_check_artifact")),
            "pronunciation_guide_artifact": _path_for_display(script_draft.get("pronunciation_guide_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Asset Production</h2>
        {_render_kv({
            "status": asset_production.get("status"),
            "produced_at": asset_production.get("produced_at"),
            "entry_count": asset_production.get("entry_count"),
            "visual_slot_count": asset_production.get("visual_slot_count"),
            "derived_broll_count": asset_production.get("derived_broll_count"),
            "fresh_official_candidate_count": asset_production.get("fresh_official_candidate_count"),
            "fresh_official_download_count": asset_production.get("fresh_official_download_count"),
            "fresh_official_download_fail_count": asset_production.get("fresh_official_download_fail_count"),
            "local_graphic_count": asset_production.get("local_graphic_count"),
            "stock_video_count": asset_production.get("stock_video_count"),
            "stock_video_fail_count": asset_production.get("stock_video_fail_count"),
            "repeat_guard": asset_production.get("repeat_guard"),
            "average_slot_seconds": asset_production.get("average_slot_seconds"),
            "downloaded_count": asset_production.get("downloaded_count"),
            "generated_count": asset_production.get("generated_count"),
            "pending_task_count": asset_production.get("pending_task_count"),
            "failed_count": asset_production.get("failed_count"),
            "asset_manifest_artifact": _path_for_display(asset_production.get("asset_manifest_artifact")),
            "asset_qc_artifact": _path_for_display(asset_production.get("asset_qc_artifact")),
            "visual_timeline_artifact": _path_for_display(asset_production.get("visual_timeline_artifact")),
            "broll_expansion_report_artifact": _path_for_display(asset_production.get("broll_expansion_report_artifact")),
            "imagegen_tasks_artifact": _path_for_display(asset_production.get("imagegen_tasks_artifact")),
            "remotion_graphic_tasks_artifact": _path_for_display(asset_production.get("remotion_graphic_tasks_artifact")),
            "graphic_render_report_artifact": _path_for_display(asset_production.get("graphic_render_report_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Audio Production</h2>
        {_render_kv({
            "status": audio_production.get("status"),
            "produced_at": audio_production.get("produced_at"),
            "scene_count": audio_production.get("scene_count"),
            "generated_count": audio_production.get("generated_count"),
            "skipped_existing_count": audio_production.get("skipped_existing_count"),
            "planned_count": audio_production.get("planned_count"),
            "failed_count": audio_production.get("failed_count"),
            "total_duration_seconds": audio_production.get("total_duration_seconds"),
            "estimated_cost_usd": audio_production.get("estimated_cost_usd"),
            "tts_manifest_artifact": _path_for_display(audio_production.get("tts_manifest_artifact")),
            "tts_qc_artifact": _path_for_display(audio_production.get("tts_qc_artifact")),
            "audio_qc_status": audio_production.get("audio_qc_status"),
            "audio_qc_checked_at": audio_production.get("audio_qc_checked_at"),
            "audio_qc_pass_count": audio_production.get("audio_qc_pass_count"),
            "audio_qc_review_count": audio_production.get("audio_qc_review_count"),
            "audio_qc_blocked_count": audio_production.get("audio_qc_blocked_count"),
            "audio_qc_artifact": _path_for_display(audio_production.get("audio_qc_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Render Preflight</h2>
        {_render_kv({
            "status": render_preflight.get("status"),
            "checked_at": render_preflight.get("checked_at"),
            "scene_count": render_preflight.get("scene_count"),
            "ready_scene_count": render_preflight.get("ready_scene_count"),
            "missing_audio_count": render_preflight.get("missing_audio_count"),
            "missing_asset_count": render_preflight.get("missing_asset_count"),
            "asset_count": render_preflight.get("asset_count"),
            "render_duration_seconds": render_preflight.get("render_duration_seconds"),
            "estimated_frames": render_preflight.get("estimated_frames"),
            "render_preflight_artifact": _path_for_display(render_preflight.get("render_preflight_artifact")),
            "render_props_preview_artifact": _path_for_display(render_preflight.get("render_props_preview_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Render</h2>
        {_render_kv({
            "status": render.get("status"),
            "rendered_at": render.get("rendered_at"),
            "scene_count": render.get("scene_count"),
            "render_duration_seconds": render.get("render_duration_seconds"),
            "final_video_bytes": render.get("final_video_bytes"),
            "final_video_path": _path_for_display(render.get("final_video_path")),
            "raw_video_path": _path_for_display(render.get("raw_video_path")),
            "render_manifest_artifact": _path_for_display(render.get("render_manifest_artifact")),
            "render_props_artifact": _path_for_display(render.get("render_props_artifact")),
            "log_artifact": _path_for_display(render.get("log_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Final QC</h2>
        {_render_kv({
            "status": final_qc.get("status"),
            "checked_at": final_qc.get("checked_at"),
            "duration_seconds": final_qc.get("duration_seconds"),
            "resolution": final_qc.get("resolution"),
            "fps": final_qc.get("fps"),
            "has_audio": final_qc.get("has_audio"),
            "file_bytes": final_qc.get("file_bytes"),
            "final_video_path": _path_for_display(final_qc.get("final_video_path")),
            "final_qc_artifact": _path_for_display(final_qc.get("final_qc_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Cost Report</h2>
        {_render_kv({
            "status": cost_report.get("status"),
            "reported_at": cost_report.get("reported_at"),
            "budget_status": cost_report.get("budget_status"),
            "estimated_total_cost_usd": cost_report.get("estimated_total_cost_usd"),
            "new_cost_this_run_usd": cost_report.get("new_cost_this_run_usd"),
            "remaining_estimated_cost_usd": cost_report.get("remaining_estimated_cost_usd"),
            "unknown_cost_item_count": cost_report.get("unknown_cost_item_count"),
            "cost_report_artifact": _path_for_display(cost_report.get("cost_report_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Final Report</h2>
        {_render_kv({
            "status": final_report.get("status"),
            "reported_at": final_report.get("reported_at"),
            "final_qc_status": final_report.get("final_qc_status"),
            "budget_status": final_report.get("budget_status"),
            "final_video_path": _path_for_display(final_report.get("final_video_path")),
            "final_report_artifact": _path_for_display(final_report.get("final_report_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Upload Pack</h2>
        {_render_kv({
            "status": upload_pack.get("status"),
            "created_at": upload_pack.get("created_at"),
            "upload_pack_dir": _path_for_display(upload_pack.get("upload_pack_dir")),
            "manifest_artifact": _path_for_display(upload_pack.get("manifest_artifact")),
            "metadata_artifact": _path_for_display(upload_pack.get("metadata_artifact")),
            "root_metadata_artifact": _path_for_display(upload_pack.get("root_metadata_artifact")),
            "thumbnail_brief_artifact": _path_for_display(upload_pack.get("thumbnail_brief_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Smoke Gate</h2>
        {_render_kv({
            "status": smoke_gate.get("status"),
            "checked_at": smoke_gate.get("checked_at"),
            "overall_score": smoke_gate.get("overall_score"),
            "blocking_gate_count": smoke_gate.get("blocking_gate_count"),
            "review_gate_count": smoke_gate.get("review_gate_count"),
            "smoke_gate_artifact": _path_for_display(smoke_gate.get("smoke_gate_artifact")),
        })}
      </div>

      <div class="panel">
        <h2>Provider Smoke</h2>
        {_render_kv({
            "status": provider_smoke.get("status"),
            "checked_at": provider_smoke.get("checked_at"),
            "provider_smoke_dir": _path_for_display(provider_smoke.get("provider_smoke_dir")),
            "manifest_artifact": _path_for_display(provider_smoke.get("manifest_artifact")),
            "live_pass_count": provider_smoke.get("live_pass_count"),
            "allow_network": provider_smoke.get("allow_network"),
            "allow_gemini_tts": provider_smoke.get("allow_gemini_tts"),
        })}
      </div>

      <div class="panel">
        <h2>Sources</h2>
        {_render_items(research.get("sources", []), "Sources pending research.")}
      </div>

      <div class="panel">
        <h2>Official Media Candidates</h2>
        {_render_items(research.get("official_media_results", []), "Official media candidates pending.")}
      </div>

      <div class="panel">
        <h2>Section Source Map</h2>
        {_render_items(research.get("section_source_map", []), "Section mapping pending research.")}
      </div>

      <div class="panel">
        <h2>Competitor Results</h2>
        {_render_items(research.get("competitor_results", []), "Competitor research pending.")}
      </div>

      <div class="panel">
        <h2>Competitor Patterns</h2>
        {_render_items(research.get("competitor_patterns", []), "Competitor pattern synthesis pending.")}
      </div>

      <div class="panel">
        <h2>Title Options</h2>
        {_render_items(seo.get("title_options", []), "Title options pending.")}
      </div>

      <div class="panel">
        <h2>Thumbnail Concepts</h2>
        {_render_items(seo.get("thumbnail_concept_options", []), "Thumbnail concepts pending.")}
      </div>

      <div class="panel third">
        <h2>Visual Source Order</h2>
        {_render_items(source_order)}
      </div>

      <div class="panel third">
        <h2>Visual No-Go</h2>
        {_render_items(no_go)}
      </div>

      <div class="panel third">
        <h2>SEO Packaging</h2>
        {_render_kv({
            "market": seo.get("market"),
            "recommended_title": seo.get("recommended_title"),
            "recommended_title_rationale": seo.get("recommended_title_rationale"),
            "thumbnail_language": seo.get("thumbnail_language"),
            "generate_thumbnail_by_default": seo.get("generate_thumbnail_by_default"),
        })}
      </div>

      <div class="panel full">
        <h2>Risks And Warnings</h2>
        {_render_items(
            list(research.get("risks", []) or [])
            + list(research.get("warnings", []) or [])
            + list(research.get("errors", []) or [])
            + list(visual_asset_plan.get("warnings", []) or [])
            + list(script_draft.get("warnings", []) or [])
            + list(asset_production.get("warnings", []) or [])
            + list(audio_production.get("warnings", []) or [])
            + list(render_preflight.get("warnings", []) or [])
            + list(render_preflight.get("errors", []) or [])
            + list(render.get("warnings", []) or [])
            + list(render.get("errors", []) or [])
            + list(final_qc.get("warnings", []) or [])
            + list(final_qc.get("errors", []) or [])
            + list(cost_report.get("warnings", []) or [])
            + list(cost_report.get("errors", []) or [])
            + list(final_report.get("warnings", []) or [])
            + list(final_report.get("errors", []) or [])
            + list(upload_pack.get("warnings", []) or [])
            + list(upload_pack.get("errors", []) or [])
            + list(smoke_gate.get("warnings", []) or [])
            + list(smoke_gate.get("errors", []) or [])
            + list(provider_smoke.get("warnings", []) or [])
            + list(provider_smoke.get("errors", []) or []),
            "No risks captured yet.",
        )}
      </div>

      <div class="panel">
        <h2>Budget</h2>
        {_render_kv(budget)}
      </div>

      <div class="panel">
        <h2>Validation</h2>
        {_render_items(issue_items, "No schema issues detected.")}
      </div>
    </section>
  </main>
</body>
</html>
"""


def write_checkpoint_html(episode_dir: str | Path, plan: dict[str, Any]) -> Path:
    path = checkpoint_path(episode_dir)
    _ensure_dir(path.parent)
    path.write_text(render_checkpoint_html(plan), encoding="utf-8")
    return path


def init_checkpoint(topic: str, episode_dir: str | Path | None = None, slug: str | None = None) -> tuple[Path, Path]:
    target_dir = Path(episode_dir) if episode_dir else make_episode_dir(topic, slug=slug)
    plan = default_producer_plan(topic, target_dir, slug=slug)
    visual_rules = plan.get("visual_rules") if isinstance(plan.get("visual_rules"), dict) else {}
    source_policy = (
        visual_rules.get("source_policy")
        if isinstance(visual_rules.get("source_policy"), dict)
        else default_visual_source_policy()
    )
    _write_json_artifact(visual_source_strategy_path(target_dir), source_policy)
    plan_path = save_producer_plan(target_dir, plan)
    html_path = write_checkpoint_html(target_dir, plan)
    return plan_path, html_path


def rerender_checkpoint(plan_path: str | Path, out_path: str | Path | None = None) -> Path:
    plan_file = Path(plan_path)
    plan = load_producer_plan(plan_file)
    target = Path(out_path) if out_path else plan_file.with_name(CHECKPOINT_FILENAME)
    _ensure_dir(target.parent)
    target.write_text(render_checkpoint_html(plan), encoding="utf-8")
    return target


def _print_validation(plan: dict[str, Any]) -> int:
    errors, warnings = validate_producer_plan(plan)
    for item in errors:
        print(f"[ERROR] {item}")
    for item in warnings:
        print(f"[WARN] {item}")
    if not errors and not warnings:
        print("[OK] producer plan schema looks valid")
    elif not errors:
        print("[OK] producer plan has no blocking schema errors")
    return 1 if errors else 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PodcastV2 Producer Mode checkpoint tools")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a skeleton producer_plan.json and checkpoint.html")
    init.add_argument("--topic", required=True, help="Episode topic")
    init.add_argument("--episode-dir", help="Existing or new episode directory")
    init.add_argument("--slug", help="Optional ASCII slug for the episode folder")

    research = sub.add_parser("research", help="Run web research and update checkpoint artifacts")
    research.add_argument("--plan", required=True, help="Path to producer_plan.json")
    research.add_argument("--max-sources", type=int, default=8, help="Maximum source results to keep")
    research.add_argument("--max-competitors", type=int, default=6, help="Maximum competitor results to keep")
    research.add_argument("--no-llm", action="store_true", help="Use heuristic synthesis instead of LLM synthesis")
    research.add_argument(
        "--no-fetch-pages",
        action="store_true",
        help="Use search snippets only; do not fetch source pages for summaries",
    )

    plan_assets = sub.add_parser(
        "plan-assets",
        help="Plan visual asset providers per beat and write planning-time asset QC",
    )
    plan_assets.add_argument("--plan", required=True, help="Path to producer_plan.json")

    draft_script = sub.add_parser(
        "draft-script",
        help="Draft script.json plus script QC, fact-check report, and pronunciation guide",
    )
    draft_script.add_argument("--plan", required=True, help="Path to producer_plan.json")
    draft_script.add_argument(
        "--no-llm",
        action="store_true",
        help="Write a non-production template fallback for smoke tests",
    )

    expand_script = sub.add_parser(
        "expand-script",
        help="Review expansion needs without padding narration; revise supported content manually",
    )
    expand_script.add_argument("--plan", required=True, help="Path to producer_plan.json")
    expand_script.add_argument(
        "--target-min",
        type=int,
        default=None,
        help="Explicit episode_spec minimum Thai Unicode characters",
    )
    expand_script.add_argument(
        "--target-max",
        type=int,
        default=None,
        help="Explicit episode_spec maximum Thai Unicode characters",
    )

    produce_assets = sub.add_parser(
        "produce-assets",
        help="Create asset_manifest.json and run safe asset production tasks",
    )
    produce_assets.add_argument("--plan", required=True, help="Path to producer_plan.json")
    produce_assets.add_argument(
        "--dry-run",
        action="store_true",
        help="Write manifest/tasks without downloading or generating media",
    )
    produce_assets.add_argument(
        "--allow-stock",
        action="store_true",
        help="Allow Pexels/Pixabay stock video downloads when keys are configured",
    )
    produce_assets.add_argument(
        "--allow-runware",
        action="store_true",
        help="Allow Runware FLUX.1 fallback image generation when configured",
    )
    produce_assets.add_argument(
        "--max-download-mb",
        type=int,
        default=80,
        help="Maximum bytes per official media download in MB",
    )

    apply_assets = sub.add_parser(
        "apply-asset-results",
        help="Apply local imagegen/remotion/manual result files to asset_manifest.json",
    )
    apply_assets.add_argument("--plan", required=True, help="Path to producer_plan.json")
    apply_assets.add_argument(
        "--source-dir",
        help="Directory containing result files, defaulting to the episode directory",
    )
    apply_assets.add_argument(
        "--force",
        action="store_true",
        help="Re-apply matching files even for entries already marked done",
    )

    render_graphics = sub.add_parser(
        "render-graphics",
        help="Render local remotion_graphic PNGs and optional preflight-only opener placeholders",
    )
    render_graphics.add_argument("--plan", required=True, help="Path to producer_plan.json")
    render_graphics.add_argument(
        "--placeholder-openers",
        action="store_true",
        help="Create temporary no-text opener placeholders without marking imagegen tasks complete",
    )
    render_graphics.add_argument(
        "--force",
        action="store_true",
        help="Regenerate local graphics even when output files already exist",
    )

    produce_tts = sub.add_parser(
        "produce-tts",
        help="Create scene_NN.wav files plus tts_manifest.json and tts_qc.json",
    )
    produce_tts.add_argument("--plan", required=True, help="Path to producer_plan.json")
    produce_tts.add_argument(
        "--dry-run",
        action="store_true",
        help="Write TTS manifest/QC without calling Gemini TTS",
    )
    produce_tts.add_argument(
        "--force",
        action="store_true",
        help="Regenerate WAV files even when scene_NN.wav already exists",
    )
    produce_tts.add_argument(
        "--tone-preset",
        default=None,
        help="Gemini TTS tone preset; defaults to the plan's audio_rules.tone_preset (host_dry for new plans), else natural_storyteller",
    )
    produce_tts.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional scene limit for samples or smoke tests",
    )

    audio_qc = sub.add_parser(
        "audio-qc",
        help="Inspect generated scene WAV files for level, clipping, and silence issues",
    )
    audio_qc.add_argument("--plan", required=True, help="Path to producer_plan.json")

    expand_broll = sub.add_parser(
        "expand-broll",
        help="Expand one-visual scenes into 5-8 second b-roll slots from real audio durations",
    )
    expand_broll.add_argument("--plan", required=True, help="Path to producer_plan.json")
    expand_broll.add_argument(
        "--target-seconds",
        type=float,
        default=6.5,
        help="Preferred visual slot duration in seconds",
    )
    expand_broll.add_argument(
        "--min-seconds",
        type=float,
        default=VISUAL_BEAT_SECONDS_MIN,
        help="Minimum visual slot duration in seconds",
    )
    expand_broll.add_argument(
        "--max-seconds",
        type=float,
        default=VISUAL_BEAT_SECONDS_MAX,
        help="Maximum visual slot duration in seconds",
    )
    expand_broll.add_argument(
        "--fresh-official",
        action="store_true",
        help="Search and download fresh official/NASA image b-roll before using local reframes",
    )
    expand_broll.add_argument(
        "--fresh-official-limit",
        type=int,
        default=64,
        help="Maximum fresh official image candidates to collect",
    )
    expand_broll.add_argument(
        "--fresh-official-max-download-mb",
        type=int,
        default=25,
        help="Maximum bytes per fresh official image download in MB",
    )
    expand_broll.add_argument(
        "--allow-stock",
        action="store_true",
        help="Download Pexels/Pixabay video b-roll for slots that would otherwise become local graphics",
    )
    expand_broll.add_argument(
        "--stock-max-slots",
        type=int,
        default=40,
        help="Maximum stock video b-roll slots to download",
    )
    expand_broll.add_argument(
        "--allow-runware",
        action="store_true",
        help="Generate Runware FLUX.1 image b-roll for slots where stock/reframes are weak",
    )
    expand_broll.add_argument(
        "--runware-max-slots",
        type=int,
        default=40,
        help="Maximum Runware FLUX.1 image b-roll slots to generate",
    )
    expand_broll.add_argument(
        "--max-visual-repeats",
        type=int,
        default=2,
        help="Maximum times the same visual source may appear in one episode",
    )
    expand_broll.add_argument(
        "--force",
        action="store_true",
        help="Regenerate existing derived b-roll reframes",
    )
    expand_broll.add_argument(
        "--legacy-keyword-tables",
        action="store_true",
        help="Allow the built-in per-episode keyword tables when broll_keywords.json is absent (older episodes only)",
    )

    render_preflight = sub.add_parser(
        "render-preflight",
        help="Check script, scene audio/assets, and Remotion readiness before render",
    )
    render_preflight.add_argument("--plan", required=True, help="Path to producer_plan.json")
    render_preflight.add_argument(
        "--image-only",
        action="store_true",
        help="Match PODCAST_RENDER_IMAGE_ONLY behavior by ignoring scene mp4 assets",
    )

    render_video = sub.add_parser(
        "render-video",
        help="Prepare episode-local render props and optionally render final.mp4",
    )
    render_video.add_argument("--plan", required=True, help="Path to producer_plan.json")
    render_video.add_argument(
        "--no-render",
        action="store_true",
        help="Prepare merged audio/render props/manifest but skip Remotion render",
    )
    render_video.add_argument(
        "--force",
        action="store_true",
        help="Regenerate merged audio/render outputs even when files already exist",
    )
    render_video.add_argument(
        "--timeout-seconds",
        type=int,
        default=7200,
        help="Maximum Remotion render time in seconds",
    )

    final_qc = sub.add_parser(
        "final-qc",
        help="Inspect final.mp4 with ffprobe and write final_qc.json",
    )
    final_qc.add_argument("--plan", required=True, help="Path to producer_plan.json")

    cost_report = sub.add_parser(
        "cost-report",
        help="Write cost_report.json from local Producer Mode manifests",
    )
    cost_report.add_argument("--plan", required=True, help="Path to producer_plan.json")

    final_report = sub.add_parser(
        "final-report",
        help="Write the final read-only Producer Mode handoff report",
    )
    final_report.add_argument("--plan", required=True, help="Path to producer_plan.json")

    upload_pack = sub.add_parser(
        "upload-pack",
        help="Write upload_pack metadata, title options, tags, and thumbnail brief",
    )
    upload_pack.add_argument("--plan", required=True, help="Path to producer_plan.json")

    smoke_gate = sub.add_parser(
        "smoke-gate",
        help="Inspect readiness before a real production/provider run",
    )
    smoke_gate.add_argument("--plan", required=True, help="Path to producer_plan.json")

    provider_smoke = sub.add_parser(
        "provider-smoke",
        help="Run controlled provider fulfillment checks and optional tiny live samples",
    )
    provider_smoke.add_argument("--plan", required=True, help="Path to producer_plan.json")
    provider_smoke.add_argument("--topic", help="Optional smoke query/topic override")
    provider_smoke.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow Pexels/Pixabay metadata API checks",
    )
    provider_smoke.add_argument(
        "--allow-gemini-tts",
        action="store_true",
        help="Allow a tiny paid Gemini TTS sample",
    )
    provider_smoke.add_argument(
        "--timeout-seconds",
        type=int,
        default=60,
        help="Network timeout for live provider smoke checks",
    )

    checkpoint = sub.add_parser("checkpoint", help="Render checkpoint.html from producer_plan.json")
    checkpoint.add_argument("--plan", required=True, help="Path to producer_plan.json")
    checkpoint.add_argument("--out", help="Optional output HTML path")

    validate = sub.add_parser("validate", help="Validate producer_plan.json")
    validate.add_argument("--plan", required=True, help="Path to producer_plan.json")

    schema = sub.add_parser("schema", help="Print the lightweight Producer Mode schema")
    schema.add_argument("--out", help="Optional JSON output path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        plan_path, html_path = init_checkpoint(args.topic, args.episode_dir, slug=args.slug)
        print(f"[OK] wrote {plan_path}")
        print(f"[OK] wrote {html_path}")
        return 0

    if args.command == "research":
        outputs = run_research_checkpoint(
            args.plan,
            use_llm=not args.no_llm,
            max_sources=args.max_sources,
            max_competitors=args.max_competitors,
            fetch_pages=not args.no_fetch_pages,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['research_brief']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "plan-assets":
        outputs = run_asset_planning_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['visual_source_strategy']}")
        print(f"[OK] wrote {outputs['visual_asset_plan']}")
        print(f"[OK] wrote {outputs['asset_qc']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "draft-script":
        outputs = run_script_draft_checkpoint(args.plan, use_llm=not args.no_llm)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['script']}")
        print(f"[OK] wrote {outputs['script_qc']}")
        print(f"[OK] wrote {outputs['fact_check_report']}")
        print(f"[OK] wrote {outputs['pronunciation_guide']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "expand-script":
        outputs = run_script_expand_checkpoint(
            args.plan,
            target_min=args.target_min,
            target_max=args.target_max,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['script']}")
        print(f"[OK] wrote {outputs['script_qc']}")
        print(f"[OK] wrote {outputs['fact_check_report']}")
        print(f"[OK] wrote {outputs['pronunciation_guide']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "produce-assets":
        outputs = run_asset_production_checkpoint(
            args.plan,
            dry_run=args.dry_run,
            allow_stock=args.allow_stock,
            allow_runware=args.allow_runware,
            max_download_mb=args.max_download_mb,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['asset_manifest']}")
        print(f"[OK] wrote {outputs['asset_qc']}")
        print(f"[OK] wrote {outputs['imagegen_tasks']}")
        print(f"[OK] wrote {outputs['remotion_graphic_tasks']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "apply-asset-results":
        outputs = run_asset_results_checkpoint(
            args.plan,
            source_dir=args.source_dir,
            force=args.force,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['asset_manifest']}")
        print(f"[OK] wrote {outputs['asset_qc']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "render-graphics":
        outputs = run_graphic_render_checkpoint(
            args.plan,
            placeholder_openers=args.placeholder_openers,
            force=args.force,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['asset_manifest']}")
        print(f"[OK] wrote {outputs['asset_qc']}")
        print(f"[OK] wrote {outputs['graphic_render_report']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "produce-tts":
        outputs = run_tts_production_checkpoint(
            args.plan,
            dry_run=args.dry_run,
            force=args.force,
            tone_preset=args.tone_preset,
            limit=args.limit,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['tts_manifest']}")
        print(f"[OK] wrote {outputs['tts_qc']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "audio-qc":
        outputs = run_audio_qc_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['audio_qc']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "expand-broll":
        outputs = run_broll_expansion_checkpoint(
            args.plan,
            target_seconds=args.target_seconds,
            min_seconds=args.min_seconds,
            max_seconds=args.max_seconds,
            fresh_official=args.fresh_official,
            fresh_official_limit=args.fresh_official_limit,
            fresh_official_max_download_mb=args.fresh_official_max_download_mb,
            allow_stock=args.allow_stock,
            stock_max_slots=args.stock_max_slots,
            allow_runware=args.allow_runware,
            runware_max_slots=args.runware_max_slots,
            max_visual_repeats=args.max_visual_repeats,
            force=args.force,
            legacy_keyword_tables=args.legacy_keyword_tables,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['asset_manifest']}")
        print(f"[OK] wrote {outputs['asset_qc']}")
        print(f"[OK] wrote {outputs['visual_timeline']}")
        print(f"[OK] wrote {outputs['broll_expansion_report']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "render-preflight":
        outputs = run_render_preflight_checkpoint(
            args.plan,
            render_image_only=args.image_only,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['render_preflight']}")
        print(f"[OK] wrote {outputs['render_props_preview']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "render-video":
        outputs = run_render_video_checkpoint(
            args.plan,
            no_render=args.no_render,
            force=args.force,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['render_manifest']}")
        print(f"[OK] wrote {outputs['render_props']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "final-qc":
        outputs = run_final_qc_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['final_qc']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "cost-report":
        outputs = run_cost_report_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['cost_report']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "final-report":
        outputs = run_final_report_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['final_report']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "upload-pack":
        outputs = run_upload_pack_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['upload_pack_manifest']}")
        print(f"[OK] wrote {outputs['upload_pack_dir']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "smoke-gate":
        outputs = run_smoke_gate_checkpoint(args.plan)
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['smoke_gate']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "provider-smoke":
        outputs = run_provider_smoke_checkpoint(
            args.plan,
            topic=args.topic,
            allow_network=args.allow_network,
            allow_gemini_tts=args.allow_gemini_tts,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"[OK] wrote {outputs['plan']}")
        print(f"[OK] wrote {outputs['provider_smoke_manifest']}")
        print(f"[OK] wrote {outputs['provider_smoke_dir']}")
        print(f"[OK] wrote {outputs['checkpoint']}")
        return 0

    if args.command == "checkpoint":
        out = rerender_checkpoint(args.plan, args.out)
        print(f"[OK] wrote {out}")
        return 0

    if args.command == "validate":
        return _print_validation(load_producer_plan(args.plan))

    if args.command == "schema":
        payload = json.dumps(PRODUCER_PLAN_SCHEMA, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            out = Path(args.out)
            _ensure_dir(out.parent)
            out.write_text(payload, encoding="utf-8")
            print(f"[OK] wrote {out}")
        else:
            print(payload, end="")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
