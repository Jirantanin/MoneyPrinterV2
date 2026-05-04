---
plan: "06-02"
phase: 6
status: complete
completed: "2026-04-02"
tasks_completed: 1
files_modified:
  - src/classes/Tts.py
key-files:
  modified:
    - src/classes/Tts.py
---

# Plan 06-02 Summary: Extend Tts.synthesize() with optional voice/rate overrides

## What Was Built

Modified `src/classes/Tts.py` to add optional `voice` and `rate` keyword arguments to `TTS.synthesize()`. The change is fully backward-compatible — existing callers (Shorts pipeline via `YouTube.py`) pass no arguments and continue using `self._voice` and `get_tts_rate()` exactly as before. The Podcast pipeline can now pass `voice=narrator["tts_voice"]` and `rate=narrator["tts_rate"]` to honour per-narrator TTS settings.

## Changes Made

**T1 — Tts.synthesize() signature + body (3 targeted edits):**

1. New signature: `synthesize(self, text, output_file=..., voice=None, rate=None)`
2. New locals: `_voice = voice if voice is not None else self._voice` / `_rate = rate if rate is not None else get_tts_rate()`
3. Updated call: `asyncio.run(_edge_tts_synthesize(text, mp3_path, _voice, _rate))`

## Self-Check

- [x] `voice=None, rate=None` in signature
- [x] `_voice = voice if voice is not None else self._voice` present
- [x] `_rate = rate if rate is not None else get_tts_rate()` present
- [x] `asyncio.run(_edge_tts_synthesize(text, mp3_path, _voice, _rate))` present
- [x] Old `asyncio.run(..., self._voice, rate)` removed
- [x] No other changes to Tts.py

## Requirements Addressed

- TTS-01 (capability): synthesize() can now accept `voice` override per call
- TTS-02 (capability): synthesize() can now accept `rate` override per call
