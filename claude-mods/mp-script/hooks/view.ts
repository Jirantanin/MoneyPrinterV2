import type { Review } from '../types'
import { changeCount, diffText } from './diff'

export type Summary = { changed: number[]; added: number; removed: number }

export function summary(r: Review): Summary {
  const changed: number[] = []
  let added = 0
  let removed = 0
  r.base.forEach((p, i) => {
    const text = r.texts[i] ?? p.text
    if (text === p.text) return
    changed.push(i)
    const c = changeCount(diffText(p.text, text))
    added += c.added
    removed += c.removed
  })

  return { changed, added, removed }
}

export function statusLine(r: Review, s: Summary): string {
  if (r.status === 'sent') return r.sentAs === undefined ? 'ส่งแล้ว: ไม่แก้' : `ส่งแล้วเป็น ${r.sentAs}`
  if (s.changed.length === 0) return 'ยังไม่ได้แก้'

  return `แก้ ${s.changed.length}/${r.base.length} ย่อหน้า · +${s.added} −${s.removed} ตัวอักษร`
}

// The prompt carries every changed paragraph whole; past this the rest are named only.
const MAX_PROMPT = 20_000

/** What the model reads when นน presses แก้เสร็จ: where the edits went, then each change as before/after. */
export function sentMessage(r: Review, savedAs: string, s: Summary): string {
  const head =
    `นนแก้บทเสร็จแล้ว: ${r.file} → ${savedAs} (แก้ ${s.changed.length}/${r.base.length} ย่อหน้า, +${s.added} −${s.removed} ตัวอักษร)\n` +
    `ไฟล์อยู่ที่ ${r.episodeDir}/${savedAs} ใช้ไฟล์นี้เป็นบทปัจจุบัน ห้ามเขียนทับคำที่นนแก้ ` +
    'เช็คว่าที่แก้กระทบ claim/source, ความยาวบท และคำอ่าน TTS ไหม แล้วบอกนนก่อนทำขั้นต่อไป'
  const parts = [head]
  let size = head.length
  const left: string[] = []
  for (const i of s.changed) {
    const p = r.base[i]!
    const block = `\n\n[${i + 1}] ${p.label}\n- เดิม: ${p.text}\n+ ใหม่: ${r.texts[i]}`
    if (size + block.length > MAX_PROMPT) {
      left.push(`[${i + 1}]`)
      continue
    }
    parts.push(block)
    size += block.length
  }
  if (left.length > 0) parts.push(`\n\nย่อหน้าที่แก้แต่ไม่ได้ยกมา (ยาวเกิน): ${left.join(' ')} ดูในไฟล์`)

  return parts.join('')
}
