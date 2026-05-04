---
phase: 05-script-generation
plan: 01
subsystem: podcast-script-generation
tags: [llm, script-generation, json-persistence, ollama, podcast]
dependency_graph:
  requires:
    - src/llm_provider.py (generate_text, generate_text_structured)
    - src/config.py (get_podcast_narrator, get_podcast_style_prompt, ROOT_DIR)
    - src/classes/Tts.py (import retained, used in future phases)
  provides:
    - src/classes/Podcast.py (generate_script implementation)
    - .mp/podcast_{slug}_{YYYYMMDD}/script.json (14-scene JSON array at runtime)
  affects:
    - src/main.py (Podcast dispatch now prompts for topic)
tech_stack:
  added: []
  patterns:
    - 3-call LLM loop with running summary injection between acts
    - SCENE_SCHEMA module-level constant for generate_text_structured structured output
    - Retry-once pattern for malformed JSON or wrong scene count
    - Episode ID from topic slug + YYYYMMDD date
key_files:
  created: []
  modified:
    - src/classes/Podcast.py
    - src/main.py
decisions:
  - Plain list of dicts (no Pydantic) for 14-scene output, consistent with D-01
  - 3-call LLM loop: call1=intro+act1(5 scenes), call2=act2(4 scenes), call3=act3+outro(5 scenes)
  - LLM-generated running summaries between calls via generate_text() (simpler than rule-based)
  - Retry-once strategy on JSON parse failure or wrong scene count with emphatic count instruction
  - Narrator persona injected as system_prompt with /no_think to disable Qwen3 thinking mode
metrics:
  duration: 8 minutes
  completed_date: "2026-04-01T08:32:58Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 5 Plan 1: Script Generation Summary

**One-liner:** 3-call Ollama loop with running summary injection generates 14-scene podcast script persisted to `.mp/podcast_{slug}_{YYYYMMDD}/script.json`.

## What Was Built

### Task 1: Podcast.py generate_script() implementation (commit: 21c6ba7)

Rewrote `src/classes/Podcast.py` from stub to full implementation:

- **SCENE_SCHEMA** module-level constant defines the JSON schema passed to `generate_text_structured()` for structured output enforcement.
- **`__init__(self, topic: str = "")`** stores topic; fetches narrator and style_prompt from config.
- **`generate_script(self, topic: str) -> list`** makes exactly 3 `generate_text_structured()` calls:
  - Call 1: intro(1) + act1(4) = 5 scenes — establishes topic context
  - Call 2: act2(4) = 4 scenes — injected with LLM-generated summary of Call 1
  - Call 3: act3(4) + outro(1) = 5 scenes — injected with LLM-generated summary of Calls 1+2
- Running summaries generated via `generate_text()` — 3-5 sentence recap of narrations so far.
- Narrator persona from `get_podcast_narrator()` injected as system prompt with `/no_think` directive on all 3 calls.
- Style prompt from `get_podcast_style_prompt()` prepended to every `image_prompt` before writing.
- Each LLM call retries once on JSON parse failure or wrong scene count with emphatic count instruction.
- Writes 14-scene flat JSON array to `.mp/podcast_{slug}_{YYYYMMDD}/script.json`.
- Phase stubs (`generate_assets`, `render`, `upload`) preserved with "Phase 6/7/8: not yet implemented" messages.

### Task 2: main.py topic prompting (commit: 85d42a8)

Updated Podcast dispatch block in `src/main.py`:

- Prompts user for topic with `input("Enter the podcast topic: ")`.
- Validates non-empty; calls `error()` and returns to menu if empty.
- Passes topic to `Podcast(topic)` constructor.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following phase stubs are intentionally preserved in `src/classes/Podcast.py`:

| Method | File | Reason |
|--------|------|--------|
| `generate_assets()` | src/classes/Podcast.py | Phase 6 — not yet implemented |
| `render()` | src/classes/Podcast.py | Phase 7 — not yet implemented |
| `upload()` | src/classes/Podcast.py | Phase 8 — not yet implemented |

These stubs are tracked intentionally. `podcast.run()` will raise `NotImplementedError` after `generate_script()` completes; the calling site in `main.py` catches and reports this gracefully.

## Self-Check: PASSED

- src/classes/Podcast.py: exists and contains full generate_script() implementation
- src/main.py: contains topic prompt and Podcast(topic) call
- commit 21c6ba7: feat(05-01): implement generate_script()
- commit 85d42a8: feat(05-01): wire topic prompting into main.py
