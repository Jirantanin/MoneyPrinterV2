# TESTING.md — Test Structure & Practices

## Status
**No formal test framework.** No pytest, no unittest, no CI pipeline.

## Ad-hoc Test Scripts
Located in `src/` and project root, run manually:

| File | Purpose |
|------|---------|
| `src/test_subtitle.py` | Test subtitle rendering |
| `src/test_combine_subtitle.py` | Test subtitle combination with video |
| `src/test_ken_burns.py` | Test Ken Burns image animation effect |
| `src/test_render_fix.py` | Test Remotion render pipeline fixes |
| `src/test_upload.py` | Test YouTube API upload |
| `test_generate.py` | Test video generation pipeline |

## How to Run
These are standalone scripts, not test cases:
```bash
python src/test_subtitle.py
python src/test_ken_burns.py
```

## Manual Testing Approach
- Run `python src/main.py` and exercise each menu option
- Remotion: `cd remotion && node scripts/render.mjs <props-json-path>`
- TypeScript check: `cd remotion && npx tsc --noEmit --skipLibCheck`

## No Mocking
Tests use real services (actual Ollama, actual Gemini API, actual YouTube API). No dependency injection or mocking infrastructure.

## Preflight Check
`python scripts/preflight_local.py` — validates external services are reachable before running.
