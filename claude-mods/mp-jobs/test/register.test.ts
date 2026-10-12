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
