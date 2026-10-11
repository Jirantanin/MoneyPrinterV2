"""Shared production contract. Recorded reviews are evidence, never auto-approval."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

THAI_MIN = 5500
THAI_MAX = 8000


def default_episode_spec() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "duration_class": "long_form_episode",
        "narrative": {"count_rule": "thai_unicode", "minimum": THAI_MIN, "maximum": THAI_MAX},
        "minimum_runtime_seconds": None,
        "aspect_ratio": "16:9",
        "max_visual_hold_seconds": 8.0,
    }


def episode_spec(plan: dict[str, Any]) -> dict[str, Any]:
    """Legacy plans get the documented default, never reinterpret old nonspace counts."""
    spec = {**default_episode_spec(), **(plan.get("episode_spec") or {})}
    spec["narrative"] = {**default_episode_spec()["narrative"], **spec["narrative"]}
    bounds = spec["narrative"]
    if bounds["count_rule"] != "thai_unicode":
        raise ValueError("episode_spec.narrative.count_rule must be thai_unicode")
    if not (0 < int(bounds["minimum"]) <= int(bounds["maximum"])):
        raise ValueError("episode_spec narrative requires 0 < minimum <= maximum")
    if spec["duration_class"] not in {"test_cut", "long_form_episode"}:
        raise ValueError("Unknown duration_class")
    for key in ("minimum_runtime_seconds", "max_visual_hold_seconds"):
        value = spec.get(key)
        if key == "max_visual_hold_seconds" and value is None:
            raise ValueError("episode_spec.max_visual_hold_seconds must be finite and positive")
        if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
            raise ValueError(f"episode_spec.{key} must be finite and positive")
    return spec


def thai_count(text: str) -> int:
    return sum("\u0e00" <= char <= "\u0e7f" for char in text)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def read_json(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def file_hash(path: Path) -> str:
    if not path.is_file():
        return "missing"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def narrative_review(text: str, plan: dict[str, Any], audio_seconds: float | None = None) -> dict[str, Any]:
    spec = episode_spec(plan)
    bounds = spec["narrative"]
    count = thai_count(text)
    exempt = spec["duration_class"] == "test_cut"
    passed = exempt or int(bounds["minimum"]) <= count <= int(bounds["maximum"])
    minimum = spec.get("minimum_runtime_seconds")
    runtime = "pending_audio"
    if audio_seconds is not None:
        runtime = "pass" if math.isfinite(audio_seconds) and audio_seconds > 0 and (minimum is None or audio_seconds >= minimum) else "fail"
    return {
        "status": "pass" if passed else "blocked", "blocking": not passed,
        "duration_class": spec["duration_class"], "thai_narrative_chars": count,
        "count_rule": "thai_unicode", "target_thai_chars_inclusive": bounds,
        "narrative_gate": "exempt_test_cut" if exempt else "pass" if passed else "fail",
        "chars_no_space": len("".join(text.split())), "chars_with_space": len(text),
        "audio_duration_seconds": audio_seconds, "minimum_runtime_seconds": minimum,
        "runtime_gate": runtime,
        "ready_for_asset_production": passed,
        "ready_for_final_render_review": passed and runtime == "pass",
        "notes": [] if passed else [f"Thai narration {count} is outside {bounds['minimum']}..{bounds['maximum']}. Revise substantive content or the explicit episode scope."],
    }


def script_revision(scenes: list[dict[str, Any]]) -> str:
    return fingerprint([{key: scene.get(key) for key in ("narration", "key_claims", "source_ids", "section_index", "non_factual")} for scene in scenes])


def claim_id(scene_index: int, claim: str) -> str:
    return f"scene_{scene_index:02d}_" + fingerprint(claim)[:16]


def claim_report(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    sources = {str(source["id"]): source for source in plan.get("research", {}).get("sources", []) if isinstance(source, dict) and source.get("id")}
    reviews = plan.get("claim_reviews") or {}
    revision = script_revision(scenes)
    claims = []
    for index, scene in enumerate(scenes, 1):
        declared = scene.get("key_claims") or []
        if scene.get("non_factual") is True and not declared:
            continue
        # Missing extraction stays unresolved, even when the scene has source IDs.
        for claim in declared or [str(scene.get("narration") or "")]:
            claim = str(claim).strip()
            cid = claim_id(index, claim)
            source_ids = [str(value) for value in scene.get("source_ids", [])]
            valid = [sid for sid in source_ids if sid in sources and sources[sid].get("url")]
            status = "mapped" if valid and declared else "unsupported"
            review = reviews.get(cid) or {}
            evidence = review.get("evidence") or []
            evidence_valid = bool(evidence) and all(
                isinstance(item, dict) and item.get("source_id") in valid
                and item.get("source_url") == sources[item["source_id"]].get("url")
                and item.get("excerpt") and item.get("locator") and item.get("accessed_at")
                and item.get("support_reason")
                for item in evidence
            )
            current = review.get("script_revision") == revision and review.get("claim") == claim
            if current and review.get("reviewer") and review.get("reviewed_at"):
                requested = review.get("status")
                if requested == "verified" and evidence_valid and declared and review.get("allowed_wording") and "limitations" in review:
                    status = "verified"
                elif requested in {"uncertain", "unsupported"}:
                    status = requested
            claims.append({"claim_id": cid, "scene": index, "claim": claim, "source_ids": valid,
                           "invalid_source_ids": [sid for sid in source_ids if sid not in valid],
                           "source_urls": [sources[sid]["url"] for sid in valid], "status": status,
                           "review": review if current else {}, "extraction_required": not bool(declared)})
    counts = {status: sum(item["status"] == status for item in claims) for status in ("mapped", "verified", "uncertain", "unsupported")}
    all_non_factual = bool(scenes) and all(scene.get("non_factual") is True for scene in scenes)
    return {"status": "pass" if (claims or all_non_factual) and counts["verified"] == len(claims) else "needs_review",
            "script_revision": revision, "claim_count": len(claims), "counts": counts,
            "unsupported_count": counts["unsupported"], "unverified_count": len(claims) - counts["verified"],
            "claims": claims, "sources": list(sources.values()),
            "policy": "Source mapping is not verification. Verified means a current, attributed evidence review was recorded; this validator does not independently establish truth."}


def production_review(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    length = narrative_review("\n".join(str(scene.get("narration") or "") for scene in scenes), plan)
    facts = claim_report(plan, scenes)
    editorial = plan.get("editorial_review") or {}
    editorial_ok = (editorial.get("status") == "pass" and editorial.get("script_revision") == script_revision(scenes)
                    and all(editorial.get(key) for key in ("reviewer", "reviewed_at", "opening_test", "section_progression", "ending_payoff", "redundancy_review", "claim_coverage_review")))
    errors = []
    if length["blocking"]:
        errors.extend(length["notes"])
    if facts["status"] != "pass":
        errors.append(f"{facts['unverified_count']} unverified claims; source IDs alone do not authorize production.")
    if not editorial_ok:
        errors.append("Current editorial review is missing or incomplete (including claim extraction coverage).")
    return {"status": "blocked" if errors else "pass", "errors": errors, "duration_review": length,
            "fact_check_report": facts, "editorial_review_current": editorial_ok}


def require_production_review(plan: dict[str, Any], scenes: list[dict[str, Any]]) -> None:
    report = production_review(plan, scenes)
    if report["errors"]:
        raise ValueError("Production review failed: " + " ".join(report["errors"]))


def sequence_review_passed(episode_dir: Path, slots: list[dict[str, Any]]) -> bool:
    review = read_json(episode_dir / "sequence_review.json", {})
    return bool(review.get("status") == "pass" and review.get("render_slots_revision") == fingerprint(slots)
                and review.get("reviewer") and review.get("reviewed_at") and review.get("decisions")
                and not review.get("unresolved_issues"))


def render_revision(episode_dir: Path, preflight: dict[str, Any], root_dir: Path) -> str:
    """Bind permission to props, actual inputs and renderer code, not mutable log timestamps."""
    props = preflight.get("props_preview") or {}
    plan = read_json(episode_dir / "producer_plan.json", {})
    paths = {episode_dir / name for name in ("script.json", "asset_manifest.json", "render_asset_manifest.json", "tts_manifest.json", "speech_map.json", "sequence_review.json")}
    paths.update(episode_dir.glob("scene_*.wav"))
    for raw in [*props.get("imagePaths", []), props.get("audioPath"), props.get("scene0VideoPath")]:
        if raw:
            path = Path(str(raw))
            paths.add(path if path.is_absolute() else root_dir / path)
    for group in ("asset_production", "audio_production"):
        key = "asset_manifest_artifact" if group == "asset_production" else "tts_manifest_artifact"
        if plan.get(group, {}).get(key):
            paths.add(Path(plan[group][key]))
    paths.update((root_dir / "remotion" / "src").rglob("*.tsx"))
    paths.update((root_dir / "remotion" / "src").rglob("*.ts"))
    paths.update((root_dir / "remotion" / "scripts").glob("*.mjs"))
    paths.update(root_dir / "src" / name for name in ("producer_renderer.py", "producer_render_preflight.py"))
    if props.get("renderer") == "minimal_doc":
        from producer_minimal_renderer import OVERRIDES_FILE, renderer_files
        paths.update(renderer_files(root_dir))
        paths.add(episode_dir / OVERRIDES_FILE)
    return fingerprint({"props": props, "episode_spec": episode_spec(plan),
                        "summary": preflight.get("summary"),
                        "script_review": {key: plan.get(key) for key in ("research", "claim_reviews", "editorial_review")},
                        "files": {str(path.resolve()): file_hash(path) for path in sorted(paths, key=str)}})


def validate_render_authorization(episode_dir: Path, preflight: dict[str, Any], root_dir: Path) -> dict[str, Any]:
    plan = read_json(episode_dir / "producer_plan.json", {})
    scenes = read_json(episode_dir / "script.json", [])
    require_production_review(plan, scenes)
    duration = narrative_review("\n".join(str(scene.get("narration") or "") for scene in scenes), plan,
                                float(preflight.get("summary", {}).get("narration_duration_seconds") or 0))
    if not duration["ready_for_final_render_review"]:
        raise ValueError("Measured narration duration does not satisfy episode_spec")
    revision = render_revision(episode_dir, preflight, root_dir)
    authorization = read_json(episode_dir / "render_authorization.json", {})
    if not (authorization.get("revision") == revision and authorization.get("authorized_by") == "user"
            and authorization.get("user_message") and authorization.get("authorized_at")):
        raise ValueError("Render requires explicit user authorization for the current prepared revision")
    attempts = read_json(episode_dir / "render_attempts.json", {})
    count = int(attempts.get("count", 0)) if attempts.get("authorization_id") == fingerprint(authorization) else 0
    if count >= 3:
        raise ValueError("Initial render plus two technical retries exhausted; report failure before requesting further attempts")
    return {"revision": revision, "authorization_id": fingerprint(authorization), "count": count + 1}
