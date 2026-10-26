# Motion and Shape Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the explainer-graphics kit shared motion, camera, type, look and rigged-cast modules, a beat-sheet + contact-sheet workflow and word-level trigger timing, then make the docs and the Producer Mode skill point at them.

**Architecture:** New classic-script modules in `doc_renderer/gfx_kit/` (loaded by `<script>` like the existing kit, every frame a pure function of `t`), built on a kit copy of the `cast.js` layer system; old kit functions stay unchanged so finished episode pages re-record identically. Node tools (record, contact sheet) share one Chrome launcher; the word-timing helper is Python next to the existing speech tools.

**Tech Stack:** SVG + vanilla JS (browser globals), Node 16.13 + puppeteer-core 19.11.1 (`doc_renderer/node_modules`), ffmpeg, Python 3.12 + pytest + numpy + faster-whisper.

**Spec:** `docs/superpowers/specs/2026-10-26-motion-spec-design.md`

## Global Constraints

- Work on a branch `motion-spec`, never on `main`. The working tree has unrelated uncommitted changes (`src/youtube_upload.py`, `doc_renderer/gfx_kit/shorts.js`, …): stage only the paths each task names.
- Every frame is a pure function of `t`; no timers, no `Math.random` (seeded `rng()` only).
- Old pages must render unchanged: do not change the behaviour of `mascot()`, `planet()`, `sun()`, `stage()`, `camera()`, `pop()`, `bump()`, `Y_lit` in glow pages, `PAPER.font`, or anything in `.mp/podcast_v2_dinosaurs-never-died_*` or `.mp/podcast_v2_cosmic-year-humans_*`.
- Node is 16.13: no `node:test`; JS tests are plain scripts using `assert` that exit non-zero on failure, run by pytest.
- Thai text never gets `letter-spacing`; letter-spacing 3–6 px only on Latin caps.
- Type: Fredoka 600/700 for numbers and Latin, Mitr for Thai; teal `#8fd8e6`, gold `#ffd98a`, white `#ffffff`; pill `rgb(6,20,40)` at 0.62; lines rise 1.3x their height through a clip on ease-out-quint over 0.55 s; numbers slam 1.7x → 1x on a spring; on-screen text ≥ 34 px.
- Springs: peak energy damping 0.42–0.5 at about 2–2.5 Hz; calm about 0.7. Easing for camera moves easeInOutCubic (`eio`); zoom interpolated in log space.
- Shared cast identity (every look): จุก body `#3dd6c0`, dark `#1f9e90`, leaves `#8be05a` / `#a8f070` / `#4a9e3c`, stem `#4cb848`, eye whites `#ffffff`, pupils `#14103a`, two highlight dots, cheeks `#ff8aa6` fully opaque; reference drawing `.mp/channel_logo_20261021/jook.js`.
- Helpers นน runs are `.py`/`.bat`; tools มิ้ง runs may be Node.
- Do not download anything without นน's go-ahead in chat (Task 5 asks).

## Review Focus

1. A page that loads both `kit.js` and `paper.js` after `spring`/`kick` move: a duplicate top-level `const kick` is a SyntaxError that blanks every paper page — Task 1 tests `paper_demo.html` still loads.
2. Ticking numbers whose digit count changes (`10:00` → `9:59`, `15°C` → `−70°C`) must not jitter or overflow — Task 5 tests slot positions across the change.
3. A Thai trigger word Whisper splits, merges or mishears must still get a time or fall back to the phrase time, never a wrong confident time — Task 8 tests a misheard trigger.
4. A whip or dive recorded with motion blur must keep its first and last frames aligned with the unblurred record (no half-frame time shift) — Task 6 tests subframe times.
5. Re-recording a cosmic-year-humans world after the kit changes must produce the same pixels — Task 9 compares a still before and after.

---

### Task 1: Test harness, springs in the kit, motion helpers

**Files:**
- Create: `doc_renderer/gfx_kit/chrome.cjs` (Chrome finder + launcher, moved out of `record.cjs`)
- Modify: `doc_renderer/gfx_kit/record.cjs` (use `chrome.cjs`; no behaviour change)
- Modify: `doc_renderer/gfx_kit/kit.js` (add `spring`, `kick`)
- Modify: `doc_renderer/gfx_kit/paper.js:23-31` (remove `spring`, `kick`; header says they live in kit.js)
- Create: `doc_renderer/gfx_kit/motion.js`
- Create: `doc_renderer/gfx_kit/tests/harness.cjs`, `doc_renderer/gfx_kit/tests/fixture.html`, `doc_renderer/gfx_kit/tests/motion.test.cjs`
- Create: `tests/test_gfx_kit_js.py`

