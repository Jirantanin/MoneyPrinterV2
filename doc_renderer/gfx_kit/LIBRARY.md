# Explainer graphics library

Rule (นน, 2026-10-13): "ไม่หยิบของเดิมมาใช้ตลอด ใช้แค่เฉพาะที่เหมือนกันจริงๆ เท่านั้น เพื่อกันซ้ำกันของแต่ละคลิป
อยากให้แต่ละคลิปมีแนวทางของตัวเอง ไม่ใช่เหมือนกันหมด"

Reuse a piece only when it is the same thing in every episode. Each episode draws its own metaphor, props,
characters and compositions, and picks its own look with `theme()`.

## Three layers

| Layer | Where | Reuse |
|---|---|---|
| Tools the viewer never sees: easing, `lerpPt`, `bump`, `mixColor`, `track`, `camera`, `chip`, `burst` | `kit.js` | Always |
| Finish: light and depth on whatever the episode draws (rim light, shade band, glow, light shaft, dust, vignette, grain) | `finish.js` | Always, coloured per episode |
| Shared cast, the same thing every time: Earth, the Sun, จุก, truth tags, the number counter, the rock generator | `kit.js` (Earth `planet(…, 'earth')`, `mascot()`), `library.js` | Yes, unchanged |
| The episode's own: recurring metaphor, props (traffic light, hourglass, calendar, buildings, mountains), topic characters, layouts, palette | the episode's page | Never copied from another episode; draw it fresh in this episode's style |

A prop that appeared twice is still a prop: an hourglass or a clock should look like this episode, not like the last
one. A piece moves into the library only when it is the same real thing (a specific spacecraft, a planet) and a second
episode needs it.

## Shared cast

| Piece | Call | Use when | Not when |
|---|---|---|---|
| Earth | `planet(parent, r, 'earth', seed)` (kit.js) | Earth itself | a generic planet: use `planet(…, 'rock'/'warm'/'gold')` or draw one |
| Sun | `sun(parent, r)`, `.state({x, y, s, o, t})` | our Sun | another star: draw it in the episode's palette |
| จุก | `mascot(parent, x, y, scale)` (kit.js) | the viewer's reaction: look, blink, hop, `!`/`?` | stating facts, narrating, or appearing in every beat |
| จุก's space helmet | `spaceHelmet(m)`, `.update(t, o)` | จุก in space; the same helmet every time (decided 2026-10-13) | a scene on Earth; a gimmick in every beat |
| จุก's other outfits | draw on `m.back` / `m.front` (behind / over the body; they follow hops and breathing) | a setting change worth a visual joke: diving gear underwater, a hard hat in a mine | an outfit that claims something the narration does not (จุก down where no one can go) or hides the eyes |
| Rock | `rock(parent, r, {seed, fill, craters})` | an asteroid or boulder; pick a new seed and a fill from this episode's palette | reusing another episode's seed and fill |
| Truth tags | `truthTag(parent, 'compare'/'suppose', x, y)`, `truthTag(parent, 'scale')`, `.update(t, tIn, tOut)`; `supposeFrame(parent)` | `เปรียบเทียบ` on an analogy that could be read as data, `supposeFrame` (dashed border) for the whole hypothetical, never the `สมมติ` label on screen (นน 2026-10-15; the word is spoken instead), `ภาพประกอบ ไม่ตามสเกล` on orbits, maps, sizes | restyling them: their fixed look ignores `theme()` so viewers recognise them |
| Counter | `counter(parent, x, y, {size, suffix})`, `.update(t, steps, climb)` | numbers the narration says; a drop or rewind is a step (swap) | counting through values nobody says; the climb guard throws if a climb counts down or misses its spoken landing value |

## Finish layer (house level)

Every episode's graphics get the same depth of finish; only the colours change (นน approved the level on 2026-10-15
from the Hatshepsut v3 cut; Kurzgesagt is the reference level, not a look to copy). Load `finish.js` after `kit.js`.

| Call | Does | Notes |
|---|---|---|
| `finishDefs(svg, {rim, shade, light, warm, warmCore, vig, vigOpacity, grain, dust})` | adds the `fin*` filters and gradients in this episode's colours | once, right after `stage()`; `light` is the offset toward the light, default `[-16, -12]` (upper left) |
| `rimForm(parent, d, fill, {rim, dx, dy})` | a filled path with a thin rim light on the lit edge | for figures and shapes you build piece by piece; the rim side follows `light` unless dx/dy are given |
| `litPass(node)` | one filter over a finished piece: rim on the lit edge, soft shade band on the far edge | props and library pieces (`rock`, planets, buildings); do not stack it over `rimForm` parts |
| `glowHalo(parent, r, {flicker, seed, soft})` → `update(t)` | screen-blended halo for a light source | torches, lamps, a sun low in the frame |
| `lightShaft(parent, d, {color, opacity, dir})` → `update(t)` | soft beam through a slot or window | one per scene is plenty |
| `dustLayer(parent, seed, {n, h, colors})` → `update(t)` | drifting particles that catch the light | |
| `finishFrame(svg, {vignette, grain})` | vignette and film grain over the frame | last, before the HUD, in place of `overlays()`; a bright scene wants a lighter `vig`/`vigOpacity` |

Also build backgrounds in layers (far, mid, light sources) with slow parallax, and use gradient fills rather than flat
ones. Check page: `finish_demo.html` (`night`, `day`), the same shapes plain and finished.
Worked example of a whole cut: `.mp/podcast_v2_hatshepsut-erased-pharaoh_20261015_165703_revision_v3gfx_01/graphics/v3/`.

