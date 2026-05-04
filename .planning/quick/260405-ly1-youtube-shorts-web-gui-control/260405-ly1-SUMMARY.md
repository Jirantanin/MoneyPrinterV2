---
phase: quick
plan: 260405-ly1
subsystem: shorts-gui
tags: [fastapi, sse, tailwind, youtube-shorts, web-ui]
dependency_graph:
  requires: [src/classes/YouTube.py, src/cache.py, src/config.py, src/classes/Tts.py]
  provides: [shorts_server.py, shorts_ui.html, main.py option 5]
  affects: [src/main.py, src/constants.py]
tech_stack:
  added: [FastAPI, uvicorn, SSE streaming]
  patterns: [podcast_server.py mirroring, background thread pipeline, cursor-based SSE, _StdoutCapture]
key_files:
  created: [src/shorts_server.py, src/shorts_ui.html]
  modified: [src/main.py, src/constants.py]
decisions:
  - Used worktree's older YouTube.py constructor signature — no fp_profile_path, takes niche/language/run_dir directly
  - Subtitles step is non-fatal (logs warning, sets srt_path=None) to avoid blocking render on Whisper failures
  - Image gallery uses SSE log events to track per-image progress (no separate /api/images endpoint needed for Shorts)
  - Port 8898 (podcast uses 8899) to allow both servers to run simultaneously
  - Publish options: public / unlisted (Shorts doesn't need schedule like Podcast)
metrics:
  duration_seconds: 330
  completed_date: "2026-04-05"
  tasks_completed: 3
  files_created: 2
  files_modified: 2
---

# Quick Task 260405-ly1: YouTube Shorts Web GUI Summary

**One-liner:** FastAPI + SSE web GUI for YouTube Shorts pipeline (topic→script→hook→metadata→images→TTS→subtitles→render) with Tailwind dark UI, account selection, step mode, video preview, and YouTube upload.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create shorts_server.py — FastAPI backend | bbafd66 | src/shorts_server.py |
| 2 | Create shorts_ui.html — Tailwind dark UI | 82c14f2 | src/shorts_ui.html |
| 3 | Wire into main.py menu | 79d9b1d | src/main.py, src/constants.py |

## What Was Built

### shorts_server.py
FastAPI backend on port 8898 mirroring `podcast_server.py` architecture:
- **10 routes:** GET `/`, GET `/api/accounts`, POST `/api/generate`, GET `/api/stream/{short_id}`, GET `/api/episode/{short_id}`, POST `/api/approve/{short_id}`, POST `/api/cancel/{short_id}`, POST `/api/upload/{short_id}`, GET `/api/shorts`, GET `/static/{short_id}/{filename}`
- **9-step pipeline** in background thread: Generate Topic → Script → Hook → Metadata → Image Prompts → Images → TTS → Subtitles → Render Video
- **SSE streaming** via cursor-based event queue (0.5s poll, keep-alive every 15s)
- **_StdoutCapture** redirects print() output from YouTube class as SSE log events
- **Pillow ANTIALIAS shim** + selenium mock applied before YouTube class instantiation
- **Per-image SSE events** during step 5 (e.g., "Image 3/6: prompt...")
- **launch_shorts_server()** opens browser at localhost:8898

### shorts_ui.html
Single-file Tailwind dark UI (Catppuccin Mocha palette, identical to podcast_ui.html):
- Account dropdown populated from `/api/accounts` with niche/language auto-fill
- Topic, niche, language inputs; auto/step mode toggle
- 9-step progress tracker with pending/running/done/error states
- Approve banner for step-by-step mode
- Log output panel (scrollable monospace)
- Portrait 9:16 video preview player (correct Shorts aspect ratio)
- Metadata panel (title, description) after step 3 completes
- Image gallery with lazy-loaded thumbnails
- Upload to YouTube button with public/unlisted options
- Recent shorts listing from `.mp/` directories

### main.py + constants.py
- `OPTIONS` now includes "YouTube Shorts GUI" at index 4 (option 5), Quit shifts to option 6
- `main()` option 5 calls `launch_shorts_server()` from `shorts_server`

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Intentional Adaptations

**1. [Adaptation] Worktree branch has older YouTube.py (no fp_profile_path)**
- The worktree is on an older branch; the modern `YouTube.__init__` takes `(account_uuid, account_nickname, niche, language, run_dir)` — no `fp_profile_path`
- `shorts_server.py` uses the modern signature (matching the main repo's YouTube.py)
- This is correct for the merge target

**2. [Adaptation] Subtitles step is non-fatal**
- Plan spec said to handle Whisper failures gracefully
- `_gen_subtitles()` wraps `generate_subtitles()` in try/except, sets `youtube.srt_path = None` on failure
- Render still proceeds (Remotion handles missing SRT gracefully)

**3. [Adaptation] No separate /api/images endpoint**
- Podcast has `/api/images/{episode_id}` using glob on scene_*.png
- Shorts images are UUID-named .png files — no consistent glob pattern
- Image progress shown via SSE log events (per-image messages during step 5)
- Gallery images loaded via direct `/static/{short_id}/{filename}` after SSE logs the filenames

**4. [Adaptation] Publish options simplified**
- Podcast has public/scheduled modes with datetime picker
- Shorts upload uses `youtube.upload_video()` which always sets `privacyStatus: public`
- UI provides public/unlisted radio (unlisted passed for future use, consistent with YouTube API body)

## Known Stubs

None — all pipeline steps wire to real YouTube class methods.

## Self-Check

Files exist:
- src/shorts_server.py: YES
- src/shorts_ui.html: YES
- src/main.py: YES (modified)
- src/constants.py: YES (modified)

Commits exist:
- bbafd66 (shorts_server.py): YES
- 82c14f2 (shorts_ui.html): YES
- 79d9b1d (main.py + constants.py): YES
