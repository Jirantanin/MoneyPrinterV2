# MPV2 Roadmap

## Current Product Direction

The current primary product surface in this repo is the Web UI Studio:

- `src/podcast_server.py` for the FastAPI backend
- `src/podcast_ui.html` for the browser UI
- Podcast and Shorts generation through the shared Studio workflow

Legacy Tkinter GUI and ad-hoc manual test scripts were retired as part of the
Web UI cleanup and are no longer part of the intended runtime path.
Retired modules are kept under `src/legacy/` for reference only.

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

## Backlog

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
