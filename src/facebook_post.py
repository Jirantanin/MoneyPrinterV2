"""User-directed Facebook Page photo post (one image + caption), posted now or scheduled, for the daily fact posts.

Nothing here runs on a schedule. Every post starts from an explicit user message recorded in the request, like the
Reel uploader (src/facebook_upload.py, whose Graph client and credentials this reuses). Receipts are written before and
after the Graph call so an interrupted post is reconciled, never blindly retried (a second call makes a second post).

A post folder holds post.json {"caption", "image", "sources": [...], "topic"?} and the image it names. The facts in the
caption must be checkable, so post.json needs at least one source URL; sources stay in the folder, not in the caption.

Flow (developers.facebook.com/docs/graph-api/reference/page/photos): multipart POST /{page-id}/photos with source,
message, and for a schedule published=false + scheduled_publish_time (unix). Verify with GET /{post-id}.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import facebook_upload as fb

SPEC_NAME = "post.json"
REQUEST_NAME = "facebook_post_request.json"
RECEIPT_NAME = "facebook_post_receipt.json"
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # Facebook's photo guidance: under 4 MB
DONE = {"posted", "scheduled_verified", "published_verified"}


def build_request(post_dir: Path, *, user_message: str, publish_at: str | None, publish_now: bool = False,
                  now: datetime | None = None) -> dict[str, Any]:
    """Build the photo-post request from post.json; scheduling is the default, posting now must be explicit."""
    if not user_message.strip():
        raise ValueError("an explicit user post message is required")
    if bool(publish_at) == publish_now:
        raise ValueError("give exactly one of --publish-at (scheduled) or --publish-now (public immediately)")
    spec_path = post_dir / SPEC_NAME
    if not spec_path.is_file():
        raise ValueError(f"{SPEC_NAME} missing in {post_dir}")
    spec = fb.read_json(spec_path)
    image = post_dir / str(spec.get("image") or "")
    if not spec.get("image") or not image.is_file():
        raise ValueError(f"image named in {SPEC_NAME} is missing: {spec.get('image')!r}")
    request: dict[str, Any] = {
        "status": "requested",
        "requested_at": (now or datetime.now(timezone.utc)).isoformat(),
        "user_message": user_message,
        "topic": spec.get("topic"),
        "image_path": str(image.resolve()),
        "image_sha256": fb.file_sha256(image),
        "image_bytes": image.stat().st_size,
        "caption": str(spec.get("caption") or "").strip(),
        "sources": [str(s).strip() for s in spec.get("sources") or [] if str(s).strip()],
        "published": publish_now,
        "scheduled_publish_time": int(fb.parse_publish_at(publish_at).timestamp()) if publish_at else None,
        "graph_version": fb.GRAPH_VERSION,
    }
    if publish_at:
        request["scheduled_publish_at"] = fb.parse_publish_at(publish_at).strftime("%Y-%m-%dT%H:%M:%SZ")
    validate_request(request, now=now)
    return request


def validate_request(request: dict[str, Any], *, now: datetime | None = None) -> None:
    image = Path(request["image_path"])
    if not image.is_file():
        raise ValueError(f"image missing: {image}")
    if image.suffix.lower() not in IMAGE_TYPES:
        raise ValueError(f"image must be PNG or JPEG, got {image.suffix}")
    if request["image_bytes"] > MAX_IMAGE_BYTES:
        raise ValueError(f"image is {request['image_bytes'] / 1e6:.1f} MB; keep it under 4 MB (export JPEG)")
    if not request["caption"]:
        raise ValueError("caption in post.json is empty")
    if not request["sources"] or not all(s.startswith(("http://", "https://")) for s in request["sources"]):
        raise ValueError("post.json needs at least one source URL (http/https) backing the fact")
    if not request["published"]:
        when = datetime.fromtimestamp(request["scheduled_publish_time"], timezone.utc)
        lead = when - (now or datetime.now(timezone.utc))
        if not fb.MIN_LEAD < lead <= fb.MAX_LEAD:
            raise ValueError("scheduled time must be more than 10 minutes and at most 29 days ahead")


def post_state(receipt: dict[str, Any]) -> str:
    """'new' | 'retry' (Facebook answered with an error, nothing was created) | 'done' | 'reconcile' (outcome unknown)."""
    status = receipt.get("status")
    if not receipt:
        return "new"
    if status == "post_failed":
        return "retry"
    if status in DONE:
        return "done"
    return "reconcile"


def post(post_dir: Path, *, graph: fb.Graph | None = None, page_id: str | None = None, log=print,
         now: datetime | None = None) -> dict[str, Any]:
    """Post the requested photo once. Refuses to post twice; an interrupted call needs a manual check, not a retry."""
    request = fb.read_json(post_dir / REQUEST_NAME)
    receipt_path = post_dir / RECEIPT_NAME
    receipt = fb.read_json(receipt_path)
    if request.get("status") != "requested":
        raise RuntimeError(f"run `request` first: {REQUEST_NAME} missing or not requested")
    state = post_state(receipt)
    if state == "done":
        return receipt
    if state == "reconcile":
        raise RuntimeError(f"receipt status {receipt.get('status')!r}: the post may already exist; run `status` and check "
                           "Meta Business Suite before deleting the receipt")
    image = Path(request["image_path"])
    if fb.file_sha256(image) != request["image_sha256"]:
        raise RuntimeError("image changed since `request`; run `request` again")
    validate_request(request, now=now)  # the 10-minute floor may have passed since `request`
    if graph is None or page_id is None:
        configured_page, token = fb.load_credentials()
        page_id, graph = page_id or configured_page, graph or fb.Graph(token)
    page_name = fb.check_page(graph, page_id)
    log(f"PAGE_OK {page_name}")
    data: dict[str, Any] = {"message": request["caption"], "published": "true" if request["published"] else "false"}
    if not request["published"]:
        data["scheduled_publish_time"] = str(request["scheduled_publish_time"])
    receipt = {"status": "posting", "page_id": page_id, "started_at": fb.utc_now(),
               "scheduled_publish_at": request.get("scheduled_publish_at")}
    fb.write_json(receipt_path, receipt)
    try:
        result = graph.post_file(f"{page_id}/photos", data, "source", image, IMAGE_TYPES[image.suffix.lower()])
    except fb.GraphError as exc:
        answered = getattr(exc, "http_status", None) is not None
        receipt.update(status="post_failed" if answered else "post_interrupted", error=str(exc))
        fb.write_json(receipt_path, receipt)
        raise
    receipt.update(status="posted", posted_at=fb.utc_now(), photo_id=str(result.get("id") or ""),
                   post_id=str(result.get("post_id") or ""))
    fb.write_json(receipt_path, receipt)
    log(f"POSTED photo {receipt['photo_id']} post {receipt['post_id'] or '?'}")
    return refresh_status(post_dir, graph=graph)


def post_status(graph: fb.Graph, receipt: dict[str, Any]) -> dict[str, Any]:
    post_id = receipt.get("post_id")
    if not post_id:
        post_id = str(graph.get(receipt["photo_id"], fields="page_story_id").get("page_story_id") or "")
        receipt["post_id"] = post_id
    if not post_id:
        return {}
    return graph.get(post_id, fields="id,is_published,scheduled_publish_time,created_time,permalink_url")


def verify(request: dict[str, Any], status: dict[str, Any]) -> str | None:
    if status.get("is_published"):
        return "published_verified"
    if not request["published"] and status.get("scheduled_publish_time") is not None:
        if fb._unix(status["scheduled_publish_time"]) != request["scheduled_publish_time"]:
            raise RuntimeError("scheduled time on Facebook does not match the request; check Meta Business Suite")
        return "scheduled_verified"
    return None


def refresh_status(post_dir: Path, *, graph: fb.Graph | None = None) -> dict[str, Any]:
    request, receipt = fb.read_json(post_dir / REQUEST_NAME), fb.read_json(post_dir / RECEIPT_NAME)
    if not receipt.get("photo_id"):
        return receipt
    if graph is None:
        graph = fb.Graph(fb.load_credentials()[1])
    status = post_status(graph, receipt)
    receipt["last_status"], receipt["checked_at"] = status, fb.utc_now()
    if receipt.get("status") in DONE:
        verified = verify(request, status)
        if verified:
            receipt.update(status=verified, verified_at=fb.utc_now())
    fb.write_json(post_dir / RECEIPT_NAME, receipt)
    return receipt


def scheduled_posts(graph: fb.Graph | None = None, page_id: str | None = None) -> list[dict[str, Any]]:
    """The Page's queued posts (read only), to see which days already have one."""
    if graph is None or page_id is None:
        configured_page, token = fb.load_credentials()
        page_id, graph = page_id or configured_page, graph or fb.Graph(token)
    rows = graph.get(f"{page_id}/scheduled_posts", fields="id,message,scheduled_publish_time", limit=100).get("data") or []
    return sorted(rows, key=lambda row: fb._unix(row.get("scheduled_publish_time")))
