"""Real provider fulfillment smoke runner for PodcastV2 Producer Mode.

The default run is no-spend/no-network. Live checks require explicit flags so a
developer can verify keys and tiny provider samples without accidentally
starting a full production episode.
"""

from __future__ import annotations

import base64
import json
import os
import re
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


PROVIDER_SMOKE_VERSION = 1
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"
GEMINI_TTS_TEXT_USD_PER_CHAR = 0.00000025
GEMINI_TTS_AUDIO_USD_PER_SECOND = 0.0005


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_config() -> dict[str, Any]:
    path = _root_dir() / "config.json"
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _nested(source: dict[str, Any], *keys: str) -> Any:
    cursor: Any = source
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _configured(value: Any) -> bool:
    return bool(str(value or "").strip())


def _redacted_config_status(cfg: dict[str, Any]) -> dict[str, Any]:
    gemini_key = (
        cfg.get("gemini_tts_api_key")
        or cfg.get("nanobanana2_api_key")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    return {
        "gemini_tts": _configured(gemini_key),
        "gemini_image_repo_fallback": _configured(
            cfg.get("nanobanana2_api_key") or os.environ.get("GEMINI_API_KEY", "")
        ),
        "pexels": _configured(cfg.get("pexels_api_key") or os.environ.get("PEXELS_API_KEY", "")),
        "pixabay": _configured(cfg.get("pixabay_api_key") or os.environ.get("PIXABAY_API_KEY", "")),
        "runware_flux1": _configured(cfg.get("runware_api_key") or os.environ.get("RUNWARE_API_KEY", "")),
        "llm_anthropic": _configured(cfg.get("anthropic_api_key")),
        "llm_minimax": _configured(cfg.get("minimax_api_key")),
        "openai_image_cli_fallback": _configured(os.environ.get("OPENAI_API_KEY", "")),
    }


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _secret_values(cfg: dict[str, Any]) -> list[str]:
    values = [
        cfg.get("gemini_tts_api_key"),
        cfg.get("nanobanana2_api_key"),
        cfg.get("pexels_api_key"),
        cfg.get("pixabay_api_key"),
        cfg.get("runware_api_key"),
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("PEXELS_API_KEY"),
        os.environ.get("PIXABAY_API_KEY"),
        os.environ.get("RUNWARE_API_KEY"),
    ]
    return [str(value) for value in values if str(value or "").strip()]


def _redact(value: Any, cfg: dict[str, Any]) -> str:
    text = str(value or "")
    for secret in _secret_values(cfg):
        text = text.replace(secret, "***REDACTED***")
    text = re.sub(r"([?&](?:key|api_key)=)[^&\\s)]+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"AIza[0-9A-Za-z_-]+", "***REDACTED***", text)
    return text


def _estimate_gemini_tts_cost(chars: int, duration_seconds: float) -> float:
    return round(chars * GEMINI_TTS_TEXT_USD_PER_CHAR + duration_seconds * GEMINI_TTS_AUDIO_USD_PER_SECOND, 6)


def _gemini_voice(cfg: dict[str, Any]) -> str:
    return str(
        _nested(cfg, "podcast_settings", "voices", "thai_gemini_voice")
        or cfg.get("thai_gemini_voice")
        or "Aoede"
    )


def _gemini_tts_sample(
    *,
    cfg: dict[str, Any],
    output_path: Path,
    text: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    api_key = (
        cfg.get("gemini_tts_api_key")
        or cfg.get("nanobanana2_api_key")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    if not _configured(api_key):
        return {
            "provider": "gemini_tts",
            "status": "blocked",
            "detail": "gemini_tts_api_key/nanobanana2_api_key/GEMINI_API_KEY is missing",
        }

    voice = _gemini_voice(cfg)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_TTS_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Audio Profile: A standard Thai documentary narrator with a clear, calm, neutral voice.\n\n"
                            "Director's Notes: Speak naturally and clearly. This is a short technical smoke test.\n\n"
                            f"Transcript:\n{text}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
        },
    }
    try:
        response = _session().post(url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
        audio_b64 = body["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        pcm_data = base64.b64decode(audio_b64)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)
        duration = len(pcm_data) / (2 * 24000)
        return {
            "provider": "gemini_tts",
            "status": "pass",
            "model": GEMINI_TTS_MODEL,
            "voice": voice,
            "output_path": str(output_path),
            "bytes": output_path.stat().st_size,
            "duration_seconds": round(duration, 3),
            "chars": len(text),
            "estimated_cost_usd": _estimate_gemini_tts_cost(len(text), duration),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "gemini_tts",
            "status": "blocked",
            "detail": _redact(exc, cfg),
        }


def _pexels_search(cfg: dict[str, Any], query: str, timeout_seconds: int) -> dict[str, Any]:
    api_key = str(cfg.get("pexels_api_key") or os.environ.get("PEXELS_API_KEY", "") or "")
    if not api_key:
        return {"provider": "pexels", "status": "blocked", "detail": "pexels_api_key is missing"}
    try:
        response = _session().get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        videos = data.get("videos") if isinstance(data.get("videos"), list) else []
        first = videos[0] if videos else {}
        return {
            "provider": "pexels",
            "status": "pass" if first else "review",
            "result_count": int(data.get("total_results") or len(videos) or 0),
            "sample": {
                "id": first.get("id"),
                "url": first.get("url"),
                "duration": first.get("duration"),
            } if isinstance(first, dict) else {},
        }
    except Exception as exc:  # noqa: BLE001
        return {"provider": "pexels", "status": "blocked", "detail": _redact(exc, cfg)}


def _pixabay_search(cfg: dict[str, Any], query: str, timeout_seconds: int) -> dict[str, Any]:
    api_key = str(cfg.get("pixabay_api_key") or os.environ.get("PIXABAY_API_KEY", "") or "")
    if not api_key:
        return {"provider": "pixabay", "status": "blocked", "detail": "pixabay_api_key is missing"}
    try:
        response = _session().get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query, "per_page": 3, "video_type": "film"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits") if isinstance(data.get("hits"), list) else []
        first = hits[0] if hits else {}
        return {
            "provider": "pixabay",
            "status": "pass" if first else "review",
            "result_count": int(data.get("totalHits") or len(hits) or 0),
            "sample": {
                "id": first.get("id"),
                "pageURL": first.get("pageURL"),
                "duration": first.get("duration"),
            } if isinstance(first, dict) else {},
        }
    except Exception as exc:  # noqa: BLE001
        return {"provider": "pixabay", "status": "blocked", "detail": _redact(exc, cfg)}


def _imagegen_task(topic: str, output_dir: Path) -> dict[str, Any]:
    prompt = (
        f"Thai documentary section opener for {topic}. Clean factual cinematic frame, "
        "no embedded text, no logo, no watermark, 16:9 composition."
    )
    task = {
        "provider": "codex_imagegen_skill",
        "status": "task_ready",
        "prompt": prompt,
        "expected_output": str(output_dir / "codex_imagegen_sample.png"),
        "note": (
            "Fulfill this with the Codex imagegen skill in-session. "
            "If the built-in image tool is unavailable, the fallback CLI requires OPENAI_API_KEY."
        ),
        "fallback_cli": {
            "status": "ready" if os.environ.get("OPENAI_API_KEY") else "blocked",
            "reason": "OPENAI_API_KEY present" if os.environ.get("OPENAI_API_KEY") else "OPENAI_API_KEY missing",
            "dry_run_supported": True,
        },
    }
    _write_json(output_dir / "codex_imagegen_sample_task.json", task)
    return task


def run_provider_smoke(
    *,
    episode_dir: str | Path,
    topic: str = "",
    allow_network: bool = False,
    allow_gemini_tts: bool = False,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    episode_path = Path(episode_dir)
    output_dir = episode_path / "provider_smoke"
    cfg = _load_config()
    topic = _clean_text(topic, "Mars rover")
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    config_status = _redacted_config_status(cfg)
    checks.append(
        {
            "provider": "config",
            "status": "pass",
            "configured": config_status,
            "detail": "Config keys inspected without exposing secrets.",
        }
    )
    checks.append(_imagegen_task(topic, output_dir))

    if allow_network:
        checks.append(_pexels_search(cfg, topic, timeout_seconds))
        checks.append(_pixabay_search(cfg, topic, timeout_seconds))
    else:
        warnings.append("Network stock-provider checks skipped; pass --allow-network to run them.")
        checks.append({"provider": "pexels", "status": "skipped", "detail": "network disabled"})
        checks.append({"provider": "pixabay", "status": "skipped", "detail": "network disabled"})

    if allow_gemini_tts:
        sample_text = "นี่คือเสียงทดสอบสั้น ๆ สำหรับระบบเล่าเรื่องสารคดีของพอดแคสต์"
        checks.append(
            _gemini_tts_sample(
                cfg=cfg,
                output_path=output_dir / "gemini_tts_sample.wav",
                text=sample_text,
                timeout_seconds=timeout_seconds,
            )
        )
    else:
        warnings.append("Gemini TTS live sample skipped; pass --allow-gemini-tts to run a tiny paid sample.")
        checks.append({"provider": "gemini_tts", "status": "skipped", "detail": "live sample disabled"})

    for check in checks:
        status = str(check.get("status") or "")
        if status == "blocked":
            errors.append(f"{check.get('provider')}: {check.get('detail', 'blocked')}")
        elif status in {"review", "skipped", "task_ready"}:
            warnings.append(f"{check.get('provider')}: {check.get('detail', status)}")

    blocking = any(str(check.get("status")) == "blocked" for check in checks)
    live_passes = sum(1 for check in checks if str(check.get("status")) == "pass")
    status = "blocked" if blocking else ("review" if warnings else "pass")
    manifest = {
        "schema_version": PROVIDER_SMOKE_VERSION,
        "stage": "provider_smoke",
        "created_at": _utc_now(),
        "status": status,
        "episode_dir": str(episode_path),
        "topic": topic,
        "allow_network": allow_network,
        "allow_gemini_tts": allow_gemini_tts,
        "live_pass_count": live_passes,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }
    _write_json(output_dir / "provider_smoke_manifest.json", manifest)
    return manifest
