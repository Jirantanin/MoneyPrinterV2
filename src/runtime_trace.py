import json
import os
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
import contextvars

from config import ROOT_DIR

_TRACE_LOCK = Lock()
_TRACE_DIR = os.path.join(ROOT_DIR, "logs")
_TRACE_FILE = os.path.join(_TRACE_DIR, "podcast_runtime_trace.jsonl")
_TRACE_RUN_ID = contextvars.ContextVar("trace_run_id", default="")
_DEFAULT_RATE_CARD = {
    "anthropic": {
        "input_per_mtok": 3.0,
        "output_per_mtok": 15.0,
        "cache_write_5m_per_mtok": 3.75,
        "cache_write_1h_per_mtok": 6.0,
        "cache_read_per_mtok": 0.30,
    },
    "gemini_image": {"per_request_usd": 0.039},
    "kling_image2video": {"per_request_usd": 0.0},
    "pexels_video": {"per_request_usd": 0.0},
    "edge_tts": {"per_char_usd": 0.0},
    "elevenlabs_tts": {"per_char_usd": 0.0},
    "gemini_tts": {"per_char_usd": 0.0},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_headers(headers: dict | None) -> dict:
    safe = dict(headers or {})
    for key in list(safe.keys()):
        if key.lower() in {"x-api-key", "authorization"}:
            safe[key] = "***REDACTED***"
    return safe


def append_trace(event_type: str, **payload) -> None:
    os.makedirs(_TRACE_DIR, exist_ok=True)
    row = {
        "id": str(uuid4()),
        "ts": _utc_now(),
        "event_type": event_type,
        "run_id": _TRACE_RUN_ID.get() or payload.pop("run_id", ""),
        **payload,
    }
    with _TRACE_LOCK:
        with open(_TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def trace_http_request(
    *,
    provider: str,
    url: str,
    method: str,
    headers: dict,
    request_json: dict,
    response_status: int | None = None,
    response_headers: dict | None = None,
    response_text: str | None = None,
    error: str | None = None,
    attempt: int = 1,
) -> None:
    append_trace(
        "http_call",
        provider=provider,
        method=method,
        url=url,
        attempt=attempt,
        request={
            "headers": _redact_headers(headers),
            "json": request_json,
        },
        response={
            "status": response_status,
            "headers": dict(response_headers or {}),
            "text": response_text,
        },
        error=error,
    )


def set_trace_run_id(run_id: str):
    return _TRACE_RUN_ID.set(run_id or "")


def reset_trace_run_id(token) -> None:
    _TRACE_RUN_ID.reset(token)


def summarize_run_cost(run_id: str) -> dict:
    if not run_id or not os.path.exists(_TRACE_FILE):
        return {
            "run_id": run_id,
            "calls": 0,
            "model": "",
            "usage": {},
            "cost_usd": 0.0,
            "pricing": {},
        }

    anthropic_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_ephemeral_5m_input_tokens": 0,
        "cache_creation_ephemeral_1h_input_tokens": 0,
    }
    provider_units: dict[str, dict] = {}
    calls = 0
    model = ""

    with open(_TRACE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("run_id") != run_id:
                continue
            if row.get("event_type") == "http_call" and row.get("provider") == "anthropic":
                response = row.get("response") or {}
                if (response.get("status") or 0) != 200:
                    continue
                text = response.get("text") or ""
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    continue
                calls += 1
                model = model or str(body.get("model") or "")
                u = body.get("usage") or {}
                anthropic_usage["input_tokens"] += int(u.get("input_tokens") or 0)
                anthropic_usage["output_tokens"] += int(u.get("output_tokens") or 0)
                anthropic_usage["cache_creation_input_tokens"] += int(u.get("cache_creation_input_tokens") or 0)
                anthropic_usage["cache_read_input_tokens"] += int(u.get("cache_read_input_tokens") or 0)
                cache_creation = u.get("cache_creation") or {}
                anthropic_usage["cache_creation_ephemeral_5m_input_tokens"] += int(cache_creation.get("ephemeral_5m_input_tokens") or 0)
                anthropic_usage["cache_creation_ephemeral_1h_input_tokens"] += int(cache_creation.get("ephemeral_1h_input_tokens") or 0)
                continue

            if row.get("event_type") == "api_usage":
                provider = str(row.get("provider") or "").strip()
                metric = str(row.get("metric") or "").strip()
                qty = float(row.get("quantity") or 0.0)
                if not provider or not metric or qty <= 0:
                    continue
                provider_units.setdefault(provider, {})
                provider_units[provider][metric] = float(provider_units[provider].get(metric, 0.0) + qty)

    cost = 0.0
    pricing = _DEFAULT_RATE_CARD
    ap = pricing["anthropic"]
    cost += (anthropic_usage["input_tokens"] / 1_000_000) * ap["input_per_mtok"]
    cost += (anthropic_usage["output_tokens"] / 1_000_000) * ap["output_per_mtok"]
    cost += (anthropic_usage["cache_creation_input_tokens"] / 1_000_000) * ap["cache_write_5m_per_mtok"]
    cost += (anthropic_usage["cache_read_input_tokens"] / 1_000_000) * ap["cache_read_per_mtok"]
    cost += (anthropic_usage["cache_creation_ephemeral_1h_input_tokens"] / 1_000_000) * ap["cache_write_1h_per_mtok"]
    if anthropic_usage["cache_creation_ephemeral_5m_input_tokens"] > 0:
        cost -= (anthropic_usage["cache_creation_input_tokens"] / 1_000_000) * ap["cache_write_5m_per_mtok"]
        cost += (anthropic_usage["cache_creation_ephemeral_5m_input_tokens"] / 1_000_000) * ap["cache_write_5m_per_mtok"]

    breakdown = {
        "anthropic": {
            "usage": anthropic_usage,
            "estimated_cost_usd": round(
                (anthropic_usage["input_tokens"] / 1_000_000) * ap["input_per_mtok"]
                + (anthropic_usage["output_tokens"] / 1_000_000) * ap["output_per_mtok"]
                + (anthropic_usage["cache_creation_input_tokens"] / 1_000_000) * ap["cache_write_5m_per_mtok"]
                + (anthropic_usage["cache_read_input_tokens"] / 1_000_000) * ap["cache_read_per_mtok"]
                + (anthropic_usage["cache_creation_ephemeral_1h_input_tokens"] / 1_000_000) * ap["cache_write_1h_per_mtok"],
                6,
            ),
        }
    }

    for provider, units in provider_units.items():
        rates = pricing.get(provider, {})
        provider_cost = 0.0
        if "requests" in units:
            provider_cost += units["requests"] * float(rates.get("per_request_usd", 0.0))
        if "chars" in units:
            provider_cost += units["chars"] * float(rates.get("per_char_usd", 0.0))
        if "seconds" in units:
            provider_cost += units["seconds"] * float(rates.get("per_second_usd", 0.0))
        cost += provider_cost
        breakdown[provider] = {
            "usage": units,
            "estimated_cost_usd": round(provider_cost, 6),
        }

    return {
        "run_id": run_id,
        "calls": calls,
        "model": model,
        "usage": anthropic_usage,
        "provider_breakdown": breakdown,
        "cost_usd": round(cost, 6),
        "pricing": pricing,
    }


def append_api_usage(provider: str, metric: str, quantity: float, **extra) -> None:
    append_trace(
        "api_usage",
        provider=provider,
        metric=metric,
        quantity=quantity,
        **extra,
    )
