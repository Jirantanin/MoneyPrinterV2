"""Render preflight checks for PodcastV2 Producer Mode.

This stage mirrors the existing PodcastV2 Remotion render contract without
starting a render. It verifies scene audio, scene assets, Remotion project
presence, and produces a render props preview that the next orchestration stage
can use as its checklist.
"""

from __future__ import annotations

import json
import re
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RENDER_PREFLIGHT_VERSION = 1
MIN_AUDIO_SECONDS = 0.25
MIN_MEDIA_BYTES = 1024
FPS = 25
IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp")
VIDEO_EXTENSIONS = ("mp4", "webm", "mov", "m4v")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _safe_title(scene: dict[str, Any], fallback: str) -> str:
    section_title = _clean_text(scene.get("section_title"))
    scene_title = _clean_text(scene.get("scene_title"))
    return (scene_title or section_title or fallback)[:100]


def _load_episode_glossary_entries(episode_path: Path) -> list[dict[str, Any]]:
    path = episode_path / "glossary_entries.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []

    entries = payload.get("entries") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return []

    clean_entries: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        term = _clean_text(item.get("term"))
        meaning = _clean_text(item.get("meaning"))
        if not term or not meaning:
            continue
        try:
            start = max(0.0, float(item.get("start", 0)))
        except (TypeError, ValueError):
            start = 0.0
        try:
            duration = max(1.0, float(item.get("duration", 5)))
        except (TypeError, ValueError):
            duration = 5.0
        clean_entries.append(
            {
                "term": term[:80],
                "meaning": meaning[:180],
                "start": round(start, 3),
                "duration": round(duration, 3),
            }
        )
    return clean_entries


