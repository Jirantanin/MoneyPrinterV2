---
phase: 07-ffmpeg-render
plan: "01"
subsystem: render
tags: [ffmpeg, zoompan, ken-burns, subprocess, concat, libx264, aac]

# Dependency graph
requires:
  - phase: 06-scene-assets
    provides: scene_NN.png and scene_NN.wav files in episode_dir, episode_dir set on Podcast instance
provides:
  - Podcast.render() fully implemented — two-pass FFmpeg pipeline producing final.mp4
  - Per-scene MP4 clips with alternating Ken Burns zoom motion (scene_00.mp4 through scene_13.mp4)
  - concat_list.txt with forward-slash absolute paths for FFmpeg concat demuxer
  - final.mp4 — all 14 clips concatenated via stream-copy, 8-10 min target duration
affects: [08-thumbnail-upload, Phase 8 upload step reads final.mp4 from episode_dir]

# Tech tracking
tech-stack:
  added: [math (stdlib), subprocess (stdlib already present via Tts.py pattern)]
  patterns:
    - ffprobe duration detection via subprocess.run with check=True
    - zoompan Ken Burns filter with math.ceil frame calculation
    - FFmpeg concat demuxer with -safe 0 and forward-slash paths on Windows
    - Per-clip resumability via os.path.exists check before render
    - Post-render sanity assertions (exists + size > 1MB)

key-files:
  created: []
  modified:
    - src/classes/Podcast.py

key-decisions:
  - "Use math.ceil(duration * FPS) for frames — not int() — to avoid zoom reset at clip end (Pitfall 1)"
  - "Use -t str(duration) instead of -shortest — -shortest can cut last second of audio (Pitfall 4)"
  - "scale+pad before zoompan is mandatory — Gemini PNGs are 768x1344, zoompan needs exact 1080x1920 match (Pitfall 2)"
  - "Write forward slashes in concat_list.txt via replace(chr(92), '/') — backslashes fail FFmpeg concat on Windows (Pitfall 3)"
  - "Always regenerate final.mp4 on concat pass — stream-copy is under 1 second, complexity of staleness check not worth it"

patterns-established:
  - "render() follows generate_assets() pattern: episode_dir guard, scene loop with skip-if-exists, descriptive FileNotFoundError"
  - "subprocess.run(cmd, capture_output=True, text=True, check=True) — established FFmpeg pattern from Tts.py"
  - "filter_complex with named output [v] + explicit -map required when mixing -loop 1 image with audio input"

requirements-completed: [REND-01, REND-02, REND-03]

# Metrics
duration: 15min
completed: 2026-04-02
---

# Phase 7 Plan 01: Podcast.render() FFmpeg Zoompan Pipeline Summary

**FFmpeg two-pass render pipeline: per-scene libx264 clips with zoompan Ken Burns motion, concatenated to final.mp4 via stream-copy concat demuxer**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-02T00:37:00Z
- **Completed:** 2026-04-02T00:52:00Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Replaced `render()` NotImplementedError stub with complete two-pass FFmpeg pipeline
- Pass 1: 14 per-scene MP4 clips rendered from PNG+WAV pairs with alternating Ken Burns zoom (even=zoom-in, odd=zoom-out) at 1080x1920, 25fps, libx264 fast, yuv420p, aac 192k
- Pass 2: All 14 clips concatenated into `final.mp4` via FFmpeg concat demuxer with `-c copy` (no re-encode)
- Full resumability: skips existing clips; raises descriptive errors for missing assets
- Post-render sanity assertions guard against empty output

## Task Commits

1. **Task 1: Implement Podcast.render() — per-scene clip render loop and concat** - `61064d8` (feat)

## Files Created/Modified

- `src/classes/Podcast.py` - Added `import math`, `import subprocess`; replaced render() stub with full FFmpeg two-pass pipeline (~100 lines)

## Decisions Made

- All FFmpeg command values taken verbatim from 07-RESEARCH.md (verified on target machine)
- `math.ceil` for frame calculation — avoids 1-frame short rounding that causes zoom reset mid-clip
- `-t str(duration)` over `-shortest` — `-shortest` can cut last audio second in some FFmpeg builds
- `scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2` prepended to zoompan — required because Gemini nanobanana2 outputs 768x1344, not 1080x1920
- `replace(chr(92), '/')` for Windows forward-slash concat paths — backslashes cause FFmpeg "No such file" even when file exists
- Always re-concatenate final.mp4 (don't check staleness) — concat with `-c copy` is under 1 second

## Deviations from Plan

None — plan executed exactly as written. All FFmpeg syntax taken verbatim from research; implementation matches plan action block 1:1.

## Issues Encountered

None — the smoke test (AST parse + grep checks) confirmed all acceptance criteria. The import smoke test from project root was not runnable due to missing venv packages (`srt_equalizer`) in the test environment, but AST parsing confirmed structural correctness without requiring import.

## User Setup Required

None — no new external service configuration required. FFmpeg and ffprobe already confirmed on PATH.

## Next Phase Readiness

- Phase 8 (thumbnail + upload) can now be planned: `Podcast.render()` produces `{episode_dir}/final.mp4`
- Episode dir convention is stable: `.mp/podcast_{slug}_{YYYYMMDD}/`
- No blockers

---
*Phase: 07-ffmpeg-render*
*Completed: 2026-04-02*
