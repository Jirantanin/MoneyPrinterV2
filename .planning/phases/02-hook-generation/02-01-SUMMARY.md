---
phase: 02-hook-generation
plan: 01
subsystem: youtube-pipeline
tags: [hook-generation, llm, pydantic, structured-output, tts, subtitles]
dependency_graph:
  requires: [01-01]
  provides: [HOOK-01, HOOK-02, HOOK-03]
  affects: [src/llm_provider.py, src/classes/YouTube.py]
tech_stack:
  added: []
  patterns:
    - Ollama structured output via format= parameter (Pydantic JSON schema)
    - Template fallback pattern for LLM robustness
    - Category-matched template dispatch
key_files:
  modified:
    - src/llm_provider.py
    - src/classes/YouTube.py
decisions:
  - Hook receives both self.subject (topic) AND self.script (body) as context — prevents semantic disconnect between hook and body
  - max_attempts=2 with retry before fallback — balances quality vs latency (one retry is cheap; template fallback is instant)
  - Markdown stripping via re.sub(r"[*#\"]") — Ollama models sometimes inject asterisks despite instructions
  - Punctuation guard added inline in generate_video() — not in generate_hook() to keep method pure
metrics:
  duration: "~15 minutes"
  completed: "2026-03-31"
  tasks: 2
  files_modified: 2
---

# Phase 02 Plan 01: Hook Generation Summary

**One-liner:** LLM-powered opening hook via Ollama structured output (Pydantic schema), with category-matched template fallback, prepended to script before TTS and subtitle generation.

## What Was Built

### Task 1 — generate_text_structured() in llm_provider.py (commit 791fac9)

Added `generate_text_structured()` function to `src/llm_provider.py` immediately after `generate_text()`. The function wraps `_client().chat()` with the `format=` parameter for Ollama structured JSON output. It accepts `prompt`, `system_prompt`, `schema` (a JSON schema dict from Pydantic's `model_json_schema()`), and optional `model_name`. Returns the raw JSON string for callers to deserialise with their own Pydantic models. Keeps `_client()` private to the module.

### Task 2 — Hook generation wired into YouTube pipeline (commit 8c195c9)

Three changes to `src/classes/YouTube.py`:

1. **Imports updated:** `from llm_provider import generate_text, generate_text_structured` and `from pydantic import BaseModel` added.

2. **Module-level definitions added before `class YouTube:`**
   - `HookOutput(BaseModel)` — Pydantic model with `hook_type: str` and `hook_text: str` fields; used to constrain Ollama's JSON output shape.
   - `_HOOK_TEMPLATES: dict` — four category-matched fallback hook sentences for `breaking_news`, `science_facts`, `weird_viral`, `default`.

3. **Two new methods on YouTube class** (inserted before `_detect_category()`):
   - `generate_hook()` — calls `generate_text_structured()` with topic+script context, validates output (non-empty, word count <= 15), strips markdown artifacts. Retries up to 2 attempts before falling back.
   - `_hook_template_fallback()` — delegates to `_detect_category()` and returns the matched template from `_HOOK_TEMPLATES`.

4. **`generate_video()` wired:** After `self.generate_script()` and before `self.generate_metadata()`, calls `self.generate_hook()`, applies punctuation guard, then sets `self.script = hook + " " + self.script`.

## Requirements Satisfied

- **HOOK-01:** `generate_hook()` uses both `self.subject` and `self.script` as prompt context to generate a contextual opening hook via Ollama structured output.
- **HOOK-02:** Hook is prepended to `self.script` in `generate_video()` before `generate_script_to_speech()` and `generate_subtitles()` — so it appears in both TTS audio and the SRT subtitle track from frame 0.
- **HOOK-03:** `_hook_template_fallback()` is called on any exception, empty hook text, or hook over 15 words — pipeline never crashes on hook failure.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Hook prompt includes full script body (not just topic) | Research finding: hook-body semantic disconnect is the main quality failure mode; LLM needs script context to write a relevant tease |
| max_attempts=2 before template fallback | One retry is cheap at local inference speeds; template fallback ensures the pipeline always completes |
| Markdown stripping with re.sub in generate_hook() | Ollama 3B-7B models frequently inject `*` or `#` despite explicit instructions; strip at the source |
| Punctuation guard in generate_video(), not generate_hook() | Keeps generate_hook() a pure string-returning method; punctuation normalization is a pipeline concern |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. The hook generation is fully wired. Template fallback is intentional and complete, not a stub.

## Self-Check: PASSED

Files verified:
- `src/llm_provider.py` — contains `def generate_text_structured`
- `src/classes/YouTube.py` — contains `HookOutput`, `_HOOK_TEMPLATES`, `generate_hook`, `_hook_template_fallback`, hook wired in `generate_video`

Commits verified:
- 791fac9 — feat(02-01): add generate_text_structured() to llm_provider.py
- 8c195c9 — feat(02-01): add hook generation to YouTube pipeline (HOOK-01/02/03)
