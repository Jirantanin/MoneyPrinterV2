# MoneyPrinterV2 — Video Engagement Upgrade

## What This Is

MoneyPrinterV2 is a Python CLI tool that auto-generates and uploads YouTube Shorts — from topic discovery through LLM scripting, image generation, TTS narration, subtitle rendering, and YouTube API upload. v1.0 shipped all planned engagement upgrades: energetic TTS delivery, LLM-selected opening hooks, Ken Burns motion on every image, and push/slide scene transitions.

## Core Value

Every generated clip must stop the scroll within the first 3 seconds — hook + motion + voice must work together to retain viewers.

## Requirements

### Validated

<!-- v1.0 shipped — all active requirements validated -->

- ✓ End-to-end YouTube Shorts pipeline (topic → script → images → TTS → subtitles → Remotion → upload) — existing
- ✓ LLM script generation via Ollama — existing
- ✓ Image generation via Gemini (Nano Banana 2) — existing
- ✓ TTS narration via edge-tts (kittentts) — existing
- ✓ Whisper subtitle generation — existing
- ✓ Remotion video renderer (1080×1920) — existing
- ✓ YouTube API v3 upload — existing
- ✓ **TTS prosody improvements** — configurable speaking rate (+20% default) via `tts_rate` config key — v1.0
- ✓ **Hook generation** — LLM-selected opening hook (question/stat/bold) prepended before TTS, spoken and subtitled from frame 0, with template fallback — v1.0
- ✓ **Ken Burns effect** — 4-direction cycle (zoom-in, zoom-out, pan-left, pan-right) on every image in Remotion — v1.0
- ✓ **Zoom/push scene transitions** — slide-push transitions via @remotion/transitions, 18 frames, duration-compensated — v1.0

### Active

<!-- Next milestone requirements go here -->

### Out of Scope

- Switching TTS provider to ElevenLabs — stay with edge-tts, only tune prosody
- Dynamic/animated subtitles (word highlight, bounce) — deferred, motion + hook shipped first
- Thai-language clips — current milestone targeted English clips only
- Twitter / AFM / Outreach improvements — unrelated pipelines, not touched
- New niche selection UI — topic discovery handled separately
- Per-hook archetype config key — LLM selects best archetype freely, defer operator control to v2

## Context

- **Shipped v1.0**: 3 phases, 3 plans, 7 tasks, ~6,500 LOC changes across 32 files
- **Tech stack**: Python 3.12, edge-tts, Ollama (local LLM), Remotion 4.0.441, @remotion/transitions 4.0.441, Pydantic 2.12.5
- **Key discovery**: edge-tts `pitch=` kwarg is silently ignored by Microsoft since v6.0.3 — only `rate=` works
- **Key discovery**: `@remotion/transitions` must be installed separately (not bundled with remotion core)
- **Key discovery**: `TransitionSeries` shortens total duration by `(N-1) * transitionFrames` — requires compensation formula
- **Known tech debt**: Worktree executor ran `npm install` in worktree but not in main repo — package.json was updated but node_modules weren't installed until manually run

## Constraints

- **Tech stack**: Remotion for all visual effects — no FFmpeg-based transitions, no MoviePy (fallback only)
- **TTS provider**: Stay on edge-tts (kittentts) — no new paid API keys required
- **LLM**: Ollama local — hook generation uses same provider, no external API
- **Asset pipeline**: All images staged to `remotion/public/assets/` before render; props JSON passed via file to `scripts/render.mjs`
- **Platform**: Windows 10 with bash shell; Node subprocess needs `shell=True` for npx

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ken Burns in Remotion (not Python/Pillow) | Remotion controls timing per frame; Python can't sync motion with audio | ✓ Shipped v1.0 |
| Hook selected by LLM (not hardcoded templates) | LLM can match tone/style to topic better than rules | ✓ Shipped v1.0 |
| edge-tts prosody via rate= kwarg only | pitch= silently ignored by Microsoft since v6.0.3; rate= confirmed working | ✓ Shipped v1.0 |
| Zoom/push transition via slide() presentation | slide() is a push wipe; Ken Burns inside each scene provides zoom energy | ✓ Shipped v1.0 |
| generate_text_structured() in llm_provider.py | Keeps _client() private; YouTube.py calls public wrapper | ✓ Shipped v1.0 |
| 1 retry before template fallback for hooks | max_attempts=2; no exponential back-off needed for short hook generation | ✓ Shipped v1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after v1.0 milestone*
