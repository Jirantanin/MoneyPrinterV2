"""
llm_provider.py - Unified LLM text generation.

Provider priority (auto-detected at call time):
  1. Explicit model route if model_name points to Anthropic / MiniMax / Ollama
  2. MiniMax via OpenRouter - if minimax_api_key is set in config.json
  3. Ollama (local) - fallback using selected model or config ollama_model

This means Podcast (and any other module) automatically uses MiniMax when
an API key is configured, but can fall back to Ollama if the remote call
times out or fails.
"""

import json
import re
import time

import ollama
import requests

from config import (
    get_anthropic_api_key,
    get_anthropic_model,
    get_minimax_api_base_url,
    get_minimax_api_key,
    get_minimax_model,
    get_ollama_base_url,
    get_ollama_model,
)
from runtime_trace import append_trace, trace_http_request

_selected_model: str | None = None


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def _ollama_client() -> ollama.Client:
    return ollama.Client(host=get_ollama_base_url())


def list_models() -> list[str]:
    """Lists all models available on the local Ollama server."""
    response = _ollama_client().list()
    return sorted(m.model for m in response.models)


def select_model(model: str) -> None:
    """Sets the Ollama model to use when MiniMax is not configured."""
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    """Returns the currently selected Ollama model, or None."""
    return _selected_model


def _resolve_ollama_model(model_name: str | None = None) -> str | None:
    return model_name or _selected_model or get_ollama_model() or None


def _normalize_model_name(model_name: str | None) -> str:
    return (model_name or "").strip()


def _is_anthropic_model(model_name: str | None) -> bool:
    name = _normalize_model_name(model_name).lower()
    return name.startswith("claude") or name.startswith("anthropic/")


def _strip_provider_prefix(model_name: str | None) -> str | None:
    name = _normalize_model_name(model_name)
    if not name:
        return None
    if "/" in name:
        provider, remainder = name.split("/", 1)
        if provider.lower() in {"anthropic", "ollama", "minimax"} and remainder:
            return remainder
    return name


def _ollama_chat(
    messages: list[dict],
    model_name: str | None = None,
    schema: dict | None = None,
) -> str:
    model = _resolve_ollama_model(model_name)
    if not model:
        raise RuntimeError(
            "No Ollama model configured. Set ollama_model in config.json, "
            "or call select_model()."
        )

    kwargs = {
        "model": model,
        "messages": messages,
    }
    if schema is not None:
        kwargs["format"] = schema

    response = _ollama_client().chat(**kwargs)
    return response["message"]["content"].strip()


# ---------------------------------------------------------------------------
# MiniMax / OpenRouter helpers
# ---------------------------------------------------------------------------

def _minimax_available() -> bool:
    return bool(get_minimax_api_key())


def _anthropic_available() -> bool:
    return bool(get_anthropic_api_key())


def _anthropic_chat(
    messages: list[dict],
    model_name: str | None = None,
    schema: dict | None = None,
    max_tokens: int = 4096,
) -> str:
    api_key = get_anthropic_api_key()
    model = _strip_provider_prefix(model_name) or get_anthropic_model()
    if not api_key:
        raise RuntimeError("Anthropic API key is not configured.")
    if not model:
        raise RuntimeError("Anthropic model is not configured.")

    system_parts = []
    content_blocks = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        api_role = "assistant" if role == "assistant" else "user"
        content_blocks.append({"role": api_role, "content": content})

    payload = {
        "model": model,
        "max_tokens": int(max(256, max_tokens)),
        "messages": content_blocks or [{"role": "user", "content": ""}],
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)

    last_error: Exception | None = None
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(15, 300),
            )
            response.raise_for_status()
            trace_http_request(
                provider="anthropic",
                url=url,
                method="POST",
                headers=headers,
                request_json=payload,
                response_status=response.status_code,
                response_headers=dict(response.headers),
                response_text=response.text,
                attempt=attempt + 1,
            )
            data = response.json()
            parts = []
            for block in data.get("content", []):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "".join(parts).strip()
        except requests.RequestException as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            trace_http_request(
                provider="anthropic",
                url=url,
                method="POST",
                headers=headers,
                request_json=payload,
                response_status=status,
                response_headers=dict(getattr(exc.response, "headers", {}) or {}),
                response_text=getattr(exc.response, "text", None),
                error=str(exc),
                attempt=attempt + 1,
            )
            retryable = status in {429, 500, 502, 503, 504} or status is None
            if retryable and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            break

    if last_error is None:
        raise RuntimeError("Anthropic request failed with an unknown error.")
    raise last_error


