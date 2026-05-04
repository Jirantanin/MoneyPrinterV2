# CONVENTIONS.md — Code Style & Patterns

## Import Style
- Wildcard imports are common: `from config import *`, `from cache import *`, `from utils import *`
- Class files use relative imports: `from .Tts import TTS`
- `sys.path` manipulation: `src/` is added to `sys.path` at startup so all imports use bare module names

## Config Pattern
Every config value read via dedicated getter function in `src/config.py`:
```python
def get_tts_voice() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("tts_voice", "Jasper")
```
- **No caching** — JSON file re-read on every call
- All getters follow `get_<key>()` naming
- Default values provided via `.get(key, default)`

## Status/Output Pattern
`src/status.py` provides colored console helpers used everywhere:
```python
info("Starting...")       # blue
success("Done!")          # green
warning("Be careful")     # yellow
error("Failed")           # red
question("Input: ")       # returns user input
```

## Class Structure
Pipeline classes (`YouTube`, `Twitter`, `AFM`, `Outreach`) follow:
- `__init__` receives account-level config (uuid, nickname, niche, etc.)
- Private attributes prefixed with `_` (e.g. `self._account_uuid`)
- Properties with `@property` for getters
- Methods return `None` or specific types with docstrings

## Error Handling
- Minimal structured error handling — mostly `try/except ValueError` for user input
- Errors printed via `error()` helper then continue or `sys.exit(1)`
- No custom exception classes
- External API calls (Gemini, Ollama, YouTube) have no retry logic

## Type Hints
- Used consistently in function signatures: `str | None` union syntax (Python 3.10+)
- `List[dict]` from `typing` for return types in `cache.py`
- No `TypedDict` or dataclasses for data structures

## Docstrings
- Google-style docstrings on all functions: Args, Returns sections
- Present even for simple getters

## Subprocess Calls
```python
# Remotion render
subprocess.run(["node", "scripts/render.mjs", props_path])

# CRON worker
subprocess.run(["python", "src/cron.py", platform, account_id, model])

# Windows: npx requires shell=True
subprocess.run(["npx", ...], shell=True)
```

## Asset Staging Pattern
Before Remotion render, all assets must be copied to `remotion/public/assets/`:
```python
shutil.copy(local_file, os.path.join(ROOT_DIR, "remotion", "public", "assets", filename))
```
`staticFile()` in Remotion only resolves paths under `public/`.
