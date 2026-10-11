"""Gemini TTS production helpers for PodcastV2 Producer Mode.

This stage reads ``script.json`` and writes PodcastV2-compatible
``scene_NN.wav`` files plus ``tts_manifest.json`` and ``tts_qc.json``. The
actual provider call reuses the existing ``classes.Tts.TTS`` implementation so
Producer Mode stays aligned with PodcastV2 voice behavior without changing the
core runtime.
"""

from __future__ import annotations

import re
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_gemini_tts_model


TTS_MANIFEST_VERSION = 1
DEFAULT_TONE_PRESET = "natural_storyteller"
# Gemini 3.8 Flash TTS standard rates ($1/1M text, $18/1M audio tokens at 25 tokens/s). Google's
# launch pricing halves these through 2026-12-31; estimates stay at the standard rate.
GEMINI_TTS_TEXT_USD_PER_CHAR = 0.00000025
GEMINI_TTS_AUDIO_USD_PER_SECOND = 0.00045
ESTIMATED_THAI_CHARS_PER_SECOND = 13.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _count_chars_no_space(value: str) -> int:
    return len(re.sub(r"\s+", "", str(value or "")))


def _narration_encoding_issue(value: str) -> str:
    """Return a safe-to-report issue when narration is not valid prose text.

    Thai mojibake can still contain many characters from the Thai Unicode block,
    so character-count checks alone are not sufficient.  C1 control characters
    are never appropriate in narration and are a reliable signal that text was
    decoded with the wrong Windows code page before reaching TTS.
    """
    text = str(value or "")
    c1_controls = sum(0x80 <= ord(char) <= 0x9F for char in text)
    if c1_controls:
        return (
            f"narration contains {c1_controls} C1 control characters; "
            "likely mojibake. Restore the source text as UTF-8 before TTS."
        )
    if "\ufffd" in text:
        return "narration contains Unicode replacement characters; restore the source text before TTS."
    return ""


def _scene_audio_path(episode_dir: Path, scene_index: int) -> Path:
    return episode_dir / f"scene_{scene_index:02d}.wav"


