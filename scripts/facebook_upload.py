#!/usr/bin/env python3
"""User-directed Facebook Page Reel upload for a finished Short (no automation; every post needs the user's explicit message)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import facebook_upload as fb  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("request", "upload", "status"))
    parser.add_argument("--short", required=True, help="The Short's script.json (its folder holds upload_pack/)")
    parser.add_argument("--publish-at", help="request: ISO time with offset, e.g. 2026-10-27T12:00+07:00 (10 min to 29 days ahead)")
    parser.add_argument("--publish-now", action="store_true", help="request: post publicly right away instead of scheduling")
    parser.add_argument("--user-message", default="", help="The user's actual instruction; never invent it")
    parser.add_argument("--dry-run", action="store_true", help="request: validate and print without writing the request")
    args = parser.parse_args()

    short_dir = Path(args.short).resolve().parent
    pack = short_dir / "upload_pack"
    if args.action == "request":
        request = fb.build_request(short_dir, user_message=args.user_message, publish_at=args.publish_at,
                                   publish_now=args.publish_now)
        if not args.dry_run:
            fb.write_json(pack / fb.REQUEST_NAME, request)
        print(json.dumps({k: request.get(k) for k in ("video_state", "scheduled_publish_at", "video_seconds", "video_path")},
                         ensure_ascii=False))
    elif args.action == "upload":
        receipt = fb.upload(short_dir, log=lambda line: print(line, flush=True))
        print(json.dumps(_summary(receipt), ensure_ascii=False))
    else:
        receipt = fb.read_json(pack / fb.RECEIPT_NAME)
        if receipt.get("video_id"):
            receipt = fb.refresh_status(short_dir)
        print(json.dumps({"state": fb.upload_state(receipt), **_summary(receipt)}, ensure_ascii=False))
    return 0


def _summary(receipt: dict) -> dict:
    last = receipt.get("last_status") or {}
    return {"status": receipt.get("status"), "video_id": receipt.get("video_id"),
            "scheduled_publish_at": receipt.get("scheduled_publish_at"), "permalink_url": last.get("permalink_url"),
            "facebook_status": last.get("status")}


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
