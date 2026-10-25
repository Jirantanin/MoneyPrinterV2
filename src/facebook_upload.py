"""User-directed Facebook Page Reel upload for a finished Short (Graph API Reels publishing flow).

Nothing here runs on a schedule. Every post starts from an explicit user message recorded in the request. Receipts are
written before and after every Graph call so an interrupted upload is reconciled, never blindly retried (a second start
creates a second Reel). The Page access token is read from the ignored config.json and never printed or written.

Flow (developers.facebook.com/docs/video-api/guides/reels-publishing): POST /{page-id}/video_reels upload_phase=start
-> POST the bytes to rupload.facebook.com/video-upload/{version}/{video-id} -> POST upload_phase=finish with
video_state PUBLISHED or SCHEDULED + scheduled_publish_time (unix, 10 minutes to 29 days ahead).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
GRAPH_VERSION = "v26.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"
RUPLOAD_URL = f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}"
REQUEST_NAME = "facebook_upload_request.json"
RECEIPT_NAME = "facebook_upload_receipt.json"
CAPTION_NAME = "facebook_caption.txt"
VIDEO_NAME = "video.mp4"
MIN_SECONDS, MAX_SECONDS = 3.0, 90.0
MIN_LEAD, MAX_LEAD = timedelta(minutes=10), timedelta(days=29)
TIMEOUT = 60
UPLOAD_TIMEOUT = 900


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def probe_duration(video: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                            capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def parse_publish_at(value: str) -> datetime:
    """ISO with offset (e.g. 2026-10-27T12:00+07:00) -> aware UTC datetime."""
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("publish time needs a timezone offset, e.g. +07:00")
    return moment.astimezone(timezone.utc)


def load_credentials(config_path: Path = CONFIG_PATH) -> tuple[str, str]:
    config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else {}
    page_id = str(config.get("facebook_page_id") or "").strip()
    token = str(config.get("facebook_page_access_token") or "").strip()
    if not page_id or not token:
        raise RuntimeError("config.json needs facebook_page_id and facebook_page_access_token (the user adds them)")
    return page_id, token


def build_request(
    short_dir: Path,
    *,
    user_message: str,
    publish_at: str | None,
    publish_now: bool = False,
    now: datetime | None = None,
    probe: Callable[[Path], float] = probe_duration,
) -> dict[str, Any]:
    """Build the Reel request from the Short's upload pack; scheduling is the default, posting now must be explicit."""
    if not user_message.strip():
        raise ValueError("an explicit user upload message is required")
    if bool(publish_at) == publish_now:
        raise ValueError("give exactly one of --publish-at (scheduled) or --publish-now (public immediately)")
    if not (short_dir / "script.json").is_file():
        raise ValueError(f"script.json missing in {short_dir}")
    pack = short_dir / "upload_pack"
    video, caption_path = pack / VIDEO_NAME, pack / CAPTION_NAME
    if not video.is_file():
        raise ValueError(f"upload_pack/{VIDEO_NAME} missing")
    if not caption_path.is_file():
        raise ValueError(f"upload_pack/{CAPTION_NAME} missing")
    request: dict[str, Any] = {
        "status": "requested",
        "requested_at": (now or datetime.now(timezone.utc)).isoformat(),
        "user_message": user_message,
        "video_path": str(video.resolve()),
        "video_sha256": file_sha256(video),
        "video_seconds": round(probe(video), 3),
        "description": caption_path.read_text(encoding="utf-8").strip(),
        "video_state": "PUBLISHED" if publish_now else "SCHEDULED",
        "scheduled_publish_time": int(parse_publish_at(publish_at).timestamp()) if publish_at else None,
        "graph_version": GRAPH_VERSION,
    }
    if publish_at:
        request["scheduled_publish_at"] = parse_publish_at(publish_at).strftime("%Y-%m-%dT%H:%M:%SZ")
    validate_request(request, now=now)
    return request


