# Stack Research

**Domain:** YouTube Shorts engagement features — Ken Burns motion, scene transitions, TTS prosody, LLM hook generation
**Researched:** 2026-03-30
**Confidence:** HIGH (all core APIs verified against official docs and source)

---

## Context: What Already Exists

The existing Remotion project (`remotion/`) already implements a basic Ken Burns effect in `VideoShort.tsx`:
- `useCurrentFrame()` + `interpolate()` driving `scale` on `<img>` tags
- Alternating zoom-in / zoom-out (scale 1.0→1.04 or 1.04→1.0)
- Cross-fade opacity between images (15-frame overlap)
- No pan (translateX/Y), no transitions package, no prosody on TTS

The upgrade adds: pan motion to Ken Burns, zoom/push scene transitions via `@remotion/transitions`, prosody parameters to the `edge-tts` `Communicate` class, and structured hook generation via Ollama.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `remotion` | 4.0.441 (installed) | Frame-accurate video rendering | Already installed; `interpolate()` + `useCurrentFrame()` are the standard Remotion primitives for Ken Burns — CSS transitions are explicitly warned against in docs because they cause render flicker |
| `@remotion/transitions` | 4.0.441 (must match remotion) | Built-in `<TransitionSeries>` + `slide()` / `fade()` presentations | Official Remotion package for scene transitions; available from v4.0.53; Remotion requires exact version parity across all `@remotion/*` packages — no `^` |
| `edge-tts` | 7.2.8 (latest as of 2026-03-30) | TTS with prosody control | `Communicate` class already accepts `rate`, `pitch`, `volume` as keyword args — zero provider change needed, just update the call site in `Tts.py` |
| `ollama` Python SDK | installed (existing) | Structured hook generation | Supports `format=` with a Pydantic JSON schema since v0.5; local inference, no API key; matches existing `llm_provider.py` pattern |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | already available via `ollama` deps | Schema definition for structured Ollama output | Define `HookOutput` model with `hook_type` + `hook_text` fields; pass `HookOutput.model_json_schema()` to `ollama.chat(format=...)` |
| `@remotion/transitions/slide` | (bundled in `@remotion/transitions`) | Push-style slide transition between scenes | Use `slide({direction: 'from-bottom'})` with `springTiming` for a Shorts-native upward push feel |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `npx tsc --noEmit --skipLibCheck` | TypeScript check before render | Run from `remotion/` after adding `@remotion/transitions`; `--skipLibCheck` required for Remotion's own type quirks (documented in CLAUDE.md) |
| `node scripts/render.mjs <props>` | Manual render test | Use to validate Ken Burns + transition changes before wiring into Python pipeline |

---

## Installation

```bash
# From remotion/ directory — MUST use exact version matching remotion@4.0.441
cd remotion
npm install @remotion/transitions@4.0.441 --save-exact
```

No new Python packages needed — `edge-tts` prosody params already exist in the installed version; `pydantic` is available transitively.

---

## API Patterns

### Ken Burns: Adding Pan to the Existing Effect

The current `VideoShort.tsx` only animates `scale`. Add `translateX` / `translateY` using the same `interpolate()` call pattern.

