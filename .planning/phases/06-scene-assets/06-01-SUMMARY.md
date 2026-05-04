---
phase: 06-scene-assets
plan: "01"
subsystem: image-generation
tags: [gemini, requests, rate-limiting, image-provider, nanobanana2]

# Dependency graph
requires: []
provides:
  - "src/image_provider.py: standalone generate_image(prompt, output_path) with 7s rate limit and 429 retry"
affects: [Podcast.py, YouTube.py, thumbnail-gen]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level float variable for cross-call rate limiting (no class instance required)"
    - "Caller-controlled output_path pattern: image path UUID decided by caller, not by image provider"
    - "429 retry: single sleep(15) + one retry, return None on second 429"

key-files:
  created:
    - src/image_provider.py
  modified: []

key-decisions:
  - "output_path is passed in by caller — image_provider.py never generates UUIDs or references run_dir"
  - "Module-level _last_image_time float enforces 7s rate limit across all callers sharing the same process"
  - "429 handling: 15s sleep + one retry is the canonical behavior extracted from YouTube.py"

patterns-established:
  - "Caller controls path: generate_image(prompt, output_path) writes to exactly where the caller says"
  - "Module-level state for rate limiting: avoids needing class instance, works across Podcast/YouTube/Thumbnail callers"

requirements-completed: [IMG-01, IMG-02, IMG-03]

# Metrics
duration: 8min
completed: 2026-04-01
---

# Phase 6 Plan 01: Create src/image_provider.py Summary

**Standalone Gemini image generation module with module-level 7s rate limit, 429 retry, and caller-controlled output path**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-01T12:46:00Z
- **Completed:** 2026-04-01T12:54:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Extracted Gemini image generation from YouTube.py into a reusable standalone module
- `generate_image(prompt, output_path)` is the single public API — callers control path, no UUID generation inside
- Module-level `_last_image_time` enforces 7-second rate limit across all callers sharing the same Python process
- 429 handling: 15s sleep + one retry; second 429 returns None cleanly

## Task Commits

1. **T1: Create src/image_provider.py with generate_image() and module-level rate limiting** - `1dd12d5` (feat)

## Files Created/Modified

- `src/image_provider.py` — Standalone image generation module with `generate_image`, `_generate_image_nanobanana2`, and `_persist_image` functions

## Decisions Made

- Output path is passed in by caller — no UUID generation, no `self.run_dir` inside `image_provider.py`; this enables Podcast.py, YouTube.py, and thumbnail gen to each manage their own path schemes
- Module-level `_last_image_time: float = 0.0` rather than an instance variable — ensures the 7s rate limit is shared across all callers in the same process

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The Python environment outside the project venv was missing `srt_equalizer` (imported at top of `config.py`). Import verification was run with `source venv/Scripts/activate` and succeeded. This is a pre-existing environment setup requirement, not a code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `src/image_provider.py` is ready for use by Podcast.py (Phase 6 subsequent plans) and YouTube.py refactor
- Callers import: `from image_provider import generate_image`
- No blockers

## Self-Check: PASSED

- src/image_provider.py: FOUND
- 06-01-SUMMARY.md: FOUND
- commit 1dd12d5: FOUND

---
*Phase: 06-scene-assets*
*Completed: 2026-04-01*
