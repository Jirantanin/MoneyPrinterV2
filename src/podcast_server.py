"""
podcast_server.py — Unified FastAPI backend for the MPV2 Studio web UI.

Podcast routes:
  GET  /                          — Serve podcast_ui.html (tabbed: Podcast + Shorts)
  POST /api/generate              — Start pipeline, return episode_id
  GET  /api/stream/{episode_id}   — SSE progress stream
  GET  /api/images/{episode_id}   — List generated images
  GET  /api/episode/{episode_id}  — Full episode state
  POST /api/upload/{episode_id}   — Upload to YouTube
  POST /api/mark-uploaded/{episode_id} — Mark episode as manually uploaded
  GET  /static/{episode_id}/{filename} — Serve episode files

Shorts routes (all prefixed with /shorts/):
  GET  /shorts/api/accounts           — List YouTube accounts from cache
  POST /shorts/api/generate           — Start Shorts pipeline, return short_id
  GET  /shorts/api/stream/{short_id}  — SSE progress stream
  GET  /shorts/api/episode/{short_id} — Full short state
  POST /shorts/api/approve/{short_id} — Approve step
  POST /shorts/api/cancel/{short_id}  — Cancel pipeline
  POST /shorts/api/upload/{short_id}  — Upload to YouTube
  GET  /shorts/api/shorts             — List recent shorts
  GET  /shorts/static/{short_id}/{filename} — Serve short files

Launch via: from podcast_server import launch_podcast_server; launch_podcast_server()
"""

import asyncio
import glob
import io
import json
import os
import sys
import threading
from datetime import datetime

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import (
    get_podcast_settings_schema,
    get_podcast_system_settings,
    update_podcast_system_settings,
)

# Module-level episode state storage
# episodes[episode_id] = {
#   "podcast": Podcast instance,
#   "topic": str,
#   "language": str,
#   "mode": "auto" | "step",
#   "status": "idle" | "running" | "waiting_approval" | "done" | "uploaded" | "error" | "cancelled",
#   "current_step": int 0-4,
#   "step_states": list of 5 dicts,
#   "scenes": list of scene narrations,
#   "metadata": dict,
#   "error": str | None,
#   "episode_dir": str,
# }
episodes: dict = {}

# episode_events[episode_id] = list of SSE event dicts
episode_events: dict = {}

# episode_approvals[episode_id] = threading.Event for step-by-step mode
episode_approvals: dict = {}

app = FastAPI(title="MPV2 Studio")


def _read_ui_file(*relative_parts: str) -> str:
    ui_path = os.path.join(os.path.dirname(__file__), *relative_parts)
    with open(ui_path, "r", encoding="utf-8") as handle:
        return handle.read()


