"""Render orchestration for PodcastV2 Producer Mode.

This module renders through the existing Remotion ``VideoPodcast`` composition
(default) or the minimal documentary renderer (``props["renderer"] == "minimal_doc"``)
without calling ``PodcastV2.render()`` directly. It keeps Producer Mode render
props and logs episode-local so concurrent Studio/PodcastV2 runs are less likely
to collide with this workflow.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from remotion_runtime import remotion_cli_command, remotion_subprocess_env


RENDER_MANIFEST_VERSION = 1
MIN_RENDER_BYTES = 1_000_000
FPS = 25
REMOTION_FRAME_TIMEOUT_MS = 120_000


def _remotion_concurrency() -> int:
    raw = os.environ.get("PRODUCER_REMOTION_CONCURRENCY", "1").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1
    return max(1, value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> Path:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _minimum_render_bytes(duration_seconds: float) -> int:
    duration = max(1.0, float(duration_seconds or 0.0))
    return max(100_000, min(MIN_RENDER_BYTES, int(duration * 50_000)))


def _run_subprocess(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int | None = None,
    log_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    if log_path:
        _ensure_dir(log_path.parent)
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\n[{_utc_now()}] RUN {' '.join(args)}\n")
            subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                check=True,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                env=env,
            )
        return
    subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        env=env,
    )


def _run_shell_command(
    command: str,
    *,
    cwd: Path,
    timeout_seconds: int,
    log_path: Path,
) -> None:
    _ensure_dir(log_path.parent)
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n[{_utc_now()}] RUN {command}\n")
        subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            check=True,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )


def _concat_scene_audio(
    *,
    episode_dir: Path,
    scene_count: int,
    force: bool,
    log_path: Path,
) -> Path:
    output_path = episode_dir / "merged_audio.wav"
    if output_path.exists() and output_path.stat().st_size > 100_000 and not force:
        return output_path

    concat_path = episode_dir / "audio_concat.txt"
    lines = []
    for index in range(scene_count):
        wav = (episode_dir / f"scene_{index:02d}.wav").resolve()
        lines.append(f"file '{str(wav).replace(chr(92), '/')}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    _run_subprocess(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(output_path),
        ],
        log_path=log_path,
    )
    if not output_path.exists() or output_path.stat().st_size <= 100_000:
        raise RuntimeError("merged_audio.wav was not created or is too small")
    return output_path


def _resolve_background_bed_path(root_dir: Path, configured_path: str) -> str:
    path = str(configured_path or "").strip()
    if not path:
        return ""
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str((root_dir / path).resolve())


def _find_background_bed_candidate(root_dir: Path) -> str:
    songs_dir = root_dir / "Songs"
    if not songs_dir.is_dir():
        return ""
    candidates = [
        path
        for path in songs_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    ]
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (item.stat().st_mtime, item.stat().st_size), reverse=True)
    return str(candidates[0])


def _background_settings() -> dict[str, Any]:
    try:
        from config import get_podcast_background_bed_settings

        return get_podcast_background_bed_settings()
    except Exception:  # noqa: BLE001
        return {}


def _mix_background_bed(
    *,
    root_dir: Path,
    episode_dir: Path,
    narration_audio: Path,
    total_duration: float,
    narration_pad_seconds: float,
    force: bool,
    log_path: Path,
) -> tuple[Path, dict[str, Any]]:
    settings = _background_settings()
    enabled = bool(settings.get("background_bed_enabled", False))
    env_enabled = os.environ.get("PODCAST_BACKGROUND_BED_ENABLED")
    if env_enabled is not None:
        enabled = env_enabled.strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return narration_audio, {"enabled": False, "status": "disabled"}

    bed_path = os.environ.get("PODCAST_BACKGROUND_BED_PATH") or str(
        settings.get("background_bed_path", "")
    )
    bed_path = _resolve_background_bed_path(root_dir, bed_path)
    if not bed_path or not Path(bed_path).exists():
        fallback = _find_background_bed_candidate(root_dir)
        if not fallback:
            return narration_audio, {"enabled": True, "status": "missing_bed_file"}
        bed_path = fallback

    output_path = episode_dir / "merged_audio_with_bed.wav"
    if output_path.exists() and output_path.stat().st_size > 100_000 and not force:
        return output_path, {"enabled": True, "status": "reused", "bed_path": bed_path}
    if output_path.exists():
        output_path.unlink()

    volume_db = float(settings.get("background_bed_volume_db", -16.0))
    ducking_ratio = float(settings.get("background_bed_ducking_ratio", 2.0))
    fade_seconds = float(settings.get("background_bed_fade_seconds", 2.0))
    fade_seconds = max(0.0, min(fade_seconds, max(0.0, total_duration / 2)))
    fade_out_start = max(0.0, total_duration - fade_seconds)

    bed_filters = [
        f"atrim=0:{total_duration:.3f}",
        "asetpts=PTS-STARTPTS",
        f"volume={volume_db:.1f}dB",
    ]
    if fade_seconds > 0:
        bed_filters.append(f"afade=t=in:st=0:d={fade_seconds:.3f}")
        bed_filters.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_seconds:.3f}")

    filter_complex = (
        f"[0:a]apad=pad_dur={max(0.0, narration_pad_seconds):.3f},"
        "asetpts=PTS-STARTPTS,asplit=2[narr_mix][narr_side];"
        f"[1:a]{','.join(bed_filters)}[bed];"
        f"[bed][narr_side]sidechaincompress=threshold=0.025:ratio={ducking_ratio:.2f}:"
        "attack=80:release=900:makeup=1[ducked];"
        "[narr_mix][ducked]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[out]"
    )

    try:
        _run_subprocess(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(narration_audio),
                "-stream_loop",
                "-1",
                "-i",
                bed_path,
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ],
            log_path=log_path,
        )
    except Exception as exc:  # noqa: BLE001
        return narration_audio, {
            "enabled": True,
            "status": "mix_failed",
            "bed_path": bed_path,
            "error": str(exc),
        }
    if not output_path.exists() or output_path.stat().st_size <= 100_000:
        return narration_audio, {"enabled": True, "status": "invalid_output", "bed_path": bed_path}
    return output_path, {"enabled": True, "status": "mixed", "bed_path": bed_path}


def _sfx_filter_complex(cues: list[dict[str, Any]], *, sample_rate: int, channel_layout: str) -> str:
    """Build the ffmpeg graph mixing input 0 (prepared audio) with one input per cue (inputs 1..n)."""
    fmt = f"aformat=sample_rates={sample_rate}:channel_layouts={channel_layout}"
    parts = [f"[0:a]{fmt}[base]"]
    labels = ["[base]"]
    for index, cue in enumerate(cues, start=1):
        filters = [fmt]
        duration = float(cue.get("duration_seconds") or 0.0)
        if duration > 0:
            filters.append(f"atrim=0:{duration:.3f}")
        filters.append("asetpts=PTS-STARTPTS")
        fade_in = float(cue.get("fade_in_seconds") or 0.0)
        fade_out = float(cue.get("fade_out_seconds") or 0.0)
        if fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in:.3f}")
        if fade_out > 0 and duration > fade_out:
            filters.append(f"afade=t=out:st={duration - fade_out:.3f}:d={fade_out:.3f}")
        filters.append(f"volume={float(cue.get('gain_db', -12.0)):.1f}dB")
        delay_ms = int(round(float(cue["start_seconds"]) * 1000))
        filters.append(f"adelay={delay_ms}:all=1")
        parts.append(f"[{index}:a]{','.join(filters)}[sfx{index}]")
        labels.append(f"[sfx{index}]")
    parts.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95:level=disabled[out]"
    )
    return ";".join(parts)


def _mix_sfx_cues(*, episode_dir: Path, audio_path: Path, log_path: Path) -> tuple[Path, dict[str, Any]]:
    """Mix optional episode-local sound effects from sfx_cues.json over the prepared audio."""
    cues_path = episode_dir / "sfx_cues.json"
    if not cues_path.is_file():
        return audio_path, {"status": "none"}
    cues = json.loads(cues_path.read_text(encoding="utf-8")).get("cues") or []
    missing = [str(cue.get("path")) for cue in cues if not (episode_dir / str(cue.get("path"))).is_file()]
    if missing:
        raise RuntimeError(f"sfx_cues.json references missing files: {missing}")
    if not cues:
        return audio_path, {"status": "none"}
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channel_layout,channels",
         "-of", "json", str(audio_path)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    layout = stream.get("channel_layout") or ("stereo" if int(stream.get("channels", 1)) > 1 else "mono")
    output_path = episode_dir / "merged_audio_with_sfx.wav"
    command = ["ffmpeg", "-y", "-i", str(audio_path)]
    for cue in cues:
        command += ["-i", str(episode_dir / str(cue["path"]))]
    command += [
        "-filter_complex", _sfx_filter_complex(cues, sample_rate=int(stream["sample_rate"]), channel_layout=layout),
        "-map", "[out]", "-c:a", "pcm_s16le", str(output_path),
    ]
    _run_subprocess(command, log_path=log_path)
    if not output_path.exists() or output_path.stat().st_size <= 100_000:
        raise RuntimeError("merged_audio_with_sfx.wav was not created or is too small")
    return output_path, {"status": "mixed", "cue_count": len(cues), "cues_path": str(cues_path)}


def _normalize_rendered_audio(
    input_path: Path,
    output_path: Path,
    log_path: Path,
    min_video_bytes: int,
) -> None:
    temp_output = Path(str(output_path) + ".tmp.mp4")
    if temp_output.exists():
        temp_output.unlink()
    _run_subprocess(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
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
            str(temp_output),
        ],
        log_path=log_path,
    )
    if not temp_output.exists() or temp_output.stat().st_size <= min_video_bytes:
        raise RuntimeError("audio normalization did not create a valid final video")
    os.replace(temp_output, output_path)


def _stage_file(source: str, assets_dir: Path, staged_files: list[Path]) -> str:
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"render asset missing: {source}")
    suffix = source_path.suffix or ".bin"
    target = assets_dir / f"producer_{uuid.uuid4().hex}{suffix}"
    _ensure_dir(target.parent)
    shutil.copy2(source_path, target)
    staged_files.append(target)
    return f"assets/{target.name}"


def _stage_podcast_props(
    *,
    raw_props: dict[str, Any],
    remotion_dir: Path,
) -> tuple[dict[str, Any], list[Path]]:
    assets_dir = remotion_dir / "public" / "assets"
    staged_files: list[Path] = []
    resolved = {
        "imagePaths": [
            _stage_file(str(path), assets_dir, staged_files)
            for path in raw_props.get("imagePaths", [])
        ],
        "audioPath": _stage_file(str(raw_props.get("audioPath", "")), assets_dir, staged_files),
        "sceneDurations": raw_props.get("sceneDurations", []),
        "sceneTitles": raw_props.get("sceneTitles", []),
        "durationInSeconds": int(float(raw_props.get("durationInSeconds") or 0) + 0.999),
        "sceneImageCounts": raw_props.get("sceneImageCounts", []),
        "sceneAssetTypes": raw_props.get("sceneAssetTypes", []),
        "sceneAssetQualifications": raw_props.get("sceneAssetQualifications", []),
        "sceneAssetCredits": raw_props.get("sceneAssetCredits", []),
        "sceneAssetFits": raw_props.get("sceneAssetFits", []),
        "sceneAssetDurations": raw_props.get("sceneAssetDurations", []),
        "producerMotionGraphics": raw_props.get("producerMotionGraphics", []),
        "glossaryEntries": raw_props.get("glossaryEntries", []),
    }
    if raw_props.get("scene0VideoPath"):
        resolved["scene0VideoPath"] = _stage_file(
            str(raw_props.get("scene0VideoPath")),
            assets_dir,
            staged_files,
        )
    return resolved, staged_files


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def _render_remotion(
    *,
    root_dir: Path,
    raw_props: dict[str, Any],
    timeout_seconds: int,
    log_path: Path,
) -> dict[str, Any]:
    remotion_dir = root_dir / "remotion"
    output_candidate = Path(str(raw_props.get("outputPath") or ""))
    if not output_candidate.is_absolute():
        output_candidate = root_dir / output_candidate
    render_tmp_dir = output_candidate.resolve().parent / "remotion_tmp"
    _ensure_dir(render_tmp_dir)
    resolved_props, staged_files = _stage_podcast_props(raw_props=raw_props, remotion_dir=remotion_dir)
    resolved_props_path = remotion_dir / f".producer-render-props-{uuid.uuid4().hex}.json"
    _write_json(resolved_props_path, resolved_props)
    output_path = str(raw_props.get("outputPath", "")).replace("\\", "/")
    props_path = str(resolved_props_path.resolve()).replace("\\", "/")
    command = remotion_cli_command(
        remotion_dir,
        "render",
        "src/Root.tsx",
        "VideoPodcast",
        output_path,
        f"--props={props_path}",
        f"--fps={FPS}",
        "--codec=h264",
        "--pixel-format=yuv420p",
        "--image-format=png",
        "--crf=18",
        f"--concurrency={_remotion_concurrency()}",
        f"--timeout={REMOTION_FRAME_TIMEOUT_MS}",
        "--overwrite",
    )
    try:
        # Long podcast renders can leave Remotion's initially-empty temp
        # subdirectories idle long enough for Windows temp cleanup to remove
        # them before the final audio preprocessing step. Keep this render's
        # temp tree episode-local and stable for the whole subprocess lifetime.
        render_env = remotion_subprocess_env(command[0])
        render_env["TEMP"] = str(render_tmp_dir.resolve())
        render_env["TMP"] = str(render_tmp_dir.resolve())
        _run_subprocess(
            command,
            cwd=remotion_dir,
            timeout_seconds=timeout_seconds,
            log_path=log_path,
            env=render_env,
        )
    finally:
        _cleanup(staged_files + [resolved_props_path])
    return {
        "command": " ".join(command),
        "output_path": output_path,
        "props_path": props_path,
        "temp_dir": str(render_tmp_dir.resolve()),
    }


def orchestrate_render(
    *,
    root_dir: str | Path,
    episode_dir: str | Path,
    preflight: dict[str, Any],
    no_render: bool = False,
    force: bool = False,
    timeout_seconds: int = 7200,
) -> dict[str, Any]:
    root_path = Path(root_dir)
    episode_path = Path(episode_dir)
    log_path = episode_path / "producer_render.log"
    raw_final_path = episode_path / "final_unnormalized.mp4"
    final_path = episode_path / "final.mp4"
    render_props_path = episode_path / "render_props.json"
    errors: list[str] = []
    warnings: list[str] = []

    if preflight.get("status") != "ready":
        return {
            "schema_version": RENDER_MANIFEST_VERSION,
            "stage": "render",
            "created_at": _utc_now(),
            "status": "blocked",
            "no_render": no_render,
            "errors": [f"render preflight is {preflight.get('status')}"],
            "warnings": warnings,
        }

    authorization_attempt = None
    if not no_render:
        from producer_contract import validate_render_authorization, read_json
        try:
            authorization_attempt = validate_render_authorization(episode_path, preflight, root_path)
        except (ValueError, TypeError, KeyError) as exc:
            return {"stage": "render", "status": "blocked", "no_render": False, "errors": [str(exc)], "warnings": []}
    if not no_render and final_path.exists() and final_path.stat().st_size > _minimum_render_bytes(0) and not force:
        previous = read_json(episode_path / "render_manifest.json", {})
        if previous.get("revision") != authorization_attempt["revision"]:
            return {"stage": "render", "status": "blocked", "errors": ["Existing final belongs to another or unknown revision; use a separate output folder or explicitly replace it."], "warnings": []}
        return {
            **previous,
            "schema_version": RENDER_MANIFEST_VERSION,
            "stage": "render",
            "created_at": _utc_now(),
            "status": "complete",
            "result": "skipped_existing_final",
            "revision": authorization_attempt["revision"],
            "final_video_path": str(final_path),
            "final_video_bytes": final_path.stat().st_size,
            "no_render": no_render,
            "errors": errors,
            "warnings": warnings,
        }

    summary = preflight.get("summary") if isinstance(preflight.get("summary"), dict) else {}
    scene_count = int(summary.get("scene_count") or 0)
    render_duration = float(summary.get("render_duration_seconds") or 0.0)
    outro_hold_seconds = float(summary.get("outro_hold_seconds") or 0.0)
    raw_props = dict(preflight.get("props_preview") or {})
    if not raw_props:
        errors.append("preflight props_preview is missing")
    if scene_count <= 0:
        errors.append("scene_count must be greater than zero")
    if errors:
        return {
            "schema_version": RENDER_MANIFEST_VERSION,
            "stage": "render",
            "created_at": _utc_now(),
            "status": "blocked",
            "no_render": no_render,
            "errors": errors,
            "warnings": warnings,
        }

    if not no_render and not Path(str(raw_props.get("audioPath") or "")).is_file():
        return {"stage": "render", "status": "blocked", "errors": ["Prepare the final audio mix before authorization"], "warnings": []}
    if not no_render and raw_final_path.exists() and force:
        raw_final_path.unlink()
    if not no_render and final_path.exists() and force:
        final_path.unlink()

    if no_render:
        merged_audio = _concat_scene_audio(
            episode_dir=episode_path, scene_count=scene_count, force=True, log_path=log_path,
        )
        render_audio, bed_result = _mix_background_bed(
            root_dir=root_path, episode_dir=episode_path, narration_audio=merged_audio,
            total_duration=render_duration, narration_pad_seconds=outro_hold_seconds,
            force=True, log_path=log_path,
        )
        render_audio, bed_result["sfx"] = _mix_sfx_cues(
            episode_dir=episode_path, audio_path=render_audio, log_path=log_path,
        )
    else:
        # Execute the prepared and approved audio, never silently rebuild the mix.
        merged_audio = episode_path / "merged_audio.wav"
        render_audio = Path(str(raw_props.get("audioPath") or ""))
        if not render_audio.is_file():
            return {"stage": "render", "status": "blocked", "errors": ["Prepare the final audio mix with --no-render before authorization"], "warnings": []}
        bed_result = {"status": "approved_prepared_audio"}
    raw_props["audioPath"] = str(render_audio.resolve())
    raw_props["outputPath"] = str(raw_final_path.resolve())
    _write_json(render_props_path, raw_props)

    manifest: dict[str, Any] = {
        "schema_version": RENDER_MANIFEST_VERSION,
        "stage": "render",
        "created_at": _utc_now(),
        "status": "prepared" if no_render else "in_progress",
        "no_render": no_render,
        "force": force,
        "render_props_path": str(render_props_path),
        "log_path": str(log_path),
        "merged_audio_path": str(merged_audio),
        "render_audio_path": str(render_audio),
        "background_bed": bed_result,
        "raw_video_path": str(raw_final_path),
        "final_video_path": str(final_path),
        "renderer": raw_props.get("renderer", "remotion"),
        "scene_count": scene_count,
        "render_duration_seconds": render_duration,
        "estimated_frames": summary.get("estimated_frames", 0),
        "errors": errors,
        "warnings": warnings,
        "revision": authorization_attempt["revision"] if authorization_attempt else None,
    }
    if no_render:
        return manifest

    _write_json(episode_path / "render_attempts.json", authorization_attempt)
    min_render_bytes = _minimum_render_bytes(render_duration)
    try:
        if raw_props.get("renderer") == "minimal_doc":
            from producer_minimal_renderer import render_minimal_doc

            render_result = render_minimal_doc(
                root_dir=root_path,
                episode_dir=episode_path,
                raw_props=raw_props,
                narration_end=render_duration - outro_hold_seconds,
                timeout_seconds=timeout_seconds,
                log_path=log_path,
            )
        else:
            render_result = _render_remotion(
                root_dir=root_path,
                raw_props=raw_props,
                timeout_seconds=timeout_seconds,
                log_path=log_path,
            )
        manifest["render_result"] = render_result
        if not raw_final_path.exists() or raw_final_path.stat().st_size <= min_render_bytes:
            raise RuntimeError("final_unnormalized.mp4 was not created or is too small")
        _normalize_rendered_audio(raw_final_path, final_path, log_path, min_render_bytes)
        if raw_final_path.exists():
            raw_final_path.unlink()
        if not final_path.exists() or final_path.stat().st_size <= min_render_bytes:
            raise RuntimeError("final.mp4 was not created or is too small")
        manifest["status"] = "complete"
        manifest["final_video_bytes"] = final_path.stat().st_size
        manifest["completed_at"] = _utc_now()
    except Exception as exc:  # noqa: BLE001
        manifest["status"] = "blocked"
        manifest["errors"] = errors + [str(exc)]
        manifest["failed_at"] = _utc_now()
    return manifest
