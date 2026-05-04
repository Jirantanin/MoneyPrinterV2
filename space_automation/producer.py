from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

try:
    from space_automation.config import SpaceAutomationConfig
    from space_automation.models import ProducerOutput, SpaceControlMetadata, producer_response_schema
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config import SpaceAutomationConfig
    from models import ProducerOutput, SpaceControlMetadata, producer_response_schema


PRODUCER_SYSTEM_PROMPT = """
You are the producer for a short-form space video pipeline.

Your job:
1. Rewrite the astronomy content into a concise, exciting script for a general audience.
2. Return control metadata for the video editor.

Hard rules:
- The script must be plain, easy to understand English.
- Aim for about 45 to 50 seconds when spoken.
- Keep the tone vivid, cinematic, and accessible.
- Do not use markdown.
- Do not mention camera directions.
- overlay_text must be short and useful on-screen text, usually a place, object name, or mission label.
- template must be:
  - "landscape_blur" for wide images
  - "portrait_ken_burns" only when a portrait crop clearly makes sense
- control.mood must be exactly one of: mysterious, hopeful, awe, urgent, calm
- control.template must be exactly one of: landscape_blur, portrait_ken_burns
- control.safe_zone must be exactly one of: top_left, top_center, top_right, center, bottom_left, bottom_center, bottom_right
- control.background_music_vibe must be exactly one of: ambient_dark, ambient_light, cinematic_space, calm_drift
- Return ONLY valid JSON matching the schema.
""".strip()


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.MULTILINE).strip()
    start = fenced.find("{")
    end = fenced.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Producer response did not contain a JSON object.")
    return fenced[start : end + 1]


def _build_user_prompt(title: str, explanation: str) -> str:
    schema_hint = json.dumps(producer_response_schema(), ensure_ascii=False)
    return (
        f"APOD title: {title}\n\n"
        f"APOD explanation:\n{explanation}\n\n"
        f"JSON schema:\n{schema_hint}\n\n"
        "Return JSON with:\n"
        "- script\n"
        "- control.mood\n"
        "- control.template\n"
        "- control.safe_zone\n"
        "- control.overlay_text\n"
        "- control.background_music_vibe\n"
    )


def _call_anthropic(config: SpaceAutomationConfig, prompt: str) -> str:
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    payload = {
        "model": config.claude_model,
        "max_tokens": 1200,
        "system": PRODUCER_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": config.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API error {exc.code}: {detail}") from exc

    text_parts = []
    for block in raw.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))

    output = "".join(text_parts).strip()
    if not output:
        raise RuntimeError("Anthropic API returned an empty producer response.")
    return output


def generate_producer_output(
    *,
    config: SpaceAutomationConfig,
    title: str,
    explanation: str,
) -> ProducerOutput:
    prompt = _build_user_prompt(title=title, explanation=explanation)
    raw = _call_anthropic(config, prompt)
    payload = json.loads(_extract_json_object(raw))

    script = str(payload.get("script", "")).strip()
    if not script:
        raise ValueError("Producer response is missing script.")

    control = SpaceControlMetadata.from_dict(payload.get("control", {}))
    _ = producer_response_schema()  # kept for a single source of truth for future callers
    return ProducerOutput(script=script, control=control)