**Interfaces:**
- Produces (`chrome.cjs`): `findChrome() -> string`, `launch({gpu = process.env.PRODUCER_CHROME_GPU === '1'} = {}) -> Promise<{browser, cleanup()}>`.
- Produces (`harness.cjs`): `loadPure(files: string[], names: string[]) -> object` (runs the kit files in a `vm` context with no DOM and returns the named globals); `withPage(query: string, fn: (page) => Promise<void>, { url = 'tests/fixture.html' } = {}) -> Promise<void>` (opens `<url>?<query>` relative to `doc_renderer/gfx_kit/` at 1920x1080, fails on any `pageerror`, awaits `window.__ready`).
- Produces (`fixture.html`): loads `kit.js, library.js, finish.js, glow.js, paper.js, cast.js, flat.js, motion.js, cam.js, type.js, cast_rig.js` in that order, skipping files that do not exist yet (`onerror` resolves), then `?run=<name>` calls `window.FIXTURES[name]()`; sets `window.__ready`.
- Produces (`kit.js`): `spring(t, zeta = .7, hz = 2) -> number`, `kick(t, amp, decay = 5, hz = 3) -> number` (bodies moved verbatim from paper.js).
- Produces (`motion.js`):
  - `ENERGY = { peak: { zeta: .45, hz: 2.4 }, calm: { zeta: .7, hz: 2 } }`
  - `squash(k) -> [sx, sy]` with `sy = 1 + k`, `sx = 1 / (1 + k)` (k > 0 stretch, k < 0 squash)
  - `land(t, t0, { amp = .3, decay = 7, hz = 2.5 } = {}) -> number` squash amount after a landing at `t0`: 0 before, `-amp * exp(-decay*d) * cos(2π hz d)` after
  - `anticip(t, t0, dur, { back = .08, lead = .15, energy = 'peak' } = {}) -> number` progress: 0 before `t0 - lead`, dips to `-back` at `t0`, then `spring(t - t0, …ENERGY[energy])` scaled so it settles at 1 by `t0 + dur`
  - `enter(t, t0, kind, { energy = 'peak', from = [0, -320] } = {}) -> { s, sx, sy, dx, dy, o }` for `kind` `'pop' | 'drop' | 'slide'` (drop falls stretched `squash(.2)` then lands with `land`; slide comes from `from` with overshoot)
  - `leave(t, t1, dur = .25) -> number` 1 → 0 on ease-in cubic
  - `blinkOpen(t, seed, every = [3, 5]) -> number` eyelid 1 open … 0.1 closed for 0.13 s, blink times from `rng(seed)` spaced `every[0]..every[1]` s
  - `storyTime(t, keys) -> number` piecewise-linear map from ambient time to story time; `keys = [[ambientT, storyT], …]`; a falling segment is a rewind; before the first key returns `t - keys[0][0] + keys[0][1]`, after the last key continues at slope 1

- [ ] **Step 1: Write the failing tests** in `doc_renderer/gfx_kit/tests/motion.test.cjs`

```js
const { spring, kick } = loadPure(['kit.js'], ['spring', 'kick']);
assert.strictEqual(spring(0), 0); assert(Math.abs(spring(5) - 1) < 1e-3); assert(spring(.25, .45, 2.4) > 1);  // overshoots
const M = loadPure(['kit.js', 'motion.js'], ['squash', 'land', 'anticip', 'enter', 'leave', 'blinkOpen', 'storyTime', 'ENERGY']);
const [sx, sy] = M.squash(-.3); assert(Math.abs(sx * sy - 1) < 1e-9 && sy < 1 && sx > 1);
assert.strictEqual(M.land(1, 2), 0); assert(M.land(2.0, 2) < 0); assert(Math.abs(M.land(3, 2)) < .01);
assert(M.anticip(2, 2, .6) < -.07);                       // dipped back at t0
assert(Math.abs(M.anticip(2.6 + 2, 2, .6) - 1) < .01);   // settled
assert.strictEqual(M.leave(.9, 1), 1); assert.strictEqual(M.leave(1.25, 1), 0);
assert.deepStrictEqual([0, 1, 2].map(t => M.storyTime(t, [[0, 0], [1, 1], [1.8, .2]])).map(v => +v.toFixed(3)), [0, 1, .6]);
const closed = Array.from({ length: 2000 }, (_, i) => M.blinkOpen(i / 100, 7)).filter(v => v < .5).length;
assert(closed > 30 && closed < 120);                      // ~5 blinks of 0.13 s in 20 s
```

and `tests/test_gfx_kit_js.py`:

