"""Final video QC helpers for PodcastV2 Producer Mode."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from producer_contract import file_hash, read_json, sequence_review_passed

from producer_visual_policy import (
    policy_review_warnings,
    policy_warnings,
    visual_policy_report,
)


FINAL_QC_VERSION = 1
EXPECTED_WIDTH = 1920
EXPECTED_HEIGHT = 1080
EXPECTED_FPS = 25.0
MIN_DURATION_SECONDS = 1.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _minimum_render_bytes(duration_seconds: float) -> int:
    duration = max(1.0, float(duration_seconds or 0.0))
    return max(100_000, min(1_000_000, int(duration * 50_000)))


def _parse_ratio(value: str) -> float:
    text = str(value or "")
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            denominator = float(right)
            return float(left) / denominator if denominator else 0.0
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _ffprobe(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return json.loads(result.stdout or "{}"), ""
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _stream(payload: dict[str, Any], codec_type: str) -> dict[str, Any]:
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
            return stream
    return {}


def _format_info(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration = 0.0
    try:
        duration = float(info.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    return {
        "duration_seconds": round(duration, 3),
        "format_name": info.get("format_name", ""),
        "bit_rate": info.get("bit_rate", ""),
        "size": int(info.get("size") or 0),
    }


def _video_info(stream: dict[str, Any]) -> dict[str, Any]:
    fps = _parse_ratio(str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0"))
    return {
        "codec_name": stream.get("codec_name", ""),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "pix_fmt": stream.get("pix_fmt", ""),
        "fps": round(fps, 3),
    }


def _audio_info(stream: dict[str, Any]) -> dict[str, Any]:
    return {
        "codec_name": stream.get("codec_name", ""),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "channel_layout": stream.get("channel_layout", ""),
    }


def build_final_qc(
    *,
    episode_dir: str | Path,
    render_manifest: dict[str, Any] | None = None,
    asset_manifest: dict[str, Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
    render_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    render_manifest = render_manifest if isinstance(render_manifest, dict) else {}
    asset_manifest = asset_manifest if isinstance(asset_manifest, dict) else {}
    tts_manifest = tts_manifest if isinstance(tts_manifest, dict) else {}
    render_preflight = render_preflight if isinstance(render_preflight, dict) else {}

    final_path = Path(str(render_manifest.get("final_video_path") or episode_path / "final.mp4"))
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    def add_check(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})
        if status == "fail":
            errors.append(f"{name}: {detail}")
        elif status == "warn":
            warnings.append(f"{name}: {detail}")

    if not final_path.exists():
        add_check("final_mp4_exists", "fail", f"missing {final_path}")
        return {
            "schema_version": FINAL_QC_VERSION,
            "stage": "final_qc",
            "created_at": _utc_now(),
            "status": "blocked",
            "final_video_path": str(final_path),
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    payload, probe_error = _ffprobe(final_path)
    if not payload:
        add_check("ffprobe", "fail", probe_error)
        return {
            "schema_version": FINAL_QC_VERSION,
            "stage": "final_qc",
            "created_at": _utc_now(),
            "status": "blocked",
            "final_video_path": str(final_path),
            "file_bytes": final_path.stat().st_size,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    fmt = _format_info(payload)
    video = _video_info(_stream(payload, "video"))
    audio = _audio_info(_stream(payload, "audio"))
    expected_duration = float(render_manifest.get("render_duration_seconds") or 0.0)
    if expected_duration <= 0:
        summary = render_preflight.get("summary") if isinstance(render_preflight.get("summary"), dict) else {}
        expected_duration = float(summary.get("render_duration_seconds") or 0.0)
    min_bytes = _minimum_render_bytes(expected_duration or fmt.get("duration_seconds", 0.0))

    add_check(
        "final_mp4_size",
        "pass" if final_path.stat().st_size > min_bytes else "fail",
        f"{final_path.stat().st_size} bytes, minimum {min_bytes}",
    )
    add_check(
        "duration",
        "pass" if fmt["duration_seconds"] >= MIN_DURATION_SECONDS else "fail",
        f"{fmt['duration_seconds']} seconds",
    )
    if expected_duration > 0:
        delta = abs(fmt["duration_seconds"] - expected_duration)
        add_check(
            "duration_matches_manifest",
            "pass" if delta <= max(2.0, expected_duration * 0.03) else "warn",
            f"actual {fmt['duration_seconds']}s, expected {round(expected_duration, 3)}s",
        )
    add_check(
        "video_stream",
        "pass" if video.get("codec_name") else "fail",
        str(video),
    )
    add_check(
        "resolution_16x9",
        "pass"
        if video.get("width") == EXPECTED_WIDTH and video.get("height") == EXPECTED_HEIGHT
        else "fail",
        f"{video.get('width')}x{video.get('height')}",
    )
    add_check(
        "fps",
        "pass" if abs(float(video.get("fps") or 0.0) - EXPECTED_FPS) <= 0.25 else "warn",
        str(video.get("fps")),
    )
    add_check(
        "audio_stream",
        "pass" if audio.get("codec_name") and audio.get("channels", 0) > 0 else "fail",
        str(audio),
    )

    asset_entries = render_preflight.get("render_slots") or (asset_manifest.get("entries") if isinstance(asset_manifest.get("entries"), list) else [])
    if asset_entries:
        visual_policy = visual_policy_report(render_preflight.get("render_slots") or [entry for entry in asset_entries if isinstance(entry, dict)])
        policy_messages = policy_warnings(visual_policy)
        policy_review_messages = policy_review_warnings(visual_policy)
        if sequence_review_passed(episode_path, render_preflight.get("render_slots") or []):
            policy_review_messages = []
        policy_check_status = "pass"
        if visual_policy.get("status") == "blocked":
            policy_check_status = "fail"
        elif policy_review_messages:
            policy_check_status = "warn"
        add_check(
            "visual_source_policy",
            policy_check_status,
            visual_policy.get("summary", ""),
        )
        for message in policy_messages:
            if message not in errors:
                errors.append(message)
        for message in policy_review_messages:
            if message not in warnings:
                warnings.append(message)
        expected_motion_graphic_count = sum(
            1
            for entry in asset_entries
            if isinstance(entry, dict)
            and str(entry.get("provider") or "") == "remotion_graphic"
            and bool(entry.get("motion_graphic_required"))
        )
        props_preview = (
            render_preflight.get("props_preview")
            if isinstance(render_preflight.get("props_preview"), dict)
            else {}
        )
        motion_specs = (
            props_preview.get("producerMotionGraphics")
            if isinstance(props_preview.get("producerMotionGraphics"), list)
            else []
        )
        if expected_motion_graphic_count and len(motion_specs) < expected_motion_graphic_count:
            add_check(
                "motion_graphic_bridge",
                "warn",
                (
                    f"{expected_motion_graphic_count} remotion_graphic assets exist, "
                    f"but {len(motion_specs)} motion specs reached render props."
                ),
            )
        missing_provenance = [
            entry
            for entry in asset_entries
            if isinstance(entry, dict)
            and not (entry.get("source_url") or entry.get("prompt") or entry.get("download_url"))
        ]
        add_check(
            "asset_provenance",
            "pass" if not missing_provenance else "warn",
            f"{len(missing_provenance)} entries missing source/prompt provenance",
        )
    else:
        visual_policy = visual_policy_report([])
        add_check("asset_manifest", "warn", "asset_manifest.json is missing or empty")

    tts_entries = tts_manifest.get("entries") if isinstance(tts_manifest.get("entries"), list) else []
    add_check(
        "tts_manifest",
        "pass" if tts_entries else "warn",
        f"{len(tts_entries)} TTS entries",
    )

    # Decode the whole file: a successful ffprobe does not establish stream integrity.
    try:
        decoded = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(final_path), "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"],
            capture_output=True, text=True, timeout=600, check=False,
        )
        add_check("full_decode", "pass" if decoded.returncode == 0 else "fail", decoded.stderr[-2000:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        add_check("full_decode", "fail", str(exc))
    technical_status = "blocked" if errors else "review" if warnings else "pass"
    output_sha256 = file_hash(final_path)
    acceptance = {}
    for category, filename, mode in (
        ("visual", "visual_qc.json", "video"),
        ("listening", "listening_qc.json", "audio"),
        ("editorial", "editorial_qc.json", "story"),
    ):
        review = read_json(episode_path / filename, {})
        samples = review.get("samples") or []
        valid_samples = bool(samples) and all(
            isinstance(sample, dict) and sample.get("mode") == mode
            and sample.get("observation") and sample.get("status") == "pass"
            and isinstance(sample.get("start_seconds"), (int, float))
            and isinstance(sample.get("end_seconds"), (int, float))
            and 0 <= sample["start_seconds"] < sample["end_seconds"] <= fmt["duration_seconds"] + 0.1
            for sample in samples
        )
        accepted = bool(review.get("status") == "pass" and review.get("reviewer")
                        and review.get("reviewed_at") and review.get("reviewed_sha256") == output_sha256
                        and review.get("coverage_notes") and "unreviewed_ranges" in review
                        and not review.get("unresolved_issues") and valid_samples)
        acceptance[category] = {"status": "pass" if accepted else "review", "artifact": filename,
                                "samples": samples, "unreviewed_ranges": review.get("unreviewed_ranges"),
                                "coverage_notes": review.get("coverage_notes")}
        add_check(f"{category}_acceptance", "pass" if accepted else "warn",
                  f"Current output SHA256 and attributed {mode} observations required in {filename}")
    status = "blocked" if errors else ("review" if warnings else "pass")
    return {
        "schema_version": FINAL_QC_VERSION,
        "stage": "final_qc",
        "created_at": _utc_now(),
        "status": status,
        "technical_status": technical_status,
        "acceptance": acceptance,
        "output_sha256": output_sha256,
        "final_video_path": str(final_path),
        "file_bytes": final_path.stat().st_size,
        "format": fmt,
        "video": video,
        "audio": audio,
        "visual_policy": visual_policy,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
