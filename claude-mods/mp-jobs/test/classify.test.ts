import { expect, test } from 'claude-code/testing'

import { classify, hostPath, logTargets, taskOutputPath } from '../hooks/classify'

const CWD = 'C:/Users/me/MoneyPrinterV2'
const EP_REL = '.mp/podcast_v2_asteroid-impact-plan_20261012_172530'
const EP = `${CWD}/${EP_REL}`
// The real background Bash text (spike finding (c)): the path is followed by more text on the same line.
const TASK_TEXT =
  'Command running in background with ID: b1x. Output is being written to: C:\\Users\\me\\AppData\\Local\\Temp\\claude\\tasks\\b1x.output. You will be notified when it completes. To check interim output, use Read on that file path.'

test('render-video is a render job on the plan episode', async () => {
  const c = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`, CWD)
  expect(c).toEqual({ kind: 'render', label: 'render', cwd: CWD, force: false, episodeDir: EP })
})

test('render-video --no-render is only preparation', async () => {
  const c = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json --no-render`, CWD)
  expect(c.kind).toBe('other')
  expect(c.label).toBe('render-video')
})

test('produce-tts keeps --force and --limit, and --dry-run is not tts', async () => {
  const c = classify(`python scripts/producer_mode.py produce-tts --plan ${EP_REL}/producer_plan.json --force --limit 5`, CWD)
  expect(c).toMatchObject({ kind: 'tts', force: true, limit: 5, episodeDir: EP })
  expect(classify(`python scripts/producer_mode.py produce-tts --plan ${EP_REL}/producer_plan.json --dry-run`, CWD).kind).toBe('other')
})

test('cd prefix with a Git Bash path', async () => {
  const c = classify(
    `cd /c/Users/me/MoneyPrinterV2 && python ${EP_REL}/fetch_official.py > ${EP_REL}/fetch_run2.log 2>&1`,
    'C:/elsewhere',
  )
  expect(c).toEqual({
    kind: 'fetch',
    label: 'fetch',
    cwd: CWD,
    force: false,
    episodeDir: EP,
    redirect: { path: `${EP}/fetch_run2.log`, appends: false },
  })
})

test('score render with tee -a appends to a shared log', async () => {
  const c = classify(`python scripts/producer_score.py render --episode ${EP_REL} | tee -a score.log`, CWD)
  expect(c).toMatchObject({ kind: 'score', label: 'score', episodeDir: EP, redirect: { path: `${CWD}/score.log`, appends: true } })
})

test('other job keeps the script name, Windows paths, and ignores /dev/null', async () => {
  const c = classify(
    'python scripts/build_timeline.py --plan "C:\\Users\\me\\MoneyPrinterV2\\.mp\\podcast_v2_x_20261012_172530\\producer_plan.json" > /dev/null',
    CWD,
  )
  expect(c).toEqual({
    kind: 'other',
    label: 'build_timeline.py',
    cwd: CWD,
    force: false,
    episodeDir: `${CWD}/.mp/podcast_v2_x_20261012_172530`,
  })
})

test('hostPath and taskOutputPath', async () => {
  expect(hostPath('/c/Users/me/a.log')).toBe('C:/Users/me/a.log')
  expect(hostPath('"C:\\x\\y.log"')).toBe('C:/x/y.log')
  expect(taskOutputPath(TASK_TEXT)).toBe('C:/Users/me/AppData/Local/Temp/claude/tasks/b1x.output')
  expect(taskOutputPath('ok')).toBeUndefined()
})

test('logTargets: render log is shared, task output and > targets start fresh', async () => {
  const render = classify(`python scripts/producer_mode.py render-video --plan ${EP_REL}/producer_plan.json`, CWD)
  expect(logTargets(render, 'C:/t/b1x.output')).toEqual([
    { path: `${EP}/producer_render.log`, isShared: true },
    { path: 'C:/t/b1x.output', isShared: false },
  ])
  const fetch = classify(`python ${EP_REL}/fetch_official.py > ${EP_REL}/f.log 2>&1`, CWD)
  expect(logTargets(fetch, 'C:/t/b2.output')).toEqual([{ path: `${EP}/f.log`, isShared: false }])
  expect(logTargets(classify('sleep 5', CWD), undefined)).toEqual([])
})