```python
@pytest.mark.parametrize("script", sorted((ROOT / "doc_renderer/gfx_kit/tests").glob("*.test.cjs")), ids=lambda p: p.name)
def test_gfx_kit_js(script):
    r = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
```

Also in `motion.test.cjs`: `withPage('g=night', …, { url: 'paper_demo.html' })` asserts no `pageerror` and `window.__ready` resolves (Review Focus 1).

- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -v` — Expected: FAIL (`motion.js` missing, `spring` not in kit.js).
- [ ] **Step 3: Implement** `chrome.cjs` (move `findChrome` and the launch args from `record.cjs`), switch `record.cjs` to it, move `spring`/`kick` into `kit.js` after `bump`, delete them from `paper.js`, write `motion.js`, `harness.cjs`, `fixture.html`.
- [ ] **Step 4: Run** `pytest tests/test_gfx_kit_js.py -v` — Expected: PASS. Also run `node doc_renderer/gfx_kit/record.cjs doc_renderer/gfx_kit/paper_demo.html night 1 <scratch>/p --stills 0.5` — Expected: `done`.
- [ ] **Step 5: Commit** `feat(gfx_kit): springs in the kit, motion helpers, JS test harness`

---

### Task 2: Kit base layers (`cast.js`) and the B flat look (`flat.js`)

**Files:**
- Create: `doc_renderer/gfx_kit/cast.js` (from `.mp/podcast_v2_dinosaurs-never-died_20261024_210648/graphics/glow/cast.js`, no `Y_dial`)
- Create: `doc_renderer/gfx_kit/flat.js` (from the same folder's `flat.js`, generalised)
- Create: `doc_renderer/gfx_kit/tests/look.test.cjs`

**Interfaces:**
- Consumes: `withPage` (Task 1).
- Produces (`cast.js`): the existing `Y`, `Y_init(look)`, `YP/YC/YE/YS`, `Y_lgrad`, `Y_rgrad`, `Y_clip`, `Y_clipTo`, `Y_blurF`, `Y_lit`, `Y_layer`, `Y_par`, `Y_pts`, `Y_blob`, `Y_ridge` with the same signatures; new `look.style: 'A' | 'B' | 'C' | 'D'` (default `'A'`); `Y_init` calls `FL_install()` when `style === 'B'`; `Y.look.style` is readable by later modules.
- Produces (`flat.js`): `FL_tone(c, light = '#ffffff', dark = '#140a30') -> {light, dark}`, `FL_rs(d, color, width, parent, extra)`, `FL_install()` which replaces `window.Y_lit` and `window.litDisc` with the flat versions (nothing is replaced at load time). Flat `Y_lit` defaults `dx = 6, dy = 5, band = .7, shade = 1.8` (shade crescent ≈ 7, 6 px per the spec).

- [ ] **Step 1: Write the failing test** `look.test.cjs` with fixtures in `fixture.html` (`FIXTURES.lookB`, `FIXTURES.lookA`): each calls `Y_init({style})` and draws `Y_lit(Y.cam, <rounded rect 200x120>, '#5fc47a')`.

```js
await withPage('run=lookB', async page => {
  const r = await page.evaluate(() => ({ paths: Y.cam.querySelectorAll('path').length, white: [...Y.cam.querySelectorAll('path')].some(p => p.getAttribute('fill') === Y.look.rim), style: Y.look.style }));
  assert.strictEqual(r.style, 'B'); assert.strictEqual(r.paths, 3); assert.strictEqual(r.white, false);   // band + shade + body, no rim colour
});
await withPage('run=lookA', async page => assert.strictEqual(await page.evaluate(() => Y.cam.querySelectorAll('path').length), 2));
```

- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k look -v` — Expected: FAIL.
- [ ] **Step 3: Implement** the two files; `flat.js` wraps its overrides in `FL_install()`.
- [ ] **Step 4: Run** the test — Expected: PASS; also confirm the dinosaurs page still records: `node doc_renderer/gfx_kit/record.cjs .mp/podcast_v2_dinosaurs-never-died_20261024_210648/graphics/glow/page.html "cold&f=w_cold.js" 1 <scratch>/d --stills .5` prints `done` (it loads its own copies).
- [ ] **Step 5: Commit** `feat(gfx_kit): kit cast.js base layers and the B flat look`

---

### Task 3: Camera module (`cam.js`)

**Files:**
- Create: `doc_renderer/gfx_kit/cam.js`
- Create: `doc_renderer/gfx_kit/tests/cam.test.cjs`

