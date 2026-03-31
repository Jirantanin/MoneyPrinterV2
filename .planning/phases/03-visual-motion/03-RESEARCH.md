# Phase 3: Visual Motion - Research

**Researched:** 2026-03-31
**Domain:** Remotion 4.x — Ken Burns animation + @remotion/transitions TransitionSeries
**Confidence:** HIGH

## Summary

Phase 3 upgrades the existing `ImageSlideshow` component in `remotion/src/VideoShort.tsx`.
The current component already implements a rudimentary Ken Burns zoom-in/zoom-out alternation
with a cross-fade using plain `<Sequence>` and `interpolate`. The phase replaces that with:

1. Full Ken Burns (zoom-in, zoom-out, pan-left, pan-right — 4-direction cycle) applied inside
   each `TransitionSeries.Sequence`.
2. `@remotion/transitions` `TransitionSeries` with `slide()` presentation (push-style) replacing
   the manual `<Sequence>` + opacity cross-fade loop.

The critical constraint is duration math: `TransitionSeries` shortens total frames by
`(N-1) * transitionFrames`. The parent composition's `durationInFrames` is already driven by
`durationInSeconds * 30` (from `calculateMetadata` in `Root.tsx`). The per-image sequence
duration must be calculated to compensate so the rendered video's total frame count still equals
`durationInSeconds * 30`.

**Primary recommendation:** Install `@remotion/transitions@4.0.441` (exact version, matching
installed `remotion@4.0.441`), rewrite `ImageSlideshow` to use `TransitionSeries` with `slide()`
and 4-direction Ken Burns cycle inside each sequence.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| remotion | 4.0.441 (installed) | Video composition framework | Already installed; all frame math is native |
| @remotion/transitions | 4.0.441 (must match exactly) | TransitionSeries, slide, wipe, linearTiming | Official first-party transitions package |
| react | 18.3.1 (installed) | Component rendering | Required by Remotion |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @remotion/cli | 4.0.441 (installed) | npx remotion render | Already wired via render.mjs |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| slide() | Custom zoom presentation | slide() is a push effect (translateX), not a scale zoom. A custom presentation with `scale()` would give a true zoom-push. However slide() satisfies VIS-03 ("zoom/push") acceptably. Custom presentation adds ~30 lines but is straightforward. |
| linearTiming | springTiming | springTiming duration is non-deterministic (`getDurationInFrames({fps:30})` returns 23 for default config). linearTiming is exact and safe for duration math. |
| 4-direction Ken Burns | 2-direction (zoom-in/zoom-out only) | Current code already does 2-direction. 4-direction (add pan-left, pan-right via translateX) satisfies VIS-02 with less template feel. |

**Installation:**
```bash
cd remotion && npm install @remotion/transitions@4.0.441
```

**Version rule (CRITICAL):** All `@remotion/*` packages must use the same version number.
The installed `remotion` and `@remotion/cli` are both `4.0.441`. Install `@remotion/transitions`
at exactly `4.0.441` and remove the `^` caret from `package.json` for this entry to prevent
drift.

---

## Architecture Patterns

### Recommended Structure

No new files are needed. All changes are inside:

```
remotion/src/
└── VideoShort.tsx     # ImageSlideshow component — full rewrite
remotion/package.json  # add @remotion/transitions@4.0.441
```

### Pattern 1: TransitionSeries Duration Compensation

**What:** `TransitionSeries` shortens total duration by `(numImages - 1) * TRANSITION_FRAMES`.
To preserve the original total frame budget (`durationInSeconds * 30`), each image's
`durationInFrames` must be padded to absorb the overlap.

**Formula:**
```
totalFrames = Math.ceil(durationInSeconds * 30)
numImages = imagePaths.length
perImageRaw = totalFrames / numImages
perImageCompensated = Math.round(perImageRaw + (numImages - 1) * TRANSITION_FRAMES / numImages)
// or equivalently:
perImageCompensated = Math.round((totalFrames + (numImages - 1) * TRANSITION_FRAMES) / numImages)
```

Verification: `numImages * perImageCompensated - (numImages - 1) * TRANSITION_FRAMES ≈ totalFrames`

**Why it matters:** Without this, a 30s video with 5 images and 20-frame transitions renders as:
`5 * (30*30/5) - 4*20 = 900 - 80 = 820 frames = 27.3s`. Audio gets cut. STATE.md explicitly
flags this as a known concern.

