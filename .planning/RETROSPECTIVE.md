# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Video Engagement Upgrade

**Shipped:** 2026-03-31
**Phases:** 3 | **Plans:** 3 | **Tasks:** 7
**Commits:** ~29 over 1-2 days

### What Was Built

- **Phase 1 — TTS Prosody:** Configurable speaking rate (+20% default) via `get_tts_rate()` getter and `tts_rate` config key; edge-tts `Communicate` wired with `rate=` kwarg
- **Phase 2 — Hook Generation:** `generate_text_structured()` in `llm_provider.py` (Ollama structured output, Pydantic `HookOutput` schema); `generate_hook()` + `_hook_template_fallback()` in `YouTube.py`, prepended to script before TTS and Whisper
- **Phase 3 — Visual Motion:** `KenBurnsFrame` sub-component with 4-direction cycle; `TransitionSeries` + `slide()` + duration compensation formula in `remotion/src/VideoShort.tsx`; `@remotion/transitions@4.0.441` installed

### What Worked

- Research-first approach surfaced critical pitfalls (TransitionSeries duration mismatch, pip version pinning) before any code was written
- Plan checker caught a verify command path bug (sys.path for llm_provider import) before execution
- Worktree isolation kept main repo clean during parallel execution
- Pydantic structured output for LLM made hook validation clean and type-safe

### What Was Inefficient

- Worktree executor ran `npm install` inside the worktree but changes didn't propagate to main repo — `@remotion/transitions` was in package.json but not installed, causing a blank white Remotion Studio until manually running `npm install`
- The `npm install` gap wasn't caught until visual verification — a post-execution `npm install` step in the plan would have prevented this

### Patterns Established

- `generate_text_structured(prompt, schema)` wrapper pattern for Ollama structured output — reusable for future LLM features needing typed output
- Duration compensation formula for `TransitionSeries`: `Math.round((totalFrames + (n-1)*tf) / n)` — document in codebase for future Remotion work
- `KenBurnsFrame` as a sub-component inside `TransitionSeries.Sequence` ensures `useCurrentFrame()` is sequence-scoped — required pattern for Remotion animations inside transitions

### Key Lessons

1. **Worktree npm installs don't propagate to main repo** — plans involving `npm install` should include a post-merge verification step or run install in the main repo directly
2. **`@remotion/transitions` is a separate package** — not bundled with `remotion` core; must be installed explicitly and pinned to the same version
3. **Remotion Studio preview with empty `imagePaths: []` shows black** — expected behavior; need real props to verify visual output
4. **edge-tts `pitch=` is silently ignored** — only `rate=` works; document this so future TTS work doesn't waste time on pitch tuning

### Cost Observations

- Model mix: opus for planning, sonnet for research/execution/verification
- Sessions: ~1 session end-to-end
- Notable: Research phase added ~5min per phase but saved multiple rework cycles; the TransitionSeries duration formula alone justified the research cost

## Milestone: v2.0 — Video Podcast Module

**Shipped:** 2026-04-05
**Phases:** 5 | **Plans:** 9 | **Tasks:** ~18
**Commits:** ~50 over 5 days (2026-04-01 → 2026-04-05)

### What Was Built

- **Phase 4 — Module Scaffold:** `Podcast.py` standalone class with four-step pipeline interface, Podcast wired into main menu, `podcast_narrator` + `podcast_style_prompt` config keys
- **Phase 5 — Script Generation:** Act-by-act 14-scene LLM generation with running summaries, narrator persona injection, `script.json` persistence
- **Phase 6 — Scene Assets:** `image_provider.py` standalone Gemini module (rate limit + retry); `Tts.synthesize(voice, rate)` override; `Podcast.generate_assets()` with resumability
- **Phase 7 — FFmpeg Render:** Two-pass pipeline — libx264 per-scene clips with zoompan Ken Burns, concat demuxer to `final.mp4`
- **Phase 8 — Thumbnail + Upload:** LLM metadata, Gemini dark-comic thumbnail, YouTube API v3 resumable upload + thumbnails().set()
- **Quick Tasks:** FastAPI web Studio (podcast_server.py port 8899), Tailwind dark UI (podcast_ui.html), unified Podcast+Shorts tab navigation

### What Worked

- Standalone module pattern (`image_provider.py`) — rate limit shared across Podcast + YouTube without coupling classes
- Act-by-act script generation with injected summaries — solved Ollama context overflow cleanly
- FastAPI + SSE streaming pattern — identical to podcast_server adapted smoothly for Shorts; unified under one server proved straightforward
- Worktree isolation worked well for quick tasks with file-based conflict resolution

### What Was Inefficient

- REQUIREMENTS.md REND-01/02/03 left unchecked despite Phase 7 completing them — documentation drift from implementation
- ROADMAP.md Phase 5 and 7 left as `[ ]` even after completion — plan tracking diverged from disk state
- Merge conflicts on quick task worktrees required manual resolution (constants.py, main.py menu numbering)
- `shorts_server.py` was created then immediately merged into `podcast_server.py` — the split was unnecessary; a unified server should have been the first design

### Patterns Established

- Module-level float for cross-call rate limiting in `image_provider.py` — reusable pattern for any shared API with rate limits
- FastAPI SSE `text/event-stream` generator pattern for pipeline streaming — established in podcast_server, extended to Shorts
- Unified Studio on single port with tab navigation — better UX than separate servers per workflow
- Quick task workflow (gsd:quick) for ad-hoc features without full phase ceremony

### Key Lessons

1. **Design the unified server first** — when multiple workflows share a UI, start with one server + tabs; don't build separate servers then merge
2. **Check requirements as phases complete** — REND requirements drifted unchecked; updating REQUIREMENTS.md immediately after each phase prevents milestone completion friction
3. **FFmpeg on Windows requires forward-slash paths in concat_list.txt** — backslashes fail silently; document this for future FFmpeg work
4. **MiniMax/OpenRouter as primary LLM dramatically improves script quality** — worth the API key; Ollama fallback ensures offline capability
5. **Worktree quick tasks create merge conflicts on shared menu files** — when adding menu options, coordinate with existing options upfront (constants.py OPTIONS list)

### Cost Observations

- Model mix: opus for planning, sonnet for execution/research
- Sessions: ~3 sessions over 5 days
- Notable: Quick tasks (gsd:quick) were efficient for web GUI work — no full phase ceremony needed for FastAPI routes + HTML

## Cross-Milestone Trends

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Phases | 3 | 5 |
| Plans | 3 | 9 |
| Avg tasks/plan | 2.3 | ~2.0 |
| Rework cycles | 1 (hook verify path fix) | 2 (server unify, menu conflicts) |
| Human checkpoints | 1 (visual motion) | 2 (merge resolution, doc drift) |
| Quick tasks | 0 | 3 |
