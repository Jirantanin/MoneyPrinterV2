# mp-jobs: Live Job Pane Design

**Date:** 2026-10-13
**Status:** Draft, awaiting review
**Scope:** A Claude Code mod that shows live progress of long-running Producer Mode jobs (render, TTS, fetch, score) that Claude launches as background Bash commands. Read-only, no pipeline changes.

## Context

Long Producer Mode jobs run as background Bash commands that Claude starts during a session. While they run, the only way for the producer to see progress is to ask Claude or open log files by hand. The logs are scattered and inconsistent:

- `render-video` writes ffmpeg progress (`frame=N … elapsed=…`) into `<ep>/producer_render.log`, which is appended across every run (75 KB on the asteroid episode). The background task's own output only holds the final `[OK] wrote …` lines.
- `produce-tts` prints nothing until it finishes. Progress is only visible as `scene_NN.wav` files appearing.
- `scripts/producer_score.py render` prints `pad block b/nb` to stdout.
- The per-episode fetch scripts (`fetch_official.py`, `search_official.py`) print one line per asset and `429 on <url>… waiting Ns` when Wikimedia rate-limits, which looks identical to a hang unless you read the log.
- Claude often redirects output itself (`> fetch_run2.log 2>&1`), so log file names differ per episode.

Nothing on disk says which episode is "current", and the newest folder by mtime is not reliably the one being worked on (today it is `firstborn…kurz-gfx_02`, not asteroid).

**Goal:** a pane beside the conversation that answers "what is running right now, how far along is it, and is it stuck or just waiting", plus a status line and a toast on finish.

**Decided during brainstorming:**
- Claude launches nearly all of these jobs in the same session, so the mod tracks jobs by hooking Claude's own background Bash calls (approach A). A progress-file contract written by the pipeline (approach B) was rejected for now: it would need changes to 4-5 pipeline files, and it only pays off for jobs started outside the session.
- The mod never launches jobs itself, so the Producer Mode skill flow and render authorization stay untouched.

## Architecture

The mod is named `mp-jobs`. It is developed in this session's dev-mods folder for hot reload and then moved to `claude-mods/mp-jobs/` in this repo. It is loaded through `CLAUDE_CODE_PLUGIN_DIRS` in `~/.claude/settings.json`. It lives in the repo because its parsers depend on this repo's log formats, so a change to a log line and its parser show up in the same diff.

```
claude-mods/mp-jobs/
  .claude-plugin/plugin.json   name, version, description, "types": "./types/index.d.ts"
  hooks/hooks.json             { "modules": ["./register.tsx"] }
  hooks/register.tsx           wiring only: hooks, timer, rendering
  hooks/jobs.ts                pure: classify(), parsers, formatting. No `$`.
  hooks/jobs.test.ts           unit tests on real commands and log excerpts
  hooks/register.test.ts       engine tests via `claude plugin test`
  types/index.d.ts             PluginState contract: 'mp-jobs': { jobs: Job[] }
```

### Job record

```ts
type JobKind = 'render' | 'tts' | 'fetch' | 'score' | 'other'

type Job = {
  id: string                 // backgroundTaskId
  kind: JobKind
  label: string              // 'render', 'tts', … or the command's script name for 'other'
  command: string            // capped to 1000 chars
  episodeDir?: string        // absolute .mp/<ep> when the command names one
  logs: { path: string; offset: number; seenMtimeMs: number }[]  // offset in characters, see Error Handling
  ttsTotal?: number          // tts only: scenes this run will write, fixed at registration
  startedAt: number          // epoch ms
  status: 'running' | 'done' | 'failed'
  phase?: string             // render: 'audio' | 'frames' | 'mux' | 'finalize'
  progress?: { done: number; total?: number; unit: string; etaMs?: number }  // 'chunk', 'fr', 'ฉาก', 'block', 'รายการ'
  note?: string              // e.g. 'รอ rate limit 240s (429)'
  lastLine?: string
  lastWriteAt: number        // newest mtime seen across logs; drives the 'เงียบ' badge
  endedAt?: number
}
```

State lives in `$.state` (session scope), so a hot reload keeps it. Running jobs plus the 5 newest finished ones are kept and older finished jobs are dropped. Nothing goes in `$.store`, because a new session starts empty.

### Classification (`classify(command, cwd, taskOutputPath)`)

