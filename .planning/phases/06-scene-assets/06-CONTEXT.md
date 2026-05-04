# Phase 6: Scene Assets - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `Podcast.generate_assets()` — reads `script.json` from the episode directory, generates one Gemini image and one edge-tts audio file per scene (14 scenes total), and saves both to `.mp/podcast_{id}/`. Resumable: scenes that already have both files are skipped. No render, no upload — pure asset generation.

</domain>

<decisions>
## Implementation Decisions

### Image Generation Code Location

- **D-01:** Extract Gemini image gen code into a new **`src/image_provider.py`** module with a standalone `generate_image(prompt, output_path)` function. This module contains: API call logic, 429 retry with 15s sleep, 7s rate limiting between calls, and `_persist_image()` helper.
- **D-02:** **Refactor `YouTube.py`** to import `generate_image` from `image_provider.py` — removes duplication and makes `image_provider.py` the single source of truth for all Gemini image gen across Shorts, Podcast, and Thumbnail (Phase 8).
- **D-03:** `Podcast.generate_assets()` calls `image_provider.generate_image(prompt, output_path)` directly — no YouTube.py dependency.

### TTS Voice and Rate Override

- **D-04:** Add **optional `voice` and `rate` parameters** to `Tts.synthesize()`:
  ```python
  def synthesize(self, text, output_file=..., voice=None, rate=None):
      _voice = voice if voice is not None else self._voice
      _rate = rate if rate is not None else get_tts_rate()
  ```
  Podcast.py passes `podcast_narrator['tts_voice']` and `podcast_narrator['tts_rate']` explicitly. Shorts pipeline passes nothing (falls back to Shorts config values). No behaviour change for existing code.

### Claude's Discretion

- Scene file naming convention (e.g., `scene_00.png` / `scene_00.wav`) — Claude decides
- Resumability check logic (both image + audio present = skip) — Claude decides
- Order of operations within `generate_assets()` (per-scene: image then TTS, or batch images then batch TTS) — Claude decides based on rate limit considerations
- Audio format: WAV (already what Tts.py produces after mp3→wav conversion) — retain for consistency with existing pipeline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — IMG-01, IMG-02, IMG-03, TTS-01, TTS-02, TTS-03 define acceptance criteria
- `.planning/ROADMAP.md` — Phase 6 success criteria (section "Phase 6: Scene Assets")

### Existing integration points
- `src/classes/YouTube.py` — contains `generate_image_nanobanana2()`, `_persist_image()`, and the 7s rate limit pattern to extract into `image_provider.py`; also refactored in this phase to import from `image_provider.py`
- `src/classes/Tts.py` — `TTS.synthesize()` modified to accept optional `voice` and `rate` params
- `src/classes/Podcast.py` — `generate_assets()` stub to implement (raises `NotImplementedError` currently)
- `src/config.py` — `get_podcast_narrator()` returns `{name, persona, tts_voice, tts_rate}`; `get_nanobanana2_api_key()`, `get_nanobanana2_api_base_url()`, `get_nanobanana2_model()`, `get_nanobanana2_aspect_ratio()` used by image gen

### Script output (Phase 5 produces, Phase 6 consumes)
- `.mp/podcast_{slug}_{YYYYMMDD}/script.json` — flat 14-element JSON array of `{narration, image_prompt}` dicts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `YouTube.generate_image_nanobanana2()` (lines 348–420 approx) — full Gemini API call logic to extract into `image_provider.py`
- `YouTube._persist_image()` (lines 326–346 approx) — writes image bytes to disk; also moves to `image_provider.py`
- `YouTube._last_image_time` + 7s enforcement in `generate_image()` — move to `image_provider.py` as module-level state
- `Tts.synthesize()` — MP3→WAV conversion via ffmpeg; reused with voice/rate override
- `get_podcast_narrator()` — returns dict with `tts_voice` and `tts_rate` keys

### Established Patterns
- Config access: re-read config on every call (no caching) — follow for `get_podcast_narrator()`
- Image gen enforces 7s minimum gap between Gemini requests (429 rate limit protection)
- Gemini 429 retry: 15s sleep, one retry, skip on second 429
- `Tts.synthesize()` saves mp3, converts to wav via ffmpeg, removes mp3, returns wav path

### Integration Points
- `src/image_provider.py` (NEW) ← extracted from YouTube.py, imported by both YouTube.py and Podcast.py
- `src/classes/Tts.py` ← add `voice`, `rate` optional params to `synthesize()`
- `src/classes/Podcast.py` ← implement `generate_assets()` using `image_provider` + `Tts`
- `.mp/podcast_{id}/` ← scene images and audio written here alongside `script.json`

</code_context>

<specifics>
## Specific Ideas

- The 7s rate limit between Gemini image requests is important — keep it in `image_provider.py` as module-level state so it works regardless of caller
- `generate_assets()` should print progress per scene (e.g., `Generating assets for scene 1/14...`) — long-running operation

</specifics>

<deferred>
## Deferred Ideas

- File naming convention and resumability mechanism — left to Claude's discretion (standard zero-padded index pattern is fine)
- Audio format choice (WAV retained) — no change needed

</deferred>

---

*Phase: 06-scene-assets*
*Context gathered: 2026-04-01*