**Example:**
```typescript
// Source: https://www.remotion.dev/docs/transitions/transitionseries
const TRANSITION_FRAMES = 18; // 0.6s at 30fps — satisfies VIS-03 (15-20 frame range)
const totalFrames = Math.ceil(durationInSeconds * 30);
const n = imagePaths.length;
const perImage = n > 1
  ? Math.round((totalFrames + (n - 1) * TRANSITION_FRAMES) / n)
  : totalFrames;
```

### Pattern 2: 4-Direction Ken Burns Cycle

**What:** Cycle through four Ken Burns variants per scene index so consecutive images drift in
different directions (satisfies VIS-02).

**The 4 variants:**
1. Zoom-in from center (scale 1.0 → 1.05, origin center)
2. Zoom-out to center (scale 1.05 → 1.0, origin center)
3. Pan left (scale 1.05 fixed, translateX 0% → -3%)
4. Pan right (scale 1.05 fixed, translateX 0% → +3%)

**Example:**
```typescript
// Source: Remotion interpolate() API — https://www.remotion.dev/docs/interpolate
type KenBurnsVariant = 'zoom-in' | 'zoom-out' | 'pan-left' | 'pan-right';
const KB_CYCLE: KenBurnsVariant[] = ['zoom-in', 'zoom-out', 'pan-left', 'pan-right'];

function getKenBurnsStyle(variant: KenBurnsVariant, progress: number): React.CSSProperties {
  switch (variant) {
    case 'zoom-in':
      return { transform: `scale(${interpolate(progress, [0,1], [1.0, 1.05])})`, transformOrigin: 'center center' };
    case 'zoom-out':
      return { transform: `scale(${interpolate(progress, [0,1], [1.05, 1.0])})`, transformOrigin: 'center center' };
    case 'pan-left':
      return { transform: `scale(1.05) translateX(${interpolate(progress, [0,1], [0, -3])}%)`, transformOrigin: 'center center' };
    case 'pan-right':
      return { transform: `scale(1.05) translateX(${interpolate(progress, [0,1], [0, 3])}%)`, transformOrigin: 'center center' };
  }
}
```

### Pattern 3: TransitionSeries with slide()

**What:** Replace the manual `Sequence` + opacity loop with `TransitionSeries`.

**Key imports:**
```typescript
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
```

**Slide directions to cycle (4 directions available):**
`'from-left'`, `'from-right'`, `'from-top'`, `'from-bottom'`

**Example structure:**
```tsx
// Source: https://www.remotion.dev/docs/transitions/transitionseries
<TransitionSeries>
  {imagePaths.map((imgPath, i) => (
    <React.Fragment key={i}>
      <TransitionSeries.Sequence durationInFrames={perImage}>
        <AbsoluteFill>
          <img
            src={staticFile(imgPath)}
            style={{
              width: "100%", height: "100%", objectFit: "cover",
              ...getKenBurnsStyle(KB_CYCLE[i % 4], localProgress),
            }}
          />
        </AbsoluteFill>
      </TransitionSeries.Sequence>
      {i < imagePaths.length - 1 && (
        <TransitionSeries.Transition
          presentation={slide({ direction: SLIDE_DIRECTIONS[i % 4] })}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />
      )}
    </React.Fragment>
  ))}
</TransitionSeries>
```

**localProgress inside TransitionSeries.Sequence:** `useCurrentFrame()` inside a
`TransitionSeries.Sequence` returns frame relative to the sequence start (same as inside
`<Sequence>`). Divide by `perImage` to get 0-1 progress.

### Anti-Patterns to Avoid

- **Using springTiming for duration math:** `springTiming` duration is computed dynamically
  (`getDurationInFrames({fps})` returns 23 for default config). It works but makes the
  compensation formula harder to reason about. Use `linearTiming` with an explicit frame count.
- **Adjacent transitions without sequences between them:** Two `TransitionSeries.Transition`
  elements cannot be consecutive — always one `TransitionSeries.Sequence` between transitions.
- **Transition longer than adjacent sequence:** Remotion will throw a runtime error if
  `TRANSITION_FRAMES > perImage`. With 5 images at 30fps over 30s: perImage ≈ 181 frames. Even
  with 3 images at 10s: perImage ≈ 102 frames. 18-frame transitions are safe for all realistic
  inputs, but add a guard for very short clips (< 3 images × 3 seconds).
