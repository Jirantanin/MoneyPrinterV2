import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Review } from '../types'
import { diffText } from './diff'
import { episodeNames, episodeSlug, fromMarkdown, isDraft, nextEditName, parseNarration, toMarkdown, withTexts } from './narration'
import { sentMessage, statusLine, summary } from './view'

const PANE = 'mp-script'
const REPO = /^(.*?[\\/]MoneyPrinterV2)(?:[\\/]|$)/i
const MD = 'script_edit.md'
const TICK_MS = 1500
// Tools that can leave a new narration draft behind.
const WRITERS = new Set(['Bash', 'PowerShell', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'])

const review = atom({ plugin: 'mp-script', key: 'review' } as const, null)
const since = atom({ plugin: 'mp-script', key: 'since' } as const, 0)
const seen = atom({ plugin: 'mp-script', key: 'seen' } as const, {})
const view = atom({ plugin: 'mp-script', key: 'view' } as const, { showAll: false, editing: null })

let ticker: { cancel: () => void } | undefined
let isTicking = false
let hasHinted = false

const repoRoot = (cwd: string) => REPO.exec(cwd)?.[1]?.replace(/\\/g, '/')

async function openPane($: EngineInterface) {
  const opened = await $.ui.open({ id: PANE, title: 'บท' })
  if (!opened.isPlaced && !hasHinted) {
    hasHinted = true
    $.ui.toast('mp-script: พิมพ์ /script เพื่อเปิดหน้าแก้บท')
  }
}

async function openEditor($: EngineInterface, path: string) {
  // `code` is a .cmd shim on Windows: only cmd runs it.
  const argv = /^[A-Za-z]:/.test(path) ? ['cmd', '/c', 'code', '-r', path.replace(/\//g, '\\')] : ['code', '-r', path]
  const ran = await $.process.run(argv, { timeoutMs: 15_000 }).catch(() => undefined)
  if (ran === undefined || ran.exitCode !== 0) $.ui.toast(`เปิด VS Code ไม่ได้ · เปิดเองที่ ${path}`)
}

async function writeMd($: EngineInterface, r: Review, texts: readonly string[]): Promise<number> {
  await $.fs.write(r.mdPath, toMarkdown(r.file, r.base.map((p, i) => ({ label: p.label, text: texts[i]! }))))

  return (await $.fs.stat(r.mdPath)).mtimeMs
}

type Opened = 'opened' | 'busy'

/** Loads a draft into script_edit.md and the pane; `force` drops edits นน has not sent. */
async function startReview($: EngineInterface, dir: string, file: string, mtimeMs: number, force: boolean): Promise<Opened | undefined> {
  const path = `${dir}/${file}`
  await update($, seen, s => ({ ...s, [path]: mtimeMs }))
  const base = parseNarration((await $.fs.read(path)) as string)
  if (base === undefined) {
    $.ui.log(`mp-script: ${file} is no narration list; left alone`)
    return undefined
  }
  const cur = await read($, review)
  if (!force && cur !== null && cur.status === 'editing' && summary(cur).changed.length > 0) {
    await update($, review, r => (r === null ? r : { ...r, newer: file }))
    $.ui.toast(`มี ${file} มาใหม่ แต่นนยังแก้ ${cur.file} ค้างอยู่`)
    return 'busy'
  }
  const fresh: Review = {
    episodeDir: dir,
    file,
    mdPath: `${dir}/${MD}`,
    base,
    texts: base.map(p => p.text),
    mdMtimeMs: 0,
    status: 'editing',
  }
  fresh.mdMtimeMs = await writeMd($, fresh, fresh.texts)
  await update($, review, () => fresh)
  await update($, view, () => ({ showAll: true, editing: null }))
  await openPane($)
  await openEditor($, fresh.mdPath)

  return 'opened'
}

/** The newest draft in the named episodes written this session and not yet handled. */
async function newestDraft($: EngineInterface, root: string, names: readonly string[]) {
  const from = await read($, since)
  const handled = await read($, seen)
  let best: { dir: string; file: string; mtimeMs: number } | undefined
  for (const name of names) {
    const dir = `${root}/.mp/${name}`
    const entries = await $.fs.list(dir).catch(() => [])
    for (const f of entries) {
      if (f.kind !== 'file' || !isDraft(f.name) || f.mtimeMs < from) continue
      if (f.mtimeMs <= (handled[`${dir}/${f.name}`] ?? 0)) continue
      if (best === undefined || f.mtimeMs > best.mtimeMs) best = { dir, file: f.name, mtimeMs: f.mtimeMs }
    }
  }

  return best
}

/** Reads script_edit.md back when it changed on disk. */
async function syncMd($: EngineInterface) {
  const r = await read($, review)
  if (r === null || r.status !== 'editing') return
  const stat = await $.fs.stat(r.mdPath).catch(() => undefined)
  if (stat === undefined) {
    const error = `${MD} หาย · กด "ทิ้งที่แก้" เพื่อสร้างใหม่`
    if (r.error !== error) await update($, review, x => (x === null ? x : { ...x, error }))
    return
  }
  if (stat.mtimeMs === r.mdMtimeMs) return
  const parsed = fromMarkdown((await $.fs.read(r.mdPath)) as string, r.base.length)
  await update($, review, x => {
    if (x === null || x.mdPath !== r.mdPath) return x
    const { error: _, ...rest } = x

    return 'error' in parsed ? { ...x, mdMtimeMs: stat.mtimeMs, error: parsed.error } : { ...rest, mdMtimeMs: stat.mtimeMs, texts: parsed.texts }
  })
}

function ensureTicker($: EngineInterface) {
  if (ticker !== undefined) return
  ticker = $.clock.every(TICK_MS, () => {
    void tick($)
  })
}

async function tick($: EngineInterface) {
  if (isTicking) return
  isTicking = true
  try {
    await syncMd($)
  } catch (err) {
    $.ui.log(`mp-script: could not read ${MD}: ${String(err)}`)
  } finally {
    isTicking = false
  }
}

async function send($: EngineInterface) {
  await syncMd($)
  const r = await read($, review)
  if (r === null || r.status !== 'editing') return
  if (r.error !== undefined) {
    $.ui.toast(`ยังส่งไม่ได้: ${r.error}`)
    return
  }
  const s = summary(r)
  if (s.changed.length === 0) return skip($)
  const names = (await $.fs.list(r.episodeDir)).map(f => f.name)
  const savedAs = nextEditName(names)
  const json = (await $.fs.read(`${r.episodeDir}/${r.file}`)) as string
  await $.fs.write(`${r.episodeDir}/${savedAs}`, withTexts(json, r.texts))
  await update($, review, x => (x === null ? x : { ...x, status: 'sent' as const, sentAs: savedAs }))
  await update($, view, v => ({ ...v, editing: null }))
  await $.prompt.submit({ text: sentMessage(r, savedAs, s), asUser: true })
  $.ui.toast(`ส่งบทที่แก้แล้ว · ${savedAs}`)
}

async function skip($: EngineInterface) {
  const r = await read($, review)
  if (r === null || r.status !== 'editing') return
  await update($, review, x => (x === null ? x : { ...x, status: 'sent' as const }))
  await $.prompt.submit({ text: `นนอ่านบท ${r.file} แล้ว ไม่แก้ ไปต่อได้`, asUser: true })
}

async function discard($: EngineInterface) {
  const r = await read($, review)
  if (r === null) return
  const texts = r.base.map(p => p.text)
  const mdMtimeMs = await writeMd($, r, texts)
  await update($, review, x => {
    if (x === null) return x
    const { error: _, ...rest } = x

    return { ...rest, texts, mdMtimeMs }
  })
  await update($, view, v => ({ ...v, editing: null }))
}

async function quickEdit($: EngineInterface, i: number, value: string) {
  const r = await read($, review)
  if (r === null || r.status !== 'editing') return
  const texts = r.texts.map((t, j) => (j === i ? value.replace(/\s+/g, ' ').trim() : t))
  const mdMtimeMs = await writeMd($, r, texts)
  await update($, review, x => (x === null ? x : { ...x, texts, mdMtimeMs }))
  await update($, view, v => ({ ...v, editing: null }))
}

async function loadNewer($: EngineInterface) {
  const r = await read($, review)
  if (r?.newer === undefined) return
  const stat = await $.fs.stat(`${r.episodeDir}/${r.newer}`)
  await startReview($, r.episodeDir, r.newer, stat.mtimeMs, true)
}

/** For /script with nothing under review: the newest draft of the most recently touched episode. */
async function latestDraft($: EngineInterface, root: string) {
  const dirs = (await $.fs.list(`${root}/.mp`).catch(() => [])).filter(f => f.kind === 'dir' && episodeNames(f.name).length > 0)
  const stamped = await Promise.all(
    dirs.map(async d => ({ name: d.name, mtimeMs: (await $.fs.stat(`${root}/.mp/${d.name}`).catch(() => undefined))?.mtimeMs ?? 0 })),
  )
  for (const d of stamped.sort((a, b) => b.mtimeMs - a.mtimeMs).slice(0, 5)) {
    const dir = `${root}/.mp/${d.name}`
    const drafts = (await $.fs.list(dir).catch(() => [])).filter(f => f.kind === 'file' && isDraft(f.name))
    const top = drafts.sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
    if (top !== undefined) return { dir, file: top.name, mtimeMs: top.mtimeMs }
  }

  return undefined
}

function notice(outcome: Opened, file: string, r: Review | null): string {
  if (outcome === 'busy') {
    return (
      `mp-script: นน still has unsent edits to ${r?.file ?? 'the previous draft'} in the script pane, so ${file} was not loaded. ` +
      'Do not write more narration now: end this turn and wait for นน.'
    )
  }

  return (
    `mp-script: ${file} is open for นน to edit (${r?.mdPath ?? MD}, live diff in the บท pane). ` +
    'Stop here: end this turn now with a one-line note that the draft is ready for นน, and wait. ' +
    'นน presses "แก้เสร็จ" to send the edits back as a message (or "ไม่แก้ ไปต่อ"). ' +
    'Until then do not write another narration version or run TTS, assets or render.'
  )
}

export const register: Register = on => {
  ticker = undefined
  isTicking = false
  hasHinted = false

  on('session.start', async ($, e, next) => {
    if (repoRoot(e.cwd) !== undefined) {
      await $.command.register({ name: 'script', description: 'Open the narration editor pane for the latest MoneyPrinter draft' })
      if ((await read($, since)) === 0) {
        const now = await $.clock.now()
        await update($, since, () => now)
      }
      ensureTicker($)
    }

    return next(e)
  })

  on('command.run', { command: 'script' }, async $ => {
    if ((await read($, review)) === null) {
      const root = repoRoot(await $.session.cwd())
      const found = root === undefined ? undefined : await latestDraft($, root)
      if (found === undefined) return { text: 'ยังไม่มีไฟล์ narration_v*.json ในตอนไหนเลย' }
      await startReview($, found.dir, found.file, found.mtimeMs, false)

      return { text: `เปิด ${found.file} ให้แก้แล้ว` }
    }
    const opened = await $.ui.open({ id: PANE, title: 'บท' })

    return { text: opened.isPlaced ? 'เปิดหน้าแก้บทแล้ว' : `หน้าแก้บทรอที่ว่าง: ${opened.reason}` }
  })

  // After a tool that writes, look for a new narration draft in the episodes it named.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (!WRITERS.has(e.tool) || ran.deny !== undefined || ran.isError === true) return ran
    try {
      const cwd = await $.session.cwd()
      const root = repoRoot(cwd)
      if (root === undefined) return ran
      const r = await read($, review)
      const names = new Set(episodeNames(`${JSON.stringify(e)} ${cwd}`))
      if (r !== null) names.add(r.episodeDir.split('/').pop()!)
      const found = await newestDraft($, root, [...names])
      if (found === undefined) return ran
      const outcome = await startReview($, found.dir, found.file, found.mtimeMs, false)
      if (outcome === undefined) return ran

      return { ...ran, context: [...(ran.context ?? []), notice(outcome, found.file, await read($, review))] }
    } catch (err) {
      $.ui.log(`mp-script: could not check for a narration draft: ${String(err)}`)
      return ran
    }
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const elements = $.ui.resolve(e)
    const { Box, Text, Button } = elements
    // The mobile app draws no field: there the pane reads only.
    const Input = 'Input' in elements ? elements.Input : undefined
    const r = await read($, review)
    if (r === null) return <Text dimColor>ยังไม่มีบทให้แก้ · บทใหม่จะเปิดที่นี่เอง</Text>
    const v = await read($, view)
    const s = summary(r)
    const isEditing = r.status === 'editing'
    const showAll = v.showAll || s.changed.length === 0
    const shown = showAll ? r.base.map((_, i) => i) : s.changed

    const paragraph = (i: number) => {
      const p = r.base[i]!
      const text = r.texts[i] ?? p.text
      const isChanged = text !== p.text

      return (
        <Box key={`p${i}`} flexDirection="column" marginTop={1}>
          <Box flexDirection="row" gap={1}>
            <Text color={isChanged ? 'warning' : undefined} dimColor={!isChanged}>{`[${i + 1}] ${p.label}`}</Text>
            {isEditing && Input !== undefined && (
              <Button key={`edit:${i}`} plain dimColor label="แก้" onPress={() => void update($, view, x => ({ ...x, editing: x.editing === i ? null : i }))} />
            )}
          </Box>
          {isChanged ? (
            <Text>
              {diffText(p.text, text).map(d =>
                d.op === 'same' ? d.text : <Text color={d.op === 'add' ? 'success' : 'error'} strikethrough={d.op === 'del'} bold={d.op === 'add'}>{d.text}</Text>,
              )}
            </Text>
          ) : (
            <Text>{text}</Text>
          )}
          {isEditing && Input !== undefined && v.editing === i && (
            <Input key={`input:${i}`} value={text} autoFocus submitLabel="บันทึก" onSubmit={value => void quickEdit($, i, value)} />
          )}
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        <Text bold>{episodeSlug(r.episodeDir)}</Text>
        <Text dimColor>{isEditing ? `${r.file} → ${MD}` : r.file}</Text>
        <Text color={r.status === 'sent' ? 'success' : s.changed.length > 0 ? 'warning' : undefined}>{statusLine(r, s)}</Text>
        {r.error !== undefined && <Text color="error">{`⚠ ${r.error}`}</Text>}
        {r.newer !== undefined && isEditing && (
          <Box flexDirection="column">
            <Text color="warning">{`มี ${r.newer} มาใหม่ระหว่างที่นนแก้ค้าง`}</Text>
            <Button key="newer" label={`โหลด ${r.newer} (ทิ้งที่แก้)`} onPress={() => void loadNewer($)} />
          </Box>
        )}
        {isEditing && (
          <Box flexDirection="row" flexWrap="wrap" gap={1} marginTop={1}>
            <Button key="send" variant="primary" label="แก้เสร็จ" onPress={() => void send($)} />
            <Button key="code" label="เปิด VS Code" onPress={() => void openEditor($, r.mdPath)} />
            {s.changed.length === 0 && <Button key="skip" label="ไม่แก้ ไปต่อ" onPress={() => void skip($)} />}
            {s.changed.length > 0 && <Button key="discard" label="ทิ้งที่แก้" onPress={() => void discard($)} />}
          </Box>
        )}
        {s.changed.length > 0 && (
          <Button key="toggle" plain dimColor label={showAll ? 'ดูเฉพาะที่แก้' : 'ดูทั้งบท'} onPress={() => void update($, view, x => ({ ...x, showAll: !showAll }))} />
        )}
        {shown.map(paragraph)}
      </Box>
    )
  })
}
