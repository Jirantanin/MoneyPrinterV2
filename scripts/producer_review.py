#!/usr/bin/env python3
"""Offline review and explicit revision authorization; never renders video."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_contract import (  # noqa: E402
    episode_spec, production_review, read_json, render_revision, script_revision,
)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "scaffold", "prepare", "authorize"))
    parser.add_argument("--plan", required=True)
    parser.add_argument("--user-message", help="Actual explicit user render authorization; never invent it")
    parser.add_argument("--output", help="Optional report path; check otherwise writes nothing")
    args = parser.parse_args()
    plan_path = Path(args.plan).resolve()
    folder = plan_path.parent
    plan = read_json(plan_path)
    if not isinstance(plan, dict):
        parser.error("Plan is missing or not an object")
    scenes = read_json(folder / "script.json", [])
    report = production_review(plan, scenes)
    now = datetime.now(timezone.utc).isoformat()
    if args.action == "scaffold":
        # Do not rewrite source plans or existing reviews. Producer merges reviewed records explicitly.
        scaffold = folder / "producer_review_template.json"
        if scaffold.exists():
            parser.error("Review template exists; preserve it and use check")
        write_json(scaffold, {
            "episode_spec": episode_spec(plan),
            "claim_reviews": {item["claim_id"]: {
                "claim": item["claim"], "script_revision": report["fact_check_report"]["script_revision"],
                "status": "mapped" if item["source_ids"] else "unsupported",
                "reviewer": None, "reviewed_at": None, "allowed_wording": None, "limitations": "",
                "evidence": [],
            } for item in report["fact_check_report"]["claims"]},
            "editorial_review": {"status": "pending", "script_revision": script_revision(scenes),
                                 "reviewer": None, "reviewed_at": None, "opening_test": None,
                                 "section_progression": [], "ending_payoff": None,
                                 "redundancy_review": None, "claim_coverage_review": None},
        })
        print(f"Pending review template: {scaffold}")
        return 0
    if args.action == "prepare":
        if report["status"] != "pass":
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        from producer_mode import run_render_preflight_checkpoint, run_render_video_checkpoint
        run_render_preflight_checkpoint(plan_path)
        outputs = run_render_video_checkpoint(plan_path, no_render=True)
        prepared = read_json(outputs["render_manifest"], {})
        if prepared.get("status") != "prepared":
            print(json.dumps(prepared, ensure_ascii=False, indent=2))
            return 1
        # Pin the exact prepared mix, including the disabled-bed case with an older mix on disk.
        preflight_path = folder / "render_preflight.json"
        preflight = read_json(preflight_path, {})
        preflight["props_preview"] = read_json(outputs["render_props"], {})
        write_json(preflight_path, preflight)
        write_json(folder / "render_props_preview.json", preflight["props_preview"])
        revision = render_revision(folder, preflight, ROOT)
        report.update({"revision": revision, "render_gate": "awaiting_user_authorization"})
        write_json(folder / "prepared_revision.json", {"revision": revision, "prepared_at": now})
    if args.action == "authorize":
        if not args.user_message or not args.user_message.strip():
            parser.error("--user-message must quote actual explicit render consent for this prepared revision")
        prepared = read_json(folder / "prepared_revision.json", {})
        preflight = read_json(folder / "render_preflight.json", {})
        revision = render_revision(folder, preflight, ROOT)
        if report["status"] != "pass" or preflight.get("status") != "ready" or prepared.get("revision") != revision:
            parser.error("Prepare and review the current revision before recording authorization")
        authorization = {"revision": revision, "authorized_by": "user", "user_message": args.user_message,
                         "authorized_at": now, "technical_retry_limit": 2}
        write_json(folder / "render_authorization.json", authorization)
        report.update({"revision": revision, "render_gate": "authorized"})
    if args.output:
        write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