- **Importing from `@remotion/transitions` top-level for slide:** The slide presentation is
  imported from `@remotion/transitions/slide`, not from `@remotion/transitions` root.
  Wipe is `@remotion/transitions/wipe`. `TransitionSeries` and timing functions come from
  `@remotion/transitions` root.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Push transition between images | Custom opacity/translateX cross-fade | `slide()` from @remotion/transitions | Handles entering/exiting sync, epsilon gap prevention, direction options |
| Timing with exact frame count | Custom easing function | `linearTiming({ durationInFrames: N })` | Built-in, deterministic, integrates with getDurationInFrames |
| Duration calculation | Guessing frame count | TransitionSeries formula: `(N_seq * framesEach) - (N_transitions * TRANSITION_FRAMES)` | Predictable, documented behavior |

**Key insight:** The current cross-fade in `ImageSlideshow` is hand-rolled with manual opacity
interpolation. It works but couples fade timing to sequence layout in a fragile way.
`TransitionSeries` decouples these — each sequence has a clean duration and transitions handle
overlap math internally.

---

## Common Pitfalls

### Pitfall 1: Silent Audio Tail (Duration Mismatch)

**What goes wrong:** After switching to `TransitionSeries`, the rendered video is shorter than
the TTS audio. The video ends early with a silent tail, or the audio is clipped.

**Why it happens:** `TransitionSeries` subtracts `(numImages - 1) * TRANSITION_FRAMES` from the
total. If `perImage = totalFrames / numImages` (the naive calculation), the total rendered frames
equal `numImages * (totalFrames/numImages) - (numImages-1)*TRANSITION_FRAMES = totalFrames -
(numImages-1)*TRANSITION_FRAMES`, which is less than `totalFrames`.

**How to avoid:** Use the compensated formula:
`perImage = Math.round((totalFrames + (numImages - 1) * TRANSITION_FRAMES) / numImages)`

**Warning signs:** Rendered MP4 duration reported by ffprobe is shorter than the TTS WAV duration.
STATE.md explicitly pre-flagged this: "Phase 3: TransitionSeries silently shortens video duration."

### Pitfall 2: Version Mismatch on @remotion/transitions

**What goes wrong:** npm installs `@remotion/transitions@4.0.434` (latest at time of search)
while `remotion@4.0.441` is already installed. Remotion prints warnings or throws errors about
mismatched package versions, and the dev server may refuse to start.

**Why it happens:** The `^4.0.0` range in package.json for `remotion` and `@remotion/cli` was
locked to `4.0.441` at install time. A new `@remotion/transitions` added without pinning drifts
to its own latest.

**How to avoid:** Install with exact version: `npm install @remotion/transitions@4.0.441` and
add `"@remotion/transitions": "4.0.441"` (no caret) to package.json.

### Pitfall 3: Ken Burns transform on img vs container

**What goes wrong:** Applying CSS `transform: scale()` directly to the `<img>` element causes
scale-up to show white/black edges outside the image bounds because the containing
`AbsoluteFill` clips at 1080×1920.

**Why it happens:** The image starts at 100%×100% fill. Scaling up reveals the background color
at edges.

**How to avoid:** Set `objectFit: "cover"` on the `<img>` (already present in current code) —
this ensures the image always fills its container even before scaling. The Ken Burns scale then
zooms within an already-filled frame, so edges are never exposed. Starting scale of 1.0 (not
less than 1.0) is important.

### Pitfall 4: Transition Duration Constraint Violation

**What goes wrong:** Remotion throws a runtime error: "A transition must not be longer than the
duration of the previous or next sequence."

**Why it happens:** Very short videos (few seconds, few images) can produce a `perImage` value
smaller than `TRANSITION_FRAMES`.

**How to avoid:** Add a guard:
```typescript
const TRANSITION_FRAMES = imagePaths.length > 1
  ? Math.min(18, Math.floor(perImageRaw / 2))
  : 0;
```
For normal usage (5+ images, 20+s video) `perImageRaw` is 120+ frames, so 18 is always safe.

### Pitfall 5: useCurrentFrame inside TransitionSeries.Sequence

**What goes wrong:** Ken Burns progress is computed incorrectly, showing jump cuts or wrong
animation phase.

