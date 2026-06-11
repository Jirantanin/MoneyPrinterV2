"""Visual asset planning for PodcastV2 Producer Mode.

This stage does not download or generate media. It maps section beats to the
best provider path, records candidate choices, and writes planning-time QC so a
producer can catch misleading visuals before production starts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


VISUAL_ASSET_PLAN_VERSION = 1
QC_CRITERIA = [
    "subject_matches_beat",
    "mood_matches_story",
    "not_misleading_as_broll",
    "not_obviously_repetitive_nearby",
]

TOKEN_STOPWORDS = {
    "about",
    "after",
    "analysis",
    "and",
    "asset",
    "beat",
    "before",
    "between",
    "broll",
    "documentary",
    "evidence",
    "explain",
    "explained",
    "explanation",
    "factual",
    "from",
    "generic",
    "image",
    "official",
    "opener",
    "section",
    "source",
    "story",
    "that",
    "the",
    "this",
    "visual",
    "with",
}

DIAGRAM_MARKERS = {
    "chart",
    "diagram",
    "graph",
    "timeline",
    "map",
    "orbit",
    "scale",
    "comparison",
    "compare",
    "data",
    "label",
    "labeled",
    "cutaway",
}

SPECIFIC_MARKERS = {
    "actual",
    "agency",
    "archive",
    "caption",
    "curiosity",
    "evidence",
    "fermi",
    "goddard",
    "jwst",
    "james webb",
    "jpl",
    "mission",
    "nasa",
    "official",
    "perseverance",
    "probe",
    "rover",
    "satellite",
    "specific",
    "telescope",
    "verified",
}

STOCK_STOPWORDS = TOKEN_STOPWORDS | {
    "angle",
    "camera",
    "clean",
    "clear",
    "context",
    "create",
    "high",
    "hook",
    "impact",
    "motion",
    "real",
    "realistic",
    "support",
    "supporting",
    "tone",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _compact(value: Any, limit: int = 360) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _tokens(value: Any, *, stopwords: set[str] | None = None) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", str(value or "").lower())
    blocked = stopwords or TOKEN_STOPWORDS
    return [word for word in words if word not in blocked]


def _score_text(query: str, text: str) -> int:
    tokens = _tokens(query)
    if not tokens:
        return 1
    haystack = str(text or "").lower()
    score = sum(1 for token in tokens if token in haystack)
    normalized_query = re.sub(r"\s+", " ", str(query or "").lower()).strip()
    if normalized_query and normalized_query in haystack:
        score += 3
    return score


def _domain(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _section_source_lookup(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    research = plan.get("research") if isinstance(plan.get("research"), dict) else {}
    sources = research.get("sources") if isinstance(research.get("sources"), list) else []
    return {str(item.get("id")): item for item in sources if isinstance(item, dict) and item.get("id")}


def _source_urls_for_section(section: dict[str, Any], source_lookup: dict[str, dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for source_id in section.get("source_ids") or []:
        source = source_lookup.get(str(source_id))
        if source and source.get("url"):
            urls.append(str(source.get("url")))
    return urls


def _beat_text(topic: str, section: dict[str, Any], beat: dict[str, Any]) -> str:
    return " ".join(
        _clean_text(value)
        for value in [
            topic,
            section.get("title"),
            section.get("narrative_goal"),
            section.get("visual_direction"),
            beat.get("role"),
            beat.get("beat_type"),
            beat.get("visual_type"),
            beat.get("source_preference"),
            beat.get("intent"),
        ]
        if _clean_text(value)
    )


def _asset_plan_id(section: dict[str, Any], beat: dict[str, Any]) -> str:
    section_index = int(section.get("section_index") or 0)
    beat_index = int(beat.get("beat_index") or 0)
    return f"S{section_index:02d}B{beat_index:02d}"


def _is_opener(beat: dict[str, Any]) -> bool:
    return (
        str(beat.get("role") or "").lower() == "opener"
        or str(beat.get("beat_type") or "").lower() == "section_opener"
        or str(beat.get("source_preference") or "").lower() == "codex_imagegen"
    )


def _is_diagram_beat(beat: dict[str, Any]) -> bool:
    visual_type = str(beat.get("visual_type") or "").lower()
    if "remotion" in visual_type or "diagram" in visual_type:
        return True
    text = " ".join(str(beat.get(key) or "").lower() for key in ("intent", "role", "beat_type"))
    return any(marker in text for marker in DIAGRAM_MARKERS)


def _requires_specific_match(section: dict[str, Any], beat: dict[str, Any], beat_text: str) -> bool:
    role = str(beat.get("role") or "").lower()
    source_preference = str(beat.get("source_preference") or "").lower()
    visual_type = str(beat.get("visual_type") or "").lower()
    if role in {"evidence", "diagram"}:
        return True
    if "official" in source_preference or "verified" in source_preference:
        return True
    if "official" in visual_type or "specific" in visual_type:
        return True
    text = f"{beat_text} {section.get('title', '')}".lower()
    return any(marker in text for marker in SPECIFIC_MARKERS)


def _stock_keyword(text: str, topic: str) -> str:
    tokens = _tokens(text, stopwords=STOCK_STOPWORDS)
    topic_tokens = _tokens(topic, stopwords=STOCK_STOPWORDS)
    ordered: list[str] = []
    for token in topic_tokens + tokens:
        if token not in ordered:
            ordered.append(token)
    if not ordered:
        return "documentary science"
    return " ".join(ordered[:3])[:60]


def _imagegen_prompt(topic: str, section: dict[str, Any], beat: dict[str, Any], variant: int) -> str:
    section_title = _clean_text(section.get("title"), "section")
    intent = _clean_text(beat.get("intent") or section.get("narrative_goal"), topic)
    visual_direction = _clean_text(section.get("visual_direction"), "documentary opener")
    lens = "wide establishing frame" if variant == 1 else "closer cinematic detail frame"
    return (
        f"Thai documentary section opener for {topic}. Section: {section_title}. "
        f"Visual idea: {intent}. Direction: {visual_direction}. {lens}. "
        "No embedded text, no logos, no watermark, factual tone, cinematic but restrained."
    )


def _candidate(
    *,
    provider: str,
    media_type: str,
    title: str,
    reason: str,
    source_url: str = "",
    download_url: str = "",
    preview_url: str = "",
    credit: str = "",
    license_note: str = "",
    prompt: str = "",
    keyword: str = "",
    score: int = 0,
    generated_or_illustrative: bool = False,
    risks: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "media_type": media_type,
        "title": _compact(title, 180),
        "reason": _compact(reason, 420),
        "source_url": source_url,
        "download_url": download_url,
        "preview_url": preview_url,
        "credit": credit,
        "license_note": license_note,
        "prompt": prompt,
        "keyword": keyword,
        "score": score,
        "generated_or_illustrative": generated_or_illustrative,
        "risks": risks or [],
    }


def _official_candidates(
    media_results: list[dict[str, Any]],
    beat_query: str,
    used_source_urls: set[str],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for media in media_results:
        if not isinstance(media, dict):
            continue
        searchable = " ".join(
            str(media.get(key) or "")
            for key in ("title", "description", "keywords", "provider", "id", "source_url")
        )
        score = _score_text(beat_query, searchable) + int(media.get("relevance_score") or 0)
        source_url = str(media.get("source_url") or "")
        if source_url and source_url in used_source_urls:
            score -= 2
        if media.get("download_url"):
            score += 1
        if str(media.get("media_type") or "") == "video":
            score += 1
        if score <= 0:
            continue
        ranked.append((score, media))
    ranked.sort(key=lambda item: item[0], reverse=True)
    candidates: list[dict[str, Any]] = []
    for score, media in ranked[:limit]:
        candidates.append(
            _candidate(
                provider=str(media.get("provider") or "official_media"),
                media_type=str(media.get("media_type") or "image"),
                title=str(media.get("title") or media.get("id") or "official media"),
                reason=str(media.get("selected_reason") or "Official/verified media candidate."),
                source_url=str(media.get("source_url") or ""),
                download_url=str(media.get("download_url") or ""),
                preview_url=str(media.get("preview_url") or ""),
                credit=str(media.get("credit") or ""),
                license_note=str(media.get("license_note") or ""),
                score=score,
                risks=[str(item) for item in (media.get("risks") or []) if str(item).strip()],
            )
        )
    return candidates


def _qc_result(
    selected: dict[str, Any],
    *,
    specific_required: bool,
    generated_or_illustrative: bool,
    reused_nearby: bool,
    has_provenance: bool,
    score: int,
    issues: list[str] | None = None,
) -> dict[str, Any]:
    issues = list(issues or [])
    source_backed_graphic = (
        selected.get("provider") == "remotion_graphic"
        and generated_or_illustrative
        and has_provenance
    )
    misleading_generated = generated_or_illustrative and not source_backed_graphic
    checks = {
        "subject_matches_beat": score >= 2 or generated_or_illustrative,
        "mood_matches_story": True,
        "not_misleading_as_broll": not (specific_required and misleading_generated),
        "not_obviously_repetitive_nearby": not reused_nearby,
    }
    if specific_required and not has_provenance:
        checks["not_misleading_as_broll"] = False
        issues.append("Specific/factual beat lacks direct official provenance.")
    if source_backed_graphic:
        issues.append("Source-backed explanatory graphic; do not present it as real footage.")
    elif generated_or_illustrative:
        issues.append("Generated/illustrative candidate must not be presented as real evidence.")
    if reused_nearby:
        issues.append("Candidate source repeats near a previous beat.")

    passed = sum(1 for value in checks.values() if value)
    if passed >= 3 and checks["not_misleading_as_broll"]:
        status = "pass"
    elif specific_required and not checks["not_misleading_as_broll"]:
        status = "needs_review"
    else:
        status = "warn"
    return {
        "status": status,
        "score": passed,
        "checks": checks,
        "issues": list(dict.fromkeys(issue for issue in issues if issue)),
        "criteria": QC_CRITERIA,
        "selected_provider": selected.get("provider"),
    }


def _select_candidate(
    candidates: list[dict[str, Any]],
    *,
    specific_required: bool,
) -> dict[str, Any]:
    if not candidates:
        return _candidate(
            provider="manual_review_required",
            media_type="none",
            title="No candidate selected",
            reason="No candidate was available for this beat.",
            risks=["Manual visual selection required before production."],
        )
    if specific_required:
        for candidate in candidates:
            if candidate.get("provider") not in {"pexels", "pixabay", "runware_flux1"}:
                return candidate
    return candidates[0]


def _beat_plan(
    *,
    topic: str,
    section: dict[str, Any],
    beat: dict[str, Any],
    source_urls: list[str],
    official_media: list[dict[str, Any]],
    used_source_urls: set[str],
) -> dict[str, Any]:
    plan_id = _asset_plan_id(section, beat)
    text = _beat_text(topic, section, beat)
    specific_required = _requires_specific_match(section, beat, text)
    candidates: list[dict[str, Any]] = []
    fallback_chain: list[str] = []

    if _is_opener(beat):
        specific_required = False
        fallback_chain = ["codex_imagegen_variant_1", "codex_imagegen_variant_2", "retry_once"]
        for variant in (1, 2):
            candidates.append(
                _candidate(
                    provider="codex_imagegen",
                    media_type="image",
                    title=f"{plan_id} opener variant {variant}",
                    reason="Section opener must use Codex imagegen and contain no embedded text.",
                    prompt=_imagegen_prompt(topic, section, beat, variant),
                    score=6 - variant,
                    generated_or_illustrative=True,
                    risks=["Generated opener is stylistic; do not use it as factual evidence."],
                )
            )
        selected = candidates[0]
    elif _is_diagram_beat(beat):
        fallback_chain = ["remotion_graphic", "official_data_snapshot_if_needed"]
        candidates.append(
            _candidate(
                provider="remotion_graphic",
                media_type="graphic",
                title=f"{plan_id} Remotion graphic",
                reason="Diagram/data/scale beat is clearer as a generated Remotion graphic.",
                source_url=source_urls[0] if source_urls else "",
                score=4 if source_urls else 2,
                generated_or_illustrative=True,
                risks=[] if source_urls else ["Diagram has no mapped source URL yet."],
            )
        )
        selected = candidates[0]
    else:
        official = _official_candidates(official_media, text, used_source_urls, limit=3)
        stock_keyword = _stock_keyword(text, topic)
        stock_candidates = [
            _candidate(
                provider="pexels",
                media_type="video",
                title=f"Pexels search: {stock_keyword}",
                reason="Generic B-roll stock-video candidate; use only if it cannot mislead viewers.",
                keyword=stock_keyword,
                score=2,
                risks=[] if not specific_required else ["Stock footage is not enough for a specific factual beat."],
            ),
            _candidate(
                provider="pixabay",
                media_type="video",
                title=f"Pixabay search: {stock_keyword}",
                reason="Fallback generic B-roll stock-video candidate.",
                keyword=stock_keyword,
                score=1,
                risks=[] if not specific_required else ["Stock footage is not enough for a specific factual beat."],
            ),
        ]
        flux_candidate = _candidate(
            provider="runware_flux1",
            media_type="image",
            title=f"FLUX.1 fallback: {stock_keyword}",
            reason="Illustrative fallback only; avoid for evidence beats unless clearly framed.",
            prompt=(
                f"Documentary still supporting this beat: {text}. "
                "No text, no logos, no fake documents, no fake data, grounded physical scene."
            ),
            score=1,
            generated_or_illustrative=True,
            risks=["AI-generated fallback must not be presented as real footage or evidence."],
        )

        if specific_required:
            candidates = official + stock_candidates + [flux_candidate]
            fallback_chain = [
                "official_verified_media",
                "manual_review_if_no_direct_match",
                "stock_or_ai_only_if_illustrative",
            ]
        else:
            strong_official = [candidate for candidate in official if int(candidate.get("score") or 0) >= 4]
            candidates = strong_official + stock_candidates + official + [flux_candidate]
            fallback_chain = ["pexels_stock_video", "pixabay_stock_video", "official_if_direct", "runware_flux1"]
        selected = _select_candidate(candidates, specific_required=specific_required)

    selected_url = str(selected.get("source_url") or selected.get("download_url") or "")
    reused_nearby = bool(selected_url and selected_url in used_source_urls)
    if selected_url:
        used_source_urls.add(selected_url)
    generated = bool(selected.get("generated_or_illustrative"))
    has_provenance = bool(selected.get("source_url") or selected.get("license_note"))
    qc = _qc_result(
        selected,
        specific_required=specific_required,
        generated_or_illustrative=generated,
        reused_nearby=reused_nearby,
        has_provenance=has_provenance,
        score=int(selected.get("score") or 0),
        issues=[str(item) for item in (selected.get("risks") or []) if str(item).strip()],
    )

    return {
        "asset_plan_id": plan_id,
        "section_index": section.get("section_index"),
        "section_title": section.get("title", ""),
        "beat_index": beat.get("beat_index"),
        "role": beat.get("role", ""),
        "beat_type": beat.get("beat_type", ""),
        "visual_type": beat.get("visual_type", ""),
        "intent": beat.get("intent", ""),
        "duration_seconds": beat.get("duration_seconds"),
        "specific_match_required": specific_required,
        "fallback_chain": fallback_chain,
        "selected_provider": selected.get("provider"),
        "selected_media_type": selected.get("media_type"),
        "selected_title": selected.get("title"),
        "selected_reason": selected.get("reason"),
        "selected_source_url": selected.get("source_url"),
        "selected_download_url": selected.get("download_url"),
        "selected_preview_url": selected.get("preview_url"),
        "selected_credit": selected.get("credit"),
        "selected_license_note": selected.get("license_note"),
        "selected_prompt": selected.get("prompt"),
        "selected_keyword": selected.get("keyword"),
        "source_urls": source_urls,
        "qc": qc,
        "candidates": candidates[:6],
    }


def build_visual_asset_plan(plan: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a planning-time asset plan and QC report from a Producer plan."""

    episode = plan.get("episode") if isinstance(plan.get("episode"), dict) else {}
    research = plan.get("research") if isinstance(plan.get("research"), dict) else {}
    topic = _clean_text(episode.get("topic"), "Untitled topic")
    sections = plan.get("sections") if isinstance(plan.get("sections"), list) else []
    official_media = (
        research.get("official_media_results")
        if isinstance(research.get("official_media_results"), list)
        else []
    )
    source_lookup = _section_source_lookup(plan)
    used_source_urls: set[str] = set()
    beat_plans: list[dict[str, Any]] = []

    for section in sections:
        if not isinstance(section, dict):
            continue
        source_urls = _source_urls_for_section(section, source_lookup)
        beats = section.get("beats") if isinstance(section.get("beats"), list) else []
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            beat_plans.append(
                _beat_plan(
                    topic=topic,
                    section=section,
                    beat=beat,
                    source_urls=source_urls,
                    official_media=official_media,
                    used_source_urls=used_source_urls,
                )
            )

    provider_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    warnings: list[str] = []
    for beat_plan in beat_plans:
        provider = str(beat_plan.get("selected_provider") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        qc = beat_plan.get("qc") if isinstance(beat_plan.get("qc"), dict) else {}
        qc_status = str(qc.get("status") or "unknown")
        status_counts[qc_status] = status_counts.get(qc_status, 0) + 1
        if qc_status != "pass":
            warnings.append(
                f"{beat_plan.get('asset_plan_id')}: {qc_status} - "
                + "; ".join(str(item) for item in (qc.get("issues") or [])[:2])
            )

    needs_review = status_counts.get("needs_review", 0)
    status = "needs_review" if needs_review else "ready"
    if not beat_plans:
        status = "blocked"
        warnings.append("No visual beats were available for asset planning.")

    now = _utc_now()
    summary = {
        "status": status,
        "beat_count": len(beat_plans),
        "provider_counts": provider_counts,
        "qc_status_counts": status_counts,
        "warnings": warnings[:20],
    }
    visual_asset_plan = {
        "schema_version": VISUAL_ASSET_PLAN_VERSION,
        "stage": "planning",
        "created_at": now,
        "topic": topic,
        "status": status,
        "summary": summary,
        "beat_plans": beat_plans,
    }
    asset_qc = {
        "schema_version": VISUAL_ASSET_PLAN_VERSION,
        "stage": "planning_candidate_qc",
        "created_at": now,
        "topic": topic,
        "status": status,
        "summary": (
            f"Checked {len(beat_plans)} visual beat plans; "
            f"{needs_review} need review before production."
        ),
        "criteria": QC_CRITERIA,
        "provider_counts": provider_counts,
        "status_counts": status_counts,
        "beat_results": [
            {
                "asset_plan_id": beat_plan.get("asset_plan_id"),
                "section_index": beat_plan.get("section_index"),
                "beat_index": beat_plan.get("beat_index"),
                "selected_provider": beat_plan.get("selected_provider"),
                "selected_title": beat_plan.get("selected_title"),
                "selected_source_domain": _domain(str(beat_plan.get("selected_source_url") or "")),
                "specific_match_required": beat_plan.get("specific_match_required"),
                "qc": beat_plan.get("qc"),
            }
            for beat_plan in beat_plans
        ],
        "warnings": warnings[:50],
    }
    return visual_asset_plan, asset_qc
