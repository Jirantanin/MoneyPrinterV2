---
phase: 04-module-scaffold
plan: 01
subsystem: api
tags: [python, podcast, stub, pipeline]

# Dependency graph
requires: []
provides:
  - "src/classes/Podcast.py — Podcast class with four-step pipeline interface (generate_script, generate_assets, render, upload, run)"
affects: [05-script-generation, 06-scene-assets, 07-ffmpeg-render, 08-thumbnail-upload, 04-02-main-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Standalone pipeline class pattern — Podcast.py mirrors YouTube.py structure but does NOT extend it"
    - "NotImplementedError stubs labeled by downstream phase number for easy grep-based tracking"
    - "Forward-compatible imports — config getters imported before they exist in config.py"

key-files:
  created:
    - src/classes/Podcast.py
  modified: []

key-decisions:
  - "Podcast.py is standalone (no YouTube.py inheritance) — isolates Podcast pipeline from Shorts pipeline per MOD-02 and D-01/D-02"
  - "NotImplementedError messages labeled 'Phase N: not yet implemented' so downstream agents can grep for remaining stubs"
  - "get_podcast_narrator and get_podcast_style_prompt imported forward-compatibly — Plan 02 adds them to config.py"

patterns-established:
  - "Phase-labeled stubs: raise NotImplementedError('Phase N: not yet implemented') — phases 5-8 replace one stub each"
  - "run() contains zero logic — it only calls the four step methods in sequence"

requirements-completed: [MOD-02]

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 4 Plan 01: Module Scaffold — Podcast.py Stub Summary

**Podcast pipeline class with five-method interface (generate_script/generate_assets/render/upload/run) and phase-labeled NotImplementedError stubs, standalone from YouTube.py**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-01T04:29:38Z
- **Completed:** 2026-04-01T04:30:39Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `src/classes/Podcast.py` as a standalone class (no YouTube.py import)
- All four step methods raise `NotImplementedError` with phase-labeled messages (Phase 5-8)
- `run()` calls the four steps in sequence with no additional logic
- Forward-compatible imports for `get_podcast_narrator` and `get_podcast_style_prompt` (added by Plan 02)
- Python syntax verified clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Podcast.py stub class** - `3a7fe15` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `src/classes/Podcast.py` — Podcast pipeline class: five-method interface with NotImplementedError stubs for phases 5-8

## Decisions Made
- Imported `get_podcast_narrator` and `get_podcast_style_prompt` even though they don't exist in `config.py` yet — Plan 02 adds them; importing now ensures the class is wired correctly and import errors surface at instantiation time rather than method-call time.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `py -c "import ast; ast.parse(open('src/classes/Podcast.py').read())"` failed with `UnicodeDecodeError` (cp874 encoding on Windows). Fixed by adding `encoding='utf-8'` to the open call in the verification command. File content was correct; only the verification invocation needed adjustment.

## Known Stubs

The following stubs are intentional — each is a Phase-N placeholder by design:

| File | Line | Stub | Reason |
|------|------|------|--------|
| src/classes/Podcast.py | 33 | `raise NotImplementedError("Phase 5: not yet implemented")` | generate_script filled in Phase 5 |
| src/classes/Podcast.py | 41 | `raise NotImplementedError("Phase 6: not yet implemented")` | generate_assets filled in Phase 6 |
| src/classes/Podcast.py | 49 | `raise NotImplementedError("Phase 7: not yet implemented")` | render filled in Phase 7 |
| src/classes/Podcast.py | 57 | `raise NotImplementedError("Phase 8: not yet implemented")` | upload filled in Phase 8 |

These stubs do NOT prevent Plan 01's goal (define class contract). Plan 02 can safely import `Podcast` without triggering any stub.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `src/classes/Podcast.py` is importable and defines the class contract for phases 5-8
- Plan 02 (main.py menu integration) can now `from classes.Podcast import Podcast` without error
- Plans 02 must also add `get_podcast_narrator` and `get_podcast_style_prompt` to `src/config.py` before `Podcast()` can be instantiated

---
*Phase: 04-module-scaffold*
*Completed: 2026-04-01*
