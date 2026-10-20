#!/usr/bin/env python3
"""User-directed storage clean-up for finished episodes (no automation; removals are staged in .mp/_trash)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import episode_storage as es  # noqa: E402

GB = 1024 ** 3
FREED_NOTE = "Space is freed after emptying .mp/_trash (scripts/empty_episode_trash.bat)."


def _gb(size: int) -> float:
    return round(size / GB, 2)


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def status() -> None:
    totals: dict[str, list[float]] = {}
    for item in es.classify(es.MP_ROOT, ROOT / "completed_topics.md", datetime.now(timezone.utc)):
        _emit({"name": item.name, "bucket": item.bucket, "gb": _gb(item.size_bytes), "has_final": item.has_final,
               "proof": item.proof_kind, "last_modified": item.last_modified.date().isoformat()})
        totals.setdefault(item.bucket, []).append(item.size_bytes)
    for bucket, sizes in sorted(totals.items()):
        _emit({"bucket_total": bucket, "folders": len(sizes), "gb": _gb(sum(sizes))})


def prune(episode: Path, apply: bool) -> None:
    if not apply:
        es.require_proof(episode, "prune")
        plan = es.prune_plan(episode)
        _emit({"episode": episode.name, "stage": "prune", "files": len(plan.remove), "gb": _gb(plan.remove_bytes),
               "unclassified_kept": [{"path": p.relative_to(episode).as_posix(), "gb": _gb(p.stat().st_size)}
                                     for p in plan.unclassified],
               "note": "DRY_RUN — rerun with --apply"})
        return
    plan, trash = es.apply_prune(episode, es.MP_ROOT, datetime.now(timezone.utc))
    _emit({"episode": episode.name, "stage": "prune", "files": len(plan.remove), "gb": _gb(plan.remove_bytes),
           "trash": _rel(trash) if trash else None, "note": FREED_NOTE})


def archive(episode: Path, apply: bool) -> None:
    if not apply:
        es.require_proof(episode, "archive")
        keep, total = es.archive_plan(episode)
        _emit({"episode": episode.name, "stage": "archive", "folder_gb": _gb(total),
               "keep": [p.relative_to(episode).as_posix() for p in keep],
               "has_final_for_stills": (episode / "final.mp4").exists(),
               "referenced_by": [_rel(p) for p in es.referenced_by(ROOT, episode.name)],
               "note": "DRY_RUN — rerun with --apply"})
        return
    size = sum(p.stat().st_size for p in episode.rglob("*") if p.is_file())
    result = es.apply_archive(episode, es.MP_ROOT, ROOT, datetime.now(timezone.utc))
    _emit({"episode": episode.name, "stage": "archive", "archive": _rel(result.archive_dir),
           "trash": _rel(result.trash_dir), "gb": _gb(size), "repointed": [_rel(p) for p in result.repointed],
           "notes": result.notes, "note": FREED_NOTE})


def remove(episode: Path, apply: bool) -> None:
    if not apply:
        size = sum(p.stat().st_size for p in episode.rglob("*") if p.is_file())
        _emit({"episode": episode.name, "stage": "remove", "gb": _gb(size),
               "referenced_by": [_rel(p) for p in es.referenced_by(ROOT, episode.name)],
               "note": "DRY_RUN — rerun with --apply"})
        return
    size = sum(p.stat().st_size for p in episode.rglob("*") if p.is_file())
    trash = es.apply_remove(episode, es.MP_ROOT, ROOT, datetime.now(timezone.utc))
    _emit({"episode": episode.name, "stage": "remove", "gb": _gb(size), "trash": _rel(trash), "note": FREED_NOTE})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "confirm", "prune", "archive", "remove"))
    parser.add_argument("--episode", nargs="+", default=[], help="Folder name(s) or path(s) under .mp/")
    parser.add_argument("--apply", action="store_true", help="Move files to .mp/_trash (default is a dry-run)")
    parser.add_argument("--user-message", default="", help="confirm: the producer's actual words; never invent them")
    parser.add_argument("--url", help="confirm: YouTube URL when the producer gives one")
    parser.add_argument("--decision", choices=es.DECISIONS, help="confirm: the producer's decision for an undecided folder")
    args = parser.parse_args()

    if args.action == "status":
        status()
        return 0
    if not args.episode:
        parser.error("--episode is required")
    if args.action in {"confirm", "remove"} and len(args.episode) != 1:
        parser.error(f"{args.action} takes exactly one --episode")
    failed = False
    for value in args.episode:
        try:
            episode = es.resolve_episode(value, es.MP_ROOT)
            if args.action == "confirm":
                _emit(es.confirm(episode, args.user_message, url=args.url, decision=args.decision))
            else:
                {"prune": prune, "archive": archive, "remove": remove}[args.action](episode, args.apply)
        except ValueError as error:  # NotProven is a ValueError
            print(f"{value}: {error}", file=sys.stderr, flush=True)
            failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
