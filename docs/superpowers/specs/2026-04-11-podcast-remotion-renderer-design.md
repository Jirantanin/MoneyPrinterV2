# Podcast Remotion Renderer Design

**Date:** 2026-04-11
**Status:** Approved
**Scope:** Transition + Ken Burns motion only (no subtitle overlay)

## Context

Podcast videos currently look static and lifeless ("แห้ง"). Each scene is a single generated image with a basic FFmpeg zoompan Ken Burns effect (just zoom in/out alternating), and scenes are joined with hard cuts via FFmpeg concat. There are no transitions, no varied motion, and no visual flow between scenes.

Meanwhile, the Shorts pipeline already uses a Remotion-based renderer (`VideoShort.tsx`) with 4 Ken Burns variants (zoom-in, zoom-out, pan-left, pan-right), slide transitions between images (4 directions), subtitle animations, and overlay effects. This infrastructure is proven and running in production.

**Goal:** Migrate podcast rendering from FFmpeg to Remotion, reusing the existing animation infrastructure to give podcasts smooth slide transitions between scenes and varied Ken Burns motion.

## Architecture

### New File: `remotion/src/VideoPodcast.tsx`

A new Remotion composition for landscape 16:9 podcast video. Minimal — only image slideshow with Ken Burns + transitions and audio playback.

**Key differences from VideoShort.tsx:**
- Resolution: **1920x1080** (landscape) vs 1080x1920 (portrait)
- FPS: **25** (matching current podcast output) vs 30
- No subtitle layer, gradient overlay, category badge, or news ticker
- Audio: plays per-scene audio files concatenated, or a single merged audio track
- Receives per-scene durations (each scene has different length based on narration)

**Components to reuse from VideoShort.tsx:**
- `KenBurnsFrame` component — extract to `remotion/src/KenBurns.tsx` shared module (works for any resolution)
- `KB_CYCLE` and `SLIDE_DIRS` constants — extract alongside KenBurnsFrame
- `TransitionSeries` + `linearTiming` + `slide()` pattern from `@remotion/transitions`
- VideoShort.tsx updated to import from the shared module (no behavior change)

**Props interface:**

```typescript
export interface PodcastProps {
  imagePaths: string[];         // one per scene, relative to remotion/public/
  audioPath: string;            // single merged audio file
  sceneDurations: number[];     // duration of each scene in seconds
  durationInSeconds: number;    // total podcast duration
}
```

**Rendering logic:**
- Each scene gets its own `TransitionSeries.Sequence` with duration calculated from `sceneDurations[i]` converted to frames
- Ken Burns variant cycles through `KB_CYCLE` (zoom-in, zoom-out, pan-left, pan-right)
- Slide transitions between scenes cycle through `SLIDE_DIRS` (from-left, from-right, from-top, from-bottom)
- Transition duration: 15 frames (~0.6s at 25fps), clamped to not exceed half of any scene's duration
- Single `<Audio>` element plays the merged audio track

### Modified File: `remotion/src/Root.tsx`

Register the new `VideoPodcast` composition alongside existing `VideoShort`:

```typescript
<Composition
  id="VideoPodcast"
  component={VideoPodcast}
  durationInFrames={...}
  fps={25}
  width={1920}
  height={1080}
  defaultProps={DEFAULT_PODCAST_PROPS}
  calculateMetadata={...}
/>
```

### Modified File: `remotion/scripts/render.mjs`

Add support for selecting composition by a `composition` field in the props JSON:

- If `props.composition === "VideoPodcast"`, render with `VideoPodcast` composition at 25fps
- Default remains `VideoShort` at 30fps for backward compatibility
- Asset staging logic stays the same (stageAsset, cleanupStaged)
- FPS is derived from the composition choice, not hardcoded

### Modified File: `src/classes/Podcast.py` — `render()` method

Replace the current FFmpeg-based render with a Remotion call:

**Current flow (to be replaced):**
1. Per-scene: FFmpeg zoompan + audio combine -> `scene_NN.mp4`
2. Write `concat_list.txt`
3. FFmpeg concat demuxer -> `final.mp4`

**New flow:**
1. Merge all per-scene WAV files into one audio track via FFmpeg concat (fast, stream-copy for WAV)
2. Collect scene durations via ffprobe (already done in current code)
3. Build props JSON with image paths, merged audio path, scene durations
4. Call `node scripts/render.mjs <props-file>` (same pattern as `YouTube.combine_remotion()`)
5. Output: `final.mp4`

**Per-scene MP4 clips are no longer created.** The entire video is rendered in one Remotion pass, which is cleaner and allows transitions to overlap between scenes.

## What Does NOT Change

- Image generation pipeline (Gemini API, prompts, aspect ratio)
- Audio/TTS generation pipeline (Edge TTS, per-scene WAV files)
- Metadata generation (title, description, tags)
- Thumbnail generation
- Shorts pipeline (VideoShort.tsx untouched)
- Upload pipeline
- Studio UI

## Critical Files

| File | Action | Purpose |
|------|--------|---------|
| `remotion/src/KenBurns.tsx` | Create | Shared KenBurnsFrame + constants (extracted from VideoShort) |
| `remotion/src/VideoPodcast.tsx` | Create | New landscape composition |
| `remotion/src/VideoShort.tsx` | Modify | Import KenBurnsFrame from shared module |
| `remotion/src/Root.tsx` | Modify | Register VideoPodcast composition |
| `remotion/scripts/render.mjs` | Modify | Support composition selection + 25fps |
| `src/classes/Podcast.py` | Modify | Replace FFmpeg render with Remotion call |
| `remotion/src/types.ts` | Modify | Add PodcastProps interface |

## Verification

1. Generate a new podcast episode (or re-render the latest "ดวงจันทร์หายไปคืนนี้" episode using existing assets)
2. Play `final.mp4` and verify:
   - Slide transitions between scenes (no hard cuts)
   - Ken Burns has 4 variants (zoom-in, zoom-out, pan-left, pan-right) cycling
   - Audio is in sync with images
   - Video is 1920x1080 landscape at 25fps
   - File size is reasonable (similar to or smaller than FFmpeg output)
3. Run a Shorts generation to confirm VideoShort pipeline is unaffected
