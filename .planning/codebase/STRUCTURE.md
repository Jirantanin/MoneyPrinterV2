# STRUCTURE.md — Directory Layout

## Top-Level
```
MoneyPrinterV2/
├── src/                    # All Python source
├── remotion/               # Node.js video renderer
├── fonts/                  # Font files (bold_font.ttf, thai_font.ttf)
├── .mp/                    # Runtime data (git-ignored): JSON cache + temp files
├── .planning/              # GSD planning documents (this directory)
├── config.json             # Active config (git-ignored)
├── config.example.json     # Config template
├── requirements.txt        # Python dependencies
├── client_secrets.json     # YouTube OAuth credentials (git-ignored)
├── token.json              # YouTube OAuth token (git-ignored)
├── scripts/                # Setup/preflight scripts
└── docs/                   # Documentation
```

## `src/` — Python Source
```
src/
├── main.py                 # Interactive menu entry point
├── cron.py                 # Headless subprocess entry point
├── config.py               # 30+ getter functions, reads config.json each call
├── cache.py                # JSON file persistence in .mp/
├── constants.py            # Menu strings, Selenium selectors
├── status.py               # info/success/warning/error colored print helpers
├── utils.py                # rem_temp_files, fetch_songs, etc.
├── art.py                  # ASCII banner (print_banner)
├── llm_provider.py         # Unified generate_text() via Ollama SDK
├── topic_discovery.py      # Trending topic pipeline (Google Trends, News, YouTube)
├── youtube_auth.py         # Standalone YouTube OAuth helper
├── classes/
│   ├── YouTube.py          # Full YT Shorts pipeline (largest class)
│   ├── Twitter.py          # Selenium Twitter automation
│   ├── Tts.py              # TTS wrapper (KittenTTS)
│   ├── AFM.py              # Amazon scraper + LLM pitch generation
│   └── Outreach.py         # Google Maps scraper + email outreach
└── test_*.py               # Ad-hoc test scripts (not a test framework)
```

## `remotion/` — Video Renderer
```
remotion/
├── src/
│   ├── Root.tsx            # registerRoot() — required entry point
│   └── VideoShort.tsx      # Main composition (1080x1920)
├── public/
│   └── assets/             # Staged files before render (images, audio, SRT)
├── scripts/
│   └── render.mjs          # Node.js render script (called by Python subprocess)
├── package.json            # remotion ^4.0.0, react 18.3.1
└── tsconfig.json
```

## Key File Locations
| What | Where |
|------|-------|
| Config | `config.json` (project root) |
| YouTube accounts cache | `.mp/youtube.json` |
| Twitter accounts cache | `.mp/twitter.json` |
| AFM products cache | `.mp/afm.json` |
| Discovered topics cache | `.mp/discovered_topics.json` |
| Temp/output files | `.mp/` or `.mp/YYYYMMDD_HHMMSS/` |
| Remotion staged assets | `remotion/public/assets/` |
| Fonts | `fonts/` |
| OAuth credentials | `client_secrets.json`, `token.json` (project root) |

## Naming Conventions
- Python files: `snake_case.py`
- Classes: `PascalCase` (one class per file in `classes/`)
- Config getters: `get_<thing>()` pattern in `config.py`
- Cache functions: `get_<thing>()`, `add_<thing>()`, `remove_<thing>()` in `cache.py`
- Test files: `test_<feature>.py` (ad-hoc scripts, not pytest)
