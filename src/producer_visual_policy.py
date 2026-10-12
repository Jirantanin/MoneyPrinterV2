"""Visual source policy for Producer Mode.

The policy is intentionally small and machine-checkable: real footage can fill
the whole cut, while graphics and generated imagery stay under user-defined
ceilings. It also surfaces review-only balance warnings when final timelines
become visually flat through too many source-media reframes.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


VISUAL_POLICY_VERSION = 1
GRAPHIC_MAX_RATIO = 0.20
GENERATED_IMAGE_MAX_RATIO = 0.50
GRAPHIC_REVIEW_MIN_RATIO = 0.08
LOCAL_REFRAME_REVIEW_MAX_RATIO = 0.60
BALANCE_REVIEW_MIN_VISUAL_COUNT = 20

GRAPHIC_PROVIDERS = {
    "local_graphic_broll",
    "remotion_graphic",
}
GENERATED_IMAGE_PROVIDERS = {
    "codex_imagegen",
    "runware_flux1",
    "runware_flux1_image",
}
REAL_FOOTAGE_PROVIDERS = {
    "nasa_svs",
    "pexels",
    "pixabay",
}
OFFICIAL_REAL_PROVIDERS = {
    "official_media",
    "nasa_images",
    "nasa_svs",
    "jpl_photojournal",
    "fresh_official_broll",
}
VERIFIED_REAL_IMAGE_PROVIDERS = {
    "wikimedia_commons",
    "manual_verified_media",
}
REAL_REFRAME_PROVIDER = "local_reframe"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()


def _provider(entry: dict[str, Any]) -> str:
    return _clean(entry.get("provider") or entry.get("selected_provider"))


def default_visual_source_policy() -> dict[str, Any]:
    return {
        "schema_version": VISUAL_POLICY_VERSION,
        "policy_name": "producer_visual_source_policy_v1",
        "created_at": _utc_now(),
        "caps": {
            "graphic_max_ratio": GRAPHIC_MAX_RATIO,
            "generated_image_max_ratio": GENERATED_IMAGE_MAX_RATIO,
            "real_footage_max_ratio": 1.0,
        },
        "balance": {
            "graphic_review_min_ratio": GRAPHIC_REVIEW_MIN_RATIO,
            "local_reframe_review_max_ratio": LOCAL_REFRAME_REVIEW_MAX_RATIO,
            "min_visual_count_for_review": BALANCE_REVIEW_MIN_VISUAL_COUNT,
            "graphic_floor_applies_when_graphics_present": True,
        },
        "counting_rules": {
            "graphics": sorted(GRAPHIC_PROVIDERS),
            "generated_images": sorted(GENERATED_IMAGE_PROVIDERS),
            "real_footage": (
                "Official/verified media, stock video, and real-footage reframes are unlimited "
                "when they remain relevant, do not loop/repeat, and do not flatten explanatory beats."
            ),
        },
        "source_order": [
            "official_or_verified_real_footage",
            "stock_video_when_not_misleading",
            "short_explanatory_graphic_under_20_percent_when_it_clarifies_process_or_data",
            "local_reframe_from_real_or_approved_source",
            "runware_or_codex_imagegen_under_50_percent",
            "manual_review_if_caps_or_relevance_fail",
        ],
    }


def plan_visual_source_policy(plan: dict[str, Any]) -> dict[str, Any] | None:
    """The episode's own source policy (``visual_rules.source_policy`` in producer_plan.json), e.g. a
    user-directed cap override; None falls back to the default policy."""
    rules = plan.get("visual_rules") if isinstance(plan, dict) else None
    policy = rules.get("source_policy") if isinstance(rules, dict) else None
    return policy if isinstance(policy, dict) and isinstance(policy.get("caps"), dict) else None


def _limit_for(total: int, ratio: float) -> int:
    if total <= 0:
        return 0
    return int(math.floor(total * ratio + 1e-9))


def _floor_for(total: int, ratio: float) -> int:
    if total <= 0 or ratio <= 0:
        return 0
    return int(math.ceil(total * ratio - 1e-9))


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _balance_config(policy: dict[str, Any]) -> dict[str, Any]:
    balance = policy.get("balance")
    return balance if isinstance(balance, dict) else {}


def is_graphic_entry(entry: dict[str, Any]) -> bool:
    provider = _provider(entry)
    timeline_role = _clean(entry.get("timeline_role"))
    media_type = _clean(entry.get("media_type") or entry.get("selected_media_type"))
    derived_from = _clean(entry.get("derived_from_provider"))
    # A downloaded stock clip remains real footage even when the expander
    # records which source beat caused it to be selected.
    if provider in REAL_FOOTAGE_PROVIDERS and media_type == "video":
        return False
    return (
        provider in GRAPHIC_PROVIDERS
        or timeline_role in GRAPHIC_PROVIDERS
        or media_type == "graphic"
        or derived_from in GRAPHIC_PROVIDERS
    )


def is_generated_image_entry(entry: dict[str, Any]) -> bool:
    provider = _provider(entry)
    media_type = _clean(entry.get("media_type") or entry.get("selected_media_type"))
    derived_from = _clean(entry.get("derived_from_provider"))
    # Provenance explains why a stock clip was selected; it does not turn the
    # downloaded video into generated imagery for the visual-source cap.
    if provider in REAL_FOOTAGE_PROVIDERS and media_type == "video":
        return False
    return provider in GENERATED_IMAGE_PROVIDERS or derived_from in GENERATED_IMAGE_PROVIDERS


def is_real_footage_entry(entry: dict[str, Any]) -> bool:
    provider = _provider(entry)
    timeline_role = _clean(entry.get("timeline_role"))
    media_type = _clean(entry.get("media_type") or entry.get("selected_media_type"))
    derived_from = _clean(entry.get("derived_from_provider"))
    if provider in REAL_FOOTAGE_PROVIDERS and media_type == "video":
        return True
    if timeline_role == "fresh_official_broll":
        return True
    if provider in OFFICIAL_REAL_PROVIDERS and media_type in {"image", "video"}:
        return True
    if provider in VERIFIED_REAL_IMAGE_PROVIDERS and media_type in {"image", "video"}:
        return True
    if provider == REAL_REFRAME_PROVIDER and derived_from not in GRAPHIC_PROVIDERS | GENERATED_IMAGE_PROVIDERS:
        return True
    return False


def classify_visual_entry(entry: dict[str, Any]) -> str:
    if is_graphic_entry(entry):
        return "graphic"
    if is_generated_image_entry(entry):
        return "generated_image"
    if is_real_footage_entry(entry):
        return "real_footage"
    media_type = _clean(entry.get("media_type") or entry.get("selected_media_type"))
    if media_type == "video":
        return "real_footage"
    return "other"


def visual_policy_report(
    entries: list[dict[str, Any]],
    *,
    total_visual_count: int | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or default_visual_source_policy()
    caps = policy.get("caps") if isinstance(policy.get("caps"), dict) else {}
    balance = _balance_config(policy)
    graphic_ratio = float(caps.get("graphic_max_ratio", GRAPHIC_MAX_RATIO))
    generated_ratio = float(caps.get("generated_image_max_ratio", GENERATED_IMAGE_MAX_RATIO))
    graphic_review_ratio = float(
        balance.get("graphic_review_min_ratio", GRAPHIC_REVIEW_MIN_RATIO)
    )
    local_reframe_review_ratio = float(
        balance.get("local_reframe_review_max_ratio", LOCAL_REFRAME_REVIEW_MAX_RATIO)
    )
    review_min_visual_count = int(
        balance.get("min_visual_count_for_review", BALANCE_REVIEW_MIN_VISUAL_COUNT)
    )
    graphic_floor_when_present = bool(
        balance.get("graphic_floor_applies_when_graphics_present", True)
    )
    total = int(total_visual_count if total_visual_count is not None else len(entries))
    total = max(total, len(entries), 0)

    provider_counts: dict[str, int] = {}
    category_counts = {
        "graphic": 0,
        "generated_image": 0,
        "real_footage": 0,
        "other": 0,
    }
    for entry in entries:
        provider = str(entry.get("provider") or entry.get("selected_provider") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        category = classify_visual_entry(entry)
        category_counts[category] = category_counts.get(category, 0) + 1

    graphic_limit = _limit_for(total, graphic_ratio)
    generated_limit = _limit_for(total, generated_ratio)
    graphic_review_min = _floor_for(total, graphic_review_ratio)
    violations: list[dict[str, Any]] = []
    review_warnings: list[dict[str, Any]] = []
    if category_counts["graphic"] > graphic_limit:
        violations.append(
            {
                "category": "graphic",
                "count": category_counts["graphic"],
                "limit": graphic_limit,
                "max_ratio": graphic_ratio,
            }
        )
    if category_counts["generated_image"] > generated_limit:
        violations.append(
            {
                "category": "generated_image",
                "count": category_counts["generated_image"],
                "limit": generated_limit,
                "max_ratio": generated_ratio,
            }
        )

    local_reframe_count = provider_counts.get(REAL_REFRAME_PROVIDER, 0)
    local_reframe_ratio = _ratio(local_reframe_count, total)
    enough_slots_for_balance = total >= review_min_visual_count
    graphic_floor_applies = (
        enough_slots_for_balance
        and graphic_review_min > 0
        and (
            not graphic_floor_when_present
            or category_counts["graphic"] > 0
        )
    )
    if graphic_floor_applies and category_counts["graphic"] < graphic_review_min:
        review_warnings.append(
            {
                "category": "graphic_density",
                "count": category_counts["graphic"],
                "review_minimum": graphic_review_min,
                "review_min_ratio": graphic_review_ratio,
                "actual_ratio": _ratio(category_counts["graphic"], total),
                "message": (
                    "Graphic density is low after timeline expansion; review concept, process, "
                    "scale, and data beats before rendering."
                ),
            }
        )
    if enough_slots_for_balance and local_reframe_ratio > local_reframe_review_ratio:
        review_warnings.append(
            {
                "category": "local_reframe_density",
                "count": local_reframe_count,
                "review_max_ratio": local_reframe_review_ratio,
                "actual_ratio": local_reframe_ratio,
                "message": (
                    "Local reframes dominate the final visual timeline; add fresh relevant "
                    "source media or earned explanatory graphics instead of filling pacing only "
                    "with reframes."
                ),
            }
        )

    ratios = {key: _ratio(value, total) for key, value in category_counts.items()}
    time_exposure = visual_time_exposure(entries)
    if time_exposure["longest_graphic_run"] > 2:
        review_warnings.append({"category": "graphic_run", "message": "More than two consecutive graphics; review the explanatory purpose of this sequence."})
    if time_exposure["coverage"] == "complete":
        for category, cap in (("graphic", graphic_ratio), ("generated_image", generated_ratio)):
            actual = time_exposure["category_ratios"].get(category, 0)
            if actual > cap:
                review_warnings.append({"category": f"{category}_screen_time", "actual_ratio": actual,
                                        "message": f"{category} occupies {actual:.1%} of screen time; review against slot ceiling {cap:.1%}."})
    provider_ratios = {key: _ratio(value, total) for key, value in provider_counts.items()}
    if violations:
        status = "blocked"
    elif review_warnings:
        status = "review"
    else:
        status = "pass"
    review_suffix = (
        f"; review warnings {len(review_warnings)}"
        if review_warnings
        else ""
    )
    return {
        "schema_version": VISUAL_POLICY_VERSION,
        "stage": "visual_source_policy",
        "created_at": _utc_now(),
        "status": status,
        "total_visual_count": total,
        "limits": {
            "graphic_max_count": graphic_limit,
            "graphic_max_ratio": graphic_ratio,
            "generated_image_max_count": generated_limit,
            "generated_image_max_ratio": generated_ratio,
            "real_footage_max_ratio": 1.0,
            "graphic_review_min_count": graphic_review_min,
            "graphic_review_min_ratio": graphic_review_ratio,
            "local_reframe_review_max_ratio": local_reframe_review_ratio,
        },
        "category_counts": category_counts,
        "category_ratios": ratios,
        "provider_counts": provider_counts,
        "provider_ratios": provider_ratios,
        "time_exposure": time_exposure,
        "violations": violations,
        "review_warnings": review_warnings,
        "summary": (
            f"Visual source policy {status}: graphics {category_counts['graphic']}/{graphic_limit}, "
            f"generated images {category_counts['generated_image']}/{generated_limit}, "
            "real footage unlimited"
            f"{review_suffix}."
        ),
    }


def visual_time_exposure(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Use assigned slot time only: a source clip's full duration is not exposure."""
    totals: dict[str, float] = {}
    sections: dict[str, dict[str, float]] = {}
    missing = 0
    longest_graphic_run = run = 0
    for entry in entries:
        category = classify_visual_entry(entry)
        run = run + 1 if category == "graphic" else 0
        longest_graphic_run = max(run, longest_graphic_run)
        try:
            seconds = float(entry["slot_duration_seconds"])
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("invalid assigned duration")
        except (KeyError, TypeError, ValueError):
            missing += 1
            continue
        totals[category] = totals.get(category, 0.0) + seconds
        section = str(entry.get("section_index") if entry.get("section_index") is not None else entry.get("scene_index", "unknown"))
        bucket = sections.setdefault(section, {})
        bucket[category] = bucket.get(category, 0.0) + seconds
    total = sum(totals.values())
    return {"coverage": "complete" if entries and not missing else "incomplete",
            "missing_duration_count": missing, "total_assigned_seconds": round(total, 3),
            "category_seconds": totals, "category_ratios": {key: round(value / total, 4) for key, value in totals.items()} if total else {},
            "sections": {key: {"seconds": value, "ratios": {category: round(seconds / sum(value.values()), 4) for category, seconds in value.items()}} for key, value in sections.items()},
            "longest_graphic_run": longest_graphic_run}


