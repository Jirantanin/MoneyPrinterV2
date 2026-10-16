#!/usr/bin/env python3
"""Per-episode YouTube review: stats, traffic, comments and retention mapped onto the episode's scenes (read-only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import youtube_review as review  # noqa: E402
import youtube_upload as yt  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Episode producer_plan.json")
    parser.add_argument("--days", type=int, help="Cut the window at N days after publishing (e.g. 7, 28); default: up to today")
    parser.add_argument("--channel-id", default=yt.DEFAULT_CHANNEL_ID)
    args = parser.parse_args()

    episode = Path(args.plan).resolve().parent
    data = review.fetch(episode, days=args.days, channel_id=args.channel_id)
    path = review.write_review(episode, review.build_review(episode, data))
    print(path)
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
