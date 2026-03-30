# Project Research Summary

**Project:** MoneyPrinterV2 — Video Engagement Upgrade
**Domain:** YouTube Shorts faceless video automation — engagement features (motion, hooks, transitions, TTS prosody)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

MoneyPrinterV2 already has a working end-to-end YouTube Shorts pipeline. This milestone is a focused engagement upgrade: four targeted changes that together transform flat, static clips into scroll-stopping content. Research confirms that all four features (Ken Burns pan, zoom-push scene transitions, LLM-selected hooks, TTS prosody rate) are achievable using existing dependencies with minimal new package requirements — `@remotion/transitions` is the only addition needed.

The recommended approach is to implement changes in dependency order: TTS prosody first (isolated Python change, no risk), hook generation second (new Ollama call in Python, no Remotion changes), then zoom-push transitions last (the highest-complexity change, requiring a Remotion component refactor and the new npm package). Ken Burns pan requires no code — existing scale animation just needs pan vectors added to the same `interpolate()` calls. No new paid APIs are required and the props JSON contract between Python and Remotion does not need to change for this milestone.

The primary risks are (1) `TransitionSeries` silently shortening video duration below TTS audio length, and (2) the LLM hook being semantically disconnected from the script body. Both are preventable by design: anchor `durationInSeconds` to the audio file and generate the hook from the already-generated script text rather than from the topic string alone. The `pitch=` parameter in `edge-tts` is silently ignored since v6.0.3 — `rate` is the only reliable prosody lever.

## Key Findings

### Recommended Stack

All four engagement features are implemented entirely within the existing tech stack. The only new dependency is `@remotion/transitions@4.0.441` (must exactly match the installed `remotion` version — Remotion enforces version parity at runtime). No Python packages are needed beyond what is already installed. `edge-tts 7.2.8` supports `rate=` as a constructor keyword arg with no upgrade required. `pydantic` (available transitively) enables structured Ollama output for hook generation.

**Core technologies:**
- `remotion@4.0.441` (installed): Frame-accurate video rendering — `interpolate()` + `useCurrentFrame()` are the only safe animation primitives; CSS transitions produce render flicker
- `@remotion/transitions@4.0.441` (new): `TransitionSeries` + `slide()` / custom `zoomPush()` presentations — must be pinned with `--save-exact` to prevent version drift
- `edge-tts@7.2.8` (installed): TTS prosody via `rate="+20%"` constructor kwarg — `pitch=` silently no-ops since v6.0.3; do not expose as a config option
- `ollama` Python SDK (installed): Structured hook generation via `format=model_json_schema()` with Pydantic — avoids fragile string parsing; all Ollama models support this

### Expected Features

Research confirms a clear P1/P2/P3 split. The four requirements from PROJECT.md all land at P1 — they are the minimum to move from "flat clip" to "scroll-stopping clip."

**Must have (table stakes — this milestone):**
- Strong 3-second hook (spoken + on-screen via subtitles) — 50-60% of viewers drop in the first 3 seconds; algorithm penalizes below 70% intro retention
- Ken Burns motion on images — static faceless content reads as screensaver; motion provides the pattern interrupt that delays the swipe
- Zoom/push scene transitions — hard cuts read as low-effort; 15-20 frame push transition at 30fps adds production value at near-zero cost
- Energetic TTS narration (`rate="+20%"` global) — monotone voice is an instant credibility signal for spam; faster rate mirrors native Shorts pacing (~160-180 WPM)

**Should have (after v1 validated):**
- Per-image motion direction variety (`zoomIn`, `panLeft`, `panRight`, `panDown`) — reduces "templated slideshow" appearance; low complexity once Ken Burns base works
- Per-segment TTS prosody — hook at higher rate, body at base rate; requires multi-call TTS concatenation; add only if flat global rate is insufficient
- Looping narrative structure — YouTube counts each loop as a new view (March 2025 change); callback ending + first/last frame match

**Defer (v2+):**
- Word-level subtitle highlighting — requires reliable Whisper word timestamps; high Remotion timing complexity
- Dynamic text callouts / lower thirds — high per-scene sync cost
- TTS provider swap to ElevenLabs — revisit only if `rate` tuning fails to lift retention; paid API cost must be justified