**Interfaces:**
- Consumes: `eio`, `spring`, `kick`, `rng` (kit.js), `ENERGY` (motion.js).
- Produces:
  - `camPath(keys, { shakes = [], drift = .015 } = {}) -> (t) => { x, y, z, rot }`. `keys = [{ t, x, y, z, move }]`, sorted by `t`; the segment ending at key `i` uses `keys[i].move`: `'push' | 'pull' | 'track' | 'dive'` → `eio`; `'punch'` → `spring(…, ENERGY.peak)` (overshoots); `'whip'` → `eio` over the given span (≈ 0.3 s); `'cut'` → jump at `keys[i].t`; `'hold'` → stays. Zoom is `z0 * (z1 / z0) ** u` always. During `'hold'` segments and after the last key, zoom grows by `drift` per second (relative) and x/y wander ≤ 6 px on a slow seeded sine, so the camera is never fully still. `shakes = [{ t0, amp = 14, decay = 9, hz = 7 }]` add `kick` offsets to x/y.
  - `camApply(cam, layers)` where `cam = {x, y, z, rot}` and `layers = [{ g, depth }]`; depth 0 static, 1 world, > 1 foreground: transform `translate(KW/2,KH/2) rotate(rot) scale(z**depth) translate(-(x*depth + KW/2*(1-depth)), -(y*depth + KH/2*(1-depth)))`.
  - `screenScale(z) -> string` = `scale(${1/z})`, for labels attached to objects so their screen size stays constant.
  - `CAM_RULES = { pullMinRatio: 3, punch: [.4, .6], pull: [2, 3], dive: [.8, 1.2], whip: .3, shake: [.3, .5], maxShakesPerWorld: 2 }` (read by the contact-sheet checker in Task 7).

- [ ] **Step 1: Write the failing test** `cam.test.cjs` (pure, `loadPure(['kit.js','motion.js','cam.js'], …)`):

```js
const c = camPath([{ t: 0, x: 960, y: 540, z: 2.4, move: 'cut' }, { t: 3, x: 960, y: 540, z: .3, move: 'pull' }]);
assert(Math.abs(c(1.5).z - Math.sqrt(2.4 * .3)) < .02);                 // log-space midpoint (eio(.5) = .5)
const p = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }, { t: .5, x: 0, y: 0, z: 1.15, move: 'punch' }]);
assert(Math.max(...Array.from({ length: 50 }, (_, i) => p(i / 50).z)) > 1.15);   // overshoot
const h = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }, { t: 1, x: 0, y: 0, z: 1, move: 'hold' }]);
assert(h(5).z > h(1).z);                                                 // drift: never still
const s = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }], { shakes: [{ t0: 1 }] });
assert(Math.abs(s(1.05).x) > 1 && Math.abs(s(2).x) < .5);
```

plus a page test: `camApply` with depths 0 / 1 / 1.4 moves a foreground point farther than a world point for the same camera change.
- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k cam -v` — Expected: FAIL.
- [ ] **Step 3: Implement** `cam.js`.
- [ ] **Step 4: Run** the test — Expected: PASS.
- [ ] **Step 5: Commit** `feat(gfx_kit): camera module with named moves, log zoom, drift and parallax`

---

### Task 4: Rigged shared cast (`cast_rig.js`)

**Files:**
- Create: `doc_renderer/gfx_kit/cast_rig.js`
- Create: `doc_renderer/gfx_kit/tests/cast_rig.test.cjs`

**Interfaces:**
- Consumes: `Y_*` and `Y.look.style` (Task 2), `FL_tone` (Task 2), `spring`, `blinkOpen`, `squash`, `land` (Task 1), `litPass`/`litDisc` (finish.js/glow.js) for paint A.
- Produces:
  - `CAST_ID` — the identity colours in Global Constraints plus Earth (`ocean: ['#5fd0ff', '#1f62c9'], land: '#5be08a', desert: '#f5c75f', ice: '#f1f8ff', cloud: '#ffffff'`) and Sun (`core: '#fff3b0', mid: '#ffd23f', edge: '#ff8a3d'`).
  - `jook(parent, { paint = Y.look.style, arms = false, helmet = false } = {}) -> { root, back, front, handL, handR, update(t, st) }`; `st` = kit `mascot()` fields (`in, look, blink, hop, bubble, mouth, wide, sleep`) plus `x, y, s, rot, armL: [deg, reach], armR: [deg, reach], squash` (−1..1). The sprout follows the body 0.07 s late (follow-through); if `st.blink` is absent, `blinkOpen(t, seed)` drives blinks. Body outline, eye/pupil/highlight geometry and proportions come from the avatar reference.
  - `earth(parent, r, { paint, light = 215, seed = 9 } = {}) -> { g, state({ x, y, s, o, spin }) }` — continents from `seed`, clouds as arched round-capped strokes following the sphere, night side per paint (B: hard shape, ≤ 4 px soft edge).
  - `sun(parent, r, { paint } = {}) -> { g, state({ x, y, s, o, t }) }` — no flares or loops on the edge.
  - Paints: `'A'` gradients + `litPass` rim; `'B'` three tones via flat `Y_lit`, no blur; `'C'` 6 px `#3a2230` outlines and an 8 px offset sticker shadow; `'D'` uses the B paint (paper is for the episode's own props; the shared cast sits in the SVG layer above the paper canvas).

