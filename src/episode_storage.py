"""User-directed storage clean-up for finished Producer Mode episodes in `.mp/`.

Nothing here runs on its own: the producer asks, Claude runs the CLI. Removals are never hard deletes. Every removed
file is moved into `.mp/_trash/<stamp>-<stage>-<episode>/` with its relative path kept, and the producer empties that
folder. An episode is pruned or archived only with proof that it is on YouTube (a verified upload receipt) or a
recorded confirmation in the producer's own words.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from fnmatch import fnmatch
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from youtube_upload import RECEIPT_NAME, read_json, utc_now, write_json

ROOT = Path(__file__).resolve().parents[1]
MP_ROOT = ROOT / ".mp"
ARCHIVE_DIR = "archive"
TRASH_DIR = "_trash"
CONFIRMATION_NAME = "manual_upload_confirmation.json"
MANIFEST_NAME = "upload_pack_manifest.json"
SKIP_DIRS = {"fonts", "oauth_backups", ARCHIVE_DIR, TRASH_DIR}
LARGE_BYTES = 50 * 1024 * 1024
EMPTY_BYTES = 1024 * 1024
IN_PROGRESS_WINDOW = timedelta(days=7)
TOPIC_LINK = re.compile(r"\.mp/([^/\s)\]|]+)")


class NotProven(ValueError):
    """The episode has no proof of upload (or no producer decision) for the requested action."""


def upload_proof(episode: Path) -> dict[str, Any] | None:
    """A verified receipt wins; otherwise the producer's recorded confirmation; otherwise None."""
    receipt = read_json(episode / "upload_pack" / RECEIPT_NAME)
    if receipt.get("video_id") and str(receipt.get("status", "")).endswith("_verified"):
        return {"kind": "receipt", "url": receipt.get("url"), "video_id": receipt["video_id"],
                "published": receipt.get("publishAt") or receipt.get("uploaded_at"),
                "thumbnail_path": receipt.get("thumbnail_path")}
    confirmation = read_json(episode / "upload_pack" / CONFIRMATION_NAME)
    return confirmation if confirmation.get("kind") in {"manual_upload", "producer_decision"} else None


def group_key(name: str) -> str:
    return name.split("_revision_")[0].split("_pilot_")[0]


def completed_topic_names(topics_file: Path) -> set[str]:
    if not topics_file.exists():
        return set()
    return set(TOPIC_LINK.findall(topics_file.read_text(encoding="utf-8")))


@dataclass
class FolderStatus:
    name: str
    path: Path
    bucket: str
    size_bytes: int
    has_final: bool
    proof_kind: str | None
    last_modified: datetime


def _files(folder: Path) -> list[Path]:
    return [path for path in folder.rglob("*") if path.is_file()]


def _folder_status(folder: Path) -> FolderStatus:
    files = _files(folder)
    stats = [path.stat() for path in files]
    newest = max((stat.st_mtime for stat in stats), default=folder.stat().st_mtime)
    proof = upload_proof(folder)
    return FolderStatus(name=folder.name, path=folder, bucket="", size_bytes=sum(stat.st_size for stat in stats),
                        has_final=(folder / "final.mp4").exists(), proof_kind=proof["kind"] if proof else None,
                        last_modified=datetime.fromtimestamp(newest, timezone.utc))


def classify(mp_root: Path, topics_file: Path, now: datetime) -> list[FolderStatus]:
    """Sort every episode-like folder under `.mp/` into uploaded / decided / probably_uploaded / undecided / in_progress."""
    folders = sorted((path for path in mp_root.iterdir() if path.is_dir() and path.name not in SKIP_DIRS),
                     key=lambda path: path.name)
    statuses = [_folder_status(folder) for folder in folders]
    uploaded_groups = {group_key(s.name) for s in statuses if s.proof_kind in {"receipt", "manual_upload"}}
    topics = completed_topic_names(topics_file)
    for status in statuses:
        if status.proof_kind in {"receipt", "manual_upload"}:
            status.bucket = "uploaded"
        elif status.proof_kind == "producer_decision":
            status.bucket = "decided"
        elif group_key(status.name) in uploaded_groups:
            status.bucket = "undecided"
        elif "_pilot_" in status.name or status.name.startswith("voice_audition") or status.size_bytes < EMPTY_BYTES:
            status.bucket = "undecided"
        elif status.name in topics or (status.path / "upload_pack" / MANIFEST_NAME).exists():
            status.bucket = "probably_uploaded"
        elif now - status.last_modified <= IN_PROGRESS_WINDOW:
            status.bucket = "in_progress"
        else:
            status.bucket = "undecided"
    return statuses


# Regenerable from the files prune keeps. Each pattern also matches inside sub-folders such as shorts_promo_gfx/.
PRUNE_REMOVE = (
    "graphics/*.mp4", "minimal_render/*", "merged_audio*.wav", "score/*.wav", "sfx/*.wav", "audio_rejected/*",
    "final_rev_*.mp4", "final_video_only.mp4", "rejected/*", "rejected_renders/*", "review/*.mp4", "review/*.jpg",
    "review/*.png", "review/*.wav", "review/*.mp3", "duplicate_frame_audit_v*/*",
)


def matches(rel: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(rel, pattern) or fnmatch(rel, "*/" + pattern) for pattern in patterns)


@dataclass
class StoragePlan:
    episode: Path
    stage: str
    remove: list[Path]
    unclassified: list[Path]
    remove_bytes: int


def prune_plan(episode: Path) -> StoragePlan:
    remove: list[Path] = []
    unclassified: list[Path] = []
    for path in sorted(_files(episode)):
        if matches(path.relative_to(episode).as_posix(), PRUNE_REMOVE):
            remove.append(path)
        elif path.name != "final.mp4" and path.stat().st_size > LARGE_BYTES:
            unclassified.append(path)
    return StoragePlan(episode, "prune", remove, unclassified, sum(path.stat().st_size for path in remove))


def require_proof(episode: Path, action: str) -> dict[str, Any]:
    proof = upload_proof(episode)
    if proof is None or (proof["kind"] == "producer_decision" and proof.get("decision") != action):
        raise NotProven(f"{episode.name}: no upload receipt or producer confirmation for {action}")
    return proof


def stage_to_trash(episode: Path, paths: list[Path], stage: str, mp_root: Path, now: datetime) -> Path | None:
    """Move `paths` (files inside `episode`, or `[episode]` itself) into a fresh `.mp/_trash/` folder."""
    if not paths:
        return None
    trash = mp_root / TRASH_DIR / f"{now:%Y%m%d-%H%M%S}-{stage}-{episode.name}"
    if trash.exists():
        raise FileExistsError(f"trash folder already exists: {trash}")
    trash.parent.mkdir(parents=True, exist_ok=True)
    if paths == [episode]:
        shutil.move(str(episode), str(trash))
        return trash
    for path in paths:
        target = trash / path.relative_to(episode)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
    return trash


def apply_prune(episode: Path, mp_root: Path, now: datetime) -> tuple[StoragePlan, Path | None]:
    require_proof(episode, "prune")
    plan = prune_plan(episode)
    return plan, stage_to_trash(episode, plan.remove, "prune", mp_root, now)
