# Architecture Research

**Domain:** YouTube Shorts engagement upgrade — Python pipeline + Remotion renderer
**Researched:** 2026-03-30
**Confidence:** HIGH (all claims verified against source code and official docs)

## Standard Architecture

### System Overview

The pipeline has a hard boundary between Python and Node.js. Python orchestrates all content generation and hands off to Remotion via a props JSON file. All visual effects live exclusively on the Remotion side of that boundary.

```
┌──────────────────────────────────────────────────────────────────┐
│  Python Layer  (src/classes/YouTube.py)                          │
│                                                                  │
│  generate_topic()  →  generate_script()  →  generate_metadata() │
│        ↓                     ↓                                   │
│  [NEW: generate_hook() inserts hook as first sentence]           │
│        ↓                                                         │
│  generate_prompts()  →  generate_image() × N  (Gemini API)      │
│        ↓                                                         │
│  generate_script_to_speech()  →  TTS class                      │
│        ↓                        [NEW: rate= param on Communicate]│
│  generate_subtitles()  →  faster-whisper  →  .srt file          │
│        ↓                                                         │
│  combine_remotion()  →  write .render-props.json                 │
│        ↓                                                         │
│  subprocess: node scripts/render.mjs <props-file>               │
├──────────────────────────────────────────────────────────────────┤
│  Node.js Boundary  (remotion/scripts/render.mjs)                 │
│                                                                  │
│  read props JSON  →  stage assets to remotion/public/assets/     │
│  →  write resolved props JSON                                    │
│  →  execSync: npx remotion render src/Root.tsx VideoShort        │
├──────────────────────────────────────────────────────────────────┤
│  Remotion Layer  (remotion/src/)                                 │
│                                                                  │
│  Root.tsx  →  VideoShort.tsx                                     │
│                 ↓                                                │
│  ImageSlideshow  [UPGRADE: zoom-push TransitionSeries]           │
│  GradientOverlay                                                 │
│  CategoryBadge                                                   │
│  SubtitleLayer                                                   │
│  BreakingNewsTicker (category-conditional)                       │
│  Audio (TTS) + Audio (BGM optional)                              │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `YouTube.generate_script()` | LLM script generation via Ollama | `src/classes/YouTube.py` |
| `YouTube.generate_hook()` | (NEW) LLM hook generation; prepends to `self.script` | `src/classes/YouTube.py` |
| `TTS.synthesize()` | edge-tts audio synthesis; outputs WAV | `src/classes/Tts.py` |
| `YouTube.combine_remotion()` | Assembles props JSON, triggers Node subprocess | `src/classes/YouTube.py` |
| `render.mjs` | Stages assets into `remotion/public/assets/`, invokes Remotion CLI | `remotion/scripts/render.mjs` |
| `ImageSlideshow` | Per-image Ken Burns (existing); (UPGRADE) zoom-push transitions | `remotion/src/VideoShort.tsx` |
| `VideoShort` | Root composition; wires all layers | `remotion/src/VideoShort.tsx` |
| `VideoProps` | Typed contract between Python props JSON and Remotion | `remotion/src/types.ts` |

## Recommended Project Structure

No new top-level directories are needed. Changes are localized to existing files plus one new Remotion utility:

```
src/
└── classes/
    └── YouTube.py          # add generate_hook(); update combine_remotion() props; update generate_video() call order
    └── Tts.py              # add rate parameter to Communicate() call

remotion/
└── src/
    ├── VideoShort.tsx      # replace ImageSlideshow implementation with TransitionSeries
    ├── types.ts            # add hookText?: string field to VideoProps (optional, for future use)
    ├── presets.ts          # no change needed
    └── transitions/
        └── ZoomPush.tsx    # (NEW) custom Remotion presentation for zoom-push transition
