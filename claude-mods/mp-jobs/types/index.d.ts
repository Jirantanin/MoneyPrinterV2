export type JobKind = 'render' | 'tts' | 'fetch' | 'score' | 'agent' | 'other'

export type JobStatus = 'running' | 'done' | 'failed'

/** A log the ticker reads; `offset` in characters, `seenMtimeMs` the mtime last read. */
export type LogRef = { path: string; offset: number; seenMtimeMs: number }

/** `total` absent means a count with no end (fetch); `etaMs` only while estimable. */
export type Progress = { done: number; total?: number; unit: string; etaMs?: number }

export type Job = {
  id: string
  kind: JobKind
  label: string
  command: string
  episodeDir?: string
  logs: LogRef[]
  /** The harness's .output for a background task: its trailer says when it ended. */
  taskOutput?: string
  ttsTotal?: number
  startedAt: number
  status: JobStatus
  phase?: string
  progress?: Progress
  note?: string
  lastLine?: string
  lastWriteAt: number
  endedAt?: number
}

declare module 'claude-code' {
  interface PluginState {
    'mp-jobs': { jobs: Job[] }
  }
}
