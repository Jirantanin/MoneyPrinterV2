import type { On } from 'claude-code'
import { mock } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

export const REPO = 'C:/Users/me/MoneyPrinterV2'
export const EP_REL = '.mp/podcast_v2_asteroid-impact-plan_20261012_172530'
export const EP = `${REPO}/${EP_REL}`
export const RENDER_CMD = `python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`
export const START = 1_000_000
export const PANE_PROPS = {
  title: 'Jobs',
  isFocused: false,
  bodyColumns: 100,
  placement: 'dock' as const,
  scroll: { offset: 0, bodyRows: 30 },
  view: {},
}

type File = { text: string; mtimeMs: number }

const notification = (id: string, status: string, code: number) =>
  `<task-notification>\n<task-id>${id}</task-id>\n<status>${status}</status>\n` +
  `<summary>Background command "job" ${status} (exit code ${code})</summary>\n</task-notification>`

/** Answers, beneath the mod, every engine call it makes, from memory. */
export function harness(on: On, cwd = REPO) {
  const files = new Map<string, File>()
  const toasts: string[] = []
  const statuses: (string | undefined)[] = []
  const opened: string[] = []
  const commands: string[] = []
  const queue: (string | undefined)[] = []
  const clock = mock.clock(on, { now: START })

  const stat = (f: File) => ({ kind: 'file' as const, size: f.text.length, mtimeMs: f.mtimeMs, isLink: false })
  // The engine hands fs hooks OS-native paths (backslashes on Windows); key the fake files by one spelling.
  const key = (p: string) => p.replace(/\\/g, '/')

  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: cwd }))
  on('command.register', (_$, e) => {
    commands.push(e.name)
    return { value: { command: e.name } }
  })
  on('ui.open', (_$, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true as const } }
  })
  on('ui.toast', (_$, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', (_$, e) => {
    statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.log', () => ({ value: undefined }))
  on('fs.read', (_$, e) => {
    const f = files.get(key(e.path))
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: f.text }
  })
  on('fs.stat', (_$, e) => {
    const f = files.get(key(e.path))
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: stat(f) }
  })
  on('fs.list', (_$, e) => {
    const dir = `${key(e.path)}/`
    const value = [...files]
      .filter(([p]) => p.startsWith(dir) && !p.slice(dir.length).includes('/'))
      .map(([p, f]) => ({ name: p.slice(dir.length), ...stat(f) }))
    return { value }
  })
  on('tool.call', { tool: 'Bash' }, () => {
    const id = queue.shift()
    return id === undefined
      ? { result: { stdout: 'ok', stderr: '', interrupted: false }, text: 'ok' }
      : {
          result: { stdout: '', stderr: '', interrupted: false, backgroundTaskId: id },
          // The real text (spike finding (c)): the path is followed by more text on the same line.
          text:
            `Command running in background with ID: ${id}. Output is being written to: C:\\tmp\\tasks\\${id}.output. ` +
            'You will be notified when it completes. To check interim output, use Read on that file path.',
        }
  })
  on('prompt.submit', (_$, e) => ({ text: e.text }))

  return {
    files,
    toasts,
    statuses,
    opened,
    commands,
    clock,
    write: (path: string, text: string, mtimeMs: number) => void files.set(key(path), { text, mtimeMs }),
    append: (path: string, text: string, mtimeMs: number) =>
      void files.set(key(path), { text: (files.get(key(path))?.text ?? '') + text, mtimeMs }),
    start: ($: Engine) => $.session.start({ cwd, surface: 'terminal', isInteractive: true }),
    background: ($: Engine, id: string | undefined, command: string) => {
      queue.push(id)
      return $.tool.call({ tool: 'Bash', command, run_in_background: id !== undefined })
    },
    notify: ($: Engine, id: string, status: string, code: number) =>
      $.prompt.submit({ text: notification(id, status, code), wait: false, origin: { kind: 'task-notification' } }),
    tick: async () => {
      await clock.advance(2000)
      await clock.settle()
    },
  }
}
