# Roadmap: MoneyPrinterV2 — Video Engagement Upgrade

## Overview

Three phases transform flat, static YouTube Shorts into scroll-stopping clips. TTS prosody lands first because audio duration is the authoritative input for all frame timing downstream. Hook generation follows, prepending the hook to the script before any audio is synthesized. Ken Burns motion and zoom-push transitions ship together last — they share the same Remotion component (ImageSlideshow) and the transitions wrapper depends on Ken Burns being stable inside it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: TTS Prosody** - Increase speaking rate and expose config value so narration sounds energetic (completed 2026-03-30)
- [ ] **Phase 2: Hook Generation** - Generate and inject a contextual opening hook sentence via LLM
- [ ] **Phase 3: Visual Motion** - Add Ken Burns pan drift and zoom-push scene transitions in Remotion

## Phase Details

### Phase 1: TTS Prosody
**Goal**: Narration is generated at an energetic speaking rate with the value tuneable from config
**Depends on**: Nothing (first phase)
**Requirements**: TTS-01, TTS-02
**Success Criteria** (what must be TRUE):
  1. A generated WAV file plays noticeably faster than the baseline (approximately +20% rate audible on first listen)
  2. The speaking rate value can be changed in `config.json` and the next generated video reflects the new value without any code changes
  3. The pipeline does not crash or produce a silent WAV when the rate config key is missing or set to the default value
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Add get_tts_rate() config getter and wire rate= into edge_tts.Communicate

### Phase 2: Hook Generation
**Goal**: Every generated script opens with an LLM-selected hook sentence that matches the topic and is spoken and subtitled from frame 0
**Depends on**: Phase 1
**Requirements**: HOOK-01, HOOK-02, HOOK-03
**Success Criteria** (what must be TRUE):
  1. A generated video begins with a spoken hook sentence (question, stat, or payoff-preview) audibly distinct from the body narration
  2. The hook sentence appears in the subtitle track from the first subtitle block, confirming it was prepended before TTS and Whisper ran
  3. When the LLM returns an unusable hook (empty, over 15 words, or malformed), the pipeline completes without crashing and falls back to a template hook
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Add generate_hook() with Ollama structured output, template fallback, and wire into generate_video()

### Phase 3: Visual Motion
**Goal**: Every image in a generated clip drifts with Ken Burns motion and scenes are separated by zoom-push transitions instead of hard cuts
**Depends on**: Phase 2
**Requirements**: VIS-01, VIS-02, VIS-03
**Success Criteria** (what must be TRUE):
  1. Each image visibly zooms and/or pans during its on-screen duration — no image is stationary for its entire screen time
  2. Consecutive images drift in different directions (zoom-in, zoom-out, pan left, pan right cycling) so the clip does not look like a looping template
  3. A visible push/zoom transition plays between each pair of scenes; no hard cuts or black frames appear at scene boundaries
  4. The rendered video's total duration matches the TTS audio length — no silent tail and no audio cutoff caused by TransitionSeries frame overlap
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. TTS Prosody | 1/1 | Complete   | 2026-03-30 |
| 2. Hook Generation | 0/1 | Not started | - |
| 3. Visual Motion | 0/TBD | Not started | - |
