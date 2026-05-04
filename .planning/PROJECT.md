# MoneyPrinterV2 — Project

## What This Is

MoneyPrinterV2 is a Python CLI tool that auto-generates and uploads YouTube content — both **YouTube Shorts** (topic → script → images → TTS → Remotion render → YouTube API upload) and **long-form Podcast episodes** (topic → 14-scene act-by-act script → per-scene Gemini images + edge-tts audio → FFmpeg Ken Burns render → YouTube API upload). v2.0 shipped a full Podcast pipeline with a FastAPI web GUI (unified Shorts+Podcast studio on port 8899) controlled via SSE-streamed progress, step-by-step approval, and YouTube scheduling.

## Core Value

Every generated clip must stop the scroll within the first 3 seconds — hook + motion + voice must work together to retain viewers.

## Current State — v2.0 SHIPPED (2026-04-05)

**Shipped:** Full Podcast pipeline + unified web Studio (Shorts + Podcast tabs)

- `src/classes/Podcast.py` — standalone pipeline class (generate_script → generate_assets → render → upload)
- `src/image_provider.py` — standalone Gemini image gen module (7s rate limit, 429 retry, resumable)
- `src/podcast_server.py` — FastAPI server port 8899, Podcast + Shorts routes, SSE streaming
- `src/podcast_ui.html` — single-file Tailwind dark Studio UI (Podcast tab + YouTube Shorts tab)
- 5 phases, 9 plans, ~7,400 LOC Python

**Tech stack:** Python 3.12, FastAPI, edge-tts, Ollama + MiniMax/OpenRouter (LLM), Remotion 4.0, FFmpeg, Gemini API (images), YouTube API v3

## Requirements

### Validated

- ✓ End-to-end YouTube Shorts pipeline (topic → script → images → TTS → subtitles → Remotion → upload) — existing
- ✓ LLM script generation via Ollama — existing
- ✓ Image generation via Gemini (Nano Banana 2) — existing
- ✓ TTS narration via edge-tts — existing
- ✓ Remotion video renderer (1080×1920) — existing
- ✓ YouTube API v3 upload — existing
- ✓ **TTS prosody improvements** — configurable speaking rate via `tts_rate` config key — v1.0
- ✓ **Hook generation** — LLM-selected opening hook prepended before TTS — v1.0
- ✓ **Ken Burns effect** — 4-direction cycle on every image in Remotion — v1.0
- ✓ **Zoom/push scene transitions** — slide-push via @remotion/transitions — v1.0
- ✓ **Podcast class scaffold** — standalone `Podcast.py` with four-step pipeline interface — v2.0 Phase 4
- ✓ **Podcast config keys** — `podcast_narrator` + `podcast_style_prompt` in config — v2.0 Phase 4
- ✓ **Script generation pipeline** — act-by-act 14-scene with narrator persona + running summaries — v2.0 Phase 5
- ✓ **Gemini image module** — `image_provider.py` with rate limit + 429 retry — v2.0 Phase 6
- ✓ **TTS voice/rate override** — `Tts.synthesize(voice, rate)` params — v2.0 Phase 6
- ✓ **Podcast.generate_assets()** — 14-scene image+audio pipeline, resumable — v2.0 Phase 6
- ✓ **FFmpeg render pipeline** — zoompan Ken Burns per-scene clips + concat to final.mp4 — v2.0 Phase 7
- ✓ **Podcast metadata + thumbnail** — LLM title/description/tags + Gemini dark-comic thumbnail — v2.0 Phase 8
- ✓ **Podcast.upload()** — YouTube API v3 resumable upload + thumbnails().set() — v2.0 Phase 8
- ✓ **Web Studio GUI** — FastAPI + SSE + Tailwind, Podcast+Shorts unified on port 8899 — v2.0 Quick Tasks

### Active (v3.0 candidates)

- [ ] Multi-channel support — separate OAuth tokens per YouTube channel
- [ ] Podcast series management — multiple named series with own narrator persona
- [ ] Auto-scheduling — cron-based episode generation and upload
- [ ] Shorts quality improvements — better topic discovery, engagement analytics
- [ ] SRT subtitles burned into Podcast video via FFmpeg

### Out of Scope

- Switching TTS to ElevenLabs — stay on edge-tts, no new paid API keys
- Dynamic/animated subtitles (word highlight, bounce) — Ken Burns + hook covers motion
- Thai-language podcast — current pipeline targets English narrator
- Twitter / AFM / Outreach improvements — unrelated pipelines
- Remotion for Podcast render — FFmpeg chosen for long-form performance
- Per-scene transition effects (slide/push) in Podcast — FFmpeg concat with Ken Burns sufficient

## Context

- **v1.0:** 3 phases, 3 plans, 7 tasks, ~6,500 LOC changes across 32 files (shipped 2026-03-31)
- **v2.0:** 5 phases, 9 plans, 13,211 insertions / 3,216 deletions across 81 files (shipped 2026-04-05)
- **Key discovery (v1.0):** edge-tts `pitch=` kwarg silently ignored since v6.0.3 — only `rate=` works
- **Key discovery (v1.0):** `@remotion/transitions` must be installed separately; `TransitionSeries` shortens total duration by `(N-1) * transitionFrames`
- **Key discovery (v2.0):** FFmpeg on Windows requires forward-slash paths in concat_list.txt; backslashes silently fail
- **Key discovery (v2.0):** MiniMax/OpenRouter added as primary LLM with Ollama fallback — improves script quality significantly

## Constraints

- **Tech stack:** Remotion for Shorts visual effects; FFmpeg for Podcast render
- **TTS provider:** Stay on edge-tts — no new paid API keys required
- **LLM:** MiniMax via OpenRouter (primary) → Ollama local (fallback)
- **Platform:** Windows 10 with bash shell; Node subprocess needs `shell=True` for npx
- **Port:** Web Studio on 8899; single server for all web workflows

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ken Burns in Remotion (not Python/Pillow) | Remotion controls timing per frame; Python can't sync motion with audio | ✓ Shipped v1.0 |
| Hook selected by LLM (not hardcoded templates) | LLM can match tone/style to topic better than rules | ✓ Shipped v1.0 |
| edge-tts prosody via rate= kwarg only | pitch= silently ignored since v6.0.3; rate= confirmed working | ✓ Shipped v1.0 |
| generate_text_structured() in llm_provider.py | Keeps _client() private; YouTube.py calls public wrapper | ✓ Shipped v1.0 |
| Podcast.py standalone (no YouTube.py inheritance) | Avoid entanglement, protect Shorts pipeline | ✓ Shipped v2.0 |
| FFmpeg render for Podcast (not Remotion) | Better performance for long-form 8-10 min output | ✓ Shipped v2.0 |
| Act-by-act script generation with running summary | Avoids Ollama context overflow for long scripts | ✓ Shipped v2.0 |
| Fixed 14-scene structure: intro(1)+act(4×3)+outro(1) | Predictable duration ≈ 8-10 min | ✓ Shipped v2.0 |
| image_provider.py module-level rate limit | Shared across Podcast + YouTube in same process | ✓ Shipped v2.0 |
| Unified Studio on port 8899 (Podcast + Shorts tabs) | Single launch point, consistent UX | ✓ Shipped v2.0 |
| MiniMax/OpenRouter as primary LLM | Better quality output; Ollama retained as fallback | ✓ Shipped v2.0 |

---
*Last updated: 2026-04-05 after v2.0 milestone — Video Podcast Module shipped*
