"""Asset production helpers for PodcastV2 Producer Mode.

This stage turns ``visual_asset_plan.json`` and ``script.json`` into an
``asset_manifest.json`` plus imagegen/remotion/manual tasks. It can download
official media under a size cap, while paid or quota-sensitive providers remain
explicit opt-in.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


ASSET_MANIFEST_VERSION = 1
DEFAULT_MAX_DOWNLOAD_MB = 80
DOWNLOAD_TIMEOUT = (10, 90)

HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    return HTTP_SESSION.get(url, **kwargs)

OFFICIAL_PROVIDERS = {"nasa_images", "nasa_svs", "jpl_photojournal"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "tif", "tiff"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}
RESULT_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
LOCAL_RESULT_PROVIDERS = {
    "codex_imagegen",
    "remotion_graphic",
    "runware_flux1",
    "pexels",
    "pixabay",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return fallback


def _extension_from_url(url: str, media_type: str = "") -> str:
    path = urlparse(str(url or "")).path.lower()
    match = re.search(r"\.([a-z0-9]+)$", path)
    ext = match.group(1) if match else ""
    if ext in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
        return "jpg" if ext == "jpeg" else ext
    if str(media_type).lower() == "video":
        return "mp4"
    return "png"


def _content_type_extension(content_type: str, fallback: str) -> str:
    content_type = str(content_type or "").lower()
    if "jpeg" in content_type:
        return "jpg"
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    if "mp4" in content_type:
        return "mp4"
    if "webm" in content_type:
        return "webm"
    return fallback


def _scene_output_path(episode_dir: Path, scene_index: int, media_type: str, url: str = "") -> Path:
    ext = _extension_from_url(url, media_type)
    return episode_dir / f"scene_{scene_index:02d}_0.{ext}"


def _download_file(url: str, output_path: Path, *, max_bytes: int) -> tuple[bool, str, int]:
    if not url:
        return False, "missing download URL", 0
    _ensure_dir(output_path.parent)
    temp_path = output_path.with_suffix(output_path.suffix + ".part")
    started = time.monotonic()
    written = 0
    try:
        with _http_get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length") or 0)
            if content_length > max_bytes:
                return False, f"download exceeds cap ({content_length} > {max_bytes} bytes)", 0
            ext = _content_type_extension(response.headers.get("content-type", ""), output_path.suffix.lstrip("."))
            if ext and output_path.suffix.lower() != f".{ext}".lower():
                output_path = output_path.with_suffix(f".{ext}")
                temp_path = output_path.with_suffix(output_path.suffix + ".part")
            with temp_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if time.monotonic() - started > DOWNLOAD_TIMEOUT[1]:
                        raise TimeoutError("download exceeded wall-clock timeout")
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if written > max_bytes:
                        raise RuntimeError(f"download exceeded cap ({written} > {max_bytes} bytes)")
        if written < 1024:
            return False, "downloaded file is too small", written
        os.replace(temp_path, output_path)
        return True, str(output_path), written
    except Exception as exc:  # noqa: BLE001
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
        return False, str(exc), written


def _config_value(key: str, fallback: str = "") -> str:
    try:
        import config

        value = config._load_config().get(key, fallback)  # type: ignore[attr-defined]
        return str(value or os.environ.get(key.upper(), "") or fallback)
    except Exception:  # noqa: BLE001
        return str(os.environ.get(key.upper(), "") or fallback)


def _scene_lookup(script: list[Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for index, scene in enumerate(script, start=1):
        if not isinstance(scene, dict):
            continue
        asset_id = str(scene.get("producer_asset_plan_id") or "")
        if asset_id:
            lookup[asset_id] = {"scene_index": index - 1, **scene}
    return lookup


def _manifest_entry_base(
    *,
    beat_plan: dict[str, Any],
    scene: dict[str, Any],
    scene_index: int,
    output_path: Path,
) -> dict[str, Any]:
    return {
        "asset_plan_id": beat_plan.get("asset_plan_id"),
        "scene_index": scene_index,
        "scene_title": scene.get("scene_title", ""),
        "provider": beat_plan.get("selected_provider"),
        "media_type": beat_plan.get("selected_media_type"),
        "local_path": str(output_path),
        "source_url": beat_plan.get("selected_source_url"),
        "download_url": beat_plan.get("selected_download_url"),
        "preview_url": beat_plan.get("selected_preview_url"),
        "credit": beat_plan.get("selected_credit"),
        "license_note": beat_plan.get("selected_license_note"),
        "prompt": beat_plan.get("selected_prompt"),
        "keyword": beat_plan.get("selected_keyword"),
        "selected_reason": beat_plan.get("selected_reason"),
        "generated_or_illustrative": bool(beat_plan.get("selected_provider") in {"codex_imagegen", "runware_flux1"}),
        "accessed_date": _utc_now()[:10],
    }


def _stock_context(scene: dict[str, Any], beat_plan: dict[str, Any]) -> str:
    return " ".join(
        _clean_text(value)
        for value in [
            scene.get("scene_title"),
            scene.get("narration"),
            beat_plan.get("selected_keyword"),
            beat_plan.get("intent"),
        ]
        if _clean_text(value)
    )


def _try_stock_download(
    *,
    provider: str,
    scene: dict[str, Any],
    beat_plan: dict[str, Any],
    output_path: Path,
    duration: float,
    allow_stock: bool,
) -> tuple[str, str, int]:
    if not allow_stock:
        return "task_pending", "stock providers require --allow-stock", 0
    keyword = str(beat_plan.get("selected_keyword") or "").strip()
    context = _stock_context(scene, beat_plan)
    if provider == "pexels":
        api_key = _config_value("pexels_api_key")
        if not api_key:
            return "task_pending", "pexels_api_key is not configured", 0
        from pexels_provider import search_pexels_video

        result = search_pexels_video(context, api_key, str(output_path), duration, keyword=keyword)
    else:
        api_key = _config_value("pixabay_api_key")
        if not api_key:
            return "task_pending", "pixabay_api_key is not configured", 0
        from pixabay_provider import search_pixabay_video

        result = search_pixabay_video(context, api_key, str(output_path), duration, keyword=keyword)
    if result and Path(result).exists():
        return "downloaded", result, Path(result).stat().st_size
    return "failed", f"{provider} did not return a usable video", 0


def _try_runware(
    *,
    beat_plan: dict[str, Any],
    output_path: Path,
    allow_runware: bool,
) -> tuple[str, str, int]:
    if not allow_runware:
        return "task_pending", "runware fallback requires --allow-runware", 0
    from runware_provider import generate_flux1_image

    result = generate_flux1_image(str(beat_plan.get("selected_prompt") or ""), str(output_path))
    if result and Path(result).exists():
        return "generated", result, Path(result).stat().st_size
    return "failed", "Runware FLUX.1 did not return a usable image", 0


def _asset_qc(entries: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    missing_local = 0
    task_pending = 0
    failed = 0
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        provider = str(entry.get("provider") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        if status in {"task_pending", "planned"}:
            task_pending += 1
        if status == "failed":
            failed += 1
        if status in {"downloaded", "generated"} and not Path(str(entry.get("local_path") or "")).exists():
            missing_local += 1
    if failed or missing_local:
        status = "blocked"
    elif task_pending:
        status = "needs_tasks"
    else:
        status = "pass"
    return {
        "schema_version": ASSET_MANIFEST_VERSION,
        "stage": "asset_production_qc",
        "created_at": _utc_now(),
        "status": status,
        "summary": (
            f"Checked {len(entries)} asset manifest entries; "
            f"{task_pending} pending tasks, {failed} failed, {missing_local} missing local files."
        ),
        "provider_counts": provider_counts,
        "status_counts": status_counts,
        "warnings": warnings,
        "entries": [
            {
                "asset_plan_id": entry.get("asset_plan_id"),
                "scene_index": entry.get("scene_index"),
                "provider": entry.get("provider"),
                "status": entry.get("status"),
                "local_path": entry.get("local_path"),
                "issue": entry.get("issue", ""),
            }
            for entry in entries
        ],
    }


def _task_result_candidates(
    *,
    entry: dict[str, Any],
    episode_dir: Path,
    source_dir: Path,
) -> list[Path]:
    scene_index = int(entry.get("scene_index") or 0)
    asset_id = str(entry.get("asset_plan_id") or "").strip()
    local_path = Path(str(entry.get("local_path") or episode_dir / f"scene_{scene_index:02d}_0.png"))
    candidates = [local_path]

    names = [local_path.name, f"scene_{scene_index:02d}_0{local_path.suffix or '.png'}"]
    if asset_id:
        names.append(f"{asset_id}{local_path.suffix or '.png'}")
    for name in names:
        candidates.append(source_dir / name)

    stems = {local_path.stem, f"scene_{scene_index:02d}_0"}
    if asset_id:
        stems.add(asset_id)
    for stem in sorted(stems):
        for ext in sorted(RESULT_EXTENSIONS):
            candidates.append(source_dir / f"{stem}.{ext}")

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _copy_result_to_expected(source: Path, expected: Path) -> Path:
    target = expected
    if source.suffix and source.suffix.lower().lstrip(".") in RESULT_EXTENSIONS:
        target = expected.with_suffix(source.suffix.lower())
    _ensure_dir(target.parent)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def apply_asset_results(
    *,
    episode_dir: str | Path,
    asset_manifest: dict[str, Any],
    source_dir: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Apply local imagegen/remotion/manual result files to asset_manifest."""

    episode_path = Path(episode_dir)
    result_dir = Path(source_dir) if source_dir else episode_path
    entries = asset_manifest.get("entries") if isinstance(asset_manifest.get("entries"), list) else []
    updated_entries: list[dict[str, Any]] = []
    warnings: list[str] = list(asset_manifest.get("warnings", []) or [])
    applied = 0
    missing = 0

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        provider = str(entry.get("provider") or "")
        status = str(entry.get("status") or "")
        placeholder_replacement = (
            provider == "codex_imagegen"
            and status == "generated"
            and bool(entry.get("preflight_placeholder_only"))
        )
        should_apply = force or placeholder_replacement or status in {"task_pending", "planned", "failed"}
        if provider not in LOCAL_RESULT_PROVIDERS and not should_apply:
            updated_entries.append(entry)
            continue
        if not should_apply:
            updated_entries.append(entry)
            continue

        expected = Path(str(entry.get("local_path") or episode_path / f"scene_{int(entry.get('scene_index') or 0):02d}_0.png"))
        match = None
        for candidate in _task_result_candidates(
            entry=entry,
            episode_dir=episode_path,
            source_dir=result_dir,
        ):
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 1024:
                match = candidate
                break

        if not match:
            missing += 1
            entry["status"] = "task_pending"
            entry["issue"] = (
                f"result file not found in {result_dir}; expected scene/task filename"
            )
            updated_entries.append(entry)
            continue

        target = _copy_result_to_expected(match, expected)
        entry["local_path"] = str(target)
        entry["bytes"] = target.stat().st_size
        entry["status"] = "downloaded" if provider in {"pexels", "pixabay"} else "generated"
        entry["issue"] = ""
        entry["result_source_path"] = str(match)
        entry["result_applied_at"] = _utc_now()
        entry.pop("preflight_placeholder_path", None)
        entry.pop("preflight_placeholder_only", None)
        applied += 1
        updated_entries.append(entry)

    status = "complete"
    if any(entry.get("status") == "failed" for entry in updated_entries):
        status = "blocked"
    elif any(entry.get("status") == "task_pending" for entry in updated_entries):
        status = "needs_tasks"
    elif any(entry.get("status") == "planned" for entry in updated_entries):
        status = "planned"

    manifest = dict(asset_manifest)
    manifest["status"] = status
    manifest["updated_at"] = _utc_now()
    manifest["entries"] = updated_entries
    manifest["result_application"] = {
        "applied_at": _utc_now(),
        "source_dir": str(result_dir),
        "applied_count": applied,
        "missing_count": missing,
        "force": force,
    }
    if missing:
        warnings.append(f"{missing} asset task result files were still missing")
    manifest["warnings"] = warnings
    return {
        "asset_manifest": manifest,
        "asset_qc": _asset_qc(updated_entries, warnings),
    }