def validate_request(request: dict[str, Any], *, now: datetime | None = None) -> None:
    video = Path(request["video_path"])
    if not video.is_file():
        raise ValueError(f"video missing: {video}")
    if not MIN_SECONDS <= request["video_seconds"] <= MAX_SECONDS:
        raise ValueError(f"Reels must be {MIN_SECONDS:g}-{MAX_SECONDS:g} seconds; video is {request['video_seconds']}s")
    if not request["description"]:
        raise ValueError(f"{CAPTION_NAME} is empty")
    if request["video_state"] == "SCHEDULED":
        when = datetime.fromtimestamp(request["scheduled_publish_time"], timezone.utc)
        lead = when - (now or datetime.now(timezone.utc))
        if not MIN_LEAD < lead <= MAX_LEAD:
            raise ValueError("scheduled time must be more than 10 minutes and at most 29 days ahead")
    elif request["video_state"] != "PUBLISHED":
        raise ValueError(f"unsupported video_state {request['video_state']}")


def upload_state(receipt: dict[str, Any]) -> str:
    """'new' | 'resume_finish' (bytes sent, nothing published) | 'done' | 'reconcile' (any interrupted step)."""
    if not receipt:
        return "new"
    status = receipt.get("status")
    if status == "uploaded" and receipt.get("video_id"):
        return "resume_finish"
    if status in {"finished", "scheduled_verified", "published_verified"}:
        return "done"
    return "reconcile"


class GraphError(RuntimeError):
    pass


