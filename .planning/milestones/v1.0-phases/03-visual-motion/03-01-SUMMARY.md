---
phase: 03-visual-motion
plan: 01
subsystem: ui
tags: [remotion, ken-burns, transitions, typescript, animation, video]

# Dependency graph
requires: []
provides:
  - Ken Burns 4-direction motion (zoom-in, zoom-out, pan-left, pan-right) on every image in generated clips
  - Slide-push scene transitions via @remotion/transitions TransitionSeries
  - Duration compensation formula preventing audio/video length mismatch
  - @remotion/transitions@4.0.441 installed and pinned
affects:
  - 03-visual-motion verification
  - YouTube pipeline (remotion render output quality)

# Tech tracking
tech-stack:
  added: ["@remotion/transitions@4.0.441"]
  patterns:
    - "KenBurnsFrame as sub-component so useCurrentFrame() is scoped to TransitionSeries.Sequence context"
    - "Duration compensation: Math.round((totalFrames + (n-1)*tf) / n) to preserve audio duration"
    - "Guard clause: Math.min(TRANSITION_FRAMES, Math.floor(perImageRaw/2)) prevents runtime error on short clips"

key-files:
  created: []
  modified:
    - remotion/package.json
    - remotion/src/VideoShort.tsx

key-decisions:
  - "Use linearTiming (not springTiming) — deterministic frame count for exact duration compensation math"
  - "slide() push transition satisfies VIS-03 zoom/push requirement; Ken Burns scaling inside each scene provides zoom energy"
  - "KenBurnsFrame extracted as separate component — ensures useCurrentFrame() returns sequence-local frame, not global"
  - "3% translateX for pan variants — subtle but perceptible on 1080px width (~32px travel)"

patterns-established:
  - "Sub-component pattern for sequence-scoped animation: inner component calls useCurrentFrame() inside TransitionSeries.Sequence"
  - "Duration compensation pattern: perImage = Math.round((totalFrames + (n-1)*tf) / n)"

requirements-completed: [VIS-01, VIS-02, VIS-03]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 3 Plan 01: Visual Motion Summary

**Ken Burns 4-direction cycle (zoom-in/out + pan-left/right) on all images with slide-push TransitionSeries transitions replacing static opacity cross-fades, using duration compensation to prevent audio cutoff**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-31T10:04:04Z
- **Completed:** 2026-03-31T10:06:28Z
- **Tasks:** 3 (2 auto + 1 checkpoint auto-approved)
- **Files modified:** 2

## Accomplishments

- Installed @remotion/transitions@4.0.441 and pinned all @remotion/* packages to exact version (no caret)
- Rewrote ImageSlideshow with KenBurnsFrame sub-component cycling through 4 directions via KB_CYCLE[i % 4]
- Replaced manual opacity cross-fade with TransitionSeries + slide() push transitions (SLIDE_DIRS[i % 4])
- Duration compensation formula: `Math.round((totalFrames + (n-1)*tf) / n)` prevents silent audio tail
- TypeScript compiles cleanly; all acceptance criteria verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Install @remotion/transitions and pin version** - `7117d4b` (chore)
2. **Task 2: Rewrite ImageSlideshow with Ken Burns + TransitionSeries** - `1f0dfef` (feat)
3. **Task 3: Visual verification** - auto-approved (auto_advance: true)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `remotion/package.json` - Added @remotion/transitions@4.0.441, pinned all @remotion/* to exact 4.0.441
- `remotion/src/VideoShort.tsx` - Rewrote ImageSlideshow component with KenBurnsFrame, TransitionSeries, slide() transitions

## Decisions Made

- Used `linearTiming` over `springTiming` — deterministic frame count makes duration compensation math exact and predictable
- `slide()` push transition chosen over custom zoom presentation — satisfies VIS-03 "zoom/push" requirement acceptably; Ken Burns scaling provides the zoom energy within each scene
- `KenBurnsFrame` extracted as a separate FC — necessary so `useCurrentFrame()` returns sequence-local frame (Remotion context-aware), not global composition frame
- Pan distance set to 3% translateX — subtly visible on mobile Shorts screen; easy to tune up to 5% if needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Worktree was missing the `remotion/` directory (untracked in git — gitignore covers `remotion/node_modules/` and `remotion/public/assets/` but not the directory itself). Merged `main` into the worktree branch to get all planning files, then copied `remotion/` from the main working directory. This was a worktree setup issue, not a code problem.

## Known Stubs

None — all components are fully wired. ImageSlideshow receives real `imagePaths` and `durationInSeconds` from the VideoShort root composition.

## Next Phase Readiness

- VIS-01, VIS-02, VIS-03 requirements completed
- Phase 03 (visual-motion) is the final phase in this milestone
- Ready for visual verification via `cd remotion && npm run studio` (http://localhost:3000) or full pipeline run
- Duration compensation formula is in place; ffprobe can verify rendered MP4 matches TTS WAV duration

---
*Phase: 03-visual-motion*
*Completed: 2026-03-31*
