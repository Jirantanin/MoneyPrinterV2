"""Cost and runtime reporting for PodcastV2 Producer Mode.

The report is intentionally artifact-only: it reads manifests already written
inside an episode folder and does not call paid providers, search APIs, or the
core PodcastV2 runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COST_REPORT_VERSION = 1
RUNWARE_FLUX1_USD_PER_IMAGE = 0.0038

FREE_OR_LOCAL_PROVIDERS = {
    "nasa_images",
    "nasa_svs",
    "jpl_photojournal",
    "pexels",
    "pixabay",
    "remotion_graphic",
    "local_reframe",
    "local_graphic_broll",
}
UNKNOWN_COST_PROVIDERS = {
    "codex_imagegen",
}
PAID_IMAGE_PROVIDERS = {
    "runware_flux1": RUNWARE_FLUX1_USD_PER_IMAGE,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _entries(manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        return []
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _counts(entries: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in entries:
        value = str(entry.get(key) or "unknown")
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def _sum_entry_cost(entries: list[dict[str, Any]]) -> float:
    return round(sum(_to_float(entry.get("estimated_cost_usd")) for entry in entries), 6)


def _tts_cost_section(tts_manifest: dict[str, Any] | None) -> dict[str, Any]:
    manifest = tts_manifest if isinstance(tts_manifest, dict) else {}
    entries = _entries(manifest)
    dry_run = bool(manifest.get("dry_run"))
    estimated = _to_float(manifest.get("estimated_cost_usd")) or _sum_entry_cost(entries)
    generated = [
        entry
        for entry in entries
        if str(entry.get("status") or "") in {"generated"}
    ]
    planned = [
        entry
        for entry in entries
        if dry_run or str(entry.get("status") or "") in {"planned", "task_pending"}
    ]
    skipped = [
        entry
        for entry in entries
        if str(entry.get("status") or "") in {"skipped_existing"}
    ]
    actual_this_run = _sum_entry_cost(generated)
    remaining = estimated if dry_run else _sum_entry_cost(planned)
    duration = _to_float(manifest.get("total_duration_seconds"))
    if not duration:
        duration = round(sum(_to_float(entry.get("duration_seconds")) for entry in entries), 3)
    return {
        "name": "Gemini TTS",
        "provider": manifest.get("provider") or "gemini_tts",
        "model": manifest.get("model") or "",
        "status": manifest.get("status") or "missing",
        "dry_run": dry_run,
        "entry_count": len(entries),
        "status_counts": _counts(entries, "status"),
        "duration_seconds": round(duration, 3),
        "estimated_total_cost_usd": round(estimated, 6),
        "new_cost_this_run_usd": round(actual_this_run, 6),
        "remaining_estimated_cost_usd": round(remaining, 6),
        "reused_entry_count": len(skipped),
    }


def _asset_cost_section(asset_manifest: dict[str, Any] | None) -> dict[str, Any]:
    manifest = asset_manifest if isinstance(asset_manifest, dict) else {}
    entries = _entries(manifest)
    provider_counts = _counts(entries, "provider")
    status_counts = _counts(entries, "status")
    provider_costs: dict[str, dict[str, Any]] = {}
    unknown_cost_items: list[dict[str, Any]] = []
    total_actual = 0.0
    total_remaining = 0.0

    for entry in entries:
        provider = str(entry.get("provider") or "unknown")
        status = str(entry.get("status") or "unknown")
        bucket = provider_costs.setdefault(
            provider,
            {
                "provider": provider,
                "entry_count": 0,
                "new_cost_this_run_usd": 0.0,
                "remaining_estimated_cost_usd": 0.0,
                "cost_basis": "free_or_local" if provider in FREE_OR_LOCAL_PROVIDERS else "unknown",
            },
        )
        bucket["entry_count"] += 1

        if provider in PAID_IMAGE_PROVIDERS:
            unit_cost = PAID_IMAGE_PROVIDERS[provider]
            bucket["cost_basis"] = f"{unit_cost:.4f}_usd_per_image"
            if status in {"generated", "downloaded"}:
                bucket["new_cost_this_run_usd"] += unit_cost
                total_actual += unit_cost
            elif status in {"task_pending", "planned", "pending"}:
                bucket["remaining_estimated_cost_usd"] += unit_cost
                total_remaining += unit_cost
        elif provider in UNKNOWN_COST_PROVIDERS:
            bucket["cost_basis"] = "external_or_unmetered"
            if status in {"generated", "task_pending", "planned", "pending"}:
                unknown_cost_items.append(
                    {
                        "provider": provider,
                        "asset_plan_id": entry.get("asset_plan_id"),
                        "scene_index": entry.get("scene_index"),
                        "status": status,
                        "reason": "Provider cost is not available from local manifests.",
                    }
                )

    for bucket in provider_costs.values():
        bucket["new_cost_this_run_usd"] = round(_to_float(bucket["new_cost_this_run_usd"]), 6)
        bucket["remaining_estimated_cost_usd"] = round(
            _to_float(bucket["remaining_estimated_cost_usd"]),
            6,
        )

    total_bytes = sum(_to_int(entry.get("bytes")) for entry in entries)
    return {
        "name": "Visual assets",
        "status": manifest.get("status") or "missing",
        "dry_run": bool(manifest.get("dry_run")),
        "entry_count": len(entries),
        "provider_counts": provider_counts,
        "status_counts": status_counts,
        "local_bytes": total_bytes,
        "provider_costs": sorted(provider_costs.values(), key=lambda item: str(item.get("provider"))),
        "new_cost_this_run_usd": round(total_actual, 6),
        "remaining_estimated_cost_usd": round(total_remaining, 6),
        "estimated_total_cost_usd": round(total_actual + total_remaining, 6),
        "unknown_cost_items": unknown_cost_items,
    }


def _render_runtime_section(
    render_manifest: dict[str, Any] | None,
    final_qc: dict[str, Any] | None,
    render_preflight: dict[str, Any] | None,
) -> dict[str, Any]:
    render_manifest = render_manifest if isinstance(render_manifest, dict) else {}
    final_qc = final_qc if isinstance(final_qc, dict) else {}
    render_preflight = render_preflight if isinstance(render_preflight, dict) else {}
    fmt = final_qc.get("format") if isinstance(final_qc.get("format"), dict) else {}
    summary = render_preflight.get("summary") if isinstance(render_preflight.get("summary"), dict) else {}
    planned_duration = (
        _to_float(render_manifest.get("render_duration_seconds"))
        or _to_float(summary.get("render_duration_seconds"))
    )
    final_duration = _to_float(fmt.get("duration_seconds")) or _to_float(final_qc.get("duration_seconds"))
    return {
        "name": "Render",
        "status": render_manifest.get("status") or "missing",
        "preflight_status": render_preflight.get("status") or "missing",
        "final_qc_status": final_qc.get("status") or "missing",
        "scene_count": _to_int(render_manifest.get("scene_count") or summary.get("scene_count")),
        "planned_duration_seconds": round(planned_duration, 3),
        "final_duration_seconds": round(final_duration, 3),
        "estimated_frames": _to_int(render_manifest.get("estimated_frames") or summary.get("estimated_frames")),
        "final_video_bytes": _to_int(render_manifest.get("final_video_bytes") or final_qc.get("file_bytes")),
        "estimated_total_cost_usd": 0.0,
        "new_cost_this_run_usd": 0.0,
        "remaining_estimated_cost_usd": 0.0,
        "cost_basis": "local_remotion_ffmpeg",
    }


def _budget_status(estimated_cost: float, warning_at: float, stop_at: float) -> str:
    if stop_at > 0 and estimated_cost >= stop_at:
        return "stop_required"
    if warning_at > 0 and estimated_cost >= warning_at:
        return "warn"
    return "pass"


def build_cost_report(
    *,
    episode_dir: str | Path,
    plan: dict[str, Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
    asset_manifest: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
    final_qc: dict[str, Any] | None = None,
    render_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a cost/runtime report from local Producer Mode artifacts."""

    episode_path = Path(episode_dir)
    plan = plan if isinstance(plan, dict) else {}
    budget = plan.get("budget") if isinstance(plan.get("budget"), dict) else {}
    warning_at = _to_float(budget.get("warning_at")) or 3.0
    stop_at = _to_float(budget.get("stop_at")) or 5.0

    tts = _tts_cost_section(tts_manifest)
    assets = _asset_cost_section(asset_manifest)
    render = _render_runtime_section(render_manifest, final_qc, render_preflight)

    sections = [tts, assets, render]
    new_cost = round(sum(_to_float(item.get("new_cost_this_run_usd")) for item in sections), 6)
    remaining = round(sum(_to_float(item.get("remaining_estimated_cost_usd")) for item in sections), 6)
    estimated_total = round(new_cost + remaining, 6)
    unknown_items = list(assets.get("unknown_cost_items", []) or [])
    warnings: list[str] = []
    errors: list[str] = []
    if unknown_items:
        warnings.append(
            f"{len(unknown_items)} asset entries use providers with no local cost signal."
        )
    if not _entries(tts_manifest):
        warnings.append("tts_manifest.json is missing or empty; TTS cost is incomplete.")
    if not _entries(asset_manifest):
        warnings.append("asset_manifest.json is missing or empty; asset cost is incomplete.")

    budget_state = _budget_status(estimated_total, warning_at, stop_at)
    if budget_state == "stop_required":
        errors.append(
            f"Estimated cost ${estimated_total:.4f} reaches stop cap ${stop_at:.2f}."
        )
    elif budget_state == "warn":
        warnings.append(
            f"Estimated cost ${estimated_total:.4f} reaches warning cap ${warning_at:.2f}."
        )

    runtime_trace_path = episode_path / "podcast_runtime_trace.jsonl"
    status = "blocked" if errors else ("review" if warnings else "pass")
    return {
        "schema_version": COST_REPORT_VERSION,
        "stage": "cost_report",
        "created_at": _utc_now(),
        "status": status,
        "episode_dir": str(episode_path),
        "budget": {
            "currency": str(budget.get("currency") or "USD"),
            "warning_at": warning_at,
            "stop_at": stop_at,
            "status": budget_state,
        },
        "totals": {
            "new_cost_this_run_usd": new_cost,
            "remaining_estimated_cost_usd": remaining,
            "estimated_total_cost_usd": estimated_total,
            "unknown_cost_item_count": len(unknown_items),
        },
        "runtime": {
            "planned_duration_seconds": render.get("planned_duration_seconds", 0),
            "final_duration_seconds": render.get("final_duration_seconds", 0),
            "scene_count": render.get("scene_count", 0),
            "estimated_frames": render.get("estimated_frames", 0),
            "runtime_trace_path": str(runtime_trace_path),
            "trace_cost_available": runtime_trace_path.exists(),
        },
        "sections": sections,
        "unknown_cost_items": unknown_items,
        "warnings": warnings,
        "errors": errors,
    }
