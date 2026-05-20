"""
runware_provider.py - Runware FLUX image generation helper.

generate_flux1_image() is used as the low-cost AI fallback for PodcastV2
secondary assets after stock video sources miss.
"""

from __future__ import annotations

import base64
import os
import re
import time
from uuid import uuid4

import requests

from config import get_runware_api_key, get_runware_image_settings, get_verbose
from runtime_trace import append_api_usage
from status import info, warning, error


RUNWARE_REQUEST_TIMEOUT = (10, 180)
RUNWARE_DOWNLOAD_TIMEOUT = (10, 60)
RUNWARE_MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
RUNWARE_MIN_SECONDS_BETWEEN_CALLS = 1.0
RUNWARE_NEGATIVE_PROMPT = (
    "text, captions, subtitles, watermark, logo, user interface, UI, "
    "low quality, blurry, distorted anatomy, extra fingers, extra limbs, "
    "oversaturated, cartoon, anime"
)

_last_runware_image_time: float = 0.0


def _persist_image(image_bytes: bytes, output_path: str) -> str | None:
    if not image_bytes or len(image_bytes) < 1024:
        return None
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "wb") as image_file:
        image_file.write(image_bytes)
    if get_verbose():
        info(f' => Wrote image from Runware FLUX to "{output_path}"')
    return output_path


def _download_image(image_url: str, output_path: str) -> str | None:
    started_at = time.monotonic()
    bytes_written = 0
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with requests.get(image_url, stream=True, timeout=RUNWARE_DOWNLOAD_TIMEOUT) as response:
        response.raise_for_status()
        with open(output_path, "wb") as image_file:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if time.monotonic() - started_at > RUNWARE_DOWNLOAD_TIMEOUT[1]:
                    raise TimeoutError("Runware image download exceeded wall-clock timeout.")
                if not chunk:
                    continue
                image_file.write(chunk)
                bytes_written += len(chunk)
                if bytes_written > RUNWARE_MAX_DOWNLOAD_BYTES:
                    raise RuntimeError("Runware image download exceeded max size.")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return output_path
    if os.path.exists(output_path):
        os.remove(output_path)
    return None


def _image_from_data_uri(data_uri: str) -> bytes | None:
    match = re.match(r"^data:image/[^;]+;base64,(.+)$", str(data_uri or ""), flags=re.I | re.S)
    if not match:
        return None
    return base64.b64decode(match.group(1))


def _record_usage(result: dict, settings: dict) -> None:
    try:
        cost = float(result.get("cost") or 0)
    except (TypeError, ValueError):
        cost = 0.0
    if cost > 0:
        append_api_usage(
            "runware_flux1_image",
            "usd",
            cost,
            model=settings["model"],
            width=settings["width"],
            height=settings["height"],
            steps=settings["steps"],
        )
        return

    append_api_usage(
        "runware_flux1_image",
        "requests",
        1,
        model=settings["model"],
        width=settings["width"],
        height=settings["height"],
        steps=settings["steps"],
    )


def generate_flux1_image(prompt: str, output_path: str, api_key: str | None = None) -> str | None:
    """
    Generate one budget-conscious FLUX.1 image via Runware and write it locally.

    The request intentionally avoids LoRAs, reference images, upscalers, and
    accelerator options so a fallback image cannot silently become expensive.
    """
    global _last_runware_image_time

    prompt = str(prompt or "").strip()
    if not prompt:
        return None

    api_key = str(api_key or get_runware_api_key() or "").strip()
    if not api_key:
        error("runware_api_key is not configured.")
        return None

    elapsed = time.time() - _last_runware_image_time
    if _last_runware_image_time > 0 and elapsed < RUNWARE_MIN_SECONDS_BETWEEN_CALLS:
        time.sleep(RUNWARE_MIN_SECONDS_BETWEEN_CALLS - elapsed)
    _last_runware_image_time = time.time()

    settings = get_runware_image_settings()
    endpoint = settings["api_base_url"].rstrip("/")
    task = {
        "taskType": "imageInference",
        "taskUUID": str(uuid4()),
        "deliveryMethod": "sync",
        "includeCost": True,
        "outputType": "URL",
        "outputFormat": settings["output_format"],
        "numberResults": 1,
        "positivePrompt": prompt[:3000],
        "negativePrompt": RUNWARE_NEGATIVE_PROMPT,
        "model": settings["model"],
        "width": settings["width"],
        "height": settings["height"],
        "steps": settings["steps"],
        "CFGScale": settings["cfg_scale"],
    }
    if settings["output_format"] in {"JPG", "WEBP"}:
        task["outputQuality"] = settings["output_quality"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        if get_verbose():
            info(
                "Generating fallback image with Runware FLUX.1 "
                f"({settings['width']}x{settings['height']}, {settings['steps']} steps)"
            )
        response = requests.post(endpoint, headers=headers, json=[task], timeout=RUNWARE_REQUEST_TIMEOUT)
        response.raise_for_status()
        body = response.json()

        errors = body.get("errors") or []
        if errors:
            message = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
            warning(f"Runware image generation returned an error: {message}")
            return None

        results = body.get("data") or []
        if not results:
            warning(f"Runware image generation returned no data: {body}")
            return None

        result = results[0]
        _record_usage(result, settings)

        image_url = result.get("imageURL")
        if image_url:
            return _download_image(str(image_url), output_path)

        image_data_uri = result.get("imageDataURI")
        if image_data_uri:
            image_bytes = _image_from_data_uri(str(image_data_uri))
            return _persist_image(image_bytes or b"", output_path)

        image_base64 = result.get("imageBase64Data")
        if image_base64:
            return _persist_image(base64.b64decode(image_base64), output_path)

        warning(f"Runware did not return an image payload: {result}")
        return None
    except Exception as exc:
        if os.path.exists(output_path):
            os.remove(output_path)
        if get_verbose():
            warning(f"Failed to generate image with Runware FLUX.1: {exc}")
        return None
