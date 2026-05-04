# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the application code. Use `src/podcast_server.py` as the primary Web UI entrypoint. `src/main.py` remains as a legacy launcher.
- `src/classes/` holds active runtime components such as `YouTube.py`, `Podcast.py`, and `Tts.py`.
- `src/legacy/classes/` holds retired modules kept only for reference.
- Shared utilities and configuration live in modules like `src/config.py`, `src/utils.py`, `src/cache.py`, and `src/constants.py`.
- `scripts/` contains helper workflows such as setup and preflight checks. Archived scripts live under `scripts/archive/`.
- `docs/` contains active documentation, while `docs/archive/` contains legacy docs kept for reference.

## Build, Test, and Development Commands
- `bash scripts/setup_local.sh`: bootstrap local development, install dependencies, seed `config.json`, run preflight, and point to the Studio launch command.
- `source venv/bin/activate && pip install -r requirements.txt`: manual dependency install or update.
- `python3 scripts/preflight_local.py`: validate local provider and config readiness before running tasks.
- `python3 -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"`: start the Studio Web UI.
- `python3 src/main.py`: start the legacy CLI launcher if needed.

## Coding Style & Naming Conventions
- Target Python 3.12.
- Use 4-space indentation and standard Python naming:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Keep new business logic in focused modules under `src/`.
- Prefer small, explicit functions and preserve the current Web UI-first behavior.

## Testing Guidelines
- There is currently no enforced automated test suite or coverage threshold.
- Minimum validation for changes:
  - Run `python3 scripts/preflight_local.py`
  - Smoke-test the Studio root route and impacted API endpoints
- When adding tests, place them in a top-level `tests/` directory with names like `test_<module>.py`.

## Commit & Pull Request Guidelines
- Follow the existing commit style: imperative summaries like `Fix ...` or `Update ...`, optionally with issue refs.
- Open PRs against `main`.
- Link each PR to an issue, keep scope to one feature or fix, and use a clear title and description.
- Mark not-ready PRs with `WIP` and remove it when ready for review.

## Security & Configuration Tips
- Treat `config.json` as environment-specific; do not commit real API keys or private paths.
- Start from `config.example.json` and prefer environment variables where supported, for example `GEMINI_API_KEY`.
