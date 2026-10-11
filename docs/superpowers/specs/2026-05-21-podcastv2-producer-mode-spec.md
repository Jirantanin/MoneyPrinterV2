# PodcastV2 Producer Mode Spec

**Date:** 2026-05-21
**Status:** Draft, agreed direction, initial checkpoint implementation started
**Scope:** CLI-first producer workflow for full YouTube 16:9 PodcastV2 episodes

## Summary

Producer Mode is a CLI-first workflow where Codex acts as the end-to-end producer for a PodcastV2-style YouTube episode. The user only has to provide a topic. Codex researches the topic, selects the strongest clickable but factual angle, builds a checkpoint, waits for user approval, then produces the episode through the existing PodcastV2/Remotion pipeline.

This spec documents the agreed behavior only. It does not create a Codex skill, implement a runner, or replace the existing PodcastV2 flow yet.

## Operating Model

- Default output is a YouTube main episode in 16:9, rendered through the existing PodcastV2/Remotion composition.
- Narration language is Thai.
- The user can start with only a topic.
- If the topic is broad, Codex researches possible angles and chooses the one most likely to earn clicks without becoming misleading.
- Producer Mode must always research before writing the script.
- The first run stops at a read-only checkpoint.
- User approval can be given conversationally with "OK", "do it", "continue", or equivalent wording.
- After approval, Codex resumes the same episode folder and completes production unless a stop rule is hit.
- The workflow should be a resumable CLI flow with stage state, not a Studio UI feature at first.
- Reusable runners/tools may be kept permanently under `scripts/` or `src/` if they are useful beyond one session.

## Approval Checkpoint

Producer Mode creates:

- `producer_plan.json` as the canonical machine-readable plan.
- `checkpoint.html` as a read-only dashboard for the user.
- `docs/superpowers/specs/podcastv2-producer-mode-progress.html` as the stable implementation progress report for Codex-side development of this mode.

`checkpoint.html` is inspect-only. It does not need edit controls or an approval button.

The progress report is a single reused HTML file. Update it after every completed implementation phase instead of creating a new report path, so it can be tagged or bookmarked once.

The checkpoint must show:

- selected angle and rationale
- topic profile
- target audience
- viewer promise
- central question
- why the topic matters now or why viewers should care
- anti-clickbait boundary
- outline with 4-7 sections by default
- estimated Thai script length
- research summary
- source mapping per section
- competitor SEO/title/thumbnail pattern
- risk notes
- initial visual direction per section
- estimated cost/runtime
- QC checklist preview

If research finds that the topic is weak, risky, overdone, hard to source, or visually impractical within budget, Codex may propose a new angle in the checkpoint. A major topic pivot requires user approval.

## Script Contract

- Script length is counted as Thai characters without whitespace.
- Hard band: 5,000-12,000 chars without whitespace.
- Default target: 8,800-9,500 chars without whitespace.
- Narrative style is documentary storytelling: clear, calm, engaging, not stiff, not sensational.
- The story should feel continuous while still being structured into sections.
- Hook starts immediately, usually within the first 15-30 seconds.
- No long intro branding before the hook.
- End with a closing thought, then a light CTA.
- Default narrator is a single narrator.

Required script artifacts:

- `producer_plan.json`
- `script.json` converted for PodcastV2/Remotion
- `script_qc.json`
- `fact_check_report.json`
- `pronunciation_guide.md` or `pronunciation_guide.json`
- `script_revision_log.md` if script changes after the first accepted version

`producer_plan.json` is the source of truth during production. `script.json` is a render/output artifact that can be regenerated from the plan.

The first implementation writes one script scene per planned visual beat, preserving section indexes, source IDs, and asset-plan IDs so downstream TTS/asset generation can trace every scene back to the checkpoint. `draft-script --no-llm` is only a smoke-test path and intentionally marks the draft as blocked; production drafts require LLM generation.

## Research Rules

Research is mandatory on every run.

Minimum research:

- Use at least 3-5 credible sources.
- Browse the web for topic research and competitor/SEO research.
- For science, technology, or current topics, prefer current official sources, papers, universities, NASA/ESA/official agencies, and reputable publications.
- Do not write from memory alone.
- Store source metadata with title, publisher, date if available, URL, accessed date, short summary, and key claims.
- Keep a lightweight source pack. Do not scrape or store full web pages by default.
- Official media source pages and captions may be promoted into `research.sources` when they directly support a factual/visual beat.