### Architecture Approach

The architecture has a clean Python-to-Node.js boundary enforced by a props JSON file. All visual effects live exclusively in Remotion TypeScript components; Python stages static assets and calls `node scripts/render.mjs`. This boundary must not be violated — implementing Ken Burns in MoviePy/Pillow would produce frame-inaccurate motion that cannot sync with Remotion's audio timeline. No props schema changes are needed for this milestone: hook text flows through the existing `script` field (prepended in Python before TTS), Ken Burns and transitions use the existing `imagePaths` + `durationInSeconds` fields, and prosody is baked into the WAV before Remotion sees it.

**Major components:**
1. `YouTube.generate_hook()` (NEW in `src/classes/YouTube.py`) — Ollama call generating a typed hook sentence; prepends to `self.script` before TTS synthesis
2. `Tts.py` `_edge_tts_synthesize()` (MODIFIED) — adds `rate="+20%"` to `edge_tts.Communicate()` constructor; reads value from `config.json` via new getter
3. `remotion/src/transitions/ZoomPush.tsx` (NEW) — custom `TransitionPresentation` driving `scale` via `presentationProgress`; entering scene zooms from 1.15 to 1.0, exiting from 1.0 to 0.9
4. `remotion/src/VideoShort.tsx` `ImageSlideshow` (MODIFIED) — replaces opacity cross-fade with `<TransitionSeries>` wrapping existing Ken Burns per-image components

### Critical Pitfalls

1. **TransitionSeries silently shortens video duration** — `TransitionSeries` overlaps adjacent sequences by the transition duration; a 10-scene video with 20-frame transitions loses 9×20=180 frames. Fix: compute `framesPerImage = Math.floor((totalFrames + (n-1)*TRANSITION_FRAMES) / n)` so the sum minus overlaps equals the audio-derived `durationInFrames`. Never use raw `imagePaths.length * framesPerImage` as total duration after adding transitions.

2. **Ken Burns pan exposing black edges** — a 4% scale-up (1.0→1.04) provides only ~21px of edge buffer on a 1080px canvas. Adding 20px `translateX` perfectly exhausts this buffer. Fix: keep pan magnitude at or below `(width * (scale - 1)) / 2`; use `overflow: hidden` on the wrapping `<AbsoluteFill>` as a safety net; or increase scale range to 1.0→1.08 if noticeable pan is desired.

3. **edge-tts pitch parameter is silently ignored** — `pitch=` was removed from the Microsoft service in v6.0.3; passing it produces identical output with no error. Fix: do not add `pitch` to `Communicate()` or expose it as a config option; rely solely on `rate`.

4. **LLM hook semantically disconnected from script body** — generating the hook from `topic` alone (without the script text) causes semantic drift: the hook promises something the body does not deliver, spiking the algorithm-weighted drop-off curve after second 5. Fix: pass the generated `script` text to the hook prompt, not just the topic; or use a combined single-prompt approach with structured output `{ "hook": "...", "body": "..." }`.

5. **LLM hook contains formatting marks read aloud by TTS** — local Ollama models frequently prepend "Hook:", add asterisks, or wrap output in quotes despite `ONLY RETURN` instructions. Fix: apply stripping regex unconditionally (`re.sub(r'[*"#\n]', ...)`, strip leading label prefixes); add a retry with template fallback after 2 failures.

## Implications for Roadmap

Research establishes a clear dependency chain that determines implementation order. All four features are P1 and ship together, but the safe build sequence within that phase is dictated by what each feature depends on. TTS prosody must come before Ken Burns (prosody affects audio duration which drives frame timing). Hook generation must come before TTS (hook is prepended to the script the TTS consumes). Remotion transitions wrap Ken Burns scenes, so Ken Burns logic must be preserved when refactoring `ImageSlideshow`.

### Phase 1: TTS Prosody Rate

**Rationale:** Zero dependencies on other features; isolated to a single Python file (`Tts.py`); immediately testable by listening to the output WAV. Completing this first confirms the rate value sounds correct before it influences Ken Burns frame timing calculations.
**Delivers:** Energetic narration at `rate="+20%"` (configurable via `config.json`); audible difference from baseline
**Addresses:** Monotone voice (table-stakes feature); energetic narration requirement from PROJECT.md
**Avoids:** Pitch false-expectation pitfall — do not add `pitch` param; document the v6.0.3 removal

