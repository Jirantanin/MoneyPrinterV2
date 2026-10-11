import os
import sys
import json
import copy

ROOT_DIR = os.path.dirname(sys.path[0])


def _load_config() -> dict:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        return json.load(file)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_nested(source: dict, *keys):
    cursor = source
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _normalize_int(value, fallback: int, minimum: int = 1, maximum: int = 10) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(minimum, min(parsed, maximum))


def _normalize_float(value, fallback: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(minimum, min(parsed, maximum))


def _normalize_bool(value, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disabled"}:
        return False
    return fallback


def _default_podcast_settings() -> dict:
    return {
        "voices": {
            "thai_gemini_voice": "en-us-knox",
        },
        "models": {
            "ollama_model": "",
            "minimax_model": "minimax/minimax-m2.5:free",
            "anthropic_model": "claude-sonnet-4-6",
        },
        "advanced": {
            "outro_hold_seconds": 3.0,
        },
        "audio": {
            "background_bed_enabled": True,
            "background_bed_path": "Songs/hope.mp3",
            "background_bed_volume_db": -16.0,
            "background_bed_ducking_ratio": 2.0,
            "background_bed_fade_seconds": 2.0,
        },
    }


def get_podcast_settings() -> dict:
    config_json = _load_config()
    defaults = _default_podcast_settings()
    nested = config_json.get("podcast_settings", {}) or {}
    settings = _deep_merge(defaults, nested)

    for model_key in ("ollama_model", "minimax_model", "anthropic_model"):
        settings["models"][model_key] = (
            _get_nested(nested, "models", model_key)
            or config_json.get(model_key)
            or defaults["models"][model_key]
        )

    outro_hold_seconds = _get_nested(nested, "advanced", "outro_hold_seconds")
    if outro_hold_seconds is None:
        outro_hold_seconds = defaults["advanced"]["outro_hold_seconds"]
    settings["advanced"]["outro_hold_seconds"] = _normalize_float(
        outro_hold_seconds, defaults["advanced"]["outro_hold_seconds"], 0.0, 10.0,
    )

    audio_defaults = defaults["audio"]
    settings["audio"]["background_bed_enabled"] = _normalize_bool(
        _get_nested(nested, "audio", "background_bed_enabled"), audio_defaults["background_bed_enabled"],
    )
    settings["audio"]["background_bed_path"] = str(
        _get_nested(nested, "audio", "background_bed_path") or audio_defaults["background_bed_path"]
    ).strip()
    for key, low, high in (
        ("background_bed_volume_db", -42.0, -4.0),
        ("background_bed_ducking_ratio", 2.0, 20.0),
        ("background_bed_fade_seconds", 0.0, 8.0),
    ):
        value = _get_nested(nested, "audio", key)
        settings["audio"][key] = _normalize_float(
            audio_defaults[key] if value is None else value, audio_defaults[key], low, high,
        )

    return settings


def get_podcast_background_bed_settings() -> dict:
    return copy.deepcopy(get_podcast_settings().get("audio", {}))


def get_podcast_outro_hold_seconds() -> float:
    return float(get_podcast_settings().get("advanced", {}).get("outro_hold_seconds", 3.0))


def get_verbose() -> bool:
    """
    Gets the verbose flag from the config file.

    Returns:
        verbose (bool): The verbose flag
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        return json.load(file)["verbose"]


def get_minimax_api_key() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        return json.load(file).get("minimax_api_key", "")


def get_anthropic_api_key() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        configured = json.load(file).get("anthropic_api_key", "")
        return configured or os.environ.get("ANTHROPIC_API_KEY", "")


def get_anthropic_model() -> str:
    return get_podcast_settings()["models"]["anthropic_model"]

def get_minimax_model() -> str:
    return get_podcast_settings()["models"]["minimax_model"]

def get_minimax_api_base_url() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        return json.load(file).get("minimax_api_base_url", "https://openrouter.ai/api/v1")

def get_gemini_tts_api_key() -> str:
    """Gets the Gemini TTS API key, falling back to nanobanana2_api_key or GEMINI_API_KEY env."""
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    return (
        cfg.get("gemini_tts_api_key", "")
        or cfg.get("nanobanana2_api_key", "")
        or os.environ.get("GEMINI_API_KEY", "")
    )

def get_gemini_tts_model() -> str:
    """Gemini TTS model id; 3.8 Flash TTS uses the Interactions API (see classes/Tts.py)."""
    try:
        configured = _load_config().get("gemini_tts_model")
    except (OSError, ValueError):
        configured = None
    return str(configured or "gemini-3.8-flash-tts")

def get_tts_gemini_thai_voice() -> str:
    """Gets the Gemini TTS voice name for Thai podcast narration."""
    return get_podcast_settings().get("voices", {}).get("thai_gemini_voice", "en-us-knox")

def get_ollama_base_url() -> str:
    """
    Gets the Ollama base URL.

    Returns:
        url (str): The Ollama base URL
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8-sig") as file:
        return json.load(file).get("ollama_base_url", "http://127.0.0.1:11434")

def get_ollama_model() -> str:
    """
    Gets the Ollama model name from the config file.

    Returns:
        model (str): The Ollama model name, or empty string if not set.
    """
    return get_podcast_settings()["models"]["ollama_model"]


def _normalize_runware_output_format(value: str | None) -> str:
    fmt = str(value or "").strip().upper()
    if fmt in {"PNG", "JPG", "WEBP"}:
        return fmt
    if fmt == "JPEG":
        return "JPG"
    return "PNG"

def _round_to_step(value: int, step: int = 64) -> int:
    if step <= 1:
        return value
    return max(step, int(round(value / step) * step))

def get_runware_api_key() -> str:
    """
    Gets the Runware API key for FLUX fallback image generation.

    Returns:
        key (str): API key
    """
    return str(_load_config().get("runware_api_key") or os.environ.get("RUNWARE_API_KEY", "") or "")

def get_runware_image_settings() -> dict:
    """Return budget-conscious Runware settings for PodcastV2 fallback images."""
    cfg = _load_config()
    width = _normalize_int(cfg.get("runware_image_width"), 1024, 128, 2048)
    height = _normalize_int(cfg.get("runware_image_height"), 576, 128, 2048)
    return {
        "api_base_url": str(cfg.get("runware_api_base_url") or "https://api.runware.ai/v1"),
        "model": str(cfg.get("runware_image_model") or "runware:101@1"),
        "width": _round_to_step(width),
        "height": _round_to_step(height),
        # Section-opener / hero images replace Codex Image Gen and are shown full frame at 1080p.
        "hero_width": _round_to_step(_normalize_int(cfg.get("runware_hero_image_width"), 1920, 128, 2048)),
        "hero_height": _round_to_step(_normalize_int(cfg.get("runware_hero_image_height"), 1088, 128, 2048)),
        "hero_model": str(cfg.get("runware_hero_image_model") or cfg.get("runware_image_model") or "runware:101@1"),
        "steps": _normalize_int(cfg.get("runware_image_steps"), 28, 1, 50),
        "cfg_scale": _normalize_float(cfg.get("runware_image_cfg_scale"), 3.5, 1.0, 20.0),
        "output_format": _normalize_runware_output_format(cfg.get("runware_image_output_format")),
        "output_quality": _normalize_int(cfg.get("runware_image_output_quality"), 90, 20, 99),
        "retry_count": _normalize_int(cfg.get("runware_image_retry_count"), 1, 1, 3),
    }
