import type { Paragraph } from '../types'

// Episode narration files Producer Mode writes, as JSON or as `[scene id] text` paragraphs;
// the mod's own `_nn` saves never count as a new draft.
const NARRATION = /^narration(?:_spoken)?_v(\d+)(?:_[a-z]+)?\.(json|txt)$/
const LABEL_KEYS = ['scene_title', 'section_title', 'title'] as const
const HEADING = /^##\s*\[(\d+)\]/
const SCENE = /^\[([^\]\r\n]+)\][ \t]*/

export const isDraft = (name: string) => NARRATION.test(name) && !/_nn\.(json|txt)$/.test(name)

/** The `[scene id] text` paragraphs of a text draft, split on blank lines. */
function sceneBlocks(text: string): { id: string; text: string }[] | undefined {
  const blocks = text.split(/\r?\n[ \t]*\r?\n/).map(b => b.trim()).filter(b => b !== '')
  if (blocks.length === 0) return undefined
  const out: { id: string; text: string }[] = []
  for (const b of blocks) {
    const m = SCENE.exec(b)
    if (m === null) return undefined
    out.push({ id: m[1]!, text: b.slice(m[0].length).replace(/\s+/g, ' ').trim() })
  }

  return out
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return undefined
  }
}

/** Where a paragraph's text sits in its entry: an array element or an object key. */
type Slot = number | string

function slotOf(entry: unknown): { slot: Slot; paragraph: Paragraph } | undefined {
  if (Array.isArray(entry)) {
    const at = entry.findLastIndex(v => typeof v === 'string')
    if (at < 0) return undefined
    const label = entry.filter((v, i) => i !== at && typeof v === 'string').join(' · ')

    return { slot: at, paragraph: { label, text: entry[at] as string } }
  }
  if (entry !== null && typeof entry === 'object' && typeof (entry as Record<string, unknown>).narration === 'string') {
    const o = entry as Record<string, unknown>
    const label = LABEL_KEYS.map(k => o[k]).find(v => typeof v === 'string') as string | undefined

    return { slot: 'narration', paragraph: { label: label ?? '', text: o.narration as string } }
  }

  return undefined
}

/** The paragraphs of a narration file: a list of `[.., title, text]` rows or `{ narration }` scenes, or `[scene id] text` paragraphs. */
export function parseNarration(json: string): Paragraph[] | undefined {
  const data = parseJson(json)
  if (data === undefined) return sceneBlocks(json)?.map(b => ({ label: b.id, text: b.text }))
  if (!Array.isArray(data) || data.length === 0) return undefined
  const out: Paragraph[] = []
  for (const entry of data) {
    const s = slotOf(entry)
    if (s === undefined) return undefined
    out.push(s.paragraph)
  }

  return out
}

/** The same file with each paragraph's text replaced, laid out as Python's `json.dump(indent=n)` laid it. */
export function withTexts(json: string, texts: readonly string[]): string {
  const parsed = parseJson(json)
  if (parsed === undefined) {
    const blocks = sceneBlocks(json)!

    return blocks.map((b, i) => `[${b.id}] ${texts[i]!}`).join('\n\n') + (json.endsWith('\n') ? '\n' : '')
  }
  const data = parsed as unknown[]
  const next = data.map((entry, i) => {
    const s = slotOf(entry)!
    const text = texts[i]!
    if (typeof s.slot === 'number') return (entry as unknown[]).map((v, j) => (j === s.slot ? text : v))

    return { ...(entry as Record<string, unknown>), [s.slot]: text }
  })
  const indent = /^[[{]\r?\n( +)/.exec(json)?.[1]?.length

  return JSON.stringify(next, null, indent) + (json.endsWith('\n') ? '\n' : '')
}

export function toMarkdown(file: string, paragraphs: readonly Paragraph[]): string {
  const head = `<!-- mp-script · ${file} · แก้ข้อความใต้หัวข้อได้เลย อย่าแตะบรรทัด ## [n] · เซฟแล้วดู diff ใน pane -->`
  const body = paragraphs.map((p, i) => `## [${i + 1}] ${p.label}`.trimEnd() + `\n\n${p.text}\n`)

  return [head, ...body].join('\n\n')
}

/** The texts under `## [1]`..`## [count]`, each once and in order; lines inside one paragraph join with a space. */
export function fromMarkdown(md: string, count: number): { texts: string[] } | { error: string } {
  const texts: (string | undefined)[] = []
  let at: number | undefined
  let lines: string[] = []
  const close = () => {
    if (at !== undefined) texts[at] = lines.join(' ').replace(/\s+/g, ' ').trim()
  }
  for (const line of md.split(/\r?\n/)) {
    const m = HEADING.exec(line)
    if (m === null) {
      if (at !== undefined && line.trim() !== '') lines.push(line.trim())
      continue
    }
    close()
    const n = Number(m[1])
    if (n < 1 || n > count) return { error: `หัวข้อ [${n}] เกินจำนวนย่อหน้า (${count})` }
    if (texts[n - 1] !== undefined) return { error: `หัวข้อ [${n}] ซ้ำ` }
    if (at !== undefined && n !== at + 2) return { error: `หัวข้อ [${n}] สลับลำดับ ต่อจาก [${at + 1}]` }
    at = n - 1
    lines = []
  }
  close()
  const missing = [...Array(count).keys()].filter(i => texts[i] === undefined).map(i => `[${i + 1}]`)
  if (missing.length > 0) return { error: `หัวข้อ ${missing.slice(0, 5).join(' ')} หาย` }

  return { texts: texts as string[] }
}

/** `narration_v<highest + 1>_nn.<ext>`: the next version, marked as นน's edit, in the format of the `edited` draft. */
export function nextEditName(names: readonly string[], edited = 'narration.json'): string {
  const top = Math.max(-1, ...names.map(n => Number(NARRATION.exec(n)?.[1] ?? -1)))
  const ext = edited.endsWith('.txt') ? 'txt' : 'json'

  return `narration_v${top + 1}_nn.${ext}`
}

/** Episode folder names a tool call mentions: `.mp/<name>` or a bare `podcast_v2_*` / `producer_cut_*`. */
export function episodeNames(text: string): string[] {
  const names = new Set<string>()
  for (const m of text.matchAll(/\.mp[\\/]+([^\\/\s"'`;|&<>()]+)/g)) names.add(m[1]!)
  for (const m of text.matchAll(/\b((?:podcast_v2|producer_cut)[_-][\w.-]+)/g)) names.add(m[1]!)

  // A file beside the folders (`.mp/youtube.json`) is no episode.
  return [...names].filter(n => !n.includes('.'))
}

export const episodeSlug = (dir: string) =>
  (dir.split(/[\\/]/).pop() ?? dir).replace(/^(?:podcast_v2|producer_cut)[_-]/, '').replace(/_\d{8}(?:_\d{4,6})?/, '')
