---
phase: quick
plan: 260405-mae
subsystem: web-gui
tags: [merge, tabs, fastapi, shorts, podcast, ui]
dependency_graph:
  requires: [260405-ly1-youtube-shorts-web-gui-control, 260402-n1i-podcast-generate-ui-with-step-progress-i]
  provides: [unified-studio-ui-port-8899]
  affects: [src/podcast_server.py, src/podcast_ui.html, src/main.py, src/constants.py]
tech_stack:
  added: []
  patterns: [tabbed-SPA, namespaced-JS, route-prefix-migration]
key_files:
  created: []
  modified:
    - src/podcast_server.py
    - src/podcast_ui.html
    - src/main.py
    - src/constants.py
  deleted:
    - src/shorts_server.py
    - src/shorts_ui.html
decisions:
  - Shorts pipeline state vars (shorts, short_events, short_approvals) added as module-level dicts in podcast_server.py — same pattern as episode dicts
  - Shorts JS fully namespaced with shorts_ prefix (functions and variables) and shorts- prefix (element IDs) to prevent collision with podcast globals
  - Tab switching is lazy-init: Shorts tab only calls loadAccounts/loadRecentShorts on first click via shorts_initialized flag
  - Deleted shorts_server.py and shorts_ui.html after migration — no orphaned server
metrics:
  duration: ~18 minutes
  completed_date: "2026-04-05"
  tasks_completed: 3
  files_modified: 4
  files_deleted: 2
---

# Quick Task 260405-mae: Merge Shorts and Podcast into Single Web App — Summary

**One-liner:** Merged YouTube Shorts GUI (shorts_server.py + shorts_ui.html) into the Podcast Studio (podcast_server.py + podcast_ui.html) as a single tabbed FastAPI app on port 8899, with fully namespaced JS to prevent variable collisions.

## Objective Achieved

Single server on port 8899 now serves both Podcast and YouTube Shorts functionality via a tab-switching UI. `main.py` option 5 launches the unified Studio. Option 6 is now Quit. `shorts_server.py` and `shorts_ui.html` are deleted.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Migrate Shorts routes into podcast_server.py, update main.py + constants.py | 9545cba |
| 2 | Add tab navigation to podcast_ui.html, embed Shorts UI with namespaced JS | 9fa16f9 |
| 3 | Delete shorts_server.py and shorts_ui.html | bc54c8b |

## What Changed

### podcast_server.py
- Renamed FastAPI app title from "Podcast Generator" to "MPV2 Studio"
- Added module-level `shorts`, `short_events`, `short_approvals` dicts
- Added `_SHORTS_STEPS` constant (9 steps)
- Added `_ShortsStdoutCapture`, `_push_shorts_event`, `_wait_for_shorts_approval`, `_run_shorts_step`, `_run_shorts_pipeline`
- Added 9 Shorts routes under `/shorts/` prefix: `GET /shorts/api/accounts`, `POST /shorts/api/generate`, `GET /shorts/api/stream/{short_id}`, `GET /shorts/api/episode/{short_id}`, `POST /shorts/api/approve/{short_id}`, `POST /shorts/api/cancel/{short_id}`, `POST /shorts/api/upload/{short_id}`, `GET /shorts/api/shorts`, `GET /shorts/static/{short_id}/{filename}`

### podcast_ui.html
- Title/header updated to "MPV2 Studio"
- Tab nav bar added (Podcast | YouTube Shorts) with `switchTab()` function
- Podcast content wrapped in `div#tab-podcast`
- Full Shorts UI added in `div#tab-shorts` (hidden by default)
- All Shorts HTML element IDs prefixed with `shorts-`
- All Shorts JS functions prefixed with `shorts_`, variables with `shorts_`
- All Shorts API fetch calls use `/shorts/api/` prefix
- All Shorts static file URLs use `/shorts/static/` prefix
- Lazy init: `shorts_initialized` flag prevents API calls until tab is first opened

### main.py
- Removed `from shorts_server import launch_shorts_server`
- Removed `elif user_input == 6` (Shorts GUI launch)
- Changed option 5 message from "Launching Podcast Generator GUI..." to "Launching Studio..."
- Changed `elif user_input == 7` (Quit) to `elif user_input == 6`

### constants.py
- Removed "YouTube Shorts GUI" entry
- Renamed "Podcast" to "Studio"
- OPTIONS now has 6 items: YouTube Shorts Automation, Twitter Bot, Affiliate Marketing, Outreach, Studio, Quit

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All Shorts functionality is wired to `/shorts/api/*` routes which are live on the unified server.

## Self-Check: PASSED

- `src/podcast_server.py` exists with all shorts routes: FOUND
- `src/podcast_ui.html` has tab-podcast, tab-shorts, switchTab, /shorts/api/generate: FOUND
- `src/shorts_server.py`: confirmed deleted
- `src/shorts_ui.html`: confirmed deleted
- Commits 9545cba, 9fa16f9, bc54c8b: FOUND
