#!/usr/bin/env python3
"""Pad scene WAVs with planned breath pauses and the opening-sting lead (see src/producer_breaths.py).

Run after produce-tts and audio-qc, before building the speech map:
    python scripts/producer_pad_breaths.py --plan <producer_plan.json>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()
    from producer_breaths import pad_breaths

    result = pad_breaths(Path(args.plan).resolve().parent)
    scenes = result["scenes"]
    print(f"[OK] lead {result['opening_seconds']:.1f}s, padded {sum(1 for s in scenes if s['breath_after_seconds'])} scenes, "
          f"+{sum(s['breath_after_seconds'] for s in scenes):.1f}s breaths")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