Research output must include section-level citation mapping. A source list at the end is not enough.

If sources conflict:

- Prefer primary/official/paper sources.
- Use qualified wording when uncertainty remains.
- Remove or reframe unsupported major claims.
- Do not present contested claims as settled facts.

Sensitive topics such as health, finance, politics, crime, or disasters are allowed, but require stronger sources, explicit risk callouts, and careful wording. Avoid direct advice for health/finance.

## SEO And Packaging Research

Competitor research is mandatory before producing final metadata.

Default market lens:

- Global/English first.
- Thai if good enough results exist.

Competitor research should identify:

- title patterns
- thumbnail patterns
- repeated keywords
- common angles
- overused or misleading patterns to avoid

Do not copy competitors directly. Extract useful patterns only.

Final upload pack must include:

- 3 title options
- final recommended title and rationale
- description
- hashtags
- tags
- pinned comment
- thumbnail prompt/brief
- 3 thumbnail concepts

Title options should cover:

- curiosity/question angle
- concrete stakes angle
- documentary/trust angle

Thumbnail concepts should be Thai-first, with English only for necessary names or terms.

Thumbnail generation is not part of the default run. The default output is a prompt, layout brief, reference pattern, and avoid list.

## Visual Structure

Use sections and visual beats, not a fixed scene count.

Default sections:

- 4-7 sections, adjusted by topic and length.
- Every section must have an opener visual.
- Every visual beat should have a clear role such as `opener`, `explanation`, `evidence`, `contrast`, `scale`, `human_impact`, `transition`, or `diagram`.

Visual cadence:

- Default beat duration is 5-8 seconds.
- Codex may adjust based on narration rhythm.
- This will increase asset count, so budget and QC rules matter.

Section openers:

- Every section opener uses the Codex `imagegen` skill.
- No text should be embedded inside generated opener images.
- Use PodcastV2 title/chapter overlay for section text.
- Keep opener visual language consistent across the episode.
- Generate 2 variants by default, choose the best one, and retry once if both fail.

B-roll and other beat visuals:

- Prefer factual/subject match over style.
- Use color grade or render treatment to improve style consistency later.
- Avoid watermark, logos, brands, and distracting visible text.

Generated still images should receive light Remotion motion treatment such as slow zoom, pan, or parallax. Avoid overdone motion.

## Visual Source Order

Visual source order depends on the beat:

1. Section opener: Codex `imagegen`.
2. Factual or specific beat: official/verified real media first when available and license allows use.
3. Generic B-roll: stock video first through Pexels, then Pixabay.
4. Fallback or illustrative beats: Runware FLUX.1, Codex image generation, or Remotion graphics as appropriate.
5. Concept diagrams/charts: Remotion graphics when labels/data matter.

For space/science, first official provider targets are:

- NASA Image and Video Library
- NASA/JPL Photojournal
- NASA SVS

Later provider registry can include:

- ESA
- NOAA
- USGS
- Wikimedia Commons with clear license
- Library of Congress
- National Archives
- museum/library collections
- CDC/WHO/NIH for health
- Fed/World Bank/IMF for economics data

Official still images can beat stock video if they are more factual. Use careful layout and motion treatment instead of choosing a generic stock video.

If official media has mismatched aspect ratio or low resolution:

- use fit/crop carefully
- use a background or frame treatment
- never stretch the image
- never crop out context in a misleading way

Official videos may be excerpted. Store source URL and timecodes in the manifest. Mute source audio by default unless there is a specific reason to use it.

## Official Media Provider

Producer Mode has a first `official_media_provider` implementation that normalizes NASA Image and Video Library, NASA SVS, and best-effort NASA/JPL Photojournal candidates into the same kind of schema as stock providers.

Suggested schema:

```json
{
  "provider": "nasa_svs",
  "title": "Example title",
  "media_type": "image",
  "source_url": "https://example.com/source",
  "download_url": "https://example.com/file.jpg",
  "credit": "NASA",
  "license_note": "NASA media usage note or source-specific license note",
  "accessed_date": "2026-05-21",
  "relevance_score": 0.92,
  "risks": [],
  "selected_reason": "Directly shows the mission discussed in section 2"
}
```

Selection priority:

1. factual relevance to the beat
2. license/provenance clarity
3. visual clarity/resolution
4. recency for current topics
5. style fit

If a source caption contradicts the script, re-check the claim. The source/caption wins until proven otherwise. Do not use official media to support claims it does not actually depict.

