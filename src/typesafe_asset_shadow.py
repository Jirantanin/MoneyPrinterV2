"""Shadow-only TypeSafe judgments for Producer Mode visual planning.

The module evaluates text metadata and visual strategy. It never approves an
asset, mutates a plan, downloads media, or claims to have inspected pixels.
"""

from __future__ import annotations

from typing import Any


SOURCE_CLASS_CRITERIA = {
    "official_verified_media": (
        "Real media from an official or verified source that directly depicts the named subject."
    ),
    "explanatory_graphic": (
        "A sourced diagram, comparison, map, timeline, scale view, or mechanism graphic."
    ),
    "licensed_stock_video": (
        "Generic licensed real footage used as non-misleading context, action, or atmosphere."
    ),
    "licensed_stock_photo": (
        "A licensed still used as non-misleading context when motion is not important."
    ),
    "generated_reconstruction": (
        "A clearly labeled generated illustration or reconstruction, never observational evidence."
    ),
    "manual_review": "No listed source class is safe without a producer decision.",
}

VISUAL_FUNCTION_CRITERIA = {
    "evidence": "Show direct evidence or the named real subject from a verified source.",
    "location": "Orient the viewer to a place, environment, or spatial context.",
    "mechanism": "Explain how a process works or how parts relate.",
    "scale": "Make a size, distance, duration, or numerical comparison understandable.",
    "action": "Show an observable action, operation, or change over time.",
    "consequence": "Show the result or impact of the narrated event or mechanism.",
    "atmosphere": "Support tone without pretending to be evidence for a specific claim.",
    "manual_review": "The intended visual function is ambiguous or combines incompatible jobs.",
}

MAX_CANDIDATES = 5


def _compact(value: Any, limit: int = 700) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _candidate_state(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "index": index,
        "provider": _compact(candidate.get("provider"), 80),
        "media_type": _compact(candidate.get("media_type"), 40),
        "title": _compact(candidate.get("title"), 240),
        "reason": _compact(candidate.get("reason"), 400),
        "keyword": _compact(candidate.get("keyword"), 180),
        "prompt": _compact(candidate.get("prompt"), 700),
        "has_source_url": bool(candidate.get("source_url")),
        "has_license_note": bool(candidate.get("license_note")),
        "generated_or_illustrative": bool(candidate.get("generated_or_illustrative")),
        "risks": [_compact(item, 240) for item in (candidate.get("risks") or [])[:4]],
    }


def build_shadow_state(topic: str, beat: dict[str, Any]) -> dict[str, Any]:
    """Return the small text-only state Jev is allowed to judge."""

    candidates = [
        _candidate_state(candidate, index)
        for index, candidate in enumerate((beat.get("candidates") or [])[:MAX_CANDIDATES])
        if isinstance(candidate, dict)
    ]
    return {
        "task_boundary": (
            "Judge metadata and visual strategy only. No image or video pixels were inspected. "
            "A producer must still inspect every selected placement."
        ),
        "topic": _compact(topic, 300),
        "beat": {
            "asset_plan_id": _compact(beat.get("asset_plan_id"), 80),
            "section_title": _compact(beat.get("section_title"), 240),
            "role": _compact(beat.get("role"), 80),
            "beat_type": _compact(beat.get("beat_type"), 120),
            "visual_type": _compact(beat.get("visual_type"), 160),
            "intent": _compact(beat.get("intent"), 900),
            "duration_seconds": beat.get("duration_seconds"),
            "specific_match_required_by_code": bool(beat.get("specific_match_required")),
            "source_urls": [_compact(url, 400) for url in (beat.get("source_urls") or [])[:5]],
        },
        "current_strategy": {
            "provider": _compact(beat.get("selected_provider"), 80),
            "media_type": _compact(beat.get("selected_media_type"), 40),
            "title": _compact(beat.get("selected_title"), 240),
            "reason": _compact(beat.get("selected_reason"), 500),
            "keyword": _compact(beat.get("selected_keyword"), 180),
            "prompt": _compact(beat.get("selected_prompt"), 700),
            "has_source_url": bool(beat.get("selected_source_url")),
            "has_license_note": bool(beat.get("selected_license_note")),
        },
        "candidates": candidates,
    }