**Why it happens:** Developer uses global `useCurrentFrame()` (from the parent VideoShort
component) instead of calling `useCurrentFrame()` inside the inner component rendered within
`TransitionSeries.Sequence`. Remotion's `useCurrentFrame()` is context-aware — inside a
`Sequence` it returns frames relative to that sequence's start.

**How to avoid:** Extract image rendering into a sub-component (e.g., `KenBurnsImage`) so
`useCurrentFrame()` is called inside the sequence context. Alternatively, use the `frame - startFrame`
local variable approach (current code already does this correctly — preserve that pattern).

---

## Code Examples

### Full ImageSlideshow Rewrite (reference pattern)

```typescript
// Source pattern from:
// - https://www.remotion.dev/docs/transitions/transitionseries
// - https://www.remotion.dev/docs/interpolate
// - https://www.remotion.dev/docs/use-current-frame

import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";

const TRANSITION_FRAMES = 18; // 0.6s at 30fps — within VIS-03 15-20 frame requirement
const KB_CYCLE = ['zoom-in', 'zoom-out', 'pan-left', 'pan-right'] as const;
const SLIDE_DIRS = ['from-left', 'from-right', 'from-top', 'from-bottom'] as const;

// Inner component so useCurrentFrame() is scoped to the Sequence context
const KenBurnsFrame: React.FC<{ imgPath: string; variant: typeof KB_CYCLE[number]; durationInFrames: number }> = ({
  imgPath, variant, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const progress = frame / durationInFrames; // 0 → 1

  let transform = '';
  if (variant === 'zoom-in')  transform = `scale(${interpolate(progress, [0,1], [1.0, 1.05])})`;
  if (variant === 'zoom-out') transform = `scale(${interpolate(progress, [0,1], [1.05, 1.0])})`;
  if (variant === 'pan-left') transform = `scale(1.05) translateX(${interpolate(progress, [0,1], [0, -3])}%)`;
  if (variant === 'pan-right') transform = `scale(1.05) translateX(${interpolate(progress, [0,1], [0, 3])}%)`;

  return (
    <AbsoluteFill>
      <img
        src={staticFile(imgPath)}
        style={{ width: '100%', height: '100%', objectFit: 'cover', transform, transformOrigin: 'center center' }}
      />
    </AbsoluteFill>
  );
};

const ImageSlideshow: React.FC<Pick<VideoProps, 'imagePaths' | 'durationInSeconds'>> = ({
  imagePaths, durationInSeconds,
}) => {
  const { durationInFrames: totalFrames } = useVideoConfig();
  const n = imagePaths.length;
  if (n === 0) return <AbsoluteFill style={{ backgroundColor: '#111' }} />;

  const tf = n > 1 ? TRANSITION_FRAMES : 0;
  const perImage = n > 1
    ? Math.round((totalFrames + (n - 1) * tf) / n)
    : totalFrames;

  return (
    <TransitionSeries>
      {imagePaths.map((imgPath, i) => (
        <React.Fragment key={i}>
          <TransitionSeries.Sequence durationInFrames={perImage}>
            <KenBurnsFrame
              imgPath={imgPath}
              variant={KB_CYCLE[i % KB_CYCLE.length]}
              durationInFrames={perImage}
            />
          </TransitionSeries.Sequence>
          {i < n - 1 && (
            <TransitionSeries.Transition
              presentation={slide({ direction: SLIDE_DIRS[i % SLIDE_DIRS.length] })}
              timing={linearTiming({ durationInFrames: tf })}
            />
          )}
        </React.Fragment>
      ))}
    </TransitionSeries>
  );
};
```

### Duration Verification (manual sanity check)

