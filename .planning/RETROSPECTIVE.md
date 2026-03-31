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

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 3 |
| Plans | 3 |
| Avg tasks/plan | 2.3 |
| Rework cycles | 1 (hook verify path fix) |
| Human checkpoints | 1 (visual motion) |
