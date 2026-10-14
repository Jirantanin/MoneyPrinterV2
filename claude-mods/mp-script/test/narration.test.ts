import { expect, test } from 'claude-code/testing'

import { diffText } from '../hooks/diff'
import { episodeNames, fromMarkdown, isDraft, nextEditName, parseNarration, toMarkdown, withTexts } from '../hooks/narration'
import { draft } from './harness'

test('reads [i, section, text] rows, [title, text] rows and { narration } scenes', async () => {
  expect(parseNarration(draft(['ก', 'ข']))).toEqual([
    { label: 'ตอน 1', text: 'ก' },
    { label: 'ตอน 2', text: 'ข' },
  ])
  expect(parseNarration('[["เปิด", "ปลายปี 2024"]]')).toEqual([{ label: 'เปิด', text: 'ปลายปี 2024' }])
  expect(parseNarration('[{"scene_title": "หัว", "narration": "เนื้อ", "image_prompt": "x"}]')).toEqual([
    { label: 'หัว', text: 'เนื้อ' },
  ])
  expect(parseNarration('{"revisions": []}')).toBeUndefined()
  expect(parseNarration('[[1, 2]]')).toBeUndefined()
})

test('writes the texts back in the layout the file had', async () => {
  const json = draft(['ก', 'ข'])
  const out = withTexts(json, ['ก', 'ขค'])
  expect(out).toBe(draft(['ก', 'ขค']))
  const scenes = '[{"scene_title": "หัว", "narration": "เนื้อ", "visual_beat": 1}]'
  expect(JSON.parse(withTexts(scenes, ['ใหม่']))).toEqual([{ scene_title: 'หัว', narration: 'ใหม่', visual_beat: 1 }])
})

test('markdown round-trips and joins wrapped lines', async () => {
  const paras = [
    { label: 'เปิด', text: 'ใต้ทะเลแปซิฟิก' },
    { label: '', text: 'เหล็กหกสิบ' },
  ]
  const md = toMarkdown('narration_v5.json', paras)
  expect(fromMarkdown(md, 2)).toEqual({ texts: ['ใต้ทะเลแปซิฟิก', 'เหล็กหกสิบ'] })
  const wrapped = md.replace('ใต้ทะเลแปซิฟิก', 'ใต้ทะเล\nแปซิฟิก')
  expect(fromMarkdown(wrapped, 2)).toEqual({ texts: ['ใต้ทะเล แปซิฟิก', 'เหล็กหกสิบ'] })
})

test('a heading lost, doubled or past the count is an error', async () => {
  expect(fromMarkdown('## [1] a\n\nx\n', 2)).toEqual({ error: 'หัวข้อ [2] หาย' })
  expect(fromMarkdown('## [1] a\n\nx\n\n## [1] a\n\ny\n', 2)).toEqual({ error: 'หัวข้อ [1] ซ้ำ' })
  expect(fromMarkdown('## [1] a\n\nx\n\n## [3] a\n\ny\n', 2)).toEqual({ error: 'หัวข้อ [3] เกินจำนวนย่อหน้า (2)' })
})

test('names: drafts, the next _nn version and episode folders', async () => {
  expect(['narration_v0.json', 'narration_v2_links.json', 'narration_spoken_v1.json'].every(isDraft)).toBe(true)
  expect(['narration_v6_nn.json', 'narration_revisions_v2.json', 'script.json'].some(isDraft)).toBe(false)
  expect(nextEditName(['narration_v0.json', 'narration_v5.json', 'narration_v2_links.json', 'x.json'])).toBe('narration_v6_nn.json')
  expect(nextEditName(['narration_v6_nn.json'])).toBe('narration_v7_nn.json')
  expect(episodeNames('python x.py --plan .mp/podcast_v2_a_20261014_174337/producer_plan.json')).toEqual(['podcast_v2_a_20261014_174337'])
  expect(episodeNames('{"file_path":"C:\\\\r\\\\.mp\\\\podcast_v2-b_20260715\\\\n.json"}')).toEqual(['podcast_v2-b_20260715'])
  expect(episodeNames('cat .mp/youtube.json')).toEqual([])
})

test('the diff keeps both sides whole', async () => {
  const a = 'นักวิทยาศาสตร์เจอเหล็กชนิดหนึ่ง ชื่อเหล็ก-60 ซึ่งโลกสร้างขึ้นเองไม่ได้'
  const b = 'นักวิทยาศาสตร์เจอเหล็กชนิดหนึ่ง ชื่อเหล็กหกสิบ เหล็กแบบนี้ โลกสร้างเองไม่ได้'
  const d = diffText(a, b)
  expect(d.filter(s => s.op !== 'add').map(s => s.text).join('')).toBe(a)
  expect(d.filter(s => s.op !== 'del').map(s => s.text).join('')).toBe(b)
  expect(d[0]).toEqual({ op: 'same', text: expect.stringContaining('นักวิทยาศาสตร์') })
  expect(diffText('ก', 'ก')).toEqual([{ op: 'same', text: 'ก' }])
})
