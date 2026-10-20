"""Offline coverage for episode storage: proof of upload, classification, prune, archive (synthetic folders only)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import episode_storage as es  # noqa: E402

NOW = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)


def _write(path: Path, data: bytes | str = b"x", size: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)
    if size is not None:
        with path.open("r+b") as stream:
            stream.truncate(size)
    return path


def _receipt(episode: Path, status: str = "uploaded_verified", video_id: str | None = "abc", **extra) -> Path:
    payload = {"status": status, "url": f"https://www.youtube.com/watch?v={video_id}", **extra}
    if video_id:
        payload["video_id"] = video_id
    return _write(episode / "upload_pack" / "youtube_upload_receipt.json", json.dumps(payload, ensure_ascii=False))


def _age(path: Path, when: datetime) -> None:
    for item in [path, *path.rglob("*")]:
        os.utime(item, (when.timestamp(), when.timestamp()))


class StorageTestCase(unittest.TestCase):
    def _root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def _mp(self) -> Path:
        mp = self._root() / ".mp"
        mp.mkdir()
        return mp


class ProofTests(StorageTestCase):
    def test_receipt_with_verified_status_is_proof(self) -> None:
        mp = self._mp()
        for status in ("uploaded_verified", "scheduled_verified", "public_verified"):
            episode = mp / f"podcast_v2_{status}"
            _receipt(episode, status)
            self.assertEqual(es.upload_proof(episode)["kind"], "receipt", status)
        interrupted = mp / "podcast_v2_interrupted"
        _receipt(interrupted, "upload_interrupted")
        self.assertIsNone(es.upload_proof(interrupted))
        no_id = mp / "podcast_v2_no_id"
        _receipt(no_id, "scheduled_verified", video_id=None)
        self.assertIsNone(es.upload_proof(no_id))

    def test_confirmation_file_is_proof(self) -> None:
        episode = self._mp() / "podcast_v2_manual"
        _write(episode / "upload_pack" / es.CONFIRMATION_NAME,
               json.dumps({"kind": "manual_upload", "user_message": "ลงแล้ว"}, ensure_ascii=False))
        self.assertEqual(es.upload_proof(episode)["kind"], "manual_upload")


class ClassifyTests(StorageTestCase):
    def test_classify_buckets(self) -> None:
        mp = self._mp()
        old = NOW - timedelta(days=60)
        uploaded = mp / "podcast_v2_a_20261001"
        _receipt(uploaded)
        _write(uploaded / "final.mp4", size=2 * 1024 * 1024)
        _write(mp / "podcast_v2_a_20261001_revision_x_01" / "final.mp4", size=2 * 1024 * 1024)
        _write(mp / "podcast_v2_b_20260601" / "upload_pack" / "upload_pack_manifest.json", "{}")
        _write(mp / "podcast_v2_b_20260601" / "final.mp4", size=2 * 1024 * 1024)
        _write(mp / "podcast_v2_c_20260601" / "final.mp4", size=2 * 1024 * 1024)
        _write(mp / "voice_audition_20261010" / "take.wav", size=2 * 1024 * 1024)
        _write(mp / "podcast_v2_d_20261019" / "draft.wav", size=2 * 1024 * 1024)
        _write(mp / "podcast_v2_e_20260101" / "draft.wav", size=2 * 1024 * 1024)
        _write(mp / "fonts" / "Kanit-Bold.ttf")
        (mp / "archive").mkdir()
        (mp / "_trash").mkdir()
        _write(mp / "youtube.json", "{}")
        for name in ("podcast_v2_a_20261001", "podcast_v2_a_20261001_revision_x_01", "podcast_v2_b_20260601",
                     "podcast_v2_c_20260601", "voice_audition_20261010", "podcast_v2_e_20260101"):
            _age(mp / name, old)
        _age(mp / "podcast_v2_d_20261019", NOW - timedelta(days=1))
        topics = _write(mp.parent / "completed_topics.md",
                        "| 2026-06-01 | C | [.mp/podcast_v2_c_20260601](.mp/podcast_v2_c_20260601) |\n")

        buckets = {status.name: status.bucket for status in es.classify(mp, topics, NOW)}

        self.assertEqual(buckets, {
            "podcast_v2_a_20261001": "uploaded",
            "podcast_v2_a_20261001_revision_x_01": "undecided",
            "podcast_v2_b_20260601": "probably_uploaded",
            "podcast_v2_c_20260601": "probably_uploaded",
            "voice_audition_20261010": "undecided",
            "podcast_v2_d_20261019": "in_progress",
            "podcast_v2_e_20260101": "undecided",
        })


EPISODE_FILES = (
    "final.mp4", "graphics/glow/s1.mp4", "graphics/glow/s1.js", "graphics/paper/pieces/a.jpg",
    "merged_audio_with_sfx.wav", "score/bed.wav", "score/cues.json", "sfx/hit.wav", "audio_raw/scene_00.wav",
    "scene_00.wav", "assets/x.jpg", "review/frame.jpg", "review/verdict.json", "final_rev_2.mp4", "rejected/old.mp4",
    "shorts_promo_gfx/graphics/c.mp4", "shorts_promo_gfx/final.mp4",
)
PRUNED = {
    "graphics/glow/s1.mp4", "merged_audio_with_sfx.wav", "score/bed.wav", "sfx/hit.wav", "review/frame.jpg",
    "final_rev_2.mp4", "rejected/old.mp4", "shorts_promo_gfx/graphics/c.mp4",
}


def _episode(mp: Path, name: str = "podcast_v2_x_20261001") -> Path:
    episode = mp / name
    for rel in EPISODE_FILES:
        _write(episode / rel)
    _write(episode / "expanded_broll" / "big.mp4", size=es.LARGE_BYTES + 1024 * 1024)
    return episode


def _rel(paths: list[Path], base: Path) -> set[str]:
    return {path.relative_to(base).as_posix() for path in paths}


class PruneTests(StorageTestCase):
    def test_prune_plan_removes_only_regenerable(self) -> None:
        episode = _episode(self._mp())
        plan = es.prune_plan(episode)
        self.assertEqual(_rel(plan.remove, episode), PRUNED)
        self.assertEqual(_rel(plan.unclassified, episode), {"expanded_broll/big.mp4"})
        self.assertEqual(plan.remove_bytes, len(PRUNED))

    def test_apply_prune_requires_proof(self) -> None:
        mp = self._mp()
        episode = _episode(mp)
        with self.assertRaises(es.NotProven):
            es.apply_prune(episode, mp, NOW)
        self.assertTrue((episode / "graphics/glow/s1.mp4").exists())
        self.assertFalse((mp / es.TRASH_DIR).exists())

    def test_producer_decision_only_covers_its_action(self) -> None:
        episode = _episode(self._mp())
        _write(episode / "upload_pack" / es.CONFIRMATION_NAME,
               json.dumps({"kind": "producer_decision", "decision": "archive", "user_message": "archive เลย"}))
        with self.assertRaises(es.NotProven):
            es.require_proof(episode, "prune")
        self.assertEqual(es.require_proof(episode, "archive")["decision"], "archive")

    def test_apply_prune_moves_into_trash_preserving_paths(self) -> None:
        mp = self._mp()
        episode = _episode(mp)
        _receipt(episode)
        plan, trash = es.apply_prune(episode, mp, NOW)
        self.assertRegex(trash.name, rf"^\d{{8}}-\d{{6}}-prune-{episode.name}$")
        self.assertEqual(trash.parent, mp / es.TRASH_DIR)
        self.assertTrue((trash / "graphics/glow/s1.mp4").exists())
        self.assertTrue((episode / "graphics/glow/s1.js").exists())
        self.assertTrue((episode / "final.mp4").exists())
        self.assertFalse((episode / "graphics/glow/s1.mp4").exists())

    def test_prune_twice_is_a_no_op(self) -> None:
        mp = self._mp()
        episode = _episode(mp)
        _receipt(episode)
        es.apply_prune(episode, mp, NOW)
        plan, trash = es.apply_prune(episode, mp, NOW + timedelta(minutes=1))
        self.assertEqual(plan.remove, [])
        self.assertIsNone(trash)
        self.assertEqual(len(list((mp / es.TRASH_DIR).iterdir())), 1)


class ConfirmAndRemoveTests(StorageTestCase):
    def test_confirm_writes_user_words(self) -> None:
        episode = _episode(self._mp())
        es.confirm(episode, "ตอนนี้ลงแล้ว", url="https://youtu.be/x")
        record = json.loads((episode / "upload_pack" / es.CONFIRMATION_NAME).read_text(encoding="utf-8"))
        self.assertEqual(record["kind"], "manual_upload")
        self.assertEqual(record["user_message"], "ตอนนี้ลงแล้ว")
        self.assertEqual(record["url"], "https://youtu.be/x")
        self.assertEqual(es.upload_proof(episode)["kind"], "manual_upload")

    def test_confirm_rejects_empty_message_and_unknown_decision(self) -> None:
        episode = _episode(self._mp())
        with self.assertRaises(ValueError):
            es.confirm(episode, "  ")
        with self.assertRaises(ValueError):
            es.confirm(episode, "ลบ", decision="burn")
        self.assertFalse((episode / "upload_pack" / es.CONFIRMATION_NAME).exists())

    def test_remove_refuses_referenced_folder(self) -> None:
        mp = self._mp()
        repo = mp.parent
        episode = _episode(mp, "podcast_v2_h_1")
        _write(repo / "doc_renderer" / "gfx_kit" / "LIBRARY.md", "Worked example: `.mp/podcast_v2_h_1/graphics/v3/`.\n")
        es.confirm(episode, "ลบทิ้งเลย", decision="remove")
        with self.assertRaisesRegex(ValueError, "LIBRARY.md"):
            es.apply_remove(episode, mp, repo, NOW)
        self.assertTrue(episode.exists())

    def test_remove_needs_the_producer_decision_not_a_receipt(self) -> None:
        mp = self._mp()
        episode = _episode(mp, "podcast_v2_h_1")
        _receipt(episode)
        with self.assertRaises(es.NotProven):
            es.apply_remove(episode, mp, mp.parent, NOW)
        self.assertTrue(episode.exists())

    def test_remove_stages_whole_folder(self) -> None:
        mp = self._mp()
        episode = _episode(mp, "podcast_v2_h_1")
        es.confirm(episode, "ลบทิ้งเลย", decision="remove")
        trash = es.apply_remove(episode, mp, mp.parent, NOW)
        self.assertFalse(episode.exists())
        self.assertTrue(trash.name.endswith("-remove-podcast_v2_h_1"))
        self.assertTrue((trash / "final.mp4").exists())


class ResolveTests(StorageTestCase):
    def test_resolve_episode_accepts_name_and_paths(self) -> None:
        mp = self._mp()
        episode = mp / "podcast_v2_a_1"
        episode.mkdir()
        (mp / "fonts").mkdir()
        previous = os.getcwd()
        os.chdir(mp.parent)
        self.addCleanup(os.chdir, previous)
        for value in ("podcast_v2_a_1", str(episode), str(episode) + "/", ".mp/podcast_v2_a_1", ".mp\\podcast_v2_a_1\\"):
            self.assertEqual(es.resolve_episode(value, mp), episode.resolve(), value)
        for value in ("nope", "fonts", str(mp), str(mp.parent)):
            with self.assertRaisesRegex(ValueError, "no episode folder"):
                es.resolve_episode(value, mp)


HAS_FFMPEG =bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class StillTimeTests(unittest.TestCase):
    def test_still_times(self) -> None:
        times = es.still_times(70.0, [{"start_seconds": 0}, {"start_seconds": 40}])
        opening = [item for item in times if item[0].startswith("opening_")]
        self.assertEqual(len(opening), 20)
        self.assertEqual(opening[0], ("opening_000s.jpg", 0))
        self.assertEqual(opening[-1], ("opening_057s.jpg", 57))
        self.assertEqual(times[20:], [("chapter_01.jpg", 20.0), ("chapter_02.jpg", 55.0)])


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg/ffprobe not on PATH")
class ArchiveTests(StorageTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._video_dir = tempfile.TemporaryDirectory()
        cls.video = Path(cls._video_dir.name) / "final.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=1", "-t", "70",
                        "-pix_fmt", "yuv420p", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._video_dir.cleanup()

    def _archivable(self, thumbnail_path: str | None = None) -> tuple[Path, Path, Path]:
        mp = self._mp()
        episode = _episode(mp)
        shutil.copy(self.video, episode / "final.mp4")
        _write(episode / "thumbnails" / "TH1.png", b"png")
        _write(episode / "producer_plan.json", json.dumps({
            "render_settings": {"renderer": "minimal_doc"},
            "sections": [{"title": "เปิด"}, {"title": "กลาง"}]}, ensure_ascii=False))
        _write(episode / "metadata.json", json.dumps({
            "title": "ชื่อตอน", "chapters": [{"start_seconds": 0, "title": "เปิด"}, {"start_seconds": 40, "title": "กลาง"}]},
            ensure_ascii=False))
        _write(episode / "cost_report.json", json.dumps({"totals": {"new_cost_this_run_usd": 0.24}}))
        _receipt(episode, "scheduled_verified", publishAt="2026-10-19T08:00:00Z",
                 thumbnail_path=thumbnail_path or str(episode / "thumbnails" / "TH1.png"))
        return mp, mp.parent, episode

    def test_archive_keeps_reference_files_and_stages_the_rest(self) -> None:
        mp, repo, episode = self._archivable()
        name = episode.name
        result = es.apply_archive(episode, mp, repo, NOW)
        archive = mp / es.ARCHIVE_DIR / name
        self.assertEqual(result.archive_dir, archive)
        for rel in ("producer_plan.json", "graphics/glow/s1.js", "review/verdict.json", "thumbnail.png", "SUMMARY.md",
                    "stills/opening_000s.jpg", "stills/chapter_02.jpg", "upload_pack/youtube_upload_receipt.json"):
            self.assertTrue((archive / rel).exists(), rel)
        self.assertEqual([p for p in archive.rglob("*") if p.suffix in {".mp4", ".wav"}], [])
        self.assertFalse(episode.exists())
        self.assertTrue((result.trash_dir / "final.mp4").exists())
        self.assertRegex(result.trash_dir.name, rf"-archive-{name}$")
        index = (mp / es.ARCHIVE_DIR / "INDEX.md").read_text(encoding="utf-8")
        self.assertEqual(sum(1 for line in index.splitlines() if "watch?v=abc" in line), 1)
        summary = (archive / "SUMMARY.md").read_text(encoding="utf-8")
        for text in ("ชื่อตอน", "watch?v=abc", "minimal_doc", "เปิด", "กลาง"):
            self.assertIn(text, summary)

    def test_archive_repoints_live_docs_only(self) -> None:
        mp, repo, episode = self._archivable()
        line = f"Worked example: `.mp/{episode.name}/graphics/glow/s1.js`\n"
        library = _write(repo / "doc_renderer" / "gfx_kit" / "LIBRARY.md", line)
        postmortem = _write(repo / "docs" / "postmortems" / "x.md", line)
        result = es.apply_archive(episode, mp, repo, NOW)
        self.assertEqual(result.repointed, [library])
        self.assertIn(f".mp/archive/{episode.name}/graphics/glow/s1.js", library.read_text(encoding="utf-8"))
        self.assertEqual(postmortem.read_text(encoding="utf-8"), line)

    def test_archive_refuses_existing_archive(self) -> None:
        mp, repo, episode = self._archivable()
        (mp / es.ARCHIVE_DIR / episode.name).mkdir(parents=True)
        with self.assertRaises(ValueError):
            es.apply_archive(episode, mp, repo, NOW)
        self.assertTrue((episode / "final.mp4").exists())
        self.assertFalse((mp / es.TRASH_DIR).exists())

    def test_archive_failure_leaves_episode_intact(self) -> None:
        mp, repo, episode = self._archivable()
        with mock.patch.object(es, "extract_stills", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                es.apply_archive(episode, mp, repo, NOW)
        self.assertTrue((episode / "final.mp4").exists())
        self.assertFalse((mp / es.ARCHIVE_DIR / episode.name).exists())
        self.assertFalse((mp / es.TRASH_DIR).exists())

    def test_missing_thumbnail_is_noted(self) -> None:
        mp, repo, episode = self._archivable(thumbnail_path="D:\\elsewhere\\TH9.png")
        result = es.apply_archive(episode, mp, repo, NOW)
        self.assertIn("thumbnail missing", result.notes)
        self.assertIn("thumbnail missing", (result.archive_dir / "SUMMARY.md").read_text(encoding="utf-8"))

    def test_archive_without_final_skips_stills(self) -> None:
        mp, repo, episode = self._archivable()
        (episode / "final.mp4").unlink()
        result = es.apply_archive(episode, mp, repo, NOW)
        self.assertFalse((result.archive_dir / "stills").exists())
        self.assertIn("final.mp4 already gone, no stills", result.notes)


if __name__ == "__main__":
    unittest.main()
