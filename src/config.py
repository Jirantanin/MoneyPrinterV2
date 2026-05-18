import os
import sys
import json
import copy
import threading
import srt_equalizer

from termcolor import colored

ROOT_DIR = os.path.dirname(sys.path[0])


def _load_config() -> dict:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8") as file:
        return json.load(file)


def _write_config(config: dict) -> None:
    with open(os.path.join(ROOT_DIR, "config.json"), "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
        file.write("\n")


_CONFIG_LOCK = threading.Lock()


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


def _normalize_rate(value, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if text == "0%":
        return "+0%"
    if text.endswith("%") and (text.startswith("+") or text.startswith("-")):
        return text
    if text.endswith("%"):
        return f"+{text}"
    return fallback


def _default_podcast_settings() -> dict:
    return {
        "voices": {
            "english_edge_voice": "en-US-ChristopherNeural",
            "english_edge_rate": "+20%",
            "thai_edge_voice": "th-TH-PremwadeeNeural",
            "thai_edge_rate": "-12%",
            "thai_elevenlabs_voice_id": "",
            "thai_elevenlabs_fallback_voice_id": "JBFqnCBsd6RMkjVDRZzb",
            "thai_gemini_voice": "Aoede",
        },
        "models": {
            "script_model": "claude-sonnet-4-6",
            "ollama_model": "",
            "minimax_model": "minimax/minimax-m2.5:free",
            "anthropic_model": "claude-sonnet-4-6",
            "image_model": "gemini-3.1-flash-image-preview",
            "image_aspect_ratio": "16:9",
        },
        "prompting": {
            "narrator_name": "Alex",
            "narrator_persona": "A curious narrator who questions assumptions, builds from simple facts to mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering about your place in the universe",
            "narrator_voice": "en-GB-RyanNeural",
            "narrator_rate": "-20%",
            "podcast_style_prompt": (
                "flat design illustration, Kurzgesagt style, vivid saturated colors, "
                "bright solid-color background, cute simple bird and creature characters, "
                "bold geometric shapes, clean vector art, no photorealism, "
                "no dark cinematic mood, no comic panels --"
            ),
            "script_system_prompt": (
                "You are {narrator_name}, {narrator_persona}. /no_think "
                "Narrate in {language} language. "
                "Write in the style of Kurzgesagt – In a Nutshell: open with a big thought-provoking question, "
                "use \"we\" to include the listener in the journey, "
                "build from simple everyday concepts to mind-blowing scale, "
                "mix short punchy sentences with longer explanatory ones, "
                "use vivid surprising analogies, and close with a philosophical reflection "
                "that leaves the listener in quiet wonder. "
                "Output ONLY valid JSON matching the provided schema. "
                "No markdown, no asterisks, no extra commentary."
            ),
            "metadata_system_prompt": (
                "You are a YouTube metadata writer for long-form podcast videos.\n\n"
                "Write ALL metadata in {language}.\n"
                "If {language} is Thai, the title, description, hashtags, and tags must be in Thai except unavoidable proper nouns.\n"
                "Do not switch to English unless the source topic itself is a proper noun, branded term, or official mission name.\n\n"
                "Topic: {topic}\n"
                "Opening narration: {opening_narration}\n\n"
                "{creative_direction_block}"
                "Generate YouTube metadata for this podcast episode. Return ONLY valid JSON with these keys:\n"
                '- "title": Engaging podcast title, max 90 characters, NO emoji, NO hashtags\n'
                '- "description": 2-3 paragraph description (max 4000 chars) summarizing what the episode covers. End with 3-5 relevant hashtags on a new line.\n'
                '- "tags": Array of 8-15 relevant tags as strings\n\n'
                "Return ONLY the JSON object, no markdown fencing."
            ),
            "thumbnail_system_prompt": (
                "YouTube thumbnail for a podcast episode about: {topic}. "
                "{creative_direction_block}"
                "One clear striking central image that fills the frame. "
                "No text, no logos."
            ),
        },
        "advanced": {
            "image_retry_count": 3,
            "audio_retry_count": 3,
            "script_sentence_length": 4,
            "outro_hold_seconds": 3.0,
        },
        "audio": {
            "background_bed_enabled": True,
            "background_bed_path": "Songs/hope.mp3",
            "background_bed_volume_db": -10.0,
            "background_bed_ducking_ratio": 2.0,
            "background_bed_fade_seconds": 2.0,
        },
    }


def _default_podcast_settings_schema() -> dict:
    return {
        "voices": {
            "english_edge_voice": {"type": "text", "label": "English Edge voice"},
            "english_edge_rate": {
                "type": "select",
                "label": "English Edge speed",
                "options": ["-20%", "-15%", "-12%", "-10%", "-5%", "+0%", "+10%", "+20%"],
            },
            "thai_edge_voice": {"type": "text", "label": "Thai Edge voice"},
            "thai_edge_rate": {
                "type": "select",
                "label": "Thai Edge speed",
                "options": ["-25%", "-20%", "-18%", "-15%", "-12%", "-10%", "-5%", "+0%"],
            },
            "thai_elevenlabs_voice_id": {"type": "text", "label": "Thai ElevenLabs voice ID"},
            "thai_elevenlabs_fallback_voice_id": {"type": "text", "label": "Thai ElevenLabs fallback voice ID"},
        },
        "models": {
            "script_model": {"type": "text", "label": "Script model"},
            "ollama_model": {"type": "text", "label": "Ollama model"},
            "minimax_model": {"type": "text", "label": "MiniMax model"},
            "anthropic_model": {"type": "text", "label": "Anthropic model"},
            "image_model": {"type": "text", "label": "Image model"},
            "image_aspect_ratio": {
                "type": "select",
                "label": "Image aspect ratio",
                "options": ["16:9", "9:16", "1:1", "4:3", "3:4"],
            },
        },
        "prompting": {
            "narrator_name": {"type": "text", "label": "Narrator name"},
            "narrator_persona": {"type": "textarea", "label": "Narrator persona"},
            "narrator_voice": {"type": "text", "label": "Narrator voice"},
            "narrator_rate": {
                "type": "select",
                "label": "Narrator speed",
                "options": ["-30%", "-25%", "-20%", "-15%", "-12%", "-10%", "-5%", "+0%"],
            },
            "podcast_style_prompt": {"type": "textarea", "label": "Podcast style prompt"},
            "script_system_prompt": {"type": "textarea", "label": "Script system prompt"},
            "metadata_system_prompt": {"type": "textarea", "label": "Metadata system prompt"},
            "thumbnail_system_prompt": {"type": "textarea", "label": "Thumbnail system prompt"},
        },
        "advanced": {
            "image_retry_count": {"type": "number", "label": "Image retry count", "min": 1, "max": 10},
            "audio_retry_count": {"type": "number", "label": "Audio retry count", "min": 1, "max": 10},
            "script_sentence_length": {"type": "number", "label": "Script sentence length", "min": 1, "max": 10},
            "outro_hold_seconds": {"type": "number", "label": "Outro hold seconds", "min": 0, "max": 10},
        },
        "audio": {
            "background_bed_enabled": {"type": "checkbox", "label": "Background bed"},
            "background_bed_path": {"type": "text", "label": "Background audio path"},
            "background_bed_volume_db": {"type": "number", "label": "Background volume dB", "min": -42, "max": -4},
            "background_bed_ducking_ratio": {"type": "number", "label": "Ducking ratio", "min": 2, "max": 20},
            "background_bed_fade_seconds": {"type": "number", "label": "Fade seconds", "min": 0, "max": 8},
        },
    }


def get_podcast_settings_schema() -> dict:
    return copy.deepcopy(_default_podcast_settings_schema())


def get_podcast_settings() -> dict:
    config_json = _load_config()
    defaults = _default_podcast_settings()
    nested = config_json.get("podcast_settings", {}) or {}
    legacy_prompting = config_json.get("podcast_narrator", {}) or {}
    settings = _deep_merge(defaults, nested)

    settings["voices"]["english_edge_voice"] = (
        _get_nested(nested, "voices", "english_edge_voice")
        or _get_nested(config_json, "tts", "edge", "voice")
        or config_json.get("tts_voice")
        or defaults["voices"]["english_edge_voice"]
    )
    settings["voices"]["english_edge_rate"] = (
        _get_nested(nested, "voices", "english_edge_rate")
        or _get_nested(config_json, "tts", "edge", "rate")
        or config_json.get("tts_rate")
        or defaults["voices"]["english_edge_rate"]
    )
    settings["voices"]["thai_edge_voice"] = (
        _get_nested(nested, "voices", "thai_edge_voice")
        or _get_nested(config_json, "tts", "edge_thai", "voice")
        or defaults["voices"]["thai_edge_voice"]
    )
    settings["voices"]["thai_edge_rate"] = (
        _get_nested(nested, "voices", "thai_edge_rate")
        or _get_nested(config_json, "tts", "edge_thai", "rate")
        or defaults["voices"]["thai_edge_rate"]
    )
    settings["voices"]["thai_elevenlabs_voice_id"] = (
        _get_nested(nested, "voices", "thai_elevenlabs_voice_id")
        or config_json.get("elevenlabs_voice_id_th")
        or defaults["voices"]["thai_elevenlabs_voice_id"]
    )
    settings["voices"]["thai_elevenlabs_fallback_voice_id"] = (
        _get_nested(nested, "voices", "thai_elevenlabs_fallback_voice_id")
        or defaults["voices"]["thai_elevenlabs_fallback_voice_id"]
    )

    settings["models"]["ollama_model"] = (
        _get_nested(nested, "models", "ollama_model")
        or config_json.get("ollama_model")
        or defaults["models"]["ollama_model"]
    )
    settings["models"]["script_model"] = (
        _get_nested(nested, "models", "script_model")
        or config_json.get("podcast_script_model")
        or config_json.get("anthropic_model")
        or config_json.get("minimax_model")
        or config_json.get("ollama_model")
        or defaults["models"]["script_model"]
    )
    settings["models"]["minimax_model"] = (
        _get_nested(nested, "models", "minimax_model")
        or config_json.get("minimax_model")
        or defaults["models"]["minimax_model"]
    )
    settings["models"]["anthropic_model"] = (
        _get_nested(nested, "models", "anthropic_model")
        or config_json.get("anthropic_model")
        or defaults["models"]["anthropic_model"]
    )
    settings["models"]["image_model"] = (
        _get_nested(nested, "models", "image_model")
        or config_json.get("nanobanana2_model")
        or defaults["models"]["image_model"]
    )
    settings["models"]["image_aspect_ratio"] = (
        _get_nested(nested, "models", "image_aspect_ratio")
        or config_json.get("nanobanana2_aspect_ratio")
        or defaults["models"]["image_aspect_ratio"]
    )

    settings["prompting"]["narrator_name"] = (
        _get_nested(nested, "prompting", "narrator_name")
        or legacy_prompting.get("name")
        or defaults["prompting"]["narrator_name"]
    )
    settings["prompting"]["narrator_persona"] = (
        _get_nested(nested, "prompting", "narrator_persona")
        or legacy_prompting.get("persona")
        or defaults["prompting"]["narrator_persona"]
    )
    settings["prompting"]["narrator_voice"] = (
        _get_nested(nested, "prompting", "narrator_voice")
        or legacy_prompting.get("tts_voice")
        or defaults["prompting"]["narrator_voice"]
    )
    settings["prompting"]["narrator_rate"] = (
        _get_nested(nested, "prompting", "narrator_rate")
        or legacy_prompting.get("tts_rate")
        or defaults["prompting"]["narrator_rate"]
    )
    settings["prompting"]["podcast_style_prompt"] = (
        _get_nested(nested, "prompting", "podcast_style_prompt")
        or config_json.get("podcast_style_prompt")
        or defaults["prompting"]["podcast_style_prompt"]
    )
    settings["prompting"]["script_system_prompt"] = (
        _get_nested(nested, "prompting", "script_system_prompt")
        or defaults["prompting"]["script_system_prompt"]
    )
    settings["prompting"]["metadata_system_prompt"] = (
        _get_nested(nested, "prompting", "metadata_system_prompt")
        or defaults["prompting"]["metadata_system_prompt"]
    )
    settings["prompting"]["thumbnail_system_prompt"] = (
        _get_nested(nested, "prompting", "thumbnail_system_prompt")
        or defaults["prompting"]["thumbnail_system_prompt"]
    )

    settings["advanced"]["image_retry_count"] = _normalize_int(
        _get_nested(nested, "advanced", "image_retry_count")
        or defaults["advanced"]["image_retry_count"],
        defaults["advanced"]["image_retry_count"],
    )
    settings["advanced"]["audio_retry_count"] = _normalize_int(
        _get_nested(nested, "advanced", "audio_retry_count")
        or defaults["advanced"]["audio_retry_count"],
        defaults["advanced"]["audio_retry_count"],
    )
    settings["advanced"]["script_sentence_length"] = _normalize_int(
        _get_nested(nested, "advanced", "script_sentence_length")
        or config_json.get("script_sentence_length")
        or defaults["advanced"]["script_sentence_length"],
        defaults["advanced"]["script_sentence_length"],
    )
    outro_hold_seconds = _get_nested(nested, "advanced", "outro_hold_seconds")
    if outro_hold_seconds is None:
        outro_hold_seconds = config_json.get("podcast_outro_hold_seconds")
    if outro_hold_seconds is None:
        outro_hold_seconds = defaults["advanced"]["outro_hold_seconds"]
    settings["advanced"]["outro_hold_seconds"] = _normalize_float(
        outro_hold_seconds,
        defaults["advanced"]["outro_hold_seconds"],
        0.0,
        10.0,
    )

    background_enabled = _get_nested(nested, "audio", "background_bed_enabled")
    if background_enabled is None:
        background_enabled = config_json.get("podcast_background_bed_enabled")
    settings["audio"]["background_bed_enabled"] = _normalize_bool(
        background_enabled,
        defaults["audio"]["background_bed_enabled"],
    )
    settings["audio"]["background_bed_path"] = str(
        _get_nested(nested, "audio", "background_bed_path")
        or config_json.get("podcast_background_bed_path")
        or defaults["audio"]["background_bed_path"]
    ).strip()
    background_volume_db = _get_nested(nested, "audio", "background_bed_volume_db")
    if background_volume_db is None:
        background_volume_db = config_json.get("podcast_background_bed_volume_db")
    if background_volume_db is None:
        background_volume_db = defaults["audio"]["background_bed_volume_db"]
    settings["audio"]["background_bed_volume_db"] = _normalize_float(
        background_volume_db,
        defaults["audio"]["background_bed_volume_db"],
        -42.0,
        -4.0,
    )
    background_ducking_ratio = _get_nested(nested, "audio", "background_bed_ducking_ratio")
    if background_ducking_ratio is None:
        background_ducking_ratio = config_json.get("podcast_background_bed_ducking_ratio")
    if background_ducking_ratio is None:
        background_ducking_ratio = defaults["audio"]["background_bed_ducking_ratio"]
    settings["audio"]["background_bed_ducking_ratio"] = _normalize_float(
        background_ducking_ratio,
        defaults["audio"]["background_bed_ducking_ratio"],
        2.0,
        20.0,
    )
    background_fade_seconds = _get_nested(nested, "audio", "background_bed_fade_seconds")
    if background_fade_seconds is None:
        background_fade_seconds = config_json.get("podcast_background_bed_fade_seconds")
    if background_fade_seconds is None:
        background_fade_seconds = defaults["audio"]["background_bed_fade_seconds"]
    settings["audio"]["background_bed_fade_seconds"] = _normalize_float(
        background_fade_seconds,
        defaults["audio"]["background_bed_fade_seconds"],
        0.0,
        8.0,
    )

    return settings


def save_podcast_settings(updates: dict) -> dict:
    if not isinstance(updates, dict):
        raise ValueError("updates must be an object")

    with _CONFIG_LOCK:
        config_json = _load_config()
        existing = get_podcast_settings()
        merged = _deep_merge(existing, updates)

        merged["voices"]["english_edge_voice"] = str(merged["voices"].get("english_edge_voice", "")).strip() or existing["voices"]["english_edge_voice"]
        merged["voices"]["english_edge_rate"] = _normalize_rate(merged["voices"].get("english_edge_rate"), existing["voices"]["english_edge_rate"])
        merged["voices"]["thai_edge_voice"] = str(merged["voices"].get("thai_edge_voice", "")).strip() or existing["voices"]["thai_edge_voice"]
        merged["voices"]["thai_edge_rate"] = _normalize_rate(merged["voices"].get("thai_edge_rate"), existing["voices"]["thai_edge_rate"])
        merged["voices"]["thai_elevenlabs_voice_id"] = str(merged["voices"].get("thai_elevenlabs_voice_id", "")).strip()
        merged["voices"]["thai_elevenlabs_fallback_voice_id"] = str(merged["voices"].get("thai_elevenlabs_fallback_voice_id", "")).strip() or existing["voices"]["thai_elevenlabs_fallback_voice_id"]
        merged["voices"]["thai_gemini_voice"] = str(merged["voices"].get("thai_gemini_voice", "")).strip() or existing["voices"].get("thai_gemini_voice", "Aoede")

        merged["models"]["script_model"] = str(merged["models"].get("script_model", "")).strip() or existing["models"]["script_model"]
        merged["models"]["ollama_model"] = str(merged["models"].get("ollama_model", "")).strip()
        merged["models"]["minimax_model"] = str(merged["models"].get("minimax_model", "")).strip() or existing["models"]["minimax_model"]
        merged["models"]["anthropic_model"] = str(merged["models"].get("anthropic_model", "")).strip() or existing["models"]["anthropic_model"]
        merged["models"]["image_model"] = str(merged["models"].get("image_model", "")).strip() or existing["models"]["image_model"]
        merged["models"]["image_aspect_ratio"] = str(merged["models"].get("image_aspect_ratio", "")).strip() or existing["models"]["image_aspect_ratio"]

        merged["prompting"]["narrator_name"] = str(merged["prompting"].get("narrator_name", "")).strip() or existing["prompting"]["narrator_name"]
        merged["prompting"]["narrator_persona"] = str(merged["prompting"].get("narrator_persona", "")).strip() or existing["prompting"]["narrator_persona"]
        merged["prompting"]["narrator_voice"] = str(merged["prompting"].get("narrator_voice", "")).strip() or existing["prompting"]["narrator_voice"]
        merged["prompting"]["narrator_rate"] = _normalize_rate(merged["prompting"].get("narrator_rate"), existing["prompting"]["narrator_rate"])
        merged["prompting"]["podcast_style_prompt"] = str(merged["prompting"].get("podcast_style_prompt", "")).strip() or existing["prompting"]["podcast_style_prompt"]
        merged["prompting"]["script_system_prompt"] = str(merged["prompting"].get("script_system_prompt", "")).strip() or existing["prompting"]["script_system_prompt"]
        merged["prompting"]["metadata_system_prompt"] = str(merged["prompting"].get("metadata_system_prompt", "")).strip() or existing["prompting"]["metadata_system_prompt"]
        merged["prompting"]["thumbnail_system_prompt"] = str(merged["prompting"].get("thumbnail_system_prompt", "")).strip() or existing["prompting"]["thumbnail_system_prompt"]

        merged["advanced"]["image_retry_count"] = _normalize_int(merged["advanced"].get("image_retry_count"), existing["advanced"]["image_retry_count"])
        merged["advanced"]["audio_retry_count"] = _normalize_int(merged["advanced"].get("audio_retry_count"), existing["advanced"]["audio_retry_count"])
        merged["advanced"]["script_sentence_length"] = _normalize_int(merged["advanced"].get("script_sentence_length"), existing["advanced"]["script_sentence_length"])
        merged["advanced"]["outro_hold_seconds"] = _normalize_float(
            merged["advanced"].get("outro_hold_seconds"),
            existing["advanced"]["outro_hold_seconds"],
            0.0,
            10.0,
        )

        merged["audio"]["background_bed_enabled"] = _normalize_bool(
            merged["audio"].get("background_bed_enabled"),
            existing["audio"]["background_bed_enabled"],
        )
        merged["audio"]["background_bed_path"] = str(
            merged["audio"].get("background_bed_path", "")
        ).strip() or existing["audio"]["background_bed_path"]
        merged["audio"]["background_bed_volume_db"] = _normalize_float(
            merged["audio"].get("background_bed_volume_db"),
            existing["audio"]["background_bed_volume_db"],
            -42.0,
            -4.0,
        )
        merged["audio"]["background_bed_ducking_ratio"] = _normalize_float(
            merged["audio"].get("background_bed_ducking_ratio"),
            existing["audio"]["background_bed_ducking_ratio"],
            2.0,
            20.0,
        )
        merged["audio"]["background_bed_fade_seconds"] = _normalize_float(
            merged["audio"].get("background_bed_fade_seconds"),
            existing["audio"]["background_bed_fade_seconds"],
            0.0,
            8.0,
        )

        config_json["podcast_settings"] = merged
        config_json["tts"] = config_json.get("tts", {})
        config_json["tts"]["edge"] = {
            "voice": merged["voices"]["english_edge_voice"],
            "rate": merged["voices"]["english_edge_rate"],
        }
        config_json["tts"]["edge_thai"] = {
            "voice": merged["voices"]["thai_edge_voice"],
            "rate": merged["voices"]["thai_edge_rate"],
        }
        config_json["podcast_script_model"] = merged["models"]["script_model"]
        config_json["tts_voice"] = merged["voices"]["english_edge_voice"]
        config_json["tts_rate"] = merged["voices"]["english_edge_rate"]
        config_json["ollama_model"] = merged["models"]["ollama_model"]
        config_json["minimax_model"] = merged["models"]["minimax_model"]
        config_json["anthropic_model"] = merged["models"]["anthropic_model"]
        config_json["nanobanana2_model"] = merged["models"]["image_model"]
        config_json["nanobanana2_aspect_ratio"] = merged["models"]["image_aspect_ratio"]
        config_json["elevenlabs_voice_id_th"] = merged["voices"]["thai_elevenlabs_voice_id"]
        config_json["podcast_narrator"] = {
            "name": merged["prompting"]["narrator_name"],
            "persona": merged["prompting"]["narrator_persona"],
            "tts_voice": merged["prompting"]["narrator_voice"],
            "tts_rate": merged["prompting"]["narrator_rate"],
        }
        config_json["podcast_style_prompt"] = merged["prompting"]["podcast_style_prompt"]
        config_json["podcast_script_system_prompt"] = merged["prompting"]["script_system_prompt"]
        config_json["podcast_metadata_system_prompt"] = merged["prompting"]["metadata_system_prompt"]
        config_json["podcast_thumbnail_system_prompt"] = merged["prompting"]["thumbnail_system_prompt"]
        config_json["podcast_image_retry_count"] = merged["advanced"]["image_retry_count"]
        config_json["podcast_audio_retry_count"] = merged["advanced"]["audio_retry_count"]
        config_json["script_sentence_length"] = merged["advanced"]["script_sentence_length"]
        config_json["podcast_outro_hold_seconds"] = merged["advanced"]["outro_hold_seconds"]
        config_json["podcast_background_bed_enabled"] = merged["audio"]["background_bed_enabled"]
        config_json["podcast_background_bed_path"] = merged["audio"]["background_bed_path"]
        config_json["podcast_background_bed_volume_db"] = merged["audio"]["background_bed_volume_db"]
        config_json["podcast_background_bed_ducking_ratio"] = merged["audio"]["background_bed_ducking_ratio"]
        config_json["podcast_background_bed_fade_seconds"] = merged["audio"]["background_bed_fade_seconds"]
        _write_config(config_json)
        return copy.deepcopy(merged)


def get_podcast_system_settings() -> dict:
    return get_podcast_settings()


def update_podcast_system_settings(settings: dict) -> dict:
    return save_podcast_settings(settings)


def get_podcast_background_bed_settings() -> dict:
    return copy.deepcopy(get_podcast_settings().get("audio", {}))


def get_podcast_outro_hold_seconds() -> float:
    return float(get_podcast_settings().get("advanced", {}).get("outro_hold_seconds", 3.0))


def assert_folder_structure() -> None:
    """
    Make sure that the nessecary folder structure is present.

    Returns:
        None
    """
    # Create the .mp folder
    if not os.path.exists(os.path.join(ROOT_DIR, ".mp")):
        if get_verbose():
            print(colored(f"=> Creating .mp folder at {os.path.join(ROOT_DIR, '.mp')}", "green"))
        os.makedirs(os.path.join(ROOT_DIR, ".mp"))

def get_first_time_running() -> bool:
    """
    Checks if the program is running for the first time by checking if .mp folder exists.

    Returns:
        exists (bool): True if the program is running for the first time, False otherwise
    """
    return not os.path.exists(os.path.join(ROOT_DIR, ".mp"))

def get_verbose() -> bool:
    """
    Gets the verbose flag from the config file.

    Returns:
        verbose (bool): The verbose flag
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["verbose"]

def get_firefox_profile_path() -> str:
    """
    Gets the path to the Firefox profile.

    Returns:
        path (str): The path to the Firefox profile
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["firefox_profile"]

def get_headless() -> bool:
    """
    Gets the headless flag from the config file.

    Returns:
        headless (bool): The headless flag
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["headless"]

def get_minimax_api_key() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("minimax_api_key", "")


def get_anthropic_api_key() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r", encoding="utf-8") as file:
        configured = json.load(file).get("anthropic_api_key", "")
        return configured or os.environ.get("ANTHROPIC_API_KEY", "")


def get_anthropic_model() -> str:
    return get_podcast_settings()["models"]["anthropic_model"]

def get_minimax_model() -> str:
    return get_podcast_settings()["models"]["minimax_model"]

def get_minimax_api_base_url() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("minimax_api_base_url", "https://openrouter.ai/api/v1")

def get_elevenlabs_api_key() -> str:
    """
    Gets the ElevenLabs API key.

    Returns:
        key (str): ElevenLabs API key
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("elevenlabs_api_key", "")

def get_elevenlabs_voice_id_th() -> str:
    """
    Gets the ElevenLabs voice ID for Thai language.

    Returns:
        voice_id (str): ElevenLabs voice ID for Thai
    """
    return get_podcast_settings()["voices"]["thai_elevenlabs_voice_id"]

def get_gemini_tts_api_key() -> str:
    """Gets the Gemini TTS API key, falling back to nanobanana2_api_key or GEMINI_API_KEY env."""
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as f:
        cfg = json.load(f)
    return (
        cfg.get("gemini_tts_api_key", "")
        or cfg.get("nanobanana2_api_key", "")
        or os.environ.get("GEMINI_API_KEY", "")
    )

def get_tts_gemini_thai_voice() -> str:
    """Gets the Gemini TTS voice name for Thai podcast narration."""
    return get_podcast_settings().get("voices", {}).get("thai_gemini_voice", "Aoede")

def get_ollama_base_url() -> str:
    """
    Gets the Ollama base URL.

    Returns:
        url (str): The Ollama base URL
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("ollama_base_url", "http://127.0.0.1:11434")

def get_ollama_model() -> str:
    """
    Gets the Ollama model name from the config file.

    Returns:
        model (str): The Ollama model name, or empty string if not set.
    """
    return get_podcast_settings()["models"]["ollama_model"]


def get_podcast_script_model() -> str:
    return get_podcast_settings()["models"]["script_model"]

def get_nanobanana2_api_base_url() -> str:
    """
    Gets the Nano Banana 2 (Gemini image) API base URL.

    Returns:
        url (str): API base URL
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get(
            "nanobanana2_api_base_url",
            "https://generativelanguage.googleapis.com/v1beta",
        )

def get_nanobanana2_api_key() -> str:
    """
    Gets the Nano Banana 2 API key.

    Returns:
        key (str): API key
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        configured = json.load(file).get("nanobanana2_api_key", "")
        return configured or os.environ.get("GEMINI_API_KEY", "")

def get_nanobanana2_model() -> str:
    """
    Gets the Nano Banana 2 model name.

    Returns:
        model (str): Model name
    """
    return get_podcast_settings()["models"]["image_model"]

def get_nanobanana2_aspect_ratio() -> str:
    """
    Gets the aspect ratio for Nano Banana 2 image generation.

    Returns:
        ratio (str): Aspect ratio
    """
    return get_podcast_settings()["models"]["image_aspect_ratio"]

def get_threads() -> int:
    """
    Gets the amount of threads to use for example when writing to a file with MoviePy.

    Returns:
        threads (int): Amount of threads
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["threads"]
    
def get_zip_url() -> str:
    """
    Gets the URL to the zip file containing the songs.

    Returns:
        url (str): The URL to the zip file
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["zip_url"]

def get_is_for_kids() -> bool:
    """
    Gets the is for kids flag from the config file.

    Returns:
        is_for_kids (bool): The is for kids flag
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["is_for_kids"]

def get_tts_voice() -> str:
    """
    Gets the TTS voice from the config file.

    Returns:
        voice (str): The TTS voice
    """
    return get_tts_edge_voice()

def get_tts_rate() -> str:
    """
    Gets the TTS speaking rate from the config file.
    Uses edge-tts rate format: percentage string with explicit sign, e.g. "+20%".
    Defaults to "+20%" (energetic Shorts pacing) if key is absent from config.

    NOTE: Do NOT add a tts_pitch getter. The pitch= kwarg on edge_tts.Communicate
    is silently ignored by Microsoft's backend since edge-tts v6.0.3.

    Returns:
        rate (str): The TTS rate string
    """
    return get_tts_edge_rate()


def get_tts_provider() -> str:
    """
    Gets the configured TTS provider.

    Returns:
        provider (str): The TTS provider name
    """
    return _load_config().get("tts_provider", "edge")


def get_tts_edge_voice() -> str:
    """
    Gets the Edge TTS voice from the provider-aware config.

    Returns:
        voice (str): The Edge TTS voice
    """
    return get_podcast_settings()["voices"]["english_edge_voice"]


def get_tts_edge_rate() -> str:
    """
    Gets the Edge TTS speaking rate from the provider-aware config.
    Uses edge-tts rate format: percentage string with explicit sign, e.g. "+20%".

    Returns:
        rate (str): The Edge TTS rate string
    """
    return get_podcast_settings()["voices"]["english_edge_rate"]


def get_tts_edge_thai_voice() -> str:
    """
    Gets the Thai Edge TTS voice from config.

    Returns:
        voice (str): The Thai Edge TTS voice
    """
    return get_podcast_settings()["voices"]["thai_edge_voice"]


def get_tts_edge_thai_rate() -> str:
    """
    Gets the Thai Edge TTS speaking rate from config.

    Returns:
        rate (str): The Thai Edge TTS rate string
    """
    return get_podcast_settings()["voices"]["thai_edge_rate"]


def get_tts_edge_thai_fallback_voice_id() -> str:
    """
    Gets the ElevenLabs fallback voice ID used for Thai TTS.

    Returns:
        voice_id (str): The fallback voice ID
    """
    return get_podcast_settings()["voices"]["thai_elevenlabs_fallback_voice_id"]


def get_assemblyai_api_key() -> str:
    """
    Gets the AssemblyAI API key.

    Returns:
        key (str): The AssemblyAI API key
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["assembly_ai_api_key"]

def get_stt_provider() -> str:
    """
    Gets the configured STT provider.

    Returns:
        provider (str): The STT provider
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("stt_provider", "local_whisper")

def get_whisper_model() -> str:
    """
    Gets the local Whisper model name.

    Returns:
        model (str): Whisper model name
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("whisper_model", "base")

def get_whisper_device() -> str:
    """
    Gets the target device for Whisper inference.

    Returns:
        device (str): Whisper device
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("whisper_device", "auto")

def get_whisper_compute_type() -> str:
    """
    Gets the compute type for Whisper inference.

    Returns:
        compute_type (str): Whisper compute type
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("whisper_compute_type", "int8")
    
def get_topic_discovery_config() -> dict:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("topic_discovery", {})

def get_topic_discovery_enabled() -> bool:
    return get_topic_discovery_config().get("enabled", False)

def get_topic_discovery_youtube_api_key() -> str:
    return get_topic_discovery_config().get("youtube_api_key", "")

def get_topic_discovery_news_api_key() -> str:
    return get_topic_discovery_config().get("news_api_key", "")

def get_topic_discovery_anthropic_api_key() -> str:
    return get_topic_discovery_config().get("anthropic_api_key", "")

def get_topic_discovery_scoring_provider() -> str:
    return get_topic_discovery_config().get("scoring_provider", "ollama")

def get_topic_discovery_geo() -> str:
    return get_topic_discovery_config().get("geo", "US")

def get_topic_discovery_max_age_hours() -> int:
    return get_topic_discovery_config().get("max_topic_age_hours", 24)

def equalize_subtitles(srt_path: str, max_chars: int = 10) -> None:
    """
    Equalizes the subtitles in a SRT file.

    Args:
        srt_path (str): The path to the SRT file
        max_chars (int): The maximum amount of characters in a subtitle

    Returns:
        None
    """
    srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)
    
def get_font() -> str:
    """
    Gets the font from the config file.

    Returns:
        font (str): The font
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["font"]

def get_fonts_dir() -> str:
    """
    Gets the fonts directory.

    Returns:
        dir (str): The fonts directory
    """
    return os.path.join(ROOT_DIR, "fonts")

def get_imagemagick_path() -> str:
    """
    Gets the path to ImageMagick.

    Returns:
        path (str): The path to ImageMagick
    """
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file)["imagemagick_path"]

def get_script_sentence_length() -> int:
    """
    Gets the forced script's sentence length.
    In case there is no sentence length in config, returns 4 when none

    Returns:
        length (int): Length of script's sentence
    """
    return get_podcast_settings()["advanced"]["script_sentence_length"]


def get_podcast_narrator() -> dict:
    """
    Gets the podcast narrator configuration object.

    Returns:
        narrator (dict): Keys: name (str), persona (str), tts_voice (str), tts_rate (str)
    """
    settings = get_podcast_settings()["prompting"]
    return {
        "name": settings["narrator_name"],
        "persona": settings["narrator_persona"],
        "tts_voice": settings["narrator_voice"],
        "tts_rate": settings["narrator_rate"],
    }


def get_podcast_style_prompt() -> str:
    """
    Gets the podcast image style lock prefix for Gemini image generation.
    Prepended to every scene image_prompt to enforce visual consistency.

    Returns:
        style_prompt (str): Style prefix string
    """
    return get_podcast_settings()["prompting"]["podcast_style_prompt"]


def get_podcast_script_system_prompt() -> str:
    return get_podcast_settings()["prompting"]["script_system_prompt"]


def get_podcast_metadata_system_prompt() -> str:
    return get_podcast_settings()["prompting"]["metadata_system_prompt"]


def get_podcast_thumbnail_system_prompt() -> str:
    return get_podcast_settings()["prompting"]["thumbnail_system_prompt"]


def get_podcast_image_retry_count() -> int:
    return get_podcast_settings()["advanced"]["image_retry_count"]


def get_podcast_audio_retry_count() -> int:
    return get_podcast_settings()["advanced"]["audio_retry_count"]


def get_kling_access_key() -> str:
    return str(_load_config().get("kling_access_key") or "")


def get_kling_secret_key() -> str:
    return str(_load_config().get("kling_secret_key") or "")