- [ ] **Step 1: Write the failing test** `cast_rig.test.cjs` — for each paint `A, B, C, D`, a fixture builds `jook` and `earth`, calls `update(2, {look: [1, 0]})`, and the test asserts:

```js
for (const paint of ['A', 'B', 'C', 'D']) await withPage(`run=rig&paint=${paint}`, async page => {
  const r = await page.evaluate(() => window.RIG_FACTS);   // set by the fixture from the built DOM
  assert.strictEqual(r.eyeWhites, 2); assert.strictEqual(r.eyeWhiteFill, '#ffffff');
  assert.strictEqual(r.pupils, 2);    assert.strictEqual(r.highlights, 4);
  assert.strictEqual(r.cheekFill, '#ff8aa6'); assert.strictEqual(r.cheekOpacity, 1);
  assert(r.pupilDx > 0);              // looks right
  assert.strictEqual(r.earthClouds.every(c => c.linecap === 'round'), true);
});
```

and the sprout lag: the sprout's vertical offset at `hop` peak `t` equals the body's at `t - 0.07` (±0.5 px).
- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k cast_rig -v` — Expected: FAIL.
- [ ] **Step 3: Implement** `cast_rig.js` (draw from the avatar reference and the prototype `.mp/shape_styles_20261026/page.html` `buildJook`/`STYLES.*.earth`, with the cheek fix).
- [ ] **Step 4: Run** the test — Expected: PASS. Record a still per paint (`--stills 2.8`) into `<scratch>` and look at all four.
- [ ] **Step 5: Commit** `feat(gfx_kit): rigged shared cast (จุก, Earth, Sun) painted per look`

---

### Task 5: Fonts and the type module (`type.js`)

**Files:**
- Add (after approval): `.mp/fonts/Fredoka-SemiBold.ttf`, `.mp/fonts/Fredoka-Bold.ttf`, `.mp/fonts/Mitr-Medium.ttf`, `.mp/fonts/Mitr-SemiBold.ttf`
- Create: `doc_renderer/gfx_kit/type.js`
- Modify: `doc_renderer/gfx_kit/template.html` (`@font-face` for Fredoka 600/700 and Mitr 500/600 from `../../fonts/`; load `cast.js, flat.js, motion.js, cam.js, type.js, cast_rig.js`; Kanit stays)
- Create: `doc_renderer/gfx_kit/tests/type.test.cjs`

**Interfaces:**
- Produces:
  - `TYPE = { teal: '#8fd8e6', gold: '#ffd98a', white: '#ffffff', pill: 'rgb(6,20,40)', pillOpacity: .62, th: 'Mitr', num: 'Fredoka', thWeight: 500, thHeadWeight: 600, numWeight: 700, latinWeight: 600 }`
  - `riseLine(parent, x, y, size, runs, t0, { anchor = 'middle', container = auto, padX = 30, energy = 'peak' } = {}) -> { g, update(t, z = 1) }`; `runs = [[text, kind, color]]`, `kind` `'th' | 'num' | 'latin'`, `color` a `TYPE` key; `container` defaults by `Y.look.style`: A `'underline'`, B `'pill'`, C `'sticker'`, D `'paper'` (a torn-strip look drawn in SVG); `letter-spacing` 5 px only on `'latin'` runs; `update(t, z)` applies `screenScale(z)` when the line hangs on a world object.
  - `digits(parent, cx, y, size, { color = 'white', weight = 700, align = 'center' } = {}) -> { g, set(str, color?) }` (`align: 'right'` pins the last slot at `cx`, for ticking counters) — fixed-width slots: digits `.58·size`, `:` and `.` `.3`, `°` `.34`, `-`/`−` `.42`, Latin caps `.62`.
  - `slam(t, t0, energy = 'peak') -> number` scale 1.7 → 1.

- [ ] **Step 1: Ask นน for the download** — the files above from `github.com/google/fonts` (`ofl/fredoka`, `ofl/mitr`, OFL licence), each a few hundred KB; state names, source and sizes; continue only on a clear yes. If Fredoka is only published as a variable font, save `Fredoka[wdth,wght].ttf` and point both weights at it.
- [ ] **Step 2: Write the failing test** `type.test.cjs`:

```js
await withPage('run=type', async page => {
  const r = await page.evaluate(() => window.TYPE_FACTS);
  assert.strictEqual(r.thaiLetterSpacing, 0);                 // no tracking on Thai runs
  assert.strictEqual(r.latinLetterSpacing, '5');
  assert.deepStrictEqual(r.hiddenBeforeT0, true);             // clipped below the line before t0
  assert(Math.abs(r.offsetAtEnd) < .5);                       // risen by t0 + 0.55
  assert.strictEqual(r.pillWhenEmpty, false);                 // pill scale 0 while the text is still below
  assert.deepStrictEqual(r.slotX['10:00'].slice(-2), r.slotX['9:59'].slice(-2));   // last two digits never move
  assert(r.widthMinus70 <= r.widthMinus70Budget);             // −70°C fits its slots
});
```

(`TYPE_FACTS` is filled by the fixture `FIXTURES.type` from `riseLine`/`digits` built at `Y.look.style = 'B'`, digits with `align: 'right'`.)
- [ ] **Step 3: Run** `pytest tests/test_gfx_kit_js.py -k type -v` — Expected: FAIL.
- [ ] **Step 4: Implement** `type.js` (from `.mp/shape_styles_20261026/type.html` `riseLine`/`digits`), update `template.html` (it also sets `PAPER.font = 'Mitr'` for new pages; `paper.js`'s own default stays Kanit for old pages).
- [ ] **Step 5: Run** the test — Expected: PASS.
- [ ] **Step 6: Commit** `feat(gfx_kit): Fredoka + Mitr type module and template fonts` (font files included).

---

### Task 6: Motion blur in `record.cjs`

**Files:**
- Modify: `doc_renderer/gfx_kit/record.cjs`
- Create: `doc_renderer/gfx_kit/tests/record.test.cjs`

**Interfaces:**
- Produces: `FIXTURES.whip` in `tests/fixture.html` (a 200x400 white bar on black moving right at 600 px/s from x = 300; used here and in Task 7).
- Produces: `subframeTimes(i, fps, from, { sub = 2, shutter = .6 }) -> number[]` exported from `record.cjs` (`module.exports` when `require.main !== module`); for `sub = 2` the times are `t ± shutter / (4 * fps)` around `t = from + i / fps`, so the blurred frame is centred on the unblurred one.
- CLI: MP4 output blends 2 subframes by default; `--mblur 0` turns it off; `--mblur N` sets the subframe count; `--shutter` (default 0.6). Stills never blur. Blending is done by ffmpeg: frames are piped at `fps * N` and filtered with `tmix=frames=N,select='not(mod(n+1\,N))',setpts=N/(<fps>*TB)`.

- [ ] **Step 1: Write the failing test** `record.test.cjs`:

```js
const { subframeTimes } = require('../record.cjs');
assert.deepStrictEqual(subframeTimes(10, 25, 0).map(v => +v.toFixed(4)), [.394, .406]);
assert.deepStrictEqual(subframeTimes(0, 25, -.8, { sub: 1 }), [-.8]);
```

plus an end-to-end check: record `tests/fixture.html` with name `x&run=whip` for 1 s with and without blur, decode frame 12 of each with ffmpeg to raw gray, and assert the blurred bar's edge is wider than the sharp one and both bars are centred within 2 px (Review Focus 4).
- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k record -v` — Expected: FAIL.
- [ ] **Step 3: Implement** the flags, `subframeTimes`, and the ffmpeg filter.
- [ ] **Step 4: Run** the test — Expected: PASS.
- [ ] **Step 5: Commit** `feat(gfx_kit): subframe motion blur for recorded MP4s`

