import type { JobKind } from '../types'

export type Redirect = { path: string; appends: boolean }

export type Classified = {
  kind: JobKind
  label: string
  cwd: string
  episodeDir?: string
  redirect?: Redirect
  force: boolean
  limit?: number
}

export type LogTarget = { path: string; isShared: boolean }

const QUOTED = `"[^"]+"|'[^']+'`
const PRODUCER = /producer_mode\.py["']?\s+([\w-]+)/
const SCRIPT = /([\w.-]+\.(?:py|mjs|cjs|js|ps1))\b/

/** Git Bash `/c/Users/...` becomes `C:/Users/...`; quotes go; separators become `/`. */
export function hostPath(p: string): string {
  return p
    .replace(/^["']|["']$/g, '')
    .replace(/^\/([a-zA-Z])\//, (_m, drive: string) => `${drive.toUpperCase()}:/`)
    .replace(/\\/g, '/')
}

export function resolvePath(p: string, cwd: string): string {
  const host = hostPath(p)
  if (/^[A-Za-z]:\//.test(host) || host.startsWith('/')) return host

  return `${hostPath(cwd).replace(/\/+$/, '')}/${host.replace(/^\.\//, '')}`
}

function argValue(command: string, name: string): string | undefined {
  return command.match(new RegExp(`--${name}(?:\\s+|=)(${QUOTED}|[^\\s;&|]+)`))?.[1]
}

function parentDir(p: string): string {
  return p.replace(/\/[^/]*$/, '')
}

function episodeDirOf(command: string, cwd: string): string | undefined {
  const plan = argValue(command, 'plan')
  if (plan !== undefined) return parentDir(resolvePath(plan, cwd))
  const episode = argValue(command, 'episode')
  if (episode !== undefined) return resolvePath(episode, cwd).replace(/\/+$/, '')
  const script = command.match(/((?:[A-Za-z]:)?[^\s"']*\.mp[\\/][^\\/\s"']+)[\\/]/)?.[1]

  return script === undefined ? undefined : resolvePath(script, cwd)
}

function redirectOf(command: string, cwd: string): Redirect | undefined {
  const found: (Redirect & { at: number })[] = []
  for (const m of command.matchAll(new RegExp(`(?:^|[^0-9&>])(>>?)\\s*(${QUOTED}|[^\\s;&|<>]+)`, 'g'))) {
    found.push({ path: m[2]!, appends: m[1] === '>>', at: m.index ?? 0 })
  }
  for (const m of command.matchAll(new RegExp(`\\|\\s*tee\\s+(-a\\s+)?(${QUOTED}|[^\\s;&|<>]+)`, 'g'))) {
    found.push({ path: m[2]!, appends: m[1] !== undefined, at: m.index ?? 0 })
  }
  const last = found
    .filter(r => !/^(?:\/dev\/null|nul)$/i.test(r.path))
    .sort((a, b) => a.at - b.at)
    .at(-1)

  return last === undefined ? undefined : { path: resolvePath(last.path, cwd), appends: last.appends }
}

export function classify(rawCommand: string, sessionCwd: string): Classified {
  let command = rawCommand.trim()
  let cwd = hostPath(sessionCwd)
  const cd = command.match(new RegExp(`^cd\\s+(${QUOTED}|[^\\s;&|]+)\\s*(?:&&|;)\\s*`))
  if (cd) {
    cwd = resolvePath(cd[1]!, cwd)
    command = command.slice(cd[0].length)
  }
  const producer = command.match(PRODUCER)?.[1]
  const limit = argValue(command, 'limit')
  const episodeDir = episodeDirOf(command, cwd)
  const redirect = redirectOf(command, cwd)
  const kind: JobKind =
    producer === 'render-video' && !/--no-render\b/.test(command) ? 'render'
    : producer === 'produce-tts' && !/--dry-run\b/.test(command) ? 'tts'
    : producer === 'produce-assets' || /\b(?:fetch|search)_official\.py\b/.test(command) ? 'fetch'
    : /producer_score\.py["']?\s+render\b/.test(command) ? 'score'
    : 'other'
  const label =
    kind !== 'other' ? kind : (producer ?? command.match(SCRIPT)?.[1] ?? command.split(/\s+/)[0] ?? 'job').slice(0, 24)

  return {
    kind,
    label,
    cwd,
    force: /--force\b/.test(command),
    ...(limit !== undefined && /^\d+$/.test(limit) ? { limit: Number(limit) } : {}),
    ...(episodeDir !== undefined ? { episodeDir } : {}),
    ...(redirect !== undefined ? { redirect } : {}),
  }
}

/**
 * The task's output file, from the text the model reads for a background Bash call:
 * "... Output is being written to: <path>.output. You will be notified ...", all one line.
 */
export function taskOutputPath(resultText: string): string | undefined {
  const path = resultText.match(/Output is being written to:?\s*(.+?\.output)\b/)?.[1]

  return path === undefined ? undefined : hostPath(path)
}

export function logTargets(c: Classified, taskOutput: string | undefined): LogTarget[] {
  const targets: LogTarget[] = []
  if (c.kind === 'render' && c.episodeDir !== undefined) {
    targets.push({ path: `${c.episodeDir}/producer_render.log`, isShared: true })
  }
  if (c.redirect !== undefined) targets.push({ path: c.redirect.path, isShared: c.redirect.appends })
  else if (taskOutput !== undefined) targets.push({ path: taskOutput, isShared: false })

  return targets.filter((t, i) => targets.findIndex(o => o.path === t.path) === i)
}
