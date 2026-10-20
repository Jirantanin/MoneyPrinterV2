# Episode Storage: Prune and Archive Design

**Date:** 2026-10-20
**Status:** Draft, awaiting review
**Scope:** A user-invoked skill plus one CLI that frees disk space taken by finished episodes in `.mp/`, in two stages (prune, then archive), while keeping a small reference record Claude can read when making new episodes.

## Context

`C:` is the only drive: 900 GB used, 52 GB free (2026-10-20). `.mp/` holds 65 GB across 36 episode folders plus auditions, pilots and empty folders. Recent episodes take 3-6 GB each and are made almost daily, so the free space lasts two to three weeks.

The bulk is regenerable intermediate media, not the deliverable. In `podcast_v2_musashi-legend-vs-record_20261016_230804` (6.3 GB): `graphics/` 4.6 GB (131 per-scene mp4 clips + 441 frame jpgs), `final.mp4` 1.2 GB, `merged_audio_with_bed.wav` + `merged_audio_with_sfx.wav` + `score/*.wav` + `sfx/*.wav` ~450 MB, root `scene_NN.wav` ~28 MB. Across `.mp/`: non-final mp4 29.4 GB, all `final.mp4` 18.9 GB, all text/code files 0.14 GB.

The producer (นน) almost never reopens a published episode. Claude does, through pointers:
- `doc_renderer/gfx_kit/LIBRARY.md` points at scene code inside episode folders (lines ~52, 125, 150) as worked examples.
- `completed_topics.md` lists finished topics with a link to each episode folder, used to avoid repeating a topic.
- Claude reads plans, narration, research, review verdicts and scene code. It cannot watch mp4; it can read images.

`claude-mods/` tests mention real episode folder names but run against a virtual filesystem (`harness.ts` `put`/`deny ENOENT`), so they do not depend on the folders existing.

## Decisions made with the producer

- **"Done" = uploaded to YouTube.** Proof is `upload_pack/youtube_upload_receipt.json` with `status` in `uploaded_verified` / `scheduled_verified` (written by `src/youtube_upload.py`).
- **Nothing runs automatically.** นน invokes the skill; Claude runs the commands. Never prune or archive as a side effect of upload or render.
- **Two stages:**
  1. **Prune** (after upload, when นน asks): delete regenerable intermediates, keep `final.mp4`, thumbnails, upload pack, and everything not regenerable.
  2. **Archive** (later, when นน asks): reduce the episode to a small reference record and delete everything else, **including `final.mp4`**. นน accepted that YouTube then holds the only copy of the video.
- **The archive is for Claude, not for นน to browse.** So: text, json, scene code, and still images. No video clips.
- **Delivered as a skill** that นน calls and Claude runs.

## Goals

- Recover ~25 GB now via prune, and nearly all of an episode's size later via archive.
- Keep everything Claude uses as reference, at a stable path, findable from one index.
- Make every destructive step show a dry-run first (what, how many files, how many GB) and require นน's go-ahead.

## Non-goals

- YouTube Analytics (views, CTR, retention) in the archive. Most valuable for reference, but needs an extra OAuth scope. Later, separate work.
- Moving data to another drive or cloud storage.
- Changing how episodes are produced or rendered.

## Anti-goals (failure even if it "works")

- Deleting anything from an episode that is not proven uploaded.
- Deleting non-reproducible inputs during prune: TTS narration takes (Gemini gives a different take on re-synthesis) and downloaded source media in `assets/` (sources may disappear).
- Touching `.mp/fonts/`, `.mp/youtube.json`, `.mp/oauth_backups/`, or any file directly under `.mp/`.
- Breaking LIBRARY.md or completed_topics.md links.
- Claude hard-deleting files. Claude moves files into a trash staging folder; นน empties it (see Deletion mechanics).

## Stage 1: Prune

Precondition: proven uploaded (receipt, or manual-upload confirmation below).

