# Repository Guidelines

## Project Structure

- `src/producer_*.py`: Producer Mode planning, evidence, asset, narration, review, and render stages.
- `src/producer_mode.py`: production plan and checkpoint helpers.
- `src/producer_contract.py`: canonical episode contract.
- `src/classes/Tts.py`: shared Gemini TTS implementation used by Producer Mode.
- `src/llm_provider.py`, `src/pexels_provider.py`, `src/pixabay_provider.py`, and `src/runware_provider.py`: provider integrations.
- `remotion/src/VideoPodcast.tsx`: opt-in Remotion documentary composition; older plans without `render_settings` fall back to it.
- `remotion/src/ClipShort.tsx`: composition used by the adjacent Shorts Pack skill.
- `src/producer_minimal_renderer.py` + `doc_renderer/`: default documentary renderer, written into new plans as `render_settings.renderer = "minimal_doc"`.
- `docs/`: active workflow documentation and retained historical references.
- `.mp/`: local episode work and generated media; do not remove as part of source cleanup.

The old Studio UI/API, automated Podcast and Shorts pipelines, scheduled runner, and APOD automation are retired and must not be reintroduced as the primary workflow.

## Development Commands

- `bash scripts/setup_local.sh`: create the Python environment, install requirements, and print the Producer Mode entry command.
- `python scripts/preflight_local.py`: check local Producer Mode configuration without calling provider APIs.
- `python scripts/producer_mode.py --help`: inspect plan and checkpoint commands.
- `python scripts/producer_review.py --help`: inspect review and render-preparation commands.
- For Remotion: run `npm install` in `remotion/`, then use the Producer Mode render command.

Target Python 3.12. Use four-space indentation, `snake_case` for Python functions and variables, and `PascalCase` for classes.

## Validation and Data Safety

Do not add or run tests unless the user asks. For workflow changes, use static source inspection and `git diff --check`; do not call paid providers or render video without the authorization required by Producer Mode.

Preserve existing working-tree edits, episode folders, local credentials, and generated media unless the user explicitly asks to remove those exact items. Keep config values and secrets out of commits.

## Contributions

Use imperative commit summaries such as `Fix ...` or `Update ...`. Keep changes scoped and describe user-visible behavior and validation in pull requests.
