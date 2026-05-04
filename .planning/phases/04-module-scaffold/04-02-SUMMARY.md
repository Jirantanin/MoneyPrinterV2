---
phase: 04-module-scaffold
plan: 02
subsystem: ui
tags: [python, config, menu, podcast]

# Dependency graph
requires:
  - phase: 04-01
    provides: Podcast.py stub class with four-step interface and NotImplementedError stubs
provides:
  - "constants.py OPTIONS list with Podcast entry at index 4 (Quit shifted to index 5)"
  - "config.py exports get_podcast_narrator() and get_podcast_style_prompt() getters"
  - "config.example.json podcast_narrator object and podcast_style_prompt defaults"
  - "main.py elif user_input==5 Podcast dispatch block with NotImplementedError catch"
affects: [05-script-generation, 06-scene-assets, 07-ffmpeg-render, 08-thumbnail-upload]

# Tech tracking
tech-stack:
  added: []
  patterns: ["json.load(file).get() pattern for optional config keys with defaults"]

key-files:
  created: []
  modified:
    - src/config.py
    - config.example.json
    - src/constants.py
    - src/main.py

key-decisions:
  - "Podcast dispatch uses try/except NotImplementedError — graceful degradation instead of crash traceback"
  - "config getters use .get() with full default dict/string — safe when podcast_narrator key absent from config.json"

patterns-established:
  - "Podcast getter pattern: json.load(file).get('podcast_narrator', {...default...}) matching all other optional getters"
  - "Menu dispatch pattern: elif user_input == N block identical style to YouTube/Twitter/AFM/Outreach blocks"

requirements-completed: [MOD-01, MOD-03]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 4 Plan 02: Module Scaffold - Menu Wiring Summary

**Podcast option wired into main menu (option 5 of 6) with config getters get_podcast_narrator() and get_podcast_style_prompt() added to config.py and config.example.json**

## Performance

- **Duration:** 5 min
- **Completed:** 2026-04-01
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `get_podcast_narrator()` and `get_podcast_style_prompt()` to `src/config.py` following the existing `json.load(file).get()` getter pattern with safe defaults
- Added `podcast_narrator` object (name, persona, tts_voice=en-GB-RyanNeural, tts_rate=-20%) and `podcast_style_prompt` string to `config.example.json`
- Inserted "Podcast" at index 4 in `constants.py` OPTIONS list, shifting "Quit" to index 5 (list length 6)
- Added `from classes.Podcast import Podcast` import and `elif user_input == 5` dispatch block to `main.py` with `NotImplementedError` catch and Quit shifted to `elif user_input == 6`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add podcast config keys and getters** - `fc3ac45` (feat)
2. **Task 2: Wire Podcast into constants and main menu** - `d705de8` (feat)

## Files Created/Modified
- `src/config.py` - Added get_podcast_narrator() and get_podcast_style_prompt() at end of file
- `config.example.json` - Added podcast_narrator object and podcast_style_prompt key
- `src/constants.py` - Inserted "Podcast" at index 4 in OPTIONS list
- `src/main.py` - Added Podcast import, elif dispatch at 5, NotImplementedError catch, Quit shifted to 6

## Decisions Made
- Podcast dispatch uses try/except NotImplementedError block — graceful "Pipeline step not yet implemented" message instead of crash traceback
- Config getters use json.load(file).get() pattern with full default dicts/strings matching all existing optional getters in config.py

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs
- `src/classes/Podcast.py` — `generate_script()`, `generate_assets()`, `render()`, `upload()` all raise `NotImplementedError("Phase N: not yet implemented")`. These are intentional stubs per MOD-02 design; Phases 5-8 will implement them.

## Next Phase Readiness
- Phase 04 module scaffold complete: Podcast.py class created (Plan 01) and wired into menu/config (Plan 02)
- Phase 05 (script-generation) can import Podcast and call generate_script() — will replace the NotImplementedError stub
- config.py getters get_podcast_narrator() and get_podcast_style_prompt() are ready for use in all downstream phases

---
*Phase: 04-module-scaffold*
*Completed: 2026-04-01*