## Licensing And Provenance

Every asset must be recorded in `asset_manifest.json`.

Required fields:

- provider
- source URL or provider asset ID
- download URL if available
- search query or prompt
- local path
- media type
- selected reason
- license/source note
- credit/attribution if required
- accessed date
- generated/illustrative flag when relevant
- timecode for video excerpts

Credits default to description, manifest, and `final_report.html`. Do not overlay credits on every shot unless the license requires visible attribution.

For NASA media:

- Use official/verified NASA sources when available.
- Store source page, credit, license/usage note, and accessed date.
- Skip media that is marked as third-party copyrighted unless permission/license is clear.
- Do not imply NASA endorsement.
- Be careful with NASA logos, insignia, identifiable people, and commercial/promotional usage.

## Visual No-Go List

These should fail QC, not merely warn:

- AI-generated likeness of a real person by default
- fake newspaper/document/screenshot that looks like evidence
- fake scientific graph or diagram without data source
- stock footage that makes viewers think it is footage of a real event when it is not
- watermark/logo/brand-distracting footage
- generated visuals presented as real evidence
- media whose caption/source contradicts the claim being made

Factual accuracy always beats beauty or drama.

## Diagrams, Charts, And Data Visuals

Use Remotion graphics for diagrams, labels, charts, and data visuals when text or numbers matter.

Represent these beats explicitly in `producer_plan.json`, for example:

```json
{
  "beat_type": "diagram",
  "visual_type": "remotion_graphic",
  "purpose": "Explain orbital distance scale",
  "labels": ["Earth", "Moon", "384,400 km"],
  "data_sources": ["https://example.com/source"]
}
```

If official data comes from a table, CSV, API, or report:

- store the subset/snapshot actually used
- store source URL and accessed date
- document transformation steps
- include the source in `fact_check_report.json`

## Asset QC

Asset QC must be written to `asset_qc.json`.

The first implementation writes planning-stage QC before downloads/generation. It checks provider choice, factual risk, provenance, repetition risk, and whether a beat needs manual review. Final asset QC must later add file-level checks after media is downloaded or generated.

A normal visual passes if at least 3 of these 4 are true:

- subject matches the beat
- mood/tone matches the story
- it can be used as B-roll without misleading viewers
- it is not obviously repetitive near adjacent beats

For specific factual objects, missions, people, places, charts, or diagrams, generic replacement is not enough. The visual must match the subject or the plan must explain why an illustrative substitute is acceptable.

If an asset fails QC:

- retry up to 2 times per scene/beat
- change provider, query, or prompt with a clear reason
- record retries and decisions
- warn only for minor mismatches that are not factual/audio/render/license problems

Fail conditions:

- factual risk
- missing section opener
- missing provenance/license data
- audio failure
- render failure
- misleading visual

## Audio And TTS

Default TTS style:

- Gemini TTS
- Thai
- single narrator
- Standard documentary / neutral documentary
- calm and clear, not trailer-like, not dark/dramatic by default

Required TTS artifacts:

- `tts_manifest.json`
- `pronunciation_guide.md` or `.json`
- `tts_qc.json`

TTS QC should check:

- all expected files exist
- duration is plausible
- no silent output
- audio level is not clipped or broken
- sample-listen hook, difficult names/terms, and ending when feasible

If names or scientific terms are likely to be misread, create pronunciation guidance before TTS.

If TTS misreads a term, fix the script or TTS prompt and regenerate only the affected segment where possible.

## Music And SFX

- Music is enabled and should follow existing PodcastV2 behavior.
- SFX is optional and experimental.
- Remove SFX if it clutters the episode or distracts from narration.
- Music/SFX from external sources must have provenance/license data in the manifest.
- Existing repo assets can be referenced by path/config.

## Rendering

Render with the existing Remotion/PodcastV2 composition.

Producer Mode prepares artifacts for the existing renderer instead of creating a new renderer first.

Default behavior:

- 16:9 main episode
- no subtitles by default
- no burn-in captions
- keep PodcastV2-style title/chapter overlay
- section chapters in metadata
- music behavior consistent with PodcastV2

Chapter timestamps must be based on real durations, not LLM guesses.

## Budget And Runtime

Cost behavior:

- warn when estimated provider cost exceeds USD 3 per episode
- stop and ask before continuing when cost reaches USD 5
- write `cost_report.json`
- write runtime/stage timings

If an API key is missing:

- use free/official web sources first when practical
- do not fake quality with weak sources silently
- checkpoint clearly if a missing key prevents acceptable quality

## Stop Rules

After checkpoint approval, Codex can continue without asking as long as it stays within the agreed rules.

Stop and ask if:

- estimated cost hits USD 5
- a major topic pivot is needed
- a major structure rewrite is needed after approval
- final QC finds misleading or high-risk factual issues
- required providers are down and the fallback would change the flow materially
- required licensing/provenance cannot be verified

## Final Output

Final output must include:

- `final.mp4`
- `producer_plan.json`
- `script.json`
- `sources` or research source pack
- `script_qc.json`
- `fact_check_report.json`
- `asset_manifest.json`
- `asset_qc.json`
- `tts_manifest.json`
- `tts_qc.json`
- `cost_report.json`
- `final_report.html`
- `upload_pack/`
- SEO metadata
- thumbnail brief with 3 concepts

`final_report.html` is read-only and should summarize:

- final video path
- duration/resolution/fps
- section outline
- asset provenance highlights
- QC warnings/failures
- cost/runtime
- SEO pack
- thumbnail concepts
- file list

## Final QC

Required final QC:

- `final.mp4` exists and opens
- resolution/fps/duration match PodcastV2 16:9 expectations
- audio is present and not obviously broken
- every section has an opener
- visuals are not misleading
- factual high-risk claims passed review
- upload pack exists
- SEO metadata exists
- asset provenance is complete
- cost/runtime report exists

If final QC finds a serious issue, fix and rerender within budget. Minor non-misleading mismatches may be shipped with explicit warnings in `final_report.html`.

## Episode Folder

Use the existing PodcastV2-style folder naming:

```text
.mp/podcast_v2_<slug>_<timestamp>
```

Keep intermediate files by default:

- downloaded stock media
- official media
- generated images
- scene clips
- audio files
- render props
- logs

Do not auto-delete production intermediates. A cleanup command can be designed later.

## Suggested CLI Shape

The current helper now uses this shape:

```powershell
python scripts/producer_mode.py init --topic "<topic>" --slug "<ascii-slug>"
python scripts/producer_mode.py research --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py plan-assets --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py draft-script --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py produce-assets --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py apply-asset-results --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json" --source-dir "<result-dir>"
python scripts/producer_mode.py produce-tts --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py render-preflight --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py render-video --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py final-qc --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py cost-report --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py final-report --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py upload-pack --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py smoke-gate --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py provider-smoke --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json" --allow-network --allow-gemini-tts
python scripts/producer_mode.py checkpoint --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py validate --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json"
python scripts/producer_mode.py schema
```

For a non-downloading smoke test:

```powershell
python scripts/producer_mode.py produce-assets --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json" --dry-run
python scripts/producer_mode.py produce-tts --plan ".mp/podcast_v2_<slug>_<timestamp>/producer_plan.json" --dry-run
```

The official media helper can also be smoke-tested directly:

```powershell
python src/official_media_provider.py "Mars rover" --limit 5
```

The CLI should:

- write `state.json`
- support resume
- support rerun of specific stages
- never restart from scratch unless explicitly asked
- keep all artifacts episode-local

Current implementation slice:

- `src/producer_mode.py` defines the lightweight schema, default plan, validation, and checkpoint HTML renderer.
- `scripts/producer_mode.py` is a wrapper CLI.
- The `research` command performs lightweight web research through keyless Bing HTML search, fetches short source-page summaries when possible, writes `research_brief.json`, updates `producer_plan.json`, and rerenders `checkpoint.html`.
- `src/official_media_provider.py` searches NASA Image and Video Library, NASA SVS, and best-effort NASA/JPL Photojournal candidates, writes normalized candidates into `research.official_media_results`, and can promote direct official captions/pages into `research.sources`.
- `src/producer_asset_planner.py` maps every visual beat to provider candidates, writes `visual_asset_plan.json`, writes planning-stage `asset_qc.json`, updates `producer_plan.json`, and rerenders `checkpoint.html`.
- `src/producer_script_writer.py` drafts render-compatible `script.json`, writes deterministic `script_qc.json`, writes `fact_check_report.json`, writes `pronunciation_guide.md`, updates `producer_plan.json`, and rerenders `checkpoint.html`.
- `src/producer_asset_producer.py` creates `asset_manifest.json`, writes production-stage `asset_qc.json`, writes `imagegen_tasks.json`, writes `remotion_graphic_tasks.json`, downloads official media under a size cap, applies local imagegen/remotion result files back into the manifest, and keeps stock/Runware behind explicit opt-in flags.
- `src/producer_tts.py` creates PodcastV2-compatible `scene_NN.wav` files through existing Gemini TTS behavior, writes `tts_manifest.json`, writes `tts_qc.json`, supports dry-run/sample limits, and updates the checkpoint through `produce-tts`.
- `src/producer_render_preflight.py` mirrors the PodcastV2/Remotion render contract without rendering, verifies `scene_NN.wav` plus `scene_NN_0.png/.mp4` readiness, writes `render_preflight.json`, writes `render_props_preview.json`, and updates the checkpoint through `render-preflight`.
- `src/producer_renderer.py` prepares episode-local render props, merges scene audio, applies the existing PodcastV2 background-bed behavior, writes `render_manifest.json`, writes `render_props.json`, and can invoke the existing Remotion `VideoPodcast` composition through `render-video`.
- `src/remotion_runtime.py` resolves a usable local Node/Remotion CLI path on Windows so render commands do not depend on a broken shell `node` or `npx` resolution.
- `src/producer_final_qc.py` inspects `final.mp4` with ffprobe, verifies duration, 1920x1080 resolution, 25fps video, audio stream presence, asset provenance, and TTS manifest presence, then writes `final_qc.json`.
- `src/producer_cost_report.py` reads local manifests only, writes `cost_report.json`, summarizes Gemini TTS estimates, Runware/asset cost assumptions, unknown-cost imagegen items, budget warning/stop status, and render/runtime duration.
- `src/producer_final_report.py` writes the read-only `final_report.html` handoff scaffold with final video path, QC status, cost/runtime, narration, visual asset provenance summary, SEO/title/thumbnail sections, warnings, errors, and artifact checklist.
- `src/producer_upload_pack.py` writes `upload_pack/` plus root `metadata.json` for uploader compatibility, including title options, description, tags, hashtags, pinned comment, thumbnail brief JSON/HTML, and an upload pack manifest.
- `src/producer_smoke_gate.py` writes `smoke_gate.json`, a read-only production readiness gate that combines research, script, assets, audio, render, handoff, budget, and provider readiness before a real provider/full-production run.
- `src/producer_provider_smoke.py` writes `provider_smoke/provider_smoke_manifest.json`, inspects provider key readiness without exposing secrets, creates a Codex imagegen task, records imagegen CLI fallback readiness, and can explicitly run live Pexels/Pixabay metadata checks plus a tiny Gemini TTS sample.
- If LLM synthesis is unavailable, `research` falls back to a conservative heuristic outline while preserving the collected source and competitor records.
- This slice can plan or produce Gemini TTS audio, preflight render readiness, orchestrate Remotion rendering, run final video QC, generate cost/final report artifacts, build upload-pack metadata, run a production smoke gate, and run controlled provider smoke checks. A short smoke render plus report/upload-pack/gate scaffold has passed; Pexels/Pixabay metadata, a tiny Gemini TTS live sample, and the imagegen CLI dry-run path have passed. Production-topic live rendering still requires real assets/audio and Codex imagegen fulfillment.

## Initial Implementation Order

1. Define `producer_plan.json` schema and checkpoint generator.
2. Implement research and SEO checkpoint stage.
3. Implement official media provider for NASA Image and Video Library, JPL Photojournal, and NASA SVS.
4. Implement visual planning and planning-stage asset QC.
5. Implement script drafting, source mapping, fact-check reports, and pronunciation guide.
6. Implement asset manifest production, official media downloads, and imagegen/remotion task handoff.
7. Wire Gemini TTS and TTS QC.
8. Wire actual Codex imagegen section opener fulfillment.
9. Wire Pexels/Pixabay/Runware fallback execution.
10. Implement render preflight and render props preparation.
11. Render through existing PodcastV2/Remotion.
12. Build `cost_report.json` and `final_report.html`.
13. Build upload pack metadata and handoff folder.
14. Run production smoke gate on a real topic before allowing full provider spend.
15. Run controlled provider smoke checks for stock providers, Gemini TTS, and Codex imagegen handoff.

## Out Of Scope For This Spec

- Creating a Codex skill.
- Adding Studio UI controls.
- Generating real thumbnails by default.
- Implementing every domain-specific media provider in the first version.
- Replacing the PodcastV2/Remotion renderer.
- Auto-deleting intermediate assets.