### Phase 2: Hook Generation

**Rationale:** Depends only on Ollama (already confirmed working). Hook must be prepended to `self.script` before TTS and subtitle generation run, so it must be implemented before full pipeline integration testing. No Remotion changes required.
**Delivers:** LLM-selected hook sentence (question/stat/bold) injected as first line of every script; Whisper subtitles automatically include hook text from frame 0
**Uses:** Ollama SDK `format=model_json_schema()` with Pydantic `HookOutput` model
**Implements:** `YouTube.generate_hook()` new method; call order in `generate_video()` becomes `generate_topic() → generate_hook() → generate_script()`
**Avoids:** Hook/script semantic disconnect — pass generated `script` text to hook prompt; apply stripping regex to output unconditionally

### Phase 3: Ken Burns Pan Enhancement

**Rationale:** Ken Burns scale animation already works (existing `interpolate()` on scale). Adding pan (`translateX`/`translateY`) is an additive change to the existing `interpolate()` call pattern — no structural refactor needed. Must be completed before Phase 4 (transitions wrap Ken Burns scenes inside `TransitionSeries.Sequence`).
**Delivers:** Per-image directional drift (4 variants cycling by index: drift right, drift left, drift down, drift up) in addition to existing zoom-in/zoom-out
**Uses:** Remotion `interpolate()` with `extrapolateLeft/Right: "clamp"` — all existing calls already follow this convention
**Implements:** Adds `translateX`/`translateY` interpolation to `ImageSlideshow` per-image render; validates no black edges at scale 1.04 + 20px pan
**Avoids:** Black edge exposure — keep pan at or below `(1080 * (scale-1)) / 2 ≈ 21px`; use `overflow: hidden` wrapper; `interpolate` clamp runaway — all new calls must include `extrapolateRight: "clamp"`

### Phase 4: Zoom-Push Scene Transitions

**Rationale:** Highest complexity change; depends on Ken Burns being stable inside `TransitionSeries.Sequence`. Requires npm install, a new TypeScript file, and structural refactor of `ImageSlideshow`. Must be last to avoid disrupting earlier phases during integration.
**Delivers:** Animated zoom-push between scenes replacing opacity cross-fade; visually distinct production value
**Uses:** `@remotion/transitions@4.0.441` (new npm package, `--save-exact`); `TransitionSeries`, `linearTiming` or `springTiming`; custom `ZoomPush.tsx` presentation
**Implements:** `remotion/src/transitions/ZoomPush.tsx` (new); `ImageSlideshow` refactored to `<TransitionSeries>` with `<TransitionSeries.Sequence>` per image and `<TransitionSeries.Transition>` between each
**Avoids:** Duration shortening — compute `framesPerImage = Math.floor((totalFrames + (n-1)*TRANSITION_FRAMES) / n)`; float precision — round `durationInSeconds` to 3 decimal places in Python before writing props JSON; add 0.1s padding in `Root.tsx`

### Phase Ordering Rationale

- TTS prosody before Ken Burns because `rate="+20%"` shortens audio duration, which is the authoritative input for Ken Burns frame timing — test prosody first to lock the duration
- Hook generation before TTS pipeline integration because the hook is prepended to `self.script` before the TTS call that produces the audio Ken Burns timing is based on
- Ken Burns pan before transitions because `TransitionSeries.Sequence` wraps the per-image Ken Burns component — the inner component must be stable before the wrapper is added
- Transitions last because they require the only new npm package and the most structural Remotion refactor — isolating this risk to the final phase prevents it from blocking earlier integration tests

### Research Flags

Phases with standard, well-documented patterns (research-phase not needed):
- **Phase 1 (TTS Prosody):** Isolated Python change; API confirmed from edge-tts source; no unknowns
- **Phase 3 (Ken Burns Pan):** Additive to existing working code; Remotion `interpolate()` is well-documented

