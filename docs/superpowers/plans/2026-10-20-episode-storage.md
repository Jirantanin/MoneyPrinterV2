# Episode Storage (Prune and Archive) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A user-invoked skill and CLI that classify `.mp/` episode folders, prune regenerable media from uploaded episodes, and archive them into small reference records, staging every removal in `.mp/_trash/` for นน to empty.

**Architecture:** One logic module `src/episode_storage.py` (classification, keep/remove rules, trash staging, archive builder, reference repointing) behind a thin argparse CLI `scripts/episode_storage.py`, mirroring `src/youtube_upload.py` / `scripts/youtube_upload.py`. Every destructive subcommand is a dry-run unless `--apply`. A repo skill tells Claude when and how to run it.

**Tech Stack:** Python 3.12 stdlib (`pathlib`, `shutil`, `fnmatch`, `subprocess`, `dataclasses`), ffmpeg/ffprobe on PATH, `unittest` tests in `tests/`.

**Spec:** `docs/superpowers/specs/2026-10-20-episode-storage-design.md`

## Global Constraints

- Nothing runs automatically; only นน's request starts prune/archive/remove.
- Claude never hard-deletes: removals are `shutil.move` into `.mp/_trash/<YYYYMMDD-HHMMSS>-<stage>-<episode>/`, preserving relative paths. นน empties `_trash/`.
- Never touch `.mp/fonts/`, `.mp/youtube.json`, `.mp/oauth_backups/`, any file directly under `.mp/`, `.mp/archive/`, `.mp/_trash/`.
- Proof of upload: receipt `upload_pack/youtube_upload_receipt.json` with a `video_id` and a `status` ending in `_verified`; or `upload_pack/manual_upload_confirmation.json`.
- Prune keeps `final.mp4`, `thumbnails/`, `upload_pack/`, `assets/`, `source_media/`, `curated_assets/`, `audio_raw/`, root `scene_NN.wav`, all text/code.
- Unmatched files over 50 MB are reported as "unclassified, kept", never removed.
- A folder referenced from a live reference doc may be archived but never removed entirely.
- Live reference docs: `completed_topics.md`, `doc_renderer/gfx_kit/LIBRARY.md`, `.claude/skills/moneyprinter-*/**/*.md`. Historical docs are not edited.
- CLI prints UTF-8 (reconfigure stdout/stderr like `scripts/youtube_upload.py`).
- Already verified while planning, no task needed: `claude-mods/mp-script/hooks/register.tsx:199` only lists `.mp/` folders matching `podcast_v2_*` / `producer_cut_*`, and `src/producer_mode.py` does not scan `.mp/`, so `archive/` and `_trash/` are never taken for episodes. `producer_breaths.py` rebuilds `scene_NN.wav` from `audio_raw/`; both are kept anyway.
- Tests never touch real `.mp/` data; they build synthetic folders in `tempfile.TemporaryDirectory()`.

## Review Focus

1. **Archive fails midway** (ffmpeg error, disk full, missing file) → the episode folder must still be in place and untouched; staging to trash is the last step. Test in Task 4.
2. **Archive run twice / archive dir already exists** → refuse before copying or moving anything. Test in Task 4.
3. **Receipt `thumbnail_path` points to a file that no longer exists** (absolute path from another machine, renamed thumbnail) → archive continues, SUMMARY notes "thumbnail missing". Test in Task 4.
4. **Episode argument as bare folder name, relative path, absolute path, or with trailing slash; or a name that does not exist** → resolves to the same folder; unknown name gives a clear error, not a traceback deep in a walk. Test in Task 5.
5. **Pruning an already-pruned episode** → reports 0 files and creates no empty trash folder. Test in Task 2.

---

### Task 1: Upload proof and folder classification

**Files:**
- Create: `src/episode_storage.py`
- Test: `tests/test_episode_storage.py`

