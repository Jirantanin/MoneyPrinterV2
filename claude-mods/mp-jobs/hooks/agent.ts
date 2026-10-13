import type { Job } from '../types'

const LABEL_MAX = 24
const LINE_MAX = 120

function cap(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

/** A subagent as a job: its id is the agent's, its label the description it was given. */
export function agentJob(id: string, description: string, subagentType: string, now: number): Job {
  return {
    id,
    kind: 'agent',
    label: cap(description.trim() || subagentType, LABEL_MAX),
    command: subagentType,
    logs: [],
    progress: { done: 0, unit: 'ขั้น' },
    startedAt: now,
    status: 'running',
    lastWriteAt: now,
  }
}

const text = (v: unknown) => (typeof v === 'string' && v.trim() !== '' ? v.trim() : undefined)

/** What one tool call of a subagent did, in a line. */
export function stepLine(e: { tool: string } & Record<string, unknown>): string {
  const description = text(e.description)
  const command = text(e.command)
  const path = text(e.file_path) ?? text(e.notebook_path) ?? text(e.path)
  const pattern = text(e.pattern)
  const line =
    e.tool === 'Bash' && (description ?? command) !== undefined
      ? (description ?? command!.split('\n')[0]!)
      : path !== undefined
        ? `${e.tool} ${path.split(/[\\/]/).at(-1)}`
        : pattern !== undefined
          ? `${e.tool} ${pattern}`
          : e.tool

  return cap(line, LINE_MAX)
}

/** Counts a step on the running agent `id`; the same list back when no job is that agent. */
export function agentStep(list: Job[], id: string, line: string, now: number): Job[] {
  if (!list.some(j => j.id === id && j.kind === 'agent' && j.status === 'running')) return list

  return list.map(j =>
    j.id === id && j.kind === 'agent' && j.status === 'running'
      ? { ...j, progress: { done: (j.progress?.done ?? 0) + 1, unit: 'ขั้น' }, lastLine: line, lastWriteAt: now }
      : j,
  )
}
