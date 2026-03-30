---
phase: 01-tts-prosody
plan: 01
subsystem: tts
tags: [edge-tts, python, config, tts-rate, prosody]

# Dependency graph
requires: []
provides:
  - get_tts_rate() getter in src/config.py returning configurable speaking rate with "+20%" default
  - tts_rate key in config.example.json for user tuning
  - edge-tts Communicate called with rate= kwarg in _edge_tts_synthesize
  - Full TTS pipeline generates audio at +20% speaking rate (configurable)
affects:
  - 02-hook-generation (imports get_tts_rate for audio duration estimation)
  - 03-ken-burns-transitions (depends on audio duration set by this phase)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config re-read on every call: get_tts_rate() called inside synthesize() not __init__() — matches existing get_tts_voice() pattern"
    - "edge-tts rate format: string with explicit sign and percent (e.g. '+20%') not a bare number"

key-files:
  created: []
  modified:
    - src/config.py
    - src/classes/Tts.py
    - config.example.json

key-decisions:
  - "Migrate Tts.py from KittenTTS to edge-tts: worktree had older KittenTTS version; plan targets edge-tts (matches main project working-tree state)"
  - "Do NOT expose tts_pitch in config: edge-tts pitch= kwarg silently ignored by Microsoft backend since v6.0.3"
  - "Fetch rate inside synthesize() not __init__(): config re-read per call is the project convention for hot-reload support"

patterns-established:
  - "TTS rate format: use '+N%' signed percent strings for all edge-tts prosody parameters"
  - "Config getter placement: new getters inserted adjacent to related getters (get_tts_rate after get_tts_voice)"

requirements-completed: [TTS-01, TTS-02]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 01 Plan 01: TTS Prosody — Speaking Rate Summary

**edge-tts Communicate wired with configurable rate= kwarg; get_tts_rate() getter added with "+20%" default for energetic Shorts pacing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-31T00:12:35Z
- **Completed:** 2026-03-31T00:15:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `get_tts_rate()` to `src/config.py` immediately after `get_tts_voice()`, returning `tts_rate` from config with `"+20%"` default
- Added `"tts_rate": "+20%"` to `config.example.json` adjacent to `tts_voice` for discoverability
- Migrated `src/classes/Tts.py` from KittenTTS to edge-tts and wired rate parameter through the full call chain: `synthesize()` → `_edge_tts_synthesize()` → `edge_tts.Communicate(text, voice, rate=rate)`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_tts_rate() getter and tts_rate config key** - `619b6cb` (feat)
2. **Task 2: Wire get_tts_rate() into Tts.py** - `df7bda7` (feat)

## Files Created/Modified

- `src/config.py` — Added `get_tts_rate()` function after `get_tts_voice()` (line ~235); returns `json.load(file).get("tts_rate", "+20%")`
- `src/classes/Tts.py` — Migrated to edge-tts; `_edge_tts_synthesize` now accepts `rate: str` and passes it to `edge_tts.Communicate`; `synthesize()` calls `get_tts_rate()` on every invocation
- `config.example.json` — Added `"tts_rate": "+20%"` immediately after `"tts_voice"` key

## Final Function Signatures (for Phase 2 reference)

`get_tts_rate()` in `src/config.py`:
```python
def get_tts_rate() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("tts_rate", "+20%")
```

`_edge_tts_synthesize` signature in `src/classes/Tts.py`:
```python
async def _edge_tts_synthesize(text: str, output_mp3: str, voice: str, rate: str) -> None:
```

## Decisions Made

- **Migrate KittenTTS to edge-tts:** The worktree had an older KittenTTS-based Tts.py. The plan was written against the edge-tts version (the main project working-tree state). Applied the migration as part of Task 2 to match the intended implementation target.
- **No tts_pitch:** pitch= is silently ignored by Microsoft's backend since edge-tts v6.0.3. Documented this in the getter's docstring to prevent future re-introduction.
- **Rate fetched in synthesize() not __init__():** Follows the project convention of re-reading config on every call so changes to config.json take effect without restarting the process.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] KittenTTS to edge-tts migration in worktree**
- **Found during:** Task 2 (Wire get_tts_rate into Tts.py)
- **Issue:** Worktree's `src/classes/Tts.py` used KittenTTS (`kittentts.KittenModel`), not edge-tts. The plan's "CURRENT STATE" interface described the edge-tts version (which matched the main project working-tree). Applying the plan's rate changes to the KittenTTS version would produce incorrect code.
- **Fix:** Rewrote Tts.py to the edge-tts implementation (matching the plan's "CURRENT STATE"), then applied the rate changes as specified.
- **Files modified:** `src/classes/Tts.py`
- **Verification:** Import check passes; `Communicate(text, voice, rate=rate)` confirmed; no old call pattern present.
- **Committed in:** `df7bda7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug/inconsistency between worktree and plan target state)
**Impact on plan:** Necessary to achieve correct implementation. No scope creep. Final result exactly matches plan's must_haves artifacts and key_links.

## Issues Encountered

- The worktree Python environment lacks `srt_equalizer` (pre-existing, out-of-scope). Import verification was run using the main project venv which has all dependencies installed. Import succeeds cleanly.

## User Setup Required

None — no external service configuration required. Users can tune speaking rate by editing `tts_rate` in `config.json`. The default `"+20%"` is active immediately if the key is absent.

## Next Phase Readiness

- Phase 02 (Hook Generation) can now import `get_tts_rate()` from `src/config.py`
- Audio duration from TTS will reflect the +20% rate, which affects hook timing estimates
- No blockers for Phase 02

---
*Phase: 01-tts-prosody*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: src/config.py
- FOUND: src/classes/Tts.py
- FOUND: config.example.json
- FOUND: .planning/phases/01-tts-prosody/01-01-SUMMARY.md
- FOUND: commit 619b6cb (Task 1)
- FOUND: commit df7bda7 (Task 2)