def _minimax_chat(
    messages: list[dict],
    model_name: str | None = None,
    schema: dict | None = None,
) -> str:
    """Calls OpenRouter (MiniMax) chat completions and returns the text."""
    api_key = get_minimax_api_key()
    base_url = get_minimax_api_base_url().rstrip("/")
    model = _strip_provider_prefix(model_name) or get_minimax_model()

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                },
                timeout=(15, 180),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    if _resolve_ollama_model(model_name):
        return _ollama_chat(messages, model_name=model_name, schema=schema)

    if last_error is None:
        raise RuntimeError("OpenRouter request failed with an unknown error.")
    raise last_error


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_text(prompt: str, model_name: str = None) -> str:
    """
    Generates text using MiniMax (if API key set) or Ollama (fallback).

    Args:
        prompt (str): User prompt.
        model_name (str): Ollama model override.

    Returns:
        response (str): Generated text.
    """
    if _is_anthropic_model(model_name):
        append_trace("llm_dispatch", route="anthropic_only", model_name=model_name or "")
        return _anthropic_chat(
            [{"role": "user", "content": prompt}],
            model_name=model_name,
            max_tokens=4096,
        )

    if _minimax_available():
        return _minimax_chat(
            [{"role": "user", "content": prompt}],
            model_name=model_name,
        )

    return _ollama_chat(
        [{"role": "user", "content": prompt}],
        model_name=model_name,
    )


def generate_text_structured(
    prompt: str,
    system_prompt: str,
    schema: dict,
    model_name: str = None,
) -> str:
    """
    Generates structured JSON text using MiniMax or Ollama.

    MiniMax path: sends system + user messages, asks for JSON explicitly,
    strips markdown fences from the response.

    Ollama path: uses native format=schema enforcement.

    Args:
        prompt (str): User prompt.
        system_prompt (str): System instructions.
        schema (dict): JSON schema - used for Ollama format enforcement;
            communicated via prompt to MiniMax.
        model_name (str): Ollama model override.

    Returns:
        response (str): Raw JSON string matching the schema.
    """
    if _is_anthropic_model(model_name):
        schema_hint = json.dumps(schema, ensure_ascii=False)
        full_system = (
            f"{system_prompt}\n\n"
            f"You MUST return valid JSON matching this schema exactly:\n{schema_hint}\n"
            "Return ONLY the JSON object, no markdown fencing, no extra text."
        )
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]
        append_trace("llm_dispatch", route="anthropic_only_structured", model_name=model_name or "")
        raw = _anthropic_chat(
            messages,
            model_name=model_name,
            schema=schema,
            max_tokens=12000,
        )
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        return raw

    if _minimax_available():
        schema_hint = json.dumps(schema, ensure_ascii=False)
        full_system = (
            f"{system_prompt}\n\n"
            f"You MUST return valid JSON matching this schema exactly:\n{schema_hint}\n"
            "Return ONLY the JSON object, no markdown fencing, no extra text."
        )
        raw = _minimax_chat(
            [
                {"role": "system", "content": full_system},
                {"role": "user", "content": prompt},
            ],
            model_name=model_name,
            schema=schema,
        )
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        return raw

    return _ollama_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        model_name=model_name,
        schema=schema,
    )