def _wav_info(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
    duration = frames / sample_rate if sample_rate else 0.0
    return {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": round(duration, 3),
    }


def _safe_wav_info(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "file does not exist"
    if path.stat().st_size <= 44:
        return None, "wav file is empty or header-only"
    try:
        return _wav_info(path), ""
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _estimate_duration_seconds(chars_no_space: int) -> float:
    if chars_no_space <= 0:
        return 0.0
    return round(chars_no_space / ESTIMATED_THAI_CHARS_PER_SECOND, 3)


def _estimate_cost(chars_no_space: int, duration_seconds: float) -> float:
    return round(
        chars_no_space * GEMINI_TTS_TEXT_USD_PER_CHAR
        + max(0.0, duration_seconds) * GEMINI_TTS_AUDIO_USD_PER_SECOND,
        6,
    )


def _entry_base(
    *,
    scene: dict[str, Any],
    scene_index: int,
    output_path: Path,
    tone_preset: str,
) -> dict[str, Any]:
    narration = _clean_text(scene.get("narration"))
    chars_no_space = _count_chars_no_space(narration)
    estimated_duration = _estimate_duration_seconds(chars_no_space)
    return {
        "scene_index": scene_index,
        "scene_title": scene.get("scene_title", ""),
        "section_index": scene.get("section_index"),
        "section_title": scene.get("section_title", ""),
        "provider": "gemini_tts",
        "model": get_gemini_tts_model(),
        "tone_preset": tone_preset,
        "local_path": str(output_path),
        "chars_no_space": chars_no_space,
        "estimated_duration_seconds": estimated_duration,
        "estimated_cost_usd": _estimate_cost(chars_no_space, estimated_duration),
        "source_ids": scene.get("source_ids", []),
        "source_urls": scene.get("source_urls", []),
        "pronunciation_terms": scene.get("pronunciation_terms", []),
    }


def _status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _tts_qc(entries: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    counts = _status_counts(entries)
    failed = counts.get("failed", 0)
    planned = counts.get("planned", 0)
    generated = counts.get("generated", 0) + counts.get("skipped_existing", 0)
    total_duration = round(
        sum(float(entry.get("duration_seconds") or 0.0) for entry in entries),
        3,
    )
    total_estimated_cost = round(
        sum(float(entry.get("estimated_cost_usd") or 0.0) for entry in entries),
        6,
    )

    if failed:
        status = "blocked"
    elif planned:
        status = "planned"
    elif entries and generated == len(entries):
        status = "pass"
    else:
        status = "pending"

    return {
        "schema_version": TTS_MANIFEST_VERSION,
        "stage": "tts_qc",
        "created_at": _utc_now(),
        "status": status,
        "summary": (
            f"Checked {len(entries)} TTS entries; "
            f"{generated} generated or reusable, {planned} planned, {failed} failed."
        ),
        "scene_count": len(entries),
        "status_counts": counts,
        "total_duration_seconds": total_duration,
        "estimated_cost_usd": total_estimated_cost,
        "warnings": warnings,
        "entries": [
            {
                "scene_index": entry.get("scene_index"),
                "status": entry.get("status"),
                "local_path": entry.get("local_path"),
                "duration_seconds": entry.get("duration_seconds"),
                "issue": entry.get("issue", ""),
            }
            for entry in entries
        ],
    }


def produce_tts(
    *,
    episode_dir: str | Path,
    script: list[Any],
    pronunciation_guide_path: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    tone_preset: str = DEFAULT_TONE_PRESET,
    limit: int | None = None,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    if not isinstance(script, list) or not script:
        warnings = ["script.json must contain at least one scene before TTS production"]
        qc = _tts_qc([], warnings)
        qc["status"] = "blocked"
        return {
            "tts_manifest": {
                "schema_version": TTS_MANIFEST_VERSION,
                "stage": "tts_production",
                "created_at": _utc_now(),
                "status": "blocked",
                "dry_run": dry_run,
                "provider": "gemini_tts",
                "tone_preset": tone_preset,
                "entries": [],
                "warnings": warnings,
            },
            "tts_qc": qc,
        }

    try:
        from classes.Tts import normalize_gemini_tts_tone_preset

        normalized_tone = normalize_gemini_tts_tone_preset(tone_preset)
    except Exception:  # noqa: BLE001
        normalized_tone = tone_preset or DEFAULT_TONE_PRESET

    selected_script = script[: max(0, int(limit))] if limit is not None else script
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    tts = None
    if not dry_run:
        from classes.Tts import TTS

        tts = TTS()

    for scene_index, scene in enumerate(selected_script):
        if not isinstance(scene, dict):
            warnings.append(f"scene {scene_index}: script entry is not an object")
            entries.append(
                {
                    "scene_index": scene_index,
                    "provider": "gemini_tts",
                    "status": "failed",
                    "issue": "script entry is not an object",
                }
            )
            continue

        output_path = _scene_audio_path(episode_path, scene_index)
        entry = _entry_base(
            scene=scene,
            scene_index=scene_index,
            output_path=output_path,
            tone_preset=normalized_tone,
        )
        narration = _clean_text(scene.get("narration"))
        if not narration:
            entry["status"] = "failed"
            entry["issue"] = "scene narration is empty"
            warnings.append(f"scene {scene_index}: narration is empty")
            entries.append(entry)
            continue

        encoding_issue = _narration_encoding_issue(narration)
        if encoding_issue:
            entry["status"] = "failed"
            entry["issue"] = encoding_issue
            warnings.append(f"scene {scene_index}: {encoding_issue}")
            entries.append(entry)
            continue

        if dry_run:
            entry["status"] = "planned"
            entry["issue"] = "dry run; Gemini TTS call skipped"
            entry["duration_seconds"] = entry["estimated_duration_seconds"]
            entries.append(entry)
            continue

        if output_path.exists() and not force:
            wav_info, issue = _safe_wav_info(output_path)
            if wav_info:
                entry.update(wav_info)
                entry["status"] = "skipped_existing"
                entry["estimated_cost_usd"] = _estimate_cost(
                    int(entry.get("chars_no_space") or 0),
                    float(entry.get("duration_seconds") or 0.0),
                )
                entries.append(entry)
                continue
            warnings.append(f"scene {scene_index}: existing wav unusable, regenerating: {issue}")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            assert tts is not None
            tts.synthesize_gemini(
                narration,
                output_file=str(output_path),
                scene_index=scene_index,
                total_scenes=len(script),
                tone_preset=normalized_tone,
            )
            wav_info, issue = _safe_wav_info(output_path)
            if not wav_info:
                raise RuntimeError(issue or "Gemini TTS did not write a valid wav file")
            entry.update(wav_info)
            entry["status"] = "generated"
            entry["estimated_cost_usd"] = _estimate_cost(
                int(entry.get("chars_no_space") or 0),
                float(entry.get("duration_seconds") or 0.0),
            )
        except Exception as exc:  # noqa: BLE001
            entry["status"] = "failed"
            entry["issue"] = str(exc)
            warnings.append(f"scene {scene_index}: Gemini TTS failed: {exc}")
        entries.append(entry)

    counts = _status_counts(entries)
    if counts.get("failed", 0):
        status = "blocked"
    elif counts.get("planned", 0):
        status = "planned"
    elif entries and counts.get("generated", 0) + counts.get("skipped_existing", 0) == len(entries):
        status = "complete"
    else:
        status = "pending"

    total_duration = round(
        sum(float(entry.get("duration_seconds") or 0.0) for entry in entries),
        3,
    )
    total_estimated_cost = round(
        sum(float(entry.get("estimated_cost_usd") or 0.0) for entry in entries),
        6,
    )

    manifest = {
        "schema_version": TTS_MANIFEST_VERSION,
        "stage": "tts_production",
        "created_at": _utc_now(),
        "status": status,
        "dry_run": dry_run,
        "provider": "gemini_tts",
        "model": get_gemini_tts_model(),
        "tone_preset": normalized_tone,
        "pronunciation_guide_path": str(pronunciation_guide_path or ""),
        "scene_count": len(entries),
        "total_duration_seconds": total_duration,
        "estimated_cost_usd": total_estimated_cost,
        "entries": entries,
        "warnings": warnings,
    }
    return {
        "tts_manifest": manifest,
        "tts_qc": _tts_qc(entries, warnings),
    }
