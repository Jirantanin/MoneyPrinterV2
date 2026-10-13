import { expect, test } from 'claude-code/testing'

import { agentJob, agentStep, stepLine } from '../hooks/agent'
import { bandRows, bandSvg } from '../hooks/band'
import { harness } from './harness'

test('a spawned agent is a running job named by its description, with no steps yet', async () => {
  const job = agentJob('a1', 'Record R07 stills for the asteroid episode', 'general-purpose', 5_000)
  expect(job).toEqual({
    id: 'a1',
    kind: 'agent',
    label: 'Record R07 stills for t…',
    command: 'general-purpose',
    logs: [],
    progress: { done: 0, unit: 'ขั้น' },
    startedAt: 5_000,
    status: 'running',
    lastWriteAt: 5_000,
  })
})

test('a step reads as what the tool did', async () => {
  expect(stepLine({ tool: 'Bash', command: 'node record.cjs runs.html R07', description: 'Record R07 stills' })).toBe(
    'Record R07 stills',
  )
  expect(stepLine({ tool: 'Bash', command: 'node record.cjs runs.html R07\necho done' })).toBe('node record.cjs runs.html R07')
  expect(stepLine({ tool: 'Read', file_path: 'C:\\x\\doc_renderer\\gfx_kit\\kit.js' })).toBe('Read kit.js')
  expect(stepLine({ tool: 'Grep', pattern: 'drawOrbit' })).toBe('Grep drawOrbit')
  expect(stepLine({ tool: 'TodoWrite' })).toBe('TodoWrite')
})

test('a step counts on its own agent only', async () => {
  const list = [agentJob('a1', 'gfx R07', 'general-purpose', 0), agentJob('a2', 'gfx R08', 'general-purpose', 0)]
  const next = agentStep(list, 'a2', 'Read kit.js', 9_000)
  expect(next[0]).toBe(list[0])
  expect(next[1]).toMatchObject({ progress: { done: 1, unit: 'ขั้น' }, lastLine: 'Read kit.js', lastWriteAt: 9_000 })
  expect(agentStep(list, 'zzz', 'Read kit.js', 9_000)).toBe(list)
})

test('the band shows an agent by its description, its step count and a sprite of its own', async () => {
  const job = { ...agentJob('a1', 'gfx R07', 'general-purpose', 0), progress: { done: 12, unit: 'ขั้น' } }
  const band = bandRows([job], 30_000)
  expect(band.rows[0]).toMatchObject({ title: 'gfx R07', pill: 'agent 12', right: '0:30' })
  const sprite = (kind: 'agent' | 'other') =>
    bandSvg({ rows: [{ ...band.rows[0]!, kind }], more: 0 }, { width: 800, now: 0, animate: false }).match(
      /<path class="sprite" d="([^"]+)"/,
    )?.[1]
  expect(sprite('agent')).not.toBe(sprite('other'))
})

test('a subagent shows from its spawn and finishes on its own turn', async ($, on) => {
  const h = harness(on)
  await h.start($)
  const started = await h.spawn($, 'gfx R07')
  expect(started.agentId).toBe('a1')
  expect(h.opened).toEqual(['mp-jobs'])
  expect(h.statuses.at(-1)).toBe('gfx R07 0:00')

  await h.clock.advance(65_000)
  await h.turnDone($, undefined, 'answer')
  expect(h.toasts).toEqual([])
  await h.turnDone($, 'a1', 'answer')
  expect(h.toasts).toEqual(['gfx R07 เสร็จ · 1:05'])
  expect(h.statuses.at(-1)).toBeUndefined()
})

test('an interrupted or failed subagent is marked failed', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.spawn($, 'gfx R07')
  await h.spawn($, 'gfx R08')
  await h.turnDone($, 'a1', 'aborted')
  await h.turnDone($, 'a2', 'error')
  expect(h.toasts).toEqual(['gfx R07 พัง', 'gfx R08 พัง'])
})

test('subagents outside the repo are left alone', async ($, on) => {
  const h = harness(on, 'C:/work/KL.App.UI')
  await h.start($)
  await h.spawn($, 'explore')
  expect(h.opened).toEqual([])
  expect(h.statuses).toEqual([])
})
