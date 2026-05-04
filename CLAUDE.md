# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

MoneyPrinterV2 in this repo is primarily a Python 3.12 Web UI Studio backed by FastAPI.
The main active workflows are:
1. YouTube Shorts generation and upload
2. YouTube Podcast generation and upload
3. Retired Twitter, Affiliate Marketing, and Outreach modules kept only under `src/legacy/classes/` for reference

There is no enforced test suite, CI pipeline, or linting config.

## Running the Application

```bash
# First-time setup
cp config.example.json config.json
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Optional quick setup helper
bash scripts/setup_local.sh

# Preflight check
python scripts/preflight_local.py

# Run Studio
python -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
```

Run the project from the repo root. `src/main.py` still exists as a legacy launcher and uses bare module imports.

## Architecture

### Entry Points
- `src/podcast_server.py` - primary FastAPI Studio backend
- `src/main.py` - legacy interactive CLI launcher
- `src/cron.py` - scheduled headless runner for older automation paths

### Key Modules
- `src/podcast_server.py` - Studio backend, SSE progress streaming, upload endpoints, settings endpoints
- `src/podcast_ui.html` - shell template (CSS, layout, tab nav); injects `{{PODCAST_COMPONENT}}` and `{{SHORTS_COMPONENT}}` placeholders server-side
- `src/ui/` - component partials and JS modules assembled into the shell:
  - `podcast_component.html` / `shorts_component.html` — tab markup (HTML only)
  - `shared.js` — tab switching logic, loaded in shell `<head>`
  - `podcast-main.js`, `podcast-dialog.js`, `podcast-settings.js`, `podcast-render.js`, `podcast-api.js` — podcast JS by concern
  - `shorts-main.js`, `shorts-render.js`, `shorts-api.js` — shorts JS by concern
  - Static assets served at `/ui-assets/{filename}` via a route in `podcast_server.py`
- `src/classes/Podcast.py` - long-form podcast pipeline
- `src/classes/YouTube.py` - Shorts pipeline and YouTube upload helpers
- `src/classes/Tts.py` - TTS dispatch by config
- `src/legacy/classes/` - retired non-Studio modules kept as reference only
- `src/llm_provider.py` - MiniMax/OpenRouter primary text generation with Ollama fallback
- `src/config.py` - config loading and settings helpers
- `src/cache.py` - JSON persistence in `.mp/`
- `remotion/` - rendering layer for Shorts and related video work

### Provider Pattern
- LLM: MiniMax via OpenRouter when configured, otherwise Ollama fallback
- Image generation: Nano Banana 2 / Gemini image API
- TTS: `tts_provider`, default `edge`
- STT: `local_whisper` or `third_party_assemblyai`

### Data Storage
Persistent state lives in `.mp/` at the project root. This directory also acts as scratch space for generated assets.

## Configuration

All config lives in `config.json` at the repo root. Start from `config.example.json`.
See `docs/Configuration.md` for the active runtime settings used by the Studio.

Key external dependencies:
- ImageMagick for parts of local media processing
- Ollama for local LLM fallback
- Nano Banana 2 / Gemini image API for image generation
- YouTube OAuth client files for upload
- Optional Go toolchain only for the legacy Outreach module

## Web UI Notes

Default local URL: `http://127.0.0.1:8899`

Windows launch shortcut:

```bash
py -c "import sys; sys.path.insert(0, 'src'); from podcast_server import launch_podcast_server; launch_podcast_server()"
```

## Windows Environment Notes
- Prefer `py` if the Microsoft Store alias interferes with `python`
- `npx` on Windows may require `shell: true` when called from Python subprocesses

## Contributing

PRs go against `main`. Keep one feature or fix per PR and use clear titles and descriptions.