| kind | Command matches | Logs read | Progress source |
|---|---|---|---|
| render | `producer_mode.py render-video` without `--no-render` | `<ep>/producer_render.log`, plus the task output | The new region of the log is read in order as a small state machine. A `RUN … audio_concat`/`merged_audio` line → `audio`. `RUN … render.cjs` → `frames`. `frames N, chunks C, todo T, workers W` → `frames`, total T chunks, and N kept as the frame count. `chunk x done (k/T) Ss` → k/T chunks with ETA `S·(T−k)/k`. `video ready …` → `mux`. A `RUN … video.mp4` line → `mux`. After that, `frame=n … elapsed=h:mm:ss` → `finalize`, n/N frames, with ETA from `elapsed`. Phase must not rely on `RUN` lines alone: `producer_renderer._run_subprocess` writes its `RUN` header without a flush, so the header lands after that command's own output (the minimal renderer's `_run` flushes). `render_manifest.json` is not read. `node render.cjs` is the long step (the asteroid run logged `chunk 21 done (23/40) 407s`); the trailing `frame=` lines come from the ~27 s loudnorm copy. |
| tts | `producer_mode.py produce-tts` | `<ep>/` listing, plus the task output | Count of `scene_NN.wav` with mtime ≥ `startedAt` against a total fixed at registration. The total is the length of `<ep>/script.json` (a list of scenes), cut to `--limit` when given. Without `--force`, scenes whose wav already exists are subtracted, because `producer_tts.py:283` skips them. Do not use `producer_plan.json` `script_draft.scene_count`: it is `0` on the asteroid episode. |
| fetch | `fetch_official.py`, `search_official.py`, `producer_mode.py produce-assets` | redirect target or task output | Count of asset lines. A trailing `429 on … waiting Ns` sets `note` to `รอ rate limit Ns (429)`. A `download failed:` line is kept as `lastLine`. |
| score | `producer_score.py render` | redirect target or task output | `pad block b/nb` (split on `\r`). The lines `pad + drone`, `air / events` and `reverb` give the phase. |
| other | any other background Bash | redirect target or task output | No progress. Shows elapsed time and `lastLine`. |

- `<ep>` comes from `--plan <path>/producer_plan.json`, `--episode <path>`, or a `.mp/<ep>/…` script path in the command.
- When the command contains `> file`, `>> file` or `| tee file`, that file replaces the task output as the log.
- Relative paths resolve against the session cwd.

### Lifecycle

1. **Register.** `on('tool.call', { tool: 'Bash' })` awaits `next(e)` and returns that result unchanged. If the result carries `backgroundTaskId` (including commands backgrounded by Ctrl+B or by timeout), the hook does the following inside its own try:
   - classify the command
   - record each shared log's current text length as its `offset` (see Error Handling)
   - append the job
   - open the pane
   - start the timer if it is not already running
2. **Poll.** `$.clock.every(2000)` runs only while any job is running and is cancelled when none is. For each running job it stats each log. When a log's mtime changed, it reads the file. `$.fs.read` has no range read, so the whole file is read. It keeps the text after `offset`, capped to the last 256 K characters, splits on `\n` and `\r`, runs the kind's parser over that whole region, and writes the job back. One `update` call per tick covers all jobs.
3. **Finish.** `on('prompt.submit')` with `e.origin.kind === 'task-notification'` parses the task id and status out of `e.text`, marks the matching job `done` or `failed`, sets `endedAt`, and raises a toast:
   - `render เสร็จ · 4:12`
   - `tts พัง · <lastLine>`

   The hook always returns `next(e)` unchanged.
4. **Silence.** A running job whose `lastWriteAt` is more than 120 s old shows a yellow `เงียบ m:ss` badge. It is never auto-ended, because a fetch on 429 legitimately waits up to 240 s.
5. **Reload.** `session.start` (which fires again on hot reload) restarts the timer when the restored state has running jobs.

**Gate:** every hook returns `next(e)` untouched unless the session cwd resolves to a path under the MoneyPrinterV2 repo root. In KL sessions the mod does nothing.

## UI

### Pane (`$.ui.open({ id: 'mp-jobs', title: 'Jobs' })`)

