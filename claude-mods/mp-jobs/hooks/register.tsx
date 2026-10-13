import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Job, LogRef } from '../types'
import { bandAlt, bandHeight, bandRows, bandSvg, bandWidth } from './band'
import { classify, logTargets, taskOutputPath } from './classify'
import { finishedTasks, sceneCount, sliceNew, ttsDone, ttsTotal } from './parse'
import { bar, clock, detail, episodeSlug, finish, keep, mergeJob, percent, silentFor, statusText } from './view'

const PANE = 'mp-jobs'
const REPO = /[\\/]MoneyPrinterV2(?:[\\/]|$)/i
const TICK_MS = 2000
// SMIL needs the sandboxed frame, which reloads (and flickers) on every redraw: a still image instead.
const ANIMATE = false

const jobs = atom({ plugin: 'mp-jobs', key: 'jobs' } as const, [])

// The engine refuses a stored `$` and a `$` passed to anything but a top-level function,
// so every helper that needs it lives here, with the module's own state beside it.
let ticker: { cancel: () => void } | undefined
let isTicking = false
let hasHinted = false
let isStatusShown = false

async function textOf($: EngineInterface, path: string): Promise<string | undefined> {
  const text = await $.fs.read(path).catch(() => undefined)

  return typeof text === 'string' ? text : undefined
}

async function showStatus($: EngineInterface, now: number) {
  const text = statusText(await read($, jobs), now)
  if (text === undefined && !isStatusShown) return
  $.ui.status(text)
  isStatusShown = text !== undefined
}

async function refresh($: EngineInterface, job: Job): Promise<Job> {
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

async function tick($: EngineInterface) {
  if (isTicking) return
  isTicking = true
  try {
    const now = await $.clock.now()
    const running = (await read($, jobs)).filter(j => j.status === 'running')
    if (running.length > 0) {
      const fresh = await Promise.all(running.map(j => refresh($, j).catch(() => j)))
      const byId = new Map(fresh.map(j => [j.id, j]))
      await update($, jobs, list => list.map(j => (j.status === 'running' ? byId.get(j.id) ?? j : j)))
    }
    await showStatus($, now)
  } finally {
    isTicking = false
  }
}

/** One ticker per load; it reads state every period and does nothing while no job runs. */
function ensureTicker($: EngineInterface) {
  if (ticker !== undefined) return
  ticker = $.clock.every(TICK_MS, () => {
    void tick($)
  })
}

async function openPane($: EngineInterface) {
  const opened = await $.ui.open({ id: PANE, title: 'Jobs' })
  if (!opened.isPlaced && !hasHinted) {
    hasHinted = true
    $.ui.toast('mp-jobs: พิมพ์ /jobs เพื่อดู')
  }
}

async function track($: EngineInterface, id: string, command: string, cwd: string, resultText: string) {
  const c = classify(command, cwd)
  const now = await $.clock.now()
  const logs: LogRef[] = []
  for (const target of logTargets(c, taskOutputPath(resultText))) {
    const text = target.isShared ? await textOf($, target.path) : undefined
    const stat = target.isShared ? await $.fs.stat(target.path).catch(() => undefined) : undefined
    logs.push({ path: target.path, offset: text?.length ?? 0, seenMtimeMs: stat?.mtimeMs ?? 0 })
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
  await showStatus($, now)
  ensureTicker($)
  await openPane($)
}

async function finishTasks($: EngineInterface, text: string) {
  const list = await read($, jobs)
  const ours = finishedTasks(text).filter(f => list.some(j => j.id === f.id && j.status === 'running'))
  if (ours.length === 0) return
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
  await showStatus($, now)
}

export const register: Register = on => {
  ticker = undefined
  isTicking = false
  hasHinted = false
  isStatusShown = false

  on('session.start', async ($, e, next) => {
    if (REPO.test(e.cwd)) {
      await $.command.register({ name: 'jobs', description: 'Show live MoneyPrinter jobs (render, TTS, fetch, score)' })
      ensureTicker($)
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
  }).catch(($, e, next) => next(e))

  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind === 'task-notification') {
      try {
        await finishTasks($, e.text)
      } catch (err) {
        $.ui.log(`mp-jobs: could not read a task notification: ${String(err)}`)
      }
    }

    return next(e)
  }).catch(($, e, next) => next(e))

  // Only the desktop draws Svg; the terminal keeps the status line.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'desktop' || e.props.hasSurvey) return next(e)
    const now = await $.clock.now()
    const band = bandRows(await read($, jobs), now)
    if (band.rows.length === 0) return next(e)
    const { Svg } = $.ui.resolve(e)
    const width = bandWidth(e.props.bodyColumns)

    return (
      <Svg
        source={bandSvg(band, { width, now, animate: ANIMATE })}
        alt={bandAlt(band)}
        width={width}
        height={bandHeight(band)}
        isInteractive={ANIMATE}
      />
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, jobs)
    const now = await $.clock.now()
    const running = list.filter(j => j.status === 'running')
    const finished = list.filter(j => j.status !== 'running')
    const dirs = [...new Set(list.flatMap(j => (j.episodeDir === undefined ? [] : [j.episodeDir])))]
    const shared = dirs.length === 1 ? episodeSlug(dirs[0]!) : undefined
    // The docked desktop pane is about 41 columns: there the detail gets a line of its own.
    const isNarrow = e.props.bodyColumns < 60
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
      const text = `${detail(job, now)}${where}`
      const quiet = silentFor(job, now)
      const under =
        job.lastLine ?? (job.status === 'running' && job.progress === undefined ? 'ยังไม่มี log' : undefined)

      return (
        <Box key={job.id} flexDirection="column">
          <Box flexDirection="row">
            <Text color={color}>{`${icon} ${job.label.padEnd(7)} `}</Text>
            {isNarrow ? meter !== '' && <Text>{meter}</Text> : <Text wrap="truncate-end">{`${meter}${text}`}</Text>}
            {quiet !== undefined && <Text color="warning">{` เงียบ ${clock(quiet)}`}</Text>}
          </Box>
          {isNarrow && <Text wrap="truncate-end">{`  ${text}`}</Text>}
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
}
