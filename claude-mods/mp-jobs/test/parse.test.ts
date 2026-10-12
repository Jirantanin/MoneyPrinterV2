import type { FsEntry } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import {
  finishedTasks, lastLine, lines, parse, parseFetch, parseRender, parseScore,
  sceneCount, sliceNew, ttsDone, ttsTotal,
} from '../hooks/parse'

// Lines copied from .mp/podcast_v2_asteroid-impact-plan_20261012_172530/producer_render.log and fetch_run2.log, paths shortened.
const RENDER_OLD = 'chunk 38 done (40/40) 683s\nvideo ready C:\\x\\video.mp4 in 686s\n'
const RENDER_FRAMES = [
  '[2026-10-12T12:54:55+00:00] RUN ffmpeg -y -f concat -safe 0 -i C:\\x\\audio_concat.txt -c copy C:\\x\\merged_audio.wav',
  'RUN node C:\\x\\doc_renderer\\render.cjs --timeline C:\\x\\timeline.json',
  'frames 19946, chunks 40, todo 40, workers 8',
  '\x1b[1m\x1b[43m\x1b[30m',
  '  Puppeteer old Headless deprecation warning:\x1b[0m\x1b[33m',
  '    information, please see https://developer.chrome.com/articles/new-headless/.',
  'chunk 3 done (1/40) 123s',
  'chunk 21 done (23/40) 407s',
  '    If you encounter any bugs, please report them to https://github.com/puppeteer/puppeteer/issues/new/choose.\x1b[0m',
].join('\n')
const RENDER_MUX = `${RENDER_FRAMES}\nchunk 38 done (40/40) 683s\nvideo ready C:\\x\\video.mp4 in 686s\nRUN ffmpeg -y -v error -i C:\\x\\video.mp4 -i C:\\x\\merged_audio_with_sfx.wav C:\\x\\final_unnormalized.mp4`
const RENDER_FINALIZE =
  `${RENDER_MUX}\n` +
  'frame= 4367 fps=766 q=-1.0 size=  233472KiB time=00:02:48.68 bitrate=11338.5kbits/s speed=29.6x elapsed=0:00:05.70    \r' +
  'frame= 9973 fps=755 q=-1.0 size=  600000KiB time=00:06:39.00 bitrate=11338.5kbits/s speed=29.6x elapsed=0:00:13.00    '
const LATE_RUN = '\n[2026-10-12T13:07:01+00:00] RUN ffmpeg -y -i .mp\\x\\final_unnormalized.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 out.mp4'

const FETCH = [
  'nasa still GSFC_20240620_Asteroid_Threat_Briefing#frame1175 1920 1080',
  'nasa clip KSC-20211123-MH-AJW01-0001-SpaceX_DART_Isolated_Launch_Views_WON_3290675#t9 1280 720 30.0',
  'commons V01 C:Catalina Sky Survey Observatory at Dusk 1920 1280 CC BY-SA 4.0',
  'download failed: https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_source=commons.wikimedia.org',
  '  429 on https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_... waiting 60s',
  '  429 on https://upload.wikimedia.org/wikipedia/commons/d/d4/2013_Chelyabinsk_meteor_trace.jpg?utm_... waiting 240s',
].join('\n')

const NOTIFY = (id: string, status: string, summary: string) =>
  `<task-notification>\n<task-id>${id}</task-id>\n<tool-use-id>toolu_01</tool-use-id>\n` +
  `<output-file>C:\\t\\${id}.output</output-file>\n<status>${status}</status>\n<summary>${summary}</summary>\n</task-notification>`

const wav = (name: string, mtimeMs: number): FsEntry => ({ name, kind: 'file', size: 10, mtimeMs, isLink: false })

test('sliceNew keeps text after the offset and caps the region', async () => {
  expect(sliceNew('old\nnew', 4)).toBe('new')
  expect(sliceNew('x'.repeat(300_000), 0)).toHaveLength(262_144)
})

test('sliceNew reads a truncated file from the start', async () => {
  expect(sliceNew('short', 100)).toBe('short')
})

