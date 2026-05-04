from __future__ import annotations

from dataclasses import asdict, dataclass


ALLOWED_MOODS = {
    "mysterious",
    "hopeful",
    "awe",
    "urgent",
    "calm",
}

ALLOWED_TEMPLATES = {
    "landscape_blur",
    "portrait_ken_burns",
}

ALLOWED_SAFE_ZONES = {
    "top_left",
    "top_center",
    "top_right",
    "center",
    "bottom_left",
    "bottom_center",
    "bottom_right",
}

ALLOWED_BGM_VIBES = {
    "ambient_dark",
    "ambient_light",
    "cinematic_space",
    "calm_drift",
}


def _normalize_token(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    return text


def _resolve_mood(value: object) -> str:
    raw = _normalize_token(value)
    if raw in ALLOWED_MOODS:
        return raw
    if "urgent" in raw:
        return "urgent"
    if "hope" in raw or "uplift" in raw:
        return "hopeful"
    if "calm" in raw or "gentle" in raw:
        return "calm"
    if "myster" in raw or "dark" in raw:
        return "mysterious"
    if "awe" in raw or "ethereal" in raw or "wonder" in raw:
        return "awe"
    raise ValueError(f"Unsupported mood: {value!r}")


def _resolve_template(value: object) -> str:
    raw = _normalize_token(value)
    if raw == "landscape blur":
        return "landscape_blur"
    if raw == "portrait ken burns":
        return "portrait_ken_burns"
    if "landscape" in raw or "blur" in raw or "wide" in raw:
        return "landscape_blur"
    if "portrait" in raw or "ken burns" in raw or "vertical" in raw:
        return "portrait_ken_burns"
    raise ValueError(f"Unsupported template: {value!r}")


def _resolve_safe_zone(value: object) -> str:
    raw = _normalize_token(value)
    raw = raw.replace("upper", "top").replace("lower", "bottom").replace("middle", "center")
    raw = raw.replace("centre", "center")
    candidate = raw.replace(" ", "_")
    if candidate in ALLOWED_SAFE_ZONES:
        return candidate
    if "top" in raw and "left" in raw:
        return "top_left"
    if "top" in raw and "right" in raw:
        return "top_right"
    if "top" in raw:
        return "top_center"
    if "bottom" in raw and "left" in raw:
        return "bottom_left"
    if "bottom" in raw and "right" in raw:
        return "bottom_right"
    if "bottom" in raw:
        return "bottom_center"
    if "center" in raw:
        return "center"
    raise ValueError(f"Unsupported safe_zone: {value!r}")


def _resolve_bgm_vibe(value: object) -> str:
    raw = _normalize_token(value)
    candidate = raw.replace(" ", "_")
    if candidate in ALLOWED_BGM_VIBES:
        return candidate
    if "dark" in raw or "myster" in raw:
        return "ambient_dark"
    if "light" in raw or "warm" in raw:
        return "ambient_light"
    if "cinematic" in raw or "space" in raw or "epic" in raw:
        return "cinematic_space"
    if "calm" in raw or "drift" in raw or "float" in raw:
        return "calm_drift"
    raise ValueError(f"Unsupported background_music_vibe: {value!r}")


@dataclass(slots=True)
class SpaceControlMetadata:
    mood: str
    template: str
    safe_zone: str
    overlay_text: str
    background_music_vibe: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "SpaceControlMetadata":
        mood = _resolve_mood(payload.get("mood", ""))
        template = _resolve_template(payload.get("template", ""))
        safe_zone = _resolve_safe_zone(payload.get("safe_zone", ""))
        overlay_text = str(payload.get("overlay_text", "")).strip()
        background_music_vibe = _resolve_bgm_vibe(payload.get("background_music_vibe", ""))

        if not overlay_text:
            raise ValueError("overlay_text cannot be empty.")

        return cls(
            mood=mood,
            template=template,
            safe_zone=safe_zone,
            overlay_text=overlay_text,
            background_music_vibe=background_music_vibe,
        )


@dataclass(slots=True)
class ProducerOutput:
    script: str
    control: SpaceControlMetadata

    def to_dict(self) -> dict:
        return {
            "script": self.script,
            "control": self.control.to_dict(),
        }


def producer_response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "minLength": 120,
            },
            "control": {
                "type": "object",
                "properties": {
                    "mood": {
                        "type": "string",
                        "enum": sorted(ALLOWED_MOODS),
                    },
                    "template": {
                        "type": "string",
                        "enum": sorted(ALLOWED_TEMPLATES),
                    },
                    "safe_zone": {
                        "type": "string",
                        "enum": sorted(ALLOWED_SAFE_ZONES),
                    },
                    "overlay_text": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "background_music_vibe": {
                        "type": "string",
                        "enum": sorted(ALLOWED_BGM_VIBES),
                    },
                },
                "required": [
                    "mood",
                    "template",
                    "safe_zone",
                    "overlay_text",
                    "background_music_vibe",
                ],
                "additionalProperties": False,
            },
        },
        "required": ["script", "control"],
        "additionalProperties": False,
    }
