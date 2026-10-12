# mp-jobs Live Job Pane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Claude Code mod that shows live progress of the render, TTS, fetch and score jobs Claude starts as background Bash commands in the MoneyPrinterV2 repo. The progress appears in a pane, a status line and toasts.

**Architecture:** A function-hooks mod (`claude-mods/mp-jobs/`).
- It hooks `tool.call` for Bash to register jobs that return a `backgroundTaskId`.
- A `$.clock.every(2000)` ticker reads each job's logs and parses them.
- `prompt.submit` with origin `task-notification` marks jobs finished.
- All parsing and formatting lives in three pure files (`classify.ts`, `parse.ts`, `view.ts`) with unit tests. `register.tsx` is wiring only.

**Tech Stack:**
- Claude Code function hooks API 2.1.295 (`claude-code`, `claude-code/testing`)
- TypeScript 5.9 (`remotion/node_modules/.bin/tsc`)
- `claude plugin test`, `claude plugin validate`

**Spec:** `docs/superpowers/specs/2026-10-13-mp-jobs-pane-design.md`

## Global Constraints

- Mod name `mp-jobs`. Pane id `mp-jobs`, pane title `Jobs`. Slash command `/jobs`. State key `{ plugin: 'mp-jobs', key: 'jobs' }`.
- Final home is `claude-mods/mp-jobs/` in this repo. Throwaway spike lives in `C:\Users\66984\.claude\dev-mods\d640dbfd-eefc-43ab-b2cc-46b820d5b706\mp-jobs-spike\` and is deleted after Task 0.
- Gate: track nothing unless the cwd matches `/[\\/]MoneyPrinterV2(?:[\\/]|$)/i`.
- The mod never launches jobs and never changes a tool result or a prompt. `tool.call` returns what `next(e)` returned. `prompt.submit` returns `next(e)`.
- Poll period 2000 ms. Silence badge after 120 000 ms without a log write, suppressed while a `note` is set. Keep running jobs plus the 5 newest finished.
- Offsets are in characters. Only `<ep>/producer_render.log` and `>>`/`tee -a` targets are shared logs that get an offset. Everything else starts at 0. A file shorter than its offset is read from the start. The parsed region is capped to the last 262 144 characters.
- The TTS total comes from `<ep>/script.json` length, cut to `--limit`. Without `--force`, subtract the existing `scene_NN.wav` files whose index is below the total. Wav files are 0-based (`scene_00.wav`).
- Thai UI strings, verbatim:
  - `ยังไม่มีงานรัน`
  - `ยังไม่มี log`
  - `─ จบแล้ว ─`
  - `เงียบ m:ss`
  - `รอ rate limit Ns (429)`
  - `พัง`
  - `เสร็จ`
  - `ฉาก`
  - `รายการ`
  - `mp-jobs: พิมพ์ /jobs เพื่อดู`
- Colors are theme keys only: `success`, `error`, `warning`, `suggestion`.
- Commands, run from the repo root in Git Bash:
  - `claude plugin test claude-mods/mp-jobs`
  - `claude plugin validate claude-mods/mp-jobs`
  - `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`

## Review Focus

1. **A command that starts with `cd /c/Users/.../MoneyPrinterV2 && …`** (Git Bash path). Relative paths after it must resolve against that directory, converted to `C:/…`, not against the session cwd. Pinned in Task 1, test `cd prefix with a Git Bash path`.
2. **A shared log that was truncated or rotated since registration** (text shorter than the offset). It is read from the start instead of returning nothing. Pinned in Task 2, test `sliceNew reads a truncated file from the start`.
3. **A `RUN` header that lands after its own command's output** (`_run_subprocess` does not flush). It must not reset the render phase or progress. Pinned in Task 2, test `a late RUN header does not reset finalize`.
4. **A task notification for a task the mod never tracked** (a subagent, a foreground job), or several notifications in one prompt. Unknown ids are ignored with no toast, and every known id is finished. Pinned in Task 2 (`finishedTasks reads every block, failure by status or exit code`) and Task 4 (`foreground commands are not tracked and unknown notifications raise no toast`).
5. **Two jobs on different episodes at once.** Finishing one keeps the other ticking and in the status line, and the pane moves the episode name into each row. Pinned in Task 4 (`finishing one job keeps the other in the status line`) and Task 5 (`two episodes put the slug on each row`).

---

## File Structure

```
claude-mods/mp-jobs/
  .claude-plugin/plugin.json      manifest, names the types contract
  .claude-plugin/types/           engine-written API types (gitignored; Task 1 seeds it for tsc)
  hooks/hooks.json                { "modules": ["./register.tsx"] }
  hooks/register.tsx              wiring: hooks, ticker, pane drawing (Tasks 1, 4, 5)
  hooks/classify.ts               pure: command → kind, label, cwd, episode dir, redirect, log targets (Task 1)
  hooks/parse.ts                  pure: log text → phase/progress/note/lastLine, TTS counts, notifications (Task 2)
  hooks/view.ts                   pure: job list ops, merge, formatting, status text (Task 3)
  types/index.d.ts                Job types + PluginState contract (Task 1)
  test/classify.test.ts           (Task 1)
  test/parse.test.ts              (Task 2)
  test/view.test.ts               (Task 3)
  test/harness.ts                 engine fakes shared by the engine tests (Task 4)
  test/register.test.ts           (Task 4)
  test/pane.test.ts               (Task 5)
  tsconfig.json
.gitignore                        + claude-mods/*/.claude-plugin/types/
```

The spec names a single `hooks/jobs.ts`. This plan splits it into `classify.ts`, `parse.ts` and `view.ts`, so each pure file has one job and its own test file.

---

### Task 0: Spike: does this desktop session draw the pane, and what do Bash and notifications look like?

Throwaway. Nothing here is committed, and the folder is deleted at the end.

**Files:**
- Create: `C:\Users\66984\.claude\dev-mods\d640dbfd-eefc-43ab-b2cc-46b820d5b706\mp-jobs-spike\.claude-plugin\plugin.json`
- Create: `…\mp-jobs-spike\hooks\hooks.json`
- Create: `…\mp-jobs-spike\hooks\register.tsx`
- Modify: this plan, section "Spike findings" at the end

**Interfaces:**
- Consumes: nothing.
- Produces: the "Spike findings" section. Task 1 and Task 2 read it for the exact background-result text and notification text.

- [ ] **Step 1: Load the plugin-authoring skill** with the Skill tool, so the engine watches the dev-mods folder.

- [ ] **Step 2: Write the spike mod**

`plugin.json`:
```json
{ "name": "mp-jobs-spike", "version": "0.0.1", "description": "Throwaway probe for the mp-jobs design" }
```

`hooks.json`:
```json
{ "modules": ["./register.tsx"] }
```

`register.tsx`:
```tsx
import type { EngineInterface, Register } from 'claude-code'

// Outside the mod folder: a write inside the watched dev-mods folder would reload the mod on every line.
const LOG =
  'C:/Users/66984/AppData/Local/Temp/claude/C--Users-66984-workspace-coding-MoneyPrinterV2/d640dbfd-eefc-43ab-b2cc-46b820d5b706/scratchpad/mp-jobs-spike.log'

export const register: Register = on => {
  const entries: string[] = []
  const note = async ($: EngineInterface, line: string) => {
    entries.push(`${new Date(await $.clock.now()).toISOString()} ${line}`)
    await $.fs.write(LOG, `${entries.join('\n')}\n`)
  }

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'jobs-spike', description: 'Open the mp-jobs spike pane' })
    const opened = await $.ui.open({ id: 'spike', title: 'Spike' })
    $.ui.status('mp-jobs spike: status line works')
    await note($, `session.start surface=${e.surface} cwd=${e.cwd} unasked-open=${JSON.stringify(opened)}`)

    return next(e)
  })

  on('command.run', { command: 'jobs-spike' }, async $ => {
    const opened = await $.ui.open({ id: 'spike', title: 'Spike' })
    await note($, `asked-open=${JSON.stringify(opened)}`)

    return { text: `spike pane: ${JSON.stringify(opened)}` }
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    const isBackground =
      ran.deny === undefined && ran.isError !== true && ran.result.backgroundTaskId !== undefined
    if (isBackground) {
      await note($, `bash-bg result=${JSON.stringify(ran.result)} text=${JSON.stringify(ran.text)}`)
      let n = 0
      const timer = $.clock.every(1000, () => {
        n += 1
        $.ui.status(`spike tick ${n} (timer from tool.call $)`)
        if (n >= 5) timer.cancel()
      })
    }

    return ran
  })

  on('prompt.submit', async ($, e, next) => {
    const text = e.origin.kind === 'task-notification' ? e.text.slice(0, 2000) : '(not logged)'
    await note($, `prompt.submit origin=${JSON.stringify(e.origin)} text=${JSON.stringify(text)}`)

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: 'spike' }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    await note($, `render Pane surface=${e.surface} placement=${e.props.placement} cols=${e.props.bodyColumns}`)

    return (
      <Box flexDirection="column">
        <Text bold>mp-jobs spike</Text>
        <Text dimColor>{`surface ${e.surface}`}</Text>
      </Box>
    )
  })
}
```

- [ ] **Step 3: Validate, then end the turn**

Run: `claude plugin validate "C:/Users/66984/.claude/dev-mods/d640dbfd-eefc-43ab-b2cc-46b820d5b706/mp-jobs-spike"`
Expected: it lists hooks on `session.start`, `command.run`, `tool.call`, `prompt.submit`, `ui.render` with no refusals.

The first write raises "Enable hot reloading for this session?". Tell นน to choose **Enable for this session** and to look for a "Spike" pane and a status line `mp-jobs spike: status line works`. End the turn, because the mod loads when the turn ends.

- [ ] **Step 4: Read what loaded**

Read `…\scratchpad\mp-jobs-spike.log`. Ask นน whether they see the pane and the status line. If no pane is visible, ask them to type `/jobs-spike` and report what appears.

- [ ] **Step 5: Run a fake background job**

Run with the Bash tool and `run_in_background: true`:
```bash
python -c "import time
for i in range(5):
    print(f'frame={i}', flush=True); time.sleep(2)"
```
Wait for the task notification. Then read `mp-jobs-spike.log` again.

- [ ] **Step 6: Record findings** in "Spike findings" at the end of this plan, each as a fact with the quoted log line:
  - (a) Is the pane drawn unasked, asked, or not at all? Note `surface` and `placement`.
  - (b) Is the status line visible?
  - (c) The exact `bash-bg` `text`, and the keys of `result`.
  - (d) The exact notification `text`. Does `<task-id>` equal `backgroundTaskId`? What do `<status>` and the `exit code` wording look like?
  - (e) Did the spike tick status reach 5 (a timer started from a `tool.call` `$` outlives its dispatch)?

- [ ] **Step 7: Gate**

If neither the pane nor the status line draws, stop. Report to นน and resume design review. The options are a terminal `claude` session, or dropping the pane for toasts only.

If (c) differs from `Command running in background with ID: <id>. Output is being written to: <path>`, change the `TASK_TEXT` fixture in Task 1 Step 1 and the regex in Task 1 Step 3 to the recorded form.

If (d) differs from the `<task-notification>` / `<task-id>` / `<status>` / `<summary>` shape used in Task 2, change `NOTIFY` in Task 2 Step 1 and `finishedTasks` in Task 2 Step 3 to the recorded form.

- [ ] **Step 8: Delete the spike**

Run: `rm -rf "C:/Users/66984/.claude/dev-mods/d640dbfd-eefc-43ab-b2cc-46b820d5b706/mp-jobs-spike"`

---

### Task 1: Scaffold the mod and classify commands

**Files:**
- Create: `claude-mods/mp-jobs/.claude-plugin/plugin.json`
- Create: `claude-mods/mp-jobs/hooks/hooks.json`
- Create: `claude-mods/mp-jobs/hooks/register.tsx` (empty register for now)
- Create: `claude-mods/mp-jobs/types/index.d.ts`
- Create: `claude-mods/mp-jobs/tsconfig.json`
- Create: `claude-mods/mp-jobs/hooks/classify.ts`
- Test: `claude-mods/mp-jobs/test/classify.test.ts`
- Modify: `.gitignore` (append one line)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `types/index.d.ts`: `JobKind`, `JobStatus`, `LogRef`, `Progress`, `Job` (shapes below), and `PluginState['mp-jobs'] = { jobs: Job[] }`
  - `hooks/classify.ts`:
    - `hostPath(p: string): string`
    - `resolvePath(p: string, cwd: string): string`
    - `type Redirect = { path: string; appends: boolean }`
    - `type Classified = { kind: JobKind; label: string; cwd: string; episodeDir?: string; redirect?: Redirect; force: boolean; limit?: number }`
    - `classify(command: string, sessionCwd: string): Classified`
    - `taskOutputPath(resultText: string): string | undefined`
    - `type LogTarget = { path: string; isShared: boolean }`
    - `logTargets(c: Classified, taskOutput: string | undefined): LogTarget[]`

- [ ] **Step 1: Write the scaffold and the failing test**

`claude-mods/mp-jobs/.claude-plugin/plugin.json`:
```json
{
  "name": "mp-jobs",
  "version": "0.1.0",
  "description": "Live pane for MoneyPrinter render, TTS, fetch and score jobs Claude runs in the background",
  "types": "./types/index.d.ts"
}
```

`claude-mods/mp-jobs/hooks/hooks.json`:
```json
{ "modules": ["./register.tsx"] }
```

`claude-mods/mp-jobs/hooks/register.tsx`:
```tsx
import type { Register } from 'claude-code'

export const register: Register = () => {}
```

`claude-mods/mp-jobs/types/index.d.ts`:
```ts
export type JobKind = 'render' | 'tts' | 'fetch' | 'score' | 'other'

export type JobStatus = 'running' | 'done' | 'failed'

/** A log the ticker reads; `offset` in characters, `seenMtimeMs` the mtime last read. */
export type LogRef = { path: string; offset: number; seenMtimeMs: number }