test('lines strips ANSI and splits on \\r; lastLine skips Puppeteer noise', async () => {
  const all = lines(RENDER_FRAMES)
  expect(all).toContain('frames 19946, chunks 40, todo 40, workers 8')
  expect(lastLine(all)).toBe('chunk 21 done (23/40) 407s')
})

test('render frames: chunks with ETA from the chunk seconds', async () => {
  expect(parseRender(RENDER_FRAMES)).toEqual({
    phase: 'frames',
    progress: { done: 23, total: 40, unit: 'chunk', etaMs: 300826 },
    lastLine: 'chunk 21 done (23/40) 407s',
  })
})

test('render audio, then mux after video ready', async () => {
  expect(parseRender(RENDER_FRAMES.split('\n')[0]!).phase).toBe('audio')
  const mux = parseRender(RENDER_MUX)
  expect(mux.phase).toBe('mux')
  expect(mux.progress).toBeUndefined()
})

test('render finalize counts frames against the frames header', async () => {
  expect(parseRender(RENDER_FINALIZE).progress).toEqual({ done: 9973, total: 19946, unit: 'fr', etaMs: 13000 })
})

test('a late RUN header does not reset finalize', async () => {
  const late = parseRender(RENDER_FINALIZE + LATE_RUN)
  expect(late.phase).toBe('finalize')
  expect(late.progress?.done).toBe(9973)
})

test('an older run before the offset cannot show as finished', async () => {
  const text = RENDER_OLD + RENDER_FRAMES.split('\n').slice(0, 3).join('\n')
  const parsed = parseRender(sliceNew(text, RENDER_OLD.length))
  expect(parsed.progress).toEqual({ done: 0, total: 40, unit: 'chunk' })
})

test('fetch counts assets and explains a trailing 429 wait', async () => {
  expect(parseFetch(FETCH)).toMatchObject({ progress: { done: 3, unit: 'รายการ' }, note: 'รอ rate limit 240s (429)' })
  const resumed = parseFetch(`${FETCH}\nnasa V24 iss040e091231 1920 1277`)
  expect(resumed.note).toBeUndefined()
  expect(resumed.progress?.done).toBe(4)
})

test('score: pad blocks, then later phases drop the bar', async () => {
  expect(parseScore('pad + drone\n\r  pad block 1/80\r  pad block 34/80')).toMatchObject({
    phase: 'pad',
    progress: { done: 34, total: 80, unit: 'block' },
  })
  const air = parseScore('pad + drone\n\r  pad block 80/80\nair / events')
  expect(air.phase).toBe('air')
  expect(air.progress).toBeUndefined()
})

test('parse for other kinds keeps only the last line', async () => {
  expect(parse('other', '[OK] wrote a\n[OK] wrote b\n')).toEqual({ lastLine: '[OK] wrote b' })
  expect(parse('tts', '')).toEqual({})
})

test('TTS totals and done counts', async () => {
  const existing = Array.from({ length: 10 }, (_, i) => wav(`scene_${String(i).padStart(2, '0')}.wav`, 500))
  expect(sceneCount('\uFEFF[{},{},{}]')).toBe(3)
  expect(sceneCount('not json')).toBe(0)
  expect(ttsTotal(36, existing, { force: false })).toBe(26)
  expect(ttsTotal(36, existing, { force: true })).toBe(36)
  expect(ttsTotal(36, existing, { force: false, limit: 12 })).toBe(2)
  expect(ttsDone([...existing, wav('scene_10.wav', 2000), wav('notes.txt', 2000)], 1000)).toBe(1)
})

test('finishedTasks reads every block, failure by status or exit code', async () => {
  const text = [
    NOTIFY('b1', 'completed', 'Background command "render" completed (exit code 0)'),
    NOTIFY('b2', 'failed', 'Background command "tts" failed with exit code 1'),
    NOTIFY('b3', 'completed', 'Background command "x" completed (exit code 2)'),
  ].join('\n')
  expect(finishedTasks(text)).toEqual([
    { id: 'b1', isFailed: false, summary: 'Background command "render" completed (exit code 0)' },
    { id: 'b2', isFailed: true, summary: 'Background command "tts" failed with exit code 1' },
    { id: 'b3', isFailed: true, summary: 'Background command "x" completed (exit code 2)' },
  ])
  expect(finishedTasks('hello')).toEqual([])
})
