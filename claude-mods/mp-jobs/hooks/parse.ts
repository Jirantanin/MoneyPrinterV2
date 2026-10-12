import type { FsEntry } from 'claude-code'

import type { JobKind, Progress } from '../types'

export type Parsed = { phase?: string; progress?: Progress; note?: string; lastLine?: string }

export type Finished = { id: string; isFailed: boolean; summary?: string }

const MAX_REGION = 262_144
const ANSI = /\x1b\[[0-9;]*[A-Za-z]/g
const NOISE =
  /puppeteer|headless|developer\.chrome\.com|^(?:metadata|handler_name|vendor_id|encoder|compatible_brands|major_brand|minor_version|side data|icc profile)\b/i
const ASSET = /^[a-z]+ \S+ .+ \d{2,5} \d{2,5}\b/
const WAV = /^scene_(\d+)\.wav$/

function compact(p: Parsed): Parsed {
  return Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined)) as Parsed
}

function eta(elapsedMs: number, done: number, total: number): number | undefined {
  return done > 0 ? Math.round((elapsedMs * (total - done)) / done) : undefined
}

function withEta(p: Progress, etaMs: number | undefined): Progress {
  return etaMs === undefined ? p : { ...p, etaMs }
}

/** The text written since `offset`; a file shorter than its offset was truncated, so all of it. */
export function sliceNew(text: string, offset: number): string {
  const fresh = text.length < offset ? text : text.slice(offset)

  return fresh.length > MAX_REGION ? fresh.slice(-MAX_REGION) : fresh
}

export function lines(text: string): string[] {
  return text
    .replace(ANSI, '')
    .split(/\r\n|\r|\n/)
    .map(l => l.trimEnd())
    .filter(l => l.trim() !== '')
}

export function lastLine(all: readonly string[]): string | undefined {
  for (let i = all.length - 1; i >= 0; i -= 1) {
    const line = all[i]!.trim()
    if (!NOISE.test(line)) return line.length > 200 ? `${line.slice(0, 199)}…` : line
  }

  return undefined
}

/**
 * Reads producer_render.log in order. Phase never relies on RUN lines alone:
 * producer_renderer._run_subprocess writes its RUN header after the command's own output.
 */
export function parseRender(text: string): Parsed {
  const all = lines(text)
  let phase: string | undefined
  let progress: Progress | undefined
  let frames = 0
  for (const line of all) {
    let m: RegExpMatchArray | null
    if (/\bRUN\b.*render\.cjs/.test(line)) {
      phase = 'frames'
      progress = undefined
    } else if ((m = line.match(/^frames (\d+), chunks \d+, todo (\d+)/))) {
      frames = Number(m[1])
      phase = 'frames'
      progress = { done: 0, total: Number(m[2]), unit: 'chunk' }
    } else if ((m = line.match(/^chunk \d+ done \((\d+)\/(\d+)\) (\d+)s/))) {
      const done = Number(m[1])
      const total = Number(m[2])
      phase = 'frames'
      progress = withEta({ done, total, unit: 'chunk' }, eta(Number(m[3]) * 1000, done, total))
    } else if (/^video ready /.test(line) || /\bRUN\b.*video\.mp4/.test(line)) {
      phase = 'mux'
      progress = undefined
    } else if ((m = line.match(/^frame=\s*(\d+).*elapsed=(\d+):(\d+):(\d+(?:\.\d+)?)/))) {
      const done = Number(m[1])
      const elapsedMs = (Number(m[2]) * 3600 + Number(m[3]) * 60 + Number(m[4])) * 1000
      phase = 'finalize'
      progress =
        frames > 0 ? withEta({ done, total: frames, unit: 'fr' }, eta(elapsedMs, done, frames)) : { done, unit: 'fr' }
    } else if (/\bRUN\b.*(?:audio_concat|merged_audio)/.test(line)) {
      phase = 'audio'
      progress = undefined
    }
  }

  return compact({ phase, progress, lastLine: lastLine(all) })
}

export function parseFetch(text: string): Parsed {
  const all = lines(text)
  const count = all.filter(l => ASSET.test(l)).length
  const wait = all.at(-1)?.match(/429 on .*waiting (\d+)s/)

  return compact({
    progress: count > 0 ? { done: count, unit: 'รายการ' } : undefined,
    note: wait ? `รอ rate limit ${wait[1]}s (429)` : undefined,
    lastLine: lastLine(all),
  })
}

export function parseScore(text: string): Parsed {
  const all = lines(text)
  let phase: string | undefined
  let progress: Progress | undefined
  for (const line of all) {
    const t = line.trim()
    const block = t.match(/^pad block (\d+)\/(\d+)$/)
    if (t === 'pad + drone') {
      phase = 'pad'
      progress = undefined
    } else if (block) {
      phase = 'pad'
      progress = { done: Number(block[1]), total: Number(block[2]), unit: 'block' }
    } else if (t === 'air / events') {
      phase = 'air'
      progress = undefined
    } else if (t === 'reverb') {
      phase = 'reverb'
      progress = undefined
    }
  }

  return compact({ phase, progress, lastLine: lastLine(all) })
}

export function parse(kind: JobKind, text: string): Parsed {
  if (kind === 'render') return parseRender(text)
  if (kind === 'fetch') return parseFetch(text)
  if (kind === 'score') return parseScore(text)

  return compact({ lastLine: lastLine(lines(text)) })
}

export function sceneCount(scriptJson: string): number {
  try {
    const parsed: unknown = JSON.parse(scriptJson.replace(/^﻿/, ''))

    return Array.isArray(parsed) ? parsed.length : 0
  } catch {
    return 0
  }
}

/** Scenes this run writes: producer_tts.py skips an existing wav unless --force. */
export function ttsTotal(scenes: number, entries: readonly FsEntry[], c: { force: boolean; limit?: number }): number {
  const n = c.limit === undefined ? scenes : Math.min(c.limit, scenes)
  if (c.force) return n
  const existing = entries.filter(f => {
    const m = f.name.match(WAV)

    return m !== null && Number(m[1]) < n
  }).length

  return Math.max(0, n - existing)
}

export function ttsDone(entries: readonly FsEntry[], startedAt: number): number {
  return entries.filter(f => WAV.test(f.name) && f.mtimeMs >= startedAt).length
}

export function finishedTasks(text: string): Finished[] {
  const found: Finished[] = []
  for (const block of text.matchAll(/<task-notification>([\s\S]*?)<\/task-notification>/g)) {
    const body = block[1]!
    const id = body.match(/<task-id>\s*([^<\s]+)\s*<\/task-id>/)?.[1]
    const status = body.match(/<status>\s*([^<\s]+)\s*<\/status>/)?.[1]
    if (id === undefined || status === undefined) continue
    const summary = body.match(/<summary>([\s\S]*?)<\/summary>/)?.[1]?.trim()
    const code = summary?.match(/exit code (\d+)/)?.[1]
    const isFailed = status !== 'completed' || (code !== undefined && code !== '0')
    found.push(summary === undefined ? { id, isFailed } : { id, isFailed, summary })
  }

  return found
}