```
asteroid-impact-plan
● render  ██████████░░░░░  62% frames · 25/40 chunk · ETA 4:10 · 7:02
● fetch   118 รายการ · ⏳ รอ rate limit 240s (429) · 2:03
◐ score   pad block 34/80 · 0:51
─ จบแล้ว ─
✓ tts     36/36 ฉาก · 3:55 · 14:02
✗ render  พัง · Error: ENOENT … · 13:40
```

- The header is the episode slug when every listed job shares one episode. Otherwise the slug moves to the end of each row.
- The progress bar appears only when `progress` exists. Otherwise the row shows phase or note, then elapsed time, with `lastLine` dimmed beneath.
- Widths follow `e.props.bodyColumns`, and long lines are truncated rather than wrapped.
- There are no buttons. The pane only displays.

### Opening

- The first registered job opens the pane on its own (unasked). An unasked pane waits undrawn below 144 columns. When `isPlaced` is false, one toast per session says `พิมพ์ /jobs เพื่อดู`.
- `/jobs` (registered in `session.start`) opens the pane as an asked open, so it is placed at any width.

### Status line

`$.ui.status('render 62% · ETA 0:41 +2')` shows the earliest-started running job, with `+N` when more are running. It is cleared when nothing runs. The status line is also the fallback if a surface does not draw the pane.

### Toast

Raised only on finish or failure. Native notifications (`$.ui.notify`) are not used, because they answer `no-surface` in a desktop-hosted session.

## Error Handling

- **Stale log content:** a shared, append-only log is read only from the offset recorded at registration, so an older run's `chunk 40 done (40/40)` cannot show 100 % at start. The shared logs are `<ep>/producer_render.log` and a `>>` or `tee -a` target. The offset is in characters, because reads are text. A `>` or `tee` target and the task output start fresh, so their offset is 0. A file shorter than its offset was truncated, and it is read from the start. TTS counts only wav files with mtime ≥ `startedAt`.
- **Never disturbs Claude's work:** the `tool.call` hook returns the result of `next(e)` whatever happens in bookkeeping, and the `prompt.submit` hook never rewrites the prompt.
- **Parser failure:** a parser that throws leaves that job with `lastLine` only, and the tick goes on for the other jobs. A missing log shows `ยังไม่มี log`, which is not an error.
- **Lost notification:** if a session dies mid-job, the silence badge is what remains visible. No job is auto-ended.
- **Cost:** each tick does a stat per log. A whole-file read happens only when that log's mtime changed (`producer_render.log` is 75 KB after many runs). TTS adds one directory listing. `script.json` is read once per TTS job.

## Testing

1. **Spike first.** This is throwaway and is deleted after. A bare mod that opens a pane, sets a status line, and logs the Bash `tool.call` result and the task-notification `prompt.submit` text. Claude runs a fake background job (a Python loop printing `frame=` lines with sleeps) to confirm three things:
   - whether this desktop Code tab draws the pane and the status line
   - whether the Bash result text names the task output file path
   - whether the notification text carries the task id and a parseable status or exit code

   If the pane is not drawn, design review resumes before building further.
2. **`jobs.test.ts`:** `classify()` against real commands:
   - `render-video` with and without `--no-render`
   - `produce-tts`
   - `fetch_official.py > fetch_run2.log 2>&1`
   - `producer_score.py render --episode …`

   Parsers against excerpts copied from the asteroid episode's logs:
   - `frames N, chunks …`, `chunk x done (k/T) Ss` and `video ready` lines
   - `frame=` lines after `video ready`, and a `RUN` header that arrives after its own output
   - `429 … waiting` lines
   - `pad block` with `\r`

   Plus a case where content before the offset must be ignored, and the TTS total with and without `--force` and `--limit`.
3. **`register.test.ts` (`claude plugin test`):**
   - a Bash `tool.call` answered with `backgroundTaskId` adds a running job
   - a task-notification `prompt.submit` marks it done and raises a toast
   - the pane mounts on both `terminal` and `desktop` surfaces and shows the job label
   - a cwd outside the repo registers nothing
4. `tsc -p claude-mods/mp-jobs` and `claude plugin validate claude-mods/mp-jobs` pass before the mod is called done.

## Out of Scope

- Jobs launched outside this session (terminal, Codex). Approach B can be revisited if that becomes common.
- Episode stage and checkpoint overview, upload calendar.
- Buttons (open log, kill job, clear).
- Remotion renderer progress parsing. The latest episodes use `minimal_doc`, so a Remotion render falls back to phase + `lastLine` until its log format is added.