```

### Structure Rationale

- **`remotion/src/transitions/`** — Isolates the custom presentation component so `VideoShort.tsx` imports it cleanly and the presentation can be unit-tested in Remotion Studio independently.
- **Hook generation in `YouTube.py`** — Keeps all Ollama calls in one class. `generate_hook()` runs before `generate_script()` or is called inside it; the hook is prepended to `self.script` before TTS and subtitle generation so it flows through without touching downstream code.
- **TTS change in `Tts.py`** — Centralizes prosody in the TTS class; callers do not change.

## Architectural Patterns

### Pattern 1: Props JSON as Python-to-Remotion Contract

**What:** Python writes all inputs to a JSON file. Node reads it. Remotion consumes it via `--props`. No shared memory, no IPC beyond the file.

**When to use:** Always — this is the existing pattern and must not change.

**Trade-offs:** Clean isolation but requires any new engagement parameters (hook type, transition style, prosody rate) that need to influence rendering to be surfaced as explicit fields in `VideoProps`. Adding a field in `types.ts` without using it is safe; omitting it means Remotion can't read it.

**Existing schema (`remotion/src/types.ts`):**
```typescript
export interface VideoProps {
  topic: string;
  script: string;
  category: VideoCategory;
  imagePaths: string[];
  audioPath: string;
  srtContent: string;
  bgmPath?: string;
  durationInSeconds: number;
}
```

**No schema changes required for this milestone.** Ken Burns and zoom-push transitions are purely frame-driven from `imagePaths` and `durationInSeconds` which already exist. Hook text is prepended to `script` (already passed). Prosody affects the WAV file before it reaches Remotion.

### Pattern 2: Ken Burns via `interpolate()` — Already Implemented

**What:** `ImageSlideshow` already applies Ken Burns using Remotion's `interpolate()` to drive CSS `transform: scale()` per frame. Alternates zoom-in/zoom-out per image index.

**Current implementation (confirmed in `VideoShort.tsx` lines 54-61):**
```typescript
const scale = interpolate(
  localFrame,
  [0, framesPerImage],
  zoomIn ? [1.0, 1.04] : [1.04, 1.0],
  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
);
```

**Status:** Implemented and working. No changes needed for Ken Burns unless zoom ratio needs tuning (`1.04` = 4% zoom, which is subtle). This can be a config value in `presets.ts` per category if desired.

### Pattern 3: Zoom-Push Transitions via `@remotion/transitions`

**What:** Replace the current cross-fade opacity approach in `ImageSlideshow` with `<TransitionSeries>` from `@remotion/transitions`. The `ZoomPush.tsx` custom presentation drives a scale + translateX animation using `presentationProgress` (0→1).

**When to use:** Replacing the existing `opacity` cross-fade between images (lines 39-50 of `VideoShort.tsx`).

**Installation required:** `@remotion/transitions` is a separate package (available from Remotion v4.0.53+). Must be added to `remotion/package.json`.

**Custom presentation pattern:**
```typescript
// remotion/src/transitions/ZoomPush.tsx
import { TransitionPresentation } from "@remotion/transitions";
import { AbsoluteFill } from "remotion";

export const zoomPush = (): TransitionPresentation<Record<string, never>> => {
  const component: React.FC<{
    children: React.ReactNode;
    presentationProgress: number;
    presentationDirection: "entering" | "exiting";
  }> = ({ children, presentationProgress, presentationDirection }) => {
    const scale = presentationDirection === "entering"
      ? interpolate(presentationProgress, [0, 1], [1.15, 1.0])
      : interpolate(presentationProgress, [0, 1], [1.0, 0.9]);

    return (
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        {children}
      </AbsoluteFill>
    );
  };
  return { component, props: {} };
};
```

**Refactored `ImageSlideshow` skeleton:**
```typescript
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { zoomPush } from "./transitions/ZoomPush";

