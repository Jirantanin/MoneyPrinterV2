# Producer Mode Configuration

Create local settings by copying `config.example.json` to `config.json`. Keep that file and all API credentials out of version control.

## Text models

- `minimax_api_key`: OpenRouter key for the configured MiniMax model.
- `minimax_api_base_url`: OpenRouter-compatible API base URL; defaults to `https://openrouter.ai/api/v1`.
- `minimax_model`: default MiniMax model, for example `minimax/minimax-m2.5:free`.
- `anthropic_api_key`: Claude API key; `ANTHROPIC_API_KEY` is also supported.
- `anthropic_model`: Claude model, currently defaulted to `claude-sonnet-4-6`.
- `podcast_settings.models`: model and voice settings shared with Producer Mode helpers.

An explicit Claude model routes to Anthropic. Calls without an explicit Claude model use MiniMax when its OpenRouter key is configured, then the local Ollama fallback if available.

## Narration and visual assets

- `gemini_tts_api_key`: Gemini TTS key. It can fall back to `nanobanana2_api_key` or `GEMINI_API_KEY`.
- `gemini_tts_model`: default `gemini-3.8-flash-tts` (Interactions API; the transcript is spoken verbatim and delivery direction is sent as a `speech_metadata` style annotation). `gemini-3.8-flash-lite-tts` is cheaper but Google does not list Thai for it.
- `podcast_settings.voices.thai_gemini_voice`: Gemini voice name; default is `en-us-knox` (Extended Library voice chosen in the 2026-10-11 audition; it reads Thai cleanly). Prebuilt names such as `Enceladus` also work.
- TTS tone preset: new plans record `audio_rules.tone_preset = "host_dry"`, one short constant delivery style. Since 2026-10-13 scripts are written for an explainer narrator who speaks as เรา (no ผม); the Knox `host_dry` delivery stays. Plans without it fall back to `natural_storyteller`; `produce-tts --tone-preset` overrides both.
- `pexels_api_key`, `pixabay_api_key`: stock video b-roll. `expand-broll --allow-stock` fills slots with Pexels/Pixabay clips (free APIs). It needs the episode's `broll_keywords.json` (`official_queries`, `official_markers`, `official_blocked`, `stock_default`, `stock_by_section`, `stock_by_asset_id`) whenever `--allow-stock` or `--fresh-official` is used; `--legacy-keyword-tables` reproduces older episodes with the built-in tables.
- `runware_api_key`: generated-image provider (paid), also supported as `RUNWARE_API_KEY`. Generated section openers (`codex_imagegen` slots in the plan) are fulfilled by `produce-assets --allow-runware`; without the flag they stay pending tasks.
- `runware_image_*`: model, dimensions, steps, format, and retry settings for Runware b-roll fallback images. `runware_hero_image_width` / `runware_hero_image_height` (default 1920x1088) size the section-opener images. Runware requires dimensions divisible by 64.
- `podcast_settings.audio`: background bed path, volume, ducking, and fade settings.

Provider use depends on the selected plan and asset. Missing optional stock or image keys should not be replaced with placeholder credentials.

## Local requirements

Install Python dependencies from `requirements.txt`. Remotion rendering also requires Node.js and dependencies installed under `remotion/`. The local preflight checks configuration and tool presence only; it does not send API requests or spend credits.

## Renderer selection

`producer_mode.py init` writes the minimal documentary renderer into new plans:

```json
"render_settings": {"renderer": "minimal_doc"}
```

The choice is copied into the prepared props, so it is part of the render revision; switching renderer after authorization requires a new prepare and new consent. `minimal_doc` needs `npm install` in `doc_renderer/` and reuses the headless Chrome bundled with `remotion/`. Video b-roll is decoded to frames and played once through its slot (a clip shorter than its slot holds its last frame and is reported as a warning, never looped). Custom graphics recorded to MP4 play like any video slot. Preflight blocks the separate `scene_00.mp4` intro video and warns that Remotion motion-graphic overlay specs and glossary entries are not drawn. Plans without `render_settings` (older episodes) fall back to Remotion `VideoPodcast`; set `"renderer": "remotion"` to choose it explicitly.

Render preflight also warns when a video clip is shorter than its slot, when several `local_reframe` slots crop the same still, and when assets in `visual_timeline.json` are missing from the render props (repairs must be synced into `asset_manifest.json`). Inspection stills before consent: `python scripts/minimal_doc_stills.py --plan <plan> --times 3,66,570` (same timeline and path handling as the render).

## Composed score and explainer graphics

The global `background_bed_*` settings loop a file from `Songs/`. An episode can instead use its own bed, set in the plan (part of the render revision):

```json
"render_settings": {"renderer": "minimal_doc",
                    "background_bed": {"path": "score/score_bed.wav", "volume_db": -18.0, "stereo": true}}
```

The path is episode-relative and must exist. The bed goes through the same sidechain ducking chain; `stereo: true` keeps the whole mix (bed, SFX cues, final AAC) at 48 kHz stereo instead of the narration's mono 24 kHz. A procedural score is authored as `score/score_cues.json` (chords, per-section moods and events; see `src/producer_score.py`) and rendered with `python scripts/producer_score.py onsets --episode <dir>` then `render --episode <dir>`. Nobody hears the score inside the tool, so a person must listen before render consent.

Flat explainer graphics use `doc_renderer/gfx_kit/` (`kit.js` scene primitives and mascot, `template.html`, `record.cjs` recorder at the 25 fps minimal_doc rate). Designed SFX stems for them are built with `src/producer_sfx_synth.py` and added to `sfx_cues.json` at the slot start.

## Framing overrides

Optional per-episode framing overrides go in `minimal_render_overrides.json` next to the plan (also part of the revision). Keys are asset file names; `kind` (`cover`, `plate`, `figure`, `slide`), `anchor` `[x, y]` (0–1 zoom focus), `zoom` `[start, end]` (also for video clips; `[1, 1]` stops the default 3% push, e.g. for graphic runs cut into slot pieces), `min_zoom` (crops burned-in corner credits) and `caption_title` (display-only). `end_card.sources` / `end_card.note` replace the generated end card. `opening.seconds` marks an opening sting: scene 0's first slot (the sting clip) plays before the narration, and `scripts/producer_pad_breaths.py` prepends that much silence to scene 0's audio; no chapter card shows during the sting, chapter 1's card starts at that time, and it must be a shot boundary. The outro hold (`outro_hold_seconds`) is where the end card appears.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `PRODUCER_MINIMAL_WORKERS` | half the CPU cores, max 8 | Parallel headless Chrome workers |
| `PRODUCER_MINIMAL_CHROME` | Remotion's bundled chrome-headless-shell | Chrome executable override |

The ignored local files `config.json`, `client_secrets.json`, and `token.json` contain environment-specific values and must remain local.