@app.get("/ui-assets/{filename}")
async def serve_ui_asset(filename: str):
    """Serve JS/CSS assets from src/ui/ directory."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".js", ".css"}:
        raise HTTPException(status_code=404)
    file_path = os.path.join(os.path.dirname(__file__), "ui", filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404)
    media_type = "application/javascript" if ext == ".js" else "text/css"
    return FileResponse(file_path, media_type=media_type)


# ---------------------------------------------------------------------------
# Shorts module-level state storage
# ---------------------------------------------------------------------------
# shorts[short_id] = {
#   "youtube": YouTube instance | None,
#   "account": dict (id, nickname, niche, language),
#   "niche": str,
#   "topic": str,
#   "language": str,
#   "mode": "auto" | "step",
#   "status": "idle" | "running" | "waiting_approval" | "done" | "error" | "cancelled",
#   "current_step": int 0-8,
#   "step_states": list of 9 dicts,
#   "metadata": dict,
#   "error": str | None,
#   "run_dir": str,
#   "video_path": str | None,
#   "cancelled": bool,
# }
shorts: dict = {}

# short_events[short_id] = list of SSE event dicts
short_events: dict = {}

# short_approvals[short_id] = threading.Event for step-by-step mode
short_approvals: dict = {}

# ---------------------------------------------------------------------------
# Clip-Shorts module-level state
# ---------------------------------------------------------------------------

# clip_events[clip_id] = list of SSE event dicts pushed by the builder thread
clip_events: dict = {}

_SHORTS_STEPS = [
    "Generate Topic",
    "Generate Script",
    "Generate Hook",
    "Generate Metadata",
    "Generate Image Prompts",
    "Generate Images",
    "Text-to-Speech",
    "Generate Subtitles",
    "Render Video",
]

_STEPS = [
    "Generate Script",
    "Generate Assets",
    "Generate Metadata",
    "Generate Thumbnail",
    "Render Video",
]

_TTS_SOURCES = {"edge", "elevenlabs", "gemini"}


def _get_youtube_auth_status() -> dict:
    from config import ROOT_DIR  # noqa: PLC0415

    token_path = os.path.join(ROOT_DIR, "token.json")
    client_secrets_path = os.path.join(ROOT_DIR, "client_secrets.json")
    status = {
        "authenticated": False,
        "token_exists": os.path.exists(token_path),
        "client_secrets_exists": os.path.exists(client_secrets_path),
        "message": "",
    }

    if not status["token_exists"]:
        status["message"] = "token.json not found. Generate is still available; upload manually if needed."
        return status

    try:
        scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ]
        creds = Credentials.from_authorized_user_file(token_path, scopes)
        if creds and not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        if creds and creds.valid:
            status["authenticated"] = True
            status["message"] = "YouTube upload is available."
        else:
            status["message"] = "YouTube token is invalid. Generate is still available; upload manually if needed."
    except Exception as exc:
        status["message"] = f"YouTube auth unavailable: {exc}"

    return status


def _default_tts_source(language: str) -> str:
    return "edge"


def _slugify_topic(topic: str) -> str:
    import re

    normalized = re.sub(r"[^a-z0-9]+", "-", (topic or "").lower()).strip("-")
    if normalized:
        return normalized
    compact = re.sub(r"\s+", "-", (topic or "").strip())
    if compact:
        return f"topic-{abs(hash(compact)) % 1000000:06d}"
    return "untitled"


def _normalize_tts_source(tts_source: str | None, language: str) -> str:
    normalized_language = (language or "English").strip()
    normalized_source = (tts_source or _default_tts_source(normalized_language)).strip().lower()
    if normalized_source not in _TTS_SOURCES:
        normalized_source = _default_tts_source(normalized_language)
    if normalized_language != "Thai" and normalized_source in ("elevenlabs", "gemini"):
        return "edge"
    return normalized_source


def _apply_request_system_settings(request_data: dict | None) -> None:
    if not isinstance(request_data, dict):
        return
    system_settings = request_data.get("system_settings")
    if isinstance(system_settings, dict):
        update_podcast_system_settings(system_settings)


def _podcast_root_dir() -> str:
    from config import ROOT_DIR  # noqa: PLC0415
    return os.path.join(ROOT_DIR, ".mp")


def _episode_dir_from_id(episode_id: str) -> str:
    return os.path.join(_podcast_root_dir(), episode_id)


def _episode_thumbnail_path(ep: dict) -> str:
    episode_dir = ep.get("episode_dir", "")
    return os.path.join(episode_dir, "thumbnail.png") if episode_dir else ""


def _episode_metadata_path(ep: dict) -> str:
    episode_dir = ep.get("episode_dir", "")
    return os.path.join(episode_dir, "metadata.json") if episode_dir else ""


def _episode_final_video_path(ep: dict) -> str:
    episode_dir = ep.get("episode_dir", "")
    return os.path.join(episode_dir, "final.mp4") if episode_dir else ""


def _episode_state_path(episode_dir: str) -> str:
    return os.path.join(episode_dir, "state.json")


def _load_episode_script_data(ep: dict) -> list:
    episode_dir = ep.get("episode_dir", "")
    if not episode_dir:
        return []
    return _load_json_if_exists(os.path.join(episode_dir, "script.json"), [])


def _is_v2_episode(ep: dict) -> bool:
    return (ep.get("episode_id") or "").startswith("podcast_v2_")


def _scene_asset_statuses(ep: dict) -> list[dict]:
    script_data = _load_episode_script_data(ep)
    if script_data:
        scene_count = len(script_data)
    else:
        scene_count = len(ep.get("scenes") or [])

    episode_dir = ep.get("episode_dir", "")
    is_v2 = _is_v2_episode(ep)
    statuses = []
    for index in range(scene_count):
        scene_num = str(index).zfill(2)
        audio_name = f"scene_{scene_num}.wav"
        audio_path = os.path.join(episode_dir, audio_name) if episode_dir else ""
        audio_exists = bool(audio_path and os.path.exists(audio_path))

        if is_v2:
            # V2: anchor image is scene_NN_0.png; fall back to legacy scene_NN.png
            anchor_name = f"scene_{scene_num}_0.png"
            anchor_path = os.path.join(episode_dir, anchor_name) if episode_dir else ""
            image_exists = bool(anchor_path and os.path.exists(anchor_path))
            if not image_exists:
                # Check legacy name in case assets were partially generated
                legacy_path = os.path.join(episode_dir, f"scene_{scene_num}.png") if episode_dir else ""
                image_exists = bool(legacy_path and os.path.exists(legacy_path))
                anchor_name = f"scene_{scene_num}.png" if image_exists else anchor_name
                anchor_path = legacy_path if image_exists else anchor_path
            image_name = anchor_name
            image_path = anchor_path
        else:
            image_name = f"scene_{scene_num}.png"
            image_path = os.path.join(episode_dir, image_name) if episode_dir else ""
            image_exists = bool(image_path and os.path.exists(image_path))

        statuses.append(
            {
                "scene_index": index,
                "image_exists": image_exists,
                "audio_exists": audio_exists,
                "image_url": (
                    f"/static/{ep['episode_id']}/{image_name}?ts={int(os.path.getmtime(image_path))}"
                    if image_exists and ep.get("episode_id")
                    else None
                ),
            }
        )
    return statuses


def _all_scene_assets_ready(ep: dict) -> bool:
    statuses = _scene_asset_statuses(ep)
    return bool(statuses) and all(item["image_exists"] and item["audio_exists"] for item in statuses)


def _invalidate_outputs_after_asset_regen(ep: dict) -> None:
    episode_dir = ep.get("episode_dir", "")
    if not episode_dir:
        return
    _delete_file(os.path.join(episode_dir, "concat_list.txt"))
    _delete_file(_episode_final_video_path(ep))
    _delete_file(_episode_metadata_path(ep))
    _delete_file(_episode_thumbnail_path(ep))
    ep["metadata"] = {}
    for index in range(2, len(ep["step_states"])):
        ep["step_states"][index]["status"] = "pending"
        ep["step_states"][index]["message"] = ""


def _refresh_asset_step_state(ep: dict) -> None:
    if _all_scene_assets_ready(ep):
        ep["step_states"][1]["status"] = "done"
        ep["step_states"][1]["message"] = ""
        if ep.get("status") == "error" and ep.get("current_step") == 1:
            ep["status"] = "idle"
            ep["error"] = None
    else:
        ep["step_states"][1]["status"] = "pending"
        ep["step_states"][1]["message"] = "Some scene assets are still missing."
        if ep.get("current_step") == 1 and ep.get("status") == "error":
            ep["error"] = ep["step_states"][1]["message"]


def _next_incomplete_step(step_states: list[dict]) -> int | None:
    for index, step in enumerate(step_states or []):
        if step.get("status") != "done":
            return index
    return None


def _can_resume_episode(ep: dict) -> bool:
    if not ep or ep.get("status") == "running":
        return False
    return _next_incomplete_step(ep.get("step_states") or []) is not None


def _is_episode_uploaded(ep: dict) -> bool:
    metadata = ep.get("metadata") or {}
    return ep.get("status") == "uploaded" or bool(metadata.get("uploaded_at") or metadata.get("video_id"))


def _delete_file(path: str) -> None:
    if path and os.path.exists(path):
        os.remove(path)


def _delete_glob(pattern: str) -> None:
    for path in glob.glob(pattern):
        if os.path.isfile(path):
            os.remove(path)


def _redo_message(step_index: int) -> str:
    return f"Redo requested from {_STEPS[step_index]}."


def _invalidate_episode_from_step(episode_id: str, step_index: int) -> None:
    ep = episodes[episode_id]
    episode_dir = ep.get("episode_dir", "")
    if not episode_dir:
        raise ValueError("episode_dir not ready yet")
    if not os.path.isdir(episode_dir):
        raise FileNotFoundError(f"episode_dir not found at {episode_dir}")

    if step_index not in range(len(_STEPS)):
        raise ValueError("invalid step")

    script_path = os.path.join(episode_dir, "script.json")
    metadata_path = _episode_metadata_path(ep)
    thumbnail_path = _episode_thumbnail_path(ep)
    final_path = _episode_final_video_path(ep)
    concat_path = os.path.join(episode_dir, "concat_list.txt")

    if step_index == 0:
        _delete_file(script_path)
        _delete_glob(os.path.join(episode_dir, "scene_*.png"))
        _delete_glob(os.path.join(episode_dir, "scene_*.wav"))
        _delete_file(metadata_path)
        _delete_file(thumbnail_path)
        _delete_file(os.path.join(episode_dir, "thumbnail_prompt.txt"))
        ep["thumbnail_gen_prompt"] = ""
        _delete_glob(os.path.join(episode_dir, "scene_*.mp4"))
        _delete_file(concat_path)
        _delete_file(final_path)
        ep["scenes"] = []
        ep["metadata"] = {}
    elif step_index == 1:
        _delete_glob(os.path.join(episode_dir, "scene_*.png"))
        _delete_glob(os.path.join(episode_dir, "scene_*.wav"))
        _delete_file(metadata_path)
        _delete_file(thumbnail_path)
        _delete_file(os.path.join(episode_dir, "thumbnail_prompt.txt"))
        ep["thumbnail_gen_prompt"] = ""
        _delete_glob(os.path.join(episode_dir, "scene_*.mp4"))
        _delete_file(concat_path)
        _delete_file(final_path)
        ep["metadata"] = {}
    elif step_index == 2:
        _delete_file(metadata_path)
        _delete_file(thumbnail_path)
        _delete_file(os.path.join(episode_dir, "thumbnail_prompt.txt"))
        ep["thumbnail_gen_prompt"] = ""
        _delete_file(concat_path)
        _delete_file(final_path)
        ep["metadata"] = {}
    elif step_index == 3:
        _delete_file(thumbnail_path)
        _delete_file(os.path.join(episode_dir, "thumbnail_prompt.txt"))
        ep["thumbnail_gen_prompt"] = ""
        _delete_file(concat_path)
        _delete_file(final_path)
    elif step_index == 4:
        _delete_file(concat_path)
        _delete_file(final_path)

    for index in range(step_index, len(ep["step_states"])):
        ep["step_states"][index]["status"] = "pending"
        ep["step_states"][index]["message"] = ""

    ep["status"] = "idle"
    ep["current_step"] = step_index
    ep["error"] = None
    ep["cancelled"] = False
    ep["logs"] = (ep.get("logs") or [])[-499:] + [_redo_message(step_index)]


def _persist_episode_state(episode_id: str) -> None:
    ep = episodes.get(episode_id)
    if not ep:
        return

    episode_dir = ep.get("episode_dir", "")
    if not episode_dir:
        return

    os.makedirs(episode_dir, exist_ok=True)
    with open(_episode_state_path(episode_dir), "w", encoding="utf-8") as f:
        json.dump(
            {
                "topic": ep.get("topic", ""),
                "creative_direction": ep.get("creative_direction", ""),
                "language": ep.get("language", "English"),
                "mode": ep.get("mode", "auto"),
                "tts_source": ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
                "script_mode": bool(ep.get("script_mode", False)),
                "raw_script": ep.get("raw_script", ""),
                "status": ep.get("status", "idle"),
                "current_step": ep.get("current_step", 0),
                "step_states": ep.get("step_states") or _make_step_states(),
                "error": ep.get("error"),
                "logs": (ep.get("logs") or [])[-500:],
                "beat_qc": ep.get("beat_qc") or {},
                "script_qc": ep.get("script_qc") or {},
                "updated_at": datetime.now().isoformat(),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def _infer_step_states_from_dir(episode_dir: str) -> tuple[list, str, int]:
    step_states = _make_step_states()
    current_step = 0
    status = "idle"

    script_path = os.path.join(episode_dir, "script.json")
    metadata_path = os.path.join(episode_dir, "metadata.json")
    final_path = os.path.join(episode_dir, "final.mp4")
    thumbnail_path = os.path.join(episode_dir, "thumbnail.png")
    scene_pngs = glob.glob(os.path.join(episode_dir, "scene_*.png"))
    scene_wavs = glob.glob(os.path.join(episode_dir, "scene_*.wav"))

    if os.path.exists(script_path):
        step_states[0]["status"] = "done"
        current_step = max(current_step, 1)
    if scene_pngs and scene_wavs:
        step_states[1]["status"] = "done"
        current_step = max(current_step, 2)
    if os.path.exists(metadata_path):
        step_states[2]["status"] = "done"
        current_step = max(current_step, 3)
    thumbnail_prompt_path = os.path.join(episode_dir, "thumbnail_prompt.txt")
    if os.path.exists(thumbnail_prompt_path) or os.path.exists(thumbnail_path):
        step_states[3]["status"] = "done"
        current_step = max(current_step, 4)
    if os.path.exists(final_path):
        step_states[4]["status"] = "done"
        current_step = 4

    done_count = sum(1 for step in step_states if step["status"] == "done")
    if done_count == len(step_states):
        status = "done"
    elif done_count > 0:
        status = "partial"
    return step_states, status, current_step


def _load_json_if_exists(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_text_if_exists(path: str) -> str:
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _topic_from_episode_id(episode_id: str) -> str:
    if not episode_id.startswith("podcast_"):
        return episode_id
    base = episode_id[len("podcast_"):]
    # New format: podcast_YYYYMMDD_HHMMSS — return as a readable date string
    import re as _re
    if _re.fullmatch(r"\d{8}_\d{6}", base):
        return base.replace("_", " ")
    # Old format: podcast_{slug}_{YYYYMMDD} — strip the trailing date and humanise slug
    parts = base.rsplit("_", 1)
    slug = parts[0] if parts else base
    return slug.replace("-", " ").strip()


def _restore_episode_from_disk(episode_id: str) -> dict | None:
    episode_dir = _episode_dir_from_id(episode_id)
    if not os.path.isdir(episode_dir):
        return None

    script_data = _load_json_if_exists(os.path.join(episode_dir, "script.json"), [])
    beat_qc = _load_json_if_exists(os.path.join(episode_dir, "beat_qc.json"), {})
    script_qc = _load_json_if_exists(os.path.join(episode_dir, "script_qc.json"), {})
    metadata = _load_json_if_exists(os.path.join(episode_dir, "metadata.json"), {})
    persisted_state = _load_json_if_exists(_episode_state_path(episode_dir), {})
    step_states, status, current_step = _infer_step_states_from_dir(episode_dir)
    scenes = [scene.get("narration", "") for scene in script_data if isinstance(scene, dict)]

    persisted_step_states = persisted_state.get("step_states")
    if isinstance(persisted_step_states, list) and len(persisted_step_states) == len(_STEPS):
        merged_step_states = []
        for index, disk_step in enumerate(step_states):
            persisted_step = persisted_step_states[index]
            merged_step_states.append(
                {
                    "name": disk_step.get("name") or _STEPS[index],
                    "status": "done" if disk_step.get("status") == "done" else persisted_step.get("status", disk_step.get("status", "pending")),
                    "message": persisted_step.get("message") or "",
                }
            )
        step_states = merged_step_states

    persisted_status = persisted_state.get("status")
    if isinstance(persisted_status, str) and persisted_status in {"idle", "done", "uploaded", "error", "cancelled", "partial"}:
        if persisted_status == "error" or _next_incomplete_step(step_states) is not None:
            status = persisted_status

    persisted_current_step = persisted_state.get("current_step")
    if isinstance(persisted_current_step, int):
        current_step = persisted_current_step

    ep = {
        "episode_id": episode_id,
        "podcast": None,
        "topic": persisted_state.get("topic") or metadata.get("title") or _topic_from_episode_id(episode_id),
        "creative_direction": persisted_state.get("creative_direction") or metadata.get("creative_direction", ""),
        "language": persisted_state.get("language") or metadata.get("language", "English"),
        "mode": persisted_state.get("mode", "auto"),
        "script_mode": bool(persisted_state.get("script_mode", False)),
        "raw_script": persisted_state.get("raw_script", ""),
        "tts_source": _normalize_tts_source(
            persisted_state.get("tts_source") or metadata.get("tts_source"),
            persisted_state.get("language") or metadata.get("language", "English"),
        ),
        "status": status,
        "current_step": current_step,
        "step_states": step_states,
        "scenes": scenes,
        "beat_qc": beat_qc or persisted_state.get("beat_qc") or {},
        "script_qc": script_qc or persisted_state.get("script_qc") or {},
        "metadata": metadata,
        "error": persisted_state.get("error"),
        "episode_dir": episode_dir,
        "cancelled": False,
        "logs": persisted_state.get("logs") if isinstance(persisted_state.get("logs"), list) else [],
        "thumbnail_gen_prompt": _load_text_if_exists(os.path.join(episode_dir, "thumbnail_prompt.txt")),
    }
    episodes[episode_id] = ep
    episode_events.setdefault(episode_id, [])
    episode_approvals.setdefault(episode_id, threading.Event())
    return ep


def _get_or_restore_episode(episode_id: str) -> dict | None:
    ep = episodes.get(episode_id)
    if ep:
        return ep
    return _restore_episode_from_disk(episode_id)


def _episode_summary_from_dir(episode_id: str, episode_dir: str) -> dict:
    metadata = _load_json_if_exists(os.path.join(episode_dir, "metadata.json"), {})
    step_states, status, current_step = _infer_step_states_from_dir(episode_dir)
    done_count = sum(1 for step in step_states if step["status"] == "done")
    is_uploaded = bool(metadata.get("video_id") or metadata.get("uploaded_at"))
    return {
        "episode_id": episode_id,
        "title": metadata.get("title") or _topic_from_episode_id(episode_id),
        "status": status,
        "current_step": current_step,
        "completed_steps": done_count,
        "is_uploaded": is_uploaded,
        "can_resume": _next_incomplete_step(step_states) is not None,
        "video_url": metadata.get("video_url"),
        "uploaded_at": metadata.get("uploaded_at"),
        "updated_at": datetime.fromtimestamp(os.path.getmtime(episode_dir)).isoformat(),
        "thumbnail_url": (
            f"/static/{episode_id}/thumbnail.png?ts={int(os.path.getmtime(os.path.join(episode_dir, 'thumbnail.png')))}"
            if os.path.exists(os.path.join(episode_dir, "thumbnail.png"))
            else None
        ),
    }


def _build_thumbnail_prompt_pack(ep: dict) -> dict:
    metadata = ep.get("metadata") or {}
    title = (metadata.get("title") or ep.get("topic") or "").strip()
    description = (metadata.get("description") or "").strip()
    tags = metadata.get("tags") or []

    title_main = title or "Podcast Episode"
    title_support = ""
    if ":" in title_main:
        left, right = [part.strip() for part in title_main.split(":", 1)]
        if left:
            title_main = left
        if right:
            title_support = right
    elif len(title_main) > 42:
        parts = title_main.split()
        title_main = " ".join(parts[:4]).strip()
        title_support = " ".join(parts[4:]).strip()

    first_sentence = ""
    if description:
        first_sentence = description.split(".")[0].strip()
    hook = title_support or first_sentence or title
    if len(hook) > 72:
        hook = hook[:69].rstrip() + "..."

    headline = hook or title_main or "Podcast Episode"
    headline = headline.replace(":", "").replace('"', "").strip()
    if len(headline) > 34:
        headline = headline[:31].rstrip() + "..."

    supporting_text = title_main.strip()
    if supporting_text.lower() == headline.lower():
        supporting_text = first_sentence or title or "Podcast Episode"
    if len(supporting_text) > 56:
        supporting_text = supporting_text[:53].rstrip() + "..."

    visual_keywords = ", ".join(tags[:4]) if tags else ep.get("topic", "")
    canva_prompt = (
        "Use the uploaded image as the main background for a YouTube podcast thumbnail.\n\n"
        f"Create a bold, cinematic YouTube thumbnail for a podcast episode titled:\n\"{title}\"\n\n"
        f"Main headline:\n{headline.upper()}\n\n"
        f"Supporting text:\n{(supporting_text or 'Podcast Episode')}\n\n"
        "Add a small red badge in the top-left corner that says:\nPODCAST\n\n"
        "Keep the main subject from the uploaded image visible and use empty or darker areas for text placement.\n"
        "Style direction: cinematic, high contrast, readable on mobile, uncluttered, premium YouTube thumbnail.\n"
        f"Visual cues to emphasize: {visual_keywords}\n"
        "Do not add watermarks. Avoid messy layouts or tiny text."
    )

    return {
        "headline": headline.upper(),
        "supporting_text": supporting_text,
        "badge_text": "PODCAST",
        "canva_prompt": canva_prompt,
        "gen_prompt": ep.get("thumbnail_gen_prompt", ""),
    }


def _save_thumbnail_image(upload_bytes: bytes, output_path: str) -> None:
    with Image.open(io.BytesIO(upload_bytes)) as img:
        img = img.convert("RGB")
        target_ratio = 16 / 9
        width, height = img.size
        source_ratio = width / height if height else target_ratio

        if source_ratio > target_ratio:
            new_width = int(height * target_ratio)
            left = max(0, (width - new_width) // 2)
            img = img.crop((left, 0, left + new_width, height))
        elif source_ratio < target_ratio:
            new_height = int(width / target_ratio)
            top = max(0, (height - new_height) // 2)
            img = img.crop((0, top, width, top + new_height))

        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        img.save(output_path, format="PNG")


def _make_step_states() -> list:
    return [{"name": name, "status": "pending", "message": ""} for name in _STEPS]


class _StdoutCapture:
    """Captures stdout and mirrors writes to the original stdout and SSE event queue."""

    def __init__(self, episode_id: str, original_stdout):
        self.episode_id = episode_id
        self.original = original_stdout

    def write(self, text: str):
        self.original.write(text)
        text = text.strip()
        if text:
            ep = episodes.get(self.episode_id)
            if ep is not None:
                ep.setdefault("logs", []).append(text)
                ep["logs"] = ep["logs"][-500:]
            episode_events.setdefault(self.episode_id, []).append(
                {
                    "type": "log",
                    "step": episodes[self.episode_id]["current_step"],
                    "message": text,
                }
            )
            _persist_episode_state(self.episode_id)

    def flush(self):
        self.original.flush()


def _push_event(episode_id: str, event: dict):
    """Append an SSE event to the episode's event queue."""
    episode_events.setdefault(episode_id, []).append(event)