const ImageSlideshow = ({ imagePaths, durationInSeconds }) => {
  const { fps } = useVideoConfig();
  const framesPerImage = Math.floor((durationInSeconds * fps) / imagePaths.length);
  const transitionDurationFrames = 12; // ~0.4s at 30fps

  return (
    <TransitionSeries>
      {imagePaths.map((imgPath, i) => (
        <>
          <TransitionSeries.Sequence durationInFrames={framesPerImage} key={i}>
            {/* img with Ken Burns scale via useCurrentFrame() */}
          </TransitionSeries.Sequence>
          {i < imagePaths.length - 1 && (
            <TransitionSeries.Transition
              presentation={zoomPush()}
              timing={linearTiming({ durationInFrames: transitionDurationFrames })}
            />
          )}
        </>
      ))}
    </TransitionSeries>
  );
};
```

**Trade-offs:** `TransitionSeries` manages its own frame accounting (total duration = sum of sequences minus overlap from transitions). This means `durationInFrames` passed to `<Composition>` must be recomputed: `(framesPerImage * N) - (transitionDurationFrames * (N-1))`. The `calculateMetadata` in `Root.tsx` currently uses only `durationInSeconds * 30`; it must remain correct because audio duration is the authority.

### Pattern 4: Hook Generation — LLM Injection Before Script

**What:** A new `generate_hook()` method calls `generate_response()` with a structured prompt asking for a single opening sentence (question, stat, or bold claim) matched to the topic. The result is prepended to `self.script` before `generate_script_to_speech()` runs.

**Integration point:** Inside `generate_video()`, call order becomes:
```
generate_topic() → generate_hook() → generate_script() → [hook prepended to self.script] → generate_metadata() → ...
```

**Prompt strategy (MEDIUM confidence — needs iteration):**
```python
def generate_hook(self) -> str:
    prompt = f"""
    Write one single sentence to open a YouTube Short video about: {self.subject}

    Use ONE of these formats (pick the best fit for the topic):
    - A surprising statistic ("Did you know X% of ...")
    - A provocative question ("What if you could ...")
    - A bold/counterintuitive claim ("Most people are wrong about ...")

    Requirements:
    - Exactly one sentence
    - Under 15 words
    - No markdown, no quotes
    - Must make a viewer stop scrolling in the first 3 seconds

    Return only the hook sentence, nothing else.
    """
    hook = self.generate_response(prompt)
    hook = hook.strip().rstrip(".")
    self.script = hook + ". " + self.script
    return hook
```

**Why this location:** `self.script` is the single source of truth that feeds TTS, subtitle generation, and metadata. Prepending here means all downstream steps automatically include the hook — no props schema changes needed.

### Pattern 5: TTS Prosody via `rate=` on `edge-tts.Communicate`

**What:** `edge-tts` v7.2.8 (current as of 2026-03-22) supports `rate` as a constructor parameter on `Communicate`. Value is a percentage string (e.g., `"+20%"`). Pitch via `pitch` parameter is documented but reported unreliable (may be a no-op on the Microsoft service side — LOW confidence on effectiveness).

**Current `Tts.py` — relevant line:**
```python
communicate = edge_tts.Communicate(text, voice)
```

**Required change:**
```python
communicate = edge_tts.Communicate(text, voice, rate="+20%")
```

**Where the rate value comes from:** Config via `config.json` / `get_tts_rate()` getter (new getter needed). Default `"+20%"`. This keeps `Tts.__init__` as the only place that reads config.

**SSML is not the path.** The web search confirmed Microsoft's service rejects custom SSML. The `rate=` constructor parameter is the correct API.

**Pitch caveat (LOW confidence):** The GitHub README shows pitch (`--pitch`) in CLI examples, but a separate issue reports it was removed in 6.0.3. At v7.2.8, testing is required to confirm whether `pitch` parameter has any effect. Do not block on it; `rate` alone produces noticeably more energetic delivery.

## Data Flow

### Full Engagement-Upgraded Pipeline

```
[YouTube.generate_video(tts)]
        │
        ├─ generate_topic()        Ollama → self.subject (str)
        │
        ├─ generate_hook()         Ollama → prepend to self.script
        │   [NEW]
        │
        ├─ generate_script()       Ollama → self.script (str, now starts with hook)
        │
        ├─ generate_metadata()     Ollama → self.metadata {title, description}
        │
        ├─ generate_prompts()      Ollama → self.image_prompts (list[str])
        │
        ├─ generate_image() × N    Gemini API → self.images (list[str] of .png paths)
        │
        ├─ generate_script_to_speech(tts)
        │       │
        │       └─ TTS.synthesize(self.script, path)
        │               └─ edge_tts.Communicate(text, voice, rate="+20%")  [CHANGED]
        │               └─ ffmpeg mp3→wav
        │               → self.tts_path (.wav)
        │
        ├─ generate_subtitles(self.tts_path)
        │       └─ faster-whisper / AssemblyAI → self.srt_path (.srt)
        │
        └─ combine_remotion()
                │
                ├─ read audio duration (moviepy AudioFileClip)
                ├─ build props dict  [NO SCHEMA CHANGE NEEDED]
                ├─ write .render-props.json
                │
                └─ subprocess: node scripts/render.mjs
                        │
                        ├─ stage images → remotion/public/assets/
                        ├─ stage audio  → remotion/public/assets/
                        ├─ read .srt → srtContent string
                        ├─ write .render-props-resolved.json
                        │
                        └─ execSync: npx remotion render
                                │
                                └─ VideoShort.tsx renders:
                                        ImageSlideshow (Ken Burns + ZoomPush transitions)  [CHANGED]
                                        GradientOverlay
                                        CategoryBadge
                                        SubtitleLayer
                                        Audio (TTS WAV)
                                        Audio (BGM optional)
                                → output .mp4

