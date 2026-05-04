# MoneyPrinter V2

MoneyPrinterV2 in this repo is operated primarily through the Web UI studio.
The current runtime path is a local FastAPI server plus a single HTML frontend
for generating podcast episodes and YouTube Shorts, reviewing outputs, and
uploading to YouTube.

## Primary Runtime

- Backend: `src/podcast_server.py`
- Frontend: `src/podcast_ui.html`
- Default local URL: `http://127.0.0.1:8899`

`src/main.py` still exists as a legacy launcher, but the Web UI is the main
entrypoint for normal use.

## Quick Start

MPV2 requires Python 3.12.

```bash
git clone <your-fork-url>
cd MoneyPrinterV2
python -m venv venv
```

Windows:

```bash
.\venv\Scripts\activate
pip install -r requirements.txt
copy config.example.json config.json
python -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
```

macOS / Linux:

```bash
source venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
```

The server opens the browser automatically and serves the studio at
`http://127.0.0.1:8899`.

## Required Local Setup

- Fill in `config.json` from `config.example.json`
- Install ImageMagick and set `imagemagick_path`
- Make sure Ollama is available if you use local generation
- Provide API keys for the image, upload, and topic-discovery features you use

See [docs/Configuration.md](docs/Configuration.md) for the active configuration
surface used by the Web UI.

## Project Shape

- `src/podcast_server.py`: FastAPI backend and Studio routes
- `src/podcast_ui.html`: main layout shell for the Studio UI
- `src/ui/`: server-composed UI components for Podcast and Shorts
- `src/classes/Podcast.py`: podcast pipeline
- `src/classes/YouTube.py`: Shorts pipeline and YouTube upload helpers
- `src/classes/Tts.py`: TTS dispatch
- `src/legacy/`: retired modules kept for reference only, not part of the active runtime
- `remotion/`: rendering layer kept in repo for current and future video work
- `.planning/`: archived design/history notes, not the main source of truth

## Docs

- [docs/Configuration.md](docs/Configuration.md)
- [docs/Roadmap.md](docs/Roadmap.md)

## Notes

- Legacy Tkinter GUI and ad-hoc manual test scripts were retired during the
  Web UI cleanup.
- Local credentials such as `config.json`, `client_secrets.json`, and
  `token.json` should stay out of version control.

## License

MoneyPrinterV2 is licensed under `Affero General Public License v3.0`. See
[LICENSE](LICENSE) for more information.
