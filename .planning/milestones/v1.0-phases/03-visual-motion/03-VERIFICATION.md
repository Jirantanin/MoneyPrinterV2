---
phase: 03-visual-motion
verified: 2026-03-31T10:30:00Z
status: human_needed
score: 4/4 must-haves verified (automated); visual playback pending human
re_verification: false
human_verification:
  - test: "Render a video and watch it (cd remotion && npm run studio, or node scripts/render.mjs <props-json-path>)"
    expected: "Every image has visible motion (no static frames); consecutive images move in different directions; scene boundaries show a slide/push wipe — not a hard cut or black frame; video plays to completion without a silent tail or audio cutoff"
    why_human: "Motion, transition type, and audio sync are perceptual qualities that cannot be verified by static code analysis or grep"
---

# Phase 3: Visual Motion — Verification Report

**Phase Goal:** Every image in a generated clip drifts with Ken Burns motion and scenes are separated by zoom-push transitions instead of hard cuts
**Verified:** 2026-03-31
**Status:** human_needed — all automated checks pass; visual playback confirmation outstanding
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Each image visibly zooms and/or pans during its on-screen duration — no image is stationary | VERIFIED (automated) | `KenBurnsFrame` applies `interpolate`-driven `transform` (scale or translateX) on every `useCurrentFrame()` tick; `objectFit: cover` prevents edge exposure; `variant` is always set from `KB_CYCLE[i % 4]` — no path skips it |
| 2  | Consecutive images drift in different directions (zoom-in, zoom-out, pan-left, pan-right cycling) | VERIFIED (automated) | `KB_CYCLE = ['zoom-in', 'zoom-out', 'pan-left', 'pan-right']` and `variant={KB_CYCLE[i % KB_CYCLE.length]}` guarantees direction changes every scene |
| 3  | A visible push/slide transition plays between each pair of scenes — no hard cuts or black frames | VERIFIED (automated) | `TransitionSeries.Transition` with `slide({ direction: SLIDE_DIRS[i % 4] })` and `linearTiming({ durationInFrames: tf })` is inserted between every adjacent pair (`i < n - 1` guard); `tf` is always >= 1 when `n > 1` |
| 4  | Rendered video total duration matches TTS audio length — no silent tail or audio cutoff | VERIFIED (automated) | Duration compensation formula `Math.round((totalFrames + (n-1)*tf) / n)` present at line 79; guard `Math.min(TRANSITION_FRAMES, Math.floor(perImageRaw/2))` at line 74 prevents runtime overflow on short clips |