Phases that may benefit from a brief implementation spike before coding:
- **Phase 2 (Hook Generation):** Hook quality depends on local Ollama model behavior — the structured output pattern is confirmed, but prompt wording will need iteration. Plan for 2-3 prompt refinement cycles; add a template fallback from day one.
- **Phase 4 (Zoom-Push Transitions):** Duration accounting with `TransitionSeries` is the main risk. Strongly recommend writing a unit test / render assertion that verifies `computedTransitionSeriesDuration === durationInSeconds * fps` before considering this phase done.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All API signatures verified against official docs and source code; installed versions confirmed locally |
| Features | MEDIUM-HIGH | Table stakes and P1 features backed by multiple third-party analytics sources; exact retention lift numbers (23%, 72%) are from practitioner blogs, not YouTube's own data releases |
| Architecture | HIGH | Claims verified against existing codebase (`VideoShort.tsx`, `Tts.py`, `YouTube.py`, `types.ts`) and official Remotion docs; no schema changes confirmed by examining current props contract |
| Pitfalls | HIGH | Critical pitfalls from official docs (Remotion, edge-tts); pitch removal corroborated by multiple independent sources; TransitionSeries duration math confirmed from Remotion docs |

**Overall confidence:** HIGH

### Gaps to Address

- **Hook prompt quality:** The hook generation prompt is a starting point — actual output quality depends on which Ollama model is running locally (7B vs 13B vs 70B produce different adherence to constraints). Plan for prompt iteration; the template fallback is not optional.
- **TTS pitch effectiveness:** Research is split — some sources say pitch was fully removed in v6.0.3, others suggest it may have server-side inconsistency. Confirm by empirical test before deciding whether to expose as a config option. Current recommendation: do not expose it.
- **TransitionSeries springTiming on slow render hardware:** `springTiming` uses physics simulation per-frame which adds minor render latency. If render time on the production machine is a concern, default to `linearTiming` which is fully deterministic. Test on actual hardware before committing to spring.
- **Hook semantic alignment validation:** No automated way to verify that the hook matches the script body without human review. Build the combined single-prompt approach (hook + body in one call) as the default, not the fallback, to eliminate the alignment risk structurally.

## Sources

### Primary (HIGH confidence)
- https://www.remotion.dev/docs/animating-properties — confirmed `interpolate()` + `useCurrentFrame()` as only safe animation pattern; CSS transitions explicitly warned against
- https://www.remotion.dev/docs/transitions/ — `@remotion/transitions` package, available from v4.0.53, built-in presentations, `TransitionSeries` usage
- https://www.remotion.dev/docs/transitions/transitionseries — duration accounting formula, `springTiming` vs `linearTiming`
- https://www.remotion.dev/docs/transitions/presentations/custom — `TransitionPresentation` API, `presentationProgress`, `presentationDirection`
- https://github.com/rany2/edge-tts/blob/master/src/edge_tts/communicate.py — `Communicate.__init__` signature confirmed; `rate`, `pitch`, `volume` as keyword-only str args
- https://docs.ollama.com/capabilities/structured-outputs — `format=model_json_schema()` pattern with Pydantic
- `remotion/node_modules/remotion/package.json` — installed version 4.0.441 verified locally

### Secondary (MEDIUM confidence)
- https://www.shortimize.com/shortimize.com/blog/youtube-shorts-retention-rate — 50-60% drop in first 3 seconds; 70% intro retention threshold
- https://www.opus.pro/blog/youtube-shorts-hook-formulas — three hook archetypes (question, stat, payoff-preview)
- https://cloudinary.com/guides/image-effects/ken-burns-effect-complete-guide-and-how-to-apply-it — safe zoom range (1.0→1.12); pan percentage guidelines
- https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide — energy transition vs fade; loop counting since March 2025
- https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/ — hook formula validation; 72% viral Shorts use fast-paced editing
- edge-tts pitch removal — corroborated by edge-tts-ext PyPI page and community reports; MEDIUM confidence (no single authoritative source)

### Tertiary (LOW confidence)
- https://crepal.ai/blog/aivideo/blog-how-to-fix-remotion-audio-out-of-sync/ — audio sync troubleshooting patterns (practitioner blog)
- https://markaicode.com/ollama-structured-output-pipeline/ — Ollama structured output reliability discussion

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
