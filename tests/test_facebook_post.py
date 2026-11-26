"""Offline coverage for the user-directed Facebook photo post: request gates, one-shot posting, verification (HTTP mocked)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import facebook_post as fp  # noqa: E402
import facebook_upload as fb  # noqa: E402

NOW = datetime(2026, 11, 26, 8, 0, tzinfo=timezone.utc)
TOKEN = "secret-page-token"


class Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


class Session:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def request(self, method, url, headers=None, timeout=None, **kwargs):
        files = kwargs.get("files") or {}
        self.calls.append({"method": method, "url": url, "headers": headers, "data": kwargs.get("data"),
                           "params": kwargs.get("params"),
                           "files": {k: (v[0], v[1].read(), v[2]) for k, v in files.items()}})
        answer = self.routes.get((method, url.split("graph.facebook.com/", 1)[-1].split("/", 1)[-1]))
        if isinstance(answer, Exception):
            raise answer
        return answer


class FacebookPostTests(unittest.TestCase):
    def _post_dir(self, **spec) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        (folder / "image.png").write_bytes(b"png-bytes")
        body = {"caption": "ดาวเสาร์ลอยน้ำได้ #รู้ดีกว่า", "image": "image.png",
                "sources": ["https://science.nasa.gov/saturn/facts/"], "topic": "saturn-floats", **spec}
        fb.write_json(folder / fp.SPEC_NAME, body)
        return folder

    def _request(self, folder: Path, **kwargs) -> dict:
        options = {"user_message": "ทำโพส fb รายวัน", "publish_at": "2026-11-27T08:00+07:00", "now": NOW, **kwargs}
        request = fp.build_request(folder, **options)
        fb.write_json(folder / fp.REQUEST_NAME, request)
        return request

    def test_builds_scheduled_request(self) -> None:
        request = self._request(self._post_dir())
        self.assertFalse(request["published"])
        self.assertEqual(request["scheduled_publish_time"], int(datetime(2026, 11, 27, 1, tzinfo=timezone.utc).timestamp()))
        self.assertEqual(request["scheduled_publish_at"], "2026-11-27T01:00:00Z")
        self.assertEqual(request["sources"], ["https://science.nasa.gov/saturn/facts/"])

    def test_refuses_bad_requests(self) -> None:
        folder = self._post_dir()
        for override in [{"user_message": " "}, {"publish_at": None}, {"publish_now": True},
                         {"publish_at": "2026-11-26T15:05+07:00"}, {"publish_at": "2026-12-30T08:00+07:00"},
                         {"publish_at": "2026-11-27T08:00"}]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                self._request(folder, **override)
        for spec in [{"caption": " "}, {"sources": []}, {"sources": ["NASA"]}, {"image": "missing.png"}]:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                self._request(self._post_dir(**spec))
        gif = self._post_dir(image="a.gif")
        (gif / "a.gif").write_bytes(b"gif")
        with self.assertRaises(ValueError):
            self._request(gif)
        big = self._post_dir()
        (big / "image.png").write_bytes(b"0" * (fp.MAX_IMAGE_BYTES + 1))
        with self.assertRaises(ValueError):
            self._request(big)

    def test_post_scheduled_then_verify_and_never_twice(self) -> None:
        folder = self._post_dir()
        request = self._request(folder)
        when = request["scheduled_publish_time"]
        session = Session({
            ("GET", "123"): Response({"id": "123", "name": "รู้ดีกว่า"}),
            ("POST", "123/photos"): Response({"id": "555", "post_id": "123_777"}),
            ("GET", "123_777"): Response({"id": "123_777", "is_published": False, "scheduled_publish_time": when}),
        })
        receipt = fp.post(folder, graph=fb.Graph(TOKEN, session), page_id="123", log=lambda _: None, now=NOW)
        self.assertEqual(receipt["status"], "scheduled_verified")
        photo = session.calls[1]
        self.assertEqual(photo["data"], {"message": request["caption"], "published": "false",
                                         "scheduled_publish_time": str(when)})
        self.assertEqual(photo["files"]["source"], ("image.png", b"png-bytes", "image/png"))
        for call in session.calls:
            self.assertEqual(call["headers"]["Authorization"], f"OAuth {TOKEN}")
            self.assertNotIn(TOKEN, json.dumps({k: call[k] for k in ("url", "data", "params")}))
        self.assertNotIn(TOKEN, (folder / fp.RECEIPT_NAME).read_text(encoding="utf-8"))
        again = Session({})
        self.assertEqual(fp.post(folder, graph=fb.Graph(TOKEN, again), page_id="123")["status"], "scheduled_verified")
        self.assertEqual(again.calls, [])

    def test_network_failure_needs_reconcile_but_clean_error_may_retry(self) -> None:
        folder = self._post_dir()
        self._request(folder, publish_at=None, publish_now=True)
        session = Session({("GET", "123"): Response({"id": "123"}),
                           ("POST", "123/photos"): ConnectionError(f"boom access_token={TOKEN}")})
        with self.assertRaises(fb.GraphError) as caught:
            fp.post(folder, graph=fb.Graph(TOKEN, session), page_id="123", log=lambda _: None)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertEqual(fb.read_json(folder / fp.RECEIPT_NAME)["status"], "post_interrupted")
        retry = Session({})
        with self.assertRaises(RuntimeError):
            fp.post(folder, graph=fb.Graph(TOKEN, retry), page_id="123")
        self.assertEqual(retry.calls, [])

        clean = self._post_dir()
        self._request(clean, publish_at=None, publish_now=True)
        denied = Session({("GET", "123"): Response({"id": "123"}),
                          ("POST", "123/photos"): Response({"error": {"message": "(#200) Permissions error", "code": 200}}, 403)})
        with self.assertRaises(fb.GraphError):
            fp.post(clean, graph=fb.Graph(TOKEN, denied), page_id="123", log=lambda _: None)
        self.assertEqual(fp.post_state(fb.read_json(clean / fp.RECEIPT_NAME)), "retry")
        ok = Session({("GET", "123"): Response({"id": "123"}),
                      ("POST", "123/photos"): Response({"id": "555"}),
                      ("GET", "555"): Response({"page_story_id": "123_777"}),
                      ("GET", "123_777"): Response({"id": "123_777", "is_published": True, "permalink_url": "https://fb/p"})})
        receipt = fp.post(clean, graph=fb.Graph(TOKEN, ok), page_id="123", log=lambda _: None)
        self.assertEqual((receipt["status"], receipt["post_id"]), ("published_verified", "123_777"))
        self.assertEqual(ok.calls[1]["data"], {"message": "ดาวเสาร์ลอยน้ำได้ #รู้ดีกว่า", "published": "true"})

    def test_changed_image_and_wrong_schedule_stop(self) -> None:
        folder = self._post_dir()
        self._request(folder)
        (folder / "image.png").write_bytes(b"redrawn")
        with self.assertRaises(RuntimeError):
            fp.post(folder, graph=fb.Graph(TOKEN, Session({})), page_id="123")
        with self.assertRaises(RuntimeError):
            fp.verify({"published": False, "scheduled_publish_time": 100}, {"is_published": False, "scheduled_publish_time": 200})
        self.assertIsNone(fp.verify({"published": True, "scheduled_publish_time": None}, {"is_published": False}))


if __name__ == "__main__":
    unittest.main()