**Score:** 4/4 truths verified (automated logic complete; Truth 3 and Truth 1 additionally require human visual playback — see Human Verification)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `remotion/package.json` | `@remotion/transitions` dependency at `4.0.441` (no caret) | VERIFIED | `"@remotion/transitions": "4.0.441"` confirmed; `remotion` and `@remotion/cli` also pinned to `4.0.441` |
| `remotion/src/VideoShort.tsx` | Rewritten `ImageSlideshow` with `KenBurnsFrame` + `TransitionSeries` | VERIFIED | 277-line file; `KenBurnsFrame` at lines 22-60; `ImageSlideshow` at lines 62-103; all downstream components (`GradientOverlay`, `CategoryBadge`, `SubtitleLayer`, `BreakingNewsTicker`, `VideoShort`) preserved unchanged |
| `remotion/node_modules/@remotion/transitions/` | Package physically installed | VERIFIED | `node_modules/@remotion/transitions/package.json` exists |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `VideoShort.tsx` | `@remotion/transitions` | `import { TransitionSeries, linearTiming } from "@remotion/transitions"` | WIRED | Line 10; `TransitionSeries` used at lines 83, 86, 92, 94, 99, 101 |
| `VideoShort.tsx` | `@remotion/transitions/slide` | `import { slide } from "@remotion/transitions/slide"` | WIRED | Line 11; `slide()` called at line 95 |
| `VideoShort.tsx` | `useCurrentFrame` inside `KenBurnsFrame` | `KenBurnsFrame` sub-component called within `TransitionSeries.Sequence` | WIRED | `useCurrentFrame()` at line 27 inside `KenBurnsFrame`; component mounted at line 87 inside `TransitionSeries.Sequence` — Remotion's context tree scopes frame to the sequence |
| `VideoShort` root | `ImageSlideshow` | `<ImageSlideshow imagePaths={props.imagePaths} durationInSeconds={props.durationInSeconds} />` | WIRED | Line 265; `props.imagePaths` flows from caller (Python-generated props JSON) through `VideoProps` type |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ImageSlideshow` | `imagePaths` | `props.imagePaths` passed from `VideoShort` root at line 265; Python generates this array from real image files staged to `remotion/public/assets/` | Yes — populated at render time by Python pipeline; `imagePaths.length === 0` guard prevents empty-state rendering | FLOWING |
| `KenBurnsFrame` | `frame` / `progress` | `useCurrentFrame()` — Remotion runtime injects real frame counter per sequence context | Yes — Remotion drives this; no static fallback | FLOWING |
| `ImageSlideshow` | `totalFrames` | `useVideoConfig().durationInFrames` — Remotion derives from composition `durationInSeconds * fps` prop | Yes — driven by TTS audio duration computed by Python | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TypeScript compiles without errors | `cd remotion && npx tsc --noEmit --skipLibCheck` | Exit 0, no errors | PASS |
| All `@remotion/*` pinned to `4.0.441` (no caret) | `node -e "const d=require('./package.json').dependencies; ..."` | `PASS` — all three entries confirmed `4.0.441` | PASS |
| `@remotion/transitions` physically installed | `ls remotion/node_modules/@remotion/transitions/package.json` | File exists | PASS |
| Visual motion and transitions in rendered video | `cd remotion && npm run studio` or `node scripts/render.mjs` | Not run — requires display/player | SKIP (human) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| VIS-01 | 03-01-PLAN.md | Every image in a generated clip has Ken Burns motion (zoom and/or pan drift) synced to its on-screen duration | SATISFIED | `KenBurnsFrame` applies directional `transform` via `interpolate` on every frame; `KB_CYCLE[i % 4]` ensures all images get a variant |
| VIS-02 | 03-01-PLAN.md | Ken Burns direction varies per scene (zoom-in, zoom-out, pan directions) so clips don't look templated | SATISFIED | `KB_CYCLE = ['zoom-in', 'zoom-out', 'pan-left', 'pan-right']` cycles deterministically; index `i % 4` guarantees no two adjacent scenes share a direction |
| VIS-03 | 03-01-PLAN.md | Scene transitions use zoom/push (not hard cuts or fade) with 15-20 frame duration at 30fps | SATISFIED | `TRANSITION_FRAMES = 18` (within 15-20 range); `linearTiming({ durationInFrames: tf })` where `tf = Math.min(18, ...)` ensures duration stays in range; `slide()` presentation is a push wipe (not fade, not cut) |

**Orphaned requirements:** None. REQUIREMENTS.md maps VIS-01, VIS-02, VIS-03 to Phase 3; all three are claimed by `03-01-PLAN.md` and verified above.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `remotion/src/VideoShort.tsx` | 156 | `return null` | Info | `SubtitleLayer` returns null when no subtitle is active — expected behavior, not a stub; subtitle entries come from real SRT data |

No blockers or warnings found.

**Specifically verified absent:**
- `CROSSFADE_FRAMES` — removed (was line 16 in old implementation)
- Standalone `Sequence` import from `"remotion"` — removed; only `TransitionSeries.Sequence` used
- `TODO`, `FIXME`, `placeholder` comments — none present
- Hardcoded empty `imagePaths={[]}` at call site — `imagePaths={props.imagePaths}` uses real runtime value

---

### Human Verification Required

#### 1. Visual playback — Ken Burns motion visible on every image

**Test:** Render a test video using `cd remotion && npm run studio` (browse to http://localhost:3000) or `cd remotion && node scripts/render.mjs <props-json-path>` with a real props JSON from a previous pipeline run. Play back the output.

**Expected:**
- Every image has visible drift (zoom in, zoom out, or pan) — no frame is completely static during its screen time
- Adjacent images move in different directions — the clip does not look like a repeating loop
- Scene boundaries show a wipe/push slide transition — no flash of black, no jump cut
- Video plays to audio completion — narration ends with the last video frame

**Why human:** Motion direction, transition sharpness, and audio-video sync are perceptual qualities. Code analysis confirms the transform math is wired and the formula is correct, but whether the motion is visibly perceptible (vs too subtle to notice) and whether the slide transition renders as expected in Chromium requires watching the output.

---

### Gaps Summary

No automated gaps. The implementation is complete and fully wired. The only open item is human visual playback (Task 3 in the plan was auto-approved in the SUMMARY without the user watching the rendered output).

**Root cause note:** Task 3 (`checkpoint:human-verify`) was marked `auto_advance: true` in the SUMMARY, meaning the visual check was skipped during execution. This is the sole reason status is `human_needed` rather than `passed`.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
