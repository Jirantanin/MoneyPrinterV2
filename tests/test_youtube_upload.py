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

    def test_request_carries_localizations_and_captions(self) -> None:
        en = {"en": {"title": "The universe in one year", "description": "English copy"}}
        episode = self._episode(localizations=en)
        (episode / "upload_pack" / yt.CAPTIONS_NAME).write_text("1\n00:00:00,000 --> 00:00:01,500\nHi\n", encoding="utf-8")
        request = yt.build_request(episode, thumbnail=episode / "thumb.png", user_message="ok", publish_at=None, now=NOW)
        self.assertEqual(request["localizations"], en)
        self.assertTrue(request["captions_path"].endswith(yt.CAPTIONS_NAME))
        too_long = self._episode(localizations={"en": {"title": "x" * 101, "description": "d"}})
        with self.assertRaises(ValueError):
            yt.build_request(too_long, thumbnail=too_long / "thumb.png", user_message="ok", publish_at=None, now=NOW)

    def test_caption_source_to_srt_joins_and_refuses_untranslated(self) -> None:
        episode = self._episode()
        speech_map = {"scenes": [{"scene_index": 0, "segments": [
            {"start": 0.2, "end": 2.0, "abs_start": 30.2, "text": "สวัสดีครับ "},
            {"start": 2.0, "end": 3.5, "abs_start": 31.9, "text": "นี่คือรู้ดีกว่า"},
            {"start": 4.0, "end": 6.0, "abs_start": 34.0, "text": "คลิปนี้"}]}]}
        (episode / "speech_map.json").write_text(json.dumps(speech_map, ensure_ascii=False), encoding="utf-8")
        (episode / "script.json").write_text(json.dumps([{"narration": "บทเต็ม"}], ensure_ascii=False), encoding="utf-8")
        source = yt.caption_source(episode)
        cues = source["scenes"][0]["cues"]
        self.assertEqual(source["scenes"][0]["narration"], "บทเต็ม")
        self.assertEqual((cues[1]["start"], cues[1]["end"]), (31.9, 33.4))
        with self.assertRaises(ValueError):
            yt.build_srt(source)
        cues[0]["en"], cues[1]["en"], cues[2]["en"] = "Hello, this is Roo Dee Kwa", "+", "In this video"
        srt = yt.build_srt(source)
        self.assertEqual(yt.parse_srt(srt), 2)
        self.assertIn("00:00:30,200 --> 00:00:33,400\nHello, this is Roo Dee Kwa", srt)
        with self.assertRaises(ValueError):
            yt.parse_srt("1\n00:00:02,000 --> 00:00:01,000\nbackwards\n")

    def test_set_captions_replaces_own_track_not_asr(self) -> None:
        calls: list[str] = []

        class Op:
            def __init__(self, result): self.result = result
            def execute(self): return self.result

        class Captions:
            def __init__(self, items): self.items = items
            def list(self, **_): return Op({"items": self.items})
            def update(self, **_): calls.append("update"); return Op({"id": "own"})
            def insert(self, **_): calls.append("insert"); return Op({"id": "new"})

        class YouTube:
            def __init__(self, items): self._captions = Captions(items)
            def captions(self): return self._captions

        srt = self._episode() / "upload_pack" / yt.CAPTIONS_NAME
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
        asr = {"id": "asr", "snippet": {"language": "en", "trackKind": "asr"}}
        self.assertEqual(yt.set_captions(YouTube([asr]), "v", srt), "new")
        own = {"id": "own", "snippet": {"language": "en", "trackKind": "standard"}}
        self.assertEqual(yt.set_captions(YouTube([asr, own]), "v", srt), "own")
        self.assertEqual(calls, ["insert", "update"])

    def test_receipt_without_video_id_requires_reconciliation(self) -> None:
        self.assertEqual(yt.upload_state({}), "new")
        self.assertEqual(yt.upload_state({"status": "upload_interrupted"}), "reconcile")
        self.assertEqual(yt.upload_state({"video_id": "x", "thumbnail_set": False}), "resume_thumbnail")
        self.assertEqual(yt.upload_state({"video_id": "x", "thumbnail_set": True, "status": "scheduled_verified"}), "done")


if __name__ == "__main__":
    unittest.main()
