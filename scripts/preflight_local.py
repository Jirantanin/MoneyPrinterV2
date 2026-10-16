#!/usr/bin/env python3
"""Offline preflight for the local Producer Mode workflow."""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.json"


def configured(value: Any) -> bool:
    return bool(str(value or "").strip())


def main() -> int:
    if not CONFIG_PATH.is_file():
        print(f"[FAIL] Missing local config: {CONFIG_PATH}")
        print("[HINT] Copy config.example.json to config.json and add the keys for your providers.")
        return 1

    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] config.json could not be read: {exc}")
        return 1

    settings = config.get("podcast_settings", {})
    models = settings.get("models", {}) if isinstance(settings, dict) else {}
    if not isinstance(models, dict):
        models = {}

    llm_ready = any(
        (
            configured(config.get("minimax_api_key")),
            configured(config.get("anthropic_api_key")) or configured(os.environ.get("ANTHROPIC_API_KEY")),
            configured(models.get("ollama_model")) or configured(config.get("ollama_model")),
        )
    )
    if llm_ready:
        print("[OK] At least one Producer Mode text model is configured")
    else:
        print("[FAIL] Configure MiniMax/OpenRouter, Claude/Anthropic, or a local Ollama model")

    gemini_key = (
        config.get("gemini_tts_api_key")
        or config.get("nanobanana2_api_key")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    if configured(gemini_key):
        print("[OK] Gemini TTS credential is configured")
    else:
        print("[FAIL] Configure gemini_tts_api_key or GEMINI_API_KEY for Producer Mode narration")

    required_paths = (
        ROOT_DIR / "scripts" / "producer_mode.py",
        ROOT_DIR / "scripts" / "producer_review.py",
        ROOT_DIR / "src" / "producer_contract.py",
        ROOT_DIR / "remotion" / "src" / "Root.tsx",
        ROOT_DIR / "remotion" / "src" / "VideoPodcast.tsx",
    )
    missing = [path for path in required_paths if not path.is_file()]
    if missing:
        for path in missing:
            print(f"[FAIL] Missing Producer Mode file: {path.relative_to(ROOT_DIR)}")
    else:
        print("[OK] Producer Mode and Remotion entry files are present")

    for executable in ("ffmpeg", "node", "npm"):
        if shutil.which(executable):
            print(f"[OK] {executable} is available")
        else:
            print(f"[WARN] {executable} is not on PATH; some production or rendering steps may be unavailable")

    if not llm_ready or not configured(gemini_key) or missing:
        print("[FAIL] Producer Mode preflight found blocking setup issues.")
        return 1

    print("[OK] Local configuration is ready for Producer Mode. Provider credentials were not tested.")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
