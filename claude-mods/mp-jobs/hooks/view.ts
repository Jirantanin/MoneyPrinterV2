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

export function thousands(n: number): string {
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