**Interfaces:**
- Consumes: `youtube_upload.RECEIPT_NAME`, `youtube_upload.read_json`, `youtube_upload.write_json`, `youtube_upload.utc_now` (stdlib-only at import time).
- Produces:
  - constants `MP_ROOT = ROOT / ".mp"`, `ARCHIVE_DIR = "archive"`, `TRASH_DIR = "_trash"`, `CONFIRMATION_NAME = "manual_upload_confirmation.json"`, `SKIP_DIRS = {"fonts", "oauth_backups", "archive", "_trash"}`, `LARGE_BYTES = 50 * 1024 * 1024`
  - `class NotProven(ValueError)`
  - `upload_proof(episode: Path) -> dict | None` — returns `{"kind": "receipt", "url", "video_id", "published": publishAt or uploaded_at, "thumbnail_path"}`, or the confirmation dict (`kind` `"manual_upload"` or `"producer_decision"`), or `None`. Receipt wins over confirmation.
  - `group_key(name: str) -> str` — `name.split("_revision_")[0].split("_pilot_")[0]`
  - `completed_topic_names(topics_file: Path) -> set[str]` — folder names from `.mp/<name>` links
  - `@dataclass FolderStatus(name: str, path: Path, bucket: str, size_bytes: int, has_final: bool, proof_kind: str | None, last_modified: datetime)`
  - `classify(mp_root: Path, topics_file: Path, now: datetime) -> list[FolderStatus]`, sorted by name

Bucket rules, first match wins:
1. proof kind `receipt`/`manual_upload` → `"uploaded"`; `producer_decision` → `"decided"`
2. another folder in the same `group_key` is `uploaded` → `"undecided"` (superseded revision/pilot/base)
3. name contains `_pilot_`, starts with `voice_audition`, or size < 1 MB → `"undecided"`
4. name in `completed_topic_names` or `upload_pack/upload_pack_manifest.json` exists → `"probably_uploaded"`
5. newest file mtime within 7 days of `now` → `"in_progress"`, else `"undecided"`

- [ ] **Step 1: Write failing tests** (helper `_mp(self)` builds a temp `.mp/` with folders and files; `_receipt(ep, status, video_id="abc")` writes a receipt)
  - `test_receipt_with_verified_status_is_proof`: statuses `uploaded_verified`, `scheduled_verified`, `public_verified` → `upload_proof(ep)["kind"] == "receipt"`; `upload_interrupted` → `None`; `scheduled_verified` without `video_id` → `None`.
  - `test_confirmation_file_is_proof`: `manual_upload_confirmation.json` `{"kind": "manual_upload", "user_message": "ลงแล้ว"}` → kind `"manual_upload"`.
  - `test_classify_buckets`: folders `podcast_v2_a_20261001` (verified receipt) → `uploaded`; `podcast_v2_a_20261001_revision_x_01` (no proof) → `undecided`; `podcast_v2_b_20260601` (manifest only) → `probably_uploaded`; `podcast_v2_c_20260601` (in topics file only) → `probably_uploaded`; `voice_audition_20261010` → `undecided`; `podcast_v2_d_20261019` (2 MB, mtime = now − 1 day) → `in_progress`; `podcast_v2_e_20260101` (2 MB, mtime old) → `undecided`; `fonts`, `archive`, `_trash`, and file `youtube.json` absent from result.
- [ ] **Step 2: Run, expect FAIL** — `venv/Scripts/python.exe -m unittest discover -s tests -p "test_episode_storage.py" -v` → `ModuleNotFoundError: episode_storage`
- [ ] **Step 3: Implement** the Produces list in `src/episode_storage.py`. Module docstring states: user-directed only, removals are staged in `.mp/_trash/`, never hard-deleted.
- [ ] **Step 4: Run, expect PASS** (same command)
- [ ] **Step 5: Commit** — `git add src/episode_storage.py tests/test_episode_storage.py && git commit -m "Classify .mp episode folders by proof of upload"`

### Task 2: Prune plan and trash staging

**Files:**
- Modify: `src/episode_storage.py`
- Test: `tests/test_episode_storage.py`

