# PodcastV2 Section + Visual Beats Roadmap

Date: 2026-05-12
Worktree: `C:\Users\66984\workspace-coding\MoneyPrinterV2-section-beats`
Branch: `codex/podcast-v2-section-beats`

## Goal

Move PodcastV2 manual script mode away from a hard `20 scenes` story contract and toward:

- deterministic story sections from the user's script structure
- variable-count visual beats for rendering and assets
- Thai-friendly length gates based on `chars_no_space`
- clear render/QC status so fallback output is not confused with a successful Remotion render

## Agreed Direction

- [x] Stop treating `20 scenes` as the script/story contract for manual script mode.
- [x] Use story sections as the narrative structure, usually 6-10 sections.
- [x] Split visual beats after the script exists, using code rather than asking the LLM to invent exactly 20 scenes.
- [x] Use Thai `chars_no_space` length gates instead of word count.
- [x] Keep B-roll in the pipeline.
- [ ] Route real media providers by subject type: NASA/real science media, Pexels, Pixabay, Wikimedia/Archive, then AI image for abstract concepts.
- [ ] Avoid generating a new AI image every 8 seconds by default; keep visual change every 7-10 seconds using images, B-roll, pan/zoom/crop shifts, or sub-shot cuts.
- [ ] Use reliable public-domain/licensed sources for real people; do not generate realistic likenesses of real people casually.

## Completed

- [x] Created the isolated worktree `MoneyPrinterV2-section-beats`.
- [x] Added manual-script length QC with:
  - minimum: `8000` chars without whitespace
  - ideal: `8800-9500`
  - soft max: `10000`
- [x] Added manual section parsing in `PodcastV2.generate_script_from_text()`.
- [x] Added deterministic visual beat splitting from parsed sections/paragraphs.
- [x] Preserved section metadata on generated visual beats:
  - `section_index`
  - `section_title`
  - `visual_beat_in_section`
  - `section_beat_count`
  - `chars_no_space`
- [x] Wrote `script_sections.json` for manual script runs.
- [x] Wrote `script_format_qc.json` and blocked manual script mode when clear `## SECTION NAME` headings are missing.
- [x] Updated script QC prompt/reporting so manual script mode no longer requires exactly 20 scenes.
- [x] Added asset completeness checks so resume does not skip partially generated scene assets.
- [x] Kept multi-asset Remotion props:
  - `sceneImageCounts`
  - `sceneAssetTypes`
  - `sceneAssetDurations`
- [x] Added `PODCAST_RENDER_IMAGE_ONLY` as an explicit render override for image-only debugging.
- [x] Increased Remotion render timeout path to support long-form attempts.
- [x] Fixed Studio/restart path issues for the worktree flow.
- [x] Verified the latest manual-script artifact produced `29` visual beats from `8404 chars_no_space`.
- [x] Verified assets/audio were generated for the latest run.
- [x] Fixed single-section chapter/title fallback so generic `Opening`/`Script` sections do not render as `Opening 1/29`, `Opening 2/29`, etc.

## In Progress

- [x] Validate full Remotion render with Node 22.
  - Current test episode: `.mp\podcast_v2_20260512_105053`
  - Current render target: `29` visual beats, about `1035.2s`
  - Node runtime observed after switch: `v22.22.2`
- [x] Confirm that the new `final.mp4` is a real Remotion output, not the PNG fallback.
- [ ] Confirm B-roll presence visually in the rendered output.

## Still To Do

- [ ] Capture Remotion stdout/stderr into an episode-local log file, for example `remotion_render.log`.
- [ ] Store render mode in state/QC, for example `remotion`, `fallback_image_concat`, or `failed`.
- [ ] Add a proper rerender path that intentionally backs up/removes `final.mp4` instead of silently skipping.
- [ ] Add post-render QC:
  - `final.mp4` exists
  - duration matches merged audio
  - scene count matches script/visual beats
  - asset count used by Remotion is reported
  - render mode is explicit
  - B-roll/video assets were included when expected
- [ ] Improve provider routing:
  - NASA / real science media for astronomy and science footage
  - Pexels for generic B-roll
  - Pixabay as secondary generic source
  - Wikimedia / Archive / Library of Congress / Smithsonian for real people and historical material when license is clear
  - AI image for abstract or unavailable concepts
- [ ] Add duplicate/repetition checks at the visual beat level.
- [ ] Add beat density checks so visual changes target roughly every 7-10 seconds without requiring a new generated image each time.
- [ ] Surface manual script format validation clearly in the Studio UI before generation, not only as a backend step error.
- [ ] Keep full-auto script generation untouched until the manual script lane is stable.

## Current Known Risk

- Remotion previously failed or timed out without useful episode-local logs.
- The last completed `final.mp4` before rerender was a fallback PNG + audio render, not a confirmed Remotion+B-roll render.
- Node 16 was incompatible with current Remotion dependencies; Node 22 is now the expected path for validation.
- Provider routing is not finished yet, so real-media/B-roll source selection can still be generic.

## Next Recommended Order

1. Finish the current Node 22 Remotion render test.
2. If it passes, inspect the final output and confirm B-roll is present.
3. Add Remotion log capture and explicit render-mode state.
4. Add proper rerender behavior.
5. Add post-render QC.
6. Then implement provider routing and beat-density tuning.
