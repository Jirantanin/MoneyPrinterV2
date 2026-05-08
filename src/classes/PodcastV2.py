"""
PodcastV2.py โ€” Enhanced Video Podcast pipeline (V2).

Extends the V1 Podcast pipeline with:
  Feature 1 โ€” TTS receives scene_index + total_scenes for scene-aware pacing.
  Feature 2 โ€” Audio is generated first; image count per scene scales with duration.
  Feature 3 โ€” B-roll clips from Pexels replace secondary AI images where possible.
  Feature 4 โ€” render() passes multi-asset props to Remotion (sceneImageCounts,
               sceneAssetTypes, sceneAssetDurations).

episode_id prefix is "podcast_v2_" to distinguish V2 episodes from V1.
All other pipeline logic (script generation, metadata, upload) is identical to
Podcast.py and is re-used without modification.
"""

import glob
import json
import math
import os
import re
import subprocess
import time
from datetime import datetime

from config import (
    ROOT_DIR,
    get_podcast_audio_retry_count,
    get_podcast_image_retry_count,
    get_podcast_narrator,
    get_podcast_script_model,
    get_podcast_metadata_system_prompt,
    get_podcast_script_system_prompt,
    get_podcast_style_prompt,
    get_podcast_thumbnail_system_prompt,
    get_script_sentence_length,
    get_tts_edge_rate,
    get_tts_edge_voice,
    get_tts_edge_thai_rate,
    get_tts_edge_thai_voice,
    get_kling_access_key,
    get_kling_secret_key,
)
from image_provider import generate_image
from kling_provider import generate_video_from_image
from llm_provider import generate_text, generate_text_structured
from runtime_trace import append_trace, reset_trace_run_id, set_trace_run_id, summarize_run_cost
from classes.Tts import TTS
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


# ---------------------------------------------------------------------------
# Re-use all helper functions from Podcast.py verbatim
# ---------------------------------------------------------------------------

def _slugify_topic(topic: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (topic or "").lower()).strip("-")
    if normalized:
        return normalized
    compact = re.sub(r"\s+", "-", (topic or "").strip())
    if compact:
        return f"topic-{abs(hash(compact)) % 1000000:06d}"
    return "untitled"


def _safe_format(template: str, **kwargs) -> str:
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return str(template).format_map(_SafeDict(**kwargs))


def _build_direction_block(creative_direction: str) -> str:
    cleaned = (creative_direction or "").strip()
    if not cleaned:
        return ""
    return (
        "Creative direction:\n"
        f"{cleaned}\n\n"
        "Use this only as a style, mood, and imagery guide. "
        "Do NOT change the core topic or invent a different central subject.\n"
    )


def _build_topic_guardrail_block(topic: str, creative_direction: str, language: str) -> str:
    topic_clean = (topic or "").strip()
    direction_clean = (creative_direction or "").strip()
    key_concepts = []
    if topic_clean:
        key_concepts.append(topic_clean)
    if direction_clean:
        key_concepts.append(direction_clean)
    concepts_text = "\n".join(f"- {item}" for item in key_concepts if item)
    if not concepts_text:
        concepts_text = "- Stay tightly anchored to the exact topic provided by the user."
    return (
        "Hard topic guardrails:\n"
        f"- The exact central topic is: {topic_clean}\n"
        "- Every scene must directly explain, question, or deepen that exact topic.\n"
        "- Reuse the concrete concepts named by the user naturally across the episode.\n"
        "- For abstract topics, stay analytical and reflective. Do NOT invent external lore or plot devices.\n"
        "- Do NOT invent archaeologists, secret organizations, ancient ruins, hidden symbols, forbidden documents, "
        "aliens, mythologies, or supernatural systems unless the user explicitly asked for them.\n"
        f"- Write ALL narration in {language}. Do not switch languages.\n"
        "Key concepts from the user that should remain visible in the writing:\n"
        f"{concepts_text}\n"
    )


def _build_topic_interpretation_block(topic: str, creative_direction: str) -> str:
    topic_clean = (topic or "").strip().lower()
    direction_clean = (creative_direction or "").strip().lower()
    combined = f"{topic_clean}\n{direction_clean}"
    if "เธเธงเธฒเธกเธ—เธฃเธเธเธณ" in combined or "memory" in combined:
        lines = [
            "Topic interpretation you must follow:",
            "- This episode is about memory, not dreams, not sleep, not ancient mysteries, and not unrelated psychology topics.",
            "- Explain that memory is reconstructed rather than replayed exactly like a recording.",
            "- Include the idea of false memory, distortion, suggestion, or emotional influence on recall.",
            "- Explore what unreliable memory means for identity, truth, and personal certainty.",
        ]
        if "เธฅเธนเธเธเธฑเธ”" in combined or "bead" in combined:
            lines.append(
                "- Reuse the user's bead metaphor across multiple scenes: the mind strings fragments together like beads until they feel like a memory."
            )
        return "\n".join(lines) + "\n"
    return ""


def _generate_image_prompt(narration: str, model_name: str | None = None) -> str:
    try:
        raw = generate_text(
            "You generate concise visual image prompts for podcast scenes.\n"
            "IMPORTANT: The image prompt MUST be written in English only. Never use Thai or other non-Latin scripts in the image prompt.\n"
            "If there is any text shown in the image, it must be in English.\n\n"
            f"Write a vivid visual image prompt for this narration:\n{narration}\n\n"
            "Return only the image prompt, no explanation, no label, no preamble.",
            model_name=model_name,
        )
        result = raw.strip()
        if result:
            return result
    except Exception:
        pass
    return narration[:300]


def _generate_scene_title(narration: str, model_name: str | None = None) -> str:
    try:
        prompt = (
            "Summarize the following narration in a short, punchy title (exactly 1-4 words). "
            "Use the SAME language as the narration (e.g., if the narration is in Thai, the title MUST be in Thai). "
            "Do NOT use markdown, do NOT use quotes, just return the plain title text.\n\n"
            f"NARRATION:\n{narration}"
        )
        title = generate_text(prompt, model_name=model_name).strip()
        title = title.replace('"', '').replace("'", '').strip('.')
        if "```" in title:
            title = title.split("```")[-1].strip()
        return title[:100]
    except Exception:
        return ""



SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_title": {"type": "string"},
                    "narration": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["scene_title", "narration", "image_prompt"],
            },
        }
    },
    "required": ["scenes"],
}


TOPIC_BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "topic_anchor": {"type": "string"},
        "main_question": {"type": "string"},
        "audience_level": {"type": "string"},
        "core_thesis": {"type": "string"},
        "allowed_concepts": {"type": "array", "items": {"type": "string"}},
        "teaser_only_concepts": {"type": "array", "items": {"type": "string"}},
        "required_concepts": {"type": "array", "items": {"type": "string"}},
        "forbidden_drifts": {"type": "array", "items": {"type": "string"}},
        "recurring_motifs": {"type": "array", "items": {"type": "string"}},
        "comprehension_contract": {"type": "array", "items": {"type": "string"}},
        "act_1_focus": {"type": "string"},
        "act_2_focus": {"type": "string"},
        "act_3_focus": {"type": "string"},
        "outro_focus": {"type": "string"},
        "visual_world": {"type": "string"},
    },
    "required": [
        "topic_anchor", "main_question", "audience_level", "core_thesis",
        "allowed_concepts", "teaser_only_concepts", "required_concepts",
        "forbidden_drifts", "recurring_motifs", "comprehension_contract",
        "act_1_focus", "act_2_focus", "act_3_focus", "outro_focus",
        "visual_world",
    ],
}


BEAT_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "episode_thesis": {"type": "string"},
        "opening_hook": {"type": "string"},
        "payoff": {"type": "string"},
        "ending_feeling": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {"type": "integer"},
                    "act": {"type": "string"},
                    "purpose": {"type": "string"},
                    "key_point": {"type": "string"},
                    "emotional_turn": {"type": "string"},
                    "visual_idea": {"type": "string"},
                    "must_include": {"type": "array", "items": {"type": "string"}},
                    "avoid": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "scene",
                    "act",
                    "purpose",
                    "key_point",
                    "emotional_turn",
                    "visual_idea",
                    "must_include",
                    "avoid",
                ],
            },
        },
    },
    "required": ["episode_thesis", "opening_hook", "payoff", "ending_feeling", "scenes"],
}


BEAT_QC_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number"},
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "scene": {"type": "integer"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["severity", "scene", "issue", "suggestion"],
            },
        },
        "rewrite_targets": {"type": "array", "items": {"type": "integer"}},
        "missing_beats": {"type": "array", "items": {"type": "string"}},
        "retention_notes": {"type": "array", "items": {"type": "string"}},
        "comprehension_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_score",
        "status",
        "summary",
        "issues",
        "rewrite_targets",
        "missing_beats",
        "retention_notes",
        "comprehension_notes",
    ],
}


BEAT_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": BEAT_SHEET_SCHEMA["properties"]["scenes"]["items"],
        }
    },
    "required": ["scenes"],
}


BEAT_RECONCILE_SCHEMA = {
    "type": "object",
    "properties": {
        "editor_notes": {"type": "array", "items": {"type": "string"}},
        "scenes": {
            "type": "array",
            "items": BEAT_SHEET_SCHEMA["properties"]["scenes"]["items"],
        },
    },
    "required": ["editor_notes", "scenes"],
}


SCRIPT_QC_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number"},
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string"},
                    "scene": {"type": "integer"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["severity", "scene", "issue", "suggestion"],
            },
        },
        "rewrite_targets": {"type": "array", "items": {"type": "integer"}},
        "retention_notes": {"type": "array", "items": {"type": "string"}},
        "comprehension_notes": {"type": "array", "items": {"type": "string"}},
        "visual_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_score",
        "status",
        "summary",
        "strengths",
        "issues",
        "rewrite_targets",
        "retention_notes",
        "comprehension_notes",
        "visual_notes",
    ],
}


SCRIPT_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene": {"type": "integer"},
                    "scene_title": {"type": "string"},
                    "narration": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["scene", "scene_title", "narration", "image_prompt"],
            },
        }
    },
    "required": ["scenes"],
}