**Confidence: HIGH** — verified against [remotion.dev/docs/animating-properties](https://www.remotion.dev/docs/animating-properties) and [remotion.dev/docs/interpolate](https://www.remotion.dev/docs/interpolate).

```tsx
// Direction variants — pick one per image deterministically (e.g. i % 4)
const panVariants = [
  { tx: [0, 20], ty: [0, 0] },   // drift right
  { tx: [20, 0], ty: [0, 0] },   // drift left
  { tx: [0, 0],  ty: [0, 20] },  // drift down
  { tx: [0, 0],  ty: [20, 0] },  // drift up
];
const variant = panVariants[i % panVariants.length];

const translateX = interpolate(localFrame, [0, framesPerImage], variant.tx, {
  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
});
const translateY = interpolate(localFrame, [0, framesPerImage], variant.ty, {
  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
});

// In style:
transform: `scale(${scale}) translateX(${translateX}px) translateY(${translateY}px)`
```

Keep the existing scale range (1.0→1.04) — subtle zoom is intentional. A 20px pan on a 1080px canvas is ~1.85%, which reads as motion without feeling shaky.

### Scene Transitions: @remotion/transitions with slide()

**Confidence: HIGH** — verified against [remotion.dev/docs/transitions](https://www.remotion.dev/docs/transitions/) and [remotion.dev/docs/transitions/transitionseries](https://www.remotion.dev/docs/transitions/transitionseries).

No built-in `zoom` presentation exists in `@remotion/transitions`. The available built-ins are: `fade`, `slide`, `wipe`, `flip`, `clockWipe`, `iris`. For a Shorts-energy "push" feel, `slide({direction: 'from-bottom'})` with `springTiming` is the correct choice — it is a push transition (entering scene slides up and displaces the exiting one).

```tsx
import { TransitionSeries, springTiming } from '@remotion/transitions';
import { slide } from '@remotion/transitions/slide';

// Replace the current Sequence-per-image approach with TransitionSeries:
<TransitionSeries>
  {imagePaths.map((imgPath, i) => (
    <React.Fragment key={i}>
      <TransitionSeries.Sequence durationInFrames={framesPerImage}>
        <KenBurnsImage src={staticFile(imgPath)} index={i} />
      </TransitionSeries.Sequence>
      {i < imagePaths.length - 1 && (
        <TransitionSeries.Transition
          presentation={slide({ direction: 'from-bottom' })}
          timing={springTiming({ config: { damping: 200 }, durationInFrames: 20 })}
        />
      )}
    </React.Fragment>
  ))}
</TransitionSeries>
```

**Duration accounting:** `TransitionSeries` shortens total duration by the transition length. For N images each `framesPerImage` long with (N-1) transitions of 20 frames each: `totalFrames = N * framesPerImage - (N-1) * 20`. Adjust `framesPerImage` calculation accordingly.

**Damping 200** disables spring overshoot — gives a snappy deceleration without bouncing, which suits Shorts pacing.

**Custom zoom presentation (if slide is rejected):** If a scale-based zoom is required instead, implement `TransitionPresentation` using `presentationProgress` to drive `scale`:

```tsx
// zoom-push.tsx
import type { TransitionPresentation, TransitionPresentationComponentProps } from '@remotion/transitions';

const ZoomPushComponent: React.FC<TransitionPresentationComponentProps<{}>> = ({
  children, presentationDirection, presentationProgress,
}) => {
  const scale = presentationDirection === 'entering'
    ? interpolate(presentationProgress, [0, 1], [1.15, 1.0])
    : interpolate(presentationProgress, [0, 1], [1.0, 0.85]);
  return (
    <AbsoluteFill style={{ transform: `scale(${scale})`, overflow: 'hidden' }}>
      {children}
    </AbsoluteFill>
  );
};

export const zoomPush = (): TransitionPresentation<{}> => ({
  component: ZoomPushComponent, props: {},
});
```

### TTS Prosody: edge-tts Communicate Parameters

**Confidence: HIGH** — verified against [edge-tts source on GitHub](https://github.com/rany2/edge-tts/blob/master/src/edge_tts/communicate.py). Version 7.2.8 is the latest (released 2026-03-22).

The `Communicate` class constructor accepts prosody as keyword-only args:

```python
# Communicate.__init__ signature (from source):
# def __init__(self, text, voice, *, rate="+0%", volume="+0%", pitch="+0Hz", ...)

communicate = edge_tts.Communicate(
    text,
    voice,
    rate="+25%",    # +25% faster — energetic but not chipmunk
    pitch="+10Hz",  # slight pitch lift — reduces monotone feeling
    volume="+0%",   # leave volume neutral; Remotion Audio handles mix
)
```

**Rate format:** percentage string, e.g. `"+25%"`, `"-10%"`. Must include sign.
**Pitch format:** Hz string, e.g. `"+10Hz"`, `"+50Hz"`. Must include sign.
**Volume format:** percentage string, same rules.

**Recommended starting values for Shorts:**
- `rate="+20%"` to `"+30%"` — native English Shorts pacing is ~160-180 WPM; neural voices default around 140 WPM
- `pitch="+5Hz"` to `"+15Hz"` — subtle lift avoids sounding artificial

**Update point in `src/classes/Tts.py`:** The `_edge_tts_synthesize` function passes only `text` and `voice` to `Communicate`. Add `rate` and `pitch` parameters sourced from `config.json` via new getter functions, with sensible defaults.

### LLM Hook Generation: Ollama Structured Output

**Confidence: HIGH** — verified against [docs.ollama.com/capabilities/structured-outputs](https://docs.ollama.com/capabilities/structured-outputs).

Use Ollama's `format=` parameter with a Pydantic schema to force structured output. This avoids fragile string parsing and works with any Ollama-served model.

```python
from pydantic import BaseModel
from ollama import chat

class HookOutput(BaseModel):
    hook_type: str   # "question" | "stat" | "bold"
    hook_text: str   # the opening sentence, ≤15 words

def generate_hook(topic: str, model: str) -> HookOutput:
    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write opening hooks for YouTube Shorts. "
                    "A hook must stop the scroll in 3 seconds. "
                    "Output ONLY valid JSON matching the provided schema. "
                    "hook_type must be one of: question, stat, bold. "
                    "hook_text must be 10-15 words, punchy, no filler words."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n"
                    "Write a single hook sentence. Choose the type that best fits the topic:\n"
                    "- question: opens with a rhetorical question ('Did you know...' / 'What if...')\n"
                    "- stat: leads with a surprising number or fact ('90% of people...')\n"
                    "- bold: makes a provocative or counterintuitive claim\n\n"
                    f"Output JSON matching this schema:\n{HookOutput.model_json_schema()}"
                ),
            },
        ],
        format=HookOutput.model_json_schema(),
    )
    return HookOutput.model_validate_json(response.message.content)
```

**Injection point:** `YouTube.generate_script()` calls `generate_text(prompt)` in `llm_provider.py`. The hook should be generated first, then injected as a constraint into the script prompt: "Begin with this exact sentence: {hook.hook_text}". This prevents the LLM from rewriting the hook in the script pass.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `@remotion/transitions` `slide()` | Custom `zoomPush` presentation | Only if product review decides scale-in/out feels better than push; custom implementation is ~20 lines (pattern above) |
| `interpolate()` for Ken Burns pan | `spring()` for pan | `spring()` is better when snap-to-final is needed; for slow continuous drift, `interpolate()` with linear extrapolation is simpler and more predictable |
| `edge-tts` prosody kwargs | Switching to ElevenLabs | ElevenLabs gives more expressive control but requires paid API key — explicitly out of scope per PROJECT.md |
| Ollama `format=` structured output | String parsing on free-text LLM output | Only use free-text if the local model doesn't support `format=`; all current Ollama models support it |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| CSS `transition:` or `animation:` on JSX elements in Remotion | Remotion renders each frame in isolation — CSS transitions are stateless per frame and produce flickering artifacts. Official docs explicitly warn against this. | `interpolate()` or `spring()` driven by `useCurrentFrame()` |
| `^` version prefix on `@remotion/transitions` in package.json | All `@remotion/*` packages must be at exactly the same version as `remotion`. A semver range risks pulling a different patch that breaks the version parity requirement. | `--save-exact` or pin manually in package.json |
| `MoviePy` for Ken Burns or transitions | Python-layer image manipulation cannot sync frame-accurate motion with the audio timeline that Remotion controls. Already marked as fallback-only in the existing codebase. | Remotion `interpolate()` inside `VideoShort.tsx` |
| SSML string wrapping in `edge-tts` | Microsoft's Edge TTS service rejects custom SSML that wasn't generated by Edge itself — the library explicitly removed SSML support for this reason. The prosody kwargs are the only supported control surface. | `rate=`, `pitch=`, `volume=` kwargs on `Communicate` |
| Hardcoded hook templates | Rules can't match tone to topic; LLM adapts phrasing to context (science fact vs. shocking stat vs. conspiracy question) | `generate_hook()` with Ollama structured output |

---

## Stack Patterns by Variant

**If the model used with Ollama does not support structured output `format=`:**
- Fall back to prompting for a JSON code block and parsing with `json.loads()` after stripping markdown fences
- Add a retry loop (max 2 retries) to handle malformed output
- Flag in config: `"hook_structured_output": false`

**If `springTiming` transition feels too snappy on slow hardware render:**
- Switch to `linearTiming({durationInFrames: 20})` — deterministic, no spring physics computation
- Spring is preferred for visual quality but linear is safe fallback

**If prosody values need per-category tuning (breaking news vs. science facts):**
- Store `tts_rate` and `tts_pitch` in `config.json` per category preset
- Read via `src/config.py` getter; pass through to `TTS.synthesize()`
- Current recommendation: single global value is sufficient for MVP

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `remotion@4.0.441` | `@remotion/transitions@4.0.441` | Must be identical version — Remotion enforces this at runtime and throws if mismatched |
| `@remotion/transitions@4.0.441` | `react@18.3.1` | Confirmed compatible — `react@18` is current Remotion 4 requirement |
| `edge-tts@7.2.8` | Python 3.12 | Latest release 2026-03-22; async API unchanged, only adds `boundary` and proxy params since v6 |
| `ollama` Python SDK | Pydantic v2 | `format=model_json_schema()` requires Pydantic v2 for `model_json_schema()` method; Pydantic v1 uses `.schema()` instead |

---

## Sources

- [remotion.dev/docs/animating-properties](https://www.remotion.dev/docs/animating-properties) — confirmed `interpolate()` + `useCurrentFrame()` as the only safe animation pattern; CSS transitions explicitly warned against
- [remotion.dev/docs/interpolate](https://www.remotion.dev/docs/interpolate) — parameter syntax, `extrapolateLeft/Right: 'clamp'` pattern
- [remotion.dev/docs/transitions/](https://www.remotion.dev/docs/transitions/) — `@remotion/transitions` package, available from v4.0.53, built-in presentations list
- [remotion.dev/docs/transitions/transitionseries](https://www.remotion.dev/docs/transitions/transitionseries) — `TransitionSeries` usage, duration accounting, `springTiming` vs `linearTiming`
- [remotion.dev/docs/transitions/presentations/custom](https://www.remotion.dev/docs/transitions/presentations/custom) — `TransitionPresentation` API, `presentationDirection`, `presentationProgress`
- [remotion.dev/docs/transitions/presentations/slide](https://www.remotion.dev/docs/transitions/presentations/slide) — `slide()` direction options confirmed: `from-left`, `from-right`, `from-top`, `from-bottom`
- [github.com/rany2/edge-tts — communicate.py](https://github.com/rany2/edge-tts/blob/master/src/edge_tts/communicate.py) — `Communicate.__init__` signature confirmed: `rate`, `pitch`, `volume` as keyword-only str args with defaults `"+0%"`, `"+0Hz"`, `"+0%"`
- [pypi.org/project/edge-tts](https://pypi.org/project/edge-tts/) — version 7.2.8, released 2026-03-22 (HIGH confidence)
- [docs.ollama.com/capabilities/structured-outputs](https://docs.ollama.com/capabilities/structured-outputs) — `format=model_json_schema()` pattern with Pydantic, recommendation to include schema in prompt text
- `remotion/node_modules/remotion/package.json` — installed version 4.0.441 (verified locally)

---

*Stack research for: YouTube Shorts engagement features (Ken Burns, transitions, TTS prosody, hook generation)*
*Researched: 2026-03-30*
