# Milestones

## v2.0 Video Podcast Module (Shipped: 2026-04-05)

**Phases completed:** 5 phases, 9 plans, 12 tasks

**Key accomplishments:**

- Podcast pipeline class with five-method interface (generate_script/generate_assets/render/upload/run) and phase-labeled NotImplementedError stubs, standalone from YouTube.py
- Podcast option wired into main menu (option 5 of 6) with config getters get_podcast_narrator() and get_podcast_style_prompt() added to config.py and config.example.json
- Standalone Gemini image generation module with module-level 7s rate limit, 429 retry, and caller-controlled output path
- T1 — Tts.synthesize() signature + body (3 targeted edits):
- Podcast.generate_assets() implemented with 14-scene image+audio pipeline, resumability, and style lock; YouTube.py image generation delegated to image_provider removing duplicate Gemini logic and _last_image_time
- FFmpeg two-pass render pipeline: per-scene libx264 clips with zoompan Ken Burns motion, concatenated to final.mp4 via stream-copy concat demuxer
- LLM-powered YouTube metadata (title/description/tags) and Gemini dark-comic thumbnail for Podcast pipeline, with JSON fallback parse and resumability
- Podcast.upload() replaces NotImplementedError stub with YouTube API v3 resumable upload, Education category (27), unlisted privacy, and thumbnails().set() — completing the full Podcast pipeline

---

## v1.0 Video Engagement Upgrade (Shipped: 2026-03-31)

**Phases completed:** 3 phases, 3 plans, 7 tasks

**Key accomplishments:**

- edge-tts Communicate wired with configurable rate= kwarg; get_tts_rate() getter added with "+20%" default for energetic Shorts pacing
- One-liner:

---
