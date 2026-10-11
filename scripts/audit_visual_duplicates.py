#!/usr/bin/env python3
"""Audit a Producer Mode visual timeline for exact and near-duplicate frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
SAMPLE_FRACTIONS = (0.25, 0.50, 0.75)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _video_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _extract_video_frame(source: Path, seconds: float, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=320:180:force_original_aspect_ratio=increase,crop=320:180",
            str(destination),
        ],
        check=True,
    )


def _normalize_image(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        scale = max(320 / image.width, 180 / image.height)
        resized = image.resize(
            (max(320, round(image.width * scale)), max(180, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
        left = (resized.width - 320) // 2
        top = (resized.height - 180) // 2
        resized.crop((left, top, left + 320, top + 180)).save(destination, quality=92)


def _hash_bits(image: Image.Image, mode: str) -> int:
    gray = image.convert("L")
    if mode == "dhash":
        pixels = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
        bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    else:
        pixels = np.asarray(gray.resize((8, 8), Image.Resampling.LANCZOS), dtype=np.float32)
        bits = (pixels > pixels.mean()).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def _frame_signature(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB").resize((64, 36), Image.Resampling.BILINEAR), dtype=np.float32)
        pil_rgb = Image.fromarray(rgb.astype(np.uint8), "RGB")
        return {
            "dhash": f"{_hash_bits(pil_rgb, 'dhash'):016x}",
            "ahash": f"{_hash_bits(pil_rgb, 'ahash'):016x}",
            "mean_rgb": [round(float(value), 2) for value in rgb.mean(axis=(0, 1))],
            "std_rgb": [round(float(value), 2) for value in rgb.std(axis=(0, 1))],
        }


def _hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _color_distance(left: dict, right: dict) -> float:
    l_mean = np.asarray(left["mean_rgb"], dtype=np.float32)
    r_mean = np.asarray(right["mean_rgb"], dtype=np.float32)
    l_std = np.asarray(left["std_rgb"], dtype=np.float32)
    r_std = np.asarray(right["std_rgb"], dtype=np.float32)
    return float(np.linalg.norm(l_mean - r_mean) + 0.5 * np.linalg.norm(l_std - r_std))


def _make_contact_sheets(frames: list[dict], output_dir: Path) -> list[str]:
    sheet_dir = output_dir / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    paths: list[str] = []
    per_page = 25
    for page_index in range(math.ceil(len(frames) / per_page)):
        page_frames = frames[page_index * per_page : (page_index + 1) * per_page]
        canvas = Image.new("RGB", (5 * 330, 5 * 215), "#111111")
        draw = ImageDraw.Draw(canvas)
        for index, frame in enumerate(page_frames):
            row, column = divmod(index, 5)
            with Image.open(frame["frame_path"]) as image:
                canvas.paste(image.convert("RGB"), (column * 330 + 5, row * 215 + 5))
            label = f"{frame['slot_id']} {frame['provider']}"
            draw.text((column * 330 + 5, row * 215 + 188), label[:48], fill="white", font=font)
        output = sheet_dir / f"timeline_contact_{page_index + 1:02d}.jpg"
        canvas.save(output, quality=90)
        paths.append(str(output))
    return paths


def audit(timeline_path: Path, output_dir: Path) -> dict:
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    slots: list[dict] = []
    errors: list[dict] = []
    exact_hash_groups: dict[str, list[str]] = defaultdict(list)
    sampled_frames: list[dict] = []
    representative_frames: list[dict] = []

    for scene in timeline.get("scenes", []):
        for fallback_index, slot in enumerate(scene.get("slots", [])):
            asset_index = int(slot.get("asset_index", fallback_index))
            slot_id = f"S{int(scene['scene_index']):02d}A{asset_index:02d}"
            source = Path(slot["local_path"])
            record = {
                "slot_id": slot_id,
                "scene_index": int(scene["scene_index"]),
                "asset_index": asset_index,
                "provider": slot.get("provider", "unknown"),
                "timeline_role": slot.get("timeline_role"),
                "local_path": str(source),
                "exists": source.exists(),
                "samples": [],
            }
            slots.append(record)
            if not source.exists():
                errors.append({"slot_id": slot_id, "error": "missing source file", "path": str(source)})
                continue
            try:
                file_hash = _sha256(source)
                record["sha256"] = file_hash
                exact_hash_groups[file_hash].append(slot_id)
                if source.suffix.lower() in VIDEO_EXTENSIONS:
                    duration = _video_duration(source)
                    record["source_duration_seconds"] = round(duration, 3)
                    fractions = SAMPLE_FRACTIONS
                    for sample_index, fraction in enumerate(fractions):
                        seconds = min(max(duration * fraction, 0.05), max(duration - 0.05, 0.05))
                        frame_path = frame_dir / f"{slot_id}_p{round(fraction * 100):02d}.jpg"
                        _extract_video_frame(source, seconds, frame_path)
                        signature = _frame_signature(frame_path)
                        frame = {
                            "slot_id": slot_id,
                            "provider": record["provider"],
                            "sample_index": sample_index,
                            "fraction": fraction,
                            "seconds": round(seconds, 3),
                            "frame_path": str(frame_path),
                            **signature,
                        }
                        record["samples"].append(frame)
                        sampled_frames.append(frame)
                    representative_frames.append(record["samples"][1])
                else:
                    frame_path = frame_dir / f"{slot_id}_still.jpg"
                    _normalize_image(source, frame_path)
                    signature = _frame_signature(frame_path)
                    frame = {
                        "slot_id": slot_id,
                        "provider": record["provider"],
                        "sample_index": 0,
                        "fraction": None,
                        "seconds": None,
                        "frame_path": str(frame_path),
                        **signature,
                    }
                    record["samples"].append(frame)
                    sampled_frames.append(frame)
                    representative_frames.append(frame)
            except Exception as exc:  # Preserve the rest of the audit if one asset is malformed.
                errors.append({"slot_id": slot_id, "error": str(exc), "path": str(source)})

    exact_duplicates = [
        {"sha256": digest, "slot_ids": slot_ids}
        for digest, slot_ids in exact_hash_groups.items()
        if len(slot_ids) > 1
    ]

    near_pairs: list[dict] = []
    by_slot = {record["slot_id"]: record for record in slots}
    slot_ids = sorted(by_slot)
    for left_index, left_id in enumerate(slot_ids):
        left = by_slot[left_id]
        if not left["samples"]:
            continue
        for right_id in slot_ids[left_index + 1 :]:
            right = by_slot[right_id]
            if not right["samples"]:
                continue
            best = None
            for left_frame in left["samples"]:
                for right_frame in right["samples"]:
                    candidate = {
                        "dhash_distance": _hamming(left_frame["dhash"], right_frame["dhash"]),
                        "ahash_distance": _hamming(left_frame["ahash"], right_frame["ahash"]),
                        "color_distance": round(_color_distance(left_frame, right_frame), 2),
                        "left_frame": left_frame["frame_path"],
                        "right_frame": right_frame["frame_path"],
                    }
                    score = candidate["dhash_distance"] + candidate["ahash_distance"] + candidate["color_distance"] / 12
                    if best is None or score < best[0]:
                        best = (score, candidate)
            assert best is not None
            candidate = best[1]
            if (
                candidate["dhash_distance"] <= 4
                and candidate["ahash_distance"] <= 5
                and candidate["color_distance"] <= 30
            ):
                near_pairs.append(
                    {
                        "left_slot_id": left_id,
                        "right_slot_id": right_id,
                        "left_provider": left["provider"],
                        "right_provider": right["provider"],
                        **candidate,
                    }
                )

    contact_sheets = _make_contact_sheets(representative_frames, output_dir)
    status = "pass" if not exact_duplicates and not near_pairs and not errors else "review"
    report = {
        "schema_version": 1,
        "stage": "duplicate_frame_audit",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "timeline_path": str(timeline_path),
        "slot_count": len(slots),
        "sampled_frame_count": len(sampled_frames),
        "exact_duplicate_group_count": len(exact_duplicates),
        "near_duplicate_pair_count": len(near_pairs),
        "error_count": len(errors),
        "thresholds": {
            "dhash_max_distance": 4,
            "ahash_max_distance": 5,
            "color_distance_max": 30,
            "video_sample_fractions": SAMPLE_FRACTIONS,
        },
        "exact_duplicate_groups": exact_duplicates,
        "near_duplicate_pairs": near_pairs,
        "errors": errors,
        "contact_sheets": contact_sheets,
        "slots": slots,
    }
    report_path = output_dir / "duplicate_frame_audit.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.timeline.resolve(), args.output_dir.resolve())
    print(
        json.dumps(
            {
                "status": report["status"],
                "slot_count": report["slot_count"],
                "sampled_frame_count": report["sampled_frame_count"],
                "exact_duplicate_group_count": report["exact_duplicate_group_count"],
                "near_duplicate_pair_count": report["near_duplicate_pair_count"],
                "error_count": report["error_count"],
                "report": str(args.output_dir.resolve() / "duplicate_frame_audit.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
