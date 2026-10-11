# MoneyPrinter V2: Producer Mode

This repository is focused on the local documentary production workflow. The supported path is the Producer Mode CLI, its review tools, and the Remotion renderer.

## Quick start

Python 3.12 is recommended.

Windows PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
python scripts/producer_mode.py --help
```

macOS/Linux:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python scripts/producer_mode.py --help
```

Set the provider keys needed for the episode in `config.json`. For Remotion rendering, install the Node dependencies from `remotion/` with `npm install`. See [Configuration](docs/Configuration.md) and the [Producer Mode workflow](docs/producer-mode-workflow.md).

## Supported production surface

- `scripts/producer_mode.py`: episode plans and production checkpoints
- `scripts/producer_review.py`: review, validation, and render preparation
- `src/producer_*.py`: Producer Mode production stages
- `remotion/src/VideoPodcast.tsx`: documentary renderer
- `remotion/src/ClipShort.tsx`: retained for the adjacent `moneyprinter-shorts-pack` skill
- `src/classes/Tts.py`: shared Gemini TTS implementation
- `src/llm_provider.py` and provider modules: text and media providers

The former Studio web UI, its Podcast/Shorts automation APIs, scheduled runners, and the separate APOD automation have been removed.

## Local data

Episode work and generated media live under `.mp/`. Keep local credentials such as `config.json`, `client_secrets.json`, and `token.json` out of version control. Preserve source episodes when starting a new revision.

## License

MoneyPrinterV2 is licensed under the Affero General Public License v3.0. See [LICENSE](LICENSE).