[YouTube.upload_video()]
        └─ YouTube Data API v3 → uploaded
```

### Props JSON Schema (No Changes Required)

The existing schema is sufficient for this milestone. All four engagement features flow through existing fields:

| Feature | How it flows |
|---------|-------------|
| Hook | Prepended to `script` string in Python — already passed to Remotion |
| Ken Burns | Already implemented using `imagePaths` + `durationInSeconds` |
| Zoom-push transitions | Same `imagePaths` array drives `TransitionSeries` |
| TTS prosody | Applied during WAV generation — affects `audioPath` file content |

**No new fields needed in `VideoProps` or `.render-props.json` for this milestone.**

If future milestones need per-image motion metadata (e.g., custom pan direction), add:
```typescript
imageMotion?: Array<{ zoomIn: boolean; panX: number; panY: number }>;
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 account / 1 video at a time | Current sync sequential pipeline is fine |
| 2-5 accounts, CRON-scheduled | Current subprocess CRON model handles this; no change |
| Parallel video generation | Would require per-account isolated run dirs (already supported via `run_dir`) |

The engagement upgrade has no scaling implications — it adds CPU time in Remotion's Chromium render (Ken Burns math is cheap; the Chromium shell startup is the bottleneck regardless).

## Anti-Patterns

### Anti-Pattern 1: Implementing Visual Effects in Python/MoviePy

**What people do:** Apply Ken Burns or transitions using `moviepy` or `Pillow` before staging to Remotion.

**Why it's wrong:** Python cannot synchronize frame-accurate motion with Remotion's frame clock. The `_add_ken_burns()` method in `combine_moviepy()` exists only as MoviePy fallback logic. Duplicating motion in both places creates inconsistency and wastes compute.

**Do this instead:** All motion effects belong exclusively in Remotion components. Python stages static PNG files; Remotion animates them.

### Anti-Pattern 2: Passing Hook as a Separate Props Field

**What people do:** Add a `hookText` field to `VideoProps`, render it as a separate on-screen text layer in Remotion.

**Why it's wrong (for this milestone):** The hook's job is to be spoken first by TTS and appear in subtitles. Rendering it separately creates two competing layers and breaks subtitle timing. The hook is content, not visual decoration.

