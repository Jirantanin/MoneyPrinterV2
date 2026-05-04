# Phase 6: Scene Assets - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 06-scene-assets
**Areas discussed:** Image gen code location, TTS voice/rate source

---

## Image gen code location

| Option | Description | Selected |
|--------|-------------|----------|
| Extract to image_provider.py | Pull generate_image_nanobanana2() and _persist_image() out of YouTube.py into a new src/image_provider.py module. Both YouTube.py and Podcast.py import from it. Also covers Phase 8 thumbnail. | ✓ |
| Copy into Podcast.py | Duplicate the Gemini image gen code inside Podcast.py. Faster now, but two copies to maintain. | |
| You decide | Claude picks the cleanest approach given the codebase. | |

**User's choice:** Extract to image_provider.py

---

## Refactor YouTube.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Refactor YouTube.py to import from image_provider.py | Single source of truth. Slightly more work but eliminates duplication permanently. | ✓ |
| YouTube.py keeps its own copy for now | Less risk — don't touch the working Shorts pipeline. Podcast.py gets a clean image_provider.py. | |

**User's choice:** Refactor YouTube.py to import from image_provider.py

---

## TTS voice/rate source

| Option | Description | Selected |
|--------|-------------|----------|
| Add optional voice/rate params to Tts.synthesize() | synthesize(text, output_file, voice=None, rate=None) — if provided, use them; otherwise fall back to Shorts config. Minimal change to Tts.py. | ✓ |
| Call edge-tts directly in Podcast.py | Bypass Tts.py entirely. No Tts.py changes, but duplicates mp3→wav conversion. | |
| You decide | Claude picks the cleanest approach. | |

**User's choice:** Add optional voice/rate params to Tts.synthesize()

---

## Claude's Discretion

- Scene file naming convention
- Resumability check logic
- Order of operations within generate_assets()
- Audio format (WAV retained)

## Deferred Ideas

None — discussion stayed within phase scope.