---

### Task 7: Beat sheet and the contact-sheet tool

**Files:**
- Create: `doc_renderer/gfx_kit/beats_template.md`
- Create: `doc_renderer/gfx_kit/contact_sheet.cjs`
- Create: `doc_renderer/gfx_kit/tests/contact_sheet.test.cjs`, `doc_renderer/gfx_kit/tests/beats_fixture.md`

**Interfaces:**
- Beat sheet = a sidecar `<world>.beats.md` next to the world file, three sections `## DIRECTION`, `## BEATS`, `## GOTCHAS`. BEATS is a Markdown table with columns exactly `time | peak | trigger | story move | camera | what changes | text | sound`; `peak` is the second the beat looks fullest (defaults to `time + 0.4` when empty); `story move` starts with its number 1–12; `camera` starts with a move name from `cam.js`.
- Produces (`contact_sheet.cjs`): `parseBeats(md: string) -> { direction: string, beats: [{ time, peak, trigger, story, storyNo, camera, cameraMove, changes, text, sound }], gotchas: string }`; `checkBeats(beats) -> string[]` problems: empty story or camera; story move "push-in" (not a story move); `drift`/`hold` camera with an empty "what changes"; no beat with story 2 or no beat with story 3 in the world; more than `CAM_RULES.maxShakesPerWorld` shakes.
- CLI: `node doc_renderer/gfx_kit/contact_sheet.cjs <page.html> "<scene&f=…>" <world.beats.md> <outdir>` → `<outdir>/beat_<n>.jpg` at each `peak` and `<outdir>/contact.html`: a grid, one card per beat (still, time, trigger, story move, camera, what changes, text), the `checkBeats` problems listed in red at the top. Exits non-zero when there are problems, but still writes the page.

