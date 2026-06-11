"""Audio signal QC for PodcastV2 Producer Mode scene WAV files."""

from __future__ import annotations

import math
import re
import sys
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIO_QC_VERSION = 1
EXPECTED_SAMPLE_RATE = 24_000
EXPECTED_CHANNELS = 1
EXPECTED_SAMPLE_WIDTH = 2
MIN_DURATION_SECONDS = 0.25
SILENCE_DBFS = -50.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _dbfs(value: float, maximum: float) -> float | None:
    if value <= 0 or maximum <= 0:
        return None
    return round(20.0 * math.log10(value / maximum), 3)


def _samples_from_pcm(raw: bytes, sample_width: int) -> tuple[list[int], int]:
    if sample_width == 1:
        return [byte - 128 for byte in raw], 128

    if sample_width == 2:
        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        return list(samples), 32768

    if sample_width == 4:
        samples = array("i")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        return list(samples), 2147483648

    return [], 0


def _edge_silence_seconds(samples: list[int], channels: int, sample_rate: int, threshold: int) -> tuple[float, float]:
    if not samples or channels <= 0 or sample_rate <= 0:
        return 0.0, 0.0

    leading = 0
    for sample in samples:
        if abs(sample) > threshold:
            break
        leading += 1

    trailing = 0
    for sample in reversed(samples):
        if abs(sample) > threshold:
            break
        trailing += 1

    samples_per_second = sample_rate * channels
    return (
        round(leading / samples_per_second, 3),
        round(trailing / samples_per_second, 3),
    )


