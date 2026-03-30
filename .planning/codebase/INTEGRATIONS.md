# INTEGRATIONS.md — External Services & APIs

## LLM
| Service | Config key | Notes |
|---------|-----------|-------|
| **Ollama** (local) | `ollama_base_url`, `ollama_model` | Default `http://127.0.0.1:11434`. Model selected at startup interactively if not configured. |

## Image Generation
| Service | Config key | Notes |
|---------|-----------|-------|
| **Gemini image API** ("Nano Banana 2") | `nanobanana2_api_key`, `nanobanana2_model` | Uses `generativelanguage.googleapis.com/v1beta`. Falls back to `GEMINI_API_KEY` env var. Model: `gemini-3.1-flash-image-preview`. Aspect ratio: `9:16`. |

## Speech
| Service | Config key | Notes |
|---------|-----------|-------|
| **KittenTTS** | `tts_voice` | Local TTS, custom wheel. Default voice: `Jasper`. |
| **faster-whisper** | `whisper_model`, `whisper_device`, `whisper_compute_type` | Local STT for subtitle generation. Default: `base` model, `auto` device, `int8` compute. |
| **AssemblyAI** | `assembly_ai_api_key` | Cloud STT alternative (when `stt_provider = "third_party_assemblyai"`). |

## Video Platform
| Service | Auth | Notes |
|---------|------|-------|
| **YouTube Data API v3** | OAuth2 (`client_secrets.json` + `token.json`) | Scopes: `youtube.upload`, `youtube.readonly`. Token refreshed automatically via `google-auth`. |

## Social Media Automation
| Service | Method | Notes |
|---------|--------|-------|
| **Twitter/X** | Selenium + pre-authenticated Firefox profile | Never handles login. Profile path per-account in cache JSON. Uses `undetected_chromedriver` as fallback. |

## Web Scraping / Data
| Service | Config key | Notes |
|---------|-----------|-------|
| **Google Maps** | `google_maps_scraper` (zip URL), `google_maps_scraper_niche` | Downloads Go binary at runtime. Timeout: `scraper_timeout` (default 300s). |
| **Amazon** | — | Scraped via Selenium/requests in `src/classes/AFM.py`. |
| **Google Trends** | — | `pytrends` library used in `src/topic_discovery.py`. |
| **NewsAPI** | `topic_discovery.news_api_key` | Used in topic discovery pipeline. |

## Email
| Service | Config key | Notes |
|---------|-----------|-------|
| **Gmail SMTP** | `email.smtp_server`, `email.username`, `email.password` | Via `yagmail`. Default: `smtp.gmail.com:587`. |

## Topic Discovery (optional)
| Service | Config key |
|---------|-----------|
| YouTube Data API (trending) | `topic_discovery.youtube_api_key` |
| Anthropic Claude API | `topic_discovery.anthropic_api_key` |
| NewsAPI | `topic_discovery.news_api_key` |
| Google Trends | (no key, pytrends) |