- [ ] **Step 1: Write the failing test** `contact_sheet.test.cjs` using `beats_fixture.md` (four rows built from the spec's two example rows plus one `drift` row with empty "what changes" and one row with story `push-in`):

```js
const { parseBeats, checkBeats } = require('../contact_sheet.cjs');
const b = parseBeats(fs.readFileSync(__dirname + '/beats_fixture.md', 'utf8'));
assert.strictEqual(b.beats.length, 4); assert.strictEqual(b.beats[0].trigger, 'แปดนาที');
assert.strictEqual(b.beats[0].storyNo, 5); assert.strictEqual(b.beats[1].cameraMove, 'dive');
assert.strictEqual(b.beats[0].peak, 3.6);                     // empty peak -> time + 0.4
const p = checkBeats(b.beats);
assert(p.some(s => /no scale reveal/.test(s)));               // fixture has no story 2
assert(p.some(s => /drift.*what changes/.test(s)));
assert(p.some(s => /push-in is not a story move/.test(s)));
```

and an end-to-end run on `tests/fixture.html?run=whip` that checks `contact.html` exists and has one `<figure>` per beat.
- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k contact -v` — Expected: FAIL.
- [ ] **Step 3: Implement** `beats_template.md` (the three sections with the spec's column list and the two example rows), `contact_sheet.cjs` (stills through `chrome.cjs`).
- [ ] **Step 4: Run** the test — Expected: PASS.
- [ ] **Step 5: Commit** `feat(gfx_kit): beat-sheet template and contact-sheet page`

---

### Task 8: Word-level trigger times

**Files:**
- Create: `src/producer_word_times.py`
- Create: `scripts/beat_word_times.py`
- Modify: `scripts/producer_gfx_short.py` (import `squash`, `char_times` from `src/producer_word_times.py` instead of defining them)
- Create: `tests/test_producer_word_times.py`

**Interfaces:**
- Consumes: `speech_onsets(audio_path, min_pause_seconds=0.16)` from `src/producer_score.py`; beat-sheet table format (Task 7).
- Produces (`src/producer_word_times.py`):
  - `squash(s: str) -> str`, `char_times(script: str, words: list[tuple[str, float, float]], dur: float) -> list[float]` (moved unchanged)
  - `trigger_time(script: str, words: list[tuple[str, float, float]], trigger: str, onsets: list[float], *, phrase_time: float | None = None, snap: float = .15, min_match: float = .6) -> dict` returning `{"trigger", "time", "method": "word" | "phrase" | "unknown", "confidence"}`. Finds `squash(trigger)` in `squash(script)`; `confidence` = share of the trigger's characters that matched heard characters; at or above `min_match` the time is the first matched character's time snapped to the nearest onset within `snap`; below it, falls back to `phrase_time` (`"phrase"`) or returns `time: None` (`"unknown"`). Never returns a `"word"` time below `min_match`.
- CLI (`scripts/beat_word_times.py`): `python scripts/beat_word_times.py <scene.wav> <scene_script.txt> <world.beats.md> [--speech-map speech_map.json --scene <id>] [--offset <scene start s>] [--write]` — transcribes with faster-whisper `large-v3`, `language="th"`, `word_timestamps=True`, `vad_filter=True`, no `initial_prompt`; prints one line per trigger; `--write` fills the `time` column (rounded to 0.01 s, plus `offset`) and appends ` (phrase)` to the trigger cell of fallbacks.

- [ ] **Step 1: Write the failing tests** `tests/test_producer_word_times.py` (no Whisper: words are given):

```python
def test_trigger_found_and_snapped():
    words = [("แสงนี้", 0.0, 0.5), ("ออกจาก", 0.5, 0.9), ("ดวงอาทิตย์", 0.9, 1.6), ("แปดนาที", 1.62, 2.2)]
    r = trigger_time("แสงนี้ออกจากดวงอาทิตย์แปดนาที", words, "แปดนาที", onsets=[0.0, 1.70])
    assert r["method"] == "word" and r["time"] == 1.70 and r["confidence"] == 1.0

def test_misheard_trigger_falls_back_to_phrase():
    words = [("แสงนี้", 0.0, 0.5), ("ออกจาก", 0.5, 0.9), ("ดวงอาทิตย์", 0.9, 1.6), ("แปะนะดี", 1.62, 2.2)]
    r = trigger_time("แสงนี้ออกจากดวงอาทิตย์แปดนาที", words, "แปดนาที", onsets=[], phrase_time=0.0)
    assert r["method"] == "phrase" and r["time"] == 0.0

def test_unknown_without_phrase():
    assert trigger_time("ก", [], "แปดนาที", onsets=[])["method"] == "unknown"

def test_gfx_short_still_imports_char_times():
    import scripts.producer_gfx_short as g   # or importlib from path, as the repo's tests do
    assert g.char_times is producer_word_times.char_times
```

plus a `--write` round trip on a temp copy of `doc_renderer/gfx_kit/tests/beats_fixture.md` with `transcribe` monkeypatched to return fixed words.
- [ ] **Step 2: Run** `pytest tests/test_producer_word_times.py -v` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the module and the CLI (`transcribe(wav) -> list[tuple[str, float, float]]` as its own function so tests can patch it).
- [ ] **Step 4: Run** `pytest tests/test_producer_word_times.py tests/test_producer_score.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** `feat(producer): word-level trigger times for beat sheets`

---

### Task 9: Demo world, docs and the Producer Mode skill

**Files:**
- Create: `doc_renderer/gfx_kit/motion_demo.html` + `doc_renderer/gfx_kit/motion_demo.beats.md` (the prototype beat rebuilt with the new modules, look B: pull-back from 2.4x to 0.6x, pin drop with `enter('drop')`, label `riseLine`, counter `digits` + `slam`, จุก `jook()` looking 0.25 s early, one `punch`)
- Modify: `doc_renderer/gfx_kit/LIBRARY.md` (new sections: "Looks" with the four looks, B space default, D history default, the shape-spec headings and the B numbers from the spec; "Shared cast identity"; "Type"; "Story moves" with the 12 moves and guard rules; "Camera"; "Motion" with the nine rules; "Beat sheet and contact sheet"; the "Glow direction" section re-labelled as look A, no longer the default; "Scenes, not diagrams" kept; the A, C and D shape specs filled in under the same eight headings from `.mp/shape_styles_20261026/page.html`, `glow.js`, `w_style.js` and `paper.js`; D notes: avoid whips and fast tracks)
- Modify: `.claude/skills/moneyprinter-producer-mode/SKILL.md` (line with "glow is the default") and `references/sequence-and-review.md:17` (default look B for space / D for history; ask before A or C; story-move menu and guards; camera energy rule — full energy only in the hook and at each world's peak; motion rules pointer; beat sheet replaces the SHOTS header; contact-sheet gate: send นน `contact.html` for every world and wait for approval before recording; word-timing helper)
- Modify: `.claude/skills/moneyprinter-producer-mode/INBOX.md` (mark the 2026-10-26 line and the "copied helpers" `cast.js` part as done)
- Create: `doc_renderer/gfx_kit/tests/compat.test.cjs`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the failing test** `compat.test.cjs` (Review Focus 5): record `--stills 2` of one cosmic-year-humans world (`.mp/podcast_v2_cosmic-year-humans_20261020_235317/graphics/glow/page.html "sp_light&f=w_space.js"`) and of `doc_renderer/gfx_kit/glow_demo.html space`, and compare each against a reference still recorded from `main` before this branch (record the two references once from an untouched `main` checkout, `git worktree add <scratch>/main main`, and store them under `doc_renderer/gfx_kit/tests/ref/`); assert mean absolute pixel difference < 1.0 (decode with ffmpeg to gray raw). Then `motion_demo.html` must load with no `pageerror`, and `contact_sheet.cjs` on `motion_demo.beats.md` must exit 0 (no problems).
- [ ] **Step 2: Run** `pytest tests/test_gfx_kit_js.py -k compat -v` — Expected: FAIL (demo missing).
- [ ] **Step 3: Implement** the demo page and beat sheet; write the LIBRARY.md and skill changes.
- [ ] **Step 4: Run** `pytest tests/test_gfx_kit_js.py tests/test_producer_word_times.py -v` — Expected: PASS. Render the demo's contact sheet and an MP4 with blur; open `contact.html` in the browser pane and send นน the contact page and the MP4.
- [ ] **Step 5: Commit** `docs(gfx_kit, producer-mode): looks, type, story moves, camera, motion rules and the contact-sheet gate`