Remove only what the pipeline can regenerate identically from files that stay:
- `graphics/**/*.mp4` and recorded frame images under `graphics/` (the `.js`/`.json`/`.md`/`.html` scene sources stay)
- `minimal_render/` contents
- `merged_audio*.wav`
- `score/*.wav` (cue sheets `score/*.json`/`*.txt` stay)
- `sfx/*.wav` (cue file `sfx_cues.json` stays)
- `audio_rejected/` (rejected takes)
- superseded renders: `final_rev_*.mp4`, `final_video_only.mp4` (the uploaded `final.mp4` stays) *(Claude's call)*
- `rejected/`, `rejected_renders/`, and media files (mp4/jpg/wav/mp3) inside `review/` (review json/txt/log stay) *(Claude's call)*
- `duplicate_frame_audit_v*/`
- older-layout derived b-roll: root `scene_NN_M.mp4` from `producer_broll_expander.py`, and `expanded_broll/` **if** the builder confirms they are derived from kept sources

Keep: `final.mp4`, `thumbnails/`, `upload_pack/`, `assets/`, `source_media/`, `curated_assets/` (downloaded originals), `audio_raw/`, root `scene_NN.wav`, all text/code/json/log/md/html.

Prune is a deny-list: only the categories above are removed. Any other file over 50 MB that fits no rule is listed in the dry-run as "unclassified, kept" so นน can see it; the rules get extended later rather than guessed at run time. *(Claude's call.)*

The rules apply recursively, including inside `shorts_promo_gfx/` (Shorts made from the episode). A Short's own receipt is not proof that the episode was uploaded.

Expected yield on today's data: roughly 25 GB from prune across uploaded episodes (the earlier 45 GB estimate assumed deleting narration and downloaded media too). Archive frees the rest.

**Builder must verify** which of `audio_raw/`, root `scene_NN.wav`, `audio_regen/` are the TTS originals versus derived from them, against `src/producer_*` and `tts_manifest.json`. Rule: TTS originals are kept; anything derived from them may be pruned. If unclear, keep.

## Stage 2: Archive

Precondition: proven uploaded. Archive works whether or not the episode was pruned first; if `final.mp4` is already gone, the still-image step is skipped and noted in the summary.

Output: `.mp/archive/<episode-folder-name>/`, then the original episode folder is removed (via trash staging).

Contents:
- **`SUMMARY.md`** — one page, assembled by the script from existing files, no LLM call: title, YouTube URL and video id, publish time, duration, cost (`cost_report.json`), art direction / renderer, voice, chapter list (from `metadata.json` chapters), section outline, review rejections and QC verdicts, and a list of the files kept.
- **Text records** (copied as-is when present): `producer_plan.json`, `script.json`, `draft_v*.md`, `research_dossier.md`, `sequence_plan.md`, `metadata.json`, `cost_report.json`, `final_qc.json`, `review_check.json`, `spoken_thai_review.json`, `sequence_review.json`, `review/*.json`, `upload_pack/*` text files (title, description, tags, timestamps, receipt, request).
- **Scene code**: `graphics/**/*.js`, `graphics/**/*.json`, `graphics/**/*.md`, preserving relative paths.
- **Shorts** (`shorts_promo_gfx/` and similar): their text, scene code, receipt and thumbnail, same rules as the episode; the Short's video and audio go.
- **Stills** (jpg, small, e.g. 960 px wide):
  - the thumbnail actually used (`thumbnail_path` in the receipt);
  - opening frames every ~3 s across the first 60 s of `final.mp4` (shows the hook → sting → greeting → roadmap rhythm);
  - one frame per chapter, at the chapter's midpoint (from `metadata.json` chapters).

Everything else goes, including `final.mp4`, all audio, `assets/`, per-episode `.py` scripts, logs other than those listed.

Expected size: 3-6 MB per episode.

### Archive index and pointers

- `.mp/archive/INDEX.md` — one row per archived episode: date, title, slug, YouTube URL, art direction, path. Claude opens this first when looking for a reference.
- When an episode is archived, repoint references to its old folder path in **live reference docs only**: `completed_topics.md`, `doc_renderer/gfx_kit/LIBRARY.md`, and `SKILL.md`/reference files of the MoneyPrinter skills (junction skills under `~/.codex/skills` included: the archive path is the same on disk for Codex, so the edit is correct for both). Report each changed file. *(Claude's call.)*
- Leave historical records alone: `docs/superpowers/specs|plans/`, `docs/postmortems/`, `.superpowers/` briefs, code docstrings, `claude-mods` test fixtures (virtual paths), generated `remotion/.render-props-*.json`.
- A folder referenced from a live reference doc may be archived but never removed entirely, so those links always resolve. *(Claude's call.)*
- Tools that list `.mp/` subfolders as episodes (e.g. `claude-mods/mp-script/hooks/register.tsx` ~line 201, any `producer_mode.py` episode discovery) must not treat `.mp/archive/` or `.mp/_trash/` as episodes. Builder checks and fixes.

## Status and one-time backfill

A `status` command classifies every `.mp/` subfolder:
- **uploaded** — receipt present with a video id and any `*_verified` status (`uploaded_verified`, `scheduled_verified`, and the hand-written `public_verified` seen on superhabitable-hunt);
- **probably uploaded** — no receipt, but listed in `completed_topics.md` **or** has `upload_pack/upload_pack_manifest.json` (episodes uploaded by hand before the uploader existed, June-September; e.g. 3i-atlas, mars-civilization base and two-jupiter-mass are listed but have no manifest);
- **not an episode / undecided** — pilots (`*_pilot_*`), voice auditions, empty or near-empty folders, unpublished revisions (e.g. `firstborn…_kurz-gfx_01` when `_02` was uploaded), samples never uploaded (Hatshepsut);
- **in progress** — everything else.

For "probably uploaded", นน confirms once (Claude asks with the list). Confirmation is recorded as `upload_pack/manual_upload_confirmation.json` holding นน's actual words, the YouTube URL if given, and a timestamp — same spirit as `user_message` in upload receipts. After that, the confirmation counts as proof.

For "not an episode / undecided", นน decides per folder: keep, prune, archive, or remove entirely. Claude never decides these. นน's explicit decision for a named folder replaces the proof-of-upload gate for that folder, and is recorded the same way (`manual_upload_confirmation.json` with `kind: "producer_decision"` and นน's words). "Remove entirely" moves the whole folder to `_trash/` with no archive record.

Revision groups (base + `_revision_*` folders): archive the uploaded one. Siblings that were never uploaded are listed for นน's decision. **Builder must verify** that revision folders are standalone copies and do not read files from their source folder at runtime before removing a source.

## Deletion mechanics

Claude does not hard-delete. Both stages **move** removed files into `.mp/_trash/<YYYYMMDD-HHMMSS>-<stage>-<episode>/`, preserving relative paths, and print the staged size. นน empties it, either in Explorer or with a `.bat` helper the skill points to (นน runs it, not Claude). The skill reminds นน that space is only freed after emptying `_trash/`.

Flow for each stage: dry-run (default) prints the file list summary and GB to be moved → นน says go → `--apply` moves → print freed-once-emptied total.

## Skill

`.claude/skills/moneyprinter-episode-archive/SKILL.md`, a real folder in the repo like `moneyprinter-youtube-upload` (not a junction to `~/.codex/skills`). *(Claude's call; matches the uploader skill, which is also repo-specific.)* Includes an `INBOX.md` per the user's skill convention.

The skill covers: when to use it (นน asks to prune, archive, clean up, or check storage), the gates (proof of upload, dry-run first, never pick undecided folders), the commands, and how to report results (GB freed after emptying trash, pointers repointed).

## CLI

`scripts/episode_storage.py` with logic in `src/episode_storage.py`, matching the `youtube_upload` split. Subcommands (names are the builder's to finalize): `status`, `confirm-upload --episode <dir> --user-message "<words>" [--url]`, `prune --episode <dir> [--apply]`, `archive --episode <dir> [--apply]`, `prune`/`archive` also accepting several episodes in one call. Python 3.12, existing dependencies; ffmpeg is already used by the renderer for frame extraction.

## Left to the builder

- Exact subcommand names and flags.
- Still-image width and jpg quality.
- `SUMMARY.md` layout, as long as it carries the fields listed.
- How to find the duration and art direction fields in `producer_plan.json` / `render_settings`.
- Tests: unit tests for classification and keep/remove rules on a synthetic episode folder; no tests that touch real `.mp/` data.
