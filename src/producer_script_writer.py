"""Script drafting helpers for PodcastV2 Producer Mode.

This stage writes render-compatible ``script.json`` plus planning-time script
QC, fact-check mapping, and a pronunciation guide. It is designed to run after
research and visual asset planning, before audio or media generation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from producer_contract import THAI_MIN, THAI_MAX, claim_report, episode_spec, narrative_review, thai_count


# Compatibility names only; production gates use episode_spec and Thai Unicode counts.
SCRIPT_MIN_CHARS_NO_SPACE = THAI_MIN
SCRIPT_TARGET_MIN_CHARS_NO_SPACE = THAI_MIN
SCRIPT_TARGET_MAX_CHARS_NO_SPACE = THAI_MAX
SCRIPT_MAX_CHARS_NO_SPACE = THAI_MAX
SCRIPT_SOFT_MAX_CHARS_NO_SPACE = THAI_MAX

ASCII_TERM_STOPWORDS = {
    "and",
    "api",
    "asset",
    "assets",
    "broll",
    "caption",
    "checkpoint",
    "codex",
    "documentary",
    "english",
    "fallback",
    "image",
    "json",
    "media",
    "mode",
    "nasa",
    "official",
    "producer",
    "script",
    "section",
    "source",
    "thai",
    "title",
    "video",
    "visual",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _compact(value: Any, limit: int = 600) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _chars_no_space(text: Any) -> int:
    return len(re.sub(r"\s+", "", str(text or "")))


def _thai_char_count(text: Any) -> int:
    return sum(1 for ch in str(text or "") if "\u0e00" <= ch <= "\u0e7f")


def _language_ratio(text: Any) -> float:
    compact = re.sub(r"\s+", "", str(text or ""))
    if not compact:
        return 0.0
    return _thai_char_count(compact) / len(compact)


def _domain(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _source_lookup(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    research = plan.get("research") if isinstance(plan.get("research"), dict) else {}
    sources = research.get("sources") if isinstance(research.get("sources"), list) else []
    return {str(item.get("id")): item for item in sources if isinstance(item, dict) and item.get("id")}


def _section_sources(section: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source_id in section.get("source_ids") or []:
        source = lookup.get(str(source_id))
        if source:
            result.append(source)
    return result


def _asset_plan_lookup(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    visual_asset_plan = (
        plan.get("visual_asset_plan") if isinstance(plan.get("visual_asset_plan"), dict) else {}
    )
    preview = (
        visual_asset_plan.get("beat_plan_preview")
        if isinstance(visual_asset_plan.get("beat_plan_preview"), list)
        else []
    )
    return {
        str(item.get("asset_plan_id")): item
        for item in preview
        if isinstance(item, dict) and item.get("asset_plan_id")
    }


def _asset_plan_id(section: dict[str, Any], beat: dict[str, Any]) -> str:
    section_index = int(section.get("section_index") or 0)
    beat_index = int(beat.get("beat_index") or 0)
    return f"S{section_index:02d}B{beat_index:02d}"


def _beat_targets(plan: dict[str, Any]) -> list[dict[str, Any]]:
    topic = _clean_text(plan.get("episode", {}).get("topic"), "Untitled topic")
    lookup = _source_lookup(plan)
    asset_lookup = _asset_plan_lookup(plan)
    targets: list[dict[str, Any]] = []
    sections = plan.get("sections") if isinstance(plan.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_sources = _section_sources(section, lookup)
        beats = section.get("beats") if isinstance(section.get("beats"), list) else []
        section_beat_count = max(1, len(beats))
        for beat_offset, beat in enumerate(beats, start=1):
            if not isinstance(beat, dict):
                continue
            asset_id = _asset_plan_id(section, beat)
            asset = asset_lookup.get(asset_id, {})
            targets.append(
                {
                    "asset_plan_id": asset_id,
                    "topic": topic,
                    "section_index": section.get("section_index"),
                    "section_title": section.get("title", ""),
                    "visual_beat": len(targets) + 1,
                    "visual_beat_in_section": beat_offset,
                    "section_beat_count": section_beat_count,
                    "scene_title_hint": section.get("title", ""),
                    "narrative_goal": section.get("narrative_goal", ""),
                    "role": beat.get("role", ""),
                    "beat_type": beat.get("beat_type", ""),
                    "intent": beat.get("intent", ""),
                    "duration_seconds": beat.get("duration_seconds"),
                    "source_ids": [source.get("id") for source in section_sources if source.get("id")],
                    "source_summaries": [
                        {
                            "id": source.get("id"),
                            "title": source.get("title"),
                            "publisher": source.get("publisher"),
                            "url": source.get("url"),
                            "summary": source.get("summary") or source.get("snippet"),
                        }
                        for source in section_sources
                    ],
                    "asset_provider": asset.get("selected_provider"),
                    "asset_title": asset.get("selected_title"),
                    "asset_source_url": asset.get("selected_source_url"),
                }
            )
    return targets


def _script_length_qc(text: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    return narrative_review(text, plan or {})


def _script_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "asset_plan_id": {"type": "string"},
                        "scene_title": {"type": "string"},
                        "narration": {"type": "string"},
                        "image_prompt": {"type": "string"},
                        "key_claims": {"type": "array", "items": {"type": "string"}},
                        "pronunciation_terms": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["asset_plan_id", "scene_title", "narration", "image_prompt"],
                },
            },
            "continuity_summary": {"type": "string"},
        },
        "required": ["scenes", "continuity_summary"],
    }


def _section_prompt(
    plan: dict[str, Any],
    section: dict[str, Any],
    targets: list[dict[str, Any]],
    previous_summary: str,
    target_chars: int,
    retry_note: str = "",
) -> str:
    topic_profile = plan.get("topic_profile") if isinstance(plan.get("topic_profile"), dict) else {}
    payload = {
        "topic": plan.get("episode", {}).get("topic"),
        "selected_angle": topic_profile.get("selected_angle"),
        "viewer_promise": topic_profile.get("viewer_promise"),
        "central_question": topic_profile.get("central_question"),
        "anti_clickbait_boundary": topic_profile.get("anti_clickbait_boundary"),
        "section": {
            "section_index": section.get("section_index"),
            "title": section.get("title"),
            "narrative_goal": section.get("narrative_goal"),
            "source_ids": section.get("source_ids"),
        },
        "previous_summary": previous_summary,
        "target_thai_unicode_chars_for_section": target_chars,
        "editorial_core": plan.get("editorial_core", {}),
        "beat_targets": targets,
    }
    return (
        "Draft one section of a Thai documentary YouTube narration.\n"
        "Return JSON only. Write all narration and scene_title values in Thai script.\n"
        "Hard requirements:\n"
        f"- Aim for {target_chars} Thai Unicode characters (U+0E00-U+0E7F); never pad to meet a count.\n"
        f"- There are {len(targets)} beat targets, so each scene should be a full spoken paragraph, not a short summary.\n"
        "- Do not write English narration. Use English only for necessary acronyms or parenthesized technical terms.\n"
        "- Translate technical terms into Thai first, for example Lunar Laser Ranging = การวัดระยะดวงจันทร์ด้วยเลเซอร์.\n"
        "- Keep claims tied to supplied source IDs; do not invent unsourced numbers or future certainty.\n"
        "Keep it spoken, calm, factual, and continuous.\n"
        "Advance one new idea per section; earn the opening promise and ending payoff. "
        "Remove repeated explanations. Source summaries support drafting only, not final verification.\n"
        "Use only the provided source summaries for factual claims. If evidence is thin, use qualified wording.\n"
        "Do not include section labels inside narration. Do not add subtitles. Do not overclaim.\n"
        "Create exactly one scene for each beat target, preserving asset_plan_id.\n"
        "Each image_prompt must be in English, concrete, no embedded text, no watermark, no fake documents, "
        "and must match the narration beat.\n"
        "Scene titles should be Thai, short, 1-5 words.\n"
        "Include key_claims for fact checking and pronunciation_terms for hard terms.\n\n"
        f"{retry_note}\n\n"
        f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _parse_json(raw: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip(), flags=re.MULTILINE)
    return json.loads(text)


def _fallback_scene(target: dict[str, Any], *, reason: str) -> dict[str, Any]:
    title = _clean_text(target.get("scene_title_hint"), f"Scene {target.get('visual_beat')}")
    source_bits = "; ".join(
        _compact(source.get("title"), 120)
        for source in target.get("source_summaries", [])[:2]
        if isinstance(source, dict)
    )
    narration = (
        f"ในจังหวะนี้ เรากลับมาที่คำถามหลักของเรื่อง {target.get('topic')} "
        f"ประเด็นที่ต้องพาผู้ชมเข้าใจคือ {target.get('intent') or target.get('narrative_goal')} "
        "ให้เล่าอย่างระมัดระวังว่าเรื่องนี้ไม่ใช่สัญญาณหายนะระยะใกล้ แต่เป็นกระบวนการช้ามากในระดับดาราศาสตร์ "
        "ภาพควรช่วยให้ผู้ชมเห็นขนาด ระยะทาง หรือแรงที่มองไม่เห็น โดยไม่ทำให้เข้าใจผิดว่าเป็นเหตุการณ์ทันที "
        f"ฐานข้อมูลที่ใช้ตรวจทานคือ {source_bits or 'แหล่งข้อมูลใน checkpoint'} "
        "ก่อนผลิตจริงควรให้ LLM หรือผู้เขียนปรับสำนวนอีกครั้งเพื่อให้ฉากนี้ลื่นกับฉากข้างเคียง."
    )
    return {
        "scene_title": _compact(title, 80),
        "narration": narration,
        "image_prompt": (
            f"Documentary visual for {target.get('topic')}: "
            f"{target.get('intent') or target.get('narrative_goal')}. "
            "No text, no logos, no fake documents, grounded factual tone."
        ),
        "section_index": target.get("section_index"),
        "section_title": target.get("section_title"),
        "visual_beat": target.get("visual_beat"),
        "visual_beat_in_section": target.get("visual_beat_in_section"),
        "section_beat_count": target.get("section_beat_count"),
        "producer_asset_plan_id": target.get("asset_plan_id"),
        "source_ids": target.get("source_ids", []),
        "source_urls": [
            source.get("url")
            for source in target.get("source_summaries", [])
            if isinstance(source, dict) and source.get("url")
        ],
        "key_claims": [target.get("intent") or target.get("narrative_goal") or reason],
        "pronunciation_terms": [],
        "draft_source": "template_fallback",
        "fallback_reason": reason,
    }


def _normalize_scene(scene: dict[str, Any], target: dict[str, Any], source: str) -> dict[str, Any]:
    narration = _clean_text(scene.get("narration"))
    image_prompt = _clean_text(scene.get("image_prompt"))
    if not image_prompt:
        image_prompt = (
            f"Documentary visual for {target.get('topic')}: "
            f"{target.get('intent') or target.get('narrative_goal')}. No text, no logos."
        )
    normalized = {
        "scene_title": _compact(scene.get("scene_title") or target.get("scene_title_hint"), 80),
        "narration": narration,
        "image_prompt": image_prompt,
        "section_index": target.get("section_index"),
        "section_title": target.get("section_title"),
        "visual_beat": target.get("visual_beat"),
        "visual_beat_in_section": target.get("visual_beat_in_section"),
        "section_beat_count": target.get("section_beat_count"),
        "producer_asset_plan_id": target.get("asset_plan_id"),
        "source_ids": target.get("source_ids", []),
        "source_urls": [
            source_item.get("url")
            for source_item in target.get("source_summaries", [])
            if isinstance(source_item, dict) and source_item.get("url")
        ],
        "key_claims": [
            _clean_text(claim)
            for claim in (scene.get("key_claims") or [])
            if _clean_text(claim)
        ],
        "pronunciation_terms": [
            _clean_text(term)
            for term in (scene.get("pronunciation_terms") or [])
            if _clean_text(term)
        ],
        "draft_source": source,
    }
    normalized["chars_no_space"] = _chars_no_space(narration)
    return normalized


def _draft_with_llm(plan: dict[str, Any], targets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    from llm_provider import generate_text_structured

    sections = plan.get("sections") if isinstance(plan.get("sections"), list) else []
    targets_by_section: dict[int, list[dict[str, Any]]] = {}
    for target in targets:
        section_index = int(target.get("section_index") or 0)
        targets_by_section.setdefault(section_index, []).append(target)

    section_count = max(1, len([section for section in sections if isinstance(section, dict)]))
    bounds = episode_spec(plan)["narrative"]
    section_target_chars = max(1, int((bounds["minimum"] + bounds["maximum"]) / 2 / section_count))
    scenes: list[dict[str, Any]] = []
    warnings: list[str] = []
    previous_summary = ""

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_index = int(section.get("section_index") or 0)
        section_targets = targets_by_section.get(section_index, [])
        if not section_targets:
            continue
        retry_note = ""
        for attempt in range(2):
            try:
                raw = generate_text_structured(
                    _section_prompt(
                        plan,
                        section,
                        section_targets,
                        previous_summary,
                        section_target_chars,
                        retry_note=retry_note,
                    ),
                    system_prompt=(
                        "You are a senior Thai documentary scriptwriter and fact checker. "
                        "Return only valid JSON. Thai narration is mandatory. "
                        "Keep claims tied to supplied sources."
                    ),
                    schema=_script_schema(),
                )
                parsed = _parse_json(raw)
                returned = parsed.get("scenes") if isinstance(parsed.get("scenes"), list) else []
                by_id = {
                    str(item.get("asset_plan_id")): item
                    for item in returned
                    if isinstance(item, dict) and item.get("asset_plan_id")
                }
                section_scenes: list[dict[str, Any]] = []
                for target_index, target in enumerate(section_targets):
                    item = by_id.get(str(target.get("asset_plan_id")))
                    if not item and target_index < len(returned) and isinstance(returned[target_index], dict):
                        item = returned[target_index]
                    if not item:
                        section_scenes.append(_fallback_scene(target, reason="LLM did not return this beat."))
                        warnings.append(f"{target.get('asset_plan_id')}: LLM omitted beat; used Thai fallback scene.")
                        continue
                    section_scenes.append(_normalize_scene(item, target, "llm_section_draft"))

                section_text = "\n".join(str(scene.get("narration") or "") for scene in section_scenes)
                section_chars = thai_count(section_text)
                section_thai_ratio = _language_ratio(section_text)
                if (
                    attempt == 0
                    and (section_thai_ratio < 0.75 or section_chars < int(section_target_chars * 0.7))
                ):
                    retry_note = (
                        "RETRY BECAUSE THE PRIOR DRAFT FAILED QC: rewrite this section in Thai only, "
                        f"with about {section_target_chars} Thai Unicode characters, adding only supported substance. "
                        "No English narration paragraphs."
                    )
                    continue

                if section_chars < int(section_target_chars * 0.7):
                    warnings.append(
                        f"section {section_index}: section draft is short "
                        f"({section_chars} < {int(section_target_chars * 0.7)} chars without whitespace)."
                    )
                if section_thai_ratio < 0.75:
                    warnings.append(
                        f"section {section_index}: Thai character ratio is low ({section_thai_ratio:.2f})."
                    )
                if len(section_scenes) < len(section_targets):
                    warnings.append(f"section {section_index}: LLM omitted one or more beats.")
                scenes.extend(section_scenes)
                previous_summary = _compact(parsed.get("continuity_summary"), 900)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 0:
                    retry_note = f"RETRY BECAUSE THE PRIOR JSON DRAFT FAILED: {exc}"
                    continue
                warnings.append(f"section {section_index}: LLM draft failed; used fallback scenes: {exc}")
                for target in section_targets:
                    scenes.append(_fallback_scene(target, reason=f"LLM section draft failed: {exc}"))

    return scenes, warnings


def _draft_without_llm(targets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    return (
        [_fallback_scene(target, reason="LLM disabled for smoke/test run.") for target in targets],
        ["LLM disabled; wrote template fallback scenes that are not production-ready Thai narration."],
    )


def _fact_check_report(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    return claim_report(plan, scenes)


def _extract_terms(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> list[str]:
    text_parts: list[str] = []
    episode = plan.get("episode") if isinstance(plan.get("episode"), dict) else {}
    text_parts.append(str(episode.get("topic") or ""))
    for scene in scenes:
        text_parts.append(str(scene.get("narration") or ""))
        text_parts.extend(str(term) for term in (scene.get("pronunciation_terms") or []))
    for source in _source_lookup(plan).values():
        text_parts.append(str(source.get("title") or ""))
    text = "\n".join(text_parts)
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9.-]{2,}\b|\b[A-Za-z]+(?:-[A-Za-z0-9]+)+\b", text)
    seen: set[str] = set()
    terms: list[str] = []
    for item in candidates:
        key = item.lower().strip(".")
        if key in ASCII_TERM_STOPWORDS or key in seen:
            continue
        seen.add(key)
        terms.append(item.strip("."))
        if len(terms) >= 30:
            break
    return terms


def _pronunciation_guide(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> str:
    topic = _clean_text(plan.get("episode", {}).get("topic"), "Untitled topic")
    terms = _extract_terms(plan, scenes)
    lines = [
        f"# Pronunciation Guide - {topic}",
        "",
        "Use this before Gemini TTS generation. Keep Thai narration neutral, documentary, and clear.",
        "",
        "## Terms To Review",
    ]
    if not terms:
        lines.append("- No hard ASCII terms were detected. Still review names and acronyms manually.")
    else:
        for term in terms:
            lines.append(f"- `{term}`: verify Thai reading before TTS.")
    lines.extend(
        [
            "",
            "## TTS Notes",
            "- Keep a calm documentary tone.",
            "- Avoid playful delivery.",
            "- Slow down slightly around names, acronyms, numbers, and mission terms.",
            "- Re-listen to the first generated sample before rendering the full episode.",
            "",
        ]
    )
    return "\n".join(lines)


def expand_script_package(
    plan: dict[str, Any],
    scenes: list[dict[str, Any]],
    *,
    target_min: int | None = None,
    target_max: int | None = None,
) -> dict[str, Any]:
    # Expansion is an editorial task. Never append topic-specific boilerplate by beat ID.
    from copy import deepcopy
    effective_plan = deepcopy(plan)
    spec = episode_spec(effective_plan)
    if target_min is not None:
        spec["narrative"]["minimum"] = target_min
    if target_max is not None:
        spec["narrative"]["maximum"] = target_max
    effective_plan["episode_spec"] = spec
    episode_spec(effective_plan)
    revised = deepcopy(scenes)
    warnings = ["No automatic padding performed. Revise the script using supported new evidence, then rerun review."]
    facts = _fact_check_report(effective_plan, revised)
    return {
        "created_at": _utc_now(), "scenes": revised,
        "script_qc": _script_qc(effective_plan, revised, warnings, facts),
        "fact_check_report": facts, "pronunciation_guide_md": _pronunciation_guide(effective_plan, revised),
        "episode_spec": spec, "warnings": warnings,
    }


def _script_qc(plan: dict[str, Any], scenes: list[dict[str, Any]], warnings: list[str], fact_report: dict[str, Any]) -> dict[str, Any]:
    text = "\n\n".join(str(scene.get("narration") or "") for scene in scenes)
    length_qc = _script_length_qc(text, plan)
    missing_fields: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes, start=1):
        for field in ("scene_title", "narration", "image_prompt"):
            if not _clean_text(scene.get(field)):
                missing_fields.append({"scene": index, "field": field})
                issues.append(
                    {
                        "severity": "high",
                        "scene": index,
                        "issue": f"Missing {field}.",
                        "suggestion": "Fill this field before asset generation.",
                    }
                )

    language = plan.get("episode", {}).get("language", "th")
    thai_ratio = _language_ratio(text)
    if language == "th" and thai_ratio < 0.75:
        issues.append(
            {
                "severity": "high",
                "scene": 0,
                "issue": f"Thai character ratio is too low for Thai narration ({thai_ratio:.2f}).",
                "suggestion": "Run draft-script with LLM enabled to generate final Thai narration.",
            }
        )
    if length_qc["status"] != "pass":
        issues.append(
            {
                "severity": "high" if length_qc["blocking"] else "medium",
                "scene": 0,
                "issue": "; ".join(length_qc.get("notes") or []),
                "suggestion": "Adjust narration length before production.",
            }
        )
    if fact_report.get("status") != "pass":
        issues.append(
            {
                "severity": "medium",
                "scene": 0,
                "issue": f"{fact_report.get('unverified_count', 0)} claims need source review.",
                "suggestion": "Verify claims against source passages; record current evidence reviews before production.",
            }
        )
    for warning in warnings:
        issues.append(
            {
                "severity": "medium",
                "scene": 0,
                "issue": warning,
                "suggestion": "Review this before production.",
            }
        )

    high_count = sum(1 for issue in issues if str(issue.get("severity")) == "high")
    medium_count = sum(1 for issue in issues if str(issue.get("severity")) == "medium")
    status = "pass"
    if high_count:
        status = "blocked"
    elif medium_count or length_qc["status"] != "pass":
        status = "review"
    score = max(0, 92 - high_count * 25 - medium_count * 8)
    return {
        "overall_score": score,
        "status": status,
        "summary": (
            f"Deterministic Producer Mode script QC checked {len(scenes)} scenes, "
            f"{length_qc['chars_no_space']} chars without whitespace, "
            f"Thai ratio {thai_ratio:.2f}."
        ),
        "strengths": [
            "Script follows Producer Mode section/beat structure.",
            "Scenes preserve source IDs and asset plan IDs for downstream production.",
        ],
        "issues": issues,
        "rewrite_targets": sorted(
            {
                int(issue.get("scene") or 0)
                for issue in issues
                if int(issue.get("scene") or 0) > 0
            }
        ),
        "retention_notes": [],
        "visual_notes": [],
        "comprehension_notes": [],
        "source": "producer_mode_draft",
        "scene_count": len(scenes),
        "chars_no_space": length_qc["chars_no_space"],
        "chars_with_space": length_qc["chars_with_space"],
        "length_status": length_qc["status"],
        "language": language,
        "thai_character_ratio": thai_ratio,
        "missing_fields": missing_fields,
        "warnings": warnings,
    }


def draft_script_package(
    plan: dict[str, Any],
    *,
    use_llm: bool = True,
) -> dict[str, Any]:
    targets = _beat_targets(plan)
    if use_llm:
        try:
            scenes, warnings = _draft_with_llm(plan, targets)
        except Exception as exc:  # noqa: BLE001
            scenes, warnings = _draft_without_llm(targets)
            warnings.append(f"LLM script draft failed before section loop: {exc}")
    else:
        scenes, warnings = _draft_without_llm(targets)

    normalized_scenes = []
    target_by_id = {str(target.get("asset_plan_id")): target for target in targets}
    for index, scene in enumerate(scenes, start=1):
        if scene.get("producer_asset_plan_id"):
            normalized = dict(scene)
        else:
            target = target_by_id.get(str(scene.get("asset_plan_id"))) or targets[min(index - 1, len(targets) - 1)]
            normalized = _normalize_scene(scene, target, str(scene.get("draft_source") or "producer_mode"))
        normalized["visual_beat"] = int(normalized.get("visual_beat") or index)
        normalized["chars_no_space"] = _chars_no_space(normalized.get("narration"))
        normalized_scenes.append(normalized)

    fact_report = _fact_check_report(plan, normalized_scenes)
    script_qc = _script_qc(plan, normalized_scenes, warnings, fact_report)
    guide = _pronunciation_guide(plan, normalized_scenes)
    return {
        "created_at": _utc_now(),
        "scenes": normalized_scenes,
        "script_qc": script_qc,
        "fact_check_report": fact_report,
        "pronunciation_guide_md": guide,
        "warnings": warnings,
    }
