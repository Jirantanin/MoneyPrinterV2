# Requirements: MoneyPrinterV2 — Video Engagement Upgrade

**Defined:** 2026-03-30
**Core Value:** Every generated clip must stop the scroll within the first 3 seconds — hook + motion + voice must work together to retain viewers.

## v1 Requirements

### Hook

- [ ] **HOOK-01**: Pipeline generates a contextual opening hook sentence (question, stat, or payoff-preview archetype) via LLM, matched to topic and script content
- [ ] **HOOK-02**: Hook sentence is prepended to the script before TTS rendering so it is both spoken and appears in subtitles
- [ ] **HOOK-03**: If LLM hook generation fails or returns output longer than 15 words, pipeline falls back gracefully without crashing

### Visual Motion

- [ ] **VIS-01**: Every image in a generated clip has Ken Burns motion (zoom and/or pan drift) synced to its on-screen duration
- [ ] **VIS-02**: Ken Burns direction varies per scene (zoom-in, zoom-out, pan directions) so clips don't look templated
- [ ] **VIS-03**: Scene transitions use zoom/push (not hard cuts or fade) with 15-20 frame duration at 30fps

### TTS Prosody

- [x] **TTS-01**: TTS narration is generated at a globally increased speaking rate (+20%) to sound energetic, applied to the full script
- [x] **TTS-02**: TTS rate value is preserved as a config option in `config.json` so it can be adjusted without code changes

## v2 Requirements

### Visual Motion (Enhanced)

- **VIS-04**: Ken Burns motion direction is passed per-scene from Python to Remotion via props JSON (explicit direction control)
- **VIS-05**: First and last frame of clip match visually to support YouTube Shorts looping (loop-count as new view, March 2025 change)

### TTS Prosody (Enhanced)

- **TTS-03**: Hook sentence is rendered at higher rate and pitch than script body (multi-segment TTS calls concatenated)
- **TTS-04**: CTA sentence is rendered at slightly slower, more emphatic rate

### Hook (Enhanced)

- **HOOK-04**: LLM is prompted to write a callback ending that references the opening hook (narrative loop structure)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fade transitions | Low energy; hurts Shorts retention; explicitly avoided per research |
| Word-level subtitle highlight (karaoke) | High complexity in Remotion; requires Whisper word timestamps; deferred to subtitle milestone |
| TTS provider swap to ElevenLabs | Paid API; edge-tts prosody tuning achieves 80% of benefit at zero cost |
| TTS pitch adjustment | edge-tts pitch silently ignored by Microsoft backend since v6.0.3 — not a viable lever |
| Transition sound effects (whoosh/swipe) | 3-track audio mixing complexity; marginal gain vs implementation cost |
| Dynamic text callouts / lower thirds | Per-scene timing sync cost; not engagement-critical for v1 |
| Twitter / AFM / Outreach improvements | Different pipelines; not in scope for this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TTS-01 | Phase 1 | Complete |
| TTS-02 | Phase 1 | Complete |
| HOOK-01 | Phase 2 | Pending |
| HOOK-02 | Phase 2 | Pending |
| HOOK-03 | Phase 2 | Pending |
| VIS-01 | Phase 3 | Pending |
| VIS-02 | Phase 3 | Pending |
| VIS-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — traceability filled after roadmap creation*
