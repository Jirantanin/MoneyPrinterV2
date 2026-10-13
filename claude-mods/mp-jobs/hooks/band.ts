import type { Job, JobKind } from '../types'
import { clock, episodeSlug, percent, silentFor, thousands } from './view'

export const BAND_ROWS = 3

/** `ratio` only when the job has a known end. */
export type BandRow = {
  id: string
  kind: JobKind
  title: string
  pill: string
  ratio?: number
  right: string
  isQuiet: boolean
}

export type Band = { rows: BandRow[]; more: number }

export type BandDraw = { width: number; now: number; animate: boolean }

const ROW_H = 32
const PAD = 0
const MORE_H = 18
const RIGHT_W = 100
const PX = 3
const SLIDE_S = 6
const FONT = 'Segoe UI, Leelawadee UI, Tahoma, sans-serif'

const COLORS: Record<JobKind | 'quiet', { fill: string; ink: string }> = {
  render: { fill: '#7F77DD', ink: '#26215C' },
  tts: { fill: '#5DCAA5', ink: '#04342C' },
  fetch: { fill: '#85B7EB', ink: '#042C53' },
  score: { fill: '#ED93B1', ink: '#4B1528' },
  other: { fill: '#B4B2A9', ink: '#2C2C2A' },
  quiet: { fill: '#EF9F27', ink: '#412402' },
}

// 8-wide pixel art: a clapperboard, a microphone, a download, two beamed notes, a critter.
const SPRITES: Record<JobKind, string[]> = {
  render: ['X.X.X.X.', 'XXXXXXXX', 'X......X', 'X......X', 'XXXXXXXX'],
  tts: ['..XXXX..', '.XXXXXX.', '.XXXXXX.', 'X.XXXX.X', 'X......X', '.XXXXXX.', '...XX...', '.XXXXXX.'],
  fetch: ['...XX...', '...XX...', '.XXXXXX.', '..XXXX..', '...XX...', 'X......X', 'XXXXXXXX'],
  score: ['..XXXXXX', '..X....X', '..X....X', 'XXX..XXX', 'XXX..XXX'],
  other: ['..X..X..', '.XXXXXX.', 'XX.XX.XX', 'XXXXXXXX', '.X.XX.X.', 'X......X'],
}

const STYLE =
  '.title{fill:#F1EFE8}.right{fill:#B4B2A9}.track{fill:#2C2C2A}' +
  '@media (prefers-color-scheme: light){.title{fill:#2C2C2A}.right{fill:#5F5E5A}.track{fill:#E8E6DF}}'

