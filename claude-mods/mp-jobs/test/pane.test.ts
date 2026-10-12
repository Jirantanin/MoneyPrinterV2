import { expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { EP_REL, PANE_PROPS, RENDER_CMD, harness } from './harness'

const SURFACES = ['terminal', 'desktop'] as const
const mount = ($: Engine, surface: (typeof SURFACES)[number], bodyColumns = PANE_PROPS.bodyColumns) =>
  $.ui.mount({ plugin: 'mp-jobs', surface, component: 'Pane', requestId: 'mp-jobs', props: { ...PANE_PROPS, bodyColumns } })

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

// The docked desktop pane measured 41 columns (spike finding (a)): truncating one long row would cut the ETA away.
test('a narrow pane puts the detail on its own line', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.background($, 'b1', RENDER_CMD)
  for (const surface of SURFACES) {
    const narrow = await mount($, surface, 41)
    expect(await narrow.find({ type: 'Text', text: /^ {2}0:00$/ })).toBeDefined()
    await narrow.unmount()
    const wide = await mount($, surface, 100)
    expect(await wide.find({ type: 'Text', text: /^ {2}0:00$/ })).toBeUndefined()
    expect(await wide.find({ type: 'Text', text: /^0:00$/ })).toBeDefined()
    await wide.unmount()
  }
})
