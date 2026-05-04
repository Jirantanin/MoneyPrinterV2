"""
kling_provider.py — Kling AI image-to-video API helper.

Generates a short video clip from a still image using the Kling
image2video endpoint. Uses HS256 JWT auth (no external jwt library needed).
"""

import base64
import hashlib
import hmac
import json
import os
import time

import requests
from runtime_trace import append_api_usage


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(access_key: str, secret_key: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = _b64url(
        json.dumps({"iss": access_key, "exp": now + 1800, "nbf": now - 5}, separators=(",", ":")).encode()
    )
    msg = f"{header}.{payload}".encode()
    sig = _b64url(hmac.new(secret_key.encode(), msg, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def generate_video_from_image(
    image_path: str,
    prompt: str,
    access_key: str,
    secret_key: str,
    output_path: str,
    duration: int = 5,
    model_name: str = "kling-v2-master",
) -> str:
    """Submit image-to-video task, poll until done, download to output_path.

    Returns output_path on success.
    Raises RuntimeError on API error/task failure, TimeoutError after 10 min.
    """
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"Bearer {_make_jwt(access_key, secret_key)}",
        "Content-Type": "application/json",
    }

    # Submit task
    resp = requests.post(
        "https://api.klingai.com/v1/videos/image2video",
        headers=headers,
        json={
            "model_name": model_name,
            "image": img_b64,
            "prompt": prompt,
            "duration": str(duration),
            "mode": "std",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Kling submit error: {data}")

    task_id = data["data"]["task_id"]
    append_api_usage(
        "kling_image2video",
        "requests",
        1,
        endpoint="https://api.klingai.com/v1/videos/image2video",
        model_name=model_name,
        duration=duration,
    )
    print(f"  Kling task submitted: {task_id}")

    # Wait out the guaranteed-processing window before first poll
    time.sleep(45)

    # Poll until complete — JWT valid 30 min, poll window max 10 min, reuse token
    for attempt in range(90):
        poll = requests.get(
            f"https://api.klingai.com/v1/videos/image2video/{task_id}",
            headers=headers,
            timeout=30,
        )
        poll.raise_for_status()
        pdata = poll.json()
        status = pdata.get("data", {}).get("task_status", "")

        if status == "succeed":
            video_url = pdata["data"]["task_result"]["videos"][0]["url"]
            print(f"  Kling task complete, downloading video...")
            tmp_path = output_path + ".tmp"
            r = requests.get(video_url, timeout=120, stream=True)
            r.raise_for_status()
            try:
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                os.replace(tmp_path, output_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
            return output_path

        if status == "failed":
            raise RuntimeError(f"Kling task failed: {pdata}")

        elapsed = 45 + (attempt + 1) * 5
        if attempt % 6 == 0:
            print(f"  Kling: waiting... ({elapsed}s, status={status})")
        time.sleep(5)

    raise TimeoutError(f"Kling task {task_id} did not complete within 10 minutes")
