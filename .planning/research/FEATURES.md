# Feature Research

**Domain:** YouTube Shorts engagement — motion, hooks, transitions, voice energy
**Researched:** 2026-03-30
**Confidence:** MEDIUM-HIGH (backed by 2025-2026 sources; exact retention lift numbers from third-party blogs, not YouTube's own data releases)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that high-performing Shorts have as standard. Without these, a generated clip feels amateurish and the algorithm deprioritizes it.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Strong 3-second hook | 50-60% of viewers drop in first 3 seconds; algorithm measures intro retention; below 70% intro retention = suppressed distribution | MEDIUM | Hook must be audio + visual — text overlay alone lifts watch time ~18%; a spoken question/stat/payoff-preview is the minimum |
| Motion on images (Ken Burns) | Faceless channels with purely static images feel like screensavers; viewers expect visual velocity; motion provides the "pattern interrupt" that prevents immediate swipe | MEDIUM | Remotion has a free Ken Burns template; `interpolate()` + CSS `transform: scale/translate` is the implementation path; zoom-in vs zoom-out vs diagonal pan all perform differently |
| Subtitles / on-screen text | 60%+ of Shorts are watched without sound on mobile; subtitles are now viewer-expected; missing them loses a majority of impressions | LOW (existing) | Already implemented via Whisper; not in scope for this milestone but must remain functional |
| Audible, energetic narration | Monotone TTS is an instant credibility kill for educational/fact-based Shorts; viewers associate flat voice with low-effort spam | MEDIUM | edge-tts supports `--rate` and `--pitch` as percentage adjustments; a single `<prosody>` tag is the only SSML permitted by Microsoft's backend |
| Visual change every 10-20 seconds | Viewers expect rapid scene cuts matching fast-paced editing norms set by TikTok/Reels; dead air or static holds longer than ~4s spike drop-off | MEDIUM | For AI-image Shorts under 30s this means every scene (one image = one scene) must have internal motion AND a distinct transition at cut |

### Differentiators (Competitive Advantage)

Features that separate a generated Short from the mass of low-effort faceless clips.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hook type matched to topic (LLM-selected) | Generic hooks ("Did you know...") perform worse than topic-matched hooks; LLM can select question/stat/payoff-preview based on content type | MEDIUM | Prompt engineering task in `YouTube.generate_script()`; three proven hook archetypes: question (relatable self-identification), direct stat (concrete number), payoff preview (show end result first) |
| Zoom/push scene transitions (not hard cuts) | Hard cuts between static images feel cheap; a 15-20 frame push or zoom transition adds production value with zero manual effort; 72% of viral Shorts (>1M views) use fast-paced editing with energy transitions | MEDIUM | Remotion `@remotion/transitions` package (`TransitionSeries`, `slide()` presentation) is the implementation path; zoom presentation or custom scale interpolation also viable |
| Per-image motion direction variety | Ken Burns that always zooms in the same direction reads as templated; varying direction (zoom-in, zoom-out, pan-left, pan-right, diagonal drift) per scene prevents the "slideshow" feel | LOW | Implement as a parameter array in Remotion props JSON — Python passes `motionDirection` per scene; Remotion picks the transform accordingly |
| Looping narrative structure | Since March 2025, YouTube counts each loop as a new view for Shorts; ending on the same visual that opened creates seamless loop potential | MEDIUM | Requires script-level awareness: LLM should be prompted to write a callback ending; visual requires first and last frame to match or dissolve |
| Prosody variation across script sections | Hook sentence at higher pitch/faster rate, content body at base rate, CTA at slightly slower rate with emphasis — mirrors how skilled narrators work | MEDIUM | Requires splitting TTS into segments with different prosody tags; more complex than a single global `<prosody>` wrapper; edge-tts allows only one `<prosody>` tag per call, so multi-segment means multiple TTS calls concatenated |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Fade transitions between scenes | Seems polished; easy to implement | Fade = low energy; creates dead time; feels like a 2015 PowerPoint; directly hurts retention for Shorts format where energy = engagement | Use push/slide/zoom transitions; reserve fade only for intro-to-first-scene if needed |
| Elaborate animated subtitle effects (word bounce, highlight karaoke) | Looks impressive in demos; seen on high-view clips | High implementation complexity in Remotion; word-level timing requires Whisper word timestamps which may be unreliable; distracts from image motion; scope risk for this milestone | Ship plain subtitles first; defer word-highlight to a dedicated subtitle milestone |
| Voice cloning / ElevenLabs swap | Premium voice quality; sounds more human | Requires paid API key; breaks the "no new paid API" constraint; ElevenLabs costs compound with volume; edge-tts prosody tuning achieves 80% of the engagement benefit at zero cost | Tune edge-tts rate (+15-25%) and pitch (+5-10Hz) first; validate retention impact before considering provider swap |
| Dynamic text overlays (stats, callouts, lower thirds) | Adds information density; looks high-production | Each overlay needs manual timing sync with script; requires significant Remotion component work; hook text is already covered by subtitles | Ship one well-executed subtitle track; add callouts in a later polish milestone |
| Hard-coded hook templates | Fast to implement; predictable output | Generic templates ("Did you know X?") are now pattern-recognized by viewers as low-effort; LLM-matched hooks outperform templates because they align tone to topic | LLM selects hook archetype + generates the line; templates as fallback only if LLM fails |
| Transition sound effects (whoosh, swipe) | Feels energetic; common on viral clips | Requires royalty-free sound library management; mixing audio complexity spikes; edge-tts audio track + background music (if any) + SFX = 3-track problem; high implementation cost for marginal gain | Skip sound effects for this milestone; focus on visual transitions and voice energy |

---

## Feature Dependencies

```
Hook Generation (LLM)
    └──feeds──> Script (first sentence injected)
                    └──feeds──> TTS rendering
                                    └──requires──> Prosody settings (rate/pitch)

Ken Burns Effect (Remotion)
    └──requires──> Per-image timing data (duration per scene)
                       └──derived from──> TTS audio duration
                                              └──requires──> Script finalized

Scene Transitions (Remotion TransitionSeries)
    └──requires──> Multiple scenes defined in Remotion composition
    └──requires──> Per-image motion (Ken Burns) already working
                       (transitions wrap Ken Burns scenes — order matters)

Prosody Tuning (edge-tts)
    └──requires──> kittentts wrapper updated to accept rate/pitch params
    └──feeds──> TTS audio duration (faster rate = shorter audio = shorter video)
                    └──affects──> Ken Burns timing (must re-derive durations)

Per-scene Motion Direction Variety
    └──requires──> Ken Burns Effect implemented
    └──enhances──> Ken Burns Effect (adds variation)

Looping Narrative Structure
    └──requires──> Hook Generation (LLM must write callback ending)
    └──enhances──> All visual features (first/last frame match)
```

### Dependency Notes

- **Ken Burns requires per-image duration data:** The zoom/pan animation must know how long each image is on screen. This duration comes from TTS audio length divided by scene count, which means TTS must complete before Remotion props are assembled.
- **Prosody tuning affects Ken Burns timing:** Faster speech rate reduces total audio duration. If prosody is tuned, the duration calculation for Ken Burns must account for the new shorter audio length — not the un-tuned baseline.
- **Transitions wrap Ken Burns scenes:** `TransitionSeries` in Remotion places transitions between scene components. The Ken Burns component is what goes *inside* each scene. Ken Burns must be implemented before transitions can wrap it.
- **Hook generation feeds script, not just the first frame:** The hook sentence determines what appears on-screen in the first 3 seconds. If the hook is a question, the image for scene 1 should visually reinforce the question — this is a prompt engineering concern downstream.

---

## MVP Definition

### Launch With (v1) — This Milestone

Minimum set to move from "flat clip" to "scroll-stopping clip."

- [ ] **Hook generation** — LLM selects archetype (question / stat / payoff-preview) and writes opening sentence; injected as first sentence in script; no topic-specific image dependency required for v1
- [ ] **Ken Burns effect on all images** — slow drift (zoom-in or zoom-out) with direction varying per scene; implemented as Remotion `interpolate()` on `scale` and `translateX/Y`; duration derived from TTS audio divided by scene count
- [ ] **Zoom/push transitions between scenes** — using `@remotion/transitions` `TransitionSeries`; 15-20 frame transition duration; push or slide presentation (not fade)
- [ ] **TTS prosody: rate +15-25%, pitch +5-10Hz** — global `<prosody>` wrapper via edge-tts `--rate` and `--pitch` flags; single value applied to full script for v1

### Add After Validation (v1.x)

Add once v1 ships and retention data is observable.

- [ ] **Per-segment prosody** — hook sentence at higher rate/pitch, body at base, CTA slower; requires multi-call TTS concatenation; add if flat rate lift is insufficient
- [ ] **Looping narrative structure** — LLM prompt updated to write callback ending; first/last frame match added to Remotion composition; add if replay rate data justifies the work
- [ ] **Per-image motion direction parameter** — Python passes `motionDirection` per scene in props JSON; reduces "templated" appearance; low complexity once Ken Burns base is working

### Future Consideration (v2+)

Defer until core engagement features are validated.

- [ ] **Word-level subtitle highlighting** — requires Whisper word timestamps; high complexity; defer to dedicated subtitle milestone
- [ ] **Dynamic text callouts** — lower thirds, stat overlays; high manual timing sync cost; defer to polish milestone
- [ ] **TTS provider swap (ElevenLabs)** — revisit only if prosody tuning does not lift retention adequately; paid API cost must be justified by measurable retention improvement

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Hook generation (LLM) | HIGH — first 3 seconds is the retention gate | LOW — prompt engineering + script injection | P1 |
| Ken Burns on images | HIGH — 23% retention lift for motion vs static opening; critical for faceless format | MEDIUM — Remotion interpolate() + duration sync | P1 |
| Zoom/push transitions | MEDIUM-HIGH — energy signal; differentiates from hard-cut spam | MEDIUM — TransitionSeries wrapping existing scenes | P1 |
| TTS prosody tuning (global) | MEDIUM — monotone = low-effort signal; energetic voice increases credibility | LOW — edge-tts `--rate`/`--pitch` flags; wrapper update | P1 |
| Per-image motion direction variety | MEDIUM — prevents "templated slideshow" look | LOW — parameter array in props JSON | P2 |
| Per-segment prosody | MEDIUM — hook sentence should feel more urgent than body | MEDIUM — multi-call TTS concatenation | P2 |
| Looping narrative structure | MEDIUM — March 2025 loop-count change makes this high ROI | MEDIUM — LLM prompt + Remotion first/last frame match | P2 |
| Word-level subtitle highlight | LOW-MEDIUM — visually impressive but complex | HIGH — word timestamps, Remotion timing sync | P3 |
| Dynamic text callouts | LOW — adds density but not engagement-critical | HIGH — per-scene timing, Remotion components | P3 |

**Priority key:**
- P1: Must have for this milestone — directly addresses "flat clip" problem
- P2: Should have — add after P1 validated
- P3: Nice to have — future consideration

---

## Competitor Feature Analysis

Tools generating similar AI Shorts (CapCut, OpusClip, Pictory, Invideo AI):

| Feature | CapCut / Pictory | OpusClip | Our Approach |
|---------|-----------------|----------|--------------|
| Ken Burns on images | Default on; no-motion is the "off" state | Not applicable (clip-based) | Implement in Remotion; default on; direction varies per scene |
| Scene transitions | Zoom/push default; user can swap | Automated based on clip energy | Remotion `TransitionSeries`; zoom/push; no user selection needed (automated) |
| Hook injection | Manual or template-based | AI-detected from existing clips | LLM-generated, topic-matched, injected into script before TTS |
| TTS voice energy | 10+ voice styles including "energetic"; most are paid | N/A (uses original audio) | edge-tts prosody tuning; constrained by Microsoft's single `<prosody>` tag limit |
| Subtitle style | Animated word-highlight (viral style) | Word-level karaoke | Plain subtitles (existing); word highlight deferred |

---

## Implementation Notes by Feature

### Ken Burns (Remotion)

- Remotion's `interpolate()` function maps frame number to scale/translate values
- A free Remotion Ken Burns template exists at reactvideoeditor.com — check source before building from scratch
- Safe zoom range: 1.0→1.12 (zoom-in) or 1.12→1.0 (zoom-out); beyond 1.2 starts to feel aggressive for educational content
- Pan offsets: ±5-8% of image width/height for subtle drift; ±15% for emphasis
- Duration: derive from `audioDuration / sceneCount` passed in props JSON from Python

### Scene Transitions (Remotion)

- `@remotion/transitions` package required: `npm install @remotion/transitions`
- `TransitionSeries` replaces `Series` for scenes with transitions
- Transition duration: 15-20 frames at 30fps = 0.5-0.67 seconds; longer feels sluggish for Shorts
- Available presentations include `slide()` (push), `fade()` (avoid), `wipe()`, custom scale (zoom)
- Avoid `fade()` — low energy; use `slide()` with `from-left`/`from-right` alternating, or custom zoom

### Hook Generation (Python/Ollama)

- Three archetypes to implement: question ("Are you making this mistake?"), stat ("90% of people don't know..."), payoff-preview ("Here's what you'll learn in 30 seconds:")
- LLM prompt should include topic + content body so the hook is contextually accurate, not generic
- Inject hook as the first sentence; do not replace the script — prepend
- Fallback: if LLM returns a hook longer than 15 words, truncate or re-prompt

### TTS Prosody (edge-tts)

- edge-tts does NOT support arbitrary SSML; Microsoft's backend permits only a single `<voice>` + single `<prosody>` tag
- Effective parameters: `--rate="+20%"` (faster, energetic), `--pitch="+8Hz"` (slightly higher, more alert)
- These are passed as CLI arguments, not SSML — the kittentts wrapper needs to expose `rate` and `pitch` parameters
- Avoid exceeding `+30%` rate — comprehension drops; avoid `+20Hz` pitch — sounds unnatural
- v1 target: `rate=+20%`, `pitch=+8Hz` applied globally; test against baseline before shipping

---

## Sources

- [YouTube Shorts Retention Rate 2026 — Shortimize](https://www.shortimize.com/shortimize.com/blog/youtube-shorts-retention-rate) — MEDIUM confidence (third-party analytics blog, not YouTube official)
- [YouTube Shorts Hook Formulas — OpusClip](https://www.opus.pro/blog/youtube-shorts-hook-formulas) — MEDIUM confidence
- [YouTube Algorithm for Faceless Channels 2026 — Virvid](https://virvid.ai/blog/faceless-youtube-algorithm-retention-2026) — MEDIUM confidence
- [Ken Burns Effect Complete Guide — Cloudinary](https://cloudinary.com/guides/image-effects/ken-burns-effect-complete-guide-and-how-to-apply-it) — HIGH confidence (established vendor)
- [Ken Burns Remotion Template — ReactVideoEditor](https://www.reactvideoeditor.com/remotion-templates/ken-burns) — MEDIUM confidence (template exists; props API not publicly documented)
- [Remotion Transitions — Official Docs](https://www.remotion.dev/docs/transitions/) — HIGH confidence (official Remotion documentation)
- [edge-tts GitHub — rany2](https://github.com/rany2/edge-tts) — HIGH confidence (official repo; custom SSML limitation confirmed)
- [YouTube Shorts Best Practices 2026 — Miraflow](https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide) — MEDIUM confidence
- [18 Viral Hook Ideas for YouTube Shorts — VidIQ](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/) — MEDIUM confidence

---

*Feature research for: YouTube Shorts engagement upgrade — Ken Burns, transitions, hooks, TTS prosody*
*Researched: 2026-03-30*
