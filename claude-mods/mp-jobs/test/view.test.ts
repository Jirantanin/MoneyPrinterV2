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
