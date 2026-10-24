import { expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { EP, PANE_PROPS, START, draft, harness } from './harness'

const SURFACES = ['terminal', 'desktop'] as const
const MD = `${EP}/script_edit.md`
const TEXTS = ['ใต้ทะเลแปซิฟิก มีเปลือกหินสีดำ', 'เหล็กชนิดนี้ โลกสร้างเองไม่ได้']
const mount = ($: Engine, surface: (typeof SURFACES)[number]) =>
  $.ui.mount({ plugin: 'mp-script', surface, component: 'Pane', requestId: 'mp-script', props: PANE_PROPS })

test('a new draft opens the pane and VS Code, and tells the model to stop', async ($, on) => {
  const h = harness(on)
  await h.start($)
  expect(h.commands).toEqual(['script'])
  const ran = await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  expect(h.opened).toEqual(['mp-script'])
  expect(h.read(MD)).toContain('## [1] ตอน 1\n\nใต้ทะเลแปซิฟิก มีเปลือกหินสีดำ')
  expect(h.runs.at(-1)?.slice(0, 4)).toEqual(['cmd', '/c', 'code', '-r'])
  expect(ran.context?.at(-1)).toMatch(/Stop here/)
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /^galactic-habitable-zone$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'ยังไม่ได้แก้' })).toBeDefined()
    expect(await ui.find({ key: 'skip' })).toBeDefined()
    await ui.unmount()
  }
})

test('files older than the session, and other files, are left alone', async ($, on) => {
  const h = harness(on)
  h.put(`${EP}/narration_v0.json`, draft(TEXTS), START - 1)
  await h.start($)
  const ran = await h.writeTool($, `${EP}/notes.json`, '{}')
  expect(ran.context).toBeUndefined()
  expect(h.opened).toEqual([])
  expect(h.read(MD)).toBeUndefined()
})

test('a read-only Bash call opens no draft, however old', async ($, on) => {
  const h = harness(on)
  h.put(`${EP}/narration_v2.json`, draft(TEXTS), START / 4)
  h.put(`${EP}/narration_v4.json`, draft(TEXTS), START / 2)
  await h.start($)
  // Written after the session started, but by no tool call of it.
  h.put(`${EP}/narration_v7.json`, draft(TEXTS))
  for (const command of [`ls ${EP}`, `python -c "import json; json.load(open('${EP}/narration_v7.json'))"`, `ls .mp/${EP.split('/').pop()}`]) {
    const ran = await h.bashTool($, command)
    expect(ran.context).toBeUndefined()
  }
  expect(h.opened).toEqual([])
  expect(h.runs).toEqual([])
  expect(h.read(MD)).toBeUndefined()
})

test('drafts from before the session stay closed when the session started outside the repo', async ($, on) => {
  const h = harness(on)
  h.put(`${EP}/narration_v6.json`, draft(TEXTS), START / 2)
  await $.session.start({ cwd: 'C:/Users/me', surface: 'terminal', isInteractive: true })
  const read = await h.bashTool($, `cat ${EP}/narration_v6.json`)
  expect(read.context).toBeUndefined()
  expect(h.read(MD)).toBeUndefined()
  // A draft the command writes still opens.
  const wrote = await h.bashTool($, `python draft.py ${EP}`, () => h.put(`${EP}/narration_v8.json`, draft(['ใหม่', 'ใหม่'])))
  expect(wrote.context?.at(-1)).toMatch(/narration_v8\.json is open/)
  expect(h.read(MD)).toContain('## [1] ตอน 1\n\nใหม่')
})

