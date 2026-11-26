#!/usr/bin/env python3
"""User-directed Facebook Page photo post (image + caption) for the daily fact posts; no automation, every post needs
the user's explicit message. A post folder holds post.json {"caption", "image", "sources", "topic"} and the image."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import facebook_post as fp  # noqa: E402
import facebook_upload as fb  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("request", "post", "status", "scheduled"))
    parser.add_argument("--post", help="The post folder's post.json (request/post/status)")
    parser.add_argument("--publish-at", help="request: ISO time with offset, e.g. 2026-11-27T08:00+07:00 (10 min to 29 days ahead)")
    parser.add_argument("--publish-now", action="store_true", help="request: post publicly right away instead of scheduling")
    parser.add_argument("--user-message", default="", help="The user's actual instruction; never invent it")
    parser.add_argument("--dry-run", action="store_true", help="request: validate and print without writing the request")
    args = parser.parse_args()

    if args.action == "scheduled":
        for row in fp.scheduled_posts():
            when = datetime.fromtimestamp(fb._unix(row.get("scheduled_publish_time")), timezone.utc).astimezone()
            first_line = (row.get("message") or "").splitlines()[0][:60] if row.get("message") else ""
            print(json.dumps({"at": when.isoformat(timespec="minutes"), "id": row.get("id"), "message": first_line},
                             ensure_ascii=False))
        return 0
    if not args.post:
        parser.error("--post is required for request/post/status")
    post_dir = Path(args.post).resolve().parent
    if args.action == "request":
        request = fp.build_request(post_dir, user_message=args.user_message, publish_at=args.publish_at,
                                   publish_now=args.publish_now)
        if not args.dry_run:
            fb.write_json(post_dir / fp.REQUEST_NAME, request)
        print(json.dumps({k: request.get(k) for k in ("published", "scheduled_publish_at", "image_bytes", "image_path")},
                         ensure_ascii=False))
    elif args.action == "post":
        receipt = fp.post(post_dir, log=lambda line: print(line, flush=True))
        print(json.dumps(_summary(receipt), ensure_ascii=False))
    else:
        receipt = fb.read_json(post_dir / fp.RECEIPT_NAME)
        if receipt.get("photo_id"):
            receipt = fp.refresh_status(post_dir)
        print(json.dumps({"state": fp.post_state(receipt), **_summary(receipt)}, ensure_ascii=False))
    return 0


def _summary(receipt: dict) -> dict:
    last = receipt.get("last_status") or {}
    return {"status": receipt.get("status"), "post_id": receipt.get("post_id"),
            "scheduled_publish_at": receipt.get("scheduled_publish_at"), "permalink_url": last.get("permalink_url")}


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