function cap(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, Math.max(1, max - 1))}…` : text
}

function pillText(job: Job): string {
  if (job.note !== undefined) return `${job.label} ${job.note}`
  const parts = [job.label]
  if (job.phase !== undefined) parts.push(job.phase)
  const p = job.progress
  if (p !== undefined) parts.push(p.total !== undefined ? `${thousands(p.done)}/${thousands(p.total)}` : thousands(p.done))

  return parts.join(' ')
}

export function bandRows(jobs: readonly Job[], now: number): Band {
  const running = jobs.filter(j => j.status === 'running').sort((a, b) => a.startedAt - b.startedAt)
  const rows = running.slice(0, BAND_ROWS).map((job): BandRow => {
    const quiet = silentFor(job, now)
    const p = job.progress
    const pct = p !== undefined ? percent(p) : undefined
    const eta = p?.etaMs !== undefined ? ` · ${clock(p.etaMs)}` : ''
    const right =
      quiet !== undefined ? `เงียบ ${clock(quiet)}` : pct !== undefined ? `${pct}%${eta}` : clock(now - job.startedAt)

    return {
      id: job.id,
      kind: job.kind,
      title: cap(job.episodeDir !== undefined ? episodeSlug(job.episodeDir) : job.label, 28),
      pill: cap(pillText(job), 34),
      ...(p?.total !== undefined && p.total > 0 ? { ratio: Math.min(1, p.done / p.total) } : {}),
      right,
      isQuiet: quiet !== undefined,
    }
  })

  return { rows, more: running.length - rows.length }
}

export function bandAlt(band: Band): string {
  const rows = band.rows.map(r => `${r.title}: ${r.pill}, ${r.right}`)
  if (band.more > 0) rows.push(`+${band.more} งาน`)

  return rows.join('; ')
}

/** The drawing's own width in CSS pixels, from the band's cells. */
export function bandWidth(columns: number): number {
  return Math.max(360, Math.min(1600, columns * 8))
}

const ENTITIES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

function esc(text: string): string {
  return text.replace(/[&<>"']/g, c => ENTITIES[c] ?? c)
}

const n = (v: number) => Math.round(v * 10) / 10

/** The same dots for a job on every redraw, so the trail does not shimmer by itself. */
function seeded(id: string): () => number {
  let s = 2166136261
  for (const ch of id) s = Math.imul(s ^ ch.charCodeAt(0), 16777619)

  return () => {
    s = (s + 0x6d2b79f5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t

    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** A dot-matrix tile, 8 dots by 3, each lit with the chance given. */
function tile(id: string, x: number, y: number, fill: string, chance: number, next: () => number): string {
  const dots: string[] = []
  for (let cy = 0; cy < 3; cy++)
    for (let cx = 0; cx < 8; cx++) if (next() < chance) dots.push(`<rect x="${cx * 4}" y="${cy * 4}" width="2.2" height="2.2"/>`)

  return `<pattern id="${id}" x="${n(x)}" y="${n(y)}" width="32" height="12" patternUnits="userSpaceOnUse"><g fill="${fill}">${dots.join('')}</g></pattern>`
}

function sprite(kind: JobKind, x: number, cy: number, fill: string): string {
  const art = SPRITES[kind]
  const top = cy - (art.length * PX) / 2
  const d = art
    .flatMap((line, row) => [...line].map((ch, col) => (ch === 'X' ? `M${n(x + col * PX)} ${n(top + row * PX)}h${PX}v${PX}h-${PX}z` : '')))
    .join('')

  return `<path class="sprite" d="${d}" fill="${fill}"/>`
}

/** Seconds into a looping animation at `now`, as a negative begin, so a redraw does not restart it. */
const phase = (now: number, seconds: number) => `-${((now / 1000) % seconds).toFixed(2)}s`

function row(r: BandRow, i: number, o: BandDraw, defs: string[]): string {
  const { fill, ink } = COLORS[r.isQuiet ? 'quiet' : r.kind]
  const titleW = Math.max(90, Math.min(230, o.width * 0.26))
  const top = PAD + i * ROW_H
  const mid = top + ROW_H / 2
  const trackX = 20 + titleW + 10
  const spriteX = o.width - 4 - 8 * PX
  const rightX = spriteX - 10 - RIGHT_W
  const trackW = Math.max(40, rightX - 12 - trackX)
  const trackY = mid - 10
  const dotsX = trackX + 6
  const dotsW = trackW - 12
  const next = seeded(r.id)
  const lit = r.ratio !== undefined ? dotsW * r.ratio : 0
  defs.push(tile(`d${i}`, dotsX, trackY + 4, fill, 0.55, next), tile(`s${i}`, dotsX, trackY + 4, fill, 0.12, next))

  const pillW = Math.min(trackW, r.pill.length * 7 + 24)
  // The pill leads the lit trail, so the dots behind it stay in view.
  const pillX = Math.min(trackX + trackW - pillW, dotsX + lit)
  const slide =
    r.ratio === undefined && o.animate
      ? `<animateTransform attributeName="transform" type="translate" values="0 0;${n(trackX + trackW - pillW - pillX)} 0;0 0" dur="${SLIDE_S}s" begin="${phase(o.now, SLIDE_S)}" repeatCount="indefinite"/>`
      : ''
  const twinkle = o.animate
    ? Array.from({ length: 5 }, (_, k) => {
        const x = dotsX + next() * (r.ratio !== undefined ? Math.max(8, lit) : dotsW)
        const y = trackY + 4 + Math.floor(next() * 3) * 4
        const dur = 1.2 + k * 0.5

        return `<rect x="${n(x)}" y="${y}" width="2.2" height="2.2" fill="${fill}"><animate attributeName="opacity" values="0.15;1;0.15" dur="${dur}s" begin="${phase(o.now, dur)}" repeatCount="indefinite"/></rect>`
      }).join('')
    : ''

  return (
    `<circle cx="8" cy="${mid}" r="5" fill="${fill}"/>` +
    `<text class="title" x="20" y="${mid + 4.5}" font-size="14" font-weight="600" fill="#F1EFE8">${esc(cap(r.title, Math.floor(titleW / 7.5)))}</text>` +
    `<rect class="track" x="${n(trackX)}" y="${trackY}" width="${n(trackW)}" height="20" rx="10" fill="#2C2C2A"/>` +
    (lit > 0 ? `<rect x="${n(dotsX)}" y="${trackY + 4}" width="${n(lit)}" height="12" fill="url(#d${i})"/>` : '') +
    `<rect x="${n(dotsX + lit)}" y="${trackY + 4}" width="${n(dotsW - lit)}" height="12" fill="url(#s${i})"/>` +
    twinkle +
    `<g><rect class="pill" x="${n(pillX)}" y="${trackY}" width="${n(pillW)}" height="20" rx="10" fill="${fill}"/>` +
    `<text x="${n(pillX + pillW / 2)}" y="${trackY + 14}" font-size="12" font-weight="600" text-anchor="middle" fill="${ink}">${esc(r.pill)}</text>${slide}</g>` +
    `<text class="right" x="${n(rightX)}" y="${mid + 4.5}" font-size="13" fill="#B4B2A9">${esc(r.right)}</text>` +
    sprite(r.kind, spriteX, mid, fill)
  )
}

/** The drawing's height in CSS pixels. */
export function bandHeight(band: Band): number {
  return PAD + band.rows.length * ROW_H + (band.more > 0 ? MORE_H : 0) + PAD
}

export function bandSvg(band: Band, o: BandDraw): string {
  const defs: string[] = []
  const rows = band.rows.map((r, i) => row(r, i, o, defs)).join('')
  const bottom = PAD + band.rows.length * ROW_H
  const height = bandHeight(band)
  const more =
    band.more > 0 ? `<text class="right" x="20" y="${bottom + 12}" font-size="12" fill="#B4B2A9">+${band.more} งาน · /jobs</text>` : ''

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${o.width}" height="${height}" viewBox="0 0 ${o.width} ${height}" font-family="${FONT}">` +
    `<style>${STYLE}</style><defs>${defs.join('')}</defs>` +
    rows +
    more +
    '</svg>'
  )
}