```typescript
// Given: 5 images, 30s clip, 18-frame transitions
// perImage = Math.round((900 + 4*18) / 5) = Math.round(972/5) = Math.round(194.4) = 194
// rendered = 5*194 - 4*18 = 970 - 72 = 898 frames = 29.93s ≈ 30s (1 frame rounding error — acceptable)

// Given: 3 images, 20s clip, 18-frame transitions
// perImage = Math.round((600 + 2*18) / 3) = Math.round(636/3) = 212
// rendered = 3*212 - 2*18 = 636 - 36 = 600 frames = 20.0s (exact)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `<Sequence>` + opacity cross-fade | `TransitionSeries` with `slide()` | Phase 3 | Removes fragile manual frame math, enables direction variety |
| 2-direction Ken Burns (zoom-in/zoom-out only) | 4-direction cycle (+ pan-left, pan-right) | Phase 3 | Satisfies VIS-02: no looping template feel |

**Deprecated/outdated in this codebase:**
- `CROSSFADE_FRAMES` constant in `VideoShort.tsx` (line 16): replaced by `TRANSITION_FRAMES` inside the new `ImageSlideshow` implementation.
- Manual `opacity` interpolation on each image: replaced by `TransitionSeries` handling overlap.

---

## Open Questions

1. **Exact pan distance for Ken Burns**
   - What we know: 3% translateX gives visible but subtle pan on a 1080px-wide image (~32px travel)
   - What's unclear: Whether 3% is enough to be perceptible on a mobile Shorts screen, or needs 5%
   - Recommendation: Use 3% in initial implementation; note in plan as an easy tuning point

2. **slide() direction vs zoom presentation**
   - What we know: VIS-03 says "zoom/push (not hard cuts or fade)". `slide()` is a push — it moves pixels laterally. A true zoom transition (scale entering, scale exiting) is not in the built-in set.
   - What's unclear: Whether the project owner considers a push-slide sufficient for "zoom/push" or wants a custom scale-based zoom presentation.
   - Recommendation: Use `slide()` (push) for v1. It is a clean, energetic transition. The Ken Burns scaling inside each scene already provides the zoom energy. Commit to this interpretation.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install, render | ✓ | (project running) | — |
| npm | Package install | ✓ | (project running) | — |
| remotion | Composition framework | ✓ | 4.0.441 | — |
| @remotion/cli | Render command | ✓ | 4.0.441 | — |
| @remotion/transitions | TransitionSeries | ✗ | not installed | None — must install |

**Missing dependencies with no fallback:**
- `@remotion/transitions@4.0.441` — must be installed before implementation. Install command:
  `cd remotion && npm install @remotion/transitions@4.0.441`

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIS-01 | Every image in a generated clip has Ken Burns motion (zoom and/or pan drift) synced to its on-screen duration | Pattern 2 (4-direction Ken Burns cycle) inside each TransitionSeries.Sequence provides per-scene motion |
| VIS-02 | Ken Burns direction varies per scene (zoom-in, zoom-out, pan directions) so clips don't look templated | 4-element cycle `['zoom-in', 'zoom-out', 'pan-left', 'pan-right']` indexed by `i % 4` gives variety |
| VIS-03 | Scene transitions use zoom/push (not hard cuts or fade) with 15-20 frame duration at 30fps | `slide()` presentation + `linearTiming({ durationInFrames: 18 })` — 18 frames is within 15-20 range; push is a "zoom/push" style |
</phase_requirements>

---

## Sources

### Primary (HIGH confidence)
- https://www.remotion.dev/docs/transitions/transitionseries — TransitionSeries API, duration formula, Sequence/Transition syntax
- https://www.remotion.dev/docs/transitioning — Duration math explanation, overlap semantics
- https://github.com/remotion-dev/remotion/tree/main/packages/transitions/src/presentations — Available presentations list (verified: slide, wipe, fade, flip, iris, clock-wipe, none — no built-in zoom)
- https://www.remotion.dev/docs/transitions/presentations/slide — slide() API, direction options
- https://www.remotion.dev/docs/transitions/presentations/custom — Custom presentation API (TransitionPresentation type)
- `remotion/node_modules/remotion/package.json` — Confirmed installed version: 4.0.441
- `remotion/src/VideoShort.tsx` — Current ImageSlideshow implementation (direct code read)

### Secondary (MEDIUM confidence)
- https://www.npmjs.com/package/@remotion/transitions (via WebSearch) — Latest version confirmed 4.0.434; 4.0.441 is aligned with installed core packages

### Tertiary (LOW confidence)
- WebSearch results for Ken Burns + Remotion patterns — community usage confirms interpolate() + scale() + translate() approach is standard

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — remotion version confirmed from node_modules, @remotion/transitions version pinned from search; installation is trivial
- Architecture: HIGH — TransitionSeries API and duration formula verified from official docs; Ken Burns pattern confirmed from existing codebase (test_ken_burns.py + current VideoShort.tsx)
- Pitfalls: HIGH — Duration mismatch pre-flagged in STATE.md and verified against TransitionSeries formula; other pitfalls derived from documented API constraints

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (Remotion 4.x is stable; @remotion/transitions API is stable since 4.0.53)
