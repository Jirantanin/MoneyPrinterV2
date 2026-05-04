# STACK.md — Technology Stack

## Runtime & Language
- **Python 3.12** — primary backend
- **Node.js** — Remotion video renderer (`remotion/`)
- **Go** — optional Google Maps scraper binary (external download)

## Python Dependencies (requirements.txt)
| Package | Purpose |
|---------|---------|
| `ollama` | LLM text generation via local Ollama server |
| `kittentts` | TTS voice synthesis (custom wheel from GitHub) |
| `faster-whisper` | Local STT / subtitle generation |
| `assemblyai` | Cloud STT alternative |
| `moviepy` | Video composition (fallback, mostly replaced by Remotion) |
| `Pillow>=10.0.0` | Image processing, Ken Burns effect |
| `selenium`, `selenium_firefox`, `undetected_chromedriver` | Browser automation for Twitter/X |
| `webdriver_manager` | Firefox/Chrome driver management |
| `google-api-python-client`, `google-auth-oauthlib` | YouTube Data API v3 upload |
| `schedule` | In-process cron scheduler |
| `yagmail` | Email sending (SMTP/Gmail) |
| `srt_equalizer` | SRT subtitle normalization |
| `prettytable` | CLI table rendering |
| `termcolor` | Colored CLI output |
| `pytrends` | Google Trends scraping |
| `newsapi-python` | News API for topic discovery |

## Node.js Stack (`remotion/`)
| Package | Version | Purpose |
|---------|---------|---------|
| `remotion` | ^4.0.0 | Video rendering framework |
| `@remotion/cli` | ^4.0.0 | CLI render tool |
| `react` | 18.3.1 | UI components |
| `typescript` | ^5.4.0 | Type checking |

## Image Generation
- **Nano Banana 2** — Gemini image API (`gemini-3.1-flash-image-preview`) via `generativelanguage.googleapis.com`

## Configuration
- `config.json` at project root (git-ignored)
- `config.example.json` as template
- All config values read via getter functions in `src/config.py` — **no caching**, re-reads JSON on every call
- `ROOT_DIR` = `os.path.dirname(sys.path[0])` (project root when running `python src/main.py`)

## Python Version
Python 3.12 (type hints use `str | None` union syntax)
