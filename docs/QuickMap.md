# Producer Mode QuickMap

## Supported path

1. Follow the installed `moneyprinter-producer-mode` skill and keep the selected episode revision explicit.
2. Create or resume a plan with `python scripts/producer_mode.py`.
3. Review the plan and production checkpoints with `python scripts/producer_review.py check --plan <plan>`.
4. Produce evidence-backed assets and Gemini narration through the Producer Mode stages.
5. Prepare a revision fingerprint with `python scripts/producer_review.py prepare --plan <plan>`.
6. Render only after the exact prepared revision has explicit user authorization.
7. Review the actual output and record final QC for the final file.

See [producer-mode-workflow.md](./producer-mode-workflow.md) for the local commands and artifacts.

## Main code paths

- `src/producer_mode.py`, `src/producer_contract.py`: planning and episode contract.
- `src/producer_script_writer.py`: script drafting helpers.
- `src/producer_asset_planner.py`, `src/producer_asset_producer.py`, `src/producer_broll_expander.py`: visual plans and media production.
- `src/producer_tts.py` and `src/classes/Tts.py`: Gemini TTS narration.
- `src/producer_renderer.py`, `src/producer_render_preflight.py`: revision-bound rendering (Remotion by default).
- `src/producer_minimal_renderer.py`, `doc_renderer/`: optional minimal documentary renderer (`render_settings.renderer = "minimal_doc"`).
- `src/producer_final_qc.py`, `src/producer_final_report.py`: technical QC and handoff reports.
- `src/llm_provider.py`: Claude/Anthropic explicit routing and MiniMax/OpenRouter default routing.
- `src/runtime_trace.py`: provider request traces and cost summaries.
- `remotion/src/VideoPodcast.tsx`: documentary composition.
- `remotion/src/ClipShort.tsx`: adjacent Shorts Pack composition.

There is no supported Studio server, automation dashboard, Podcast V1/V2 API, or scheduled generation flow.

## Episode artifacts

Working episodes are stored under `.mp/`. Common files include:

- `producer_plan.json`: episode scope, editorial decisions, evidence, and visual plan.
- `script.json`: narration and scene/beat content.
- `scene_*.wav`, asset files, and render props: prepared production inputs.
- `final.mp4`, QC reports, and handoff metadata: output and acceptance record.

Inspect the actual folder and plan before resuming; do not assume the newest episode is the intended revision.
