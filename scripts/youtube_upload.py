#!/usr/bin/env python3
"""User-directed YouTube upload for a finished episode (no automation; every step needs the user's explicit message)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import youtube_upload as yt  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("reconnect", "request", "upload", "schedule", "status"))
    parser.add_argument("--plan", help="Episode producer_plan.json")
    parser.add_argument("--thumbnail", help="request: chosen thumbnail image")
    parser.add_argument("--publish-at", help="ISO time with offset, e.g. 2026-10-05T18:30+07:00; omit to stay private")
    parser.add_argument("--title", help="request: override metadata title (must be the user-approved title)")
    parser.add_argument("--user-message", default="", help="The user's actual instruction; never invent it")
    parser.add_argument("--channel-id", default=yt.DEFAULT_CHANNEL_ID)
    args = parser.parse_args()

    if args.action == "reconnect":
        yt.reconnect()
        print("YOUTUBE_RECONNECTED")
        return 0
    if not args.plan:
        parser.error("--plan is required")
    episode = Path(args.plan).resolve().parent
    pack = episode / "upload_pack"
    if args.action == "request":
        if not args.thumbnail:
            parser.error("--thumbnail is required")
        request = yt.build_request(episode, thumbnail=Path(args.thumbnail), user_message=args.user_message,
                                   publish_at=args.publish_at, title=args.title)
        yt.write_json(pack / yt.REQUEST_NAME, request)
        print(json.dumps({k: request[k] for k in ("title", "thumbnail_path", "privacyStatus", "publishAt")}, ensure_ascii=False))
    elif args.action == "upload":
        receipt = yt.upload(episode, channel_id=args.channel_id, log=lambda line: print(line, flush=True))
        status = (receipt.get("verification") or {}).get("status", {})
        print(json.dumps({"url": receipt.get("url"), "status": receipt["status"], "privacy": status.get("privacyStatus"),
                          "publishAt": status.get("publishAt")}, ensure_ascii=False))
    elif args.action == "schedule":
        if not args.publish_at:
            parser.error("--publish-at is required")
        record = yt.schedule(episode, publish_at=args.publish_at, user_message=args.user_message, channel_id=args.channel_id)
        print(json.dumps(record["youtube_status"], ensure_ascii=False))
    else:
        receipt = yt.read_json(pack / yt.RECEIPT_NAME)
        if not receipt.get("video_id"):
            print(json.dumps({"state": yt.upload_state(receipt)}))
            return 0
        result = yt.video_status(yt.youtube_client(), receipt["video_id"])
        print(json.dumps({"url": receipt["url"], "status": result["status"],
                          "duration": result["contentDetails"].get("duration"),
                          "definition": result["contentDetails"].get("definition"),
                          "processing": result.get("processingDetails", {}).get("processingStatus")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
