import type { On } from 'claude-code'
import { mock } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

export const REPO = 'C:/Users/me/MoneyPrinterV2'
export const EP = `${REPO}/.mp/podcast_v2_galactic-habitable-zone_20261014_174337`
export const START = 1_000_000
export const PANE_PROPS = {
  title: 'บท',
  isFocused: false,
  bodyColumns: 41,
  placement: 'dock' as const,
  scroll: { offset: 0, bodyRows: 30 },
  view: {},
}

/** A narration draft as Producer Mode writes it: `json.dump(indent=1)` of `[i, section, text]` rows. */
export const draft = (texts: readonly string[]) => JSON.stringify(texts.map((t, i) => [i, `ตอน ${i + 1}`, t]), null, 1)

type File = { text: string; mtimeMs: number }

/** Answers, beneath the mod, every engine call it makes, from memory. */
export function harness(on: On) {
  const files = new Map<string, File>()
  const toasts: string[] = []
  const opened: string[] = []
  const commands: string[] = []
  const prompts: string[] = []
  const runs: (readonly string[])[] = []
  const clock = mock.clock(on, { now: START })
  // Every write lands later than the last, as on disk.
  let stamp = START + 1000

  const stat = (f: File) => ({ kind: 'file' as const, size: f.text.length, mtimeMs: f.mtimeMs, isLink: false })
  const key = (p: string) => p.replace(/\\/g, '/')
  const put = (path: string, text: string, mtimeMs = (stamp += 1000)) => void files.set(key(path), { text, mtimeMs })

  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: REPO }))
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
  on('ui.log', () => ({ value: undefined }))
  on('fs.read', (_$, e) => {
    const f = files.get(key(e.path))
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: f.text }
  })
  on('fs.stat', (_$, e) => {
    const f = files.get(key(e.path))
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: stat(f) }
  })
  on('fs.write', (_$, e) => {
    put(e.path, e.text)
    return { value: undefined }
  })
  on('fs.list', (_$, e) => {
    const dir = `${key(e.path)}/`
    const value = [...files]
      .filter(([p]) => p.startsWith(dir) && !p.slice(dir.length).includes('/'))
      .map(([p, f]) => ({ name: p.slice(dir.length), ...stat(f) }))
    return { value }
  })
  on('process.run', (_$, e) => {
    runs.push(e.argv)
    return { value: { exitCode: 0, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('prompt.submit', (_$, e) => {
    prompts.push(e.text)
    return { text: e.text }
  })
  on('tool.call', { tool: 'Write' }, (_$, e) => {
    put(e.file_path, e.content)
    return { result: { type: 'create', filePath: e.file_path, content: e.content, structuredPatch: [], originalFile: null }, text: 'ok' }
  })

  return {
    files,
    toasts,
    opened,
    commands,
    prompts,
    runs,
    put,
    read: (path: string) => files.get(key(path))?.text,
    start: ($: Engine) => $.session.start({ cwd: REPO, surface: 'terminal', isInteractive: true }),
    /** The model writing a file with the Write tool. */
    writeTool: ($: Engine, path: string, content: string) => $.tool.call({ tool: 'Write', file_path: path, content }),
    tick: async () => {
      await clock.advance(1500)
      await clock.settle()
    },
  }
}
