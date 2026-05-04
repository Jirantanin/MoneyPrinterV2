---
phase: quick
plan: 260402-n1i
subsystem: podcast-ui
tags: [fastapi, sse, tailwind, web-gui, podcast]
dependency_graph:
  requires: []
  provides: [podcast-web-gui]
  affects: [src/main.py]
tech_stack:
  added: [fastapi, uvicorn, tailwindcss-cdn]
  patterns: [sse-streaming, background-thread-pipeline, module-level-state, stdout-capture]
key_files:
  created:
    - src/podcast_server.py
    - src/podcast_ui.html
  modified:
    - src/main.py
    - requirements.txt
decisions:
  - FastAPI + SSE over WebSockets — simpler, no extra JS library, server-sent events sufficient for unidirectional progress updates
  - Tailwind CDN with inline config — no build step, single HTML file, custom color palette via tailwind.config
  - Module-level dict state — avoids class-level complexity, background threads update shared dict safely for read-heavy SSE polling
  - Stdout capture via sys.stdout swap — captures Podcast method print() output as log events without modifying Podcast.py
  - Episode ID matches Podcast.py naming convention (podcast_{slug}_{YYYYMMDD}) — avoids duplicate directories
metrics:
  duration: 3m
  completed_date: "2026-04-02"
  tasks_completed: 3
  files_created: 2
  files_modified: 2
requirements_satisfied: [GUI-01]
---

# Quick Task 260402-n1i: Podcast Generate UI with Step Progress Summary

**One-liner:** FastAPI + SSE backend with dark Tailwind single-page UI replacing tkinter podcast_gui — real-time 5-step pipeline progress, progressive image gallery, upload button gated on all-steps-done.

## What Was Built

### src/podcast_server.py (391 lines)

FastAPI app on port 8899 with 7 routes:

- `GET /` — serves `podcast_ui.html` via `HTMLResponse`
- `POST /api/generate` — creates episode state, starts `_run_pipeline` background thread, returns `episode_id`
- `GET /api/stream/{episode_id}` — SSE `StreamingResponse` yielding `step_start`, `step_done`, `step_error`, `log`, `complete`/`error` events at 0.5s poll interval with keep-alive comments every 15s
- `GET /api/images/{episode_id}` — scans `episode_dir` for `scene_*.png` + `thumbnail.png`, returns sorted list
- `GET /api/episode/{episode_id}` — full state snapshot (status, steps, scenes, metadata, episode_dir)
- `POST /api/upload/{episode_id}` — calls `podcast.upload()` via `asyncio.to_thread()`
- `GET /static/{episode_id}/{filename}` — serves episode files with path-traversal protection

`_StdoutCapture` class mirrors Podcast method print output to SSE log events without modifying Podcast.py.

`launch_podcast_server()` opens browser after 1.5s delay, starts uvicorn on 127.0.0.1:8899.

### src/podcast_ui.html (566 lines)

Single-file HTML with Tailwind CDN, no build step:

- Dark theme: charcoal (#1e1e2e) body, surface (#313244) cards, custom Tailwind color config
- Topic input + Generate button with Enter key support and disabled states during pipeline
- 5-step pipeline panel: grey circle (pending), yellow CSS spinner with animation (running), green check (done), red X (error)
- Sub-status text under each active step showing captured Podcast print output in real time
- Image gallery: CSS grid with aspect-video cards, images appear progressively via 2s polling, click to open full-size
- Script panel: numbered scene narrations with accent-colored scene numbers, scrollable, appends incrementally
- Metadata panel: title (large font), description (pre-wrap), tags as pill badges — hidden until metadata step done
- Upload button: disabled (opacity-50 cursor-not-allowed) until all 5 steps done, then enables (sky blue)
- Upload result shows clickable YouTube link or inline error message

### src/main.py

Option 5 block: `podcast_gui.launch_podcast_gui` replaced with `podcast_server.launch_podcast_server`. One-line change.

### requirements.txt

Added `fastapi` and `uvicorn[standard]` at end of file.

## Deviations from Plan

None — plan executed exactly as written.

Previous `podcast_gui.py` (tkinter, from an earlier run) remains on disk but is no longer imported anywhere.

## Known Stubs

None. Upload button calls the real `podcast.upload()` method. All pipeline steps invoke real Podcast methods.

## Commits

| Task | Commit  | Description |
|------|---------|-------------|
| Task 1 | 0e153cb | feat(260402-n1i): create podcast_server.py FastAPI backend with SSE streaming |
| Task 2 | 5dbcb24 | feat(260402-n1i): create podcast_ui.html dark Tailwind UI with SSE and image polling |
| Task 3 | 678446b | feat(260402-n1i): wire podcast_server into main menu option 5, add fastapi deps |

## Self-Check: PASSED

Files exist:
- FOUND: src/podcast_server.py
- FOUND: src/podcast_ui.html

Commits exist:
- FOUND: 0e153cb
- FOUND: 5dbcb24
- FOUND: 678446b