def policy_warnings(report: dict[str, Any]) -> list[str]:
    return [
        (
            f"visual policy violation: {item.get('category')} "
            f"{item.get('count')}/{item.get('limit')} exceeds max ratio {item.get('max_ratio')}"
        )
        for item in report.get("violations", [])
        if isinstance(item, dict)
    ]


def policy_review_warnings(report: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for item in report.get("review_warnings", []):
        if not isinstance(item, dict):
            continue
        category = item.get("category") or "visual_balance"
        message = item.get("message") or "Visual source balance needs producer review."
        if "review_minimum" in item:
            messages.append(
                f"visual policy review: {category} {item.get('count')}/{item.get('review_minimum')} "
                f"below review target ratio {item.get('review_min_ratio')}; {message}"
            )
        elif "review_max_ratio" in item:
            messages.append(
                f"visual policy review: {category} {item.get('count')} ratio {item.get('actual_ratio')} "
                f"exceeds review ratio {item.get('review_max_ratio')}; {message}"
            )
        else:
            messages.append(f"visual policy review: {category}; {message}")
    return messages


def can_add_visual_entry(
    current_entries: list[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    planned_total_count: int,
    policy: dict[str, Any] | None = None,
) -> bool:
    report = visual_policy_report(
        [*current_entries, candidate],
        total_visual_count=planned_total_count,
        policy=policy,
    )
    return report.get("status") != "blocked"