def build_shadow_questions(candidate_count: int) -> dict[str, Any]:
    """Build narrow independent TypeSafe questions for one visual beat."""

    from typesafe_sdk import Choice, Noul, NoulCriteria

    suitable = NoulCriteria(
        true=(
            "The candidate's described subject, source class, and intended use support the beat "
            "without pretending generic or generated material is direct evidence."
        ),
        false=(
            "The candidate is semantically weak, serves a different visual job, lacks required "
            "specificity, or would create a misleading evidence impression."
        ),
    )
    misleading = NoulCriteria(
        true=(
            "A reasonable viewer could mistake the described asset for direct evidence, real footage "
            "of the named event, or a verified measurement when it is not."
        ),
        false=(
            "The use is direct verified evidence, or it is clearly contextual/illustrative and cannot "
            "reasonably be mistaken for direct evidence."
        ),
    )
    questions: dict[str, Any] = {
        "visual_function": Choice(
            instructions="Which single visual function should this beat primarily perform?",
            criteria=VISUAL_FUNCTION_CRITERIA,
        ),
        "source_class": Choice(
            instructions=(
                "Which source class should be attempted first for this beat while respecting the "
                "truth boundary?"
            ),
            criteria=SOURCE_CLASS_CRITERIA,
        ),
        "specific_subject_required": Noul(
            instructions=(
                "Does this beat require the exact named subject, event, object, location, document, "
                "or measurement rather than a generic visual substitute?"
            ),
        ),
        "generic_stock_safe": Noul(
            instructions=(
                "Could generic licensed stock be used for this beat without implying that it depicts "
                "the specific narrated evidence or event?"
            ),
        ),
        "generated_safe_if_labeled": Noul(
            instructions=(
                "Could a clearly labeled generated illustration or reconstruction support this beat "
                "without replacing evidence the viewer needs to see?"
            ),
        ),
        "current_strategy_suitable": Noul(
            instructions=(
                "Is `current_strategy` suitable for `beat.intent` under `task_boundary`, based only "
                "on the supplied metadata?"
            ),
            criteria=suitable,
        ),
        "current_strategy_misleading": Noul(
            instructions=(
                "Could `current_strategy` mislead viewers about what is direct evidence for this beat?"
            ),
            criteria=misleading,
        ),
    }
    for index in range(candidate_count):
        questions[f"candidate_{index}_suitable"] = Noul(
            instructions=(
                f"Is `candidates[{index}]` suitable for `beat.intent` under `task_boundary`, based "
                "only on the supplied metadata?"
            ),
            criteria=suitable,
        )
        questions[f"candidate_{index}_misleading"] = Noul(
            instructions=(
                f"Could `candidates[{index}]` mislead viewers about what is direct evidence for "
                "this beat?"
            ),
            criteria=misleading,
        )
    return questions


def _answer_value(answer: Any, field: str, default: Any = None) -> Any:
    if answer is None:
        return default
    if isinstance(answer, dict):
        return answer.get(field, default)
    return getattr(answer, field, default)


def review_visual_beat_shadow(
    topic: str,
    beat: dict[str, Any],
    *,
    client: Any,
    min_choice_confidence: float = 0.75,
    risk_threshold: float = 0.50,
) -> dict[str, Any]:
    """Call TypeSafe and return a non-authoritative shadow recommendation."""

    state = build_shadow_state(topic, beat)
    questions = build_shadow_questions(len(state["candidates"]))
    response = client.system_one(state=state, questions=questions)
    answers = response.answers

    visual_answer = answers["visual_function"]
    source_answer = answers["source_class"]
    visual_confidence = float(_answer_value(visual_answer, "confidence", 0.0) or 0.0)
    source_confidence = float(_answer_value(source_answer, "confidence", 0.0) or 0.0)
    misleading_probability = float(
        _answer_value(answers.get("current_strategy_misleading"), "noul", 1.0) or 0.0
    )

    candidate_reviews: list[dict[str, Any]] = []
    for candidate in state["candidates"]:
        index = int(candidate["index"])
        suitable_probability = float(
            _answer_value(answers.get(f"candidate_{index}_suitable"), "noul", 0.0) or 0.0
        )
        candidate_misleading = float(
            _answer_value(answers.get(f"candidate_{index}_misleading"), "noul", 1.0) or 0.0
        )
        candidate_reviews.append(
            {
                "candidate_index": index,
                "provider": candidate.get("provider"),
                "title": candidate.get("title"),
                "suitable_probability": round(suitable_probability, 4),
                "misleading_probability": round(candidate_misleading, 4),
                "shadow_rank_score": round(
                    suitable_probability * (1.0 - candidate_misleading), 4
                ),
            }
        )
    candidate_reviews.sort(key=lambda item: item["shadow_rank_score"], reverse=True)

    review_reasons: list[str] = []
    if visual_confidence < min_choice_confidence:
        review_reasons.append("visual_function_confidence_below_threshold")
    if source_confidence < min_choice_confidence:
        review_reasons.append("source_class_confidence_below_threshold")
    if misleading_probability >= risk_threshold:
        review_reasons.append("current_strategy_may_mislead_as_evidence")
    if _answer_value(source_answer, "choice") == "manual_review":
        review_reasons.append("source_class_requires_manual_review")

    usage = getattr(response, "usage", None)
    return {
        "asset_plan_id": beat.get("asset_plan_id"),
        "mode": "shadow",
        "approval": False,
        "pixel_inspection_performed": False,
        "status": "review_required" if review_reasons else "shadow_recommendation",
        "review_reasons": review_reasons,
        "model": getattr(response, "model", None),
        "recommended_visual_function": _answer_value(visual_answer, "choice"),
        "visual_function_confidence": round(visual_confidence, 4),
        "visual_function_probabilities": _answer_value(visual_answer, "probabilities", {}),
        "recommended_source_class": _answer_value(source_answer, "choice"),
        "source_class_confidence": round(source_confidence, 4),
        "source_class_probabilities": _answer_value(source_answer, "probabilities", {}),
        "specific_subject_probability": round(
            float(_answer_value(answers.get("specific_subject_required"), "noul", 0.0) or 0.0), 4
        ),
        "generic_stock_safe_probability": round(
            float(_answer_value(answers.get("generic_stock_safe"), "noul", 0.0) or 0.0), 4
        ),
        "generated_safe_if_labeled_probability": round(
            float(_answer_value(answers.get("generated_safe_if_labeled"), "noul", 0.0) or 0.0), 4
        ),
        "current_strategy_suitable_probability": round(
            float(_answer_value(answers.get("current_strategy_suitable"), "noul", 0.0) or 0.0), 4
        ),
        "current_strategy_misleading_probability": round(misleading_probability, 4),
        "candidate_reviews": candidate_reviews,
        "usage": {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        },
    }
