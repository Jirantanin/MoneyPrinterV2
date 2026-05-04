"""
image_provider.py — Standalone Gemini image generation module.

Public interface: generate_image(prompt, output_path)
"""

import base64
import os
import time

import requests

from config import (
    get_nanobanana2_api_key,
    get_nanobanana2_api_base_url,
    get_nanobanana2_model,
    get_nanobanana2_aspect_ratio,
    get_verbose,
)
from status import info, warning, error
from runtime_trace import append_api_usage

# Module-level rate-limit state: tracks when the last image was generated.
_last_image_time: float = 0.0


def _persist_image(image_bytes: bytes, output_path: str, provider_label: str) -> str:
    """
    Writes image bytes to the caller-specified path.

    Args:
        image_bytes (bytes): Raw image payload.
        output_path (str): Absolute path where the PNG should be written.
        provider_label (str): Human-readable label used in verbose log output.

    Returns:
        output_path (str): The path that was written.
    """
    with open(output_path, "wb") as image_file:
        image_file.write(image_bytes)

    if get_verbose():
        info(f' => Wrote image from {provider_label} to "{output_path}"')

    return output_path


def _generate_image_nanobanana2(prompt: str, output_path: str, aspect_ratio: str | None = None) -> str | None:
    """
    Calls the Nano Banana 2 (Gemini) image API for the given prompt and writes
    the result to output_path.

    Handles HTTP 429 by sleeping 15 seconds and retrying once.  A second 429
    returns None.

    Args:
        prompt (str): Image generation prompt.
        output_path (str): Destination path for the generated PNG.

    Returns:
        output_path (str) on success, or None on failure.
    """
    if get_verbose():
        info(f"Generating Image using Nano Banana 2 API: {prompt}")

    api_key = get_nanobanana2_api_key()
    if not api_key:
        error("nanobanana2_api_key is not configured.")
        return None

    base_url = get_nanobanana2_api_base_url().rstrip("/")
    model = get_nanobanana2_model()
    aspect_ratio = aspect_ratio or get_nanobanana2_aspect_ratio()

    endpoint = f"{base_url}/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect_ratio},
        },
    }

    def _do_request():
        return requests.post(
            endpoint,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )

    def _parse_image(response):
        body = response.json()
        candidates = body.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                inline_data = part.get("inlineData") or part.get("inline_data")
                if not inline_data:
                    continue
                data = inline_data.get("data")
                mime_type = inline_data.get("mimeType") or inline_data.get("mime_type", "")
                if data and str(mime_type).startswith("image/"):
                    image_bytes = base64.b64decode(data)
                    return _persist_image(image_bytes, output_path, "Nano Banana 2 API")
        if get_verbose():
            warning(f"Nano Banana 2 did not return an image payload. Response: {body}")
        return None

    try:
        response = _do_request()
        if response.status_code == 429:
            if get_verbose():
                warning("Gemini 429 rate limit hit. Waiting 15s before retry...")
            time.sleep(15)
            response = _do_request()
            if response.status_code == 429:
                if get_verbose():
                    warning("Gemini 429 rate limit on retry too. Skipping prompt.")
                return None
        response.raise_for_status()
        result = _parse_image(response)
        if result:
            append_api_usage(
                "gemini_image",
                "requests",
                1,
                endpoint=endpoint,
                model=model,
                aspect_ratio=aspect_ratio,
            )
        return result
    except Exception as e:
        if get_verbose():
            warning(f"Failed to generate image with Nano Banana 2 API: {str(e)}")
        return None


def generate_image(prompt: str, output_path: str, aspect_ratio: str | None = None) -> str | None:
    """
    Generates an AI image for the given prompt and writes it to output_path.

    Enforces a minimum 7-second gap between successive calls using module-level
    state so that all callers (YouTube.py, Podcast.py, thumbnail gen) share a
    single rate-limit counter.

    Args:
        prompt (str): Image generation prompt.
        output_path (str): Caller-controlled destination path for the PNG.
        aspect_ratio (str | None): Override aspect ratio (e.g. "16:9", "9:16").
            If None, uses the nanobanana2_aspect_ratio value from config.json.

    Returns:
        output_path (str) on success, or None on failure / API error.
    """
    global _last_image_time
    elapsed = time.time() - _last_image_time
    if _last_image_time > 0 and elapsed < 7:
        time.sleep(7 - elapsed)
    _last_image_time = time.time()
    return _generate_image_nanobanana2(prompt, output_path, aspect_ratio=aspect_ratio)
