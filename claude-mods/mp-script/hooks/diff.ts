export type Segment = { op: 'same' | 'del' | 'add'; text: string }

// Thai vowels and tone marks that sit above or below their consonant: never split from it.
const COMBINING = /[ัิ-ฺ็-๎]/
// Past this many token pairs the table costs more than the paragraph is worth: show it replaced whole.
const MAX_CELLS = 250_000

function clusters(s: string): string[] {
  const out: string[] = []
  for (const ch of s) {
    if (out.length > 0 && COMBINING.test(ch)) out[out.length - 1] += ch
    else out.push(ch)
  }

  return out
}

/** Thai words where the runtime segments them, else consonant clusters. */
export function tokens(s: string): string[] {
  const Segmenter = (Intl as { Segmenter?: typeof Intl.Segmenter }).Segmenter
  if (Segmenter === undefined) return clusters(s)

  return [...new Segmenter('th', { granularity: 'word' }).segment(s)].map(x => x.segment)
}

function push(out: Segment[], op: Segment['op'], text: string) {
  const last = out[out.length - 1]
  if (last?.op === op) last.text += text
  else out.push({ op, text })
}

/** A word-level diff of two paragraphs, deletions before additions within each change. */
export function diffText(a: string, b: string): Segment[] {
  if (a === b) return a === '' ? [] : [{ op: 'same', text: a }]
  const x = tokens(a)
  const y = tokens(b)
  if (x.length * y.length > MAX_CELLS) {
    return [
      { op: 'del', text: a },
      { op: 'add', text: b },
    ]
  }
  // lcs[i][j]: the common length of x[i..] and y[j..].
  const lcs = Array.from({ length: x.length + 1 }, () => new Uint32Array(y.length + 1))
  for (let i = x.length - 1; i >= 0; i--) {
    for (let j = y.length - 1; j >= 0; j--) {
      lcs[i]![j] = x[i] === y[j] ? lcs[i + 1]![j + 1]! + 1 : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!)
    }
  }
  const out: Segment[] = []
  let del = ''
  let add = ''
  const flush = () => {
    if (del !== '') push(out, 'del', del)
    if (add !== '') push(out, 'add', add)
    del = add = ''
  }
  let i = 0
  let j = 0
  while (i < x.length || j < y.length) {
    if (i < x.length && j < y.length && x[i] === y[j]) {
      flush()
      push(out, 'same', x[i]!)
      i++
      j++
    } else if (j >= y.length || (i < x.length && lcs[i + 1]![j]! >= lcs[i]![j + 1]!)) {
      del += x[i++]
    } else {
      add += y[j++]
    }
  }
  flush()

  return out
}

/** Characters added and removed, spaces not counted. */
export function changeCount(segments: readonly Segment[]): { added: number; removed: number } {
  const len = (s: string) => [...s.replace(/\s/g, '')].length
  let added = 0
  let removed = 0
  for (const s of segments) {
    if (s.op === 'add') added += len(s.text)
    if (s.op === 'del') removed += len(s.text)
  }

  return { added, removed }
}