**Interfaces:**
- Consumes: `upload_proof`, `NotProven`, `TRASH_DIR`, `LARGE_BYTES` (Task 1).
- Produces:
  - `matches(rel: str, patterns: tuple[str, ...]) -> bool` — `rel` is a posix relative path; true when `fnmatch(rel, p)` or `fnmatch(rel, "*/" + p)` for any `p` (so rules also apply inside `shorts_promo_gfx/` etc.).
  - `PRUNE_REMOVE = ("graphics/*.mp4", "minimal_render/*", "merged_audio*.wav", "score/*.wav", "sfx/*.wav", "audio_rejected/*", "final_rev_*.mp4", "final_video_only.mp4", "rejected/*", "rejected_renders/*", "review/*.mp4", "review/*.jpg", "review/*.png", "review/*.wav", "review/*.mp3", "duplicate_frame_audit_v*/*")`
  - `@dataclass StoragePlan(episode: Path, stage: str, remove: list[Path], unclassified: list[Path], remove_bytes: int)`
  - `prune_plan(episode: Path) -> StoragePlan` — `unclassified` = unmatched files > `LARGE_BYTES` whose name is not `final.mp4`.
  - `require_proof(episode: Path, action: str) -> dict` — returns the proof or raises `NotProven`. `producer_decision` counts only when its `decision == action`.
  - `stage_to_trash(episode: Path, paths: list[Path], stage: str, mp_root: Path, now: datetime) -> Path | None` — moves `paths` (files, or the episode folder itself) under `mp_root/_trash/<now:%Y%m%d-%H%M%S>-<stage>-<episode.name>/`, keeping paths relative to `episode` (the folder itself lands as the trash folder's content). Returns `None` and creates nothing when `paths` is empty.
  - `apply_prune(episode: Path, mp_root: Path, now: datetime) -> tuple[StoragePlan, Path | None]` — `require_proof(episode, "prune")`, then stage `plan.remove`.

- [ ] **Step 1: Write failing tests** (synthetic episode with: `final.mp4`, `graphics/glow/s1.mp4`, `graphics/glow/s1.js`, `graphics/paper/pieces/a.jpg`, `merged_audio_with_sfx.wav`, `score/bed.wav`, `score/cues.json`, `sfx/hit.wav`, `audio_raw/scene_00.wav`, `scene_00.wav`, `assets/x.jpg`, `review/frame.jpg`, `review/verdict.json`, `final_rev_2.mp4`, `rejected/old.mp4`, `shorts_promo_gfx/graphics/c.mp4`, `shorts_promo_gfx/final.mp4`, `expanded_broll/big.mp4` written with 51 MB via `f.truncate`)
  - `test_prune_plan_removes_only_regenerable`: removed set == {`graphics/glow/s1.mp4`, `merged_audio_with_sfx.wav`, `score/bed.wav`, `sfx/hit.wav`, `review/frame.jpg`, `final_rev_2.mp4`, `rejected/old.mp4`, `shorts_promo_gfx/graphics/c.mp4`}; `unclassified == [expanded_broll/big.mp4]`.
  - `test_apply_prune_requires_proof`: no receipt → `NotProven`; nothing moved.
  - `test_producer_decision_only_covers_its_action`: decision `"archive"` → `require_proof(ep, "prune")` raises; `require_proof(ep, "archive")` returns it.
  - `test_apply_prune_moves_into_trash_preserving_paths`: with receipt, after apply `trash/graphics/glow/s1.mp4` exists, `ep/graphics/glow/s1.js` and `ep/final.mp4` still exist, trash folder name matches `^\d{8}-\d{6}-prune-<name>$`.
  - `test_prune_twice_is_a_no_op` (Review Focus 5): second `apply_prune` returns `(plan with remove == [], None)` and `_trash/` has one folder only.
- [ ] **Step 2: Run, expect FAIL** (command from Task 1)
- [ ] **Step 3: Implement** the Produces list.
- [ ] **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** — `git commit -m "Prune regenerable episode media into a trash staging folder"`

### Task 3: Confirmations, references, and remove-entirely

**Files:**
- Modify: `src/episode_storage.py`
- Test: `tests/test_episode_storage.py`

**Interfaces:**
- Consumes: `require_proof`, `stage_to_trash`, `CONFIRMATION_NAME`, `write_json`, `utc_now`.
- Produces:
  - `confirm(episode: Path, user_message: str, url: str | None = None, decision: str | None = None) -> dict` — writes `upload_pack/manual_upload_confirmation.json` = `{"kind": "producer_decision" if decision else "manual_upload", "user_message", "url", "decision", "confirmed_at"}`. Refuses empty `user_message` (`ValueError`); `decision` must be one of `"keep"`, `"prune"`, `"archive"`, `"remove"`. Creates `upload_pack/` if missing.
  - `reference_files(repo_root: Path) -> list[Path]` — `completed_topics.md`, `doc_renderer/gfx_kit/LIBRARY.md`, and `repo_root.glob(".claude/skills/moneyprinter-*/**/*.md")`, existing files only.
  - `referenced_by(repo_root: Path, name: str) -> list[Path]` — reference files whose text contains `".mp/" + name`.
  - `apply_remove(episode: Path, mp_root: Path, repo_root: Path, now: datetime) -> Path` — requires `producer_decision` with `decision == "remove"`; raises `ValueError` naming the files when `referenced_by` is non-empty; stages the whole folder with stage `"remove"`.

- [ ] **Step 1: Write failing tests**
  - `test_confirm_writes_user_words`: `confirm(ep, "ตอนนี้ลงแล้ว", url="https://youtu.be/x")` → file has `kind == "manual_upload"`, the exact Thai message, url; `upload_proof(ep)["kind"] == "manual_upload"`.
  - `test_confirm_rejects_empty_message_and_unknown_decision`.
  - `test_remove_refuses_referenced_folder`: temp repo with `doc_renderer/gfx_kit/LIBRARY.md` containing `.mp/podcast_v2_h_1/graphics/v3/` and decision `remove` → `ValueError` mentioning `LIBRARY.md`; folder still exists.
  - `test_remove_stages_whole_folder`: unreferenced, decision `remove` → folder gone from `.mp/`, present under `_trash/*-remove-<name>/`.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** — `git commit -m "Record producer upload confirmations and guard folder removal"`

### Task 4: Archive builder

**Files:**
- Modify: `src/episode_storage.py`
- Test: `tests/test_episode_storage.py`

**Interfaces:**
- Consumes: `matches`, `require_proof`, `upload_proof`, `stage_to_trash`, `reference_files` (Tasks 1-3).
- Produces:
  - `ARCHIVE_KEEP = ("producer_plan.json", "script.json", "draft_v*.md", "research_dossier.md", "sequence_plan.md", "metadata.json", "cost_report.json", "final_qc.json", "review_check.json", "spoken_thai_review.json", "sequence_review.json", "review/*.json", "upload_pack/*.json", "upload_pack/*.txt", "upload_pack/*.md", "graphics/*.js", "graphics/*.json", "graphics/*.md")` — applied with `matches`, so Shorts subfolders are covered.
  - `video_duration(video: Path) -> float` — ffprobe `format=duration`.
  - `still_times(duration: float, chapters: list[dict]) -> list[tuple[str, float]]` — opening `(f"opening_{t:03d}s.jpg", t)` for `t` in `range(0, min(60, int(duration)), 3)`; then per chapter `i` (1-based, ordered by `start_seconds`) `(f"chapter_{i:02d}.jpg", (start + next_start_or_duration) / 2)`.
  - `extract_stills(video: Path, out_dir: Path, times: list[tuple[str, float]]) -> list[Path]` — one ffmpeg call per still: `-ss <t> -i <video> -frames:v 1 -vf scale=960:-2 -q:v 4`; raises `RuntimeError` on non-zero exit.
  - `write_summary(episode: Path, archive_dir: Path, proof: dict, stills: list[Path], notes: list[str]) -> Path` — `SUMMARY.md` with: title (`metadata.json` or `upload_pack/metadata.json`), URL, video id, published time, duration, cost (`cost_report.json` totals), renderer (`producer_plan.json.render_settings.renderer`) and graphics style (subfolder names of `graphics/`), chapters, section titles (`producer_plan.json.sections`), QC acceptance statuses (`final_qc.json.acceptance`), `notes`, and the list of kept files. Missing sources become "—".
  - `append_index(archive_root: Path, row: dict) -> Path` — `INDEX.md` with header `| Published | Title | Folder | YouTube | Style |` created on first use; one row appended per archive.
  - `repoint_references(repo_root: Path, name: str) -> list[Path]` — in `reference_files`, replace `".mp/" + name` with `".mp/archive/" + name`; returns changed files.
  - `@dataclass ArchiveResult(archive_dir: Path, trash_dir: Path, repointed: list[Path], notes: list[str])`
  - `archive_plan(episode: Path) -> tuple[list[Path], int]` — files to keep, total folder bytes (for the dry-run).
  - `apply_archive(episode: Path, mp_root: Path, repo_root: Path, now: datetime) -> ArchiveResult`

`apply_archive` order (staging is last, so any earlier failure leaves the episode untouched):
1. `require_proof(episode, "archive")`; refuse if `mp_root/archive/<name>` exists.
2. Copy keep files into `mp_root/archive/<name>/`, same relative paths.
3. Copy the thumbnail from `proof["thumbnail_path"]` (or its basename under `thumbnails/`) to `thumbnail<suffix>`; if missing, add note `"thumbnail missing"`.
4. If `final.mp4` exists: `extract_stills` into `stills/`; else note `"final.mp4 already gone, no stills"`.
5. `write_summary`, `append_index`.
6. `stage_to_trash(episode, [episode], "archive", ...)`.
7. `repoint_references`.

On an exception in steps 2-5, remove the partial `archive/<name>/` (`shutil.rmtree` on the folder this call created; it holds only copies) and re-raise.

- [ ] **Step 1: Write failing tests** (episode fixture from Task 2 plus `producer_plan.json` with `render_settings`, `sections`; `metadata.json` with two chapters; `cost_report.json`; receipt with `thumbnail_path` → `thumbnails/TH1.png`; `final.mp4` generated in `setUpClass` with `ffmpeg -f lavfi -i testsrc=size=160x90:rate=1 -t 70`; ffmpeg tests `@unittest.skipUnless(shutil.which("ffmpeg"), ...)`)
  - `test_still_times`: `still_times(70.0, [{"start_seconds": 0}, {"start_seconds": 40}])` → 20 opening entries starting `("opening_000s.jpg", 0)` ending `("opening_057s.jpg", 57)`, then `("chapter_01.jpg", 20.0)`, `("chapter_02.jpg", 55.0)`.
  - `test_archive_keeps_reference_files_and_stages_the_rest`: after `apply_archive`, archive has `producer_plan.json`, `graphics/glow/s1.js`, `review/verdict.json`, `thumbnail.png`, `SUMMARY.md`, `stills/opening_000s.jpg`, `stills/chapter_02.jpg`; archive has no `.mp4`/`.wav`; `.mp/<name>` is gone; `_trash/*-archive-<name>/final.mp4` exists; `INDEX.md` has one data row with the URL.
  - `test_archive_repoints_live_docs_only`: temp repo `LIBRARY.md` and `docs/postmortems/x.md` both mention `.mp/<name>/graphics/glow/s1.js`; only `LIBRARY.md` now reads `.mp/archive/<name>/graphics/glow/s1.js`.
  - `test_archive_refuses_existing_archive` (Review Focus 2): pre-create `archive/<name>/` → `ValueError`; episode untouched, nothing in `_trash/`.
  - `test_archive_failure_leaves_episode_intact` (Review Focus 1): patch `extract_stills` to raise `RuntimeError` → re-raised; `.mp/<name>/final.mp4` still exists; `archive/<name>/` does not exist; `_trash/` empty.
  - `test_missing_thumbnail_is_noted` (Review Focus 3): receipt `thumbnail_path` = `"D:\\elsewhere\\TH9.png"` → archive succeeds, `"thumbnail missing"` in `result.notes` and in `SUMMARY.md`.
  - `test_archive_without_final_skips_stills`: delete `final.mp4` first → no `stills/`, note present.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** — `git commit -m "Archive uploaded episodes into small reference records"`

### Task 5: CLI, trash helper, skill

**Files:**
- Create: `scripts/episode_storage.py`
- Create: `scripts/empty_episode_trash.bat`
- Create: `.claude/skills/moneyprinter-episode-archive/SKILL.md`, `.claude/skills/moneyprinter-episode-archive/INBOX.md`
- Modify: `CLAUDE.md` (Entry Points list: one line for `scripts/episode_storage.py` + `src/episode_storage.py` and the skill)
- Test: `tests/test_episode_storage.py`

**Interfaces:**
- Consumes: everything in Tasks 1-4.
- Produces:
  - `resolve_episode(value: str, mp_root: Path) -> Path` in `src/episode_storage.py` — accepts bare folder name, relative or absolute path, trailing slash; the result must be a direct child of `mp_root` not in `SKIP_DIRS`; otherwise `ValueError(f"no episode folder {value!r} under .mp/")`.
  - CLI: `python scripts/episode_storage.py <action> ...`, actions:
    - `status` → one JSON line per folder: `name, bucket, gb, has_final, proof, last_modified`; then a totals line per bucket.
    - `confirm --episode E --user-message "<words>" [--url U] [--decision keep|prune|archive|remove]`
    - `prune --episode E [E ...] [--apply]`
    - `archive --episode E [E ...] [--apply]`
    - `remove --episode E [--apply]`
    - Dry-run prints per episode: files to move, GB, unclassified list (prune), files kept (archive), and `DRY_RUN — rerun with --apply`. `--apply` prints the trash folder, GB staged, repointed files, and the line `Space is freed after emptying .mp/_trash (scripts/empty_episode_trash.bat).`
    - `NotProven` / `ValueError` → message on stderr, exit 2, continue to the next episode when several are given.
  - `empty_episode_trash.bat`: shows the size of `.mp\_trash`, asks `Y/N` with `choice`, then `rmdir /s /q .mp\_trash`. Run by นน only.
  - `SKILL.md` (frontmatter `name: moneyprinter-episode-archive`, description: use when นน asks to check storage, prune, archive, clean up or free disk space from `.mp/` episodes). Body covers:
    - Gates: only on นน's request; always dry-run first and show GB; `--apply` only after นน says go; never choose for `undecided` / `probably_uploaded` folders. Ask นน, then record the answer with `confirm` using นน's actual words.
    - First-time backfill: run `status`, list `probably_uploaded` for one confirmation, list `undecided` for per-folder decisions.
    - Claude never empties `_trash/` and never runs the `.bat`; it tells นน the GB waiting there.
    - Commands, run from the repo root with `venv/Scripts/python.exe` and `PYTHONIOENCODING=utf-8`.
    - When looking for a past episode as reference: open `.mp/archive/INDEX.md`, then the episode's `SUMMARY.md`.
  - `INBOX.md`: same header format as `.claude/skills/moneyprinter-youtube-upload/INBOX.md`, no entries.

- [ ] **Step 1: Write failing test** `test_resolve_episode_accepts_name_and_paths` (Review Focus 4): for folder `podcast_v2_a_1` under temp `.mp`, `"podcast_v2_a_1"`, `str(path)`, `str(path) + "/"`, and `".mp/podcast_v2_a_1"` (with cwd = temp root via `os.chdir` in `addCleanup`) all resolve to the same path; `"nope"` and `"fonts"` raise `ValueError` with `"no episode folder"`.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement `resolve_episode`, the CLI, the `.bat`, the skill files, the CLAUDE.md line.**
- [ ] **Step 4: Run, expect PASS** — full file: `venv/Scripts/python.exe -m unittest discover -s tests -p "test_episode_storage.py" -v`
- [ ] **Step 5: Smoke the CLI on a temp copy** — `venv/Scripts/python.exe scripts/episode_storage.py --help` lists the five actions.
- [ ] **Step 6: Commit** — `git add scripts/episode_storage.py scripts/empty_episode_trash.bat .claude/skills/moneyprinter-episode-archive CLAUDE.md src/episode_storage.py tests/test_episode_storage.py && git commit -m "Add episode storage CLI and archive skill"`

### Task 6: Read-only check against real `.mp/`

**Files:** none changed.

- [ ] **Step 1:** `PYTHONIOENCODING=utf-8 venv/Scripts/python.exe scripts/episode_storage.py status` → every folder from the spec's context appears; the 11 receipt folders are `uploaded`; the hand-uploaded June-September ones are `probably_uploaded`; `firstborn…_kurz-gfx_01`, the firstborn base, pilots and auditions are `undecided`.
- [ ] **Step 2:** `... prune --episode <each uploaded folder>` (dry-run only) → total GB to move is around 25 GB; list every `unclassified` file over 50 MB for นน.
- [ ] **Step 3:** `... archive --episode podcast_v2_musashi-legend-vs-record_20261016_230804` (dry-run only) → kept-file list contains `producer_plan.json`, `graphics/paper/*.js`, `upload_pack/youtube_upload_receipt.json`; no media.
- [ ] **Step 4:** Revision standalone check (spec: verify before a source folder is removed). For each `group_key` with more than one folder, search the revision folders' `*.json` for the base folder's name (`Grep`, read-only) and list any hits. A hit means that base must be archived, not removed.
- [ ] **Step 5:** Report the four outputs to นน. No `--apply` in this task; the first real prune or archive is นน's call through the skill.
- [ ] **Step 6:** Full test suite still passes: `venv/Scripts/python.exe -m unittest discover -s tests -v`.
