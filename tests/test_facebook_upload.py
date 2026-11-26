"""Offline coverage for the user-directed Facebook Reel request, upload states and Graph calls (HTTP mocked)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import facebook_upload as fb  # noqa: E402

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
TOKEN = "secret-page-token"


class Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class Session:
    """Records Graph calls and answers them from a route table keyed by (method, url suffix)."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def request(self, method, url, headers=None, timeout=None, **kwargs):
        body = kwargs.get("json") or {}
        self.calls.append({"method": method, "url": url, "headers": headers, "json": body, "params": kwargs.get("params")})
        key = (method, url.rsplit("/", 1)[-1], body.get("upload_phase"))
        answer = self.routes.get(key) or self.routes.get(key[:2])
        if isinstance(answer, Exception):
            raise answer
        return answer


class FacebookUploadTests(unittest.TestCase):
    def _short(self, caption="คำบรรยาย #รู้ดีกว่า") -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        short = Path(temp.name)
        (short / "upload_pack").mkdir()
        (short / "script.json").write_text("{}", encoding="utf-8")
        (short / "upload_pack" / "video.mp4").write_bytes(b"video-bytes")
        (short / "upload_pack" / "facebook_caption.txt").write_text(caption, encoding="utf-8")
        return short

    def _request(self, short: Path, **kwargs) -> dict:
        options = {"user_message": "ลง Reel ด้วย", "publish_at": "2026-10-27T12:00+07:00", "now": NOW,
                   "probe": lambda _: 73.75, **kwargs}
        request = fb.build_request(short, **options)
        fb.write_json(short / "upload_pack" / fb.REQUEST_NAME, request)
        return request

    def test_builds_scheduled_request_with_unix_time(self) -> None:
        request = self._request(self._short())
        self.assertEqual(request["video_state"], "SCHEDULED")
        self.assertEqual(request["scheduled_publish_time"], int(datetime(2026, 10, 27, 5, tzinfo=timezone.utc).timestamp()))
        self.assertEqual(request["scheduled_publish_at"], "2026-10-27T05:00:00Z")
        self.assertEqual(request["user_message"], "ลง Reel ด้วย")
        self.assertEqual(request["description"], "คำบรรยาย #รู้ดีกว่า")

    def test_refuses_bad_requests(self) -> None:
        short = self._short()
        bad = [
            {"user_message": " "},
            {"publish_at": None},  # neither scheduled nor explicitly now
            {"publish_now": True},  # both
            {"publish_at": "2026-10-25T15:05+07:00"},  # 5 minutes ahead
            {"publish_at": "2026-11-24T12:00+07:00"},  # over 29 days
            {"publish_at": "2026-10-27T12:00"},  # no offset
            {"probe": lambda _: 95.0},  # over 90 seconds
        ]
        for override in bad:
            with self.subTest(override=override), self.assertRaises(ValueError):
                self._request(short, **override)
        with self.assertRaises(ValueError):
            self._request(self._short(caption="  "))
        now = self._request(short, publish_at=None, publish_now=True)
        self.assertEqual((now["video_state"], now["scheduled_publish_time"]), ("PUBLISHED", None))

    def test_upload_start_bytes_finish_then_verify(self) -> None:
        short = self._short()
        request = self._request(short)
        when = request["scheduled_publish_time"]
        session = Session({
            ("GET", "123"): Response({"id": "123", "name": "รู้ดีกว่า"}),
            ("POST", "video_reels", "start"): Response({"video_id": "987", "upload_url": "https://rupload.facebook.com/video-upload/987"}),
            ("POST", "987"): Response({"success": True}),
            ("POST", "video_reels", "finish"): Response({"success": True}),
            ("GET", "987"): Response({"status": {"video_status": "processing", "publishing_phase": {
                "status": "complete", "publish_status": "scheduled", "publish_time": when}}}),
        })
        receipt = fb.upload(short, graph=fb.Graph(TOKEN, session), page_id="123", log=lambda _: None, now=NOW)
        self.assertEqual(receipt["status"], "scheduled_verified")
        self.assertEqual(fb._unix("2026-10-27T05:00:00+0000"), when)  # what the live API actually returns
        self.assertEqual(receipt["video_id"], "987")
        upload_call = session.calls[2]
        self.assertTrue(upload_call["url"].startswith("https://rupload.facebook.com/video-upload/"))
        self.assertEqual(upload_call["headers"]["file_size"], str(len(b"video-bytes")))
        finish = session.calls[3]["json"]
        self.assertEqual((finish["video_state"], finish["scheduled_publish_time"]), ("SCHEDULED", when))
        self.assertEqual(finish["description"], request["description"])
        for call in session.calls:
            self.assertEqual(call["headers"]["Authorization"], f"OAuth {TOKEN}")
            self.assertNotIn(TOKEN, json.dumps({k: call[k] for k in ("url", "json", "params")}))
        self.assertNotIn(TOKEN, (short / "upload_pack" / fb.RECEIPT_NAME).read_text(encoding="utf-8"))
        # Done receipts never post again.
        self.assertEqual(fb.upload(short, graph=fb.Graph(TOKEN, Session({})), page_id="123")["status"], "scheduled_verified")

    def test_interrupted_bytes_require_reconciliation_not_retry(self) -> None:
        short = self._short()
        self._request(short)
        session = Session({
            ("GET", "123"): Response({"id": "123", "name": "Page"}),
            ("POST", "video_reels", "start"): Response({"video_id": "987"}),
            ("POST", "987"): ConnectionError(f"boom access_token={TOKEN}"),
        })
        with self.assertRaises(fb.GraphError) as caught:
            fb.upload(short, graph=fb.Graph(TOKEN, session), page_id="123", log=lambda _: None, now=NOW)
        self.assertNotIn(TOKEN, str(caught.exception))
        receipt = fb.read_json(short / "upload_pack" / fb.RECEIPT_NAME)
        self.assertEqual((receipt["status"], receipt["video_id"]), ("upload_interrupted", "987"))
        retry = Session({})
        with self.assertRaises(RuntimeError):
            fb.upload(short, graph=fb.Graph(TOKEN, retry), page_id="123", now=NOW)
        self.assertEqual(retry.calls, [])

    def test_graph_error_and_page_mismatch_stop(self) -> None:
        short = self._short()
        self._request(short)
        wrong_page = Session({("GET", "123"): Response({"id": "555", "name": "Other"})})
        with self.assertRaises(RuntimeError):
            fb.upload(short, graph=fb.Graph(TOKEN, wrong_page), page_id="123", now=NOW)
        self.assertFalse((short / "upload_pack" / fb.RECEIPT_NAME).exists())
        denied = Session({("GET", "123"): Response({"error": {"message": "(#200) Permissions error", "code": 200}}, 403)})
        with self.assertRaises(fb.GraphError) as caught:
            fb.upload(short, graph=fb.Graph(TOKEN, denied), page_id="123", now=NOW)
        self.assertIn("Permissions error", str(caught.exception))

    def test_upload_state_and_resume_finish(self) -> None:
        self.assertEqual(fb.upload_state({}), "new")
        self.assertEqual(fb.upload_state({"status": "started", "video_id": "1"}), "reconcile")
        self.assertEqual(fb.upload_state({"status": "finishing", "video_id": "1"}), "reconcile")
        self.assertEqual(fb.upload_state({"status": "uploaded", "video_id": "1"}), "resume_finish")
        self.assertEqual(fb.upload_state({"status": "finished", "video_id": "1"}), "done")
        short = self._short()
        self._request(short, publish_at=None, publish_now=True)
        fb.write_json(short / "upload_pack" / fb.RECEIPT_NAME, {"status": "uploaded", "video_id": "987", "page_id": "123"})
        session = Session({
            ("POST", "video_reels", "finish"): Response({"success": True}),
            ("GET", "987"): Response({"status": {"video_status": "processing", "publishing_phase": {"status": "in_progress"}}}),
        })
        receipt = fb.upload(short, graph=fb.Graph(TOKEN, session), page_id="123", now=NOW)
        self.assertEqual([c["json"].get("upload_phase") for c in session.calls], ["finish", None])
        self.assertEqual(session.calls[0]["json"]["video_state"], "PUBLISHED")
        self.assertEqual(receipt["status"], "finished")  # still processing; `status` verifies later

    def test_changed_video_after_request_stops(self) -> None:
        short = self._short()
        self._request(short)
        (short / "upload_pack" / "video.mp4").write_bytes(b"re-rendered")
        with self.assertRaises(RuntimeError):
            fb.upload(short, graph=fb.Graph(TOKEN, Session({})), page_id="123")

    def test_load_credentials_requires_both_keys(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config = Path(temp.name) / "config.json"
        config.write_text(json.dumps({"facebook_page_id": "123", "facebook_page_access_token": ""}), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            fb.load_credentials(config)
        config.write_text(json.dumps({"facebook_page_id": 123, "facebook_page_access_token": TOKEN}), encoding="utf-8")
        self.assertEqual(fb.load_credentials(config), ("123", TOKEN))


if __name__ == "__main__":
    unittest.main()
