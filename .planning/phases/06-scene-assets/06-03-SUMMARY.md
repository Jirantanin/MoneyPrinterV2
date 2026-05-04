---
phase: 06-scene-assets
plan: "03"
subsystem: podcast-assets
tags: [podcast, image-generation, tts, resumability, image_provider, refactor]

# Dependency graph
requires:
  - "06-01: src/image_provider.py with generate_image(prompt, output_path)"
  - "06-02: Tts.synthesize() voice/rate override params"
provides:
  - "src/classes/Podcast.py: working generate_assets() — reads script.json, emits 14 PNG+WAV pairs"
  - "src/classes/YouTube.py: image gen delegated to image_provider, _last_image_time removed"
affects:
  - "Podcast pipeline: generate_assets() unblocked for Phase 7 rendering"
  - "YouTube pipeline: image gen logic unified under image_provider.py"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-file resumability: os.path.exists(image_path) and os.path.exists(audio_path) guard before generate"
    - "Style lock prefix: self.style_prompt prepended to every image_prompt before calling generate_image (IMG-02)"
    - "Delegation pattern: YouTube._persist_image and generate_image_nanobanana2 delegate to image_provider functions"

key-files:
  created: []
  modified:
    - src/classes/Podcast.py
    - src/classes/YouTube.py

key-decisions:
  - "generate_assets() checks image and audio existence independently — partial re-runs regenerate only the missing file"
  - "YouTube._last_image_time removed from class state; rate limit now fully owned by image_provider module state"
  - "generate_image_nanobanana2 creates UUID path itself then passes to _ip_generate_image — image_provider never touches self.run_dir"

requirements-completed: [IMG-01, IMG-02, IMG-03, TTS-01, TTS-02, TTS-03]

# Metrics
duration: 12min
completed: 2026-04-02
---

# Phase 6 Plan 03: Implement Podcast.generate_assets() and refactor YouTube.py to use image_provider — Summary

**Podcast.generate_assets() implemented with 14-scene image+audio pipeline, resumability, and style lock; YouTube.py image generation delegated to image_provider removing duplicate Gemini logic and _last_image_time**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-04-02
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

### T1 — Podcast.generate_assets()

- Added `from image_provider import generate_image` import
- Added `self.episode_dir: str = ""` to `__init__`
- Assigned `self.episode_dir = episode_dir` at end of `generate_script()` before return
- Replaced `raise NotImplementedError("Phase 6: not yet implemented")` stub with full implementation:
  - Validates `self.episode_dir` is set (raises ValueError if not)
  - Reads and validates `script.json` (must be exactly 14 scenes)
  - Per-scene loop with `str(i).zfill(2)` naming: `scene_00.png` through `scene_13.png`, `scene_00.wav` through `scene_13.wav`
  - Resumability: both-file check skips already-generated scenes; per-file checks allow regenerating partial pairs
  - Style lock (IMG-02): `styled_prompt = f"{self.style_prompt} {scene['image_prompt']}"` prepended before every `generate_image()` call
  - TTS uses `voice=narrator["tts_voice"]` and `rate=narrator["tts_rate"]` from podcast_narrator config

### T2 — YouTube.py refactor

- Added `from image_provider import generate_image as _ip_generate_image` module-level import
- Removed `self._last_image_time: float = 0.0` from `__init__` (rate limiting now in image_provider module state)
- `_persist_image()`: delegates byte write to `image_provider._persist_image`, retains `self.images.append`
- `generate_image_nanobanana2()`: creates UUID path, delegates to `_ip_generate_image(prompt, image_path)`, appends on success
- `generate_image()`: now a single-line delegation `return self.generate_image_nanobanana2(prompt)` — all rate limit logic removed

## Task Commits

1. **T1: Implement Podcast.generate_assets()** - `d153824` (feat)
2. **T2: Refactor YouTube.py image gen to image_provider** - `51c8759` (refactor)

## Files Created/Modified

- `src/classes/Podcast.py` — generate_assets() stub replaced with full implementation; self.episode_dir tracking added; generate_image import added
- `src/classes/YouTube.py` — _persist_image, generate_image_nanobanana2, generate_image refactored to delegate to image_provider; _last_image_time removed

## Decisions Made

- Per-file resumability: image and audio existence are checked separately — if only the image is missing, only the image is regenerated (and vice versa). This is more robust than the per-scene (both-or-neither) check.
- `generate_image_nanobanana2` creates the UUID path itself and passes it to `_ip_generate_image` — image_provider.py never references `self.run_dir`, preserving the caller-controlled path pattern from 06-01.
- `self._last_image_time` fully removed from YouTube class — no duplicate rate-limit tracking.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `Podcast.render()` — raises `NotImplementedError("Phase 7: not yet implemented")` — intentional, Phase 7 scope
- `Podcast.upload()` — raises `NotImplementedError("Phase 8: not yet implemented")` — intentional, Phase 8 scope

These stubs do not affect plan 06-03's goal (generate_assets is fully implemented).

## Self-Check: PASSED

- src/classes/Podcast.py: FOUND
- src/classes/YouTube.py: FOUND
- 06-03-SUMMARY.md: FOUND
- commit d153824: FOUND
- commit 51c8759: FOUND
- `from image_provider import generate_image` in Podcast.py: FOUND (line 20)
- `self.episode_dir: str = ""` in Podcast.py: FOUND (line 51)
- `self.episode_dir = episode_dir` in Podcast.py: FOUND (line 221)
- `scene_num = str(i).zfill(2)` in Podcast.py: FOUND (line 254)
- `Generating assets for scene` in Podcast.py: FOUND (line 263)
- `styled_prompt = f"{self.style_prompt}` in Podcast.py: FOUND (line 269)
- `voice=narrator["tts_voice"]` in Podcast.py: FOUND (line 279)
- `from image_provider import generate_image as _ip_generate_image` in YouTube.py: FOUND (line 16)
- `_last_image_time` in YouTube.py: NOT FOUND (removed correctly)
- `_ip_generate_image(prompt, image_path)` in YouTube.py: FOUND (line 338)

---
*Phase: 06-scene-assets*
*Completed: 2026-04-02*
