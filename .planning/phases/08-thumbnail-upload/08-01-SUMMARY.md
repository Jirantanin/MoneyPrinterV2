---
phase: 08-thumbnail-upload
plan: "01"
subsystem: podcast
tags: [python, llm, gemini, image-generation, youtube-metadata]

# Dependency graph
requires:
  - phase: 07-ffmpeg-render
    provides: render() producing final.mp4 in episode_dir; Podcast class skeleton with episode_dir set after generate_script()
provides:
  - generate_metadata() method: LLM-powered title/description/tags written to metadata.json
  - generate_thumbnail() method: Gemini dark comic style image written to thumbnail.png
  - Both methods wired into Podcast.run() pipeline before upload()
affects: [08-thumbnail-upload plan 02 (upload() implementation that reads metadata.json and thumbnail.png)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON parse with markdown-fence strip fallback for LLM text output"
    - "Resumability skip via os.path.exists before expensive API call"
    - "Style prompt prefix (self.style_prompt) applied uniformly to all Gemini image prompts"

key-files:
  created: []
  modified:
    - src/classes/Podcast.py

key-decisions:
  - "Fallback metadata uses topic string directly — avoids hard failure if LLM output is unparseable"
  - "thumbnail.png skip check mirrors scene image resumability pattern already used in generate_assets()"
  - "Category ID left to upload() — generate_metadata() only produces title/description/tags consumed by uploader"

patterns-established:
  - "generate_metadata fallback: title=Podcast:{topic[:80]}, description=deep dive about {topic}, tags=[topic, podcast, ...]"
  - "generate_thumbnail prompt format: {style_prompt} A dramatic podcast cover image for an episode about: {topic}. Bold, cinematic composition. No text overlay."

requirements-completed: [THUMB-01, UPLD-02]

# Metrics
duration: 5min
completed: 2026-04-02
---

# Phase 8 Plan 01: Metadata and Thumbnail Generation Summary

**LLM-powered YouTube metadata (title/description/tags) and Gemini dark-comic thumbnail for Podcast pipeline, with JSON fallback parse and resumability**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-02T04:13:00Z
- **Completed:** 2026-04-02T04:15:28Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `generate_metadata()` to Podcast: reads script.json for opening narration context, calls LLM for title/description/tags JSON, falls back gracefully on parse failure, persists to metadata.json
- Added `generate_thumbnail()` to Podcast: applies dark comic style_prompt prefix to thumbnail prompt, calls generate_image(), skips if thumbnail.png already exists
- Updated `run()` to call both methods between `render()` and `upload()` in correct pipeline order
- Added `self.metadata: dict = {}` to `__init__` for attribute initialization

## Task Commits

Each task was committed atomically:

1. **Task 1: Add generate_metadata() and generate_thumbnail() methods to Podcast** - `bf46dbc` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/classes/Podcast.py` - Added generate_metadata(), generate_thumbnail(), self.metadata init; updated run()

## Decisions Made
- Fallback metadata uses topic string directly — avoids hard failure when LLM produces un-parseable text
- thumbnail.png skip check mirrors the scene image resumability pattern already established in generate_assets()
- Category ID (27=Education) will be set in upload() not generate_metadata() — metadata dict only contains title/description/tags

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial AST verification failed due to Windows cp874 codec on the file open — fixed by adding `encoding='utf-8'` to the verification command. Not a code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- metadata.json and thumbnail.png are produced in episode_dir and ready for upload() to consume
- Plan 02 (upload()) can now read metadata.json (title/description/tags) and thumbnail.png for the YouTube API upload call
- No blockers

## Self-Check

Checking claims before finalizing.

---
*Phase: 08-thumbnail-upload*
*Completed: 2026-04-02*
