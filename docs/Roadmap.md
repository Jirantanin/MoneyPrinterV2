# MPV2 Roadmap

## Current Product Direction

The current primary product surface in this repo is the Web UI Studio:

- `src/podcast_server.py` for the FastAPI backend
- `src/podcast_ui.html` for the browser UI
- PodcastV2 long-form generation through `/api/v2/*`
- Podcast V1 and Shorts generation through the shared Studio workflow

Legacy Tkinter GUI and ad-hoc manual test scripts were retired as part of the
Web UI cleanup and are no longer part of the intended runtime path.
Retired modules are kept under `src/legacy/` for reference only.

PodcastV2 is now the main long-form lane. The practical goal is not just
"generate a video"; it is a resumable production pipeline with inspectable
script QC, deterministic visual planning, stock-first B-roll, Remotion render,
upload metadata, and cost trace artifacts.

## Shipped

### v1.0 - Video Engagement Upgrade (2026-03-31)

- TTS prosody improvements with configurable Edge voices and rate
- Hook generation for Shorts scripts
- Visual motion with Ken Burns style zooming and FFmpeg subtitle rendering

### v2.0 - YouTube Podcast Module (2026-04-02)

- Full podcast pipeline from script to rendered video and thumbnail
- Fixed 14-scene structure for long-form episodes
- FastAPI studio with SSE progress streaming on port `8899`
- Unified browser UI for Podcast and Shorts workflows

### Post-v2.0 Polish (2026-04-05)

- MiniMax/OpenRouter as primary LLM with Ollama fallback
- Step-by-step approval mode
- Thumbnail Studio panel
- Publish scheduling via YouTube `publishAt`
- Resume from existing `.mp/` episode directories

### PodcastV2 Production Hardening (2026-05)

- Claude/Anthropic script generation path for PodcastV2 with no silent script-provider fallback
- Runtime trace and `cost_summary.json` for estimated provider spend
- Thai Gemini TTS tone preset support, including the stable `natural_storyteller` preset key
- Manual script mode with section parsing and Thai-friendly length/format QC
- `script_sections.json` and `visual_beats.json` artifacts for section-based long-form structure
- Deterministic visual planner in `src/visual_planner.py`
- Inspectable `visual_plan.json` and `stock_query_report.json`
- Secondary visual routing: `Pexels -> Pixabay -> Runware FLUX.1`
- Multi-asset Remotion props for mixed image/video scene assets
- Background bed support for PodcastV2 render
- Terminal cost summary events over the existing SSE stream

## Backlog

### PodcastV2 Quality and Reliability

- Add episode-local Remotion stdout/stderr logs, for example `remotion_render.log`
- Persist explicit render mode/state, for example `remotion`, `fallback_image_concat`, or `failed`
- Add post-render QC for `final.mp4`, duration, scene count, asset count, and B-roll presence
- Add a safe rerender path that intentionally replaces stale `final.mp4`
- Make the cost console live during long asset generation with latest activity deltas
- Improve real-media provider routing for NASA/science, historical/public-domain sources, and real people
- Add duplicate/repetition checks at the visual beat level
- Surface manual script format validation earlier in the Studio UI

### Shorts Quality

- Add royalty-free background music support
- Improve image prompt consistency per niche
- Handle image provider failures for restricted topics more gracefully
- Tune TTS for horror-style narration

### Content Variety

- Multi-niche Shorts rotation
- Series continuity across podcast episodes
- Better Thai-language narration quality

### Growth and Analytics

- YouTube Analytics API integration
- Title and thumbnail experimentation workflows

### More Platforms

- TikTok upload
- Instagram Reels upload