def produce_assets(
    *,
    episode_dir: str | Path,
    visual_asset_plan: dict[str, Any],
    script: list[Any],
    dry_run: bool = False,
    allow_stock: bool = False,
    allow_runware: bool = False,
    max_download_mb: int = DEFAULT_MAX_DOWNLOAD_MB,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    scene_by_asset = _scene_lookup(script)
    entries: list[dict[str, Any]] = []
    imagegen_tasks: list[dict[str, Any]] = []
    remotion_tasks: list[dict[str, Any]] = []
    warnings: list[str] = []
    max_bytes = max(1, int(max_download_mb)) * 1024 * 1024

    for beat_plan in visual_asset_plan.get("beat_plans") or []:
        if not isinstance(beat_plan, dict):
            continue
        asset_id = str(beat_plan.get("asset_plan_id") or "")
        scene = scene_by_asset.get(asset_id, {})
        scene_index = int(scene.get("scene_index") if scene else len(entries))
        provider = str(beat_plan.get("selected_provider") or "")
        media_type = str(beat_plan.get("selected_media_type") or "image")
        output_path = _scene_output_path(
            episode_path,
            scene_index,
            media_type,
            str(beat_plan.get("selected_download_url") or beat_plan.get("selected_source_url") or ""),
        )
        entry = _manifest_entry_base(
            beat_plan=beat_plan,
            scene=scene,
            scene_index=scene_index,
            output_path=output_path,
        )

        if provider == "codex_imagegen":
            entry["status"] = "task_pending"
            entry["issue"] = "Codex imagegen must be run in-session for this section opener."
            imagegen_tasks.append(
                {
                    "asset_plan_id": asset_id,
                    "scene_index": scene_index,
                    "output_path": str(output_path.with_suffix(".png")),
                    "prompt": beat_plan.get("selected_prompt"),
                    "section_title": beat_plan.get("section_title"),
                    "scene_title": scene.get("scene_title", ""),
                }
            )
        elif provider == "remotion_graphic":
            entry["status"] = "task_pending"
            entry["issue"] = "Remotion graphic task requires a later graphics renderer stage."
            remotion_tasks.append(
                {
                    "asset_plan_id": asset_id,
                    "scene_index": scene_index,
                    "output_path": str(output_path.with_suffix(".png")),
                    "prompt": beat_plan.get("selected_reason"),
                    "source_urls": beat_plan.get("source_urls", []),
                }
            )
        elif provider in OFFICIAL_PROVIDERS:
            if dry_run:
                entry["status"] = "planned"
                entry["issue"] = "dry run; official media download skipped"
            else:
                ok, detail, bytes_written = _download_file(
                    str(beat_plan.get("selected_download_url") or ""),
                    output_path,
                    max_bytes=max_bytes,
                )
                entry["bytes"] = bytes_written
                if ok:
                    entry["status"] = "downloaded"
                    entry["local_path"] = detail
                else:
                    preview_url = str(beat_plan.get("selected_preview_url") or "")
                    preview_path = _scene_output_path(episode_path, scene_index, "image", preview_url)
                    preview_ok = False
                    preview_detail = ""
                    preview_bytes = 0
                    if preview_url and preview_url != str(beat_plan.get("selected_download_url") or ""):
                        preview_ok, preview_detail, preview_bytes = _download_file(
                            preview_url,
                            preview_path,
                            max_bytes=max_bytes,
                        )
                    if preview_ok:
                        entry["status"] = "downloaded"
                        entry["media_type"] = "image"
                        entry["local_path"] = preview_detail
                        entry["bytes"] = preview_bytes
                        entry["issue"] = f"primary download skipped/failed ({detail}); used official preview image"
                        entry["primary_download_issue"] = detail
                    else:
                        entry["status"] = "failed"
                        entry["issue"] = (
                            f"{detail}; preview fallback failed: {preview_detail}"
                            if preview_url
                            else detail
                        )
                        warnings.append(f"{asset_id}: official download failed: {entry['issue']}")
        elif provider in {"pexels", "pixabay"}:
            if dry_run:
                entry["status"] = "planned"
                entry["issue"] = "dry run; stock download skipped"
            else:
                status, detail, size = _try_stock_download(
                    provider=provider,
                    scene=scene,
                    beat_plan=beat_plan,
                    output_path=output_path.with_suffix(".mp4"),
                    duration=float(beat_plan.get("duration_seconds") or 7),
                    allow_stock=allow_stock,
                )
                entry["status"] = status
                entry["bytes"] = size
                if status == "downloaded":
                    entry["local_path"] = detail
                else:
                    entry["issue"] = detail
                    if status == "failed":
                        warnings.append(f"{asset_id}: {provider} failed: {detail}")
        elif provider == "runware_flux1":
            if dry_run:
                entry["status"] = "planned"
                entry["issue"] = "dry run; Runware generation skipped"
            else:
                status, detail, size = _try_runware(
                    beat_plan=beat_plan,
                    output_path=output_path.with_suffix(".png"),
                    allow_runware=allow_runware,
                )
                entry["status"] = status
                entry["bytes"] = size
                if status == "generated":
                    entry["local_path"] = detail
                else:
                    entry["issue"] = detail
                    if status == "failed":
                        warnings.append(f"{asset_id}: Runware failed: {detail}")
        else:
            entry["status"] = "task_pending"
            entry["issue"] = f"provider {provider or 'unknown'} requires manual handling"
            warnings.append(f"{asset_id}: provider {provider or 'unknown'} requires manual handling")
        entries.append(entry)

    manifest_status = "dry_run" if dry_run else "complete"
    if any(entry.get("status") == "failed" for entry in entries):
        manifest_status = "blocked"
    elif any(entry.get("status") == "task_pending" for entry in entries):
        manifest_status = "needs_tasks"
    elif any(entry.get("status") == "planned" for entry in entries):
        manifest_status = "planned"

    manifest = {
        "schema_version": ASSET_MANIFEST_VERSION,
        "stage": "asset_production",
        "created_at": _utc_now(),
        "status": manifest_status,
        "dry_run": dry_run,
        "max_download_mb": max_download_mb,
        "entries": entries,
        "imagegen_tasks": imagegen_tasks,
        "remotion_graphic_tasks": remotion_tasks,
        "warnings": warnings,
    }
    asset_qc = _asset_qc(entries, warnings)
    return {
        "asset_manifest": manifest,
        "asset_qc": asset_qc,
        "imagegen_tasks": imagegen_tasks,
        "remotion_graphic_tasks": remotion_tasks,
    }
