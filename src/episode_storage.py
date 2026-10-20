"""User-directed storage clean-up for finished Producer Mode episodes in `.mp/`.

Nothing here runs on its own: the producer asks, Claude runs the CLI. Removals are never hard deletes. Every removed
file is moved into `.mp/_trash/<stamp>-<stage>-<episode>/` with its relative path kept, and the producer empties that
folder. An episode is pruned or archived only with proof that it is on YouTube (a verified upload receipt) or a
recorded confirmation in the producer's own words.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
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


DECISIONS = ("keep", "prune", "archive", "remove")


def confirm(episode: Path, user_message: str, url: str | None = None, decision: str | None = None) -> dict[str, Any]:
    """Record the producer's own words: that the episode is on YouTube, or what to do with an undecided folder."""
    if not user_message.strip():
        raise ValueError("user_message must be the producer's actual words")
    if decision is not None and decision not in DECISIONS:
        raise ValueError(f"decision must be one of {', '.join(DECISIONS)}")
    record = {"kind": "producer_decision" if decision else "manual_upload", "user_message": user_message,
              "url": url, "decision": decision, "confirmed_at": utc_now()}
    (episode / "upload_pack").mkdir(exist_ok=True)
    write_json(episode / "upload_pack" / CONFIRMATION_NAME, record)
    return record


def reference_files(repo_root: Path) -> list[Path]:
    """Live reference docs whose episode paths follow an archive. Historical specs, plans and postmortems are left alone."""
    fixed = [repo_root / "completed_topics.md", repo_root / "doc_renderer" / "gfx_kit" / "LIBRARY.md"]
    skills = sorted(repo_root.glob(".claude/skills/moneyprinter-*/**/*.md"))
    return [path for path in [*fixed, *skills] if path.is_file()]


def referenced_by(repo_root: Path, name: str) -> list[Path]:
    needle = f".mp/{name}"
    return [path for path in reference_files(repo_root) if needle in path.read_text(encoding="utf-8")]


def apply_remove(episode: Path, mp_root: Path, repo_root: Path, now: datetime) -> Path:
    """Move a whole folder to trash with no archive record. Only on the producer's explicit "remove" decision."""
    decision = read_json(episode / "upload_pack" / CONFIRMATION_NAME)
    if decision.get("kind") != "producer_decision" or decision.get("decision") != "remove":
        raise NotProven(f"{episode.name}: removing a whole folder needs the producer's recorded remove decision")
    references = referenced_by(repo_root, episode.name)
    if references:
        names = ", ".join(str(path.relative_to(repo_root)) for path in references)
        raise ValueError(f"{episode.name} is referenced by {names}; archive it instead of removing it")
    return stage_to_trash(episode, [episode], "remove", mp_root, now)


# What Claude reads back from a finished episode. Applied with `matches`, so Shorts sub-folders are covered too.
ARCHIVE_KEEP = (
    "producer_plan.json", "script.json", "draft_v*.md", "research_dossier.md", "sequence_plan.md", "metadata.json",
    "cost_report.json", "final_qc.json", "review_check.json", "spoken_thai_review.json", "sequence_review.json",
    "review/*.json", "upload_pack/*.json", "upload_pack/*.txt", "upload_pack/*.md",
    "graphics/*.js", "graphics/*.json", "graphics/*.md",
)
INDEX_HEADER = "# Episode archive\n\n| Published | Title | Folder | YouTube | Style |\n|---|---|---|---|---|\n"