## Each episode's own look

`theme({...})` before building sets the background gradient, nebula blobs (or none), star counts and colours, and
palette overrides. Without it the kit draws its original violet space, so older pages render unchanged.
`library_demo.html` shows the same cast under three example themes (`space`, `ocean`, `dusk`); they are examples,
not presets to pick from.

Record the choice in the plan as `visual_rules.art_direction` (palette, background, recurring metaphor, camera and
motion language, topic characters) and make it visibly different from the last three episodes; see the
producer-mode skill, sequence-and-review.md.

## Glow direction (`glow.js`), the house default

Since 2026-10-16 (นน, from the black-hole test) the default look is flat vector shapes that emit light, built on the
finish layer: load `glow.js` after `finish.js`. Our own version, not a copy: จุก is the character, the palette is the
episode's own (fallback mint and amber on deep teal), and the truth tags and Kanit labels stay. Pick paper-collage
instead when the story is about paper; a plain finish-only cut is still fine for a quiet beat.

| Call | Does | Notes |
|---|---|---|
| `glowDefs(svg, {hot, warm, accent, cool, deep, grain, vig, vigOpacity})` | blur filters, live grain, vignette | once, after `finishDefs()` |
| `bloom(parent, draw, {blur, opacity})` | `draw(g, k)` runs twice: blurred screen-blended copy (k > 1, widen it) then the crisp shapes | every light source and hot shape; not on text |
| `flowPath(parent, d, {color, width, speed, dashes})` → `update(t)` | dashes travel along any path | currents, orbits, signals, wind, blood flow; `dashes` a seed or `[[dash, gap], …]` |
| `flowBands(parent, bands, {cx, cy, ry, a0, a1, speed})` → `update(t)` | concentric glowing ribbons with flowing streaks | disks and rings: back half `a0: PI, a1: 2PI` before the body, front half `0..PI` after it |
| `glowMotes(parent, seed, {n, orbit, hide})` → `update(t)` | particles with their own glow, drifting or orbiting an ellipse | `hide(x, y)` hides the ones behind a body |
| `depthFG(parent, seed, [[x, y, r], …], {fill, rim, vx})` → `update(t)` | out-of-focus foreground shapes with a lit edge, fast parallax | 2-3 at the frame edges, never over a label |
| `blinkLight(parent, x, y, {color, period})` → `update(t)` | nav/status light | |
| `pulseRing(parent, x, y, r)` → `update(t, t0)` returns the level | light ring at a moment of impact | flare something else with the returned level |
| `glowFrame(svg, {grain})` → `update(t)` | vignette + grain that changes every 2 frames | replaces `finishFrame()`; call `update(t)` in render |

Also: slow camera push and a small roll on the scene group, parallax on everything (far stars < mid < scene < foreground),
rim light on characters from the scene's brightest source (`litPass`), and a reflection of that light where it would be
seen (a visor, glass). Check page: `glow_demo.html` (`space`, `earth`). Worked example: the black-hole test in the
2026-10-16 session (not in the repo). Renders are fast on the GPU (`PRODUCER_CHROME_GPU=1`, about 4-6 s per second of
1080p for the demo); blur filters are the cost, so keep `bloom` to the bright pieces.

## Paper-collage direction (`paper.js`)

A second house look besides the glow look (นน chose it on 2026-10-16 from the Hatshepsut S10/S14 test):
torn-paper cut-outs with deckle edges, pencil hatch, papyrus fibre, "boil" (shapes re-jitter every 2 frames, backdrops
every 6), drawn on a Canvas 2D layer under the kit's SVG. Pick it per episode as the art direction when cut, torn,
pasted or rebuilt paper carries the story (erasure, archives, folk tales, history told as a scrapbook); it is not a
default. The palette, props and characters are still the episode's own.

| Call | Does | Notes |
|---|---|---|
| `paperStage(svg)` | canvas behind the `stage()` svg | right after `stage()`; the svg stays on top for `truthTag`, `counter`, `footer` |
| `paperFrame(t)` → ctx | clears and sets the boil clocks | first line of `render(t)`; draw with `pctx` |
| `paper(pts, fill, id, o)` | a torn cut-out | `o`: `edge`, `edgeW`, `edgeAmp`, `amp`, `tex`, `speck` (stone), `fiber` (papyrus), `slow` (backdrops) |
| `pline(pts, color, w, id, o)` | hand-drawn stroke | carved grooves, cracks, trails; `dash` |
| `ptag(text, x, y, k, id, o)` | label on a torn strip | `k` from `pop()`; Kanit 900 |
| `pgrid(pts, step)` | graph-paper lines clipped to a sheet | work notes, plans, "a museum workroom" |
| `pflame(x, y, s, t, id)` / `pnight(lights, o)` | cut-paper flame / darkness with light pools | `pnight` after the scene, before tags; keep pools small (r 350-550) or the night disappears |
| `pfinish(o)` | paper grain + vignette | last |

Rules that came out of the test: every `id` is unique per shape (it seeds the jitter); motion stays a pure function of
`t` (`spring`, `kick` are in paper.js); build characters from separate pieces with pivots so they can act; keep the
truth tags in the svg, not redrawn on paper. Check page: `paper_demo.html` (`night`, `day`). Worked example:
`.mp/podcast_v2_hatshepsut-erased-pharaoh_20261015_165703_revision_v3gfx_01/graphics/paper/` (S10 erasure, S14 rebuild,
side-by-side with v3 in `out/`). The grain and textures are rebuilt per page load, not per frame; draw static backdrops into an offscreen canvas if a long run renders slowly.
