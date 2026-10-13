import { expect, test } from 'claude-code/testing'

import type { Job } from '../types'
import { bandAlt, bandRows, bandSvg, bandWidth } from '../hooks/band'
import type { Band } from '../hooks/band'
import { RENDER_CMD, harness } from './harness'

const EP_DIR = 'C:/x/.mp/podcast_v2_asteroid-impact-plan_20261012_172530'
const BAND_PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 120,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

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

const RENDER_ROW = {
  id: 'b1',
  kind: 'render' as const,
  title: 'asteroid-impact-plan',
  pill: 'render frames 10/40',
  ratio: 0.25,
  right: '25% · 5:00',
  isQuiet: false,
}
const one = (row: Partial<Band['rows'][number]> = {}): Band => ({ rows: [{ ...RENDER_ROW, ...row }], more: 0 })
const pillX = (svg: string) => Number(svg.match(/<rect class="pill" x="([\d.]+)"/)?.[1])
const sprite = (svg: string) => svg.match(/<path class="sprite" d="([^"]+)"/)?.[1]

test('a render row: slug title, phase and count in the pill, percent and ETA on the right', async () => {
  const band = bandRows(
    [job({ episodeDir: EP_DIR, phase: 'frames', progress: { done: 10, total: 40, unit: 'chunk', etaMs: 300_000 }, lastWriteAt: 50_000 })],
    60_000,
  )
  expect(band).toEqual({ rows: [RENDER_ROW], more: 0 })
})

test('a count with no end has no ratio and shows the time so far; a job outside an episode goes by its label', async () => {
  const band = bandRows(
    [job({ id: 'b2', kind: 'fetch', label: 'fetch', progress: { done: 12, unit: 'รายการ' }, lastWriteAt: 40_000 })],
    42_000,
  )
  expect(band.rows).toEqual([{ id: 'b2', kind: 'fetch', title: 'fetch', pill: 'fetch 12', right: '0:42', isQuiet: false }])
})

test('a quiet job says how long it has been silent', async () => {
  const [row] = bandRows([job({ phase: 'frames' })], 135_000).rows
  expect(row?.isQuiet).toBe(true)
  expect(row?.right).toBe('เงียบ 2:15')
  expect(row?.pill).toBe('render frames')
})

test('a note takes the place of the count in the pill', async () => {
  const [row] = bandRows(
    [job({ kind: 'fetch', label: 'fetch', progress: { done: 12, unit: 'รายการ' }, note: 'รอ rate limit 30s (429)' })],
    300_000,
  ).rows
  expect(row?.pill).toBe('fetch รอ rate limit 30s (429)')
  expect(row?.isQuiet).toBe(false)
})

test('only running jobs, oldest first, three rows at most', async () => {
  const band = bandRows(
    [
      job({ id: 'e', startedAt: 5 }),
      job({ id: 'done', startedAt: 0, status: 'done', endedAt: 9 }),
      job({ id: 'a', startedAt: 1 }),
      job({ id: 'd', startedAt: 4 }),
      job({ id: 'b', startedAt: 2 }),
      job({ id: 'c', startedAt: 3 }),
    ],
    10,
  )
  expect(band.rows.map(r => r.id)).toEqual(['a', 'b', 'c'])
  expect(band.more).toBe(2)
})

