# Phase 4: Module Scaffold - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire up `src/classes/Podcast.py`, the main menu entry in `src/main.py`, and the `config.json` schema for `podcast_narrator` + `podcast_style_prompt`. No pipeline logic — pure scaffolding that downstream phases (5–8) build on.

</domain>

<decisions>
## Implementation Decisions

### Podcast.py Class Interface

- **D-01:** Expose **granular step methods** — `generate_script()`, `generate_assets()`, `render()`, `upload()` — matching the four downstream phases exactly. Each phase fills in one method.
- **D-02:** Also expose a **`run()` entry point** that calls the step methods in order (`generate_script → generate_assets → render → upload`). `main.py` calls `podcast.run()` — single call site, steps remain individually testable.
- **D-03:** Stub methods raise `NotImplementedError('Phase N: not yet implemented')` in Phase 4. Makes gaps explicit, prevents silent no-ops, easy to grep for remaining stubs.

### Claude's Discretion

- Menu placement (before Quit, after Outreach) — standard pattern, Claude decides position
- Config getter pattern (individual getters vs object getter) — follow existing `config.py` conventions
- `config.example.json` defaults for `podcast_narrator` — use values from REQUIREMENTS.md (`en-GB-RyanNeural`, `-20%`); name/persona can be placeholder strings

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

### Project requirements
- `.planning/REQUIREMENTS.md` — MOD-01, MOD-02, MOD-03 define the scaffold acceptance criteria
- `.planning/ROADMAP.md` — Phase 4 success criteria (section "Phase 4: Module Scaffold")

### Existing integration points
- `src/main.py` — main menu dispatch (add Podcast option here)
- `src/constants.py` — `OPTIONS` list (add "Podcast" entry here)
- `src/config.py` — config getter functions (add podcast getters here)
- `config.example.json` — config template (add `podcast_narrator` object + `podcast_style_prompt` key here)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/classes/YouTube.py` — reference for class structure/import patterns; do NOT modify
- `src/classes/Tts.py` — edge-tts wrapper reusable by Podcast.py for TTS in Phase 6
- `src/llm_provider.py` — `generate_text()` reusable for script generation in Phase 5
- `config.py` getters: `get_tts_voice()`, `get_tts_rate()` — pattern to follow for new podcast getters

### Established Patterns
- Classes are standalone files in `src/classes/`, imported and instantiated in `main.py`
- Config access: individual getter functions per key, each re-reads `config.json` on every call
- Menu dispatch: `user_input == N` integer check in `main.py`, option label in `constants.OPTIONS`

### Integration Points
- `constants.py` → add `"Podcast"` to `OPTIONS` list (before `"Quit"`)
- `main.py` → add `elif user_input == N:` block that instantiates `Podcast` and calls `.run()`
- `config.py` → add getters for `podcast_narrator.*` fields and `podcast_style_prompt`
- `config.example.json` → add `podcast_narrator` object and `podcast_style_prompt` key with defaults

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-module-scaffold*
*Context gathered: 2026-04-01*
