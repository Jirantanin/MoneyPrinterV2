# CLAUDE.md

Guidance for work in this repository.

## Project Focus

The supported product workflow is MoneyPrinter Producer Mode: evidence-backed Thai documentary planning, assets, narration, review, and revision-bound rendering. The production flow is operated through local CLI tools and the Producer Mode skill, not a web automation studio.

The adjacent `moneyprinter-shorts-pack` skill uses the Remotion `ClipShort` composition. TypeSafe asset review is advisory and cannot replace producer review.

## Entry Points

- `scripts/producer_mode.py`: plan and checkpoint CLI
- `scripts/producer_review.py`: checks and render preparation
- `src/producer_*.py`: production stages
- `src/producer_contract.py`: canonical episode specification
- `remotion/src/VideoPodcast.tsx`: Remotion documentary composition (opt-in with `"renderer": "remotion"`; plans without `render_settings` fall back to it)
- `remotion/src/ClipShort.tsx`: Shorts Pack composition
- `src/producer_minimal_renderer.py` + `doc_renderer/`: default documentary renderer; `producer_mode.py init` writes `render_settings.renderer = "minimal_doc"` into new plans (see `docs/Configuration.md`)
- `src/producer_score.py` + `scripts/producer_score.py`: composed procedural score bed from a cue sheet (`render_settings.background_bed`)
- `doc_renderer/gfx_kit/` + `src/producer_sfx_synth.py`: flat explainer-graphic kit, recorder and designed SFX stems
- `src/classes/Tts.py`: Gemini TTS implementation
- `src/llm_provider.py`: Anthropic, MiniMax/OpenRouter, and local Ollama routing
- `scripts/youtube_upload.py` + `src/youtube_upload.py`: user-directed YouTube upload/schedule of a finished episode (private or scheduled `publishAt`, receipts in `upload_pack/`); see the `moneyprinter-youtube-upload` skill

The former Studio server/UI, automated Podcast/Shorts flows, scheduled runner, and separate APOD automation have been removed. The YouTube uploader is not automation: nothing runs on a schedule, and each upload records the user's explicit instruction.

## Local Setup

Use Python 3.12, install `requirements.txt`, copy `config.example.json` to the ignored local `config.json`, and run `python scripts/producer_mode.py --help`. For video rendering, install Node dependencies in `remotion/`.

See `docs/Index.md`, `docs/Configuration.md`, and `docs/producer-mode-workflow.md`. Do not expose credentials or delete episode data during code cleanup.