test('the drawing escapes titles and carries every row text', async () => {
  const svg = bandSvg(one({ title: 'a<b&"c' }), { width: 800, now: 0, animate: false })
  expect(svg.startsWith('<svg ')).toBe(true)
  expect(svg).toMatch(/viewBox="0 0 800 /)
  expect(svg).toContain('a&lt;b&amp;&quot;c')
  expect(svg).not.toContain('a<b')
  expect(svg).toContain('render frames 10/40')
  expect(svg).toContain('25% · 5:00')
})

test('each row adds height and an overflow adds a line', async () => {
  const height = (band: Band) => Number(bandSvg(band, { width: 800, now: 0, animate: false }).match(/height="([\d.]+)"/)?.[1])
  const two: Band = { rows: [RENDER_ROW, { ...RENDER_ROW, id: 'b2' }], more: 0 }
  expect(height(two)).toBeGreaterThan(height(one()))
  expect(height({ ...two, more: 2 })).toBeGreaterThan(height(two))
  expect(bandSvg({ ...two, more: 2 }, { width: 800, now: 0, animate: false })).toContain('+2 งาน')
})

test('the pill sits further right as the job gets further', async () => {
  const at = (ratio: number) => pillX(bandSvg(one({ ratio }), { width: 800, now: 0, animate: false }))
  expect(at(0.75)).toBeGreaterThan(at(0.25))
})

test('each kind has its own sprite', async () => {
  const render = sprite(bandSvg(one(), { width: 800, now: 0, animate: false }))
  const tts = sprite(bandSvg(one({ kind: 'tts' }), { width: 800, now: 0, animate: false }))
  expect(render).toBeDefined()
  expect(tts).toBeDefined()
  expect(render).not.toBe(tts)
})

test('animation only when asked; a count with no end slides its pill', async () => {
  const endless = one({ ratio: undefined, pill: 'fetch 12', kind: 'fetch' })
  delete endless.rows[0]!.ratio
  expect(bandSvg(endless, { width: 800, now: 0, animate: true })).toContain('<animateTransform')
  expect(bandSvg(endless, { width: 800, now: 0, animate: false })).not.toContain('<animate')
  expect(bandSvg(one(), { width: 800, now: 0, animate: true })).not.toContain('<animateTransform')
})

test('alt text reads each row and the overflow', async () => {
  expect(bandAlt({ rows: [RENDER_ROW], more: 1 })).toBe('asteroid-impact-plan: render frames 10/40, 25% · 5:00; +1 งาน')
})

test('the width follows the band and stays in bounds', async () => {
  expect(bandWidth(120)).toBe(960)
  expect(bandWidth(10)).toBe(360)
  expect(bandWidth(500)).toBe(1600)
})

test('the band draws running jobs as one picture on the desktop', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, 'b1', RENDER_CMD)
  const ui = await $.ui.mount({ plugin: 'mp-jobs', surface: 'desktop', component: 'AbovePrompt', props: BAND_PROPS })
  const svg = await ui.find({ type: 'Svg' })
  expect(svg).toBeDefined()
  expect(String(svg?.props.source)).toContain('asteroid-impact-plan')
  expect(String(svg?.props.source)).toContain('width="960"')
  expect(String(svg?.props.alt)).toContain('render')
  // The sandboxed frame reloads on every 2 s redraw and flickers: a still image does not.
  expect(svg?.props.isInteractive).not.toBe(true)
  expect(String(svg?.props.source)).not.toContain('<animate')
  // Without a size the desktop shrinks the drawing to its frame's default.
  expect(svg?.props.width).toBe(960)
  expect(svg?.props.height).toBe(Number(String(svg?.props.source).match(/height="([\d.]+)"/)?.[1]))
  await ui.unmount()
})

test('the band stays out of the way: nothing running, a survey, the terminal, only finished jobs', async ($, on) => {
  const h = harness(on)
  await h.start($)
  const mount = (surface: 'desktop' | 'terminal', hasSurvey = false) =>
    $.ui.mount({ plugin: 'mp-jobs', surface, component: 'AbovePrompt', props: { ...BAND_PROPS, hasSurvey } })
  const drawn = async (surface: 'desktop' | 'terminal', hasSurvey = false) => {
    const ui = await mount(surface, hasSurvey)
    const isOurs = (await ui.find({ type: 'Svg' })) !== undefined || (await ui.find({ text: /asteroid/ })) !== undefined
    const isEngine = (await ui.find({ text: /engine band/ })) !== undefined
    await ui.unmount()
    return isOurs ? 'ours' : isEngine ? 'engine' : 'nothing'
  }

  expect(await drawn('desktop')).toBe('engine')
  await h.background($, 'b1', RENDER_CMD)
  expect(await drawn('desktop')).toBe('ours')
  expect(await drawn('desktop', true)).toBe('engine')
  expect(await drawn('terminal')).toBe('engine')
  await h.notify($, 'b1', 'completed', 0)
  expect(await drawn('desktop')).toBe('engine')
})
