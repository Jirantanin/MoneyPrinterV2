#!/usr/bin/env python3
"""Render minimal_doc inspection stills for a prepared episode through the real render code path.

Run after `render-preflight` or `producer_review.py prepare`; never renders video.
    python scripts/minimal_doc_stills.py --plan <producer_plan.json> --times 3,66,570
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--times", required=True, help="Comma-separated seconds, e.g. 3,66.2,570")
    args = parser.parse_args()
    from producer_minimal_renderer import render_minimal_stills

    episode = Path(args.plan).resolve().parent
    preflight = json.loads((episode / "render_preflight.json").read_text(encoding="utf-8"))
    props = preflight.get("props_preview") or json.loads((episode / "render_props_preview.json").read_text(encoding="utf-8"))
    if props.get("renderer") != "minimal_doc":
        parser.error("render_settings.renderer is not minimal_doc for this episode")
    narration_end = float(preflight["summary"]["narration_duration_seconds"])
    out = render_minimal_stills(root_dir=ROOT, episode_dir=episode, raw_props=props, narration_end=narration_end,
                                times=[float(t) for t in args.times.split(",") if t.strip()],
                                log_path=episode / "minimal_stills.log")
    print(f"[OK] stills in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