/** `total` absent means a count with no end (fetch); `etaMs` only while estimable. */
export type Progress = { done: number; total?: number; unit: string; etaMs?: number }

export type Job = {
  id: string
  kind: JobKind
  label: string
  command: string
  episodeDir?: string
  logs: LogRef[]
  ttsTotal?: number
  startedAt: number
  status: JobStatus
  phase?: string
  progress?: Progress
  note?: string
  lastLine?: string
  lastWriteAt: number
  endedAt?: number
}

declare module 'claude-code' {
  interface PluginState {
    'mp-jobs': { jobs: Job[] }
  }
}
```

`claude-mods/mp-jobs/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "es2023", "lib": ["es2023"], "types": [],
    "module": "esnext", "moduleResolution": "bundler",
    "strict": true, "noUncheckedIndexedAccess": true,
    "noEmit": true, "skipLibCheck": true,
    "jsx": "react", "jsxFactory": "h", "jsxFragmentFactory": "Fragment"
  },
  "include": ["hooks", "test", "types", ".claude-plugin/types/claude-code/index.d.ts"]
}
```

Append to `.gitignore`:
```
claude-mods/*/.claude-plugin/types/
```

`claude-mods/mp-jobs/test/classify.test.ts`:
```ts
import { expect, test } from 'claude-code/testing'

import { classify, hostPath, logTargets, taskOutputPath } from '../hooks/classify'

const CWD = 'C:/Users/me/MoneyPrinterV2'
const EP_REL = '.mp/podcast_v2_asteroid-impact-plan_20261012_172530'
const EP = `${CWD}/${EP_REL}`
const TASK_TEXT =
  'Command running in background with ID: b1x. Output is being written to: C:\\Users\\me\\AppData\\Local\\Temp\\claude\\tasks\\b1x.output'

test('render-video is a render job on the plan episode', async () => {
  const c = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`, CWD)
  expect(c).toEqual({ kind: 'render', label: 'render', cwd: CWD, force: false, episodeDir: EP })
})

test('render-video --no-render is only preparation', async () => {
  const c = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json --no-render`, CWD)
  expect(c.kind).toBe('other')
  expect(c.label).toBe('render-video')
})

test('produce-tts keeps --force and --limit, and --dry-run is not tts', async () => {
  const c = classify(`python scripts/producer_mode.py produce-tts --plan ${EP_REL}/producer_plan.json --force --limit 5`, CWD)
  expect(c).toMatchObject({ kind: 'tts', force: true, limit: 5, episodeDir: EP })
  expect(classify(`python scripts/producer_mode.py produce-tts --plan ${EP_REL}/producer_plan.json --dry-run`, CWD).kind).toBe('other')
})

test('cd prefix with a Git Bash path', async () => {
  const c = classify(
    `cd /c/Users/me/MoneyPrinterV2 && python ${EP_REL}/fetch_official.py > ${EP_REL}/fetch_run2.log 2>&1`,
    'C:/elsewhere',
  )
  expect(c).toEqual({
    kind: 'fetch',
    label: 'fetch',
    cwd: CWD,
    force: false,
    episodeDir: EP,
    redirect: { path: `${EP}/fetch_run2.log`, appends: false },
  })
})

test('score render with tee -a appends to a shared log', async () => {
  const c = classify(`python scripts/producer_score.py render --episode ${EP_REL} | tee -a score.log`, CWD)
  expect(c).toMatchObject({ kind: 'score', label: 'score', episodeDir: EP, redirect: { path: `${CWD}/score.log`, appends: true } })
})

test('other job keeps the script name, Windows paths, and ignores /dev/null', async () => {
  const c = classify(
    'python scripts/build_timeline.py --plan "C:\\Users\\me\\MoneyPrinterV2\\.mp\\podcast_v2_x_20261012_172530\\producer_plan.json" > /dev/null',
    CWD,
  )
  expect(c).toEqual({
    kind: 'other',
    label: 'build_timeline.py',
    cwd: CWD,
    force: false,
    episodeDir: `${CWD}/.mp/podcast_v2_x_20261012_172530`,
  })
})

test('hostPath and taskOutputPath', async () => {
  expect(hostPath('/c/Users/me/a.log')).toBe('C:/Users/me/a.log')
  expect(hostPath('"C:\\x\\y.log"')).toBe('C:/x/y.log')
  expect(taskOutputPath(TASK_TEXT)).toBe('C:/Users/me/AppData/Local/Temp/claude/tasks/b1x.output')
  expect(taskOutputPath('ok')).toBeUndefined()
})

test('logTargets: render log is shared, task output and > targets start fresh', async () => {
  const render = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`, CWD)
  expect(logTargets(render, 'C:/t/b1x.output')).toEqual([
    { path: `${EP}/producer_render.log`, isShared: true },
    { path: 'C:/t/b1x.output', isShared: false },
  ])
  const fetch = classify(`python ${EP_REL}/fetch_official.py > ${EP_REL}/f.log 2>&1`, CWD)
  expect(logTargets(fetch, 'C:/t/b2.output')).toEqual([{ path: `${EP}/f.log`, isShared: false }])
  expect(logTargets(classify('sleep 5', CWD), undefined)).toEqual([])
})
```

- [ ] **Step 2: Seed the types for tsc and run the test to verify it fails**

Run:
```bash
mkdir -p claude-mods/mp-jobs/.claude-plugin/types/claude-code && cp "C:/Users/66984/AppData/Local/Temp/claude/bundled-skills/2.1.295/81b947ff1606222d6cef6a359f1f5d63/plugin-authoring/types/claude-code.d.ts" claude-mods/mp-jobs/.claude-plugin/types/claude-code/index.d.ts
```
If that folder is gone after a restart, load the plugin-authoring skill again and copy from the path it names.

Run: `claude plugin test claude-mods/mp-jobs`
Expected: FAIL, the import of `../hooks/classify` cannot be resolved.

- [ ] **Step 3: Write `hooks/classify.ts`**

```ts
import type { JobKind } from '../types'

export type Redirect = { path: string; appends: boolean }

export type Classified = {
  kind: JobKind
  label: string
  cwd: string
  episodeDir?: string
  redirect?: Redirect
  force: boolean
  limit?: number
}

export type LogTarget = { path: string; isShared: boolean }

const QUOTED = `"[^"]+"|'[^']+'`
const PRODUCER = /producer_mode\.py["']?\s+([\w-]+)/
const SCRIPT = /([\w.-]+\.(?:py|mjs|cjs|js|ps1))\b/

/** Git Bash `/c/Users/...` becomes `C:/Users/...`; quotes go; separators become `/`. */
export function hostPath(p: string): string {
  return p
    .replace(/^["']|["']$/g, '')
    .replace(/^\/([a-zA-Z])\//, (_m, drive: string) => `${drive.toUpperCase()}:/`)
    .replace(/\\/g, '/')
}

export function resolvePath(p: string, cwd: string): string {
  const host = hostPath(p)
  if (/^[A-Za-z]:\//.test(host) || host.startsWith('/')) return host

  return `${hostPath(cwd).replace(/\/+$/, '')}/${host.replace(/^\.\//, '')}`
}

function argValue(command: string, name: string): string | undefined {
  return command.match(new RegExp(`--${name}(?:\\s+|=)(${QUOTED}|[^\\s;&|]+)`))?.[1]
}

function parentDir(p: string): string {
  return p.replace(/\/[^/]*$/, '')
}

function episodeDirOf(command: string, cwd: string): string | undefined {
  const plan = argValue(command, 'plan')
  if (plan !== undefined) return parentDir(resolvePath(plan, cwd))
  const episode = argValue(command, 'episode')
  if (episode !== undefined) return resolvePath(episode, cwd).replace(/\/+$/, '')
  const script = command.match(/((?:[A-Za-z]:)?[^\s"']*\.mp[\\/][^\\/\s"']+)[\\/]/)?.[1]

  return script === undefined ? undefined : resolvePath(script, cwd)
}

function redirectOf(command: string, cwd: string): Redirect | undefined {
  const found: (Redirect & { at: number })[] = []
  for (const m of command.matchAll(new RegExp(`(?:^|[^0-9&>])(>>?)\\s*(${QUOTED}|[^\\s;&|<>]+)`, 'g'))) {
    found.push({ path: m[2]!, appends: m[1] === '>>', at: m.index ?? 0 })
  }
  for (const m of command.matchAll(new RegExp(`\\|\\s*tee\\s+(-a\\s+)?(${QUOTED}|[^\\s;&|<>]+)`, 'g'))) {
    found.push({ path: m[2]!, appends: m[1] !== undefined, at: m.index ?? 0 })
  }
  const last = found
    .filter(r => !/^(?:\/dev\/null|nul)$/i.test(r.path))
    .sort((a, b) => a.at - b.at)
    .at(-1)

  return last === undefined ? undefined : { path: resolvePath(last.path, cwd), appends: last.appends }
}

export function classify(rawCommand: string, sessionCwd: string): Classified {
  let command = rawCommand.trim()
  let cwd = hostPath(sessionCwd)
  const cd = command.match(new RegExp(`^cd\\s+(${QUOTED}|[^\\s;&|]+)\\s*(?:&&|;)\\s*`))
  if (cd) {
    cwd = resolvePath(cd[1]!, cwd)
    command = command.slice(cd[0].length)
  }
  const producer = command.match(PRODUCER)?.[1]
  const limit = argValue(command, 'limit')
  const episodeDir = episodeDirOf(command, cwd)
  const redirect = redirectOf(command, cwd)
  const kind: JobKind =
    producer === 'render-video' && !/--no-render\b/.test(command) ? 'render'
    : producer === 'produce-tts' && !/--dry-run\b/.test(command) ? 'tts'
    : producer === 'produce-assets' || /\b(?:fetch|search)_official\.py\b/.test(command) ? 'fetch'
    : /producer_score\.py["']?\s+render\b/.test(command) ? 'score'
    : 'other'
  const label =
    kind !== 'other' ? kind : (producer ?? command.match(SCRIPT)?.[1] ?? command.split(/\s+/)[0] ?? 'job').slice(0, 24)

  return {
    kind,
    label,
    cwd,
    force: /--force\b/.test(command),
    ...(limit !== undefined && /^\d+$/.test(limit) ? { limit: Number(limit) } : {}),
    ...(episodeDir !== undefined ? { episodeDir } : {}),
    ...(redirect !== undefined ? { redirect } : {}),
  }
}

/** The task's output file, from the text the model reads for a background Bash call. */
export function taskOutputPath(resultText: string): string | undefined {
  const path = resultText.match(/Output is being written to:?\s*(\S.*?)\s*$/m)?.[1]

  return path === undefined ? undefined : hostPath(path.replace(/\.$/, ''))
}

export function logTargets(c: Classified, taskOutput: string | undefined): LogTarget[] {
  const targets: LogTarget[] = []
  if (c.kind === 'render' && c.episodeDir !== undefined) {
    targets.push({ path: `${c.episodeDir}/producer_render.log`, isShared: true })
  }
  if (c.redirect !== undefined) targets.push({ path: c.redirect.path, isShared: c.redirect.appends })
  else if (taskOutput !== undefined) targets.push({ path: taskOutput, isShared: false })

  return targets.filter((t, i) => targets.findIndex(o => o.path === t.path) === i)
}
```

- [ ] **Step 4: Run tests, type-check, validate**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: PASS, 8 tests in `classify.test.ts`. If the runner cannot resolve the extensionless `../hooks/classify`, change every relative import in the mod to end in `.ts`/`.tsx` and add `"allowImportingTsExtensions": true` to `tsconfig.json`.

Run: `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: no output, exit 0.

Run: `claude plugin validate claude-mods/mp-jobs`
Expected: valid, with no hooks yet.

- [ ] **Step 5: Commit**

```bash
git add .gitignore claude-mods/mp-jobs
git commit -m "Scaffold the mp-jobs mod and classify background commands" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Parse logs, TTS counts and task notifications

**Files:**
- Create: `claude-mods/mp-jobs/hooks/parse.ts`
- Test: `claude-mods/mp-jobs/test/parse.test.ts`

**Interfaces:**
- Consumes: `JobKind`, `Progress` from `../types`; `FsEntry` from `claude-code`.
- Produces:
  - `type Parsed = { phase?: string; progress?: Progress; note?: string; lastLine?: string }` (no key is ever present with value `undefined`)
  - `sliceNew(text: string, offset: number): string`
  - `lines(text: string): string[]`
  - `lastLine(all: readonly string[]): string | undefined`
  - `parseRender(text: string): Parsed`
  - `parseFetch(text: string): Parsed`
  - `parseScore(text: string): Parsed`
  - `parse(kind: JobKind, text: string): Parsed`
  - `sceneCount(scriptJson: string): number`
  - `ttsTotal(scenes: number, entries: readonly FsEntry[], c: { force: boolean; limit?: number }): number`
  - `ttsDone(entries: readonly FsEntry[], startedAt: number): number`
  - `type Finished = { id: string; isFailed: boolean; summary?: string }`
  - `finishedTasks(text: string): Finished[]`

- [ ] **Step 1: Write the failing test**

The fixtures are lines copied from `.mp/podcast_v2_asteroid-impact-plan_20261012_172530/producer_render.log` and `fetch_run2.log`, with paths shortened.

`claude-mods/mp-jobs/test/parse.test.ts`:
```ts
import type { FsEntry } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import {
  finishedTasks, lastLine, lines, parse, parseFetch, parseRender, parseScore,
  sceneCount, sliceNew, ttsDone, ttsTotal,
} from '../hooks/parse'

const RENDER_OLD = 'chunk 38 done (40/40) 683s\nvideo ready C:\\x\\video.mp4 in 686s\n'
const RENDER_FRAMES = [
  '[2026-10-12T12:54:55+00:00] RUN ffmpeg -y -f concat -safe 0 -i C:\\x\\audio_concat.txt -c copy C:\\x\\merged_audio.wav',
  'RUN node C:\\x\\doc_renderer\\render.cjs --timeline C:\\x\\timeline.json',
  'frames 19946, chunks 40, todo 40, workers 8',
  '\x1b[1m\x1b[43m\x1b[30m',
  '  Puppeteer old Headless deprecation warning:\x1b[0m\x1b[33m',
  '    information, please see https://developer.chrome.com/articles/new-headless/.',
  'chunk 3 done (1/40) 123s',
  'chunk 21 done (23/40) 407s',
  '    If you encounter any bugs, please report them to https://github.com/puppeteer/puppeteer/issues/new/choose.\x1b[0m',
].join('\n')
const RENDER_MUX = `${RENDER_FRAMES}\nchunk 38 done (40/40) 683s\nvideo ready C:\\x\\video.mp4 in 686s\nRUN ffmpeg -y -v error -i C:\\x\\video.mp4 -i C:\\x\\merged_audio_with_sfx.wav C:\\x\\final_unnormalized.mp4`
const RENDER_FINALIZE =
  `${RENDER_MUX}\n` +
  'frame= 4367 fps=766 q=-1.0 size=  233472KiB time=00:02:48.68 bitrate=11338.5kbits/s speed=29.6x elapsed=0:00:05.70    \r' +
  'frame= 9973 fps=755 q=-1.0 size=  600000KiB time=00:06:39.00 bitrate=11338.5kbits/s speed=29.6x elapsed=0:00:13.00    '
const LATE_RUN = '\n[2026-10-12T13:07:01+00:00] RUN ffmpeg -y -i .mp\\x\\final_unnormalized.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 out.mp4'

const FETCH = [
  'nasa still GSFC_20240620_Asteroid_Threat_Briefing#frame1175 1920 1080',
  'nasa clip KSC-20211123-MH-AJW01-0001-SpaceX_DART_Isolated_Launch_Views_WON_3290675#t9 1280 720 30.0',
  'commons V01 C:Catalina Sky Survey Observatory at Dusk 1920 1280 CC BY-SA 4.0',
  'download failed: https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_source=commons.wikimedia.org',
  '  429 on https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_... waiting 60s',
  '  429 on https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_... waiting 240s',
].join('\n')

const NOTIFY = (id: string, status: string, summary: string) =>
  `<task-notification>\n<task-id>${id}</task-id>\n<tool-use-id>toolu_01</tool-use-id>\n` +
  `<output-file>C:\\t\\${id}.output</output-file>\n<status>${status}</status>\n<summary>${summary}</summary>\n</task-notification>`

const wav = (name: string, mtimeMs: number): FsEntry => ({ name, kind: 'file', size: 10, mtimeMs, isLink: false })

test('sliceNew keeps text after the offset and caps the region', async () => {
  expect(sliceNew('old\nnew', 4)).toBe('new')
  expect(sliceNew('x'.repeat(300_000), 0)).toHaveLength(262_144)
})

test('sliceNew reads a truncated file from the start', async () => {
  expect(sliceNew('short', 100)).toBe('short')
})

test('lines strips ANSI and splits on \\r; lastLine skips Puppeteer noise', async () => {
  const all = lines(RENDER_FRAMES)
  expect(all).toContain('frames 19946, chunks 40, todo 40, workers 8')
  expect(lastLine(all)).toBe('chunk 21 done (23/40) 407s')
})

test('render frames: chunks with ETA from the chunk seconds', async () => {
  expect(parseRender(RENDER_FRAMES)).toEqual({
    phase: 'frames',
    progress: { done: 23, total: 40, unit: 'chunk', etaMs: 300826 },
    lastLine: 'chunk 21 done (23/40) 407s',
  })
})

test('render audio, then mux after video ready', async () => {
  expect(parseRender(RENDER_FRAMES.split('\n')[0]!).phase).toBe('audio')
  const mux = parseRender(RENDER_MUX)
  expect(mux.phase).toBe('mux')
  expect(mux.progress).toBeUndefined()
})

test('render finalize counts frames against the frames header', async () => {
  expect(parseRender(RENDER_FINALIZE).progress).toEqual({ done: 9973, total: 19946, unit: 'fr', etaMs: 13000 })
})

test('a late RUN header does not reset finalize', async () => {
  const late = parseRender(RENDER_FINALIZE + LATE_RUN)
  expect(late.phase).toBe('finalize')
  expect(late.progress?.done).toBe(9973)
})

test('an older run before the offset cannot show as finished', async () => {
  const text = RENDER_OLD + RENDER_FRAMES.split('\n').slice(0, 3).join('\n')
  const parsed = parseRender(sliceNew(text, RENDER_OLD.length))
  expect(parsed.progress).toEqual({ done: 0, total: 40, unit: 'chunk' })
})

test('fetch counts assets and explains a trailing 429 wait', async () => {
  expect(parseFetch(FETCH)).toMatchObject({ progress: { done: 3, unit: 'รายการ' }, note: 'รอ rate limit 240s (429)' })
  const resumed = parseFetch(`${FETCH}\nnasa V24 iss040e091231 1920 1277`)
  expect(resumed.note).toBeUndefined()
  expect(resumed.progress?.done).toBe(4)
})

test('score: pad blocks, then later phases drop the bar', async () => {
  expect(parseScore('pad + drone\n\r  pad block 1/80\r  pad block 34/80')).toMatchObject({
    phase: 'pad',
    progress: { done: 34, total: 80, unit: 'block' },
  })
  const air = parseScore('pad + drone\n\r  pad block 80/80\nair / events')
  expect(air.phase).toBe('air')
  expect(air.progress).toBeUndefined()
})

test('parse for other kinds keeps only the last line', async () => {
  expect(parse('other', '[OK] wrote a\n[OK] wrote b\n')).toEqual({ lastLine: '[OK] wrote b' })
  expect(parse('tts', '')).toEqual({})
})

test('TTS totals and done counts', async () => {
  const existing = Array.from({ length: 10 }, (_, i) => wav(`scene_${String(i).padStart(2, '0')}.wav`, 500))
  expect(sceneCount('\uFEFF[{},{},{}]')).toBe(3)
  expect(sceneCount('not json')).toBe(0)
  expect(ttsTotal(36, existing, { force: false })).toBe(26)
  expect(ttsTotal(36, existing, { force: true })).toBe(36)
  expect(ttsTotal(36, existing, { force: false, limit: 12 })).toBe(2)
  expect(ttsDone([...existing, wav('scene_10.wav', 2000), wav('notes.txt', 2000)], 1000)).toBe(1)
})

test('finishedTasks reads every block, failure by status or exit code', async () => {
  const text = [
    NOTIFY('b1', 'completed', 'Background command "render" completed (exit code 0)'),
    NOTIFY('b2', 'failed', 'Background command "tts" failed with exit code 1'),
    NOTIFY('b3', 'completed', 'Background command "x" completed (exit code 2)'),
  ].join('\n')
  expect(finishedTasks(text)).toEqual([
    { id: 'b1', isFailed: false, summary: 'Background command "render" completed (exit code 0)' },
    { id: 'b2', isFailed: true, summary: 'Background command "tts" failed with exit code 1' },
    { id: 'b3', isFailed: true, summary: 'Background command "x" completed (exit code 2)' },
  ])
  expect(finishedTasks('hello')).toEqual([])
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: FAIL in `parse.test.ts`, `../hooks/parse` not found. `classify.test.ts` still passes.

- [ ] **Step 3: Write `hooks/parse.ts`**

```ts
import type { FsEntry } from 'claude-code'

import type { JobKind, Progress } from '../types'

export type Parsed = { phase?: string; progress?: Progress; note?: string; lastLine?: string }

export type Finished = { id: string; isFailed: boolean; summary?: string }

const MAX_REGION = 262_144
const ANSI = /\x1b\[[0-9;]*[A-Za-z]/g
const NOISE =
  /puppeteer|headless|developer\.chrome\.com|^(?:metadata|handler_name|vendor_id|encoder|compatible_brands|major_brand|minor_version|side data|icc profile)\b/i
const ASSET = /^[a-z]+ \S+ .+ \d{2,5} \d{2,5}\b/
const WAV = /^scene_(\d+)\.wav$/

function compact(p: Parsed): Parsed {
  return Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined)) as Parsed
}

function eta(elapsedMs: number, done: number, total: number): number | undefined {
  return done > 0 ? Math.round((elapsedMs * (total - done)) / done) : undefined
}

function withEta(p: Progress, etaMs: number | undefined): Progress {
  return etaMs === undefined ? p : { ...p, etaMs }
}

/** The text written since `offset`; a file shorter than its offset was truncated, so all of it. */
export function sliceNew(text: string, offset: number): string {
  const fresh = text.length < offset ? text : text.slice(offset)

  return fresh.length > MAX_REGION ? fresh.slice(-MAX_REGION) : fresh
}

export function lines(text: string): string[] {
  return text
    .replace(ANSI, '')
    .split(/\r\n|\r|\n/)
    .map(l => l.trimEnd())
    .filter(l => l.trim() !== '')
}

export function lastLine(all: readonly string[]): string | undefined {
  for (let i = all.length - 1; i >= 0; i -= 1) {
    const line = all[i]!.trim()
    if (!NOISE.test(line)) return line.length > 200 ? `${line.slice(0, 199)}…` : line
  }

  return undefined
}

/**
 * Reads producer_render.log in order. Phase never relies on RUN lines alone:
 * producer_renderer._run_subprocess writes its RUN header after the command's own output.
 */
export function parseRender(text: string): Parsed {
  const all = lines(text)
  let phase: string | undefined
  let progress: Progress | undefined
  let frames = 0
  for (const line of all) {
    let m: RegExpMatchArray | null
    if (/\bRUN\b.*render\.cjs/.test(line)) {
      phase = 'frames'
      progress = undefined
    } else if ((m = line.match(/^frames (\d+), chunks \d+, todo (\d+)/))) {
      frames = Number(m[1])
      phase = 'frames'
      progress = { done: 0, total: Number(m[2]), unit: 'chunk' }
    } else if ((m = line.match(/^chunk \d+ done \((\d+)\/(\d+)\) (\d+)s/))) {
      const done = Number(m[1])
      const total = Number(m[2])
      phase = 'frames'
      progress = withEta({ done, total, unit: 'chunk' }, eta(Number(m[3]) * 1000, done, total))
    } else if (/^video ready /.test(line) || /\bRUN\b.*video\.mp4/.test(line)) {
      phase = 'mux'
      progress = undefined
    } else if ((m = line.match(/^frame=\s*(\d+).*elapsed=(\d+):(\d+):(\d+(?:\.\d+)?)/))) {
      const done = Number(m[1])
      const elapsedMs = (Number(m[2]) * 3600 + Number(m[3]) * 60 + Number(m[4])) * 1000
      phase = 'finalize'
      progress =
        frames > 0 ? withEta({ done, total: frames, unit: 'fr' }, eta(elapsedMs, done, frames)) : { done, unit: 'fr' }
    } else if (/\bRUN\b.*(?:audio_concat|merged_audio)/.test(line)) {
      phase = 'audio'
      progress = undefined
    }
  }

  return compact({ phase, progress, lastLine: lastLine(all) })
}

export function parseFetch(text: string): Parsed {
  const all = lines(text)
  const count = all.filter(l => ASSET.test(l)).length
  const wait = all.at(-1)?.match(/429 on .*waiting (\d+)s/)

  return compact({
    progress: count > 0 ? { done: count, unit: 'รายการ' } : undefined,
    note: wait ? `รอ rate limit ${wait[1]}s (429)` : undefined,
    lastLine: lastLine(all),
  })
}

export function parseScore(text: string): Parsed {
  const all = lines(text)
  let phase: string | undefined
  let progress: Progress | undefined
  for (const line of all) {
    const t = line.trim()
    const block = t.match(/^pad block (\d+)\/(\d+)$/)
    if (t === 'pad + drone') {
      phase = 'pad'
      progress = undefined
    } else if (block) {
      phase = 'pad'
      progress = { done: Number(block[1]), total: Number(block[2]), unit: 'block' }
    } else if (t === 'air / events') {
      phase = 'air'
      progress = undefined
    } else if (t === 'reverb') {
      phase = 'reverb'
      progress = undefined
    }
  }

  return compact({ phase, progress, lastLine: lastLine(all) })
}

export function parse(kind: JobKind, text: string): Parsed {
  if (kind === 'render') return parseRender(text)
  if (kind === 'fetch') return parseFetch(text)
  if (kind === 'score') return parseScore(text)

  return compact({ lastLine: lastLine(lines(text)) })
}

export function sceneCount(scriptJson: string): number {
  try {
    const parsed: unknown = JSON.parse(scriptJson.replace(/^\uFEFF/, ''))

    return Array.isArray(parsed) ? parsed.length : 0
  } catch {
    return 0
  }
}

/** Scenes this run writes: producer_tts.py skips an existing wav unless --force. */
export function ttsTotal(scenes: number, entries: readonly FsEntry[], c: { force: boolean; limit?: number }): number {
  const n = c.limit === undefined ? scenes : Math.min(c.limit, scenes)
  if (c.force) return n
  const existing = entries.filter(f => {
    const m = f.name.match(WAV)

    return m !== null && Number(m[1]) < n
  }).length

  return Math.max(0, n - existing)
}

export function ttsDone(entries: readonly FsEntry[], startedAt: number): number {
  return entries.filter(f => WAV.test(f.name) && f.mtimeMs >= startedAt).length
}

export function finishedTasks(text: string): Finished[] {
  const found: Finished[] = []
  for (const block of text.matchAll(/<task-notification>([\s\S]*?)<\/task-notification>/g)) {
    const body = block[1]!
    const id = body.match(/<task-id>\s*([^<\s]+)\s*<\/task-id>/)?.[1]
    const status = body.match(/<status>\s*([^<\s]+)\s*<\/status>/)?.[1]
    if (id === undefined || status === undefined) continue
    const summary = body.match(/<summary>([\s\S]*?)<\/summary>/)?.[1]?.trim()
    const code = summary?.match(/exit code (\d+)/)?.[1]
    const isFailed = status !== 'completed' || (code !== undefined && code !== '0')
    found.push(summary === undefined ? { id, isFailed } : { id, isFailed, summary })
  }

  return found
}
```

- [ ] **Step 4: Run tests and type-check**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: PASS, 8 tests in `classify.test.ts` and 13 in `parse.test.ts`.

Run: `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add claude-mods/mp-jobs/hooks/parse.ts claude-mods/mp-jobs/test/parse.test.ts
git commit -m "Parse render, fetch, score and TTS progress for mp-jobs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Job list operations and formatting

**Files:**
- Create: `claude-mods/mp-jobs/hooks/view.ts`
- Test: `claude-mods/mp-jobs/test/view.test.ts`

**Interfaces:**
- Consumes: `Job`, `LogRef`, `Progress` from `../types`; `parse`, `lines`, `lastLine` from `./parse`.
- Produces:
  - `SILENCE_MS = 120_000`
  - `KEEP_FINISHED = 5`
  - `keep(list: readonly Job[]): Job[]`
  - `finish(list: readonly Job[], f: { id: string; isFailed: boolean }, now: number): Job[]`
  - `type Refreshed = { logs: LogRef[]; lastWriteAt: number; primary?: string; secondary?: string; ttsDone?: number }`
  - `mergeJob(job: Job, r: Refreshed): Job`
  - `clock(ms: number): string`
  - `percent(p: Progress): number | undefined`
  - `bar(p: Progress, width: number): string`
  - `silentFor(job: Job, now: number): number | undefined`
  - `detail(job: Job, now: number): string`
  - `statusText(jobs: readonly Job[], now: number): string | undefined`
  - `episodeSlug(dir: string): string`

- [ ] **Step 1: Write the failing test**

`claude-mods/mp-jobs/test/view.test.ts`:
```ts
import { expect, test } from 'claude-code/testing'

import type { Job } from '../types'
import {
  bar, clock, detail, episodeSlug, finish, keep, mergeJob, percent, silentFor, statusText,
} from '../hooks/view'

const job = (over: Partial<Job>): Job => ({
  id: 'b1',
  kind: 'render',
  label: 'render',
  command: 'python scripts/producer_mode.py render-video',
  logs: [],
  startedAt: 0,
  status: 'running',
  lastWriteAt: 0,
  ...over,
})

test('clock formats m:ss and h:mm:ss', async () => {
  expect(clock(0)).toBe('0:00')
  expect(clock(65_000)).toBe('1:05')
  expect(clock(3_725_000)).toBe('1:02:05')
})

test('percent and bar', async () => {
  expect(percent({ done: 25, total: 40, unit: 'chunk' })).toBe(62)
  expect(percent({ done: 118, unit: 'รายการ' })).toBeUndefined()
  expect(bar({ done: 25, total: 40, unit: 'chunk' }, 8)).toBe('█████░░░')
})

test('detail for running, counting, finished and failed jobs', async () => {
  expect(
    detail(job({ phase: 'frames', progress: { done: 25, total: 40, unit: 'chunk', etaMs: 250_000 } }), 422_000),
  ).toBe('frames · 25/40 chunk · ETA 4:10 · 7:02')
  expect(
    detail(job({ kind: 'fetch', label: 'fetch', progress: { done: 118, unit: 'รายการ' }, note: 'รอ rate limit 240s (429)' }), 123_000),
  ).toBe('118 รายการ · ⏳ รอ rate limit 240s (429) · 2:03')
  expect(
    detail(job({ status: 'done', endedAt: 235_000, progress: { done: 36, total: 36, unit: 'ฉาก', etaMs: 5 } }), 999_000),
  ).toBe('36/36 ฉาก · 3:55')
  expect(detail(job({ status: 'failed', phase: 'frames', endedAt: 60_000 }), 999_000)).toBe('frames · พัง · 1:00')
  expect(detail(job({ phase: 'finalize', progress: { done: 12_410, total: 19_946, unit: 'fr' } }), 1_000)).toBe(
    'finalize · 12,410/19,946 fr · 0:01',
  )
})

test('silentFor only for running jobs without a note', async () => {
  expect(silentFor(job({ lastWriteAt: 0 }), 130_000)).toBe(130_000)
  expect(silentFor(job({ lastWriteAt: 0 }), 100_000)).toBeUndefined()
  expect(silentFor(job({ lastWriteAt: 0, note: 'รอ rate limit 240s (429)' }), 200_000)).toBeUndefined()
  expect(silentFor(job({ lastWriteAt: 0, status: 'done', endedAt: 1 }), 200_000)).toBeUndefined()
})

test('statusText shows the earliest running job and how many more', async () => {
  expect(statusText([], 0)).toBeUndefined()
  expect(statusText([job({ progress: { done: 10, total: 40, unit: 'chunk', etaMs: 300_000 } })], 0)).toBe(
    'render 25% · ETA 5:00',
  )
  expect(statusText([job({ phase: 'audio' })], 0)).toBe('render audio')
  expect(
    statusText([job({ id: 'b2', kind: 'other', label: 'build_timeline.py', startedAt: 5 }), job({ startedAt: 0 })], 61_000),
  ).toBe('render 1:01 +1')
})

test('keep holds running jobs and the 5 newest finished', async () => {
  const finished = Array.from({ length: 7 }, (_, i) => job({ id: `f${i}`, status: 'done', endedAt: i }))
  const kept = keep([job({ id: 'r' }), ...finished])
  expect(kept.map(j => j.id)).toEqual(['r', 'f6', 'f5', 'f4', 'f3', 'f2'])
})

test('finish marks only the running job with that id', async () => {
  const list = [job({ id: 'b1' }), job({ id: 'b2', status: 'done', endedAt: 5 })]
  expect(finish(list, { id: 'b1', isFailed: true }, 9)[0]).toMatchObject({ id: 'b1', status: 'failed', endedAt: 9 })
  expect(finish(list, { id: 'b2', isFailed: true }, 9)[1]).toMatchObject({ status: 'done', endedAt: 5 })
  expect(finish(list, { id: 'zz', isFailed: false }, 9)).toEqual(keep(list))
})

test('mergeJob replaces parsed fields from the primary log', async () => {
  const before = job({ phase: 'audio', note: 'stale', lastLine: 'old' })
  const merged = mergeJob(before, { logs: [], lastWriteAt: 7, primary: 'frames 100, chunks 4, todo 4, workers 2' })
  expect(merged).toMatchObject({ phase: 'frames', progress: { done: 0, total: 4, unit: 'chunk' }, lastWriteAt: 7 })
  expect(merged.note).toBeUndefined()
})

test('mergeJob falls back to the secondary log for the last line', async () => {
  const merged = mergeJob(job({ kind: 'other', label: 'x' }), { logs: [], lastWriteAt: 1, secondary: '[OK] wrote a\n' })
  expect(merged.lastLine).toBe('[OK] wrote a')
})

test('mergeJob keeps TTS progress from the scene count', async () => {
  const tts = job({ kind: 'tts', label: 'tts', ttsTotal: 3, progress: { done: 0, total: 3, unit: 'ฉาก' } })
  expect(mergeJob(tts, { logs: [], lastWriteAt: 1, primary: '', ttsDone: 2 }).progress).toEqual({ done: 2, total: 3, unit: 'ฉาก' })
  expect(mergeJob(tts, { logs: [], lastWriteAt: 1, ttsDone: 9 }).progress?.done).toBe(3)
})

test('episodeSlug drops the prefix and timestamp, keeps a revision tag', async () => {
  expect(episodeSlug('C:/r/.mp/podcast_v2_asteroid-impact-plan_20261012_172530')).toBe('asteroid-impact-plan')
  expect(episodeSlug('C:/r/.mp/podcast_v2_firstborn-cosmic-silence_20261011_221035_revision_kurz-gfx_02')).toBe(
    'firstborn-cosmic-silence · kurz-gfx_02',
  )
  expect(episodeSlug('C:\\r\\.mp\\producer_cut_3min_x\\')).toBe('producer_cut_3min_x')
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: FAIL in `view.test.ts`, `../hooks/view` not found.

- [ ] **Step 3: Write `hooks/view.ts`**

```ts
import type { Job, LogRef, Progress } from '../types'
import { lastLine, lines, parse } from './parse'

export const SILENCE_MS = 120_000
export const KEEP_FINISHED = 5

export type Refreshed = { logs: LogRef[]; lastWriteAt: number; primary?: string; secondary?: string; ttsDone?: number }

export function keep(list: readonly Job[]): Job[] {
  const running = list.filter(j => j.status === 'running')
  const finished = list
    .filter(j => j.status !== 'running')
    .sort((a, b) => (b.endedAt ?? 0) - (a.endedAt ?? 0))
    .slice(0, KEEP_FINISHED)

  return [...running, ...finished]
}

export function finish(list: readonly Job[], f: { id: string; isFailed: boolean }, now: number): Job[] {
  return keep(
    list.map((j): Job =>
      j.id === f.id && j.status === 'running' ? { ...j, status: f.isFailed ? 'failed' : 'done', endedAt: now } : j,
    ),
  )
}

/** `primary` is the new region of the job's first log, `secondary` of its second. */
export function mergeJob(job: Job, r: Refreshed): Job {
  let next: Job = { ...job, logs: r.logs, lastWriteAt: r.lastWriteAt }
  if (r.primary !== undefined) {
    const { phase: _phase, progress: _progress, note: _note, lastLine: _line, ...base } = next
    next = { ...base, ...parse(job.kind, r.primary) }
  }
  if (next.lastLine === undefined && r.secondary !== undefined) {
    const line = lastLine(lines(r.secondary))
    if (line !== undefined) next = { ...next, lastLine: line }
  }
  if (job.ttsTotal !== undefined) {
    const done = Math.min(r.ttsDone ?? job.progress?.done ?? 0, job.ttsTotal)
    next = { ...next, progress: { done, total: job.ttsTotal, unit: 'ฉาก' } }
  }

  return next
}

export function clock(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = String(total % 60).padStart(2, '0')

  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}

function thousands(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export function percent(p: Progress): number | undefined {
  return p.total !== undefined && p.total > 0 ? Math.min(100, Math.floor((p.done / p.total) * 100)) : undefined
}

export function bar(p: Progress, width: number): string {
  const ratio = p.total !== undefined && p.total > 0 ? Math.min(1, p.done / p.total) : 0
  const filled = Math.round(ratio * width)

  return '█'.repeat(filled) + '░'.repeat(width - filled)
}

export function silentFor(job: Job, now: number): number | undefined {
  const quiet = now - job.lastWriteAt

  return job.status === 'running' && job.note === undefined && quiet > SILENCE_MS ? quiet : undefined
}

export function detail(job: Job, now: number): string {
  const parts: string[] = []
  if (job.phase !== undefined) parts.push(job.phase)
  const p = job.progress
  if (p !== undefined) {
    parts.push(
      p.total !== undefined ? `${thousands(p.done)}/${thousands(p.total)} ${p.unit}` : `${thousands(p.done)} ${p.unit}`,
    )
    if (job.status === 'running' && p.etaMs !== undefined) parts.push(`ETA ${clock(p.etaMs)}`)
  }
  if (job.note !== undefined) parts.push(`⏳ ${job.note}`)
  if (job.status === 'failed') parts.push('พัง')
  parts.push(clock((job.endedAt ?? now) - job.startedAt))

  return parts.join(' · ')
}

export function statusText(jobs: readonly Job[], now: number): string | undefined {
  const running = jobs.filter(j => j.status === 'running').sort((a, b) => a.startedAt - b.startedAt)
  const first = running[0]
  if (first === undefined) return undefined
  const pct = first.progress !== undefined ? percent(first.progress) : undefined
  const head =
    pct !== undefined ? `${first.label} ${pct}%` : `${first.label} ${first.phase ?? clock(now - first.startedAt)}`
  const eta = first.progress?.etaMs !== undefined ? ` · ETA ${clock(first.progress.etaMs)}` : ''
  const more = running.length > 1 ? ` +${running.length - 1}` : ''

  return `${head}${eta}${more}`
}

export function episodeSlug(dir: string): string {
  const name = dir.replace(/[\\/]+$/, '').split(/[\\/]/).at(-1) ?? dir
  const m = name.match(/^podcast_v2_(.+?)_\d{8}(?:_\d{6})?(?:_revision_(.+))?$/)
  if (m === null) return name

  return m[2] === undefined ? m[1]! : `${m[1]} · ${m[2]}`
}
```

- [ ] **Step 4: Run tests and type-check**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: PASS, with 11 tests in `view.test.ts`, plus the earlier files.

Run: `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add claude-mods/mp-jobs/hooks/view.ts claude-mods/mp-jobs/test/view.test.ts
git commit -m "Add job list operations and formatting for mp-jobs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Wire the lifecycle (register, tick, finish, /jobs)

**Files:**
- Modify: `claude-mods/mp-jobs/hooks/register.tsx` (replace the empty register)
- Create: `claude-mods/mp-jobs/test/harness.ts`
- Test: `claude-mods/mp-jobs/test/register.test.ts`

**Interfaces:**
- Consumes:
  - `classify`, `logTargets`, `taskOutputPath` (Task 1)
  - `sceneCount`, `ttsTotal`, `ttsDone`, `finishedTasks`, `sliceNew` (Task 2)
  - `keep`, `finish`, `mergeJob`, `statusText`, `clock` (Task 3)
- Produces:
  - Hooks on `session.start`, `command.run` (`jobs`), `tool.call` (Bash), `prompt.submit`
  - The `jobs` atom
  - Module-private constants `PANE = 'mp-jobs'` and `REPO`, used by Task 5's hook in the same file
  - `test/harness.ts` exports: `REPO`, `EP_REL`, `EP`, `RENDER_CMD`, `START`, `PANE_PROPS`, and `harness(on: On, cwd?: string)`. The `harness` return value has:
    - `files: Map<string, { text: string; mtimeMs: number }>`
    - `toasts: string[]`
    - `statuses: (string | undefined)[]`
    - `opened: string[]`
    - `commands: string[]`
    - `clock: MockClock`
    - `write(path, text, mtimeMs)`
    - `append(path, text, mtimeMs)`
    - `start($)`
    - `background($, id | undefined, command)`
    - `notify($, id, status, exitCode)`
    - `tick()`

- [ ] **Step 1: Write the harness and the failing test**

`claude-mods/mp-jobs/test/harness.ts`:
```ts
import type { On } from 'claude-code'
import { mock } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

export const REPO = 'C:/Users/me/MoneyPrinterV2'
export const EP_REL = '.mp/podcast_v2_asteroid-impact-plan_20261012_172530'
export const EP = `${REPO}/${EP_REL}`
export const RENDER_CMD = `python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`
export const START = 1_000_000
export const PANE_PROPS = {
  title: 'Jobs',
  isFocused: false,
  bodyColumns: 100,
  placement: 'dock' as const,
  scroll: { offset: 0, bodyRows: 30 },
  view: {},
}

type File = { text: string; mtimeMs: number }

const notification = (id: string, status: string, code: number) =>
  `<task-notification>\n<task-id>${id}</task-id>\n<status>${status}</status>\n` +
  `<summary>Background command "job" ${status} (exit code ${code})</summary>\n</task-notification>`

/** Answers, beneath the mod, every engine call it makes, from memory. */
export function harness(on: On, cwd = REPO) {
  const files = new Map<string, File>()
  const toasts: string[] = []
  const statuses: (string | undefined)[] = []
  const opened: string[] = []
  const commands: string[] = []
  const queue: (string | undefined)[] = []
  const clock = mock.clock(on, { now: START })

  const stat = (f: File) => ({ kind: 'file' as const, size: f.text.length, mtimeMs: f.mtimeMs, isLink: false })

  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: cwd }))
  on('command.register', (_$, e) => {
    commands.push(e.name)
    return { value: { command: e.name } }
  })
  on('ui.open', (_$, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true as const } }
  })
  on('ui.toast', (_$, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', (_$, e) => {
    statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.log', () => ({ value: undefined }))
  on('fs.read', (_$, e) => {
    const f = files.get(e.path)
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: f.text }
  })
  on('fs.stat', (_$, e) => {
    const f = files.get(e.path)
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: stat(f) }
  })
  on('fs.list', (_$, e) => {
    const dir = `${e.path}/`
    const value = [...files]
      .filter(([p]) => p.startsWith(dir) && !p.slice(dir.length).includes('/'))
      .map(([p, f]) => ({ name: p.slice(dir.length), ...stat(f) }))
    return { value }
  })
  on('tool.call', { tool: 'Bash' }, () => {
    const id = queue.shift()
    return id === undefined
      ? { result: { stdout: 'ok', stderr: '', interrupted: false }, text: 'ok' }
      : {
          result: { stdout: '', stderr: '', interrupted: false, backgroundTaskId: id },
          text: `Command running in background with ID: ${id}. Output is being written to: C:\\tmp\\tasks\\${id}.output`,
        }
  })
  on('prompt.submit', (_$, e) => ({ text: e.text }))

  return {
    files,
    toasts,
    statuses,
    opened,
    commands,
    clock,
    write: (path: string, text: string, mtimeMs: number) => void files.set(path, { text, mtimeMs }),
    append: (path: string, text: string, mtimeMs: number) =>
      void files.set(path, { text: (files.get(path)?.text ?? '') + text, mtimeMs }),
    start: ($: Engine) => $.session.start({ cwd, surface: 'terminal', isInteractive: true }),
    background: ($: Engine, id: string | undefined, command: string) => {
      queue.push(id)
      return $.tool.call({ tool: 'Bash', command, run_in_background: id !== undefined })
    },
    notify: ($: Engine, id: string, status: string, code: number) =>
      $.prompt.submit({ text: notification(id, status, code), wait: false, origin: { kind: 'task-notification' } }),
    tick: async () => {
      await clock.advance(2000)
      await clock.settle()
    },
  }
}
```

`claude-mods/mp-jobs/test/register.test.ts`:
```ts
import { expect, test } from 'claude-code/testing'

import { EP, EP_REL, RENDER_CMD, START, harness } from './harness'

test('tracks a background render and finishes it on the notification', async ($, on) => {
  const h = harness(on)
  h.write(`${EP}/producer_render.log`, 'chunk 38 done (40/40) 683s\n', START - 5000)
  await h.start($)
  expect(h.commands).toEqual(['jobs'])

  await h.background($, 'b1', RENDER_CMD)
  expect(h.opened).toEqual(['mp-jobs'])
  expect(h.statuses.at(-1)).toBe('render 0:00')

  h.append(
    `${EP}/producer_render.log`,
    'RUN node C:\\x\\render.cjs --timeline t.json\nframes 19946, chunks 40, todo 40, workers 8\nchunk 3 done (10/40) 100s\n',
    START + 1000,
  )
  await h.tick()
  expect(h.statuses.at(-1)).toBe('render 25% · ETA 5:00')

  await h.notify($, 'b1', 'completed', 0)
  expect(h.toasts).toEqual(['render เสร็จ · 0:02'])
  expect(h.statuses.at(-1)).toBeUndefined()
})

test('a failed job toasts its last line', async ($, on) => {
  const h = harness(on)
  h.write('C:/tmp/tasks/b4.output', '', START)
  await h.start($)
  await h.background($, 'b4', 'python scripts/build_timeline.py')
  h.append('C:/tmp/tasks/b4.output', 'Traceback (most recent call last):\nValueError: no shots\n', START + 1000)
  await h.notify($, 'b4', 'failed', 1)
  expect(h.toasts).toEqual(['build_timeline.py พัง · ValueError: no shots'])
})

test('counts TTS scenes written after the start', async ($, on) => {
  const h = harness(on)
  h.write(`${EP}/script.json`, '[{},{},{},{}]', START - 9000)
  h.write(`${EP}/scene_00.wav`, 'x', START - 9000)
  await h.start($)
  await h.background($, 'b2', `python scripts/producer_mode.py produce-tts --plan ${EP_REL}/producer_plan.json`)
  expect(h.statuses.at(-1)).toBe('tts 0%')

  h.write(`${EP}/scene_01.wav`, 'x', START + 1500)
  h.write(`${EP}/scene_02.wav`, 'x', START + 1500)
  await h.tick()
  expect(h.statuses.at(-1)).toBe('tts 66%')
})

test('finishing one job keeps the other in the status line', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, 'b1', RENDER_CMD)
  await h.background($, 'b3', `python ${EP_REL}/fetch_official.py > ${EP_REL}/fetch_run3.log 2>&1`)
  expect(h.statuses.at(-1)).toBe('render 0:00 +1')

  await h.notify($, 'b1', 'completed', 0)
  await h.tick()
  expect(h.statuses.at(-1)).toBe('fetch 0:02')
})

test('foreground commands are not tracked and unknown notifications raise no toast', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, undefined, 'ls')
  expect(h.opened).toEqual([])
  await h.notify($, 'zzz', 'completed', 0)
  expect(h.toasts).toEqual([])
})

test('does nothing outside the repo', async ($, on) => {
  const h = harness(on, 'C:/work/KL.App.UI')
  await h.start($)
  await h.background($, 'b9', 'npm run build')
  expect(h.commands).toEqual([])
  expect(h.opened).toEqual([])
  expect(h.statuses).toEqual([])
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: FAIL in `register.test.ts`. Example: `expect(h.commands).toEqual(['jobs'])` receives `[]`, because register is still empty.

- [ ] **Step 3: Replace `hooks/register.tsx`**

```tsx
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Job, LogRef } from '../types'
import { classify, logTargets, taskOutputPath } from './classify'
import { finishedTasks, sceneCount, sliceNew, ttsDone, ttsTotal } from './parse'
import { clock, finish, keep, mergeJob, statusText } from './view'

const PANE = 'mp-jobs'
const REPO = /[\\/]MoneyPrinterV2(?:[\\/]|$)/i
const TICK_MS = 2000

const jobs = atom({ plugin: 'mp-jobs', key: 'jobs' } as const, [])

export const register: Register = on => {
  let session$: EngineInterface | undefined
  let ticker: { cancel: () => void } | undefined
  let isTicking = false
  let hasHinted = false

  const textOf = async ($: EngineInterface, path: string): Promise<string | undefined> => {
    const text = await $.fs.read(path).catch(() => undefined)

    return typeof text === 'string' ? text : undefined
  }

  const refresh = async ($: EngineInterface, job: Job): Promise<Job> => {
    let lastWriteAt = job.lastWriteAt
    const fresh: (string | undefined)[] = []
    const logs: LogRef[] = []
    for (const [i, log] of job.logs.entries()) {
      const stat = await $.fs.stat(log.path).catch(() => undefined)
      if (stat === undefined || stat.mtimeMs === log.seenMtimeMs) {
        logs.push(log)
        continue
      }
      lastWriteAt = Math.max(lastWriteAt, stat.mtimeMs)
      const text = await textOf($, log.path)
      fresh[i] = text === undefined ? undefined : sliceNew(text, log.offset)
      logs.push({ ...log, seenMtimeMs: stat.mtimeMs })
    }
    let done: number | undefined
    if (job.kind === 'tts' && job.episodeDir !== undefined) {
      const entries = await $.fs.list(job.episodeDir).catch(() => [])
      done = ttsDone(entries, job.startedAt)
      for (const f of entries) if (/^scene_\d+\.wav$/.test(f.name)) lastWriteAt = Math.max(lastWriteAt, f.mtimeMs)
    }

    return mergeJob(job, {
      logs,
      lastWriteAt,
      ...(fresh[0] !== undefined ? { primary: fresh[0] } : {}),
      ...(fresh[1] !== undefined ? { secondary: fresh[1] } : {}),
      ...(done !== undefined ? { ttsDone: done } : {}),
    })
  }

  const stopTicker = () => {
    ticker?.cancel()
    ticker = undefined
  }

  const tick = async ($: EngineInterface) => {
    if (isTicking) return
    isTicking = true
    try {
      const now = await $.clock.now()
      const running = (await read($, jobs)).filter(j => j.status === 'running')
      if (running.length === 0) {
        stopTicker()
        $.ui.status(undefined)
        return
      }
      const fresh = await Promise.all(running.map(j => refresh($, j).catch(() => j)))
      const byId = new Map(fresh.map(j => [j.id, j]))
      await update($, jobs, list => list.map(j => (j.status === 'running' ? byId.get(j.id) ?? j : j)))
      $.ui.status(statusText(await read($, jobs), now))
    } finally {
      isTicking = false
    }
  }

  const startTicker = ($: EngineInterface) => {
    if (ticker !== undefined) return
    ticker = $.clock.every(TICK_MS, () => {
      void tick($)
    })
  }

  const openPane = async ($: EngineInterface) => {
    const opened = await $.ui.open({ id: PANE, title: 'Jobs' })
    if (!opened.isPlaced && !hasHinted) {
      hasHinted = true
      $.ui.toast('mp-jobs: พิมพ์ /jobs เพื่อดู')
    }
  }

  const track = async ($: EngineInterface, id: string, command: string, cwd: string, resultText: string) => {
    const c = classify(command, cwd)
    const now = await $.clock.now()
    const logs: LogRef[] = []
    for (const target of logTargets(c, taskOutputPath(resultText))) {
      const text = target.isShared ? await textOf($, target.path) : undefined
      const stat = await $.fs.stat(target.path).catch(() => undefined)
      logs.push({ path: target.path, offset: text?.length ?? 0, seenMtimeMs: target.isShared ? stat?.mtimeMs ?? 0 : 0 })
    }
    let total: number | undefined
    if (c.kind === 'tts' && c.episodeDir !== undefined) {
      const script = await textOf($, `${c.episodeDir}/script.json`)
      const entries = await $.fs.list(c.episodeDir).catch(() => [])
      total = ttsTotal(script === undefined ? 0 : sceneCount(script), entries, c)
    }
    const job: Job = {
      id,
      kind: c.kind,
      label: c.label,
      command: command.slice(0, 1000),
      ...(c.episodeDir !== undefined ? { episodeDir: c.episodeDir } : {}),
      logs,
      ...(total !== undefined ? { ttsTotal: total, progress: { done: 0, total, unit: 'ฉาก' } } : {}),
      startedAt: now,
      status: 'running',
      lastWriteAt: now,
    }
    await update($, jobs, list => keep([...list.filter(j => j.id !== id), job]))
    $.ui.status(statusText(await read($, jobs), now))
    startTicker(session$ ?? $)
    await openPane($)
  }

  on('session.start', async ($, e, next) => {
    session$ = $
    if (REPO.test(e.cwd)) {
      await $.command.register({ name: 'jobs', description: 'Show live MoneyPrinter jobs (render, TTS, fetch, score)' })
      if ((await read($, jobs)).some(j => j.status === 'running')) startTicker($)
    }

    return next(e)
  })

  on('command.run', { command: 'jobs' }, async $ => {
    const opened = await $.ui.open({ id: PANE, title: 'Jobs' })

    return { text: opened.isPlaced ? 'Jobs pane opened.' : `Jobs pane waits: ${opened.reason}` }
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const cwd = await $.session.cwd().catch(() => '')
    const ran = await next(e)
    if (!REPO.test(cwd) || ran.deny !== undefined || ran.isError === true) return ran
    const id = ran.result.backgroundTaskId
    if (id === undefined) return ran
    try {
      await track($, id, e.command, cwd, ran.text ?? '')
    } catch (err) {
      $.ui.log(`mp-jobs: could not track ${id}: ${String(err)}`)
    }

    return ran
  })

  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind !== 'task-notification') return next(e)
    try {
      const ended = finishedTasks(e.text)
      const list = await read($, jobs)
      const ours = ended.filter(f => list.some(j => j.id === f.id && j.status === 'running'))
      if (ours.length > 0) {
        const now = await $.clock.now()
        for (const f of ours) {
          const job = list.find(j => j.id === f.id)!
          const last = await refresh($, job).catch(() => job)
          await update($, jobs, cur => finish(cur.map(j => (j.id === last.id ? last : j)), f, now))
          $.ui.toast(
            f.isFailed
              ? `${last.label} พัง · ${last.lastLine ?? f.summary ?? ''}`
              : `${last.label} เสร็จ · ${clock(now - last.startedAt)}`,
          )
        }
        $.ui.status(statusText(await read($, jobs), now))
      }
    } catch (err) {
      $.ui.log(`mp-jobs: could not read a task notification: ${String(err)}`)
    }

    return next(e)
  })
}
```

- [ ] **Step 4: Run tests, type-check, validate**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: PASS for all files, including 6 tests in `register.test.ts`.

If `a failed job toasts its last line` fails because the toast shows the summary instead of `ValueError: no shots`, the task output's first stat happened before the write. Confirm that `refresh` in `prompt.submit` reads the file whose `seenMtimeMs` is 0. Do not change the expectation.

Run: `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: exit 0.

Run: `claude plugin validate claude-mods/mp-jobs`
Expected: hooks on `session.start`, `command.run`, `tool.call`, `prompt.submit`, with no refusals.

- [ ] **Step 5: Commit**

```bash
git add claude-mods/mp-jobs/hooks/register.tsx claude-mods/mp-jobs/test/harness.ts claude-mods/mp-jobs/test/register.test.ts
git commit -m "Track background jobs, tick their logs and finish them in mp-jobs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Draw the pane

**Files:**
- Modify: `claude-mods/mp-jobs/hooks/register.tsx` (add a `ui.render` hook inside `register`, and imports)
- Test: `claude-mods/mp-jobs/test/pane.test.ts`

**Interfaces:**
- Consumes:
  - `PANE`, the `jobs` atom (Task 4)
  - `bar`, `clock`, `detail`, `episodeSlug`, `percent`, `silentFor` from `./view` (Task 3)
  - `harness`, `PANE_PROPS`, `RENDER_CMD`, `EP_REL` (Task 4)
- Produces: the `ui.render` hook for `{ component: 'Pane', requestId: 'mp-jobs' }`.

- [ ] **Step 1: Write the failing test**

`claude-mods/mp-jobs/test/pane.test.ts`:
```ts
import { expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { EP_REL, PANE_PROPS, RENDER_CMD, harness } from './harness'

const SURFACES = ['terminal', 'desktop'] as const
const mount = ($: Engine, surface: (typeof SURFACES)[number]) =>
  $.ui.mount({ plugin: 'mp-jobs', surface, component: 'Pane', requestId: 'mp-jobs', props: PANE_PROPS })

test('empty pane says nothing runs', async ($, on) => {
  const h = harness(on)
  await h.start($)
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /ยังไม่มีงานรัน/ })).toBeDefined()
    await ui.unmount()
  }
})

test('one episode: header once, finished jobs below the divider', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, 'b1', RENDER_CMD)
  await h.background($, 'b2', `python ${EP_REL}/fetch_official.py > ${EP_REL}/fetch_run3.log 2>&1`)
  await h.notify($, 'b2', 'completed', 0)
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /^asteroid-impact-plan$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /● render/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /ยังไม่มี log/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /─ จบแล้ว ─/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /✓ fetch/ })).toBeDefined()
    await ui.unmount()
  }
})

test('two episodes put the slug on each row', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, 'b1', RENDER_CMD)
  await h.background(
    $,
    'b2',
    'python .mp/podcast_v2_firstborn-cosmic-silence_20261011_221035_revision_kurz-gfx_02/fetch_official.py',
  )
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /^asteroid-impact-plan$/ })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: /· firstborn-cosmic-silence · kurz-gfx_02/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /· asteroid-impact-plan/ })).toBeDefined()
    await ui.unmount()
  }
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: FAIL in `pane.test.ts`. Example: `ui.find(... /ยังไม่มีงานรัน/)` is undefined, or the mount is refused because no hook draws `Pane`.

- [ ] **Step 3: Add the render hook to `register.tsx`**

Change the view import to:
```tsx
import { bar, clock, detail, episodeSlug, finish, keep, mergeJob, percent, silentFor, statusText } from './view'
```

Add this hook inside `register`, after the `prompt.submit` hook:
```tsx
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, jobs)
    const now = await $.clock.now()
    const running = list.filter(j => j.status === 'running')
    const finished = list.filter(j => j.status !== 'running')
    const dirs = [...new Set(list.flatMap(j => (j.episodeDir === undefined ? [] : [j.episodeDir])))]
    const shared = dirs.length === 1 ? episodeSlug(dirs[0]!) : undefined
    const barWidth = e.props.bodyColumns >= 70 ? 15 : 8

    const row = (job: Job) => {
      const color = job.status === 'failed' ? 'error' : job.status === 'done' ? 'success' : 'suggestion'
      const icon = job.status === 'failed' ? '✗' : job.status === 'done' ? '✓' : '●'
      const pct = job.progress !== undefined ? percent(job.progress) : undefined
      const meter =
        job.status === 'running' && job.progress !== undefined && pct !== undefined
          ? `${bar(job.progress, barWidth)} ${String(pct).padStart(3)}% `
          : ''
      const where = shared === undefined && job.episodeDir !== undefined ? ` · ${episodeSlug(job.episodeDir)}` : ''
      const quiet = silentFor(job, now)
      const under =
        job.lastLine ?? (job.status === 'running' && job.progress === undefined ? 'ยังไม่มี log' : undefined)

      return (
        <Box key={job.id} flexDirection="column">
          <Box flexDirection="row">
            <Text color={color}>{`${icon} ${job.label.padEnd(7)} `}</Text>
            <Text wrap="truncate-end">{`${meter}${detail(job, now)}${where}`}</Text>
            {quiet !== undefined && <Text color="warning">{` เงียบ ${clock(quiet)}`}</Text>}
          </Box>
          {under !== undefined && <Text dimColor wrap="truncate-end">{`  ${under}`}</Text>}
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        {shared !== undefined && <Text bold>{shared}</Text>}
        {list.length === 0 && <Text dimColor>ยังไม่มีงานรัน</Text>}
        {running.map(row)}
        {finished.length > 0 && <Text dimColor>─ จบแล้ว ─</Text>}
        {finished.map(row)}
      </Box>
    )
  })
```

- [ ] **Step 4: Run tests, type-check, validate**

Run: `claude plugin test claude-mods/mp-jobs`
Expected: PASS for all files, including 3 tests in `pane.test.ts` on both `terminal` and `desktop`.

If a mount is refused with "an element its table lacks" or "a prop not allowed", read the reason. Change only that element or prop to one the reason names. Do not drop the surface from `SURFACES`.

Run: `remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: exit 0.

Run: `claude plugin validate claude-mods/mp-jobs`
Expected: a `ui.render` hook on `Pane` is listed, with no refusals.

- [ ] **Step 5: Commit**

```bash
git add claude-mods/mp-jobs/hooks/register.tsx claude-mods/mp-jobs/test/pane.test.ts
git commit -m "Draw the mp-jobs pane" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Live check in this session, then install

**Files:**
- Create (scratch, not committed): `C:\Users\66984\AppData\Local\Temp\claude\C--Users-66984-workspace-coding-MoneyPrinterV2\d640dbfd-eefc-43ab-b2cc-46b820d5b706\scratchpad\mp-jobs-fake\` with these files:
  - `scripts/producer_mode.py`
  - `fetch_official.py`
  - `scripts/producer_score.py`
  - `.mp/podcast_v2_fake-episode_20261013_000000/` with `producer_plan.json` and `script.json`
- Create (temporary): `C:\Users\66984\.claude\dev-mods\d640dbfd-eefc-43ab-b2cc-46b820d5b706\mp-jobs\` (a copy of the mod)
- Modify (only with นน's explicit yes): `C:\Users\66984\.claude\settings.json` `env.CLAUDE_CODE_PLUGIN_DIRS`

**Interfaces:**
- Consumes: the finished mod (Tasks 1-5).
- Produces: nothing further in code.

- [ ] **Step 1: Write fake jobs that print the real log formats.** Every path below is under the scratchpad `mp-jobs-fake\`, written as `$F`.

`$F/scripts/producer_mode.py`:
```python
import json, sys, time
from pathlib import Path

cmd, plan = sys.argv[1], Path(sys.argv[sys.argv.index("--plan") + 1])
ep = plan.parent
if cmd == "render-video":
    time.sleep(1)  # let the mod record the log's offset before the first write
    log = ep / "producer_render.log"
    with log.open("a", encoding="utf-8") as f:
        f.write("RUN node C:\\x\\doc_renderer\\render.cjs --timeline t.json\n"); f.flush()
        f.write("frames 2000, chunks 10, todo 10, workers 4\n"); f.flush()
        for k in range(1, 11):
            time.sleep(2); f.write(f"chunk {k} done ({k}/10) {k * 2}s\n"); f.flush()
        f.write("video ready C:\\x\\video.mp4 in 21s\n"); f.flush()
        for n in range(500, 2001, 500):
            time.sleep(1); f.write(f"frame= {n} fps=500 q=-1.0 size=1KiB time=00:00:01.00 bitrate=1kbits/s speed=30x elapsed=0:00:0{n // 500}.00    \r"); f.flush()
    print("[OK] wrote render_manifest.json")
elif cmd == "produce-tts":
    scenes = json.loads((ep / "script.json").read_text(encoding="utf-8"))
    for i in range(len(scenes)):
        time.sleep(2); (ep / f"scene_{i:02d}.wav").write_bytes(b"RIFF")
    print("[OK] wrote tts_manifest.json")
```

`$F/fetch_official.py`:
```python
import sys, time
for i in range(3):
    print(f"nasa V0{i} PIA0000{i} 1920 1080", flush=True); time.sleep(1)
print("  429 on https://upload.wikimedia.org/x.jpg?utm_... waiting 150s", flush=True)
time.sleep(150)
print("nasa V09 PIA00009 1920 1080", flush=True)
sys.exit(1)
```

`$F/scripts/producer_score.py`:
```python
import sys, time
print("pad + drone", flush=True)
for b in range(1, 21):
    print(f"\r  pad block {b}/20", end="", flush=True); time.sleep(0.5)
print(); print("air / events", flush=True); time.sleep(2); print("reverb", flush=True); time.sleep(2)
```

`$F/.mp/podcast_v2_fake-episode_20261013_000000/producer_plan.json` holds `{}`. `script.json` holds `[{},{},{},{},{}]`.

- [ ] **Step 2: Load the mod live**

Copy `claude-mods/mp-jobs` to `C:\Users\66984\.claude\dev-mods\d640dbfd-eefc-43ab-b2cc-46b820d5b706\mp-jobs`, without `.claude-plugin/types`. Hot reload, already enabled in Task 0, loads it when the turn ends. End the turn.

- [ ] **Step 3: Run the fake jobs from the repo root, each as a background Bash call**

```bash
python "$F/scripts/producer_mode.py" render-video --plan "$F/.mp/podcast_v2_fake-episode_20261013_000000/producer_plan.json"
```
```bash
python "$F/scripts/producer_mode.py" produce-tts --plan "$F/.mp/podcast_v2_fake-episode_20261013_000000/producer_plan.json" --force
```
```bash
python "$F/fetch_official.py" > "$F/.mp/podcast_v2_fake-episode_20261013_000000/fetch_run1.log" 2>&1
```
```bash
python "$F/scripts/producer_score.py" render --episode "$F/.mp/podcast_v2_fake-episode_20261013_000000"
```
Replace `$F` with the absolute scratchpad path.

- [ ] **Step 4: Ask นน to watch and confirm each, one line each**

- render moves `frames` 10%…100% with an ETA, then `mux`, then `finalize` with an `fr` count. It ends with `render เสร็จ · m:ss`.
- tts goes `0/5 ฉาก` → `5/5 ฉาก`, with no silence badge.
- fetch shows `3 รายการ · ⏳ รอ rate limit 150s (429)` with no `เงียบ` badge during the 150 s. It ends with the toast `fetch พัง · nasa V09 PIA00009 1920 1080`.
- score goes `pad` 1/20…20/20, then `air`, then `reverb`.
- The header reads `fake-episode`.
- The status line follows the earliest running job, with `+N`.

Record any mismatch as a failing test in the owning task's test file before fixing it.

- [ ] **Step 5: Install for future sessions (ask first)**

Ask นน: "Add `CLAUDE_CODE_PLUGIN_DIRS = C:/Users/66984/workspace-coding/MoneyPrinterV2/claude-mods/mp-jobs` to the `env` block of `~/.claude/settings.json`?"

Only on a clear yes:
1. Read the file.
2. Add the key, merging with any existing value with `;`.
3. Delete the dev-mods copy, so the mod does not load twice:
   ```bash
   rm -rf "C:/Users/66984/.claude/dev-mods/d640dbfd-eefc-43ab-b2cc-46b820d5b706/mp-jobs"
   ```

On a no, leave the dev-mods copy and say it loads only in this session.

- [ ] **Step 6: Final checks and commit**

Run: `claude plugin test claude-mods/mp-jobs && claude plugin validate claude-mods/mp-jobs && remotion/node_modules/.bin/tsc -p claude-mods/mp-jobs`
Expected: all pass.

If Step 4 led to fixes, commit them:
```bash
git add claude-mods/mp-jobs
git commit -m "Fix mp-jobs issues found in the live check" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Spike findings

Recorded 2026-10-13 from `scratchpad/mp-jobs-spike.log` in the desktop Code tab session.

- **(a) Pane:** drawn unasked. `session.start ... unasked-open={"isPlaced":true}`, then `render Pane surface=desktop placement=dock cols=41`. The docked pane is only **41 columns** wide. Note that `session.start` `e.surface` was `null`; the render's `e.surface` is `desktop`.
- **(b) Status line:** visible. นน saw both the pane and the status line.
- **(c) Background Bash:** `result={"stdout":"","stderr":"","interrupted":false,"isImage":false,"noOutputExpected":false,"backgroundTaskId":"bb7rwf3pb"}`. The `text` is `Command running in background with ID: bb7rwf3pb. Output is being written to: C:\...	asksb7rwf3pb.output. You will be notified when it completes. To check interim output, use Read on that file path.` The path is followed by `. You will be notified…` **on the same line**, so the plan's `(\S.*?)\s*$` regex would swallow that sentence. The path must end at `.output`.
- **(d) Notification:** `prompt.submit origin={"kind":"task-notification"}` with text `<task-notification>
<task-id>bb7rwf3pb</task-id>
<tool-use-id>…</tool-use-id>
<output-file>…</output-file>
<status>completed</status>
<summary>Background command "Run a short fake job in the background" completed (exit code 0)</summary>
</task-notification>`. `<task-id>` equals `backgroundTaskId`, and the shape matches `NOTIFY` and `finishedTasks`.
- **(e) Timer from a `tool.call` `$`:** not confirmed by eye. The ledger ruling avoids depending on it: the ticker starts in `session.start`, the documented home for work that outlives a dispatch.
- **Validator rule found while writing the spike:** `$` may not be stored (`session$ = $` is refused). `$` may only be passed to functions declared at the top level of the file. Closures inside `register` cannot receive it, but a timer callback that calls a top-level function with `$` is accepted.
