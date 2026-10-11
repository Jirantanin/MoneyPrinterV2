"""User-directed YouTube upload for a finished Producer Mode episode.

Nothing here runs on a schedule. Every upload or schedule change starts from an explicit user message that is
recorded in the request. Receipts are written at every step so an interrupted upload is reconciled, never blindly
retried (a retry after a lost response creates a duplicate video).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = ROOT / "token.json"
CLIENT_SECRETS_PATH = ROOT / "client_secrets.json"
DEFAULT_CHANNEL_ID = "UCnlERX4BbV3dysREOIYysKw"  # รู้ดีกว่า
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
CATEGORY_SCIENCE_TECH = "28"
MAX_TITLE = 100
MAX_DESCRIPTION_BYTES = 5000
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
REQUEST_NAME = "youtube_upload_request.json"
RECEIPT_NAME = "youtube_upload_receipt.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parse_publish_at(value: str) -> str:
    """Accept ISO with offset (e.g. 2026-10-05T18:30+07:00); return YouTube's UTC Z form."""
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("publish time needs a timezone offset, e.g. +07:00")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_request(
    episode_dir: Path,
    *,
    thumbnail: Path,
    user_message: str,
    publish_at: str | None,
    title: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the upload request from the episode's upload pack; refuse fallback copy or a past publish time."""
    if not user_message.strip():
        raise ValueError("an explicit user upload message is required")
    pack = episode_dir / "upload_pack"
    metadata = read_json(pack / "metadata.json")
    if not metadata:
        raise ValueError("upload_pack/metadata.json is missing; run producer_mode.py upload-pack first")
    if metadata.get("description_source") == "generated_fallback":
        raise ValueError("upload pack still uses generated fallback copy; write seo_packaging and rerun upload-pack")
    final_title = (title or metadata.get("title") or "").strip()
    title_options = metadata.get("title_options")
    if isinstance(title_options, list) and any(o.get("role") == "fallback_topic" for o in title_options if isinstance(o, dict)):
        raise ValueError("title comes from fallback_topic; write seo_packaging.title_options")
    video = episode_dir / "final.mp4"
    request: dict[str, Any] = {
        "status": "requested",
        "requested_at": (now or datetime.now(timezone.utc)).isoformat(),
        "user_message": user_message,
        "video_path": str(video),
        "thumbnail_path": str(thumbnail.resolve()),
        "title": final_title,
        "description": metadata.get("description") or "",
        "tags": list(metadata.get("tags") or []),
        "categoryId": CATEGORY_SCIENCE_TECH,
        "language": "th",
        "privacyStatus": "private",
        "publishAt": parse_publish_at(publish_at) if publish_at else None,
    }
    validate_request(request, now=now)
    return request


def validate_request(request: dict[str, Any], *, now: datetime | None = None) -> None:
    video, thumbnail = Path(request["video_path"]), Path(request["thumbnail_path"])
    if not video.is_file():
        raise ValueError(f"final video missing: {video}")
    if not thumbnail.is_file() or thumbnail.stat().st_size >= MAX_THUMBNAIL_BYTES:
        raise ValueError("thumbnail missing or not under 2 MB")
    if not request["title"] or len(request["title"]) > MAX_TITLE:
        raise ValueError(f"title must be 1-{MAX_TITLE} characters")
    if len(request["description"].encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise ValueError(f"description exceeds {MAX_DESCRIPTION_BYTES} bytes")
    if request.get("publishAt"):
        moment = datetime.fromisoformat(request["publishAt"].replace("Z", "+00:00"))
        if moment <= (now or datetime.now(timezone.utc)):
            raise ValueError("publishAt is in the past")


def upload_state(receipt: dict[str, Any]) -> str:
    """'new' | 'resume_thumbnail' | 'done' | 'reconcile' (earlier attempt without a video id)."""
    if not receipt:
        return "new"
    if not receipt.get("video_id"):
        return "reconcile"
    if not receipt.get("thumbnail_set"):
        return "resume_thumbnail"
    return "done" if receipt.get("status") in {"uploaded_verified", "scheduled_verified"} else "resume_thumbnail"


def youtube_client():
    import google_auth_httplib2
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import build_http

    credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as exc:  # google.auth.exceptions.RefreshError
            raise RuntimeError("YouTube token expired or revoked; run `youtube_upload.py reconnect` (user signs in)") from exc
    transport = build_http()
    transport.timeout = 60
    return build("youtube", "v3", http=google_auth_httplib2.AuthorizedHttp(credentials, http=transport), cache_discovery=False)


def reconnect() -> None:
    """Browser OAuth; the user signs in themselves. Backs up the old token, never prints secrets."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), SCOPES)
    credentials = flow.run_local_server(
        host="localhost", port=0, open_browser=True, timeout_seconds=900,
        authorization_prompt_message="Complete YouTube sign-in in the browser window.",
        success_message="YouTube connected. You can close this tab.",
    )
    if TOKEN_PATH.exists():
        backups = ROOT / ".mp" / "oauth_backups"
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TOKEN_PATH, backups / f"token-before-reconnect-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json")
    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")


def _check_channel(youtube, channel_id: str) -> str:
    items = youtube.channels().list(part="snippet", mine=True).execute().get("items", [])
    if len(items) != 1 or items[0]["id"] != channel_id:
        raise RuntimeError("authorized account is not the expected channel; stop")
    return items[0]["snippet"]["title"]


def upload(episode_dir: Path, *, channel_id: str = DEFAULT_CHANNEL_ID, log=print) -> dict[str, Any]:
    from googleapiclient.http import MediaFileUpload

    pack = episode_dir / "upload_pack"
    request = read_json(pack / REQUEST_NAME)
    if not request:
        raise ValueError("no upload request; run `youtube_upload.py request` first")
    receipt_path = pack / RECEIPT_NAME
    receipt = read_json(receipt_path)
    state = upload_state(receipt)
    if state == "reconcile":
        raise RuntimeError("earlier attempt has no video id; check YouTube Studio for a partial upload before retrying")
    if state == "done":
        return receipt
    if state == "new":
        validate_request(request)
    youtube = youtube_client()
    channel_title = _check_channel(youtube, channel_id)
    video, thumbnail = Path(request["video_path"]), Path(request["thumbnail_path"])
    if state == "new":
        receipt = {
            "status": "upload_starting", "started_at": utc_now(), "channel_id": channel_id, "channel_title": channel_title,
            "video_path": str(video), "video_sha256": file_sha256(video),
            "thumbnail_path": str(thumbnail), "thumbnail_sha256": file_sha256(thumbnail),
            "privacy_status": "private", "publishAt": request.get("publishAt"), "title": request["title"],
            "user_message": request.get("user_message"), "thumbnail_set": False,
        }
        write_json(receipt_path, receipt)
        status: dict[str, Any] = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
        if request.get("publishAt"):
            status["publishAt"] = request["publishAt"]
        body = {
            "snippet": {"title": request["title"], "description": request["description"], "tags": request["tags"],
                        "categoryId": request["categoryId"], "defaultLanguage": "th", "defaultAudioLanguage": "th"},
            "status": status,
        }
        media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
        insert = youtube.videos().insert(part="snippet,status", body=body, media_body=media,
                                         notifySubscribers=bool(request.get("publishAt")))
        response = None
        while response is None:
            try:
                progress, response = insert.next_chunk(num_retries=3)
            except Exception:
                receipt.update(status="upload_interrupted", resumable_uri=insert.resumable_uri)
                write_json(receipt_path, receipt)
                raise
            if progress:
                log(f"UPLOAD_PROGRESS {round(progress.progress() * 100)}")
        receipt.update(video_id=response["id"], url=f"https://www.youtube.com/watch?v={response['id']}",
                       status="uploaded", uploaded_at=utc_now())
        write_json(receipt_path, receipt)
    if not receipt.get("thumbnail_set"):
        mime = "image/png" if thumbnail.suffix.lower() == ".png" else "image/jpeg"
        youtube.thumbnails().set(videoId=receipt["video_id"], media_body=MediaFileUpload(str(thumbnail), mimetype=mime)).execute(num_retries=2)
        receipt["thumbnail_set"] = True
        write_json(receipt_path, receipt)
    result = video_status(youtube, receipt["video_id"])
    if result["snippet"]["channelId"] != channel_id or result["snippet"]["title"] != request["title"]:
        raise RuntimeError("uploaded video does not match the request; inspect in Studio")
    if result["status"]["privacyStatus"] != "private" or result["status"].get("publishAt") != request.get("publishAt"):
        raise RuntimeError("privacy/publishAt on YouTube does not match the request; inspect in Studio")
    receipt.update(status="scheduled_verified" if request.get("publishAt") else "uploaded_verified",
                   verified_at=utc_now(), verification=result)
    write_json(receipt_path, receipt)
    return receipt


def video_status(youtube, video_id: str) -> dict[str, Any]:
    items = youtube.videos().list(part="snippet,status,contentDetails,processingDetails", id=video_id).execute().get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"video {video_id} not found")
    return items[0]


def schedule(episode_dir: Path, *, publish_at: str, user_message: str, channel_id: str = DEFAULT_CHANNEL_ID) -> dict[str, Any]:
    if not user_message.strip():
        raise ValueError("an explicit user message is required to change publication")
    pack = episode_dir / "upload_pack"
    receipt = read_json(pack / RECEIPT_NAME)
    if not receipt.get("video_id"):
        raise ValueError("no uploaded video in the receipt")
    when = parse_publish_at(publish_at)
    if datetime.fromisoformat(when.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        raise ValueError("publish time is in the past")
    youtube = youtube_client()
    _check_channel(youtube, channel_id)
    current = video_status(youtube, receipt["video_id"])
    status = {"privacyStatus": "private", "publishAt": when,
              "selfDeclaredMadeForKids": current["status"].get("selfDeclaredMadeForKids", False)}
    youtube.videos().update(part="status", body={"id": receipt["video_id"], "status": status}).execute()
    result = video_status(youtube, receipt["video_id"])
    record = {"video_id": receipt["video_id"], "publishAt": when, "user_message": user_message,
              "verified_at": utc_now(), "youtube_status": result["status"]}
    write_json(pack / "youtube_schedule_receipt.json", record)
    return record
