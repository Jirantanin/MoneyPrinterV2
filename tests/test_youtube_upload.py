"""Offline coverage for the user-directed YouTube upload request and receipt states (no network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import youtube_upload as yt  # noqa: E402

NOW = datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc)


class UploadRequestTests(unittest.TestCase):
    def _episode(self, **metadata) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        episode = Path(temp.name)
        (episode / "upload_pack").mkdir()
        (episode / "final.mp4").write_bytes(b"video")
        (episode / "thumb.png").write_bytes(b"png")
        payload = {"title": "ชื่อคลิป", "description": "คำอธิบาย", "tags": ["สารคดี"],
                   "description_source": "seo_packaging.upload_description", **metadata}
        (episode / "upload_pack" / "metadata.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return episode

    def test_builds_private_scheduled_request_in_utc(self) -> None:
        episode = self._episode()
        request = yt.build_request(episode, thumbnail=episode / "thumb.png", user_message="upload ได้",
                                   publish_at="2026-10-05T18:30+07:00", now=NOW)
        self.assertEqual(request["publishAt"], "2026-10-05T11:30:00Z")
        self.assertEqual(request["privacyStatus"], "private")
        self.assertEqual(request["user_message"], "upload ได้")

    def test_refuses_without_user_message_fallback_copy_or_past_time(self) -> None:
        episode = self._episode()
        with self.assertRaises(ValueError):
            yt.build_request(episode, thumbnail=episode / "thumb.png", user_message=" ", publish_at=None, now=NOW)
        with self.assertRaises(ValueError):
            yt.build_request(episode, thumbnail=episode / "thumb.png", user_message="ok",
                             publish_at="2026-10-05T10:00+07:00", now=NOW)
        with self.assertRaises(ValueError):
            yt.build_request(episode, thumbnail=episode / "thumb.png", user_message="ok",
                             publish_at="2026-10-05T18:30", now=NOW)
        fallback = self._episode(description_source="generated_fallback")
        with self.assertRaises(ValueError):
            yt.build_request(fallback, thumbnail=fallback / "thumb.png", user_message="ok", publish_at=None, now=NOW)

    def test_receipt_without_video_id_requires_reconciliation(self) -> None:
        self.assertEqual(yt.upload_state({}), "new")
        self.assertEqual(yt.upload_state({"status": "upload_interrupted"}), "reconcile")
        self.assertEqual(yt.upload_state({"video_id": "x", "thumbnail_set": False}), "resume_thumbnail")
        self.assertEqual(yt.upload_state({"video_id": "x", "thumbnail_set": True, "status": "scheduled_verified"}), "done")


if __name__ == "__main__":
    unittest.main()
