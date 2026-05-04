# Configuration

The active runtime in this repo is the Web UI Studio served by
`src/podcast_server.py`. Configuration lives in `config.json` at the repo root
and should be created from `config.example.json`.

## Core Runtime Settings

- `ollama_base_url`: local Ollama base URL
- `ollama_model`: default Ollama model for text generation fallback
- `minimax_api_key`: OpenRouter API key for MiniMax
- `minimax_api_base_url`: OpenRouter base URL
- `minimax_model`: MiniMax model name
- `nanobanana2_api_base_url`: image API base URL
- `nanobanana2_api_key`: image API key, falls back to `GEMINI_API_KEY`
- `nanobanana2_model`: image generation model
- `nanobanana2_aspect_ratio`: image aspect ratio for generated visuals
- `threads`: worker count for local media processing
- `imagemagick_path`: path to `magick.exe` on Windows or `convert` on Unix

## TTS and Subtitle Settings

- `tts_provider`: current TTS engine, default `edge`
- `tts.edge.voice`: Edge voice name for default narration
- `tts.edge.rate`: Edge speed adjustment
- `stt_provider`: subtitle transcription provider
- `whisper_model`: local Whisper model
- `whisper_device`: `auto`, `cpu`, or `cuda`
- `whisper_compute_type`: local Whisper compute type
- `assembly_ai_api_key`: AssemblyAI key if using third-party transcription
- `tts_voice`: legacy value kept for backward compatibility

## Podcast Settings

The Studio reads podcast system settings through `src/config.py` and supports
both nested settings and older flat keys.

- `podcast_narrator.name`: narrator name used in prompting
- `podcast_narrator.persona`: narrator persona used in prompting
- `podcast_narrator.tts_voice`: narrator voice
- `podcast_narrator.tts_rate`: narrator speech rate
- `podcast_style_prompt`: style suffix appended to generated podcast image prompts
- `elevenlabs_voice_id_th`: Thai ElevenLabs voice id when that path is enabled

## Shorts and Upload Settings

- `is_for_kids`: YouTube audience flag for uploads
- `font`: subtitle or graphics font file in `fonts/`
- `client_secrets.json`: local OAuth client config for YouTube upload
- `token.json`: generated local OAuth token for YouTube upload

## Topic Discovery Settings

- `topic_discovery.enabled`: enable scheduled topic discovery
- `topic_discovery.youtube_api_key`: YouTube Data API key
- `topic_discovery.news_api_key`: NewsAPI key
- `topic_discovery.anthropic_api_key`: Anthropic key for scoring if used
- `topic_discovery.scoring_provider`: `ollama` or `anthropic`
- `topic_discovery.geo`: region code such as `TH` or `US`
- `topic_discovery.max_topic_age_hours`: freshness window for candidates

## Legacy Local Values

`firefox_profile` remains in the example config only for older browser-driven
helpers. It is not part of the main Studio runtime.
Modules under `src/legacy/` may still reference older config concepts, but that
folder is reference-only and not part of the supported runtime path.

## Environment Variable Fallbacks

- `GEMINI_API_KEY`: used when `nanobanana2_api_key` is empty

## Recommended Workflow

1. Copy `config.example.json` to `config.json`
2. Fill in only the providers you actually use
3. Keep `config.json`, `client_secrets.json`, and `token.json` local only
4. Launch the Studio from `src/podcast_server.py`