def _wav_info(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "missing wav file"
    if path.stat().st_size <= 44:
        return None, "wav file is empty or header-only"
    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
        duration = frames / sample_rate if sample_rate else 0.0
        if duration < MIN_AUDIO_SECONDS:
            return None, f"wav duration is too short ({duration:.3f}s)"
        return {
            "path": str(path),
            "exists": True,
            "bytes": path.stat().st_size,
            "duration_seconds": round(duration, 3),
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": sample_width,
        }, ""
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _asset_info(path: Path, asset_type: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "type": asset_type,
        "bytes": path.stat().st_size if path.exists() else 0,
        "exists": path.exists(),
    }


def _find_scene_asset(
    episode_dir: Path,
    scene_num: str,
    asset_index: int,
    *,
    render_image_only: bool = False,
) -> tuple[Path | None, str]:
    stem = f"scene_{scene_num}_{asset_index}"
    for ext in IMAGE_EXTENSIONS:
        candidate = episode_dir / f"{stem}.{ext}"
        if candidate.exists():
            return candidate, "image"
    if not render_image_only:
        for ext in VIDEO_EXTENSIONS:
            candidate = episode_dir / f"{stem}.{ext}"
            if candidate.exists():
                return candidate, "video"
    return None, ""


def _manifest_asset_type(entry: dict[str, Any], path: Path) -> str:
    media_type = str(entry.get("media_type") or "").lower()
    suffix = path.suffix.lower().lstrip(".")
    if media_type == "video" or suffix in VIDEO_EXTENSIONS:
        return "video"
    return "image"


def _group_manifest_assets(asset_entries: list[Any]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for entry in asset_entries:
        if not isinstance(entry, dict):
            continue
        try:
            scene_index = int(entry.get("scene_index"))
            asset_index = int(entry.get("asset_index", 0) or 0)
        except (TypeError, ValueError):
            continue
        local_path = str(entry.get("local_path") or "").strip()
        status = str(entry.get("status") or "").lower()
        if not local_path or status not in {"downloaded", "generated", "skipped_existing"}:
            continue
        item = dict(entry)
        item["_asset_index"] = asset_index
        grouped.setdefault(scene_index, []).append(item)
    for entries in grouped.values():
        entries.sort(key=lambda item: int(item.get("_asset_index", 0) or 0))
    return grouped


def _collect_manifest_assets(
    entries: list[dict[str, Any]],
    *,
    render_image_only: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    assets: list[dict[str, Any]] = []
    for entry in entries:
        path = Path(str(entry.get("local_path") or ""))
        asset_type = _manifest_asset_type(entry, path)
        if render_image_only and asset_type == "video":
            continue
        if not path.exists():
            return assets, f"{path.name or entry.get('local_path')} is missing"
        if path.stat().st_size <= MIN_MEDIA_BYTES:
            return assets, f"{path.name} is too small"
        info = _asset_info(path.resolve(), asset_type)
        info["asset_index"] = int(entry.get("asset_index", len(assets)) or 0)
        motion_graphic = entry.get("motion_graphic")
        if isinstance(motion_graphic, dict):
            info["motion_graphic"] = motion_graphic
        assets.append(info)
    return assets, ""


def _collect_scene_assets(
    episode_dir: Path,
    scene_index: int,
    *,
    render_image_only: bool = False,
    manifest_entries: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    scene_num = f"{scene_index:02d}"
    if manifest_entries:
        manifest_assets, manifest_issue = _collect_manifest_assets(
            manifest_entries,
            render_image_only=render_image_only,
        )
        if manifest_assets or manifest_issue:
            return manifest_assets, manifest_issue

    assets: list[dict[str, Any]] = []
    asset_index = 0
    while True:
        asset_path, asset_type = _find_scene_asset(
            episode_dir,
            scene_num,
            asset_index,
            render_image_only=render_image_only,
        )
        if not asset_path:
            break
        if asset_path.stat().st_size <= MIN_MEDIA_BYTES:
            return assets, f"{asset_path.name} is too small"
        assets.append(_asset_info(asset_path.resolve(), asset_type))
        asset_index += 1

    if not assets:
        for ext in IMAGE_EXTENSIONS:
            legacy = episode_dir / f"scene_{scene_num}.{ext}"
            if legacy.exists():
                if legacy.stat().st_size <= MIN_MEDIA_BYTES:
                    return assets, f"{legacy.name} is too small"
                assets.append(_asset_info(legacy.resolve(), "image"))
                break
        if not assets:
            return assets, (
                f"missing scene_{scene_num}_0 image"
                + (" or video" if not render_image_only else "")
            )
    return assets, ""


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return fallback


def _remotion_checks(root_dir: Path) -> list[dict[str, Any]]:
    remotion_dir = root_dir / "remotion"
    checks = [
        ("remotion_dir", remotion_dir),
        ("package_json", remotion_dir / "package.json"),
        ("render_script", remotion_dir / "scripts" / "render.mjs"),
        ("root_composition", remotion_dir / "src" / "Root.tsx"),
        ("podcast_component", remotion_dir / "src" / "VideoPodcast.tsx"),
    ]
    results: list[dict[str, Any]] = []
    for name, path in checks:
        results.append(
            {
                "name": name,
                "path": str(path),
                "status": "pass" if path.exists() else "missing",
            }
        )
    root_file = remotion_dir / "src" / "Root.tsx"
    if root_file.exists():
        text = root_file.read_text(encoding="utf-8", errors="replace")
        results.append(
            {
                "name": "composition_id",
                "path": str(root_file),
                "status": "pass" if 'id="VideoPodcast"' in text else "missing",
                "detail": "VideoPodcast",
            }
        )
    return results


def _status_from_issues(
    *,
    missing_audio: int,
    missing_assets: int,
    remotion_missing: int,
) -> str:
    if remotion_missing:
        return "blocked"
    if missing_audio and missing_assets:
        return "blocked"
    if missing_audio:
        return "needs_audio"
    if missing_assets:
        return "needs_assets"
    return "ready"


def build_render_preflight(
    *,
    root_dir: str | Path,
    episode_dir: str | Path,
    script: list[Any],
    asset_manifest: dict[str, Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
    render_image_only: bool = False,
) -> dict[str, Any]:
    root_path = Path(root_dir)
    episode_path = Path(episode_dir)
    scenes = [scene for scene in script if isinstance(scene, dict)]
    errors: list[str] = []
    warnings: list[str] = []

    if not scenes:
        errors.append("script.json has no renderable scenes")

    remotion_checks = _remotion_checks(root_path)
    remotion_missing = sum(1 for item in remotion_checks if item.get("status") != "pass")
    if remotion_missing:
        errors.append("Remotion project files are missing or incomplete")

    asset_entries = (
        asset_manifest.get("entries", [])
        if isinstance(asset_manifest, dict) and isinstance(asset_manifest.get("entries"), list)
        else []
    )
    tts_entries = (
        tts_manifest.get("entries", [])
        if isinstance(tts_manifest, dict) and isinstance(tts_manifest.get("entries"), list)
        else []
    )
    if not asset_entries:
        warnings.append("asset_manifest.json is missing or has no entries")
    if not tts_entries:
        warnings.append("tts_manifest.json is missing or has no entries")
    manifest_assets_by_scene = _group_manifest_assets(asset_entries)

    scene_reports: list[dict[str, Any]] = []
    image_paths: list[str] = []
    scene_asset_types: list[str] = []
    scene_image_counts: list[int] = []
    producer_motion_graphics: list[dict[str, Any]] = []
    scene_durations: list[float] = []
    scene_titles: list[str] = []
    missing_audio = 0
    missing_assets = 0

    for index, scene in enumerate(scenes):
        scene_num = f"{index:02d}"
        wav_path = episode_path / f"scene_{scene_num}.wav"
        audio_info, audio_issue = _wav_info(wav_path)
        if not audio_info:
            missing_audio += 1

        assets, asset_issue = _collect_scene_assets(
            episode_path,
            index,
            render_image_only=render_image_only,
            manifest_entries=manifest_assets_by_scene.get(index, []),
        )
        if asset_issue:
            missing_assets += 1

        duration = float(audio_info.get("duration_seconds", 0.0)) if audio_info else 0.0
        if audio_info:
            scene_durations.append(duration)
        else:
            scene_durations.append(0.0)
        scene_titles.append(_safe_title(scene, f"Scene {index + 1}"))
        scene_image_counts.append(len(assets))
        for asset in assets:
            image_paths.append(str(Path(str(asset["path"])).resolve()))
            scene_asset_types.append(str(asset["type"]))
            motion_graphic = asset.get("motion_graphic")
            if isinstance(motion_graphic, dict):
                motion_spec = dict(motion_graphic)
                motion_spec.setdefault("sceneIndex", index)
                motion_spec.setdefault("assetIndex", int(asset.get("asset_index", 0) or 0))
                producer_motion_graphics.append(motion_spec)

        status = "pass"
        issues: list[str] = []
        if audio_issue:
            issues.append(f"audio: {audio_issue}")
        if asset_issue:
            issues.append(f"assets: {asset_issue}")
        if issues:
            status = "blocked"
        scene_reports.append(
            {
                "scene_index": index,
                "scene_title": scene.get("scene_title", ""),
                "section_title": scene.get("section_title", ""),
                "status": status,
                "audio": audio_info or {"path": str(wav_path), "exists": False},
                "assets": assets,
                "issues": issues,
            }
        )

    narration_duration = round(sum(scene_durations), 3)
    try:
        from config import get_podcast_outro_hold_seconds

        outro_hold_seconds = max(0.0, float(get_podcast_outro_hold_seconds()))
    except Exception:  # noqa: BLE001
        outro_hold_seconds = 0.0
    render_duration = round(narration_duration + outro_hold_seconds, 3)

    render_scene_durations = list(scene_durations)
    if outro_hold_seconds > 0 and render_scene_durations:
        render_scene_durations[-1] = round(render_scene_durations[-1] + outro_hold_seconds, 3)

    scene_asset_durations: list[float] = []
    for index, count in enumerate(scene_image_counts):
        if count <= 0:
            continue
        duration = render_scene_durations[index] if index < len(render_scene_durations) else 0.0
        per_asset = duration / count if duration > 0 else 0.0
        scene_asset_durations.extend([round(per_asset, 3)] * count)

    merged_audio_path = episode_path / "merged_audio.wav"
    render_audio_path = (
        episode_path / "merged_audio_with_bed.wav"
        if (episode_path / "merged_audio_with_bed.wav").exists()
        else merged_audio_path
    )
    raw_output_path = episode_path / "final_unnormalized.mp4"
    final_output_path = episode_path / "final.mp4"
    glossary_entries = _load_episode_glossary_entries(episode_path)

    props_preview = {
        "composition": "VideoPodcast",
        "imagePaths": image_paths,
        "audioPath": str(render_audio_path.resolve()),
        "sceneDurations": render_scene_durations,
        "sceneTitles": scene_titles,
        "durationInSeconds": render_duration,
        "outputPath": str(raw_output_path.resolve()),
        "sceneImageCounts": scene_image_counts,
        "sceneAssetTypes": scene_asset_types,
        "sceneAssetDurations": scene_asset_durations,
        "producerMotionGraphics": producer_motion_graphics,
        "glossaryEntries": glossary_entries,
    }
    scene0_video = episode_path / "scene_00.mp4"
    if scene0_video.exists():
        props_preview["scene0VideoPath"] = str(scene0_video.resolve())

    status = _status_from_issues(
        missing_audio=missing_audio,
        missing_assets=missing_assets,
        remotion_missing=remotion_missing,
    )
    if missing_audio:
        errors.append(f"{missing_audio} scenes are missing valid audio")
    if missing_assets:
        errors.append(f"{missing_assets} scenes are missing valid visual assets")

    return {
        "schema_version": RENDER_PREFLIGHT_VERSION,
        "stage": "render_preflight",
        "created_at": _utc_now(),
        "status": status,
        "episode_dir": str(episode_path),
        "render_image_only": render_image_only,
        "summary": {
            "scene_count": len(scenes),
            "ready_scene_count": sum(1 for item in scene_reports if item.get("status") == "pass"),
            "missing_audio_count": missing_audio,
            "missing_asset_count": missing_assets,
            "asset_count": len(image_paths),
            "narration_duration_seconds": narration_duration,
            "outro_hold_seconds": outro_hold_seconds,
            "render_duration_seconds": render_duration,
            "estimated_frames": int(round(render_duration * FPS)),
            "remotion_missing_count": remotion_missing,
            "final_output_path": str(final_output_path.resolve()),
            "raw_output_path": str(raw_output_path.resolve()),
        },
        "render_contract": {
            "composition": "VideoPodcast",
            "fps": FPS,
            "requires": [
                "script.json",
                "scene_NN.wav for every scene",
                "scene_NN_0 image or video for every scene",
                "remotion/scripts/render.mjs",
                "remotion/src/Root.tsx composition id VideoPodcast",
            ],
            "planned_props_file": str((root_path / "remotion" / ".render-props-podcast.json").resolve()),
            "planned_merged_audio_path": str(merged_audio_path.resolve()),
            "planned_render_audio_path": str(render_audio_path.resolve()),
        },
        "remotion_checks": remotion_checks,
        "scenes": scene_reports,
        "props_preview": props_preview,
        "warnings": warnings,
        "errors": errors,
    }
