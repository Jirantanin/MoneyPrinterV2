# CONCERNS.md — Technical Debt & Concerns

## Performance

### config.py: No caching (file re-read on every call)
Every `get_*()` function in `src/config.py` opens and parses `config.json` from disk. During video generation, this is called dozens of times in sequence.
- **Impact:** Minor I/O overhead in hot paths
- **Location:** `src/config.py` — all getter functions

### Remotion asset staging is fragile
Assets must be manually copied to `remotion/public/assets/` before render. If a previous run left stale files, the wrong assets can be used.
- **Location:** `src/classes/YouTube.py` — `combine_remotion()`

## Reliability

### No retry logic on external API calls
Gemini image API, Ollama, and YouTube API calls have no retry/backoff. A transient network error fails the entire pipeline.
- **Location:** `src/classes/YouTube.py`, `src/llm_provider.py`

### CRON runs in-process (process death = lost schedule)
`schedule` library runs in the same Python process as the interactive menu. If the process crashes or is restarted, all scheduled jobs are lost. No persistence.
- **Location:** `src/main.py` — CRON setup sections

### `rem_temp_files()` cleans `.mp/` aggressively
On each startup, non-JSON files in `.mp/` are deleted. Any in-progress render files from a previous interrupted run are lost.
- **Location:** `src/utils.py`

### Global `_selected_model` state in llm_provider.py
`select_model()` sets a module-level global. If `cron.py` is run without passing a model argument, it hard-fails. The model must be passed as `sys.argv[3]`.
- **Location:** `src/llm_provider.py`, `src/cron.py`

## Security

### `client_secrets.json` and `token.json` at project root
YouTube OAuth credentials sit unprotected at the project root. Both are in `.gitignore` but could accidentally be committed.

### Firefox profiles contain pre-authenticated sessions
Twitter/X automation relies on saved browser sessions. Profile paths stored in plain JSON cache (`.mp/twitter.json`).

### `zip_url` config downloads and executes external binary
Google Maps scraper is downloaded from a configurable URL (`google_maps_scraper`) and executed. A supply chain compromise in this URL would execute arbitrary code. (Fixed for song archive in commit `aa1d8f6` but the scraper URL remains user-configurable.)

### Wildcard imports expose namespace
`from config import *`, `from cache import *`, etc. throughout `main.py` and class files make it hard to trace where names come from and could cause silent shadowing.

## Maintainability

### `src/main.py` is very large (~528 lines)
All 4 platform workflows are inline in one function. Hard to test or extend individual workflows.

### `src/classes/YouTube.py` is the most complex file
Full pipeline from topic generation to YouTube upload. Tightly coupled — hard to unit test individual stages.

### No structured logging
All output goes through `status.py` print helpers. No log levels, no log files, no structured output for monitoring automated runs.

### `combine_moviepy()` is dead code
Kept as fallback but `combine_remotion()` is the active path. Creates confusion about which render path is in use.
- **Location:** `src/classes/YouTube.py`

## Windows-Specific Issues
- Must use `py` not `python` on Windows (Microsoft Store alias)
- `npx` inside Node subprocesses requires `shell=True`
- Path separators in config may need attention if config.json is shared across OSes
