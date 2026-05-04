from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SPACE_AUTOMATION_DIR = ROOT_DIR / "space_automation"
OUTPUT_DIR = SPACE_AUTOMATION_DIR / "output"
ROOT_CONFIG_PATH = ROOT_DIR / "config.json"


def _load_root_config() -> dict:
    if not ROOT_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(ROOT_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


_ROOT_CONFIG = _load_root_config()


def _env_or_config(env_name: str, config_key: str, default: str = "") -> str:
    env_value = os.getenv(env_name, "").strip()
    if env_value:
        return env_value

    config_value = str(_ROOT_CONFIG.get(config_key, "")).strip()
    if config_value:
        return config_value

    return default


@dataclass(slots=True)
class SpaceAutomationConfig:
    nasa_apod_url: str = "https://api.nasa.gov/planetary/apod"
    nasa_api_key: str = os.getenv("NASA_API_KEY", "DEMO_KEY")
    anthropic_api_key: str = _env_or_config("ANTHROPIC_API_KEY", "anthropic_api_key", "")
    gemini_api_key: str = _env_or_config("GEMINI_API_KEY", "gemini_tts_api_key", "")
    claude_model: str = os.getenv("SPACE_CLAUDE_MODEL", "claude-haiku-4-5")
    gemini_tts_voice: str = os.getenv("SPACE_GEMINI_TTS_VOICE", "iapetus")
    ffmpeg_path: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    ffprobe_path: str = os.getenv("FFPROBE_PATH", "ffprobe")
    output_dir: Path = OUTPUT_DIR
    request_timeout_seconds: int = 60
    target_width: int = 1080
    target_height: int = 1920
    target_fps: int = 30

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)


_CONFIG = SpaceAutomationConfig()


def get_space_automation_config() -> SpaceAutomationConfig:
    _CONFIG.ensure_directories()
    return _CONFIG