def _wait_for_approval(episode_id: str) -> bool:
    """Block until user approves or cancels. Returns True to continue, False to cancel."""
    ep = episodes[episode_id]
    ep["status"] = "waiting_approval"
    _persist_episode_state(episode_id)
    evt = episode_approvals.get(episode_id)
    if evt:
        evt.wait()
        evt.clear()
    ep["status"] = "running"
    _persist_episode_state(episode_id)
    return not ep.get("cancelled", False)


def _run_step(episode_id: str, step_index: int, fn) -> bool:
    """Run a single pipeline step. Returns False if error or cancelled."""
    ep = episodes[episode_id]
    ep["current_step"] = step_index
    ep["step_states"][step_index]["status"] = "running"
    ep["step_states"][step_index]["message"] = ""
    _persist_episode_state(episode_id)
    _push_event(episode_id, {"type": "step_start", "step": step_index, "name": _STEPS[step_index]})
    try:
        result = fn()
        ep["step_states"][step_index]["status"] = "done"
        ep["step_states"][step_index]["message"] = ""
        _persist_episode_state(episode_id)
        _push_event(episode_id, {"type": "step_done", "step": step_index})
        return result
    except Exception as exc:
        ep["step_states"][step_index]["status"] = "error"
        ep["step_states"][step_index]["message"] = str(exc)
        _push_event(episode_id, {"type": "step_error", "step": step_index, "error": str(exc)})
        ep["status"] = "error"
        ep["error"] = str(exc)
        _persist_episode_state(episode_id)
        return None  # sentinel for error


def _build_podcast_instance(ep: dict):
    from classes.Podcast import Podcast  # noqa: PLC0415

    podcast = Podcast(
        topic=ep.get("topic", ""),
        language=ep.get("language", "English"),
        tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
        creative_direction=ep.get("creative_direction", ""),
        visual_style=ep.get("visual_style", ""),
        script_mode=ep.get("script_mode", False),
        raw_script=ep.get("raw_script", ""),
    )
    podcast.episode_dir = ep.get("episode_dir", "")
    podcast.metadata = ep.get("metadata") or {}
    ep["podcast"] = podcast
    return podcast