class Graph:
    """Thin Graph API client; the token travels only in the Authorization header and never appears in errors."""

    def __init__(self, token: str, session=None):
        if session is None:
            import requests

            session = requests.Session()
        self._token, self._session = token, session

    def _call(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        headers = {"Authorization": f"OAuth {self._token}", **kwargs.pop("headers", {})}
        try:
            response = self._session.request(method, url, headers=headers, timeout=kwargs.pop("timeout", TIMEOUT), **kwargs)
        except Exception as exc:  # network errors; keep the token out of the message
            raise GraphError(f"{method} {url} failed: {type(exc).__name__}") from None
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400 or "error" in payload:
            error = payload.get("error") or {}
            raise GraphError(f"{method} {url} -> HTTP {response.status_code}: {error.get('message', 'no message')} "
                             f"(code {error.get('code')}, subcode {error.get('error_subcode')}, "
                             f"fbtrace {error.get('fbtrace_id')})")
        return payload

    def get(self, path: str, **params) -> dict[str, Any]:
        return self._call("GET", f"{GRAPH_URL}/{path}", params=params)

    def post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", f"{GRAPH_URL}/{path}", json=data)

    def upload_bytes(self, video_id: str, video: Path) -> dict[str, Any]:
        size = video.stat().st_size
        with video.open("rb") as stream:
            return self._call("POST", f"{RUPLOAD_URL}/{video_id}", data=stream, timeout=UPLOAD_TIMEOUT,
                              headers={"offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"})


def check_page(graph: Graph, page_id: str) -> str:
    page = graph.get(page_id, fields="id,name")
    if str(page.get("id")) != page_id:
        raise RuntimeError("token does not resolve to the configured Page; stop")
    return page.get("name", "")


def reel_status(graph: Graph, video_id: str) -> dict[str, Any]:
    return graph.get(video_id, fields="status,description,permalink_url,created_time")


def _unix(value: Any) -> int:
    """publish_time comes back as an ISO string (2026-10-27T05:00:00+0000) though the docs say unix."""
    if isinstance(value, str) and not value.isdigit():
        return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").timestamp())
    return int(value or 0)


def verify(request: dict[str, Any], status: dict[str, Any]) -> str | None:
    """Verified receipt status when Facebook reports the requested publish state, else None (still processing)."""
    publishing = (status.get("status") or {}).get("publishing_phase") or {}
    if request["video_state"] == "SCHEDULED":
        if publishing.get("publish_status") == "scheduled":
            if _unix(publishing.get("publish_time")) != request["scheduled_publish_time"]:
                raise RuntimeError("scheduled time on Facebook does not match the request; check Meta Business Suite")
            return "scheduled_verified"
    elif publishing.get("publish_status") == "published":
        return "published_verified"
    if publishing.get("publish_status") == "error" or (status.get("status") or {}).get("video_status") in {"error", "upload_failed"}:
        raise RuntimeError(f"Facebook reports an error: {status.get('status')}")
    return None


def upload(short_dir: Path, *, graph: Graph | None = None, page_id: str | None = None, log=print) -> dict[str, Any]:
    pack = short_dir / "upload_pack"
    request = read_json(pack / REQUEST_NAME)
    if not request:
        raise ValueError("no upload request; run `facebook_upload.py request` first")
    receipt_path = pack / RECEIPT_NAME
    receipt = read_json(receipt_path)
    state = upload_state(receipt)
    if state == "reconcile":
        raise RuntimeError(f"earlier attempt stopped at '{receipt.get('status')}'; run `status` and check the Page in "
                           "Meta Business Suite before anything else (a new start would create a second Reel)")
    if state == "done":
        return receipt
    if graph is None or page_id is None:
        page_id, token = load_credentials()
        graph = Graph(token)
    video = Path(request["video_path"])
    if file_sha256(video) != request["video_sha256"]:
        raise RuntimeError("video.mp4 changed since the request; run `request` again")
    if state == "new":
        validate_request(request)
        page_name = check_page(graph, page_id)
        receipt = {"status": "starting", "started_at": utc_now(), "page_id": page_id, "page_name": page_name,
                   "video_path": str(video), "video_sha256": request["video_sha256"], "video_state": request["video_state"],
                   "scheduled_publish_time": request.get("scheduled_publish_time"),
                   "scheduled_publish_at": request.get("scheduled_publish_at"), "user_message": request["user_message"]}
        write_json(receipt_path, receipt)
        started = graph.post(f"{page_id}/video_reels", {"upload_phase": "start"})
        receipt.update(status="started", video_id=str(started["video_id"]))
        write_json(receipt_path, receipt)
        log(f"REEL_STARTED {receipt['video_id']}")
        try:
            result = graph.upload_bytes(receipt["video_id"], video)
        except Exception:
            receipt["status"] = "upload_interrupted"
            write_json(receipt_path, receipt)
            raise
        if not result.get("success"):
            receipt["status"] = "upload_interrupted"
            write_json(receipt_path, receipt)
            raise RuntimeError(f"rupload did not report success: {result}")
        receipt.update(status="uploaded", uploaded_at=utc_now())
        write_json(receipt_path, receipt)
        log("REEL_BYTES_UPLOADED")
    elif page_id != receipt.get("page_id"):
        raise RuntimeError("configured Page differs from the receipt's Page; stop")
    finish: dict[str, Any] = {"upload_phase": "finish", "video_id": receipt["video_id"],
                              "video_state": request["video_state"], "description": request["description"]}
    if request["video_state"] == "SCHEDULED":
        validate_request(request)  # the 10-minute floor may have passed while uploading
        finish["scheduled_publish_time"] = request["scheduled_publish_time"]
    receipt["status"] = "finishing"
    write_json(receipt_path, receipt)
    graph.post(f"{page_id}/video_reels", finish)
    receipt.update(status="finished", finished_at=utc_now())
    write_json(receipt_path, receipt)
    return refresh_status(short_dir, graph=graph)


def refresh_status(short_dir: Path, *, graph: Graph | None = None) -> dict[str, Any]:
    """Read the Reel's status; marks the receipt verified once Facebook reports the requested publish state."""
    pack = short_dir / "upload_pack"
    request, receipt = read_json(pack / REQUEST_NAME), read_json(pack / RECEIPT_NAME)
    if not receipt.get("video_id"):
        return receipt
    if graph is None:
        graph = Graph(load_credentials()[1])
    status = reel_status(graph, receipt["video_id"])
    receipt["last_status"], receipt["checked_at"] = status, utc_now()
    if receipt.get("status") in {"finished", "scheduled_verified", "published_verified"}:
        verified = verify(request, status)
        if verified:
            receipt.update(status=verified, verified_at=receipt.get("verified_at") or utc_now())
    write_json(pack / RECEIPT_NAME, receipt)
    return receipt
