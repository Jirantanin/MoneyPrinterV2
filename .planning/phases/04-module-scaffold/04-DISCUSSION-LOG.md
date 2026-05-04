# Phase 4: Module Scaffold - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 04-module-scaffold
**Areas discussed:** Podcast.py class skeleton

---

## Podcast.py class skeleton

### How should Podcast.py expose its pipeline?

| Option | Description | Selected |
|--------|-------------|----------|
| Granular step methods | generate_script(), generate_assets(), render(), upload() — each phase fills in one method | ✓ |
| Single run() entry point | One run() calls all steps internally | |
| Phase-gated run() | run(phase=N) skips steps above N | |

**User's choice:** Granular step methods
**Notes:** Matches the 4 downstream phases exactly; makes incomplete state explicit.

---

### Should Podcast.py also have a run() that calls the steps in order?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, run() calls all steps | main.py calls podcast.run(); steps individually testable | ✓ |
| No, main.py calls steps directly | main.py orchestrates sequence | |

**User's choice:** Yes, run() calls all steps
**Notes:** Single call site for main.py; keeps pipeline logic inside Podcast class.

---

### What should stub methods do in Phase 4?

| Option | Description | Selected |
|--------|-------------|----------|
| Raise NotImplementedError | raise NotImplementedError('Phase N: not yet implemented') | ✓ |
| Print + return None | Prints message, returns None silently | |
| Pass silently | Empty pass | |

**User's choice:** Raise NotImplementedError
**Notes:** Explicit gaps, easy to grep, prevents silent no-ops.

---

## Claude's Discretion

- Menu placement — standard position before Quit
- Config getter pattern — follow existing config.py conventions
- config.example.json defaults — use REQUIREMENTS.md values

## Deferred Ideas

None.