def _get_audio_duration(audio_path: str) -> float:
    """Return duration in seconds via ffprobe, or 0.0 on error."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _get_config_value(key: str, default):
    """Read a top-level key from config.json."""
    try:
        config_path = os.path.join(ROOT_DIR, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get(key, default)
    except Exception:
        return default


def _extract_json_candidate(text: str) -> str:
    stripped = str(text or "").strip()
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.MULTILINE).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start:end + 1]
    return stripped


def _load_llm_json_candidate(candidate: str) -> dict:
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        original_exc = exc

    repair_candidates = []
    repaired = re.sub(r"\}\s*\}\s*\]\s*\}\s*$", r"}]}", candidate)
    if repaired != candidate:
        repair_candidates.append(repaired)
    brace_positions = [match.start() for match in re.finditer(r"\}", candidate)]
    for pos in reversed(brace_positions[-6:]):
        repair_candidates.append(candidate[:pos] + candidate[pos + 1:])

    seen = set()
    for repaired in repair_candidates:
        if repaired in seen:
            continue
        seen.add(repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            continue
    raise original_exc


def _compact_text(value, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _build_comprehension_contract_block(topic_brief: dict) -> str:
    """Return the listener-understanding constraints shared by beat and script prompts."""
    main_question = str(topic_brief.get("main_question") or topic_brief.get("topic_anchor") or "").strip()
    audience_level = str(topic_brief.get("audience_level") or "curious non-expert listener").strip()
    allowed = [
        str(item).strip()
        for item in (topic_brief.get("allowed_concepts") or topic_brief.get("required_concepts") or [])
        if str(item).strip()
    ][:5]
    teaser_only = [
        str(item).strip()
        for item in (topic_brief.get("teaser_only_concepts") or [])
        if str(item).strip()
    ][:4]
    contract = [
        str(item).strip()
        for item in (topic_brief.get("comprehension_contract") or [])
        if str(item).strip()
    ][:6]
    lines = [
        "Listener comprehension contract:",
        f"- Main question: {main_question}",
        f"- Target listener: {audience_level}",
        "- One scene may introduce at most one new hard concept.",
        "- Explain every hard term in plain language immediately before or after naming it.",
        "- Add a short recap or checkpoint every 3-4 scenes.",
        "- Do not list multiple theories or mechanisms back-to-back.",
    ]
    if allowed:
        lines.append("- Allowed core concepts to explain deeply: " + "; ".join(allowed))
    if teaser_only:
        lines.append("- Teaser-only concepts, max one sentence each: " + "; ".join(teaser_only))
    for item in contract:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


GLOSSARY_TERMS = [
    ("event horizon", ["event horizon", "ขอบ event horizon"], "ขอบที่แสงหนีไม่พ้น"),
    ("Hawking radiation", ["hawking radiation", "รังสีฮอว์คิง"], "รังสีที่ทำให้หลุมดำค่อยๆ สูญเสียพลังงาน"),
    ("unitarity", ["unitarity"], "กฎว่าข้อมูลของระบบไม่ควรหายไปจริงๆ"),
    ("entropy", ["entropy"], "มาตรวัดจำนวนสถานะที่เป็นไปได้ หรือความไม่รู้ของระบบ"),
    ("information paradox", ["information paradox", "black hole information paradox"], "ปัญหาว่าข้อมูลในหลุมดำหายไปได้ไหม"),
    ("virtual particles", ["virtual particle", "virtual particles", "อนุภาคเสมือน"], "คู่อนุภาคชั่วคราวตามภาพของควอนตัม"),
    ("Page curve", ["page curve"], "กราฟที่บอกว่าข้อมูลควรค่อยๆ กลับออกมา"),
    ("firewall", ["firewall"], "แนวคิดว่าขอบหลุมดำอาจเป็นกำแพงพลังงานรุนแรง"),
    ("soft hair", ["soft hair"], "แนวคิดว่าขอบหลุมดำอาจเก็บร่องรอยข้อมูลบางอย่าง"),
    ("holographic principle", ["holographic principle", "holography"], "แนวคิดว่าข้อมูลในปริมาตรอาจถูกเข้ารหัสบนขอบ"),
    ("quantum gravity", ["quantum gravity"], "ทฤษฎีที่ต้องรวมแรงโน้มถ่วงกับควอนตัมเข้าด้วยกัน"),
    ("island formula", ["island formula"], "สูตรที่นับบางส่วนในหลุมดำร่วมกับรังสีเพื่อคำนวณข้อมูล"),
    ("replica wormhole", ["replica wormhole"], "โครงสร้างคณิตศาสตร์ที่ช่วยให้สูตร island ทำงาน"),
    ("path integral", ["path integral"], "วิธีคำนวณควอนตัมโดยรวมเส้นทางที่เป็นไปได้จำนวนมาก"),
    ("Bose-Einstein condensate", ["bose-einstein condensate"], "สสารเย็นจัดที่อะตอมจำนวนมากทำตัวเหมือนระบบเดียว"),
]


# ---------------------------------------------------------------------------
# PodcastV2 class
# ---------------------------------------------------------------------------

class PodcastV2:
    """V2 Video Podcast pipeline with multi-image-per-scene and Pexels B-roll."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")

    def __init__(
        self,
        topic: str = "",
        language: str = "English",
        tts_source: str = "edge",
        creative_direction: str = "",
        visual_style: str = "",
        script_mode: bool = False,
        raw_script: str = "",
    ) -> None:
        self.topic = topic
        self.language = language
        self.tts_source = (tts_source or "edge").lower()
        self.creative_direction = (creative_direction or "").strip()
        self.visual_style = (visual_style or "").strip()
        self.script_mode = script_mode
        self.raw_script = (raw_script or "").strip()
        self.narrator = get_podcast_narrator()
        self.style_prompt = self.visual_style if self.visual_style else get_podcast_style_prompt()
        self.episode_dir: str = ""
        self.metadata: dict = {}

    def _parse_llm_json(self, raw: str, label: str) -> dict:
        candidate = _extract_json_candidate(raw)
        try:
            return _load_llm_json_candidate(candidate)
        except json.JSONDecodeError as exc:
            if self.episode_dir:
                safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "llm_json"
                raw_path = os.path.join(self.episode_dir, f"{safe_label}_raw.txt")
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(str(raw or ""))
                raise ValueError(f"{label} returned invalid JSON. Raw response saved to {raw_path}: {exc}") from exc
            raise ValueError(f"{label} returned invalid JSON: {exc}") from exc

    # ------------------------------------------------------------------
    # Helpers shared with Podcast.py
    # ------------------------------------------------------------------

    def _compile_topic_brief(self, topic: str, script_model: str) -> dict:
        prompt = (
            f"Create a writing brief for a podcast episode about: {topic}\n\n"
            f"{_build_direction_block(self.creative_direction)}"
            "Interpret the user's actual topic as literally and faithfully as possible.\n"
            "This brief will control a later script generator, so it must prevent topic drift.\n"
            "Do NOT turn the topic into a different theme just because it sounds poetic, mysterious, or philosophical.\n"
            "For abstract topics, explain the real idea directly.\n"
            "Required output rules:\n"
            "- topic_anchor must restate the exact topic in one line.\n"
            "- main_question must be the ONE question this episode answers; do not make it broad.\n"
            "- audience_level must describe the assumed listener knowledge in plain terms.\n"
            "- core_thesis must explain the actual idea the episode should explore.\n"
            "- allowed_concepts must contain at most 5 concepts that may be explained deeply.\n"
            "- teaser_only_concepts must contain advanced related concepts that should be mentioned briefly only, not taught.\n"
            "- required_concepts must be concrete concepts, phrases, or angles that should appear across the episode.\n"
            "- forbidden_drifts must list topic substitutions or wrong directions the writer must avoid.\n"
            "- recurring_motifs should include any user-provided metaphor or recurring image.\n"
            "- comprehension_contract must list 4-6 concrete rules that keep the episode easy to follow when heard aloud.\n"
            "- act_1_focus, act_2_focus, act_3_focus, and outro_focus must describe what each section should do.\n"
            "- Act 3 should mostly pay off the main question; advanced frontier ideas belong in teaser_only_concepts unless required by the topic.\n"
            "- visual_world should describe the visual feeling while staying consistent with the real topic.\n"
        )
        raw = generate_text_structured(
            prompt=prompt,
            system_prompt=(
                f"Create a tight topic brief in {self.language}. "
                "Be literal, precise, and faithful to the user's topic. "
                "Do not invent a different subject."
            ),
            schema=TOPIC_BRIEF_SCHEMA,
            model_name=script_model,
        )
        brief = self._parse_llm_json(raw, "topic_brief")
        brief["topic_anchor"] = topic
        brief["main_question"] = str(brief.get("main_question") or topic).strip()
        brief["audience_level"] = str(
            brief.get("audience_level") or "Curious non-expert listener; no specialist background assumed."
        ).strip()
        if self.creative_direction:
            direction = self.creative_direction.strip()
            if direction not in brief["required_concepts"]:
                brief["required_concepts"].insert(0, direction)
        if topic not in brief["required_concepts"]:
            brief["required_concepts"].insert(0, topic)
        brief["required_concepts"] = [str(x).strip() for x in brief["required_concepts"] if str(x).strip()][:8]
        if not brief.get("allowed_concepts"):
            brief["allowed_concepts"] = brief["required_concepts"][:5]
        brief["allowed_concepts"] = [str(x).strip() for x in brief["allowed_concepts"] if str(x).strip()][:5]
        allowed_lower = {x.lower() for x in brief["allowed_concepts"]}
        brief["teaser_only_concepts"] = [
            str(x).strip()
            for x in brief.get("teaser_only_concepts", [])
            if str(x).strip() and str(x).strip().lower() not in allowed_lower
        ][:4]
        brief["forbidden_drifts"] = [str(x).strip() for x in brief["forbidden_drifts"] if str(x).strip()][:8]
        brief["recurring_motifs"] = [str(x).strip() for x in brief["recurring_motifs"] if str(x).strip()][:6]
        if not brief.get("comprehension_contract"):
            brief["comprehension_contract"] = [
                "Keep the episode on one question instead of surveying the whole field.",
                "Use plain-language explanations before technical labels.",
                "Place recap sentences before major turns.",
                "Save advanced solution names for brief teasers unless they are essential.",
            ]
        brief["comprehension_contract"] = [
            str(x).strip() for x in brief["comprehension_contract"] if str(x).strip()
        ][:6]
        return brief

    def _compile_beat_sheet(self, topic: str, topic_brief: dict, script_model: str) -> dict:
        """Create a 20-scene structural outline before narration is drafted."""
        comprehension_contract = _build_comprehension_contract_block(topic_brief)
        beat_sheet = {
            "episode_thesis": str(topic_brief.get("core_thesis") or topic).strip(),
            "opening_hook": str(topic_brief.get("act_1_focus") or topic).strip(),
            "payoff": str(topic_brief.get("act_3_focus") or topic_brief.get("core_thesis") or topic).strip(),
            "ending_feeling": str(topic_brief.get("outro_focus") or "Leave the listener with wonder and intellectual honesty.").strip(),
            "scenes": [],
        }

        def _compile_chunk(stage_name: str, start_scene: int, count: int, act_rules: str, prior_context: str = "") -> list[dict]:
            prompt = (
                f"Create beat-sheet scenes {start_scene}-{start_scene + count - 1} "
                f"for a long-form video podcast about: {topic}\n\n"
                f"{_build_direction_block(self.creative_direction)}"
                f"Language: {self.language}\n"
                f"Locked topic brief:\n{json.dumps(topic_brief, ensure_ascii=False, indent=2)}\n\n"
                f"{comprehension_contract}\n"
                f"{prior_context}\n\n"
                "The beat sheet is a structural plan, not final narration.\n"
                f"Return EXACTLY {count} scenes.\n"
                f"{act_rules}\n"
                "Each scene must move the same central topic forward.\n"
                "Each scene must have one distinct job and at most one new hard concept.\n"
                "Use recap/checkpoint scenes deliberately instead of adding more concepts.\n"
                "Do not turn teaser-only concepts into full explanatory scenes.\n"
                "Hard length limits: purpose max 24 words, key_point max 32 words, "
                "emotional_turn max 18 words, visual_idea max 18 words.\n"
                "must_include and avoid must be short arrays, max 2 items each, max 10 words per item.\n"
                "Return ONLY valid JSON matching the schema with a top-level scenes array."
            )
            raw = generate_text_structured(
                prompt=prompt,
                system_prompt=(
                    "You are an expert documentary showrunner. Build precise scene-by-scene structure "
                    "before any narration is written. Return ONLY valid JSON."
                ),
                schema=BEAT_PATCH_SCHEMA,
                model_name=script_model,
            )
            result = self._parse_llm_json(raw, f"beat_sheet_{stage_name}")
            scenes = result.get("scenes") or []
            if len(scenes) != count:
                raise ValueError(f"Expected {count} {stage_name} beat scenes, got {len(scenes)}")
            for offset, scene in enumerate(scenes):
                scene["scene"] = start_scene + offset
            return scenes

        act1a = _compile_chunk(
            "act1a",
            1,
            4,
            "Scene 1 must start in media res with a concrete moment, event, question, or striking image. "
            "Scenes 2-4 are Act 1: context and essential setup.",
        )
        act1a_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in act1a],
            ensure_ascii=False,
        )
        act1b = _compile_chunk(
            "act1b",
            5,
            3,
            "Scenes 5-7 complete Act 1 with necessary facts and a bridge into Act 2.",
            prior_context=f"Scenes 1-4 already planned:\n{act1a_context}",
        )
        act1 = act1a + act1b
        act1_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in act1],
            ensure_ascii=False,
        )
        act2a = _compile_chunk(
            "act2a",
            8,
            3,
            "Scenes 8-10 begin Act 2: complication, tension, deeper explanation, and contrast.",
            prior_context=f"Act 1 beats already planned:\n{act1_context}",
        )
        act12a_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in (act1 + act2a)],
            ensure_ascii=False,
        )
        act2b = _compile_chunk(
            "act2b",
            11,
            3,
            "Scenes 11-13 finish Act 2 with midpoint escalation and a strong act break.",
            prior_context=f"Scenes 1-10 already planned:\n{act12a_context}",
        )
        act2 = act2a + act2b
        act12_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in (act1 + act2)],
            ensure_ascii=False,
        )
        act3a = _compile_chunk(
            "act3a",
            14,
            3,
            "Scenes 14-16 begin Act 3 with payoff and observational or practical stakes.",
            prior_context=f"Scenes 1-13 already planned:\n{act12_context}",
        )
        act123a_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in (act1 + act2 + act3a)],
            ensure_ascii=False,
        )
        act3b = _compile_chunk(
            "act3b",
            17,
            2,
            "Scenes 17-18 synthesize the unresolved frontier and recent progress without false closure.",
            prior_context=f"Scenes 1-16 already planned:\n{act123a_context}",
        )
        act123b_context = json.dumps(
            [{"scene": s.get("scene"), "purpose": s.get("purpose"), "key_point": s.get("key_point")} for s in (act1 + act2 + act3a + act3b)],
            ensure_ascii=False,
        )
        outro = _compile_chunk(
            "outro",
            19,
            2,
            "Scene 19 delivers the final payoff and resolution. "
            "Scene 20 is the outro: philosophical or memorable closing, no YouTube CTA.",
            prior_context=f"Scenes 1-18 already planned:\n{act123b_context}",
        )
        act3 = act3a + act3b + outro
        beat_sheet["scenes"] = act1 + act2 + act3
        return self._normalize_beat_sheet(beat_sheet)

    def _normalize_beat_sheet(self, beat_sheet: dict) -> dict:
        scenes = beat_sheet.get("scenes") or []
        if len(scenes) != 20:
            raise ValueError(f"Expected 20 beat scenes, got {len(scenes)}")
        normalized = []
        for index, scene in enumerate(scenes, start=1):
            item = dict(scene)
            item["scene"] = index
            item["act"] = _compact_text(item.get("act"), 40)
            item["purpose"] = _compact_text(item.get("purpose"), 220)
            item["key_point"] = _compact_text(item.get("key_point"), 260)
            item["emotional_turn"] = _compact_text(item.get("emotional_turn"), 180)
            item["visual_idea"] = _compact_text(item.get("visual_idea"), 180)
            item["must_include"] = [
                _compact_text(x, 120) for x in item.get("must_include", []) if str(x).strip()
            ][:3]
            item["avoid"] = [
                _compact_text(x, 120) for x in item.get("avoid", []) if str(x).strip()
            ][:3]
            normalized.append(item)
        beat_sheet["scenes"] = normalized
        return beat_sheet

    def _reconcile_beat_sheet(self, beat_sheet: dict, topic_brief: dict, script_model: str) -> dict:
        current_scenes = beat_sheet.get("scenes") or []
        comprehension_contract = _build_comprehension_contract_block(topic_brief)
        scene_map = [
            {
                "scene": scene.get("scene"),
                "act": scene.get("act"),
                "purpose": scene.get("purpose"),
                "key_point": scene.get("key_point"),
                "emotional_turn": scene.get("emotional_turn"),
                "visual_idea": scene.get("visual_idea"),
            }
            for scene in current_scenes
        ]
        prompt = (
            f"Reconcile this 20-scene beat sheet before QC for a long-form video podcast about: {self.topic}\n\n"
            f"Language: {self.language}\n"
            f"Creative direction: {self.creative_direction}\n\n"
            "You are seeing all 20 scenes after they were generated in separate chunks. "
            "Your job is to fix global structure problems caused by chunking.\n\n"
            f"{comprehension_contract}\n"
            "Global goals:\n"
            "- Every scene must have one distinct narrative job.\n"
            "- Remove repeated roles such as multiple bridge scenes, repeated paradox summaries, repeated quantum-gravity conclusions, or multiple outros.\n"
            "- Preserve a clear escalation: hook -> setup -> mechanism -> paradox -> attempted solutions -> frontier -> payoff -> outro.\n"
            "- Preserve a listener-friendly explanation path: one question -> one mechanism -> one conflict -> one payoff.\n"
            "- Move advanced side paths into teaser-only mentions when they are not needed for the main question.\n"
            "- Scene 20 must be the only true outro. Scene 19 must be final payoff, not another outro.\n"
            "- If two scenes repeat, differentiate their jobs instead of adding more exposition.\n"
            "- Keep all 20 scene numbers; do not delete scenes or change their order.\n\n"
            "Output rules:\n"
            "- Return ONLY scenes that need a patch, max 8 scenes.\n"
            "- Keep each returned scene number identical to its original scene number.\n"
            "- Do not rewrite polished scenes that already have a distinct role.\n"
            "- purpose max 24 words, key_point max 32 words, emotional_turn max 18 words, visual_idea max 18 words.\n"
            "- must_include and avoid max 2 items each, max 10 words per item.\n\n"
            f"TOPIC BRIEF JSON:\n{json.dumps(topic_brief, ensure_ascii=False)}\n\n"
            f"CURRENT 20-SCENE MAP JSON:\n{json.dumps(scene_map, ensure_ascii=False)}"
        )
        raw = generate_text_structured(
            prompt=prompt,
            system_prompt=(
                "You are a global documentary story editor. Reconcile structure across all scenes, "
                "patch only duplicated or misordered scene roles, and return only valid JSON."
            ),
            schema=BEAT_RECONCILE_SCHEMA,
            model_name=script_model,
        )
        result = self._parse_llm_json(raw, "beat_reconcile")
        patches = result.get("scenes") or []
        by_scene = {}
        for scene in patches[:8]:
            try:
                scene_number = int(scene.get("scene", 0))
            except (TypeError, ValueError):
                continue
            if 1 <= scene_number <= 20:
                by_scene[scene_number] = scene

        if not by_scene:
            print("Beat reconcile: no global patches needed")
            return beat_sheet

        merged = dict(beat_sheet)
        merged["scenes"] = [
            by_scene.get(int(scene.get("scene", 0)), scene)
            for scene in current_scenes
        ]
        reconciled = self._normalize_beat_sheet(merged)
        reconcile_report = {
            "editor_notes": [
                _compact_text(note, 220)
                for note in (result.get("editor_notes") or [])
                if str(note).strip()
            ][:8],
            "patched_scenes": sorted(by_scene),
        }
        with open(os.path.join(self.episode_dir, "beat_reconcile.json"), "w", encoding="utf-8") as f:
            json.dump(reconcile_report, f, ensure_ascii=False, indent=2)
        print(f"Beat reconcile: patched scenes={','.join(str(x) for x in sorted(by_scene))}")
        return reconciled

    def _beat_qc_needs_rewrite(self, report: dict) -> bool:
        if report.get("qc_error") and int(report.get("scene_count") or 0) == 20:
            return False
        status = str(report.get("status", "review")).lower()
        try:
            score = float(report.get("overall_score", 0))
        except (TypeError, ValueError):
            score = 0.0
        blocking_issues = [
            issue for issue in (report.get("issues") or [])
            if str(issue.get("severity", "")).lower() in {"high", "major", "critical"}
        ]
        return status != "pass" or score < 75 or bool(blocking_issues)

    def _beat_qc_can_continue_after_rewrites(self, report: dict) -> bool:
        """Let generation continue after QC has already spent its rewrite budget."""
        if report.get("qc_error"):
            return int(report.get("scene_count") or 0) == 20
        if int(report.get("scene_count") or 0) != 20:
            return False
        try:
            score = float(report.get("overall_score", 0))
        except (TypeError, ValueError):
            score = 0.0
        return score >= 70

    def _beat_rewrite_targets(self, report: dict) -> list[int]:
        targets = []
        for value in report.get("rewrite_targets") or []:
            try:
                scene_number = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= scene_number <= 20 and scene_number not in targets:
                targets.append(scene_number)
        for issue in report.get("issues") or []:
            try:
                scene_number = int(issue.get("scene") or issue.get("scene_number") or 0)
            except (TypeError, ValueError):
                continue
            if 1 <= scene_number <= 20 and scene_number not in targets:
                targets.append(scene_number)
        return targets

    def _rewrite_beat_sheet(
        self,
        beat_sheet: dict,
        qc_report: dict,
        topic_brief: dict,
        script_model: str,
        attempt: int,
    ) -> dict:
        targets = self._beat_rewrite_targets(qc_report)
        current_scenes = beat_sheet.get("scenes") or []
        full_scene_context = json.dumps(
            [
                {
                    "scene": scene.get("scene"),
                    "act": scene.get("act"),
                    "purpose": scene.get("purpose"),
                    "key_point": scene.get("key_point"),
                }
                for scene in current_scenes
            ],
            ensure_ascii=False,
        )
        if not targets:
            targets = [int(scene.get("scene", 0)) for scene in current_scenes[:2] if scene.get("scene")]

        def _scene_from_issue(issue: dict) -> int:
            try:
                return int(issue.get("scene") or issue.get("scene_number") or 0)
            except (TypeError, ValueError):
                return 0

        comprehension_contract = _build_comprehension_contract_block(topic_brief)
        by_scene = {}
        for batch_start in range(0, len(targets), 2):
            batch_targets = targets[batch_start:batch_start + 2]
            batch_set = set(batch_targets)
            target_text = ", ".join(str(t) for t in batch_targets)
            focused_scenes = [
                scene for scene in current_scenes
                if int(scene.get("scene", 0)) in batch_set
            ]
            focused_issues = [
                issue for issue in (qc_report.get("issues") or [])
                if _scene_from_issue(issue) in batch_set
            ]
            prompt = (
                f"Rewrite selected beat-sheet scenes for a long-form video podcast about: {self.topic}\n\n"
                f"Language: {self.language}\n"
                f"Creative direction: {self.creative_direction}\n"
                f"Rewrite attempt: {attempt}\n"
                f"Primary rewrite targets: {target_text}\n\n"
                f"{comprehension_contract}\n"
                "Rules:\n"
                "- Return ONLY the rewritten target scenes, not the full 20-scene beat sheet.\n"
                "- Keep each returned scene number identical to its original scene number.\n"
                "- The production contract requires exactly 20 scenes, so do not solve QC notes by deleting, merging, or renumbering scenes.\n"
                "- If QC asks to merge or cut scenes, reinterpret that as: make the duplicate scene do a distinct transition, landing, bridge, or payoff job.\n"
                "- Fix the listed QC issue directly, but keep the rewrite compact.\n"
                "- Do not drift away from the exact topic.\n"
                "- Fix listener comprehension by narrowing scene jobs before adding detail.\n"
                "- Keep teaser-only concepts brief; do not make them full scene lessons.\n"
                "- purpose max 30 words, key_point max 34 words, emotional_turn max 22 words, visual_idea max 20 words.\n"
                "- must_include and avoid max 3 items each; every item max 12 words.\n\n"
                f"TOPIC BRIEF JSON:\n{json.dumps(topic_brief, ensure_ascii=False)}\n\n"
                f"FULL 20-SCENE CONTEXT JSON:\n{full_scene_context}\n\n"
                f"TARGET SCENES JSON:\n{json.dumps(focused_scenes, ensure_ascii=False)}\n\n"
                f"TARGET QC ISSUES JSON:\n{json.dumps(focused_issues, ensure_ascii=False)}\n\n"
                f"MISSING BEATS JSON:\n{json.dumps(qc_report.get('missing_beats') or [], ensure_ascii=False)}"
            )
            raw = generate_text_structured(
                prompt=prompt,
                system_prompt=(
                    "You are a senior documentary story editor. Rewrite only what is needed, "
                    "keep every field concise, and return only valid JSON."
                ),
                schema=BEAT_PATCH_SCHEMA,
                model_name=script_model,
            )
            patches = self._parse_llm_json(
                raw,
                f"beat_rewrite_{attempt}_{batch_targets[0]}_{batch_targets[-1]}",
            ).get("scenes", [])
            for scene in patches:
                try:
                    scene_number = int(scene.get("scene", 0))
                except (TypeError, ValueError):
                    continue
                if scene_number in batch_set:
                    by_scene[scene_number] = scene
        if not by_scene:
            raise ValueError("Beat rewrite returned no target scenes")
        merged = dict(beat_sheet)
        merged["scenes"] = [
            by_scene.get(int(scene.get("scene", 0)), scene)
            for scene in current_scenes
        ]
        return self._normalize_beat_sheet(merged)

    def _repair_beat_sheet_structure(
        self,
        beat_sheet: dict,
        qc_report: dict,
        topic_brief: dict,
        script_model: str,
    ) -> dict:
        """Rewrite the whole 20-scene outline when local patches cannot fix global duplication."""
        comprehension_contract = _build_comprehension_contract_block(topic_brief)
        prompt = (
            f"Repair the full beat-sheet structure for a long-form video podcast about: {self.topic}\n\n"
            f"Language: {self.language}\n"
            f"Creative direction: {self.creative_direction}\n\n"
            f"{comprehension_contract}\n"
            "This is a structural repair pass after targeted rewrites failed.\n"
            "Return one complete beat sheet with exactly 20 scenes numbered 1 through 20.\n\n"
            "Hard rules:\n"
            "- Keep exactly 20 scenes; do not delete, merge, skip, duplicate, or renumber scenes.\n"
            "- Every scene must have a distinct narrative job.\n"
            "- If the QC report asks to merge or cut duplicated scenes, solve it by repurposing one scene into a bridge, landing pause, checkpoint, teaser, final payoff, or outro.\n"
            "- Scene 19 must be the single final payoff.\n"
            "- Scene 20 must be the only outro and must not repeat the final payoff.\n"
            "- Teaser-only concepts must stay brief and must not become full lessons.\n"
            "- Preserve the exact topic and the topic brief; do not invent a new episode.\n"
            "- Keep fields concise: purpose max 30 words, key_point max 34 words, emotional_turn max 22 words, visual_idea max 20 words.\n"
            "- must_include and avoid max 3 items each; every item max 12 words.\n\n"
            f"TOPIC BRIEF JSON:\n{json.dumps(topic_brief, ensure_ascii=False)}\n\n"
            f"CURRENT BEAT SHEET JSON:\n{json.dumps(beat_sheet, ensure_ascii=False)}\n\n"
            f"QC REPORT JSON:\n{json.dumps(qc_report, ensure_ascii=False)}"
        )
        raw = generate_text_structured(
            prompt=prompt,
            system_prompt=(
                "You are a senior documentary showrunner doing a full outline repair. "
                "Fix global duplication and pacing, keep exactly 20 scenes, and return only valid JSON."
            ),
            schema=BEAT_SHEET_SCHEMA,
            model_name=script_model,
        )
        repaired = self._parse_llm_json(raw, "beat_structural_repair")
        return self._normalize_beat_sheet(repaired)

    def _prepare_beat_sheet(self, topic: str, topic_brief: dict, script_model: str) -> tuple[dict, dict]:
        beat_sheet = self._compile_beat_sheet(topic, topic_brief, script_model)
        with open(os.path.join(self.episode_dir, "beat_sheet_initial.json"), "w", encoding="utf-8") as f:
            json.dump(beat_sheet, f, ensure_ascii=False, indent=2)

        beat_sheet = self._reconcile_beat_sheet(beat_sheet, topic_brief, script_model)
        with open(os.path.join(self.episode_dir, "beat_sheet_reconciled.json"), "w", encoding="utf-8") as f:
            json.dump(beat_sheet, f, ensure_ascii=False, indent=2)

        beat_qc_report = self._write_beat_quality_report(beat_sheet)
        for attempt in range(1, 3):
            if not self._beat_qc_needs_rewrite(beat_qc_report):
                break
            print(f"Beat QC rewrite attempt {attempt}/2...")
            beat_sheet = self._rewrite_beat_sheet(
                beat_sheet=beat_sheet,
                qc_report=beat_qc_report,
                topic_brief=topic_brief,
                script_model=script_model,
                attempt=attempt,
            )
            with open(os.path.join(self.episode_dir, f"beat_sheet_rewrite_{attempt}.json"), "w", encoding="utf-8") as f:
                json.dump(beat_sheet, f, ensure_ascii=False, indent=2)
            beat_qc_report = self._write_beat_quality_report(beat_sheet)
            beat_qc_report["rewrite_attempts"] = attempt
            with open(os.path.join(self.episode_dir, "beat_qc.json"), "w", encoding="utf-8") as f:
                json.dump(beat_qc_report, f, ensure_ascii=False, indent=2)

        if self._beat_qc_needs_rewrite(beat_qc_report):
            print("Beat QC structural repair pass...")
            beat_sheet = self._repair_beat_sheet_structure(
                beat_sheet=beat_sheet,
                qc_report=beat_qc_report,
                topic_brief=topic_brief,
                script_model=script_model,
            )
            with open(os.path.join(self.episode_dir, "beat_sheet_structural_repair.json"), "w", encoding="utf-8") as f:
                json.dump(beat_sheet, f, ensure_ascii=False, indent=2)
            beat_qc_report = self._write_beat_quality_report(beat_sheet)
            beat_qc_report["rewrite_attempts"] = 2
            beat_qc_report["structural_repair_attempted"] = True
            with open(os.path.join(self.episode_dir, "beat_qc.json"), "w", encoding="utf-8") as f:
                json.dump(beat_qc_report, f, ensure_ascii=False, indent=2)

        with open(os.path.join(self.episode_dir, "beat_sheet.json"), "w", encoding="utf-8") as f:
            json.dump(beat_sheet, f, ensure_ascii=False, indent=2)
        if self._beat_qc_needs_rewrite(beat_qc_report):
            if self._beat_qc_can_continue_after_rewrites(beat_qc_report):
                beat_qc_report["status"] = "accepted_with_warnings"
                beat_qc_report["summary"] = (
                    f"{beat_qc_report.get('summary', '').strip()} "
                    "Beat QC accepted with warnings after rewrite budget was exhausted; "
                    "script generation will continue using the latest beat sheet."
                ).strip()
                beat_qc_report["blocking_after_rewrites"] = False
                with open(os.path.join(self.episode_dir, "beat_qc.json"), "w", encoding="utf-8") as f:
                    json.dump(beat_qc_report, f, ensure_ascii=False, indent=2)
                return beat_sheet, beat_qc_report
            beat_qc_report["status"] = "blocked"
            beat_qc_report["summary"] = (
                f"{beat_qc_report.get('summary', '').strip()} "
                "Beat QC still needs review after 2 rewrite attempts."
            ).strip()
            beat_qc_report["blocking_after_rewrites"] = True
            with open(os.path.join(self.episode_dir, "beat_qc.json"), "w", encoding="utf-8") as f:
                json.dump(beat_qc_report, f, ensure_ascii=False, indent=2)
            raise RuntimeError("Beat QC blocked script generation after 2 rewrite attempts.")
        return beat_sheet, beat_qc_report

    def _write_beat_quality_report(self, beat_sheet: dict) -> dict:
        """Create a non-blocking QC report for the beat sheet."""
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")

        report_path = os.path.join(self.episode_dir, "beat_qc.json")
        scenes = beat_sheet.get("scenes") if isinstance(beat_sheet, dict) else []
        scene_count = len(scenes or [])
        fallback_report = {
            "overall_score": 0 if scene_count != 20 else 70,
            "status": "review" if scene_count != 20 else "pass",
            "summary": "Deterministic beat QC completed. LLM QC was not available.",
            "issues": [],
            "rewrite_targets": [],
            "missing_beats": [],
            "retention_notes": [],
            "comprehension_notes": [],
            "scene_count": scene_count,
        }
        if scene_count != 20:
            fallback_report["issues"].append({
                "severity": "high",
                "scene": 0,
                "issue": f"Expected 20 beat scenes, got {scene_count}.",
                "suggestion": "Regenerate the beat sheet before drafting narration.",
            })

        try:
            script_model = get_podcast_script_model()
            prompt = (
                f"Topic: {self.topic}\n"
                f"Language: {self.language}\n"
                f"Creative direction: {self.creative_direction}\n\n"
                "Review this beat sheet before narration is drafted. "
                "Check topic focus, act progression, hook strength, repetition, missing payoff, "
                "scene-to-scene escalation, listener comprehension, concept overload, recap placement, "
                "hard-term pacing, and visual usefulness. "
                "Important production contract: this pipeline intentionally uses exactly 20 scenes. "
                "Do not recommend deleting, merging, reducing below 20 scenes, or changing scene numbers. "
                "When two scenes overlap, judge whether one can be converted into a distinct bridge, landing pause, "
                "transition, teaser, or payoff job within the fixed 20-scene structure. "
                "Score 0-100. Use status 'pass' only if this is ready for narration drafting; "
                "otherwise use 'review'. Use scene numbers as 1-based indexes.\n\n"
                "Comprehension rules:\n"
                "- Flag any scene that introduces more than one hard concept.\n"
                "- Flag advanced concepts that should be teaser-only but are treated as full lessons.\n"
                "- Flag missing recap/checkpoint moments after dense sections.\n"
                "- Put listener-understanding notes in comprehension_notes.\n\n"
                f"BEAT SHEET JSON:\n{json.dumps(beat_sheet, ensure_ascii=False)}"
            )
            raw = generate_text_structured(
                prompt=prompt,
                system_prompt=(
                    "You are a senior story editor reviewing a documentary podcast outline. "
                    "Return ONLY valid JSON matching the schema."
                ),
                schema=BEAT_QC_SCHEMA,
                model_name=script_model,
            )
            report = self._parse_llm_json(raw, "beat_qc")
            report["scene_count"] = scene_count
            report["status"] = str(report.get("status", "review")).lower()
            if report["status"] not in {"pass", "review"}:
                report["status"] = "review"
        except Exception as exc:
            report = fallback_report
            report["qc_error"] = str(exc)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(
            "Beat QC: "
            f"{report.get('status', 'review')} "
            f"score={report.get('overall_score', 0)} "
            f"issues={len(report.get('issues') or [])}"
        )
        return report

    def _load_script_scenes(self) -> list:
        if not self.episode_dir:
            raise ValueError("episode_dir is not set. Call generate_script() before generate_assets().")
        script_path = os.path.join(self.episode_dir, "script.json")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"script.json not found at {script_path}")
        with open(script_path, "r", encoding="utf-8") as f:
            scenes = json.load(f)
        if not scenes:
            raise ValueError("script.json is empty")
        return scenes

    def _scene_audio_path(self, scene_index: int) -> str:
        scene_num = str(scene_index).zfill(2)
        return os.path.join(self.episode_dir, f"scene_{scene_num}.wav")

    def _scene_asset_base(self, scene_index: int) -> str:
        return os.path.join(self.episode_dir, f"scene_{str(scene_index).zfill(2)}")

    def _format_timestamp(self, seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _scene_duration_seconds(self, scene_index: int) -> float:
        wav_path = self._scene_audio_path(scene_index)
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"scene_{str(scene_index).zfill(2)}.wav not found at {wav_path}")
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                wav_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())

    def _build_chapter_timestamps(self, scenes: list[dict]) -> str:
        if not scenes:
            return ""

        lines = ["Chapters:"]
        elapsed = 0.0
        for index, scene in enumerate(scenes):
            scene_title = str(scene.get("scene_title", "")).strip() or f"Scene {index + 1}"
            lines.append(f"{self._format_timestamp(elapsed)} {scene_title}")
            elapsed += self._scene_duration_seconds(index)
        return "\n".join(lines)

    def _build_glossary_entries(self, scenes: list[dict], scene_durations: list[float]) -> list[dict]:
        """Create one-time glossary overlays for hard terms found in narration."""
        entries: list[dict] = []
        used_terms: set[str] = set()
        elapsed = 0.0

        for index, scene in enumerate(scenes):
            duration = scene_durations[index] if index < len(scene_durations) else 0.0
            narration = str(scene.get("narration", "") or "")
            lower_narration = narration.lower()

            if duration < 8:
                elapsed += duration
                continue

            for term, aliases, meaning in GLOSSARY_TERMS:
                term_key = term.lower()
                if term_key in used_terms:
                    continue
                if any(alias.lower() in lower_narration for alias in aliases):
                    used_terms.add(term_key)
                    # Start after the chapter title has mostly faded, without waiting too long.
                    start_offset = min(max(4.2, duration * 0.18), max(0.0, duration - 5.5))
                    entries.append({
                        "term": term,
                        "meaning": meaning,
                        "start": round(elapsed + start_offset, 2),
                        "duration": 5.0,
                        "scene": index + 1,
                    })
                    break

            elapsed += duration

        return entries

    def _normalize_rendered_audio(self, input_path: str, output_path: str) -> None:
        """Normalize podcast render loudness without re-encoding video."""
        temp_output = output_path + ".tmp.mp4"
        if os.path.exists(temp_output):
            os.remove(temp_output)
        print("Normalizing final audio loudness to -16 LUFS...")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-movflags",
                "+faststart",
                temp_output,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        if not os.path.exists(temp_output) or os.path.getsize(temp_output) <= 1_000_000:
            raise RuntimeError("Audio normalization did not create a valid final video.")
        os.replace(temp_output, output_path)

    def _write_script_quality_report(self, scenes: list[dict], source: str = "generated") -> dict:
        """Create a non-blocking script QC report for review before asset generation."""
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")

        report_path = os.path.join(self.episode_dir, "script_qc.json")
        scene_count = len(scenes or [])
        missing_fields = []
        for index, scene in enumerate(scenes or [], start=1):
            for field in ("scene_title", "narration", "image_prompt"):
                if not str(scene.get(field, "")).strip():
                    missing_fields.append({"scene": index, "field": field})

        fallback_report = {
            "overall_score": 0 if scene_count != 20 or missing_fields else 70,
            "status": "review" if scene_count != 20 or missing_fields else "pass",
            "summary": "Deterministic QC completed. LLM QC was not available.",
            "strengths": [],
            "issues": [],
            "rewrite_targets": [],
            "retention_notes": [],
            "visual_notes": [],
            "comprehension_notes": [],
            "source": source,
            "scene_count": scene_count,
            "missing_fields": missing_fields,
        }
        if scene_count != 20:
            fallback_report["issues"].append({
                "severity": "high",
                "scene": 0,
                "issue": f"Expected 20 scenes, got {scene_count}.",
                "suggestion": "Regenerate or split the script into exactly 20 scenes before asset generation.",
            })
        for item in missing_fields:
            fallback_report["issues"].append({
                "severity": "high",
                "scene": item["scene"],
                "issue": f"Missing {item['field']}.",
                "suggestion": "Fill the missing field before asset generation.",
            })
            fallback_report["rewrite_targets"].append(item["scene"])

        try:
            script_model = get_podcast_script_model()
            compact_scenes = [
                {
                    "scene": index + 1,
                    "title": scene.get("scene_title", ""),
                    "narration": scene.get("narration", ""),
                    "image_prompt": scene.get("image_prompt", ""),
                }
                for index, scene in enumerate(scenes or [])
            ]
            system_prompt = (
                "You are a senior podcast script editor and retention analyst. "
                "Review the script for topic focus, hook strength, scene flow, repetition, payoff, "
                "spoken-language quality, listener comprehension, concept density, term explanation, "
                "recap cadence, and visual prompt usefulness. "
                "Return ONLY valid JSON matching the provided schema. "
                "Use status 'pass' when the script is ready for asset generation. "
                "Use status 'review' for editorial improvements that should guide rewrites. "
                "Reserve severity 'high' for true asset-blocking problems: missing core beats, incoherent "
                "story flow, unusable visual prompts, severe repetition that would feel like duplicate scenes, "
                "concept density that would make the target listener unable to follow, or narration that cannot "
                "be spoken cleanly. Mark polish, light pacing, or wording issues as medium or low unless they "
                "make the episode unusable."
            )
            prompt = (
                f"Topic: {self.topic}\n"
                f"Language: {self.language}\n"
                f"Creative direction: {self.creative_direction}\n"
                f"Source: {source}\n\n"
                "Score the script from 0-100. "
                "Call out only actionable issues, with scene numbers using 1-based indexing. "
                "Use severity low, medium, or high. "
                "A script with complete structure and score 80+ should not be blocked for polish-only issues; "
                "use review plus warnings instead.\n"
                "Put notes about whether a non-specialist listener can follow the episode in comprehension_notes. "
                "Check that hard terms are explained in plain language and that recap/checkpoint sentences appear "
                "after dense runs of scenes.\n\n"
                f"SCENES JSON:\n{json.dumps(compact_scenes, ensure_ascii=False)}"
            )
            raw = generate_text_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=SCRIPT_QC_SCHEMA,
                model_name=script_model,
            )
            report = self._parse_llm_json(raw, f"script_qc_{source}")
            report["source"] = source
            report["scene_count"] = scene_count
            report["missing_fields"] = missing_fields
            report["status"] = str(report.get("status", "review")).lower()
            if report["status"] not in {"pass", "review", "blocked"}:
                report["status"] = "review"
        except Exception as exc:
            report = fallback_report
            report["qc_error"] = str(exc)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(
            "Script QC: "
            f"{report.get('status', 'review')} "
            f"score={report.get('overall_score', 0)} "
            f"issues={len(report.get('issues') or [])}"
        )
        return report

    def _script_qc_needs_rewrite(self, report: dict) -> bool:
        if report.get("qc_error") and int(report.get("scene_count") or 0) == 20:
            return False
        status = str(report.get("status", "review")).lower()
        try:
            score = float(report.get("overall_score", 0))
        except (TypeError, ValueError):
            score = 0.0
        blocking_issues = [
            issue for issue in (report.get("issues") or [])
            if str(issue.get("severity", "")).lower() in {"high", "major", "critical"}
        ]
        return status != "pass" or score < 75 or bool(blocking_issues)

    def _script_qc_can_accept_after_rewrites(self, report: dict) -> bool:
        try:
            score = float(report.get("overall_score", 0))
        except (TypeError, ValueError):
            score = 0.0
        scene_count = int(report.get("scene_count") or 0)
        missing_fields = report.get("missing_fields") or []
        return scene_count == 20 and not missing_fields and score >= 80

    def _script_rewrite_targets(self, report: dict) -> list[int]:
        targets = []
        for value in report.get("rewrite_targets") or []:
            try:
                scene_number = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= scene_number <= 20 and scene_number not in targets:
                targets.append(scene_number)
        for issue in report.get("issues") or []:
            try:
                scene_number = int(issue.get("scene", 0))
            except (TypeError, ValueError):
                continue
            if 1 <= scene_number <= 20 and scene_number not in targets:
                targets.append(scene_number)
        return targets

    def _rewrite_script_scenes(
        self,
        scenes: list[dict],
        qc_report: dict,
        beat_sheet: dict,
        topic_brief: dict,
        script_model: str,
        attempt: int,
    ) -> list[dict]:
        targets = self._script_rewrite_targets(qc_report)
        target_text = ", ".join(str(t) for t in targets) if targets else "the weakest scenes only"
        target_set = set(targets)
        focused_scenes = [
            {
                "scene": index + 1,
                "scene_title": scene.get("scene_title", ""),
                "narration": scene.get("narration", ""),
                "image_prompt": scene.get("image_prompt", ""),
            }
            for index, scene in enumerate(scenes)
            if not target_set or (index + 1) in target_set
        ]
        focused_beats = [
            beat for beat in (beat_sheet.get("scenes") or [])
            if not target_set or int(beat.get("scene", 0)) in target_set
        ]
        focused_issues = [
            issue for issue in (qc_report.get("issues") or [])
            if not target_set or int(issue.get("scene", 0) or 0) in target_set
        ]
        comprehension_contract = _build_comprehension_contract_block(topic_brief)
        prompt = (
            f"Rewrite selected scenes in a 20-scene video podcast script about: {self.topic}\n\n"
            f"Language: {self.language}\n"
            f"Creative direction: {self.creative_direction}\n"
            f"Rewrite attempt: {attempt}\n"
            f"Primary rewrite targets: {target_text}\n\n"
            f"{comprehension_contract}\n"
            "Rules:\n"
            "- Return ONLY the rewritten target scenes, not the full 20-scene script.\n"
            "- Keep each returned scene number identical to its original scene number.\n"
            "- Keep the same language as the original script.\n"
            "- Keep each narration natural for spoken TTS.\n"
            "- Fix every QC issue directly.\n"
            "- Reduce concept overload before polishing wording.\n"
            "- Add or preserve listener checkpoint sentences when a scene follows dense material.\n"
            "- Keep image_prompt in English only and concrete for visual generation.\n"
            "- Follow the target beat sheet.\n\n"
            f"TARGET BEATS JSON:\n{json.dumps(focused_beats, ensure_ascii=False)}\n\n"
            f"FOCUSED SCENES TO FIX:\n{json.dumps(focused_scenes, ensure_ascii=False)}\n\n"
            f"TARGET QC ISSUES JSON:\n{json.dumps(focused_issues, ensure_ascii=False)}"
        )
        raw = generate_text_structured(
            prompt=prompt,
            system_prompt=(
                "You are a senior podcast script editor. Rewrite only what needs repair, "
                "and return only the corrected target scenes as valid JSON."
            ),
            schema=SCRIPT_PATCH_SCHEMA,
            model_name=script_model,
        )
        try:
            rewritten = self._parse_llm_json(raw, f"script_rewrite_{attempt}").get("scenes", [])
        except json.JSONDecodeError:
            raw_path = os.path.join(self.episode_dir, f"script_rewrite_{attempt}_raw.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(raw)
            raise ValueError(f"Script rewrite returned invalid JSON. Raw response saved to {raw_path}")
        by_scene = {int(scene.get("scene", 0)): scene for scene in rewritten if scene.get("scene")}
        if not by_scene:
            raise ValueError("Script rewrite returned no target scenes")
        merged = []
        for index, scene in enumerate(scenes, start=1):
            patch = by_scene.get(index)
            if patch:
                merged.append({
                    "scene_title": patch.get("scene_title", scene.get("scene_title", "")),
                    "narration": patch.get("narration", scene.get("narration", "")),
                    "image_prompt": patch.get("image_prompt", scene.get("image_prompt", "")),
                })
            else:
                merged.append(scene)
        return merged

    def _prepare_script_scenes(
        self,
        scenes: list[dict],
        beat_sheet: dict,
        topic_brief: dict,
        script_model: str,
    ) -> tuple[list[dict], dict]:
        with open(os.path.join(self.episode_dir, "script_initial.json"), "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)

        qc_report = self._write_script_quality_report(scenes, source="generated")
        for attempt in range(1, 3):
            if not self._script_qc_needs_rewrite(qc_report):
                break
            print(f"Script QC rewrite attempt {attempt}/2...")
            scenes = self._rewrite_script_scenes(
                scenes=scenes,
                qc_report=qc_report,
                beat_sheet=beat_sheet,
                topic_brief=topic_brief,
                script_model=script_model,
                attempt=attempt,
            )
            with open(os.path.join(self.episode_dir, f"script_rewrite_{attempt}.json"), "w", encoding="utf-8") as f:
                json.dump(scenes, f, ensure_ascii=False, indent=2)
            qc_report = self._write_script_quality_report(scenes, source=f"rewrite_{attempt}")
            qc_report["rewrite_attempts"] = attempt
            with open(os.path.join(self.episode_dir, "script_qc.json"), "w", encoding="utf-8") as f:
                json.dump(qc_report, f, ensure_ascii=False, indent=2)

        if self._script_qc_needs_rewrite(qc_report):
            if self._script_qc_can_accept_after_rewrites(qc_report):
                qc_report["status"] = "accepted_with_warnings"
                qc_report["summary"] = (
                    f"{qc_report.get('summary', '').strip()} "
                    "Script QC accepted with warnings after rewrite budget was exhausted; "
                    "asset generation will continue using the latest script."
                ).strip()
                qc_report["blocking_after_rewrites"] = False
                with open(os.path.join(self.episode_dir, "script_qc.json"), "w", encoding="utf-8") as f:
                    json.dump(qc_report, f, ensure_ascii=False, indent=2)
                return scenes, qc_report
            qc_report["status"] = "blocked"
            qc_report["summary"] = (
                f"{qc_report.get('summary', '').strip()} "
                "Script QC still needs review after 2 rewrite attempts."
            ).strip()
            qc_report["blocking_after_rewrites"] = True
            with open(os.path.join(self.episode_dir, "script_qc.json"), "w", encoding="utf-8") as f:
                json.dump(qc_report, f, ensure_ascii=False, indent=2)
            raise RuntimeError("Script QC blocked asset generation after 2 rewrite attempts.")
        return scenes, qc_report

    # ------------------------------------------------------------------
    # Feature 1 โ€” TTS with scene_index
    # ------------------------------------------------------------------

    def _generate_scene_audio_with_retry(
        self, narration: str, audio_path: str, scene_number: int,
        scene_index: int = -1, total_scenes: int = 20,
    ) -> None:
        last_error = None
        mp3_path = audio_path.replace(".wav", ".mp3")
        max_attempts = max(1, get_podcast_audio_retry_count())
        for attempt in range(1, max_attempts + 1):
            try:
                if self.language == "Thai" and self.tts_source == "elevenlabs":
                    TTS().synthesize_elevenlabs(narration, output_file=audio_path)
                elif self.language == "Thai" and self.tts_source == "gemini":
                    TTS().synthesize_gemini(
                        narration, output_file=audio_path,
                        scene_index=scene_index, total_scenes=total_scenes,
                    )
                elif self.language == "Thai":
                    TTS().synthesize(
                        narration,
                        output_file=audio_path,
                        voice=get_tts_edge_thai_voice(),
                        rate=get_tts_edge_thai_rate(),
                    )
                else:
                    TTS().synthesize(
                        narration,
                        output_file=audio_path,
                        voice=get_tts_edge_voice(),
                        rate=get_tts_edge_rate(),
                    )
                if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                    raise RuntimeError("tts provider did not return a valid wav file")
                return
            except Exception as exc:
                last_error = exc
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                print(
                    f"  Warning: audio generation failed for scene {scene_number} "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                if attempt < max_attempts:
                    time.sleep(2)
        raise RuntimeError(
            f"Scene {scene_number}: audio generation failed after {max_attempts} attempts: {last_error}"
        ) from last_error

    # ------------------------------------------------------------------
    # Feature 2 โ€” gen audio first, then scale image count by duration
    # Feature 3 โ€” Pexels B-roll for secondary images
    # ------------------------------------------------------------------

    def _generate_scene_image_with_retry(
        self, image_prompt: str, image_path: str, scene_number: int,
    ) -> None:
        last_error = None
        max_attempts = max(1, get_podcast_image_retry_count())
        for attempt in range(1, max_attempts + 1):
            try:
                result = generate_image(image_prompt, image_path)
                if result is None or not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                    raise RuntimeError("image provider did not return a valid image")
                return
            except Exception as exc:
                last_error = exc
                if os.path.exists(image_path):
                    os.remove(image_path)
                print(
                    f"  Warning: image generation failed for scene {scene_number} "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                if attempt < max_attempts:
                    time.sleep(2)
        raise RuntimeError(
            f"Scene {scene_number}: image generation failed after {max_attempts} attempts: {last_error}"
        ) from last_error

    def _get_seconds_per_image(self) -> int:
        return int(_get_config_value("podcast_v2_seconds_per_image", 8))

    def _get_pexels_api_key(self) -> str:
        return str(_get_config_value("pexels_api_key", "") or "")

    def _fallback_image_prompt_for_asset(
        self,
        scene: dict,
        narration_chunk: str,
        asset_idx: int,
    ) -> tuple[str, str]:
        roles = [
            (
                "detail",
                "Create a macro or close-up detail of one concrete object, particle interaction, "
                "instrument, texture, or physical clue from this moment. Avoid a wide scene."
            ),
            (
                "metaphor",
                "Create a symbolic visual metaphor for the idea in this moment. Use a new visual motif, "
                "not the same literal subject as the anchor image."
            ),
            (
                "environment",
                "Create a wide environmental or mood shot that supports this moment through place, "
                "lighting, scale, or atmosphere. Focus on setting, not the anchor subject."
            ),
            (
                "human_scale",
                "Create a human-scale visual anchor such as a lab, observatory, instrument, notebook, "
                "screen, or silhouette reacting to the concept. Do not show a celebrity likeness."
            ),
            (
                "texture",
                "Create an abstract field, data, material, equation-free pattern, or particle texture "
                "that can work as connective visual tissue."
            ),
        ]
        role_name, role_direction = roles[(asset_idx - 1) % len(roles)]
        title = _compact_text(scene.get("scene_title", ""), 80)
        anchor_prompt = _compact_text(scene.get("image_prompt", ""), 420)
        moment = _compact_text(narration_chunk or scene.get("narration", ""), 300)
        prompt = (
            f"{anchor_prompt}\n\n"
            f"Fallback asset role: {role_name}.\n"
            f"{role_direction}\n"
            f"Scene title: {title}\n"
            f"Narration moment to visualize: {moment}\n\n"
            "Make this image visibly different from the scene anchor: change subject emphasis, "
            "camera distance, composition, and visual motif. Do not recreate the same framing. "
            "No text overlays, no logos, cinematic 16:9."
        )
        return role_name, prompt

    def generate_scene_assets(
        self,
        scene_index: int,
        force_image: bool = False,
        force_audio: bool = False,
        total_scenes: int = 20,
        _scenes: list | None = None,
        _pexels_key: str | None = None,
        _seconds_per_image: int | None = None,
    ) -> None:
        """Generate audio then scaled multi-image assets for a single scene.

        Audio is generated first so its duration drives n_images.
        Image[0] is always AI-generated (anchor visual).
        Image[1+] try Pexels B-roll first, fall back to AI gen.
        """
        scenes = _scenes if _scenes is not None else self._load_script_scenes()
        if scene_index < 0 or scene_index >= len(scenes):
            raise ValueError(f"scene_index must be between 0 and {len(scenes) - 1}")

        scene = scenes[scene_index]
        scene_num = str(scene_index).zfill(2)
        audio_path = self._scene_audio_path(scene_index)
        scene_number = scene_index + 1
        script_model = get_podcast_script_model()

        # Clear existing assets if forced
        if force_audio and os.path.exists(audio_path):
            os.remove(audio_path)
        if force_audio:
            mp3_path = audio_path.replace(".wav", ".mp3")
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
        if force_image:
            for f in glob.glob(os.path.join(self.episode_dir, f"scene_{scene_num}_*.png")):
                os.remove(f)
            for f in glob.glob(os.path.join(self.episode_dir, f"scene_{scene_num}_*.mp4")):
                os.remove(f)

        # โ”€โ”€ Step A: Generate audio (Feature 1 + 2) โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€
        if not os.path.exists(audio_path):
            self._generate_scene_audio_with_retry(
                scene["narration"], audio_path, scene_number,
                scene_index=scene_index, total_scenes=total_scenes,
            )

        # โ”€โ”€ Step B: Measure duration & decide n_images โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€
        duration = _get_audio_duration(audio_path)
        spi = _seconds_per_image if _seconds_per_image is not None else self._get_seconds_per_image()
        n_images = max(1, round(duration / spi)) if duration > 0 else 1
        time_per_asset = duration / n_images if n_images > 0 else spi

        # Split narration into n_images chunks for per-asset keyword gen
        narration = scene.get("narration", "")
        words = narration.split()
        chunk_size = max(1, math.ceil(len(words) / n_images) if words else 1)
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, max(1, len(words)), chunk_size)]
        chunks = chunks[:n_images]
        while len(chunks) < n_images:
            chunks.append(chunks[-1] if chunks else narration[:100])

        # โ”€โ”€ Step C: Generate images (Feature 2 + 3) โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€โ”€
        pexels_key = _pexels_key if _pexels_key is not None else self._get_pexels_api_key()

        for asset_idx in range(n_images):
            png_path = os.path.join(self.episode_dir, f"scene_{scene_num}_{asset_idx}.png")
            mp4_path = os.path.join(self.episode_dir, f"scene_{scene_num}_{asset_idx}.mp4")

            # Skip if already exists (resumability)
            if os.path.exists(png_path) or os.path.exists(mp4_path):
                continue

            if asset_idx == 0:
                # Anchor visual โ€” always AI gen
                self._generate_scene_image_with_retry(scene["image_prompt"], png_path, scene_number)
            else:
                # Try Pexels B-roll first
                broll_found = False
                if pexels_key:
                    from pexels_provider import search_pexels_video
                    result = search_pexels_video(
                        narration_chunk=chunks[asset_idx],
                        api_key=pexels_key,
                        output_path=mp4_path,
                        time_per_asset=time_per_asset,
                        asset_index=asset_idx,
                    )
                    if result:
                        broll_found = True
                        print(f"  Pexels B-roll: scene {scene_number} asset {asset_idx}")

                if not broll_found:
                    # Fall back to AI gen with a distinct visual role per asset.
                    role_name, varied_prompt = self._fallback_image_prompt_for_asset(
                        scene,
                        chunks[asset_idx],
                        asset_idx,
                    )
                    print(f"  AI fallback image: scene {scene_number} asset {asset_idx} role={role_name}")
                    self._generate_scene_image_with_retry(varied_prompt, png_path, scene_number)

    def _generate_scene0_video(self, image_path: str, scene: dict, video_path: str) -> None:
        """Generate Kling animated clip for scene 0 (same as V1)."""
        access_key = get_kling_access_key()
        secret_key = get_kling_secret_key()
        if not access_key or not secret_key:
            print("  Skipping scene 0 video: Kling keys not configured.")
            return
        image_prompt_excerpt = scene.get("image_prompt", "")[:200]
        prompt = f"Gentle ambient camera motion, slow zoom in. {image_prompt_excerpt}"
        print("  Generating scene 0 video via Kling (this takes ~1-2 min)...")
        try:
            generate_video_from_image(
                image_path=image_path,
                prompt=prompt,
                access_key=access_key,
                secret_key=secret_key,
                output_path=video_path,
                duration=5,
            )
            print(f"  Scene 0 video ready: {video_path}")
        except Exception as exc:
            print(f"  Warning: Kling video generation failed: {exc}")
            if os.path.exists(video_path):
                os.remove(video_path)

    def generate_assets(self) -> None:
        """Generate per-scene multi-image/audio assets (V2).

        Reads script.json. Produces:
          scene_NN.wav            โ€” TTS audio
          scene_NN_0.png          โ€” anchor AI image
          scene_NN_1.mp4/.png     โ€” B-roll or AI variant
          scene_NN_2.png          โ€” AI variant (if needed)
          ...
          scene_00.mp4            โ€” Kling intro video (scene 0 only, V1 compat.)
        """
        scenes = self._load_script_scenes()
        total = len(scenes)
        pexels_key = self._get_pexels_api_key()
        seconds_per_image = self._get_seconds_per_image()

        for i, scene in enumerate(scenes):
            audio_path = self._scene_audio_path(i)
            scene_num = str(i).zfill(2)
            anchor_img = os.path.join(self.episode_dir, f"scene_{scene_num}_0.png")

            if os.path.exists(anchor_img) and os.path.exists(audio_path):
                print(f"Skipping scene {i + 1}/{total} (already generated).")
            else:
                print(f"Generating V2 assets for scene {i + 1}/{total}...")
                self.generate_scene_assets(
                    i, total_scenes=total,
                    _scenes=scenes, _pexels_key=pexels_key, _seconds_per_image=seconds_per_image,
                )

            # Scene 0: Kling intro video (uses anchor image)
            if i == 0:
                kling_video_path = os.path.join(self.episode_dir, "scene_00.mp4")
                if not os.path.exists(kling_video_path) or os.path.getsize(kling_video_path) < 10_000:
                    if os.path.exists(anchor_img):
                        self._generate_scene0_video(anchor_img, scene, kling_video_path)

    # ------------------------------------------------------------------
    # Feature 4 โ€” render() with multi-asset Remotion props
    # ------------------------------------------------------------------

    def render(self) -> None:
        """Render V2 podcast video via Remotion.

        Collects all per-scene assets (scene_NN_K.png / scene_NN_K.mp4),
        builds multi-asset Remotion props, and invokes the renderer.
        """
        if not self.episode_dir:
            raise ValueError("episode_dir is not set. Call generate_script() before render().")

        scenes = self._load_script_scenes()
        total = len(scenes)
        final_path = os.path.join(self.episode_dir, "final.mp4")
        raw_final_path = os.path.join(self.episode_dir, "final_unnormalized.mp4")

        if os.path.exists(final_path) and os.path.getsize(final_path) > 1_000_000:
            print(f"Skipping render (final.mp4 already exists at {final_path}).")
            return
        if os.path.exists(raw_final_path):
            os.remove(raw_final_path)

        wav_paths = []
        scene_durations = []
        all_image_paths: list[str] = []
        scene_image_counts: list[int] = []
        scene_asset_types: list[str] = []

        for i in range(total):
            scene_num = str(i).zfill(2)
            wav_path = os.path.join(self.episode_dir, f"scene_{scene_num}.wav")

            if not os.path.exists(wav_path):
                raise FileNotFoundError(
                    f"scene_{scene_num}.wav not found at {wav_path}. "
                    "Run generate_assets() first."
                )

            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
                capture_output=True, text=True, check=True,
            )
            duration = float(result.stdout.strip())
            wav_paths.append(wav_path)
            scene_durations.append(duration)

            # Collect assets for this scene in index order
            asset_idx = 0
            scene_assets: list[tuple[str, str]] = []  # (abs_path, type)

            while True:
                png = os.path.join(self.episode_dir, f"scene_{scene_num}_{asset_idx}.png")
                mp4 = os.path.join(self.episode_dir, f"scene_{scene_num}_{asset_idx}.mp4")
                if os.path.exists(png):
                    scene_assets.append((os.path.abspath(png), "image"))
                elif os.path.exists(mp4):
                    scene_assets.append((os.path.abspath(mp4), "video"))
                else:
                    break
                asset_idx += 1

            if not scene_assets:
                # Fallback: look for legacy scene_NN.png (V1-style single image)
                legacy_png = os.path.join(self.episode_dir, f"scene_{scene_num}.png")
                if os.path.exists(legacy_png):
                    scene_assets.append((os.path.abspath(legacy_png), "image"))
                else:
                    raise FileNotFoundError(
                        f"No assets found for scene {i} (scene_{scene_num}_0.png / .mp4 missing). "
                        "Run generate_assets() first."
                    )

            for path, asset_type in scene_assets:
                all_image_paths.append(path)
                scene_asset_types.append(asset_type)
            scene_image_counts.append(len(scene_assets))

        total_duration = sum(scene_durations)

        # Merge audio
        merged_audio = os.path.join(self.episode_dir, "merged_audio.wav")
        if not os.path.exists(merged_audio):
            concat_audio_path = os.path.join(self.episode_dir, "audio_concat.txt")
            with open(concat_audio_path, "w", encoding="utf-8") as f:
                for wav in wav_paths:
                    abs_wav = os.path.abspath(wav).replace("\\", "/")
                    f.write(f"file '{abs_wav}'\n")
            print("Merging scene audio files...")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", concat_audio_path, "-c", "copy", merged_audio],
                capture_output=True, text=True, check=True,
            )

        # Build per-asset durations: each asset in a scene shares equal time
        scene_asset_durations: list[float] = []
        for i, count in enumerate(scene_image_counts):
            per_asset = scene_durations[i] / count
            scene_asset_durations.extend([per_asset] * count)

        from pathlib import Path
        remotion_dir = Path(ROOT_DIR) / "remotion"
        scene_titles = [s.get("scene_title", "") for s in scenes][:total]
        glossary_entries = self._build_glossary_entries(scenes, scene_durations)

        props = {
            "composition": "VideoPodcast",
            "imagePaths": all_image_paths,
            "audioPath": os.path.abspath(merged_audio),
            "sceneDurations": scene_durations,
            "sceneTitles": scene_titles,
            "durationInSeconds": total_duration,
            "outputPath": os.path.abspath(raw_final_path),
            "sceneImageCounts": scene_image_counts,
            "sceneAssetTypes": scene_asset_types,
            "sceneAssetDurations": scene_asset_durations,
            "glossaryEntries": glossary_entries,
        }

        video_path_0 = os.path.join(self.episode_dir, "scene_00.mp4")
        if os.path.exists(video_path_0):
            props["scene0VideoPath"] = os.path.abspath(video_path_0)

        import json as _json
        props_file = remotion_dir / ".render-props-podcast.json"
        props_file.write_text(_json.dumps(props, ensure_ascii=False), encoding="utf-8")
        props_file_path = str(props_file.resolve())

        print(f"Rendering {total} scenes via Remotion ({total_duration:.1f}s total)...")
        subprocess.run(
            ["node", "scripts/render.mjs", props_file_path],
            cwd=str(remotion_dir),
            check=True,
            shell=True,
            timeout=1800,
        )

        assert os.path.exists(raw_final_path), f"final_unnormalized.mp4 not found at {raw_final_path}"
        assert os.path.getsize(raw_final_path) > 1_000_000, (
            f"final_unnormalized.mp4 is suspiciously small ({os.path.getsize(raw_final_path)} bytes)"
        )
        self._normalize_rendered_audio(raw_final_path, final_path)
        if os.path.exists(raw_final_path):
            os.remove(raw_final_path)

        assert os.path.exists(final_path), f"final.mp4 not found at {final_path}"
        assert os.path.getsize(final_path) > 1_000_000, (
            f"final.mp4 is suspiciously small ({os.path.getsize(final_path)} bytes)"
        )
        print(f"Final video: {final_path} (audio normalized, glossary entries={len(glossary_entries)})")

    # ------------------------------------------------------------------
    # Script generation โ€” identical to Podcast.py
    # ------------------------------------------------------------------

    def generate_script(self, topic: str) -> list:
        run_id = f"podcast_v2_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        trace_token = set_trace_run_id(run_id)
        append_trace(
            "podcast_v2_generate_script_start",
            run_id=run_id,
            topic=topic,
            language=self.language,
            creative_direction=self.creative_direction,
        )
        try:
            narrator = get_podcast_narrator()
            script_model = get_podcast_script_model()
            if not str(script_model).lower().startswith(("claude", "anthropic/")):
                raise ValueError(
                    f"script_model must be Claude/Anthropic only for PodcastV2. Current value: {script_model}"
                )

            sentence_length = max(1, get_script_sentence_length())
            system_prompt = _safe_format(
                get_podcast_script_system_prompt(),
                narrator_name=narrator["name"],
                narrator_persona=narrator["persona"],
                language=self.language,
                topic=topic,
                creative_direction=self.creative_direction,
            )
            direction_block = _build_direction_block(self.creative_direction)
            topic_guardrail_block = _build_topic_guardrail_block(
                topic=topic, creative_direction=self.creative_direction, language=self.language,
            )
            topic_interpretation_block = _build_topic_interpretation_block(
                topic=topic, creative_direction=self.creative_direction,
            )
            slug = _slugify_topic(topic)
            date_str = datetime.now().strftime("%Y%m%d")
            episode_id = f"podcast_v2_{slug}_{date_str}"
            episode_dir = os.path.join(ROOT_DIR, ".mp", episode_id)
            os.makedirs(episode_dir, exist_ok=True)
            self.episode_dir = episode_dir

            topic_brief = self._compile_topic_brief(topic, script_model)
            topic_brief_json = json.dumps(topic_brief, ensure_ascii=False, indent=2)
            comprehension_contract = _build_comprehension_contract_block(topic_brief)
            with open(os.path.join(episode_dir, "topic_brief.json"), "w", encoding="utf-8") as f:
                json.dump(topic_brief, f, ensure_ascii=False, indent=2)

            beat_sheet, beat_qc_report = self._prepare_beat_sheet(topic, topic_brief, script_model)
            beat_scenes = beat_sheet.get("scenes", [])

            def _beat_slice(start: int, end: int) -> str:
                return json.dumps(beat_scenes[start:end], ensure_ascii=False, indent=2)

            def _extract_json_candidate(text: str) -> str:
                stripped = str(text or "").strip()
                stripped = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", stripped, flags=re.MULTILINE).strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    return stripped
                start = stripped.find("{")
                end = stripped.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return stripped[start:end + 1]
                return stripped

            def _call_llm(prompt, expected, stage_name: str):
                current_prompt = prompt
                last_exc = None
                for attempt in range(1, 4):
                    raw = generate_text_structured(
                        prompt=current_prompt,
                        system_prompt=system_prompt,
                        schema=SCENE_SCHEMA,
                        model_name=script_model,
                    )
                    append_trace(
                        "podcast_v2_llm_raw",
                        run_id=run_id,
                        stage=stage_name,
                        attempt=attempt,
                        expected_scenes=expected,
                        raw_text=raw,
                    )
                    candidate = _extract_json_candidate(raw)
                    try:
                        result = json.loads(candidate)["scenes"]
                        if len(result) != expected:
                            raise ValueError(f"Expected {expected} scenes, got {len(result)}")
                        return result
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        last_exc = exc
                        append_trace(
                            "podcast_v2_llm_parse_error",
                            run_id=run_id,
                            stage=stage_name,
                            attempt=attempt,
                            error=str(exc),
                            candidate_json=candidate,
                        )
                        current_prompt = (
                            "Your previous response was invalid. Fix it now.\n"
                            f"Return EXACTLY {expected} scenes.\n"
                            "Return ONLY one valid JSON object matching schema. No markdown.\n\n"
                            f"Original task:\n{prompt}\n\n"
                            f"Previous invalid response:\n{raw}"
                        )
                raise ValueError(f"LLM returned invalid JSON after 3 attempts: {last_exc}") from last_exc

            style_constraint = (
                f"The image_prompt will be prefixed with this style: '{self.style_prompt[:80]}'. "
                "Do NOT add keywords that contradict this style."
            )
            common_scene_rules = (
                f"Each scene needs a 'scene_title' (a short 1-4 word summarizing title in the same language as the podcast), "
                f"a 'narration' (about {sentence_length} sentences of engaging spoken text), "
                "and an 'image_prompt' (vivid visual description for an illustration, MUST be in English only).\n"
                f"{style_constraint}\n"
                f"{comprehension_contract}"
                "Narration must sound like guided explanation, not an essay being read aloud.\n"
                "Use listener checkpoint sentences such as 'At this point, remember only this...' after dense ideas.\n"
                "Do not introduce a new technical label unless the surrounding sentence explains it in plain language.\n"
                "Do not teach teaser-only concepts; mention them only as a next-door mystery or future frontier.\n"
                "Do NOT invent superhero-like characters, comic-book heroes, or recurring protagonists unless explicitly asked.\n"
            )

            prompt_1 = (
                f"Create a podcast script about: {topic}\n\n"
                f"{direction_block}{topic_guardrail_block}\n{topic_interpretation_block}\n"
                f"Locked topic brief:\n{topic_brief_json}\n\n"
                "Generate EXACTLY 7 scenes:\n"
                "  Scene 1: START IN MEDIA RES - begin with a specific real event, name, date, or moment of danger or wonder.\n"
                "  Scenes 2-7: Act 1 - establish background, context, and key facts.\n\n"
                f"Act 1 focus: {topic_brief['act_1_focus']}\n"
                f"Follow these locked scene beats exactly:\n{_beat_slice(0, 7)}\n\n"
                f"{common_scene_rules}"
                "Return EXACTLY 7 scenes, no more, no fewer."
            )
            append_trace("podcast_v2_stage_start", run_id=run_id, stage="act1")
            scenes_1 = _call_llm(prompt_1, 7, "act1")

            narrations_1 = "\n\n".join(s["narration"] for s in scenes_1)
            summary_1 = generate_text(
                f"Summarize the following podcast narration in 3-5 sentences.\nTopic: {topic}\n\n"
                f"{topic_interpretation_block}\nLocked brief:\n{topic_brief_json}\n\n{narrations_1}",
                model_name=script_model,
            )
            visual_summary_1 = generate_text(
                "Summarize key visual elements (characters, locations, palette, mood) in 2-3 sentences.\n\n"
                + "\n---\n".join(s["image_prompt"] for s in scenes_1),
                model_name=script_model,
            )

            prompt_2 = (
                f"Story so far:\n{summary_1}\n\nVisual style:\n{visual_summary_1}\n\n"
                f"Continue about: {topic}\n\n"
                f"{direction_block}{topic_guardrail_block}\n{topic_interpretation_block}\n"
                f"Locked topic brief:\n{topic_brief_json}\n\n"
                "Generate EXACTLY 6 scenes for Act 2 - deepen, complicate, build tension.\n"
                f"Act 2 focus: {topic_brief['act_2_focus']}\n"
                f"Follow these locked scene beats exactly:\n{_beat_slice(7, 13)}\n\n"
                f"{common_scene_rules}"
                "Return EXACTLY 6 scenes, no more, no fewer."
            )
            append_trace("podcast_v2_stage_start", run_id=run_id, stage="act2")
            scenes_2 = _call_llm(prompt_2, 6, "act2")

            narrations_12 = "\n\n".join(s["narration"] for s in (scenes_1 + scenes_2))
            summary_2 = generate_text(
                f"Summarize in 3-5 sentences.\nTopic: {topic}\n\n"
                f"{topic_interpretation_block}\nLocked brief:\n{topic_brief_json}\n\n{narrations_12}",
                model_name=script_model,
            )
            visual_summary_2 = generate_text(
                "Summarize key visual elements in 2-3 sentences.\n\n"
                + "\n---\n".join(s["image_prompt"] for s in (scenes_1 + scenes_2)),
                model_name=script_model,
            )

            prompt_3 = (
                f"Story so far:\n{summary_2}\n\nVisual style:\n{visual_summary_2}\n\n"
                f"Conclude about: {topic}\n\n"
                f"{direction_block}{topic_guardrail_block}\n{topic_interpretation_block}\n"
                f"Locked topic brief:\n{topic_brief_json}\n\n"
                "Generate EXACTLY 7 scenes:\n"
                "  Scenes 1-6: Act 3 - resolve the arc, deliver the payoff.\n"
                "  Scene 7: Outro - philosophical reflection, no YouTube CTAs.\n\n"
                f"Act 3 focus: {topic_brief['act_3_focus']}\nOutro focus: {topic_brief['outro_focus']}\n"
                f"Follow these locked scene beats exactly:\n{_beat_slice(13, 20)}\n\n"
                f"{common_scene_rules}"
                "Return EXACTLY 7 scenes, no more, no fewer."
            )
            append_trace("podcast_v2_stage_start", run_id=run_id, stage="act3_outro")
            scenes_3 = _call_llm(prompt_3, 7, "act3_outro")

            all_scenes = scenes_1 + scenes_2 + scenes_3
            assert len(all_scenes) == 20, f"Expected 20 scenes total, got {len(all_scenes)}"

            style_prompt = self.style_prompt
            for scene in all_scenes:
                if not scene.get("scene_title"):
                    scene["scene_title"] = _generate_scene_title(scene["narration"], model_name=script_model)
                scene["image_prompt"] = f"{style_prompt} {scene['image_prompt']}"

            all_scenes, qc_report = self._prepare_script_scenes(
                all_scenes,
                beat_sheet=beat_sheet,
                topic_brief=topic_brief,
                script_model=script_model,
            )
            script_path = os.path.join(episode_dir, "script.json")
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(all_scenes, f, ensure_ascii=False, indent=2)

            cost_summary = summarize_run_cost(run_id)
            append_trace(
                "podcast_v2_generate_script_done",
                run_id=run_id,
                script_path=script_path,
                scene_count=len(all_scenes),
                model=script_model,
                estimated_cost=cost_summary,
                beat_qc={
                    "status": beat_qc_report.get("status"),
                    "score": beat_qc_report.get("overall_score"),
                    "issues": len(beat_qc_report.get("issues") or []),
                },
                script_qc={
                    "status": qc_report.get("status"),
                    "score": qc_report.get("overall_score"),
                    "issues": len(qc_report.get("issues") or []),
                },
            )
            print(
                "[Cost Estimate] "
                f"run_id={run_id} model={cost_summary.get('model') or script_model} "
                f"calls={cost_summary.get('calls', 0)} "
                f"estimated_usd=${cost_summary.get('cost_usd', 0.0):.6f}"
            )
            return all_scenes
        finally:
            reset_trace_run_id(trace_token)
    def generate_script_from_text(self, text: str) -> list:
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")

        schema = {
            "type": "object",
            "properties": {"segments": {"type": "array", "items": {"type": "string"}}},
            "required": ["segments"],
        }
        system_prompt = (
            "You are a script editor. Split the provided narration text into segments for a video podcast. "
            "Rules:\n"
            "- Divide the text into EXACTLY 20 segments. No more, no fewer.\n"
            "- CRITICAL: DO NOT automatically translate the text to English. Keep the exact original language.\n"
            "- Do NOT change, rephrase, or omit any content โ€” copy the exact words verbatim.\n"
            "- Each segment should be a natural, coherent chunk.\n"
            "- Return ONLY valid JSON matching the schema."
        )
        split_prompt = (
            f"Split this narration into EXACTLY 20 segments. "
            f"Do not translate. Do not change any wording.\n\nNARRATION:\n{text.strip()}"
        )
        script_model = get_podcast_script_model()
        result_json = generate_text_structured(split_prompt, system_prompt, schema, model_name=script_model)
        try:
            segments = json.loads(result_json).get("segments", [])
            segments = [s.strip() for s in segments if s.strip()]
        except (json.JSONDecodeError, AttributeError):
            segments = []

        if len(segments) != 20:
            words = [w.strip() for w in text.split() if w.strip()]
            chunk_size = math.ceil(max(1, len(words) / 20))
            segments = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)][:20]
            while len(segments) < 20:
                segments.append("...")

        scenes = []
        for narration in segments:
            image_prompt = _generate_image_prompt(narration, model_name=script_model)
            if self.style_prompt:
                image_prompt = f"{self.style_prompt} {image_prompt}"
            scene_title = _generate_scene_title(narration, model_name=script_model)
            scenes.append({"scene_title": scene_title, "narration": narration, "image_prompt": image_prompt})

        script_path = os.path.join(self.episode_dir, "script.json")
        os.makedirs(self.episode_dir, exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        self._write_script_quality_report(scenes, source="manual_script")
        return scenes

    # ------------------------------------------------------------------
    # Metadata, thumbnail, upload โ€” identical to Podcast.py
    # ------------------------------------------------------------------

    def generate_metadata(self) -> dict:
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")
        script_path = os.path.join(self.episode_dir, "script.json")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"script.json not found at {script_path}")
        with open(script_path, "r", encoding="utf-8") as f:
            scenes = json.load(f)
        context_scenes = scenes[:2] if len(scenes) >= 2 else scenes
        context_excerpt = " ".join(s["narration"] for s in context_scenes)
        prompt = _safe_format(
            get_podcast_metadata_system_prompt(),
            topic=self.topic,
            language=self.language,
            opening_narration=context_excerpt,
            creative_direction=self.creative_direction,
            creative_direction_block=(
                f"Creative direction:\n{self.creative_direction}\n\n"
                if self.creative_direction else ""
            ),
        )
        raw = generate_text(prompt, model_name=get_podcast_script_model())
        metadata = None
        try:
            metadata = json.loads(raw)
        except json.JSONDecodeError:
            stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            try:
                metadata = json.loads(stripped)
            except json.JSONDecodeError:
                pass
        if metadata is None:
            default_title_prefix = "เธเธญเธ”เนเธเธชเธ•เน" if self.language == "Thai" else "Podcast"
            default_description = (
                f"เธ•เธญเธเธเธญเธ”เนเธเธชเธ•เนเธ—เธตเนเธเธฐเธเธฒเนเธเธชเธณเธฃเธงเธเน€เธฃเธทเนเธญเธ {self.topic} เนเธเธเธฅเธถเธเธเธถเนเธ"
                if self.language == "Thai"
                else f"A deep dive podcast episode about {self.topic}."
            )
            metadata = {
                "title": f"{default_title_prefix}: {self.topic[:80]}",
                "description": default_description,
                "tags": [self.topic.lower(), "podcast", "deep dive", "storytelling"],
            }
        metadata["title"] = str(metadata.get("title", f"Podcast: {self.topic[:80]}"))[:100]
        if not isinstance(metadata.get("tags"), list):
            metadata["tags"] = [self.topic.lower(), "podcast"]

        base_description = str(metadata.get("description", "")).strip()
        chapter_block = self._build_chapter_timestamps(scenes)
        hashtags_block = ""
        if base_description:
            description_lines = base_description.rstrip().splitlines()
            trailing_hashtags = []
            while description_lines and description_lines[-1].lstrip().startswith("#"):
                trailing_hashtags.insert(0, description_lines.pop().rstrip())
            base_description = "\n".join(description_lines).rstrip()
            hashtags_block = "\n".join(trailing_hashtags).strip()

        final_description_parts = []
        if base_description:
            final_description_parts.append(base_description)
        if chapter_block:
            final_description_parts.append(chapter_block)
        if hashtags_block:
            final_description_parts.append(hashtags_block)

        metadata["description"] = "\n\n".join(final_description_parts).strip()[:5000]
        self.metadata = metadata
        metadata_path = os.path.join(self.episode_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                merged = {**existing, **metadata}
            except (json.JSONDecodeError, IOError):
                merged = metadata
        else:
            merged = metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"Metadata title: {metadata['title']}")
        return metadata

    def generate_thumbnail(self) -> str | None:
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")
        prompt_path = os.path.join(self.episode_dir, "thumbnail_prompt.txt")
        if os.path.exists(prompt_path):
            print("Skipping thumbnail prompt build (already exists).")
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        prompt = _safe_format(
            get_podcast_thumbnail_system_prompt(),
            topic=self.topic,
            creative_direction_block=(
                f"Use this visual style and creative direction:\n{self.creative_direction}\n{self.style_prompt}\n\n"
                if (self.creative_direction or self.style_prompt) else ""
            ),
        )
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Thumbnail prompt saved: {prompt_path}")
        return prompt

    def _build_youtube_client(self):
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(self.TOKEN_PATH, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            else:
                raise RuntimeError("token.json not found or invalid. Run: python src/youtube_auth.py")
        return build("youtube", "v3", credentials=creds)

    def upload(self, privacy_status: str = "public", publish_at: str | None = None) -> str | None:
        if not self.episode_dir:
            raise ValueError("episode_dir is not set.")
        final_path = os.path.join(self.episode_dir, "final.mp4")
        if not os.path.exists(final_path):
            raise FileNotFoundError(f"final.mp4 not found at {final_path}. Run render() first.")
        if not self.metadata:
            meta_path = os.path.join(self.episode_dir, "metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            else:
                raise FileNotFoundError(f"metadata.json not found. Run generate_metadata() first.")
        yt = self._build_youtube_client()
        effective_privacy = "private" if publish_at else privacy_status
        status_block: dict = {"privacyStatus": effective_privacy, "selfDeclaredMadeForKids": False}
        if publish_at:
            status_block["publishAt"] = publish_at
        body = {
            "snippet": {
                "title": self.metadata["title"],
                "description": self.metadata["description"],
                "tags": self.metadata.get("tags", []),
                "categoryId": "27",
            },
            "status": status_block,
        }
        print(f"Uploading to YouTube: {self.metadata['title']}")
        import socket as _socket
        _socket.setdefaulttimeout(300)
        media = MediaFileUpload(final_path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
        request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Upload progress: {int(status.progress() * 100)}%")
        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Upload complete: {video_url}")
        thumbnail_path = os.path.join(self.episode_dir, "thumbnail.png")
        if os.path.exists(thumbnail_path):
            try:
                thumb_media = MediaFileUpload(thumbnail_path, mimetype="image/png")
                yt.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                print(f"Thumbnail set for video {video_id}")
            except Exception as e:
                print(f"Warning: Thumbnail upload failed: {e}")
        self.metadata["video_id"] = video_id
        self.metadata["video_url"] = video_url
        self.metadata["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_path = os.path.join(self.episode_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        return video_url

    def run(self) -> None:
        self.generate_script(self.topic)
        self.generate_assets()
        self.generate_metadata()
        self.generate_thumbnail()
        self.render()
        self.upload()
