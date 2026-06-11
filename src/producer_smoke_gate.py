"""Production smoke gate for PodcastV2 Producer Mode.

This module is deliberately read-only. It inspects episode-local artifacts and
local provider readiness, then explains whether an episode is safe to push into
real provider calls or a production render.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SMOKE_GATE_VERSION = 1
READY_STATUSES = {"pass", "ready", "complete"}
REVIEW_STATUSES = {"review", "needs_review"}
BLOCKED_STATUSES = {"blocked", "failed", "needs_tasks", "planned", "pending", "dry_run"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _status(value: Any) -> str:
    return str(value or "missing").lower()


def _gate(
    *,
    name: str,
    status: str,
    score: int,
    detail: str,
    next_action: str = "",
    blocking: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "score": max(0, min(100, int(score))),
        "blocking": bool(blocking),
        "detail": detail,
        "next_action": next_action,
    }


def _provider_key_status() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    try:
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        with config_path.open("r", encoding="utf-8-sig") as f:
            loaded = json.load(f)
        cfg = loaded if isinstance(loaded, dict) else {}
        pexels_key = str(cfg.get("pexels_api_key") or os.environ.get("PEXELS_API_KEY", "") or "")
        pixabay_key = str(
            cfg.get("pixabay_api_key") or os.environ.get("PIXABAY_API_KEY", "") or ""
        )
        values = {
            "llm_anthropic": cfg.get("anthropic_api_key", ""),
            "llm_minimax": cfg.get("minimax_api_key", ""),
            "gemini_tts": (
                cfg.get("gemini_tts_api_key", "")
                or cfg.get("nanobanana2_api_key", "")
                or os.environ.get("GEMINI_API_KEY", "")
            ),
            "gemini_image_repo_fallback": (
                cfg.get("nanobanana2_api_key", "") or os.environ.get("GEMINI_API_KEY", "")
            ),
            "pexels": pexels_key,
            "pixabay": pixabay_key,
            "runware_flux1": cfg.get("runware_api_key", "") or os.environ.get("RUNWARE_API_KEY", ""),
        }
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "provider": "config",
                "status": "blocked",
                "configured": False,
                "required": True,
                "detail": f"Could not inspect provider config: {exc}",
            }
        ]

    for provider, value in values.items():
        required = provider in {"gemini_tts"}
        configured = bool(str(value or "").strip())
        if configured:
            status = "ready"
        elif required:
            status = "blocked"
        else:
            status = "optional_missing"
        statuses.append(
            {
                "provider": provider,
                "status": status,
                "configured": configured,
                "required": required,
                "detail": (
                    "configured"
                    if configured
                    else "missing; required for this provider path"
                    if required
                    else "missing; optional depending on selected asset plan"
                ),
            }
        )
    statuses.append(
        {
            "provider": "codex_imagegen_skill",
            "status": "session_required",
            "configured": None,
            "required": True,
            "detail": (
                "Section openers require Codex imagegen fulfillment in the active session; "
                "this cannot be proven from config keys."
            ),
        }
    )
    return statuses


def _research_gate(plan: dict[str, Any]) -> dict[str, Any]:
    research = _as_dict(plan.get("research"))
    sources = _as_list(research.get("sources"))
    competitor = _as_list(research.get("competitor_results"))
    minimum = int(research.get("minimum_sources") or 3)
    status = _status(research.get("status"))
    if status != "complete" or len(sources) < minimum:
        return _gate(
            name="research",
            status="blocked",
            score=30 if sources else 0,
            blocking=True,
            detail=f"Research status={status}; sources={len(sources)}/{minimum}.",
            next_action="Run research with page fetch enabled and keep at least 3-5 credible sources.",
        )
    if not competitor:
        return _gate(
            name="research",
            status="review",
            score=75,
            detail="Topic sources pass, but competitor SEO results are empty.",
            next_action="Refresh competitor search before final metadata decisions.",
        )
    return _gate(
        name="research",
        status="ready",
        score=95,
        detail=f"Research has {len(sources)} sources and {len(competitor)} competitor records.",
    )


def _script_gate(plan: dict[str, Any], script_qc: dict[str, Any]) -> dict[str, Any]:
    script_draft = _as_dict(plan.get("script_draft"))
    status = _status(script_draft.get("status") or script_qc.get("status"))
    chars = int(script_qc.get("chars_no_space") or script_draft.get("chars_no_space") or 0)
    thai_ratio = _to_float(script_qc.get("thai_character_ratio"))
    length_status = _status(script_qc.get("length_status") or script_draft.get("length_status"))
    if status not in READY_STATUSES or thai_ratio < 0.65:
        return _gate(
            name="script",
            status="blocked",
            score=45 if chars else 0,
            blocking=True,
            detail=(
                f"Script status={status}; chars_no_space={chars}; "
                f"thai_ratio={thai_ratio:.2f}; length_status={length_status}."
            ),
            next_action="Run draft-script with production LLM and verify Thai narration quality.",
        )
    if length_status not in {"pass", "ready"}:
        return _gate(
            name="script",
            status="review",
            score=80,
            detail=f"Script is Thai and structurally present but length_status={length_status}.",
            next_action="Revise into the preferred 8,800-9,500 Thai chars without whitespace band.",
        )
    return _gate(
        name="script",
        status="ready",
        score=95,
        detail=f"Script status={status}; chars_no_space={chars}; thai_ratio={thai_ratio:.2f}.",
    )


def _asset_gate(plan: dict[str, Any], asset_manifest: dict[str, Any], asset_qc: dict[str, Any]) -> dict[str, Any]:
    asset_state = _as_dict(plan.get("asset_production"))
    entries = _as_list(asset_manifest.get("entries"))
    status = _status(asset_state.get("status") or asset_manifest.get("status") or asset_qc.get("status"))
    pending = [
        entry for entry in entries if isinstance(entry, dict) and _status(entry.get("status")) in {"task_pending", "planned", "pending"}
    ]
    failed = [
        entry for entry in entries if isinstance(entry, dict) and _status(entry.get("status")) == "failed"
    ]
    missing_files = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and _status(entry.get("status")) in {"downloaded", "generated"}
        and not Path(str(entry.get("local_path") or "")).exists()
    ]
    if status not in READY_STATUSES or pending or failed or missing_files:
        return _gate(
            name="assets",
            status="blocked",
            score=45 if entries else 0,
            blocking=True,
            detail=(
                f"Asset status={status}; entries={len(entries)}; "
                f"pending={len(pending)}; failed={len(failed)}; missing_files={len(missing_files)}."
            ),
            next_action=(
                "Fulfill Codex imagegen opener tasks, download official/stock media, "
                "apply results, and rerun produce-assets/apply-asset-results."
            ),
        )
    return _gate(
        name="assets",
        status="ready",
        score=95,
        detail=f"All {len(entries)} asset manifest entries are fulfilled with local files.",
    )


def _audio_gate(plan: dict[str, Any], tts_manifest: dict[str, Any], tts_qc: dict[str, Any]) -> dict[str, Any]:
    audio_state = _as_dict(plan.get("audio_production"))
    status = _status(audio_state.get("status") or tts_manifest.get("status") or tts_qc.get("status"))
    entries = _as_list(tts_manifest.get("entries"))
    dry_run = bool(tts_manifest.get("dry_run"))
    failed = [
        entry for entry in entries if isinstance(entry, dict) and _status(entry.get("status")) == "failed"
    ]
    planned = [
        entry
        for entry in entries
        if isinstance(entry, dict) and _status(entry.get("status")) in {"planned", "pending"}
    ]
    if dry_run or status not in READY_STATUSES or planned or failed:
        return _gate(
            name="audio",
            status="blocked",
            score=45 if entries else 0,
            blocking=True,
            detail=(
                f"Audio status={status}; dry_run={dry_run}; entries={len(entries)}; "
                f"planned={len(planned)}; failed={len(failed)}."
            ),
            next_action="Run produce-tts without --dry-run, then listen/QC representative scenes.",
        )
    return _gate(
        name="audio",
        status="ready",
        score=95,
        detail=f"Audio has {len(entries)} produced/reusable TTS entries.",
    )


def _render_gate(
    render_preflight: dict[str, Any],
    render_manifest: dict[str, Any],
    final_qc: dict[str, Any],
) -> dict[str, Any]:
    preflight = _status(render_preflight.get("status"))
    render = _status(render_manifest.get("status"))
    qc = _status(final_qc.get("status"))
    if preflight != "ready" or render != "complete" or qc != "pass":
        return _gate(
            name="render",
            status="blocked",
            score=60 if preflight == "ready" else 30,
            blocking=True,
            detail=f"preflight={preflight}; render={render}; final_qc={qc}.",
            next_action="Run render-preflight, render-video, and final-qc after real assets/audio are complete.",
        )
    return _gate(
        name="render",
        status="ready",
        score=95,
        detail="Render preflight, final render, and final QC pass.",
    )


def _handoff_gate(
    cost_report: dict[str, Any],
    final_report: dict[str, Any],
    upload_pack: dict[str, Any],
) -> dict[str, Any]:
    cost = _status(cost_report.get("status"))
    final = _status(final_report.get("status"))
    upload = _status(upload_pack.get("status"))
    budget = _as_dict(cost_report.get("budget"))
    budget_status = _status(budget.get("status"))
    if budget_status == "stop_required":
        return _gate(
            name="handoff",
            status="blocked",
            score=40,
            blocking=True,
            detail=f"Budget status={budget_status}; cost={cost}; final_report={final}; upload_pack={upload}.",
            next_action="Stop and ask before continuing because the budget stop cap was reached.",
        )
    if cost in BLOCKED_STATUSES or final in BLOCKED_STATUSES or upload in BLOCKED_STATUSES:
        return _gate(
            name="handoff",
            status="blocked",
            score=55,
            blocking=True,
            detail=f"cost={cost}; final_report={final}; upload_pack={upload}.",
            next_action="Regenerate cost-report, final-report, and upload-pack after final QC.",
        )
    if cost in REVIEW_STATUSES or final in REVIEW_STATUSES or upload in REVIEW_STATUSES:
        return _gate(
            name="handoff",
            status="review",
            score=80,
            detail=f"cost={cost}; final_report={final}; upload_pack={upload}; budget={budget_status}.",
            next_action="Review warnings in the reports before upload.",
        )
    return _gate(
        name="handoff",
        status="ready",
        score=95,
        detail=f"cost={cost}; final_report={final}; upload_pack={upload}; budget={budget_status}.",
    )


def _provider_gate(provider_statuses: list[dict[str, Any]], asset_manifest: dict[str, Any]) -> dict[str, Any]:
    entries = _as_list(asset_manifest.get("entries"))
    used_providers = {
        str(entry.get("provider") or "")
        for entry in entries
        if isinstance(entry, dict) and entry.get("provider")
    }
    status_by_provider = {str(item.get("provider")): item for item in provider_statuses}
    blockers: list[str] = []
    warnings: list[str] = []
    if status_by_provider.get("gemini_tts", {}).get("status") == "blocked":
        blockers.append("gemini_tts key missing")
    if "pexels" in used_providers and status_by_provider.get("pexels", {}).get("status") != "ready":
        blockers.append("pexels key missing for selected provider")
    if "pixabay" in used_providers and status_by_provider.get("pixabay", {}).get("status") != "ready":
        blockers.append("pixabay key missing for selected provider")
    if "runware_flux1" in used_providers and status_by_provider.get("runware_flux1", {}).get("status") != "ready":
        blockers.append("runware key missing for selected provider")
    if "codex_imagegen" in used_providers:
        warnings.append("codex_imagegen requires active-session fulfillment")
    if blockers:
        return _gate(
            name="providers",
            status="blocked",
            score=45,
            blocking=True,
            detail="; ".join(blockers + warnings),
            next_action="Configure missing provider keys or adjust the asset plan before live production.",
        )
    if warnings:
        return _gate(
            name="providers",
            status="review",
            score=80,
            detail="; ".join(warnings),
            next_action="Confirm Codex imagegen tasks can be fulfilled in this session.",
        )
    return _gate(
        name="providers",
        status="ready",
        score=95,
        detail="Required selected provider paths look available from local config/state.",
    )


def build_smoke_gate(
    *,
    episode_dir: str | Path,
    plan: dict[str, Any],
    script_qc: dict[str, Any] | None = None,
    asset_manifest: dict[str, Any] | None = None,
    asset_qc: dict[str, Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
    tts_qc: dict[str, Any] | None = None,
    render_preflight: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
    final_qc: dict[str, Any] | None = None,
    cost_report: dict[str, Any] | None = None,
    final_report: dict[str, Any] | None = None,
    upload_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    script_qc = _as_dict(script_qc)
    asset_manifest = _as_dict(asset_manifest)
    asset_qc = _as_dict(asset_qc)
    tts_manifest = _as_dict(tts_manifest)
    tts_qc = _as_dict(tts_qc)
    render_preflight = _as_dict(render_preflight)
    render_manifest = _as_dict(render_manifest)
    final_qc = _as_dict(final_qc)
    cost_report = _as_dict(cost_report)
    final_report = _as_dict(final_report)
    upload_pack = _as_dict(upload_pack)

    provider_statuses = _provider_key_status()
    gates = [
        _research_gate(plan),
        _script_gate(plan, script_qc),
        _asset_gate(plan, asset_manifest, asset_qc),
        _audio_gate(plan, tts_manifest, tts_qc),
        _render_gate(render_preflight, render_manifest, final_qc),
        _handoff_gate(cost_report, final_report, upload_pack),
        _provider_gate(provider_statuses, asset_manifest),
    ]
    blocking = [gate for gate in gates if gate.get("blocking")]
    review = [gate for gate in gates if gate.get("status") == "review"]
    overall_score = round(sum(int(gate.get("score") or 0) for gate in gates) / max(1, len(gates)))
    if blocking:
        status = "blocked"
    elif review:
        status = "review"
    else:
        status = "ready"

    next_actions = [
        str(gate.get("next_action"))
        for gate in gates
        if gate.get("next_action") and gate.get("status") != "ready"
    ]
    warnings = [str(gate.get("detail")) for gate in review]
    errors = [str(gate.get("detail")) for gate in blocking]

    return {
        "schema_version": SMOKE_GATE_VERSION,
        "stage": "smoke_gate",
        "created_at": _utc_now(),
        "episode_dir": str(episode_path),
        "status": status,
        "overall_score": overall_score,
        "summary": (
            f"Production smoke gate is {status}; "
            f"{len(blocking)} blocking gates and {len(review)} review gates."
        ),
        "gates": gates,
        "provider_readiness": provider_statuses,
        "next_actions": next_actions,
        "warnings": warnings,
        "errors": errors,
    }
