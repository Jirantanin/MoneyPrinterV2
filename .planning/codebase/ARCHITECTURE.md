# ARCHITECTURE.md — System Architecture

## Pattern
**CLI monolith** with class-based pipeline objects. No web server, no REST API, no message queue. All execution is synchronous and sequential within each pipeline.

## Entry Points

| File | Role |
|------|------|
| `src/main.py` | Interactive menu loop. `__main__` block: setup → model selection → `while True: main()`. |
| `src/cron.py` | Headless subprocess runner. Called as `python src/cron.py <platform> <account_uuid> <model>`. |

## Layers

```
┌─────────────────────────────────────────┐
│  CLI Interface (main.py / cron.py)      │  Input: stdin / sys.argv
├─────────────────────────────────────────┤
│  Pipeline Classes (src/classes/)        │  YouTube, Twitter, AFM, Outreach
├─────────────────────────────────────────┤
│  Provider Modules (src/)               │  llm_provider, Tts, topic_discovery
├─────────────────────────────────────────┤
│  Infrastructure (src/)                  │  config, cache, utils, status, constants
├─────────────────────────────────────────┤
│  External Services                      │  Ollama, Gemini API, YouTube API, Selenium
├─────────────────────────────────────────┤
│  Remotion Renderer (remotion/)          │  Node.js subprocess for final video render
└─────────────────────────────────────────┘
```

## YouTube Pipeline (most complex)
`YouTube.generate_video(tts)` → `YouTube.upload_video()`

```
topic → script → metadata (title/desc/tags)
     → image_prompts → generate_images (Gemini API)
     → TTS audio (KittenTTS)
     → STT subtitles (Whisper / AssemblyAI)
     → stage assets to remotion/public/assets/
     → combine_remotion() → subprocess Node.js render
     → upload_video() → YouTube API v3
```

`combine_moviepy()` exists as fallback but is inactive.

## CRON Scheduler
- Uses Python `schedule` library (in-process, not OS cron)
- Scheduled job: `subprocess.run(["python", "src/cron.py", platform, account_id, model])`
- Jobs set up interactively from `main.py` menu, run in same process

## Data Flow
- All persistent state → `.mp/` JSON files (accounts, videos, posts, products)
- Temporary files (WAV, PNG, SRT, MP4) → `.mp/` or timestamped run dir `.mp/YYYYMMDD_HHMMSS/`
- Remotion assets → `remotion/public/assets/` (staged before render, cleaned after)
- `rem_temp_files()` called on each run to clean non-JSON files from `.mp/`

## Subprocess Pattern
- Remotion render: `subprocess.run(["node", "scripts/render.mjs", props_path])`
- Google Maps scraper: Go binary downloaded and run via subprocess
- CRON workers: `subprocess.run(["python", "src/cron.py", ...])`
- Windows note: `npx` requires `shell=True` (resolves to `npx.cmd`)