test('edits in script_edit.md show as a diff and send back as a new _nn version', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  h.put(MD, h.read(MD)!.replace('โลกสร้างเองไม่ได้', 'โลกเราสร้างเองไม่ได้'))
  await h.tick()
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /^แก้ 1\/2 ย่อหน้า · \+3 −0/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'เรา' })).toBeDefined()
    await ui.unmount()
  }
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'send' })
  const saved = h.read(`${EP}/narration_v1_nn.json`)
  expect(saved).toBe(draft([TEXTS[0]!, 'เหล็กชนิดนี้ โลกเราสร้างเองไม่ได้']))
  expect(h.prompts.at(-1)).toMatch(/narration_v0\.json → narration_v1_nn\.json/)
  expect(h.prompts.at(-1)).toContain('- เดิม: เหล็กชนิดนี้ โลกสร้างเองไม่ได้\n+ ใหม่: เหล็กชนิดนี้ โลกเราสร้างเองไม่ได้')
  expect(await ui.find({ type: 'Text', text: 'ส่งแล้วเป็น narration_v1_nn.json' })).toBeDefined()
  expect(await ui.find({ key: 'send' })).toBeUndefined()
  // The mod's own save is no new draft.
  const again = await h.writeTool($, `${EP}/notes.json`, '{}')
  expect(again.context).toBeUndefined()
})

test('a broken heading blocks sending', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  h.put(MD, h.read(MD)!.replace('## [2] ตอน 2', 'ตอน 2'))
  await h.tick()
  const ui = await mount($, 'desktop')
  expect(await ui.find({ type: 'Text', text: '⚠ หัวข้อ [2] หาย' })).toBeDefined()
  await ui.press({ key: 'send' })
  expect(h.prompts).toEqual([])
  expect(h.toasts.at(-1)).toBe('ยังส่งไม่ได้: หัวข้อ [2] หาย')
})

test('a quick edit in the pane rewrites the paragraph in script_edit.md', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'edit:0' })
  await ui.input({ key: 'input:0', text: 'ใต้ทะเลแปซิฟิก  มีหินสีดำ ' })
  expect(h.read(MD)).toContain('## [1] ตอน 1\n\nใต้ทะเลแปซิฟิก มีหินสีดำ\n')
  expect(await ui.find({ type: 'Text', text: /^แก้ 1\/2 ย่อหน้า/ })).toBeDefined()
  expect(await ui.find({ key: 'input:0' })).toBeUndefined()
})

test('no edits: "ไม่แก้ ไปต่อ" tells the model to go on', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'skip' })
  expect(h.prompts).toEqual(['นนอ่านบท narration_v0.json แล้ว ไม่แก้ ไปต่อได้'])
  expect(await ui.find({ type: 'Text', text: 'ส่งแล้ว: ไม่แก้' })).toBeDefined()
})

test('a newer draft does not overwrite unsent edits', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  h.put(MD, h.read(MD)!.replace('สีดำ', 'สีดำสนิท'))
  await h.tick()
  const ran = await h.writeTool($, `${EP}/narration_v1.json`, draft(['อื่น', 'อื่น']))
  expect(ran.context?.at(-1)).toMatch(/unsent edits to narration_v0\.json/)
  expect(h.read(MD)).toContain('สีดำสนิท')
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'newer' })
  expect(h.read(MD)).toContain('## [1] ตอน 1\n\nอื่น')
  expect(await ui.find({ type: 'Text', text: 'narration_v1.json → script_edit.md' })).toBeDefined()
})

test('discard puts the draft back', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  h.put(MD, h.read(MD)!.replace('สีดำ', 'สีแดง'))
  await h.tick()
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'discard' })
  expect(h.read(MD)).toContain('มีเปลือกหินสีดำ')
  expect(await ui.find({ type: 'Text', text: 'ยังไม่ได้แก้' })).toBeDefined()
})

test('a small fix of an approved draft is reported, not reopened', async ($, on) => {
  const h = harness(on)
  await h.start($)
  await h.writeTool($, `${EP}/narration_v0.json`, draft(TEXTS))
  const ui = await mount($, 'desktop')
  await ui.press({ key: 'skip' })
  const before = h.opened.length
  const fixed = await h.writeTool($, `${EP}/narration_v1.json`, draft([TEXTS[0]!.replace('สีดำ', 'สีดํา'), TEXTS[1]!]))
  expect(fixed.context?.at(-1)).toMatch(/not reopened for review/)
  expect(h.opened.length).toBe(before)
  const rewrite = await h.writeTool($, `${EP}/narration_v2.json`, draft(['บทใหม่ทั้งย่อหน้า ไม่ใช่แค่คำผิด', TEXTS[1]!]))
  expect(rewrite.context?.at(-1)).toMatch(/Stop here/)
})
