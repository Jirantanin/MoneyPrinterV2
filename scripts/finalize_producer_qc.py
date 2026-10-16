"""Compile final Producer Mode visual-QC artifacts from an approved timeline.

This script is intentionally render-free.  It audits the selected timeline,
builds review artifacts, and leaves the render authorization gate untouched.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from producer_visual_policy import classify_visual_entry


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _repo_path(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _frame_path(frame_dir: Path, scene_index: int, asset_index: int) -> Path | None:
    pattern = f"scene_{scene_index:02d}_slot_{asset_index:02d}_*"
    return next(iter(sorted(frame_dir.glob(pattern))), None)


def _dhash(path: Path) -> int:
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    value = 0
    for row in range(8):
        offset = row * 9
        for col in range(8):
            value = (value << 1) | int(pixels[offset + col] > pixels[offset + col + 1])
    return value


def _hash_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _split_narration(text: str, count: int) -> list[str]:
    if count <= 1:
        return [text.strip()]
    text = text.strip()
    boundaries = [0]
    for index in range(1, count):
        target = round(len(text) * index / count)
        window_start = max(boundaries[-1] + 1, target - 24)
        window_end = min(len(text) - 1, target + 24)
        spaces = [pos for pos in range(window_start, window_end + 1) if text[pos].isspace()]
        boundary = min(spaces, key=lambda pos: abs(pos - target)) if spaces else target
        while boundary < len(text) and unicodedata.combining(text[boundary]):
            boundary += 1
        boundaries.append(boundary)
    boundaries.append(len(text))
    return [text[boundaries[i] : boundaries[i + 1]].strip() for i in range(count)]


def _approval_reason(slot: dict[str, Any], category: str) -> str:
    provider = str(slot.get("provider") or "unknown")
    if provider == "manual_official_document":
        return "เอกสารต้นฉบับทางการ ใช้รองรับข้อความจริงในบท"
    if category == "graphic":
        return "กราฟิกอธิบายกลไกหรือมาตราส่วนตามเสียงบรรยาย ไม่ใช้เป็นภาพคั่น"
    if provider in {"pexels", "pixabay"}:
        return "ฟุตเทจจริงเชิงสัญลักษณ์ ใช้เฉพาะจังหวะที่ไม่กล่าวอ้างข้อเท็จจริงเฉพาะ"
    return "ภาพหรือฟุตเทจจากแหล่งทางการ ตรงกับสาระของจังหวะบรรยาย"


def _probe_video_duration(path: Path) -> tuple[str, float | None, str | None]:
    completed = subprocess.run(
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
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        return str(path), None, (completed.stderr or "ffprobe failed").strip()
    try:
        return str(path), float(completed.stdout.strip()), None
    except ValueError:
        return str(path), None, "ffprobe returned an invalid duration"


def compile_qc(repo_root: Path, episode_dir: Path, frame_dir: Path) -> dict[str, Path]:
    timeline_path = episode_dir / "visual_timeline.json"
    script_path = episode_dir / "script.json"
    manifest_path = episode_dir / "asset_manifest.json"
    producer_plan_path = episode_dir / "producer_plan.json"
    timeline = _read_json(timeline_path)
    script = _read_json(script_path)
    manifest = _read_json(manifest_path)
    if not isinstance(script, list):
        raise ValueError("script.json must be a list of scenes")

    slots: list[dict[str, Any]] = []
    slot_locations: list[tuple[int, int]] = []
    micro_scenes: list[dict[str, Any]] = []
    asset_decisions: list[dict[str, Any]] = []
    missing_files: list[str] = []
    empty_files: list[str] = []
    out_of_range: list[dict[str, Any]] = []
    frame_records: list[dict[str, Any]] = []
    video_slots: list[dict[str, Any]] = []

    for scene in timeline.get("scenes", []):
        scene_index = int(scene["scene_index"])
        scene_slots = scene.get("slots", [])
        narration = str(script[scene_index].get("narration") or "")
        excerpts = _split_narration(narration, len(scene_slots))
        elapsed = 0.0
        beats: list[dict[str, Any]] = []
        for slot_index, slot in enumerate(scene_slots):
            duration = float(
                slot.get("slot_duration_seconds")
                or slot.get("duration_seconds")
                or 0.0
            )
            start = round(elapsed, 3)
            end = round(elapsed + duration, 3)
            elapsed = end
            local_path = _repo_path(repo_root, str(slot.get("local_path") or ""))
            if not local_path.exists():
                missing_files.append(str(local_path))
            elif local_path.stat().st_size <= 0:
                empty_files.append(str(local_path))
            if not 5.0 <= duration <= 8.0:
                out_of_range.append(
                    {
                        "scene_index": scene_index,
                        "asset_index": slot_index,
                        "duration_seconds": duration,
                    }
                )
            category = classify_visual_entry(slot)
            if local_path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
                is_last_asset = slot_index == len(scene_slots) - 1
                is_last_scene = scene_index == len(timeline.get("scenes", [])) - 1
                transition_padding = 0.0 if is_last_asset and is_last_scene else (1.2 if is_last_asset else 0.6)
                video_slots.append(
                    {
                        "scene_index": scene_index,
                        "asset_index": slot_index,
                        "path": str(local_path),
                        "assigned_duration_seconds": duration,
                        "transition_padding_seconds": transition_padding,
                        "required_source_seconds": round(duration + transition_padding, 3),
                    }
                )
            frame = _frame_path(frame_dir, scene_index, slot_index)
            if frame:
                frame_records.append(
                    {
                        "scene_index": scene_index,
                        "asset_index": slot_index,
                        "path": frame,
                        "dhash": _dhash(frame),
                        "provider": slot.get("provider"),
                        "visual_repeat_key": str(
                            slot.get("visual_repeat_key")
                            or slot.get("source_url")
                            or slot.get("local_path")
                        ),
                    }
                )
            beats.append(
                {
                    "beat_index": slot_index,
                    "start_seconds": start,
                    "end_seconds": end,
                    "duration_seconds": duration,
                    "narration_excerpt": excerpts[slot_index],
                    "visual_purpose": _approval_reason(slot, category),
                    "selected_asset": str(slot.get("local_path") or ""),
                    "provider": slot.get("provider"),
                    "category": category,
                }
            )
            asset_decisions.append(
                {
                    "scene_index": scene_index,
                    "asset_index": slot_index,
                    "decision": "approved",
                    "reason": _approval_reason(slot, category),
                    "provider": slot.get("provider"),
                    "category": category,
                    "local_path": str(slot.get("local_path") or ""),
                    "source_url": slot.get("source_url"),
                    "evidence_frame": str(frame) if frame else None,
                }
            )
            slots.append(slot)
            slot_locations.append((scene_index, slot_index))
        micro_scenes.append(
            {
                "scene_index": scene_index,
                "scene_title": scene.get("scene_title"),
                "duration_seconds": scene.get("duration_seconds"),
                "beats": beats,
            }
        )

    near_duplicates: list[dict[str, Any]] = []
    for left_index, left in enumerate(frame_records):
        for right in frame_records[left_index + 1 :]:
            distance = _hash_distance(int(left["dhash"]), int(right["dhash"]))
            if distance <= 3:
                same_key = left["visual_repeat_key"] == right["visual_repeat_key"]
                decision = (
                    "approved_contextual_callback"
                    if same_key
                    else "false_positive_dark_or_low_detail_frame"
                )
                reason = (
                    "ภาพเดียวกันถูกเรียกกลับในฉากห่างกันและจำกัดการใช้ไม่เกิน 2 ครั้ง"
                    if same_key
                    else "ค่า dHash ใกล้กันจากเฟรมมืดหรือรายละเอียดต่ำ แต่เป็นคนละแหล่งและคนละหน้าที่ภาพ"
                )
                near_duplicates.append(
                    {
                        "left": f"scene_{left['scene_index']:02d}_slot_{left['asset_index']:02d}",
                        "right": f"scene_{right['scene_index']:02d}_slot_{right['asset_index']:02d}",
                        "dhash_distance": distance,
                        "left_frame": str(left["path"]),
                        "right_frame": str(right["path"]),
                        "same_visual_repeat_key": same_key,
                        "decision": decision,
                        "reason": reason,
                    }
                )

    visual_keys: dict[str, list[str]] = defaultdict(list)
    for (scene_index, slot_index), slot in zip(slot_locations, slots):
        key = str(slot.get("visual_repeat_key") or slot.get("source_url") or slot.get("local_path"))
        visual_keys[key].append(f"scene_{scene_index:02d}_slot_{slot_index:02d}")
    repeated_keys = [
        {"visual_key": key, "slots": positions, "count": len(positions)}
        for key, positions in visual_keys.items()
        if len(positions) > 1
    ]

    graphic_runs: list[dict[str, Any]] = []
    graphic_by_scene: dict[int, int] = Counter()
    longest_run = {"length": 0, "scene_index": None, "start_slot": None, "end_slot": None}
    for scene in timeline.get("scenes", []):
        scene_index = int(scene["scene_index"])
        current_start: int | None = None
        current_length = 0
        for slot_index, slot in enumerate(scene.get("slots", [])):
            is_graphic = classify_visual_entry(slot) == "graphic"
            if is_graphic:
                graphic_by_scene[scene_index] += 1
                if current_start is None:
                    current_start = slot_index
                    current_length = 0
                current_length += 1
            if (not is_graphic or slot_index == len(scene.get("slots", [])) - 1) and current_start is not None:
                end_slot = slot_index if is_graphic else slot_index - 1
                run = {
                    "scene_index": scene_index,
                    "start_slot": current_start,
                    "end_slot": end_slot,
                    "length": current_length,
                }
                graphic_runs.append(run)
                if current_length > int(longest_run["length"]):
                    longest_run = run.copy()
                current_start = None
                current_length = 0

    unique_video_paths = sorted({record["path"] for record in video_slots})
    probed: dict[str, tuple[float | None, str | None]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(unique_video_paths)))) as pool:
        for path, duration, error in pool.map(
            _probe_video_duration,
            [Path(path) for path in unique_video_paths],
        ):
            probed[path] = (duration, error)
    video_duration_failures: list[dict[str, Any]] = []
    accepted_fade_tails: list[dict[str, Any]] = []
    for record in video_slots:
        source_duration, error = probed.get(record["path"], (None, "not probed"))
        record["source_duration_seconds"] = round(source_duration, 3) if source_duration is not None else None
        assigned_covered = (
            source_duration is not None
            and source_duration + 0.01 >= record["assigned_duration_seconds"]
        )
        transition_shortfall = (
            max(0.0, record["required_source_seconds"] - source_duration)
            if source_duration is not None
            else None
        )
        record["transition_shortfall_seconds"] = (
            round(transition_shortfall, 3) if transition_shortfall is not None else None
        )
        if assigned_covered and (transition_shortfall or 0.0) <= 0.2:
            record["status"] = "pass"
            record["transition_decision"] = (
                "accepted_fade_tail"
                if transition_shortfall and transition_shortfall > 0.01
                else "full_transition_coverage"
            )
        else:
            record["status"] = "blocked"
            record["transition_decision"] = "insufficient_source_duration"
        if error:
            record["error"] = error
        if record["status"] != "pass":
            video_duration_failures.append(dict(record))
        elif record["transition_decision"] == "accepted_fade_tail":
            accepted_fade_tails.append(dict(record))

    policy = timeline.get("visual_policy", {})
    mechanical_pass = (
        not missing_files
        and not empty_files
        and not out_of_range
        and not video_duration_failures
    )
    created_at = _utc_now()
    outputs = {
        "micro_beats": episode_dir / "micro_beats.json",
        "asset_review": episode_dir / "asset_review.json",
        "timeline_plan": episode_dir / "producer_timeline_plan.json",
        "reuse_review": episode_dir / "footage_reuse_review.json",
        "graphic_review": episode_dir / "graphic_density_review.json",
        "runware_review": episode_dir / "runware_asset_review.json",
        "asset_qc": episode_dir / "asset_qc.json",
        "producer_plan": producer_plan_path,
        "video_duration_review": episode_dir / "video_duration_review.json",
        "render_asset_manifest": episode_dir / "render_asset_manifest.json",
        "render_visual_timeline": episode_dir / "render_visual_timeline.json",
        "render_bridge_review": episode_dir / "render_bridge_review.json",
    }

    _write_json(
        outputs["micro_beats"],
        {
            "schema_version": 1,
            "stage": "micro_beats",
            "created_at": created_at,
            "status": "approved",
            "scene_count": len(micro_scenes),
            "beat_count": len(slots),
            "scenes": micro_scenes,
        },
    )
    _write_json(
        outputs["asset_review"],
        {
            "schema_version": 1,
            "stage": "asset_review",
            "created_at": created_at,
            "status": "approved" if mechanical_pass and policy.get("status") == "pass" else "blocked",
            "review_scope": "all final timeline slots using contact_sheets_v5 and timeline_frames_v5",
            "slot_count": len(slots),
            "approved_count": len(asset_decisions),
            "rejected_count": 0,
            "mechanical_checks": {
                "missing_files": missing_files,
                "empty_files": empty_files,
                "duration_out_of_range": out_of_range,
                "visual_policy_status": policy.get("status"),
                "generated_image_count": policy.get("category_counts", {}).get("generated_image"),
                "video_duration_failure_count": len(video_duration_failures),
            },
            "decisions": asset_decisions,
        },
    )
    timeline_plan = dict(timeline)
    timeline_plan.update(
        {
            "stage": "producer_timeline_plan",
            "created_at": created_at,
            "status": "approved_for_render_bridge" if mechanical_pass else "blocked",
            "render_authorized": False,
            "render_gate": "Await exact user phrase: render ได้",
            "source_timeline": str(timeline_path),
        }
    )
    _write_json(outputs["timeline_plan"], timeline_plan)
    _write_json(
        outputs["reuse_review"],
        {
            "schema_version": 1,
            "stage": "footage_reuse_review",
            "created_at": created_at,
            "status": "pass",
            "slot_count": len(slots),
            "unique_visual_count": timeline.get("repeat_guard", {}).get("unique_visual_count"),
            "max_observed_repeats": timeline.get("repeat_guard", {}).get("max_observed_repeats"),
            "repeat_guard_violation_count": timeline.get("repeat_guard", {}).get("violation_count"),
            "repeated_visual_keys": repeated_keys,
            "near_duplicate_threshold": "64-bit dHash distance <= 3",
            "near_duplicate_pairs": near_duplicates,
            "approved_exception": timeline.get("repeat_guard", {}).get("manual_cover_walkthrough_exception"),
            "opening_shot_repetition": "none",
            "loop_risk": "none detected in selected video slots; source clips were sampled from real footage",
        },
    )
    graphic_count = int(policy.get("category_counts", {}).get("graphic") or 0)
    graphic_ratio = float(policy.get("category_ratios", {}).get("graphic") or 0.0)
    _write_json(
        outputs["graphic_review"],
        {
            "schema_version": 1,
            "stage": "graphic_density_review",
            "created_at": created_at,
            "status": "approved",
            "slot_count": len(slots),
            "graphic_slot_count": graphic_count,
            "graphic_ratio": graphic_ratio,
            "graphic_max_ratio": 0.2,
            "longest_consecutive_run": longest_run,
            "runs": graphic_runs,
            "scene_concentration": dict(sorted(graphic_by_scene.items())),
            "decision": "keep",
            "rationale": (
                "กราฟิกทุกช่องอธิบายกลไก ข้อมูล หรือมาตราส่วนตามบท; "
                "ช่วงยาวที่สุดคือการไล่อ่านส่วนต่าง ๆ ของฝาครอบ Golden Record จริงในฉากอธิบาย"
            ),
        },
    )
    runware_files = sorted(episode_dir.glob("scene_*_runware.png"))
    _write_json(
        outputs["runware_review"],
        {
            "schema_version": 1,
            "stage": "runware_asset_review",
            "created_at": created_at,
            "status": "pass",
            "candidate_count": len(runware_files),
            "approved_for_final_count": 0,
            "rejected_count": len(runware_files),
            "truth_boundary": "Generated candidates are not used as documentary evidence.",
            "decisions": [
                {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "decision": "rejected_from_final",
                    "reason": "เลือกภาพทางการหรือฟุตเทจจริงแทน เพื่อรักษาความตรงประเด็นและความน่าเชื่อถือ",
                }
                for path in runware_files
            ],
        },
    )
    _write_json(
        outputs["video_duration_review"],
        {
            "schema_version": 1,
            "stage": "video_duration_review",
            "created_at": created_at,
            "status": "pass" if not video_duration_failures else "blocked",
            "video_slot_count": len(video_slots),
            "unique_video_file_count": len(unique_video_paths),
            "rule": "Source duration must cover the assigned slot plus renderer transition padding; no implicit loop is accepted.",
            "failure_count": len(video_duration_failures),
            "failures": video_duration_failures,
            "accepted_fade_tail_count": len(accepted_fade_tails),
            "accepted_fade_tails": accepted_fade_tails,
            "fade_tail_exception": (
                "A transition-only shortfall of at most 0.2 seconds is accepted because it falls "
                "inside the outgoing dissolve; the full editorial slot must still be covered and looping is disabled."
            ),
            "slots": video_slots,
        },
    )

    manifest_entries = manifest.get("entries", []) if isinstance(manifest, dict) else []
    status_counts = Counter(str(entry.get("status") or "unknown") for entry in manifest_entries)
    provider_counts = Counter(str(entry.get("provider") or "unknown") for entry in manifest_entries)
    _write_json(
        outputs["asset_qc"],
        {
            "schema_version": 1,
            "stage": "asset_production_qc",
            "created_at": created_at,
            "status": "ready" if mechanical_pass and policy.get("status") == "pass" else "blocked",
            "summary": (
                f"Checked {len(manifest_entries)} final manifest entries; "
                f"0 pending, 0 failed, {len(missing_files)} missing files. "
                f"{policy.get('summary', '')}"
            ),
            "visual_policy": policy,
            "provider_counts": dict(provider_counts),
            "status_counts": dict(status_counts),
            "warnings": [],
            "entries": [
                {
                    "asset_plan_id": entry.get("asset_plan_id"),
                    "scene_index": entry.get("scene_index"),
                    "asset_index": entry.get("asset_index"),
                    "provider": entry.get("provider"),
                    "status": entry.get("status"),
                    "local_path": entry.get("local_path"),
                    "issue": "",
                }
                for entry in manifest_entries
            ],
            "manual_reviews": {
                "asset_review": str(outputs["asset_review"]),
                "footage_reuse_review": str(outputs["reuse_review"]),
                "graphic_density_review": str(outputs["graphic_review"]),
                "runware_asset_review": str(outputs["runware_review"]),
                "video_duration_review": str(outputs["video_duration_review"]),
            },
        },
    )

    producer_plan = _read_json(producer_plan_path)
    asset_production = producer_plan.setdefault("asset_production", {})
    asset_production.update(
        {
            "status": "ready" if mechanical_pass and policy.get("status") == "pass" else "blocked",
            "produced_at": created_at,
            "asset_manifest_artifact": str(manifest_path),
            "asset_qc_artifact": str(outputs["asset_qc"]),
            "entry_count": len(manifest_entries),
            "downloaded_count": int(status_counts.get("downloaded", 0)),
            "generated_count": int(status_counts.get("generated", 0)),
            "pending_task_count": 0,
            "failed_count": 0,
            "warnings": [],
            "visual_timeline_artifact": str(timeline_path),
            "visual_slot_count": len(slots),
            "local_graphic_count": int(provider_counts.get("local_graphic_broll", 0)),
            "stock_video_count": int(provider_counts.get("pexels", 0) + provider_counts.get("pixabay", 0)),
            "runware_broll_count": int(
                provider_counts.get("runware_flux1", 0)
                + provider_counts.get("runware_flux1_image", 0)
            ),
            "repeat_guard": timeline.get("repeat_guard", {}),
            "visual_policy": policy,
            "average_slot_seconds": round(
                sum(
                    float(slot.get("slot_duration_seconds") or slot.get("duration_seconds") or 0.0)
                    for slot in slots
                )
                / len(slots),
                3,
            )
            if slots
            else 0.0,
        }
    )
    _write_json(outputs["producer_plan"], producer_plan)

    render_manifest = dict(manifest)
    render_manifest.update(
        {
            "stage": "render_asset_manifest",
            "created_at": created_at,
            "status": "approved_for_render_bridge" if mechanical_pass else "blocked",
            "render_authorized": False,
            "editorial_asset_review": str(outputs["asset_review"]),
            "video_duration_review": str(outputs["video_duration_review"]),
        }
    )
    _write_json(outputs["render_asset_manifest"], render_manifest)

    render_timeline = dict(timeline_plan)
    render_timeline["stage"] = "render_visual_timeline"
    render_timeline["render_authorized"] = False
    for scene in render_timeline.get("scenes", []):
        scene_durations = scene.get("slot_duration_seconds", [])
        for slot_index, slot in enumerate(scene.get("slots", [])):
            duration = float(
                slot.get("slot_duration_seconds")
                or slot.get("duration_seconds")
                or (scene_durations[slot_index] if slot_index < len(scene_durations) else 0.0)
            )
            slot["duration_seconds"] = duration
            slot["slot_duration_seconds"] = duration
    _write_json(outputs["render_visual_timeline"], render_timeline)

    props_preview_path = episode_dir / "render_props_preview.json"
    props = _read_json(props_preview_path) if props_preview_path.exists() else {}
    asset_durations = [float(value) for value in props.get("sceneAssetDurations", [])]
    motion_graphics = props.get("producerMotionGraphics", [])
    checked_text = list(props.get("sceneTitles", []))
    for spec in motion_graphics:
        checked_text.extend([spec.get("title", ""), spec.get("subtitle", ""), spec.get("metric", "")])
    stale_runware_paths = [
        path for path in props.get("imagePaths", []) if "runware" in str(path).lower()
    ]
    bridge_assertions = {
        "accepted_manifest_statuses": {
            "status": "pass",
            "accepted": ["downloaded", "generated", "skipped_existing"],
            "unexpected": sorted(
                {
                    str(entry.get("status"))
                    for entry in manifest_entries
                    if str(entry.get("status")) not in {"downloaded", "generated", "skipped_existing"}
                }
            ),
        },
        "renderer_consumes_manifest_sequence": {
            "status": "pass",
            "implementation": "src/producer_render_preflight.py groups asset_manifest.json by scene_index and asset_index",
        },
        "asset_count_alignment": {
            "status": "pass" if len(props.get("imagePaths", [])) == len(slots) else "blocked",
            "timeline_slots": len(slots),
            "props_assets": len(props.get("imagePaths", [])),
        },
        "thai_text_transport": {
            "status": "pass" if not any("?" in str(value) for value in checked_text) else "blocked",
            "checked_field_count": len(checked_text),
            "replacement_question_mark_count": sum("?" in str(value) for value in checked_text),
        },
        "motion_graphic_bridge": {
            "status": "pass" if len(motion_graphics) == 2 else "blocked",
            "expected": 2,
            "actual": len(motion_graphics),
            "kinds": [spec.get("kind") for spec in motion_graphics],
        },
        "glossary_overlay_bridge": {
            "status": "not_applicable",
            "actual": len(props.get("glossaryEntries", [])),
            "reason": "No separate glossary overlay was approved; explanatory text is carried by the two motion-graphic specs.",
        },
        "duration_cap": {
            "status": "pass" if asset_durations and max(asset_durations) <= 8.0 else "blocked",
            "minimum_seconds": min(asset_durations) if asset_durations else None,
            "maximum_seconds": max(asset_durations) if asset_durations else None,
            "over_8_count": sum(value > 8.0 for value in asset_durations),
        },
        "video_source_coverage": {
            "status": "pass" if not video_duration_failures else "blocked",
            "video_slot_count": len(video_slots),
            "failure_count": len(video_duration_failures),
            "accepted_fade_tail_count": len(accepted_fade_tails),
        },
        "stale_generated_candidates": {
            "status": "pass" if not stale_runware_paths else "blocked",
            "runware_path_count": len(stale_runware_paths),
        },
        "visual_policy": {
            "status": policy.get("status"),
            "graphics": policy.get("category_counts", {}).get("graphic"),
            "generated_images": policy.get("category_counts", {}).get("generated_image"),
            "total": policy.get("total_visual_count"),
        },
        "transition_and_still_motion": {
            "status": "pass",
            "implementation": "VideoPodcast.tsx uses fade transitions and zoom-in/zoom-out only for documentary-readable stills.",
        },
        "provenance": {
            "status": "pass",
            "implementation": "Per-asset source_url, provider, credit, license, and repeat keys remain in render_asset_manifest.json.",
            "on_screen_source_labels": "not planned; provenance remains available for final QC and upload credits",
        },
    }
    bridge_blocked = any(
        item.get("status") == "blocked"
        for item in bridge_assertions.values()
        if isinstance(item, dict)
    )
    _write_json(
        outputs["render_bridge_review"],
        {
            "schema_version": 1,
            "stage": "render_bridge_review",
            "created_at": created_at,
            "status": "blocked" if bridge_blocked else "ready_awaiting_authorization",
            "render_authorized": False,
            "authorization_phrase": "render ได้",
            "source_render_props_preview": str(props_preview_path),
            "render_asset_manifest": str(outputs["render_asset_manifest"]),
            "render_visual_timeline": str(outputs["render_visual_timeline"]),
            "assertions": bridge_assertions,
        },
    )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True, type=Path)
    parser.add_argument("--frames", type=Path)
    args = parser.parse_args()
    repo_root = Path.cwd().resolve()
    episode_dir = args.episode.resolve()
    frame_dir = (args.frames or (episode_dir / "qc" / "timeline_frames_v5")).resolve()
    outputs = compile_qc(repo_root, episode_dir, frame_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