**Do this instead:** Prepend the hook to `self.script` in Python before TTS synthesis. It automatically appears in the WAV audio and in the Whisper-generated subtitles.

### Anti-Pattern 3: Using SSML Tags Directly with edge-tts

**What people do:** Wrap text in `<speak><prosody rate="fast">...</prosody></speak>` and pass to `edge_tts.Communicate`.

**Why it's wrong:** Microsoft's service blocks custom SSML. The library deliberately removed general SSML support. Passing SSML tags as text causes them to be spoken literally.

**Do this instead:** Use the `rate=` constructor parameter on `edge_tts.Communicate`. This is the only supported prosody control path at edge-tts v7.x.

### Anti-Pattern 4: Changing `durationInSeconds` Without Accounting for Transition Overlap

**What people do:** Use `imagePaths.length * framesPerImage / fps` as total duration after adding `TransitionSeries`.

**Why it's wrong:** `TransitionSeries` overlaps adjacent sequences by the transition duration. The actual video duration is `(framesPerImage * N) - (transitionDurationFrames * (N-1))`. If this is shorter than the TTS audio, the render will clip audio.

**Do this instead:** Keep `durationInSeconds` anchored to the TTS audio duration (current behavior). Size `framesPerImage` so the image slideshow is slightly longer than the audio — pad with the last image if needed. Audio is always the authoritative duration.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Ollama (hook generation) | Same `generate_response()` call, new method | No new client; same local HTTP |
| edge-tts (prosody) | Constructor param `rate="+20%"` on `Communicate` | v7.2.8 confirmed; pitch effectiveness LOW confidence |
| `@remotion/transitions` | npm install in `remotion/`; import in `VideoShort.tsx` | Separate package; needs `npm install @remotion/transitions` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Python → Node | `.render-props.json` file (read by `render.mjs`) | Existing contract; no schema change needed |
| Node → Remotion | `.render-props-resolved.json` + `--props` CLI flag | `render.mjs` writes this after staging assets |
| `generate_hook()` → `generate_script()` | `self.script` string on the `YouTube` instance | Hook prepended in Python memory before TTS |
| `VideoShort` → `ZoomPush` | Imported as Remotion presentation function | New file; pure TypeScript, no side effects |

## Build Order Implications

Dependencies between the four features determine implementation order:

```
1. TTS Prosody  (Tts.py: add rate= param)
       — no dependencies, isolated change, lowest risk
       — test immediately: listen to output WAV

2. Hook Generation  (YouTube.py: add generate_hook())
       — depends on: working Ollama connection (already confirmed)
       — test: run generate_video(), inspect self.script to confirm hook prepended
       — unblocks: nothing, but improves subtitle quality for testing

3. Zoom-Push Transitions  (remotion/src/transitions/ZoomPush.tsx + VideoShort.tsx refactor)
       — depends on: @remotion/transitions installed
       — install: cd remotion && npm install @remotion/transitions
       — test: npx remotion studio — observe transition between images
       — Ken Burns (existing) must be preserved inside the new TransitionSeries.Sequence

4. Full integration test
       — run full pipeline end-to-end
       — verify audio duration == video duration (no clip)
       — verify hook appears in subtitles at t=0
       — verify zoom-push visible between images
       — verify speech rate feels energetic
```

Ken Burns requires no code changes (already implemented in `VideoShort.tsx`). It must be preserved when refactoring `ImageSlideshow` to use `TransitionSeries`.

## Sources

- Remotion v4 transitions docs: https://www.remotion.dev/docs/transitions/
- Remotion custom presentations: https://www.remotion.dev/docs/transitions/presentations/custom
- edge-tts GitHub (v7.2.8): https://github.com/rany2/edge-tts
- Existing codebase: `remotion/src/VideoShort.tsx`, `src/classes/Tts.py`, `src/classes/YouTube.py`, `remotion/src/types.ts`

---
*Architecture research for: YouTube Shorts engagement upgrade (MoneyPrinterV2)*
*Researched: 2026-03-30*