def _scene_status(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "blocked"
    if warnings:
        return "review"
    return "pass"


def inspect_wav(path: str | Path) -> dict[str, Any]:
    wav_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []

    if not wav_path.exists():
        return {
            "path": str(wav_path),
            "exists": False,
            "status": "blocked",
            "errors": ["missing wav file"],
            "warnings": [],
        }
    if wav_path.stat().st_size <= 44:
        return {
            "path": str(wav_path),
            "exists": True,
            "bytes": wav_path.stat().st_size,
            "status": "blocked",
            "errors": ["wav file is empty or header-only"],
            "warnings": [],
        }

    try:
        with wave.open(str(wav_path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frames = wav.getnframes()
            raw = wav.readframes(frames)
    except Exception as exc:  # noqa: BLE001
        return {
            "path": str(wav_path),
            "exists": True,
            "bytes": wav_path.stat().st_size,
            "status": "blocked",
            "errors": [f"cannot read wav: {exc}"],
            "warnings": [],
        }

    duration = frames / sample_rate if sample_rate else 0.0
    if duration < MIN_DURATION_SECONDS:
        errors.append(f"duration too short: {duration:.3f}s")
    if sample_rate != EXPECTED_SAMPLE_RATE:
        warnings.append(f"sample_rate {sample_rate} differs from expected {EXPECTED_SAMPLE_RATE}")
    if channels != EXPECTED_CHANNELS:
        warnings.append(f"channels {channels} differs from expected {EXPECTED_CHANNELS}")
    if sample_width != EXPECTED_SAMPLE_WIDTH:
        warnings.append(f"sample_width {sample_width} differs from expected {EXPECTED_SAMPLE_WIDTH}")

    samples, max_amplitude = _samples_from_pcm(raw, sample_width)
    sample_count = len(samples)
    if not samples or max_amplitude <= 0:
        warnings.append(f"unsupported PCM sample_width {sample_width}; signal metrics skipped")
        return {
            "path": str(wav_path),
            "exists": True,
            "bytes": wav_path.stat().st_size,
            "status": _scene_status(errors, warnings),
            "duration_seconds": round(duration, 3),
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": sample_width,
            "frames": frames,
            "signal": {},
            "errors": errors,
            "warnings": warnings,
        }

    abs_samples = [abs(sample) for sample in samples]
    peak = max(abs_samples) if abs_samples else 0
    rms = math.sqrt(sum(sample * sample for sample in samples) / sample_count) if sample_count else 0.0
    silence_threshold = max(1, int(max_amplitude * (10.0 ** (SILENCE_DBFS / 20.0))))
    clipped_threshold = max_amplitude - 8
    clipped = sum(1 for value in abs_samples if value >= clipped_threshold)
    near_silent = sum(1 for value in abs_samples if value <= silence_threshold)
    leading_silence, trailing_silence = _edge_silence_seconds(
        samples,
        channels,
        sample_rate,
        silence_threshold,
    )

    clipping_ratio = clipped / sample_count if sample_count else 0.0
    near_silence_ratio = near_silent / sample_count if sample_count else 0.0
    peak_dbfs = _dbfs(float(peak), float(max_amplitude))
    rms_dbfs = _dbfs(float(rms), float(max_amplitude))

    if clipping_ratio > 0.0005:
        warnings.append(f"possible clipping ratio {clipping_ratio:.5f}")
    if rms_dbfs is not None and rms_dbfs < -32.0:
        warnings.append(f"low RMS level {rms_dbfs:.2f} dBFS")
    if rms_dbfs is not None and rms_dbfs > -7.0:
        warnings.append(f"hot RMS level {rms_dbfs:.2f} dBFS")
    if near_silence_ratio > 0.55:
        warnings.append(f"high near-silence ratio {near_silence_ratio:.2%}")
    if leading_silence > 1.5:
        warnings.append(f"leading silence {leading_silence:.2f}s")
    if trailing_silence > 1.5:
        warnings.append(f"trailing silence {trailing_silence:.2f}s")

    return {
        "path": str(wav_path),
        "exists": True,
        "bytes": wav_path.stat().st_size,
        "status": _scene_status(errors, warnings),
        "duration_seconds": round(duration, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width": sample_width,
        "frames": frames,
        "signal": {
            "peak": peak,
            "peak_dbfs": peak_dbfs,
            "rms": round(rms, 3),
            "rms_dbfs": rms_dbfs,
            "clipping_ratio": round(clipping_ratio, 8),
            "near_silence_ratio": round(near_silence_ratio, 6),
            "leading_silence_seconds": leading_silence,
            "trailing_silence_seconds": trailing_silence,
            "silence_threshold_dbfs": SILENCE_DBFS,
        },
        "errors": errors,
        "warnings": warnings,
    }


def _scene_indices(script: list[Any] | None, tts_manifest: dict[str, Any] | None, episode_dir: Path) -> list[int]:
    if isinstance(script, list) and script:
        return list(range(len([scene for scene in script if isinstance(scene, dict)])))

    entries = tts_manifest.get("entries", []) if isinstance(tts_manifest, dict) else []
    indices = [
        int(entry.get("scene_index"))
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("scene_index", "")).isdigit()
    ]
    if indices:
        return sorted(set(indices))

    return sorted(
        int(match.group(1))
        for path in episode_dir.glob("scene_*.wav")
        for match in [re.fullmatch(r"scene_(\d{2})\.wav", path.name)]
        if match
    )


def build_audio_qc(
    *,
    episode_dir: str | Path,
    script: list[Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    entries: list[dict[str, Any]] = []

    manifest_entries = {
        int(entry.get("scene_index")): entry
        for entry in (tts_manifest.get("entries", []) if isinstance(tts_manifest, dict) else [])
        if isinstance(entry, dict) and str(entry.get("scene_index", "")).isdigit()
    }

    for scene_index in _scene_indices(script, tts_manifest, episode_path):
        wav_path = episode_path / f"scene_{scene_index:02d}.wav"
        wav_report = inspect_wav(wav_path)
        manifest_entry = manifest_entries.get(scene_index, {})
        manifest_duration = manifest_entry.get("duration_seconds")
        duration_delta = None
        warnings = list(wav_report.get("warnings", []) or [])
        if isinstance(manifest_duration, (int, float)) and wav_report.get("duration_seconds") is not None:
            duration_delta = round(float(wav_report["duration_seconds"]) - float(manifest_duration), 3)
            if abs(duration_delta) > 0.15:
                warnings.append(f"duration differs from tts_manifest by {duration_delta:.3f}s")
                wav_report["status"] = _scene_status(list(wav_report.get("errors", []) or []), warnings)
                wav_report["warnings"] = warnings

        entries.append(
            {
                "scene_index": scene_index,
                "scene_title": manifest_entry.get("scene_title", ""),
                "status": wav_report.get("status"),
                "duration_delta_seconds": duration_delta,
                **wav_report,
            }
        )

    counts: dict[str, int] = {}
    total_duration = 0.0
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
        total_duration += float(entry.get("duration_seconds") or 0.0)

    blocked = counts.get("blocked", 0)
    review = counts.get("review", 0)
    if blocked:
        status = "blocked"
    elif review:
        status = "review"
    elif entries:
        status = "pass"
    else:
        status = "blocked"

    warnings = [
        f"scene {entry['scene_index']:02d}: {warning}"
        for entry in entries
        for warning in (entry.get("warnings", []) or [])
    ]
    errors = [
        f"scene {entry['scene_index']:02d}: {error}"
        for entry in entries
        for error in (entry.get("errors", []) or [])
    ]
    if not entries:
        errors.append("no scene WAV files found")

    return {
        "schema_version": AUDIO_QC_VERSION,
        "stage": "audio_signal_qc",
        "created_at": _utc_now(),
        "status": status,
        "episode_dir": str(episode_path),
        "scene_count": len(entries),
        "status_counts": counts,
        "total_duration_seconds": round(total_duration, 3),
        "expected": {
            "sample_rate": EXPECTED_SAMPLE_RATE,
            "channels": EXPECTED_CHANNELS,
            "sample_width": EXPECTED_SAMPLE_WIDTH,
            "min_duration_seconds": MIN_DURATION_SECONDS,
        },
        "summary": (
            f"Checked {len(entries)} scene WAV files; "
            f"{counts.get('pass', 0)} pass, {review} review, {blocked} blocked."
        ),
        "warnings": warnings,
        "errors": errors,
        "entries": entries,
    }