def video_duration(video: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                            capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def still_times(duration: float, chapters: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Opening frames every 3 s across the first minute, then one frame at each chapter's midpoint."""
    times: list[tuple[str, float]] = [(f"opening_{t:03d}s.jpg", t) for t in range(0, min(60, int(duration)), 3)]
    starts = sorted(float(chapter.get("start_seconds") or 0) for chapter in chapters)
    for index, start in enumerate(starts, 1):
        end = starts[index] if index < len(starts) else duration
        times.append((f"chapter_{index:02d}.jpg", (start + end) / 2))
    return times


def extract_stills(video: Path, out_dir: Path, times: list[tuple[str, float]]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stills = []
    for name, seconds in times:
        target = out_dir / name
        result = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{seconds:.2f}", "-i", str(video), "-frames:v", "1",
                                 "-vf", "scale=960:-2", "-q:v", "4", str(target)], capture_output=True, text=True)
        if result.returncode != 0 or not target.exists():
            raise RuntimeError(f"ffmpeg could not extract {name} at {seconds:.2f}s: {result.stderr.strip()}")
        stills.append(target)
    return stills


def _metadata(episode: Path) -> dict[str, Any]:
    return read_json(episode / "metadata.json") or read_json(episode / "upload_pack" / "metadata.json")


def _style(episode: Path) -> str:
    renderer = (read_json(episode / "producer_plan.json").get("render_settings") or {}).get("renderer") or "—"
    graphics = episode / "graphics"
    looks = sorted(path.name for path in graphics.iterdir() if path.is_dir()) if graphics.is_dir() else []
    return " · ".join([renderer, *looks])


def _clock(seconds: float | None) -> str:
    return "—" if seconds is None else f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def write_summary(episode: Path, archive_dir: Path, proof: dict[str, Any], stills: list[Path], notes: list[str],
                  duration: float | None = None) -> Path:
    """One page assembled from the episode's own files; no model call. Missing sources print as "—"."""
    metadata = _metadata(episode)
    plan = read_json(episode / "producer_plan.json")
    cost = (read_json(episode / "cost_report.json").get("totals") or {}).get("estimated_total_cost_usd")
    tts = read_json(episode / "tts_manifest.json")
    voice = " / ".join(str(tts[key]) for key in ("provider", "model", "tone_preset") if tts.get(key)) or "—"
    acceptance = read_json(episode / "final_qc.json").get("acceptance") or {}
    lines = [
        f"# {metadata.get('title') or episode.name}", "",
        f"- Folder: `{episode.name}`",
        f"- YouTube: {proof.get('url') or '—'} (video id {proof.get('video_id') or '—'})",
        f"- Proof: {proof.get('kind')}" + (f" — \"{proof['user_message']}\"" if proof.get("user_message") else ""),
        f"- Published: {proof.get('published') or '—'}",
        f"- Duration: {_clock(duration)}",
        f"- Cost: {'—' if cost is None else f'${cost:.2f}'}",
        f"- Style: {_style(episode)}",
        f"- Voice: {voice}", "",
        "## Chapters", "",
        *([f"- {chapter.get('timestamp') or _clock(chapter.get('start_seconds'))} {chapter.get('title', '')}"
          for chapter in metadata.get("chapters") or []] or ["—"]), "",
        "## Sections", "",
        *([f"{section.get('section_index', index)}. {section.get('title', '')}"
          for index, section in enumerate(plan.get("sections") or [], 1)] or ["—"]), "",
        "## QC acceptance", "",
        *([f"- {key}: {value.get('status')}" for key, value in acceptance.items() if isinstance(value, dict)] or ["—"]), "",
        "## Notes", "",
        *([f"- {note}" for note in notes] or ["—"]), "",
        "## Stills", "",
        *([f"- `stills/{still.name}`" for still in stills] or ["—"]), "",
        "## Files kept", "",
        *[f"- `{path.relative_to(archive_dir).as_posix()}`" for path in sorted(archive_dir.rglob("*"))
          if path.is_file() and path.parent.name != "stills"],
    ]
    target = archive_dir / "SUMMARY.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def append_index(archive_root: Path, row: dict[str, Any]) -> Path:
    index = archive_root / "INDEX.md"
    if not index.exists():
        index.write_text(INDEX_HEADER, encoding="utf-8")
    cells = [str(row.get(key) or "—").replace("|", "/") for key in ("published", "title", "folder", "url", "style")]
    with index.open("a", encoding="utf-8") as stream:
        stream.write("| " + " | ".join(cells) + " |\n")
    return index


def repoint_references(repo_root: Path, name: str) -> list[Path]:
    old, new = f".mp/{name}", f".mp/{ARCHIVE_DIR}/{name}"
    changed = []
    for path in reference_files(repo_root):
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")
            changed.append(path)
    return changed


@dataclass
class ArchiveResult:
    archive_dir: Path
    trash_dir: Path
    repointed: list[Path]
    notes: list[str]


def archive_plan(episode: Path) -> tuple[list[Path], int]:
    files = sorted(_files(episode))
    keep = [path for path in files if matches(path.relative_to(episode).as_posix(), ARCHIVE_KEEP)]
    return keep, sum(path.stat().st_size for path in files)


def _copy_thumbnails(episode: Path, archive_dir: Path, notes: list[str]) -> None:
    """The thumbnail each receipt (episode and any Short) actually used, as `thumbnail<suffix>` beside that receipt."""
    for receipt_path in sorted(episode.rglob(RECEIPT_NAME)):
        owner = receipt_path.parent.parent
        recorded = read_json(receipt_path).get("thumbnail_path")
        if not recorded:
            continue
        name = PureWindowsPath(recorded).name
        candidates = [Path(recorded), owner / "thumbnails" / name]
        source = next((path for path in candidates if path.is_file()), None)
        if source is None:
            notes.append("thumbnail missing" if owner == episode else f"thumbnail missing for {owner.name}")
            continue
        target = archive_dir / owner.relative_to(episode) / f"thumbnail{source.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def apply_archive(episode: Path, mp_root: Path, repo_root: Path, now: datetime) -> ArchiveResult:
    """Copy the reference record into `.mp/archive/<name>/`, then stage the whole episode in trash (last, so a failure
    before it leaves the episode untouched), then repoint live reference docs."""
    proof = require_proof(episode, "archive")
    archive_dir = mp_root / ARCHIVE_DIR / episode.name
    if archive_dir.exists():
        raise ValueError(f"{archive_dir} already exists; this episode was archived before")
    keep, _ = archive_plan(episode)
    notes: list[str] = []
    archive_dir.mkdir(parents=True)
    try:
        for path in keep:
            target = archive_dir / path.relative_to(episode)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        _copy_thumbnails(episode, archive_dir, notes)
        final = episode / "final.mp4"
        stills: list[Path] = []
        duration = None
        if final.exists():
            duration = video_duration(final)
            stills = extract_stills(final, archive_dir / "stills",
                                    still_times(duration, _metadata(episode).get("chapters") or []))
        else:
            notes.append("final.mp4 already gone, no stills")
        write_summary(episode, archive_dir, proof, stills, notes, duration)
        append_index(mp_root / ARCHIVE_DIR, {"published": proof.get("published"), "title": _metadata(episode).get("title"),
                                             "folder": f"`{ARCHIVE_DIR}/{episode.name}`", "url": proof.get("url"),
                                             "style": _style(episode)})
    except BaseException:
        shutil.rmtree(archive_dir)  # only the copies made above
        raise
    trash = stage_to_trash(episode, [episode], "archive", mp_root, now)
    return ArchiveResult(archive_dir, trash, repoint_references(repo_root, episode.name), notes)