def _run_pipeline(episode_id: str, start_step: int = 0):
    """Background thread — runs the full Podcast pipeline for an episode."""
    ep = episodes[episode_id]
    ep["status"] = "running"
    ep["cancelled"] = False
    ep["error"] = None
    step_mode = ep.get("mode") == "step"
    start_step = max(0, min(start_step, len(_STEPS) - 1))

    original_stdout = sys.stdout
    sys.stdout = _StdoutCapture(episode_id, original_stdout)

    try:
        podcast = _build_podcast_instance(ep)
        _persist_episode_state(episode_id)

        if start_step <= 0:
            if ep.get("script_mode"):
                if not podcast.episode_dir:
                    from config import ROOT_DIR  # noqa: PLC0415
                    episode_dir = os.path.join(ROOT_DIR, ".mp", episode_id)
                    os.makedirs(episode_dir, exist_ok=True)
                    podcast.episode_dir = episode_dir
                    ep["episode_dir"] = episode_dir
                    _persist_episode_state(episode_id)
                result = _run_step(episode_id, 0, lambda: podcast.generate_script_from_text(ep["raw_script"]))
            else:
                result = _run_step(episode_id, 0, lambda: podcast.generate_script(ep["topic"]))
            if result is None:
                return
            scenes = result
            ep["scenes"] = [s.get("narration", "") for s in (scenes or [])]
            ep["episode_dir"] = podcast.episode_dir
            ep["beat_qc"] = _load_json_if_exists(os.path.join(ep["episode_dir"], "beat_qc.json"), {})
            ep["script_qc"] = _load_json_if_exists(os.path.join(ep["episode_dir"], "script_qc.json"), {})

            _episode_metadata_path = os.path.join(ep["episode_dir"], "metadata.json")
            try:
                _lang_meta = {}
                if os.path.exists(_episode_metadata_path):
                    with open(_episode_metadata_path, "r", encoding="utf-8") as _f:
                        _lang_meta = json.load(_f)
                _lang_meta["language"] = ep.get("language", "English")
                _lang_meta["tts_source"] = ep.get("tts_source", _default_tts_source(ep.get("language", "English")))
                _lang_meta["creative_direction"] = ep.get("creative_direction", "")
                _lang_meta["visual_style"] = ep.get("visual_style", "")
                with open(_episode_metadata_path, "w", encoding="utf-8") as _f:
                    json.dump(_lang_meta, _f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            _persist_episode_state(episode_id)

        if step_mode and start_step <= 0:
            _push_event(episode_id, {"type": "waiting_approval", "step": 0, "next_step": 1, "next_name": _STEPS[1]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 1:
            if start_step == 1:
                _push_event(episode_id, {"type": "resume", "step": 1, "message": f"Resuming from {_STEPS[1]}."})
            result = _run_step(episode_id, 1, podcast.generate_assets)
            if result is None and ep["status"] == "error":
                return

        if step_mode and start_step <= 1:
            _push_event(episode_id, {"type": "waiting_approval", "step": 1, "next_step": 2, "next_name": _STEPS[2]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        # Step 2: Generate Metadata
        def _gen_metadata():
            meta = podcast.generate_metadata()
            ep["metadata"] = meta
            _persist_episode_state(episode_id)
            return meta

        if start_step <= 2:
            if start_step == 2:
                _push_event(episode_id, {"type": "resume", "step": 2, "message": f"Resuming from {_STEPS[2]}."})
            result = _run_step(episode_id, 2, _gen_metadata)
            if result is None and ep["status"] == "error":
                return

        if step_mode and start_step <= 2:
            _push_event(episode_id, {"type": "waiting_approval", "step": 2, "next_step": 3, "next_name": _STEPS[3]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 3:
            if start_step == 3:
                _push_event(episode_id, {"type": "resume", "step": 3, "message": f"Resuming from {_STEPS[3]}."})
            result = _run_step(episode_id, 3, podcast.generate_thumbnail)
            if result is None and ep["status"] == "error":
                return
            if isinstance(result, str):
                ep["thumbnail_gen_prompt"] = result

        if step_mode and start_step <= 3:
            _push_event(episode_id, {"type": "waiting_approval", "step": 3, "next_step": 4, "next_name": _STEPS[4]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 4:
            if start_step == 4:
                _push_event(episode_id, {"type": "resume", "step": 4, "message": f"Resuming from {_STEPS[4]}."})
            result = _run_step(episode_id, 4, podcast.render)
            if result is None and ep["status"] == "error":
                return

        ep["status"] = "done"
        _persist_episode_state(episode_id)
        _push_event(episode_id, {"type": "complete"})

    except Exception as exc:
        ep["status"] = "error"
        ep["error"] = str(exc)
        _persist_episode_state(episode_id)
        _push_event(episode_id, {"type": "error", "message": str(exc)})
    finally:
        sys.stdout = original_stdout


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the Studio UI assembled from the shell and component partials."""
    content = _read_ui_file("podcast_ui.html")
    content = content.replace("{{PODCAST_COMPONENT}}", _read_ui_file("ui", "podcast_component.html"))
    content = content.replace("{{SHORTS_COMPONENT}}", _read_ui_file("ui", "shorts_component.html"))
    content = content.replace("{{CLIP_SHORTS_COMPONENT}}", _read_ui_file("ui", "clip_shorts_component.html"))
    content = content.replace("{{PODCAST_V2_COMPONENT}}", _read_ui_file("ui", "podcast_v2_component.html"))
    return HTMLResponse(content=content)


@app.get("/api/settings/podcast")
async def api_get_podcast_settings():
    return JSONResponse({
        "ok": True,
        "settings": get_podcast_system_settings(),
        "schema": get_podcast_settings_schema(),
    })


@app.post("/api/settings/podcast")
async def api_save_podcast_settings(request_data: dict | None = None):
    try:
        settings = update_podcast_system_settings(request_data or {})
    except Exception as exc:
        return JSONResponse({"error": f"failed to save settings: {exc}"}, status_code=400)
    return JSONResponse({
        "ok": True,
        "settings": settings,
        "schema": get_podcast_settings_schema(),
    })


@app.post("/api/generate")
async def api_generate(request_data: dict):
    """Start the podcast pipeline for a topic. Returns episode_id."""
    _apply_request_system_settings(request_data)
    script_mode = bool(request_data.get("script_mode", False))
    raw_script = (request_data.get("raw_script") or "").strip()
    topic = (request_data.get("topic") or "").strip()

    if script_mode:
        if not raw_script:
            return JSONResponse({"error": "raw_script is required in script mode"}, status_code=400)
        title = (request_data.get("title") or "Custom Script").strip()
    else:
        if not topic:
            return JSONResponse({"error": "topic is required"}, status_code=400)
        title = topic

    mode = request_data.get("mode", "auto")
    if mode not in ("auto", "step"):
        mode = "auto"

    language = (request_data.get("language") or "English").strip()
    if language not in ("Thai", "English"):
        language = "English"
    tts_source = _normalize_tts_source(request_data.get("tts_source"), language)
    creative_direction = (request_data.get("creative_direction") or "").strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    episode_id = f"podcast_{timestamp}"

    # Initialize episode state
    episodes[episode_id] = {
        "episode_id": episode_id,
        "podcast": None,
        # In script mode, use the first 150 chars of the raw script as topic context
        # so the metadata LLM generates a YouTube title from actual content, not user label.
        # The user-provided title is captured in the episode_id slug for display only.
        "topic": raw_script[:150].strip() if script_mode else title,
        "creative_direction": creative_direction,
        "visual_style": (request_data.get("visual_style") or "").strip(),
        "language": language,
        "tts_source": tts_source,
        "mode": mode,
        "script_mode": script_mode,
        "raw_script": raw_script,
        "status": "idle",
        "current_step": 0,
        "step_states": _make_step_states(),
        "scenes": [],
        "beat_qc": {},
        "script_qc": {},
        "metadata": {},
        "error": None,
        "episode_dir": "",
        "cancelled": False,
        "logs": [],
    }
    episode_events[episode_id] = []
    episode_approvals[episode_id] = threading.Event()

    # Start pipeline in background thread
    t = threading.Thread(target=_run_pipeline, args=(episode_id,), daemon=True)
    t.start()

    return JSONResponse({"episode_id": episode_id})


@app.get("/api/episodes")
async def api_episodes():
    """List saved podcast episodes from disk."""
    root_dir = _podcast_root_dir()
    if not os.path.isdir(root_dir):
        return JSONResponse({"episodes": []})

    episode_dirs = [
        entry for entry in os.scandir(root_dir)
        if entry.is_dir() and entry.name.startswith("podcast_")
    ]
    summaries = [
        _episode_summary_from_dir(entry.name, entry.path)
        for entry in sorted(episode_dirs, key=lambda e: e.stat().st_mtime, reverse=True)
    ]
    return JSONResponse({"episodes": summaries})


@app.post("/api/load/{episode_id}")
async def api_load_episode(episode_id: str):
    """Restore an existing episode from disk into active state."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    return JSONResponse({"ok": True, "episode_id": episode_id})


@app.post("/api/resume/{episode_id}")
async def api_resume_episode(episode_id: str, request_data: dict | None = None):
    """Resume an episode from the first incomplete step."""
    _apply_request_system_settings(request_data)
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    if ep.get("status") == "running":
        return JSONResponse({"error": "episode is already running"}, status_code=409)

    next_step = _next_incomplete_step(ep.get("step_states") or [])
    if next_step is None:
        return JSONResponse({"error": "episode is already complete"}, status_code=400)
    if next_step == 0:
        return JSONResponse({"error": "resume is only available after script generation created episode files"}, status_code=400)

    body = request_data or {}
    mode = body.get("mode", ep.get("mode", "auto"))
    if mode not in ("auto", "step"):
        mode = "auto"
    ep["tts_source"] = _normalize_tts_source(body.get("tts_source", ep.get("tts_source")), ep.get("language", "English"))

    ep["mode"] = mode
    ep["status"] = "idle"
    ep["cancelled"] = False
    ep["error"] = None
    for index in range(next_step, len(ep["step_states"])):
        if ep["step_states"][index].get("status") != "done":
            ep["step_states"][index]["status"] = "pending"
            ep["step_states"][index]["message"] = ""

    ep["current_step"] = next_step
    episode_events[episode_id] = []
    episode_approvals.setdefault(episode_id, threading.Event()).clear()
    _persist_episode_state(episode_id)

    pipeline_fn = _run_v2_pipeline if _is_v2_episode(ep) else _run_pipeline
    t = threading.Thread(target=pipeline_fn, args=(episode_id, next_step), daemon=True)
    t.start()
    return JSONResponse({"ok": True, "episode_id": episode_id, "resumed_from_step": next_step})


@app.post("/api/redo/{episode_id}")
async def api_redo_episode(episode_id: str, request_data: dict | None = None):
    """Invalidate outputs from a step onward, then rerun from that step."""
    _apply_request_system_settings(request_data)
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    if ep.get("status") == "running":
        return JSONResponse({"error": "episode is already running"}, status_code=409)
    if _is_episode_uploaded(ep):
        return JSONResponse({"error": "redo is blocked for uploaded/history episodes"}, status_code=409)

    body = request_data or {}
    step = body.get("step")
    if not isinstance(step, int) or step not in range(len(_STEPS)):
        return JSONResponse({"error": "invalid step"}, status_code=400)

    mode = body.get("mode", ep.get("mode", "auto"))
    if mode not in ("auto", "step"):
        mode = "auto"
    ep["tts_source"] = _normalize_tts_source(body.get("tts_source", ep.get("tts_source")), ep.get("language", "English"))

    try:
        ep["mode"] = mode
        _invalidate_episode_from_step(episode_id, step)
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    episode_events[episode_id] = [{"type": "log", "step": step, "message": _redo_message(step)}]
    episode_approvals.setdefault(episode_id, threading.Event()).clear()
    _persist_episode_state(episode_id)

    pipeline_fn = _run_v2_pipeline if _is_v2_episode(ep) else _run_pipeline
    t = threading.Thread(target=pipeline_fn, args=(episode_id, step), daemon=True)
    t.start()
    return JSONResponse({"ok": True, "episode_id": episode_id, "redo_from_step": step})


@app.post("/api/approve/{episode_id}")
async def api_approve(episode_id: str):
    """Approve the current step and continue to next (step-by-step mode)."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    evt = episode_approvals.get(episode_id)
    if evt:
        evt.set()
    return JSONResponse({"ok": True})


@app.post("/api/asset/{episode_id}/regen")
async def api_regen_scene_asset(episode_id: str, request_data: dict | None = None):
    _apply_request_system_settings(request_data)
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    if ep.get("status") == "running":
        return JSONResponse({"error": "episode is already running"}, status_code=409)
    if _is_episode_uploaded(ep):
        return JSONResponse({"error": "asset regen is blocked for uploaded/history episodes"}, status_code=409)

    body = request_data or {}
    scene_index = body.get("scene_index")
    if not isinstance(scene_index, int):
        return JSONResponse({"error": "scene_index must be an integer"}, status_code=400)

    original_stdout = sys.stdout
    sys.stdout = _StdoutCapture(episode_id, original_stdout)
    try:
        if _is_v2_episode(ep):
            podcast = _build_podcast_v2_instance(ep)
            scenes = podcast._load_script_scenes()
            total_scenes = len(scenes)
            print(f"Regenerating V2 scene asset {scene_index + 1}...")
            await asyncio.to_thread(
                podcast.generate_scene_assets, scene_index, True, True, total_scenes
            )
        else:
            podcast = _build_podcast_instance(ep)
            print(f"Regenerating scene asset {scene_index + 1}...")
            await asyncio.to_thread(podcast.generate_scene_assets, scene_index, True, True)
        _invalidate_outputs_after_asset_regen(ep)
        _refresh_asset_step_state(ep)
        ep["status"] = "idle"
        ep["current_step"] = 1
        ep["cancelled"] = False
        _persist_episode_state(episode_id)
        return JSONResponse(
            {
                "ok": True,
                "episode_id": episode_id,
                "scene_index": scene_index,
                "asset_statuses": _scene_asset_statuses(ep),
                "can_resume": _can_resume_episode(ep),
            }
        )
    except Exception as exc:
        ep["step_states"][1]["status"] = "error"
        ep["step_states"][1]["message"] = str(exc)
        ep["status"] = "error"
        ep["current_step"] = 1
        ep["error"] = str(exc)
        _persist_episode_state(episode_id)
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        sys.stdout = original_stdout


@app.post("/api/cancel/{episode_id}")
async def api_cancel(episode_id: str):
    """Cancel the pipeline (works in both auto and step mode)."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)
    ep["cancelled"] = True
    ep["status"] = "cancelled"
    _persist_episode_state(episode_id)
    _push_event(episode_id, {"type": "cancelled"})
    # Unblock any waiting approval
    evt = episode_approvals.get(episode_id)
    if evt:
        evt.set()
    return JSONResponse({"ok": True})


@app.get("/api/stream/{episode_id}")
async def api_stream(episode_id: str):
    """SSE endpoint — streams step and log events for the given episode."""
    if not _get_or_restore_episode(episode_id):
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    async def event_generator():
        cursor = 0
        keep_alive_counter = 0
        while True:
            ep = episodes.get(episode_id)
            events = episode_events.get(episode_id, [])

            # Yield any new events
            while cursor < len(events):
                evt = events[cursor]
                cursor += 1
                yield f"data: {json.dumps(evt)}\n\n"

            # Check if pipeline is finished (and we have sent all events)
            if ep and ep["status"] in ("done", "error", "cancelled") and cursor >= len(events):
                return

            # Keep-alive comment every ~15 seconds (30 * 0.5s sleeps)
            keep_alive_counter += 1
            if keep_alive_counter >= 30:
                keep_alive_counter = 0
                yield ": keep-alive\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/images/{episode_id}")
async def api_images(episode_id: str):
    """List available scene images for an episode."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    episode_dir = ep.get("episode_dir", "")
    if not episode_dir or not os.path.isdir(episode_dir):
        return JSONResponse({"images": [], "asset_statuses": _scene_asset_statuses(ep)})

    # Collect scene_NN.png and thumbnail.png
    scene_files = sorted(glob.glob(os.path.join(episode_dir, "scene_*.png")))
    thumbnail = os.path.join(episode_dir, "thumbnail.png")
    all_files = scene_files[:]
    if os.path.exists(thumbnail):
        all_files.append(thumbnail)

    filenames = [os.path.basename(p) for p in all_files]
    return JSONResponse({"images": filenames, "asset_statuses": _scene_asset_statuses(ep)})


@app.get("/api/episode/{episode_id}")
async def api_episode(episode_id: str):
    """Return full episode state (status, steps, scenes, metadata)."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    return JSONResponse(
        {
            "episode_id": episode_id,
            "topic": ep["topic"],
            "creative_direction": ep.get("creative_direction", ""),
            "visual_style": ep.get("visual_style", ""),
            "language": ep.get("language", "English"),
            "tts_source": ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
            "mode": ep.get("mode", "auto"),
            "status": ep["status"],
            "current_step": ep["current_step"],
            "step_states": ep["step_states"],
            "scenes": ep["scenes"],
            "scene_count": len(_load_episode_script_data(ep)) or len(ep["scenes"]),
            "beat_qc": (
                _load_json_if_exists(os.path.join(ep["episode_dir"], "beat_qc.json"), {})
                if ep.get("episode_dir")
                else ep.get("beat_qc", {})
            ),
            "script_qc": (
                _load_json_if_exists(os.path.join(ep["episode_dir"], "script_qc.json"), {})
                if ep.get("episode_dir")
                else ep.get("script_qc", {})
            ),
            "asset_statuses": _scene_asset_statuses(ep),
            "metadata": ep["metadata"],
            "episode_dir": ep["episode_dir"],
            "error": ep["error"],
            "logs": ep.get("logs") or [],
            "can_resume": _can_resume_episode(ep),
            "next_incomplete_step": _next_incomplete_step(ep.get("step_states") or []),
            "is_uploaded": bool((ep.get("metadata") or {}).get("video_id") or (ep.get("metadata") or {}).get("uploaded_at")),
            "video_url": (ep.get("metadata") or {}).get("video_url"),
            "uploaded_at": (ep.get("metadata") or {}).get("uploaded_at"),
            "thumbnail_url": (
                f"/static/{episode_id}/thumbnail.png?ts={int(os.path.getmtime(_episode_thumbnail_path(ep)))}"
                if os.path.exists(_episode_thumbnail_path(ep))
                else None
            ),
            "final_video_url": (
                f"/static/{episode_id}/final.mp4?ts={int(os.path.getmtime(os.path.join(ep['episode_dir'], 'final.mp4')))}"
                if ep.get("episode_dir") and os.path.exists(os.path.join(ep["episode_dir"], "final.mp4"))
                else None
            ),
            "thumbnail_prompt_pack": _build_thumbnail_prompt_pack(ep),
        }
    )


@app.post("/api/thumbnail/{episode_id}")
async def api_thumbnail_upload(episode_id: str, file: UploadFile = File(...)):
    """Replace the generated thumbnail with a user-supplied image."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    episode_dir = ep.get("episode_dir", "")
    if not episode_dir or not os.path.isdir(episode_dir):
        return JSONResponse({"error": "episode_dir not ready yet"}, status_code=400)

    if not (file.content_type or "").startswith("image/"):
        return JSONResponse({"error": "file must be an image"}, status_code=400)

    try:
        upload_bytes = await file.read()
        if not upload_bytes:
            return JSONResponse({"error": "empty file"}, status_code=400)
        output_path = _episode_thumbnail_path(ep)
        _save_thumbnail_image(upload_bytes, output_path)
        _push_event(episode_id, {"type": "thumbnail_updated"})
        return JSONResponse(
            {
                "ok": True,
                "thumbnail_url": f"/static/{episode_id}/thumbnail.png?ts={int(os.path.getmtime(output_path))}",
            }
        )
    except Exception as exc:
        return JSONResponse({"error": f"thumbnail upload failed: {exc}"}, status_code=500)


@app.post("/api/upload/{episode_id}")
async def api_upload(episode_id: str, request_data: dict = None):
    """Upload the generated episode to YouTube.

    Optional body:
      { "privacy_status": "public"|"unlisted"|"private",
        "publish_at": "2025-06-01T12:00:00.000Z" }
    """
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    podcast = ep.get("podcast")
    if not podcast:
        from classes.Podcast import Podcast  # noqa: PLC0415
        podcast = Podcast(
            topic=ep.get("topic", ""),
            language=ep.get("language", "English"),
            tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
            creative_direction=ep.get("creative_direction", ""),
        )
        podcast.episode_dir = ep.get("episode_dir", "")
        podcast.metadata = ep.get("metadata") or {}
        ep["podcast"] = podcast

    body = request_data or {}
    privacy_status = body.get("privacy_status", "public")
    publish_at = body.get("publish_at") or None

    try:
        video_url = await asyncio.to_thread(podcast.upload, privacy_status, publish_at)
        return JSONResponse({"video_url": video_url, "scheduled": bool(publish_at), "publish_at": publish_at})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/mark-uploaded/{episode_id}")
async def api_mark_uploaded(episode_id: str):
    """Mark an episode as manually uploaded to YouTube.

    Updates episode state and persists uploaded_at to metadata.json.
    """
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    uploaded_at = datetime.now().isoformat()

    # Update in-memory state
    ep["status"] = "uploaded"
    if ep.get("metadata") is None:
        ep["metadata"] = {}
    ep["metadata"]["uploaded_at"] = uploaded_at
    _persist_episode_state(episode_id)

    # Persist to metadata.json
    episode_dir = ep.get("episode_dir", "")
    if episode_dir:
        metadata_path = os.path.join(episode_dir, "metadata.json")
        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {}
            meta["uploaded_at"] = uploaded_at
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            return JSONResponse({"error": f"failed to persist: {exc}"}, status_code=500)

    return JSONResponse({"ok": True, "uploaded_at": uploaded_at})


# ---------------------------------------------------------------------------
# Podcast V2 routes  (/api/v2/*)
# ---------------------------------------------------------------------------


def _build_podcast_v2_instance(ep: dict):
    from classes.PodcastV2 import PodcastV2  # noqa: PLC0415

    podcast = PodcastV2(
        topic=ep.get("topic", ""),
        language=ep.get("language", "English"),
        tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
        creative_direction=ep.get("creative_direction", ""),
        visual_style=ep.get("visual_style", ""),
        script_mode=ep.get("script_mode", False),
        raw_script=ep.get("raw_script", ""),
    )
    podcast.episode_dir = ep.get("episode_dir", "")
    podcast.metadata = ep.get("metadata") or {}
    ep["podcast"] = podcast
    return podcast


def _run_v2_pipeline(episode_id: str, start_step: int = 0):
    """Background thread — runs the full PodcastV2 pipeline."""
    ep = episodes[episode_id]
    ep["status"] = "running"
    ep["cancelled"] = False
    ep["error"] = None
    step_mode = ep.get("mode") == "step"
    start_step = max(0, min(start_step, len(_STEPS) - 1))

    original_stdout = sys.stdout
    sys.stdout = _StdoutCapture(episode_id, original_stdout)

    try:
        podcast = _build_podcast_v2_instance(ep)
        _persist_episode_state(episode_id)

        if start_step <= 0:
            if ep.get("script_mode"):
                if not podcast.episode_dir:
                    from config import ROOT_DIR  # noqa: PLC0415
                    episode_dir = os.path.join(ROOT_DIR, ".mp", episode_id)
                    os.makedirs(episode_dir, exist_ok=True)
                    podcast.episode_dir = episode_dir
                    ep["episode_dir"] = episode_dir
                    _persist_episode_state(episode_id)
                result = _run_step(episode_id, 0, lambda: podcast.generate_script_from_text(ep["raw_script"]))
            else:
                result = _run_step(episode_id, 0, lambda: podcast.generate_script(ep["topic"]))
            if result is None:
                return
            scenes = result
            ep["scenes"] = [s.get("narration", "") for s in (scenes or [])]
            ep["episode_dir"] = podcast.episode_dir
            ep["beat_qc"] = _load_json_if_exists(os.path.join(ep["episode_dir"], "beat_qc.json"), {})
            ep["script_qc"] = _load_json_if_exists(os.path.join(ep["episode_dir"], "script_qc.json"), {})

            _episode_metadata_path = os.path.join(ep["episode_dir"], "metadata.json")
            try:
                _lang_meta = {}
                if os.path.exists(_episode_metadata_path):
                    with open(_episode_metadata_path, "r", encoding="utf-8") as _f:
                        _lang_meta = json.load(_f)
                _lang_meta["language"] = ep.get("language", "English")
                _lang_meta["tts_source"] = ep.get("tts_source", _default_tts_source(ep.get("language", "English")))
                _lang_meta["creative_direction"] = ep.get("creative_direction", "")
                _lang_meta["visual_style"] = ep.get("visual_style", "")
                with open(_episode_metadata_path, "w", encoding="utf-8") as _f:
                    json.dump(_lang_meta, _f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            _persist_episode_state(episode_id)

        if step_mode and start_step <= 0:
            _push_event(episode_id, {"type": "waiting_approval", "step": 0, "next_step": 1, "next_name": _STEPS[1]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 1:
            if start_step == 1:
                _push_event(episode_id, {"type": "resume", "step": 1, "message": f"Resuming from {_STEPS[1]}."})
            result = _run_step(episode_id, 1, podcast.generate_assets)
            if result is None and ep["status"] == "error":
                return

        if step_mode and start_step <= 1:
            _push_event(episode_id, {"type": "waiting_approval", "step": 1, "next_step": 2, "next_name": _STEPS[2]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        def _gen_metadata_v2():
            meta = podcast.generate_metadata()
            ep["metadata"] = meta
            _persist_episode_state(episode_id)
            return meta

        if start_step <= 2:
            if start_step == 2:
                _push_event(episode_id, {"type": "resume", "step": 2, "message": f"Resuming from {_STEPS[2]}."})
            result = _run_step(episode_id, 2, _gen_metadata_v2)
            if result is None and ep["status"] == "error":
                return

        if step_mode and start_step <= 2:
            _push_event(episode_id, {"type": "waiting_approval", "step": 2, "next_step": 3, "next_name": _STEPS[3]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 3:
            if start_step == 3:
                _push_event(episode_id, {"type": "resume", "step": 3, "message": f"Resuming from {_STEPS[3]}."})
            result = _run_step(episode_id, 3, podcast.generate_thumbnail)
            if result is None and ep["status"] == "error":
                return
            if isinstance(result, str):
                ep["thumbnail_gen_prompt"] = result

        if step_mode and start_step <= 3:
            _push_event(episode_id, {"type": "waiting_approval", "step": 3, "next_step": 4, "next_name": _STEPS[4]})
            if not _wait_for_approval(episode_id):
                _push_event(episode_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                _persist_episode_state(episode_id)
                return

        if start_step <= 4:
            if start_step == 4:
                _push_event(episode_id, {"type": "resume", "step": 4, "message": f"Resuming from {_STEPS[4]}."})
            result = _run_step(episode_id, 4, podcast.render)
            if result is None and ep["status"] == "error":
                return

        ep["status"] = "done"
        _persist_episode_state(episode_id)
        _push_event(episode_id, {"type": "complete"})

    except Exception as exc:
        ep["status"] = "error"
        ep["error"] = str(exc)
        _persist_episode_state(episode_id)
        _push_event(episode_id, {"type": "error", "message": str(exc)})
    finally:
        sys.stdout = original_stdout


@app.post("/api/v2/generate")
async def api_v2_generate(request_data: dict):
    """Start the V2 podcast pipeline. Returns episode_id prefixed with podcast_v2_."""
    _apply_request_system_settings(request_data)
    script_mode = bool(request_data.get("script_mode", False))
    raw_script = (request_data.get("raw_script") or "").strip()
    topic = (request_data.get("topic") or "").strip()

    if script_mode:
        if not raw_script:
            return JSONResponse({"error": "raw_script is required in script mode"}, status_code=400)
        title = (request_data.get("title") or "Custom Script").strip()
    else:
        if not topic:
            return JSONResponse({"error": "topic is required"}, status_code=400)
        title = topic

    mode = request_data.get("mode", "auto")
    if mode not in ("auto", "step"):
        mode = "auto"

    language = (request_data.get("language") or "English").strip()
    if language not in ("Thai", "English"):
        language = "English"
    tts_source = _normalize_tts_source(request_data.get("tts_source"), language)
    creative_direction = (request_data.get("creative_direction") or "").strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    episode_id = f"podcast_v2_{timestamp}"

    episodes[episode_id] = {
        "episode_id": episode_id,
        "podcast": None,
        "topic": raw_script[:150].strip() if script_mode else title,
        "creative_direction": creative_direction,
        "visual_style": (request_data.get("visual_style") or "").strip(),
        "language": language,
        "tts_source": tts_source,
        "mode": mode,
        "script_mode": script_mode,
        "raw_script": raw_script,
        "status": "idle",
        "current_step": 0,
        "step_states": _make_step_states(),
        "scenes": [],
        "beat_qc": {},
        "script_qc": {},
        "metadata": {},
        "error": None,
        "episode_dir": "",
        "cancelled": False,
        "logs": [],
    }
    episode_events[episode_id] = []
    episode_approvals[episode_id] = threading.Event()

    t = threading.Thread(target=_run_v2_pipeline, args=(episode_id,), daemon=True)
    t.start()

    return JSONResponse({"episode_id": episode_id})


@app.get("/api/v2/stream/{episode_id}")
async def api_v2_stream(episode_id: str):
    """SSE stream for a V2 episode — delegates to shared episode_events."""
    return await api_stream(episode_id)


@app.get("/api/v2/episode/{episode_id}")
async def api_v2_episode(episode_id: str):
    """Full V2 episode state — delegates to the shared episode state handler."""
    return await api_episode(episode_id)


@app.post("/api/v2/upload/{episode_id}")
async def api_v2_upload(episode_id: str, request_data: dict = None):
    """Upload a V2 episode to YouTube — uses PodcastV2 instance."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    podcast = ep.get("podcast")
    if not podcast:
        from classes.PodcastV2 import PodcastV2  # noqa: PLC0415
        podcast = PodcastV2(
            topic=ep.get("topic", ""),
            language=ep.get("language", "English"),
            tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
            creative_direction=ep.get("creative_direction", ""),
        )
        podcast.episode_dir = ep.get("episode_dir", "")
        podcast.metadata = ep.get("metadata") or {}
        ep["podcast"] = podcast

    body = request_data or {}
    privacy_status = body.get("privacy_status", "public")
    publish_at = body.get("publish_at") or None

    try:
        video_url = await asyncio.to_thread(podcast.upload, privacy_status, publish_at)
        return JSONResponse({"video_url": video_url, "scheduled": bool(publish_at), "publish_at": publish_at})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/static/{episode_id}/{filename}")
async def serve_static(episode_id: str, filename: str):
    """Serve a file from the episode directory."""
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    episode_dir = ep.get("episode_dir", "")
    if not episode_dir:
        return JSONResponse({"error": "episode_dir not set yet"}, status_code=404)

    # Security: only allow basename, no path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(episode_dir, safe_filename)

    if not os.path.exists(file_path):
        return JSONResponse({"error": "file not found"}, status_code=404)

    # Determine media type
    if safe_filename.endswith(".png"):
        media_type = "image/png"
    elif safe_filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif safe_filename.endswith(".wav"):
        media_type = "audio/wav"
    elif safe_filename.endswith(".json"):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"

    return FileResponse(file_path, media_type=media_type)


# ---------------------------------------------------------------------------
# Shorts helpers
# ---------------------------------------------------------------------------


def _shorts_root_dir() -> str:
    from config import ROOT_DIR  # noqa: PLC0415
    return os.path.join(ROOT_DIR, ".mp")


def _make_shorts_step_states() -> list:
    return [{"name": name, "status": "pending", "message": ""} for name in _SHORTS_STEPS]


def _shorts_state_path(run_dir: str) -> str:
    return os.path.join(run_dir, "state.json") if run_dir else ""


def _shorts_preview(text: str, limit: int = 140) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _shorts_word_count(text: str) -> int:
    return len([part for part in str(text or "").split() if part])


def _shorts_has_thai(text: str) -> bool:
    return any("\u0E00" <= ch <= "\u0E7F" for ch in str(text or ""))


def _shorts_review_payload(ep: dict) -> dict:
    youtube = ep.get("youtube")
    metadata = ep.get("metadata") or {}
    discovery = ep.get("discovery") or {}
    discovery_winner = discovery.get("winner") or {}
    script = str(ep.get("script") or getattr(youtube, "script", "") or "").strip()
    base_script = str(ep.get("base_script") or "").strip()
    hook = str(ep.get("hook") or "").strip()
    image_prompts = list(ep.get("image_prompts") or getattr(youtube, "image_prompts", []) or [])
    images = list(ep.get("images") or getattr(youtube, "images", []) or [])
    tts_path = ep.get("tts_path") or getattr(youtube, "tts_path", None)
    srt_path = ep.get("srt_path") or getattr(youtube, "srt_path", None)
    video_path = ep.get("video_path") or getattr(youtube, "video_path", None)

    prompt_cards = []
    for index, prompt in enumerate(image_prompts):
        image_path = images[index] if index < len(images) else ""
        prompt_cards.append(
            {
                "index": index,
                "prompt": prompt,
                "prompt_preview": _shorts_preview(prompt, 180),
                "image_filename": os.path.basename(image_path) if image_path else None,
                "image_exists": bool(image_path and os.path.exists(image_path)),
            }
        )

    notes = []
    if script and _shorts_word_count(script) < 40:
        notes.append("Script looks very short for a short-form episode.")
    if script and _shorts_word_count(script) > 260:
        notes.append("Script looks long for a short-form episode.")
    if not hook:
        notes.append("Hook has not been captured yet.")
    if not image_prompts:
        notes.append("No image prompts captured yet.")
    if image_prompts and images and len(images) < len(image_prompts):
        notes.append("Some image prompts may not have produced images yet.")
    if ep.get("language") == "Thai":
        if metadata.get("title") and not _shorts_has_thai(str(metadata.get("title"))):
            notes.append("Title appears non-Thai while the episode language is Thai.")
        if metadata.get("description") and not _shorts_has_thai(str(metadata.get("description"))):
            notes.append("Description appears non-Thai while the episode language is Thai.")
    if ep.get("topic") and script and str(ep.get("topic", "")).lower() not in script.lower():
        notes.append("Script does not visibly repeat the topic string; double-check topic anchoring.")

    review = {
        "topic": ep.get("topic", ""),
        "discovery_topic": discovery_winner.get("topic", ""),
        "discovery_angle": discovery_winner.get("angle", ""),
        "language": ep.get("language", "English"),
        "niche": ep.get("niche", ""),
        "mode": ep.get("mode", "auto"),
        "status": ep.get("status", "idle"),
        "current_step": ep.get("current_step", 0),
        "script_word_count": _shorts_word_count(script),
        "script_char_count": len(script),
        "base_script_word_count": _shorts_word_count(base_script),
        "hook_word_count": _shorts_word_count(hook),
        "image_prompt_count": len(image_prompts),
        "image_count": len(images),
        "title": metadata.get("title", ""),
        "description_preview": _shorts_preview(metadata.get("description", ""), 260),
        "tags": metadata.get("tags", []) if isinstance(metadata.get("tags"), list) else [],
        "prompt_cards": prompt_cards,
        "quality_notes": notes,
        "ready_for_upload": bool(
            ep.get("status") == "done"
            and script
            and metadata.get("title")
            and image_prompts
            and images
            and video_path
        ),
        "tts_path": tts_path,
        "srt_path": srt_path,
        "video_path": video_path,
    }
    ep["review"] = review
    ep["quality_notes"] = notes
    ep["script"] = script
    ep["base_script"] = base_script
    ep["hook"] = hook
    ep["image_prompts"] = image_prompts
    ep["images"] = images
    ep["tts_path"] = tts_path
    ep["srt_path"] = srt_path
    ep["video_path"] = video_path
    return review


def _persist_shorts_state(short_id: str) -> None:
    ep = _get_or_restore_short(short_id)
    if not ep:
        return

    run_dir = ep.get("run_dir", "")
    if not run_dir:
        return

    os.makedirs(run_dir, exist_ok=True)
    payload = {
        "short_id": short_id,
        "topic": ep.get("topic", ""),
        "discovery": ep.get("discovery") or {},
        "niche": ep.get("niche", ""),
        "language": ep.get("language", "English"),
        "mode": ep.get("mode", "auto"),
        "status": ep.get("status", "idle"),
        "current_step": ep.get("current_step", 0),
        "step_states": ep.get("step_states") or _make_shorts_step_states(),
        "metadata": ep.get("metadata") or {},
        "script": ep.get("script", ""),
        "base_script": ep.get("base_script", ""),
        "hook": ep.get("hook", ""),
        "image_prompts": ep.get("image_prompts") or [],
        "images": [os.path.basename(p) for p in (ep.get("images") or [])],
        "quality_notes": ep.get("quality_notes") or [],
        "review": ep.get("review") or {},
        "error": ep.get("error"),
        "cancelled": bool(ep.get("cancelled", False)),
        "tts_path": ep.get("tts_path"),
        "srt_path": ep.get("srt_path"),
        "video_path": ep.get("video_path"),
        "updated_at": datetime.now().isoformat(),
    }

    with open(_shorts_state_path(run_dir), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _restore_short_from_disk(short_id: str) -> dict | None:
    root_dir = _shorts_root_dir()
    if short_id.startswith("short_"):
        dir_name = short_id[len("short_"):]
    else:
        dir_name = short_id
    run_dir = os.path.join(root_dir, dir_name)
    if not os.path.isdir(run_dir):
        return None

    state = _load_json_if_exists(_shorts_state_path(run_dir), {})
    if not state:
        return None

    ep = {
        "short_id": short_id,
        "youtube": None,
        "account": {},
        "niche": state.get("niche", ""),
        "topic": state.get("topic", ""),
        "discovery": state.get("discovery") or {},
        "language": state.get("language", "English"),
        "mode": state.get("mode", "auto"),
        "status": state.get("status", "idle"),
        "current_step": state.get("current_step", 0),
        "step_states": state.get("step_states") if isinstance(state.get("step_states"), list) else _make_shorts_step_states(),
        "metadata": state.get("metadata") or {},
        "script": state.get("script", ""),
        "base_script": state.get("base_script", ""),
        "hook": state.get("hook", ""),
        "image_prompts": state.get("image_prompts") or [],
        "images": state.get("images") or [],
        "quality_notes": state.get("quality_notes") or [],
        "review": state.get("review") or {},
        "error": state.get("error"),
        "run_dir": run_dir,
        "video_path": state.get("video_path"),
        "tts_path": state.get("tts_path"),
        "srt_path": state.get("srt_path"),
        "cancelled": bool(state.get("cancelled", False)),
        "logs": [],
    }
    shorts[short_id] = ep
    short_events.setdefault(short_id, [])
    short_approvals.setdefault(short_id, threading.Event())
    return ep


def _get_or_restore_short(short_id: str) -> dict | None:
    return shorts.get(short_id) or _restore_short_from_disk(short_id)


class _ShortsStdoutCapture:
    """Captures stdout and mirrors writes to original stdout and SSE event queue for Shorts."""

    def __init__(self, short_id: str, original_stdout):
        self.short_id = short_id
        self.original = original_stdout

    def write(self, text: str):
        self.original.write(text)
        text = text.strip()
        if text:
            short_events.setdefault(self.short_id, []).append(
                {
                    "type": "log",
                    "step": shorts[self.short_id]["current_step"],
                    "message": text,
                }
            )

    def flush(self):
        self.original.flush()


def _push_shorts_event(short_id: str, event: dict):
    """Append an SSE event to the short's event queue."""
    short_events.setdefault(short_id, []).append(event)


def _wait_for_shorts_approval(short_id: str) -> bool:
    """Block until user approves or cancels. Returns True to continue, False to cancel."""
    ep = shorts[short_id]
    ep["status"] = "waiting_approval"
    _persist_shorts_state(short_id)
    evt = short_approvals.get(short_id)
    if evt:
        evt.wait()
        evt.clear()
    ep["status"] = "running"
    _persist_shorts_state(short_id)
    return not ep.get("cancelled", False)


def _run_shorts_step(short_id: str, step_index: int, fn) -> bool:
    """Run a single Shorts pipeline step. Returns False if error or cancelled."""
    ep = shorts[short_id]
    ep["current_step"] = step_index
    ep["step_states"][step_index]["status"] = "running"
    ep["step_states"][step_index]["message"] = ""
    _persist_shorts_state(short_id)
    _push_shorts_event(short_id, {"type": "step_start", "step": step_index, "name": _SHORTS_STEPS[step_index]})
    try:
        result = fn()
        ep["step_states"][step_index]["status"] = "done"
        _persist_shorts_state(short_id)
        _push_shorts_event(short_id, {"type": "step_done", "step": step_index})
        return result
    except Exception as exc:
        ep["step_states"][step_index]["status"] = "error"
        ep["step_states"][step_index]["message"] = str(exc)
        _push_shorts_event(short_id, {"type": "step_error", "step": step_index, "error": str(exc)})
        ep["status"] = "error"
        ep["error"] = str(exc)
        _persist_shorts_state(short_id)
        return None  # sentinel for error


def _run_shorts_pipeline(short_id: str):
    """Background thread — runs the full YouTube Shorts pipeline."""
    ep = shorts[short_id]
    ep["status"] = "running"
    step_mode = ep.get("mode") == "step"

    original_stdout = sys.stdout
    sys.stdout = _ShortsStdoutCapture(short_id, original_stdout)

    try:
        # Pillow ANTIALIAS shim — must be before any image work
        from PIL import Image as _PILShim  # noqa: PLC0415
        if not hasattr(_PILShim, "ANTIALIAS"):
            _PILShim.ANTIALIAS = _PILShim.LANCZOS

        # Mock selenium (not needed for API-based pipeline)
        from unittest.mock import MagicMock  # noqa: PLC0415
        sys.modules.setdefault("selenium_firefox", MagicMock())

        from classes.YouTube import YouTube  # noqa: PLC0415
        from classes.Tts import TTS  # noqa: PLC0415
        from topic_discovery import run_discovery  # noqa: PLC0415

        account = ep["account"]
        youtube = YouTube(
            account_uuid=account["id"],
            account_nickname=account["nickname"],
            niche=ep["niche"],
            language=ep["language"],
            run_dir=ep["run_dir"],
        )
        ep["youtube"] = youtube

        # Step 0: Generate Topic (skip if user provided one)
        if ep.get("topic"):
            youtube.subject = ep["topic"]
            ep["step_states"][0]["status"] = "done"
            ep["step_states"][0]["message"] = youtube.subject
            _push_shorts_event(short_id, {"type": "step_start", "step": 0, "name": _SHORTS_STEPS[0]})
            _push_shorts_event(short_id, {"type": "step_done", "step": 0})
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
        else:
            def _discover_topic():
                discovery_result = run_discovery(ep.get("language") or "English")
                if not discovery_result or not isinstance(discovery_result, dict):
                    raise RuntimeError("Topic discovery failed")

                winner = discovery_result.get("winner") or {}
                topic = str(winner.get("topic") or "").strip()
                angle = str(winner.get("angle") or "").strip()
                if not topic:
                    raise RuntimeError("Topic discovery returned no winning topic")

                youtube.subject = topic
                ep["topic"] = topic
                ep["discovery"] = discovery_result
                ep["step_states"][0]["message"] = f"{topic} — {angle}" if angle else topic
                _shorts_review_payload(ep)
                _persist_shorts_state(short_id)
                return topic

            result = _run_shorts_step(short_id, 0, _discover_topic)
            if result is None and ep["status"] == "error":
                return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 0, "next_step": 1, "next_name": _SHORTS_STEPS[1]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 1: Generate Script
        result = _run_shorts_step(short_id, 1, youtube.generate_script)
        if result is None and ep["status"] == "error":
            return
        ep["base_script"] = result or ""
        ep["script"] = result or ""
        ep["step_states"][1]["message"] = f"{_shorts_word_count(result or '')} words"
        _shorts_review_payload(ep)
        _persist_shorts_state(short_id)

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 1, "next_step": 2, "next_name": _SHORTS_STEPS[2]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 2: Generate Hook — prepend to script
        def _gen_hook():
            hook = youtube.generate_hook()
            if hook and hook[-1] not in ".?!":
                hook += "."
            youtube.script = hook + " " + youtube.script
            ep["hook"] = hook
            ep["script"] = youtube.script
            ep["step_states"][2]["message"] = hook
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
            return hook

        result = _run_shorts_step(short_id, 2, _gen_hook)
        if result is None and ep["status"] == "error":
            return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 2, "next_step": 3, "next_name": _SHORTS_STEPS[3]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 3: Generate Metadata
        def _gen_shorts_metadata():
            meta = youtube.generate_metadata()
            ep["metadata"] = meta
            ep["step_states"][3]["message"] = (meta or {}).get("title", "")
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
            return meta

        result = _run_shorts_step(short_id, 3, _gen_shorts_metadata)
        if result is None and ep["status"] == "error":
            return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 3, "next_step": 4, "next_name": _SHORTS_STEPS[4]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 4: Generate Image Prompts
        result = _run_shorts_step(short_id, 4, youtube.generate_prompts)
        if result is None and ep["status"] == "error":
            return
        ep["image_prompts"] = list(result or [])
        ep["step_states"][4]["message"] = f"{len(ep['image_prompts'])} prompts"
        _shorts_review_payload(ep)
        _persist_shorts_state(short_id)

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 4, "next_step": 5, "next_name": _SHORTS_STEPS[5]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 5: Generate Images — iterate with per-image progress events
        ep["current_step"] = 5
        ep["step_states"][5]["status"] = "running"
        _push_shorts_event(short_id, {"type": "step_start", "step": 5, "name": _SHORTS_STEPS[5]})
        try:
            import json as _json  # noqa: PLC0415
            import uuid as _uuid  # noqa: PLC0415

            image_prompts = youtube.image_prompts or []

            # Flatten any nested JSON array strings
            flat_prompts = []
            for p in image_prompts:
                p_stripped = str(p).strip()
                if p_stripped.startswith("["):
                    try:
                        inner = _json.loads(p_stripped)
                        if isinstance(inner, list):
                            flat_prompts.extend(str(x) for x in inner)
                            continue
                    except Exception:
                        pass
                flat_prompts.append(p_stripped)

            total = len(flat_prompts)
            for i, prompt in enumerate(flat_prompts, 1):
                if ep.get("cancelled"):
                    break
                _push_shorts_event(short_id, {"type": "log", "step": 5, "message": f"Image {i}/{total}: {str(prompt)[:60]}..."})
                youtube.generate_image(prompt)

            # Fallback placeholder if no images generated
            if not youtube.images:
                from PIL import Image as _PILI  # noqa: PLC0415
                placeholder = os.path.join(ep["run_dir"], str(_uuid.uuid4()) + ".png")
                _PILI.new("RGB", (1080, 1920), color=(30, 30, 50)).save(placeholder)
                youtube.images.append(placeholder)
                _push_shorts_event(short_id, {"type": "log", "step": 5, "message": "No images generated — created placeholder."})

            ep["images"] = list(youtube.images or [])
            ep["step_states"][5]["message"] = f"{len(ep['images'])} images"
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
            ep["step_states"][5]["status"] = "done"
            _push_shorts_event(short_id, {"type": "step_done", "step": 5})
        except Exception as exc:
            ep["step_states"][5]["status"] = "error"
            ep["step_states"][5]["message"] = str(exc)
            _push_shorts_event(short_id, {"type": "step_error", "step": 5, "error": str(exc)})
            ep["status"] = "error"
            ep["error"] = str(exc)
            return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 5, "next_step": 6, "next_name": _SHORTS_STEPS[6]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 6: Text-to-Speech
        import uuid as _uuid2  # noqa: PLC0415

        def _gen_tts():
            tts = TTS()
            tts_path = os.path.join(ep["run_dir"], str(_uuid2.uuid4()) + ".wav")
            tts.synthesize(youtube.script, output_file=tts_path)
            youtube.tts_path = tts_path
            ep["tts_path"] = tts_path
            ep["step_states"][6]["message"] = os.path.basename(tts_path)
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
            return tts_path

        result = _run_shorts_step(short_id, 6, _gen_tts)
        if result is None and ep["status"] == "error":
            return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 6, "next_step": 7, "next_name": _SHORTS_STEPS[7]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 7: Generate Subtitles
        def _gen_subtitles():
            try:
                srt_path = youtube.generate_subtitles(youtube.tts_path)
                youtube.srt_path = srt_path
                ep["srt_path"] = srt_path
                ep["step_states"][7]["message"] = os.path.basename(srt_path)
                _shorts_review_payload(ep)
                _persist_shorts_state(short_id)
                return srt_path
            except Exception as e:
                _push_shorts_event(short_id, {"type": "log", "step": 7, "message": f"Warning: subtitles skipped — {e}"})
                youtube.srt_path = None
                ep["srt_path"] = None
                _shorts_review_payload(ep)
                _persist_shorts_state(short_id)
                return None

        result = _run_shorts_step(short_id, 7, _gen_subtitles)
        if ep["status"] == "error":
            return

        if step_mode:
            _push_shorts_event(short_id, {"type": "waiting_approval", "step": 7, "next_step": 8, "next_name": _SHORTS_STEPS[8]})
            if not _wait_for_shorts_approval(short_id):
                _push_shorts_event(short_id, {"type": "cancelled"})
                ep["status"] = "cancelled"
                return

        # Step 8: Render Video (Remotion)
        def _combine():
            video_path = youtube.combine_remotion()
            youtube.video_path = os.path.abspath(video_path)
            ep["video_path"] = youtube.video_path
            ep["step_states"][8]["message"] = os.path.basename(video_path)
            _shorts_review_payload(ep)
            _persist_shorts_state(short_id)
            return video_path

        result = _run_shorts_step(short_id, 8, _combine)
        if result is None and ep["status"] == "error":
            return

        ep["status"] = "done"
        _shorts_review_payload(ep)
        _persist_shorts_state(short_id)
        _push_shorts_event(short_id, {"type": "complete"})

    except Exception as exc:
        ep["status"] = "error"
        ep["error"] = str(exc)
        _push_shorts_event(short_id, {"type": "error", "message": str(exc)})
    finally:
        sys.stdout = original_stdout


# ---------------------------------------------------------------------------
# Shorts routes
# ---------------------------------------------------------------------------


@app.get("/shorts/api/accounts")
async def shorts_api_accounts():
    """Return YouTube accounts from cache (safe fields only — no firefox_profile)."""
    from cache import get_accounts  # noqa: PLC0415
    accounts = get_accounts("youtube")
    safe = [
        {
            "id": a.get("id", ""),
            "nickname": a.get("nickname", ""),
            "niche": a.get("niche", ""),
            "language": a.get("language", ""),
        }
        for a in accounts
    ]
    return JSONResponse({"accounts": safe, "youtube_auth": _get_youtube_auth_status()})


@app.get("/shorts/api/youtube-auth-status")
async def shorts_api_youtube_auth_status():
    return JSONResponse(_get_youtube_auth_status())


@app.post("/shorts/api/generate")
async def shorts_api_generate(request_data: dict):
    """Start the YouTube Shorts pipeline. Returns short_id."""
    account_id = (request_data.get("account_id") or "").strip()
    if not account_id:
        return JSONResponse({"error": "account_id is required"}, status_code=400)

    # Look up account from cache
    from cache import get_accounts  # noqa: PLC0415
    accounts = get_accounts("youtube")
    account = next((a for a in accounts if a.get("id") == account_id), None)
    if not account:
        return JSONResponse({"error": f"account_id '{account_id}' not found in cache"}, status_code=404)

    topic = (request_data.get("topic") or "").strip()
    niche = (request_data.get("niche") or account.get("niche") or "").strip()
    language = (request_data.get("language") or account.get("language") or "English").strip()
    mode = request_data.get("mode", "auto")
    if mode not in ("auto", "step"):
        mode = "auto"

    # Build short_id and run_dir (timestamped)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = f"short_{timestamp}"

    from config import ROOT_DIR  # noqa: PLC0415
    run_dir = os.path.join(ROOT_DIR, ".mp", short_id)
    os.makedirs(run_dir, exist_ok=True)

    # Initialize short state
    shorts[short_id] = {
        "youtube": None,
        "account": {
            "id": account.get("id", ""),
            "nickname": account.get("nickname", ""),
            "niche": account.get("niche", ""),
            "language": account.get("language", ""),
        },
        "niche": niche,
        "topic": topic,
        "discovery": {},
        "language": language,
        "mode": mode,
        "status": "idle",
        "current_step": 0,
        "step_states": _make_shorts_step_states(),
        "metadata": {},
        "script": "",
        "base_script": "",
        "hook": "",
        "image_prompts": [],
        "images": [],
        "tts_path": None,
        "srt_path": None,
        "quality_notes": [],
        "review": {},
        "error": None,
        "run_dir": run_dir,
        "video_path": None,
        "cancelled": False,
        "logs": [],
    }
    short_events[short_id] = []
    short_approvals[short_id] = threading.Event()
    _persist_shorts_state(short_id)

    # Start pipeline in background thread
    t = threading.Thread(target=_run_shorts_pipeline, args=(short_id,), daemon=True)
    t.start()

    return JSONResponse({"short_id": short_id})


@app.get("/shorts/api/stream/{short_id}")
async def shorts_api_stream(short_id: str):
    """SSE endpoint — streams step and log events for the given short."""
    if short_id not in shorts:
        return JSONResponse({"error": "unknown short_id"}, status_code=404)

    async def event_generator():
        cursor = 0
        keep_alive_counter = 0
        while True:
            ep = shorts.get(short_id)
            events = short_events.get(short_id, [])

            while cursor < len(events):
                evt = events[cursor]
                cursor += 1
                yield f"data: {json.dumps(evt)}\n\n"

            if ep and ep["status"] in ("done", "error", "cancelled") and cursor >= len(events):
                return

            keep_alive_counter += 1
            if keep_alive_counter >= 30:
                keep_alive_counter = 0
                yield ": keep-alive\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/shorts/api/episode/{short_id}")
async def shorts_api_episode(short_id: str):
    """Return full short state (status, steps, metadata, video_url, etc.)."""
    ep = _get_or_restore_short(short_id)
    if not ep:
        return JSONResponse({"error": "unknown short_id"}, status_code=404)

    review = _shorts_review_payload(ep)
    video_path = ep.get("video_path") or ""
    video_url = None
    if video_path and os.path.exists(video_path):
        filename = os.path.basename(video_path)
        video_url = f"/shorts/static/{short_id}/{filename}"

    return JSONResponse(
        {
            "short_id": short_id,
            "topic": ep.get("topic") or (ep.get("youtube") and getattr(ep["youtube"], "subject", "")) or "",
            "discovery": ep.get("discovery") or {},
            "niche": ep.get("niche", ""),
            "language": ep.get("language", ""),
            "account": ep.get("account", {}),
            "status": ep["status"],
            "current_step": ep["current_step"],
            "step_states": ep["step_states"],
            "metadata": ep["metadata"],
            "script": ep.get("script", ""),
            "base_script": ep.get("base_script", ""),
            "hook": ep.get("hook", ""),
            "image_prompts": ep.get("image_prompts") or [],
            "images": [os.path.basename(p) for p in (ep.get("images") or [])],
            "review": review,
            "quality_notes": ep.get("quality_notes") or [],
            "error": ep["error"],
            "run_dir": ep.get("run_dir", ""),
            "tts_path": ep.get("tts_path"),
            "srt_path": ep.get("srt_path"),
            "video_path": video_path,
            "video_url": video_url,
            "ready_for_upload": review.get("ready_for_upload", False),
        }
    )


@app.post("/shorts/api/approve/{short_id}")
async def shorts_api_approve(short_id: str):
    """Approve the current step and continue to next (step-by-step mode)."""
    ep = shorts.get(short_id)
    if not ep:
        return JSONResponse({"error": "unknown short_id"}, status_code=404)
    evt = short_approvals.get(short_id)
    if evt:
        evt.set()
    return JSONResponse({"ok": True})


@app.post("/shorts/api/cancel/{short_id}")
async def shorts_api_cancel(short_id: str):
    """Cancel the pipeline (works in both auto and step mode)."""
    ep = _get_or_restore_short(short_id)
    if not ep:
        return JSONResponse({"error": "unknown short_id"}, status_code=404)
    ep["cancelled"] = True
    ep["status"] = "cancelled"
    _persist_shorts_state(short_id)
    evt = short_approvals.get(short_id)
    if evt:
        evt.set()
    _push_shorts_event(short_id, {"type": "cancelled"})
    return JSONResponse({"ok": True})


@app.post("/shorts/api/upload/{short_id}")
async def shorts_api_upload(short_id: str, request_data: dict = None):
    """Upload the generated Short to YouTube via API."""
    ep = _get_or_restore_short(short_id)
    if not ep:
        return JSONResponse({"error": "unknown short_id"}, status_code=404)

    auth_status = _get_youtube_auth_status()
    if not auth_status.get("authenticated"):
        return JSONResponse(
            {
                "error": auth_status.get("message") or "YouTube auth unavailable",
                "manual_upload_recommended": True,
                "auth_status": auth_status,
            },
            status_code=400,
        )

    youtube = ep.get("youtube")
    if not youtube:
        return JSONResponse({"error": "pipeline not run yet for this short"}, status_code=400)

    if not ep.get("video_path") or not os.path.exists(ep["video_path"]):
        return JSONResponse({"error": "video file not found — run the pipeline first"}, status_code=400)

    try:
        result = await asyncio.to_thread(youtube.upload_video)
        if result:
            video_url = getattr(youtube, "uploaded_video_url", None)
            return JSONResponse({"success": True, "video_url": video_url})
        else:
            return JSONResponse({"success": False, "error": "upload_video() returned False"}, status_code=500)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/shorts/api/shorts")
async def shorts_api_list():
    """List recent shorts from .mp/ dirs (dirs containing .mp4 files, sorted by mtime desc)."""
    root_dir = _shorts_root_dir()
    if not os.path.isdir(root_dir):
        return JSONResponse({"shorts": []})

    results = []
    try:
        entries = [
            e for e in os.scandir(root_dir)
            if e.is_dir() and (e.name.startswith("short_") or (not e.name.startswith("podcast_") and len(e.name) == 15 and e.name[:8].isdigit()))
        ]
        for entry in sorted(entries, key=lambda e: e.stat().st_mtime, reverse=True)[:20]:
            mp4_files = glob.glob(os.path.join(entry.path, "*.mp4"))
            short_id = f"short_{entry.name}" if not entry.name.startswith("short_") else entry.name
            ep = shorts.get(short_id) or {}
            state = _load_json_if_exists(_shorts_state_path(entry.path), {})
            metadata = (ep.get("metadata") or state.get("metadata") or {})
            results.append(
                {
                    "short_id": short_id,
                    "dir_name": entry.name,
                    "title": metadata.get("title") or state.get("topic") or entry.name,
                    "status": ep.get("status") or state.get("status") or ("done" if mp4_files else "partial"),
                    "has_video": bool(mp4_files),
                    "video_filename": os.path.basename(mp4_files[0]) if mp4_files else None,
                    "hook_preview": _shorts_preview(state.get("hook") or ep.get("hook") or "", 80),
                    "updated_at_state": state.get("updated_at"),
                    "updated_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                }
            )
    except Exception:
        pass

    return JSONResponse({"shorts": results})


@app.get("/shorts/static/{short_id}/{filename}")
async def shorts_serve_static(short_id: str, filename: str):
    """Serve a file from the short's run_dir."""
    ep = shorts.get(short_id)

    run_dir = ""
    if ep:
        run_dir = ep.get("run_dir", "")
    else:
        root_dir = _shorts_root_dir()
        if short_id.startswith("short_"):
            dir_name = short_id[len("short_"):]
        else:
            dir_name = short_id
        candidate = os.path.join(root_dir, dir_name)
        if os.path.isdir(candidate):
            run_dir = candidate

    if not run_dir:
        return JSONResponse({"error": "short not found"}, status_code=404)

    # Security: only allow basename, no path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(run_dir, safe_filename)

    if not os.path.exists(file_path):
        return JSONResponse({"error": "file not found"}, status_code=404)

    if safe_filename.endswith(".png"):
        media_type = "image/png"
    elif safe_filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif safe_filename.endswith(".wav"):
        media_type = "audio/wav"
    elif safe_filename.endswith(".srt"):
        media_type = "text/plain"
    elif safe_filename.endswith(".json"):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"

    return FileResponse(file_path, media_type=media_type)


# ---------------------------------------------------------------------------
# Clip-Shorts routes
# ---------------------------------------------------------------------------


@app.get("/podcast/episodes")
async def podcast_list_episodes():
    """
    List completed podcast episode directories available for clip extraction.

    An episode qualifies if its directory (under .mp/) starts with "podcast_"
    and contains both script.json and final.mp4.

    Returns:
        JSON array of {episode_dir, topic, scene_count}.
    """
    from config import ROOT_DIR  # noqa: PLC0415

    mp_dir = os.path.join(ROOT_DIR, ".mp")
    if not os.path.isdir(mp_dir):
        return JSONResponse([])

    results = []
    for name in sorted(os.listdir(mp_dir), reverse=True):  # newest first
        ep_dir = os.path.join(mp_dir, name)
        if not name.startswith("podcast_") or not os.path.isdir(ep_dir):
            continue

        script_path = os.path.join(ep_dir, "script.json")
        final_path = os.path.join(ep_dir, "final.mp4")
        if not os.path.isfile(script_path) or not os.path.isfile(final_path):
            continue

        # Determine a human-readable topic and scene count
        topic = name
        scene_count = 0
        try:
            with open(script_path, "r", encoding="utf-8") as fh:
                scenes = json.load(fh)
            scene_count = len(scenes)
            # Prefer metadata.json title if available
            meta_path = os.path.join(ep_dir, "metadata.json")
            if os.path.isfile(meta_path):
                with open(meta_path, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                topic = meta.get("title") or meta.get("topic") or name
            elif scenes:
                # Fall back to first scene narration (truncated)
                first_narration = scenes[0].get("narration", name)
                topic = first_narration[:80] + ("…" if len(first_narration) > 80 else "")
        except Exception:  # noqa: BLE001
            pass

        results.append({
            "episode_dir": ep_dir,
            "topic": topic,
            "scene_count": scene_count,
        })

    return JSONResponse(results)


@app.post("/podcast/clip-shorts")
async def podcast_clip_shorts(request_data: dict):
    """
    Start the Podcast-to-Shorts pipeline for a completed episode.

    Scores scenes with an LLM, selects the top-N, renders each as a vertical
    9:16 Short via Remotion, and streams progress as SSE events.

    Request body:
        episode_dir (str): Path to the episode directory.
        top_n (int): Number of top scenes to clip (1–5, default 3).

    SSE event types:
        progress — {"type": "progress", "message": str}
        done     — {"type": "done", "shorts": [{scene_index, score, reason, output_path}]}
        error    — {"type": "error", "message": str}
    """
    import uuid as _uuid  # noqa: PLC0415

    episode_dir = (request_data.get("episode_dir") or "").strip()
    top_n = max(1, min(5, int(request_data.get("top_n", 3))))

    if not episode_dir or not os.path.isdir(episode_dir):
        return JSONResponse({"error": "episode_dir is missing or does not exist"}, status_code=400)
    if not os.path.isfile(os.path.join(episode_dir, "script.json")):
        return JSONResponse({"error": "episode_dir has no script.json"}, status_code=400)

    clip_id = str(_uuid.uuid4())
    clip_events[clip_id] = []

    def _push(evt: dict):
        clip_events[clip_id].append(evt)

    def _run():
        try:
            from podcast_shorts_scorer import score_scenes    # noqa: PLC0415
            from podcast_shorts_builder import build_short    # noqa: PLC0415

            _push({"type": "progress", "message": "Scoring scenes…"})
            top_scenes = score_scenes(episode_dir, top_n=top_n)

            shorts_built = []
            for i, scene in enumerate(top_scenes):
                scene_idx = scene["scene_index"]
                _push({
                    "type": "progress",
                    "message": f"Building short {i + 1}/{len(top_scenes)} (scene {scene_idx:02d}, score {scene['score']}/10)…",
                })
                output_path = os.path.join(episode_dir, f"short_scene_{scene_idx:02d}.mp4")
                build_short(episode_dir, scene_idx, output_path)
                shorts_built.append({
                    "scene_index": scene_idx,
                    "score": scene["score"],
                    "reason": scene.get("reason", ""),
                    "output_path": output_path,
                })

            _push({"type": "done", "shorts": shorts_built})

        except Exception as exc:  # noqa: BLE001
            _push({"type": "error", "message": str(exc)})

    threading.Thread(target=_run, daemon=True).start()

    async def _event_generator():
        cursor = 0
        keep_alive_counter = 0
        try:
            while True:
                events = clip_events.get(clip_id, [])
                while cursor < len(events):
                    evt = events[cursor]
                    cursor += 1
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt["type"] in ("done", "error"):
                        return
                keep_alive_counter += 1
                if keep_alive_counter >= 30:  # every ~9 s at 0.3 s sleep
                    keep_alive_counter = 0
                    yield ": keep-alive\n\n"
                await asyncio.sleep(0.3)
        finally:
            clip_events.pop(clip_id, None)  # free memory once stream closes

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def launch_podcast_server():
    """Start the FastAPI server and open browser automatically."""
    import webbrowser

    PORT = 8899
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
