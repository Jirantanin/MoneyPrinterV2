# Explainer graphics library

Rule (นน, 2026-10-13): "ไม่หยิบของเดิมมาใช้ตลอด ใช้แค่เฉพาะที่เหมือนกันจริงๆ เท่านั้น เพื่อกันซ้ำกันของแต่ละคลิป
อยากให้แต่ละคลิปมีแนวทางของตัวเอง ไม่ใช่เหมือนกันหมด"

Reuse a piece only when it is the same thing in every episode. Each episode draws its own metaphor, props,
characters and compositions, and picks its own look with `theme()`.

## Looks (since 2026-10-26)

Four looks are kept and each episode picks one (นน, from `.mp/shape_styles_20261026/compare.html`). **B flat geometric
is the default for space episodes; D paper collage is the default for history episodes.** A storybook glow and C kawaii
sticker, or swapping a default, are per-episode choices: ask นน. Set it with `Y_init({style, ...})` (cast.js); B installs
`flat.js`. Spec and rationale: `docs/superpowers/specs/2026-10-26-motion-spec-design.md`.

**Shared cast identity, every look.** จุก keeps its body outline, sprout, proportions, white eyes, `#14103a` pupils, two
highlight dots per eye and opaque `#ff8aa6` cheeks (reference: the channel avatar, `.mp/channel_logo_20261021/jook.js`);
Earth keeps its ocean and land colours; the Sun keeps `#fff3b0 → #ffd23f → #ff8a3d`. A look changes only how bodies are
painted and lit. Use the rigged cast in `cast_rig.js` (`jook`, `earth`, `castSun`, painted per look).

Every look's shape spec fills the same headings:

| | B flat geometric (space default) | A storybook glow | C kawaii sticker | D paper collage (history default) |
|---|---|---|---|---|
| 1 primitives | circles, capsules, rounded rects, rounded polygons; corner radius 12 px on every piece; limbs full capsules; no outlines; a line is an object (thick, round-capped) | circles, capsules, rounded rects; corners 25–50 % of the short side; no outlines, no sharp corners except a pin tip | the same primitives with 6 px `#3a2230` outlines (4 px when far), round joins | torn paper: deckle edge, edge jitter 3–6 px, boil every 2 frames (backdrops 6) |
| 2 colour and light | three tones in the body's own hue: lit band upper-left, base, hard shade crescent lower-right (`Y_lit` dx 6, dy 5); no gradient inside a piece except sky and ocean; at most five hues plus one warm accent | 2–3 stop gradients that shift hue (never toward grey or brown); rim and shade band from `finForm`; one light direction per scene | flat pastels; no light; an offset sticker shadow (8 px, `#1c1236` at 45 %) | colours 20 % muted; pencil hatch at 45°; light as pools in the dark (`pnight`) |
| 3 depth | by value only; blur only on far background and at most 4 px on a planet's day/night edge | rim light; bloom only on small emitters (under 60 px) | stacking and the sticker shadow | paper layers with a soft 6 px offset shadow |
| 4 sizes at 1x | main planet r 200–260, topic character about 330 px tall, จุก about 130 px | same | topic character head:body 1:1.5 | same as B |
| 5 detail by size | under 100 px on screen: one shape, one colour; over 300 px: full three tones | under 80 px: silhouette and rim; 80–300 px: two tones | under 100 px: no inner detail | under 100 px: no hatch |
| 6 banned | straight capsule clouds (read as loading bars; clouds are arched strokes); highlight ellipses over land; translucent cheeks or overlays on flat colour (turn grey); big bright nebula discs (read as bokeh) | big blurred halos on big bodies (muddy); outlines | faces on props (จุก is the only one who reacts); glow | ruler-straight lines; whips and fast tracks (the boiling edges read as noise) |
| 7 rig | separate pieces with pivots (`jook()` arms, sprout follow-through) | same | same | cut pieces on brads; the shared cast stays in the SVG layer with the B paint |

Prototype of all four on one beat: `.mp/shape_styles_20261026/page.html?g=A|B|C|D&play`. Demo world in B with every
module: `motion_demo.html` (+ `motion_demo.beats.md`).

## Backgrounds in look B (since 2026-10-27)

นน, after comparing backgrounds: "บางที่เว้นที่ไว้เยอะเกินไป ไม่มี layer รายละเอียดน้ำ สีจม". A background is judged by
empty space, layer count, water detail and colour separation, not by how many props it has. Approved on the
before/after of `.mp/whatif_moon_iss_20261027/compare_bg.html` (code `world_v2.js` there).

1. **Five depth layers in every wide shot:** sky (static), far (camera depth 0.3–0.5), mid-far (about 0.65), the world
   (1), near (1.3–1.6, or screen-fixed with its own slow drift). Each layer has its own silhouettes, and things are
   never lined up on one baseline.
2. **Farther is lighter:** each layer back is lighter, less saturated and closer to the sky colour at the horizon;
   its details are dimmer (far windows at about a third of the near ones' opacity). The nearest layer is the darkest
   and most saturated. A layer is never darker than the one in front of it; that inversion is what sinks the colours
   into one mass.
3. **The sky is a layer too:** a gradient that turns warm toward the horizon when there is a light below it (a city,
   a sunset), plus cloud banks: scalloped round tops on a flat base, lit like any B body (`Y_lit` with a light band
   and a dark crescent in the cloud's own hue). Never long capsules (they read as pipes or loading bars). Circles
   unioned into one path wind the same way as `rigRR` (clockwise), or the overlaps turn into holes.
4. **No empty quarter:** split the frame in four; each quarter has something at its own depth. Space: a soft curving
   Milky Way band (star density plus very faint blurred ellipses, never a straight streak), a few sparkle stars that
   twinkle, one or two far planets, satellites or traffic around the planet, city lights on its night side, and one
   near object at a corner. Leave a gap only when the gap is the point (the distance between two bodies), and even
   then keep stars in it.
5. **Silhouette variety:** towers with setbacks, rounded crowns, spires, rooftop tanks, aerials with blinking lights,
   one light strip on a landmark; no two neighbours the same. No triangle mountains or zigzag ridges.
6. **Water has five things:** (a) every light source reflected as a vertical column of short horizontal dashes below
   it, fading with depth; (b) a wide pale column under the Moon or Sun; (c) two-tone ripples, denser and longer toward
   the camera; (d) foam where the water meets anything standing in it; (e) floating things when the story allows. The
   body is a gradient from a lighter surface to the deep, slightly transparent (about 0.9) over what it covers. A
   character in the water is clipped at the waterline; never paint a front water lip over it (it hides (a) to (c)).
7. **Check on the contact sheet:** before sending it, look at each still for an empty quarter, two neighbouring
   layers of the same value, and a flat colour field over a fifth of the frame with no detail. Fix those first.

## Three layers

| Layer | Where | Reuse |
|---|---|---|
| Tools the viewer never sees: easing, `lerpPt`, `bump`, `mixColor`, `track`, `camera`, `chip`, `burst` | `kit.js` | Always |
| Finish: light and depth on whatever the episode draws (rim light, shade band, glow, light shaft, dust, vignette, grain) | `finish.js` | Always, coloured per episode |
| Shared cast, the same thing every time: Earth, the Sun, จุก, truth tags, the number counter, the rock generator | new pages: `cast_rig.js` (`jook`, `earth`, `castSun`); older pages: `kit.js` (`planet(…, 'earth')`, `mascot()`), `library.js` | Yes, unchanged |
| Motion, camera and type tools: springs, entrances, camera moves, rising lines, digit slots | `kit.js` (`spring`, `kick`), `motion.js`, `cam.js`, `type.js` | Always (new pages) |
| The episode's own: recurring metaphor, props (traffic light, hourglass, calendar, buildings, mountains), topic characters, layouts, palette | the episode's page | Never copied from another episode; draw it fresh in this episode's style |

A prop that appeared twice is still a prop: an hourglass or a clock should look like this episode, not like the last
one. A piece moves into the library only when it is the same real thing (a specific spacecraft, a planet) and a second
episode needs it.

## Shared cast

| Piece | Call | Use when | Not when |
|---|---|---|---|
| Earth | new pages `earth(parent, r, {paint, light, seed})` (cast_rig.js); older pages `planet(parent, r, 'earth', seed)` (kit.js) | Earth itself | a generic planet: use `planet(…, 'rock'/'warm'/'gold')` or draw one |
| Sun | `sun(parent, r)`, `.state({x, y, s, o, t})`; on new pages the rigged `castSun(parent, r, {paint})` (cast_rig.js) | our Sun | another star: draw it in the episode's palette |
| จุก | new pages `jook(parent, {paint, arms, helmet})`, `.update(t, {x, y, s, look, blink, hop, bubble, mouth, wide, armL, armR, squash})` (cast_rig.js); older pages `mascot(parent, x, y, scale)` (kit.js) | the viewer's reaction: look, blink, hop, `!`/`?` | stating facts, narrating, or appearing in every beat |
| จุก's space helmet | `spaceHelmet(m)`, `.update(t, o)` | จุก in space; the same helmet every time (decided 2026-10-13) | a scene on Earth; a gimmick in every beat |
| จุก's other outfits | draw on `m.back` / `m.front` (behind / over the body; they follow hops and breathing) | a setting change worth a visual joke: diving gear underwater, a hard hat in a mine | an outfit that claims something the narration does not (จุก down where no one can go) or hides the eyes |
| Rock | `rock(parent, r, {seed, fill, craters})` | an asteroid or boulder; pick a new seed and a fill from this episode's palette | reusing another episode's seed and fill |
| Truth tags | `truthTag(parent, 'compare'/'suppose', x, y)`, `truthTag(parent, 'scale')`, `.update(t, tIn, tOut)`; `supposeFrame(parent)` | `เปรียบเทียบ` on an analogy that could be read as data, `supposeFrame` (dashed border) for the whole hypothetical, never the `สมมติ` label on screen (นน 2026-10-15; the word is spoken instead), `ภาพประกอบ ไม่ตามสเกล` on orbits, maps, sizes | restyling them: their fixed look ignores `theme()` so viewers recognise them |
| Counter | `counter(parent, x, y, {size, suffix})`, `.update(t, steps, climb)` | numbers the narration says; a drop or rewind is a step (swap) | counting through values nobody says; the climb guard throws if a climb counts down or misses its spoken landing value |
| Dinosaurs and small mammals | `dinos.js` (load it via `?f=../../../../doc_renderer/gfx_kit/dinos.js` after `flat.js`): `Dino.hadro / cera / rex / bird / ptero / mam`, `.update(t, {x, y, s, flip, walk, head, chew, jaw, look, blink, hop, …})` | any episode with prehistoric animals: the channel's own cute flat cast (นน 2026-10-26), one outline per animal with a pale underside band, stub legs, big eyes, rounded snouts; recolour per episode | pointed beaks or outlines (นน turned both down); a scientific reconstruction where the anatomy is the point: use real figures |
| Mesozoic world | `meso.js` (`?f=../../../../doc_renderer/gfx_kit/meso.js`): `Meso.world({ gy, x0, x1, seed, sun })`, `W.makeFG()` after your actor layer, then `W.paint(a, b, k)`, `W.sky_({...})`, `W.cam([cx, cy, z], anchor)`, `W.sway(T)`; plants `Meso.fernPlant / araucaria / treeFern / cycad / bush` | any dinosaur-age place: the cosmic-year standard world (far ridges and misty tree line, araucarias, tree ferns, cycads, bushes, ground ferns with long shadows, light pools, dust, dark corner fronds, parallax); palettes night, dawn, ash, morn, day, chill (นน 2026-10-26: "ดูทำลวกๆมาก" about a background drawn without it) | drawing a new background from triangles and flat blobs; a world with grass or flowers (not yet evolved) without adding them |
| Space world | `cosmos.js` (`?f=../../../../doc_renderer/gfx_kit/cosmos.js`): `Cosmos.space(Y_layer(Y.bg), { sun, seed, pal })` → `update(t, { cam, dim })`; `Cosmos.rocks(layer, [[x, y, r, seed, stack]], { sun })` → `update(t, cam)`; `Cosmos.atmo(group, R, { rot })`; `Cosmos.star(...)` | any space shot: a light source in frame (bloom, spikes), nebula ribbons, twinkling stars, near rocks with a lit band toward the sun (flat look) or a rim (glow look), an atmosphere crescent on the lit limb; palettes `violet` and `veiled` (sun starved behind soot). Put the sun where the planet's lit side faces (นน 2026-10-26: flat navy space with grey corner rocks fell below the standard) | a shot whose light source is the subject itself (draw it); a planet lit from a side with no sun in the sky |

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

## Look A, glow direction (`glow.js`)

The house default from 2026-10-16 until 2026-10-26, when B flat geometric became the space default (see "Looks").
From the black-hole test (นน), this look is flat vector shapes that emit light, built on the
finish layer: load `glow.js` after `finish.js`. Our own version, not a copy: จุก is the character, the palette is the
episode's own (fallback mint and amber on deep teal), and the truth tags and Kanit labels stay. Pick paper-collage
instead when the story is about paper; a plain finish-only cut is still fine for a quiet beat.

| Call | Does | Notes |
|---|---|---|
| `glowDefs(svg, {hot, warm, accent, cool, deep, grain, vig, vigOpacity})` | blur filters, live grain, vignette | once, after `finishDefs()` |
| `bloom(parent, draw, {blur, opacity})` | `draw(g, k)` runs twice: blurred screen-blended copy (k > 1, widen it) then the crisp shapes | small light sources and hot shapes; not on text, not on big bodies (use `litDisc`; see "Scenes, not diagrams") |
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

## Scenes, not diagrams (the house default since 2026-10-18)

นน approved this from the superhabitable s22 test (round 2): the graphics explain and compare, but every shot is a
scene in a world, not a slide. It applies to every look (glow and paper alike).

**Exception: a diagram stage (นน 2026-11-01).** When the idea is itself a structure (axes of space and time, a family
tree, the glands around one organ, a risk table), a diagram may carry it, as a stage: set up once, then returned to across
the episode; holding the episode's own characters or drawn things (not icons or text boxes); and something happens on it
on the narration's words (a character leaves a trail along an axis, a branch dims and vanishes, a bar cracks). Never a
static diagram shown once. All three Kurzgesagt clips in `research_notes/teardown_kurz_compare.md` lean on such stages.

1. **A world, not objects on a plain background.** Every wide shot has a setting with layers: sky or far wall, far
   props that belong to the episode (its metaphor, distant bodies, probes with light trails, debris), the subject, and a
   foreground. Every corner has something to look at, and every piece serves the same story.
2. **Comparisons are revealed by motion.** A size or quantity is shown by something happening: a body rising over a
   horizon, the camera pulling back, a boundary travelling from one thing onto another, a container filling up. Never two
   things lined up on a baseline with a dashed line between them.
3. **Cause on screen.** When the narration says someone did something (a team set a threshold, a telescope measured),
   show who does it: the boundary comes out of the team's tablet, the light goes into the telescope.
4. **Crisp light, not blur.** Light the bodies with `litDisc` (flat terminator, rim stroke on the lit edge) or `rimForm`
   and `litPass`. Keep `bloom` and blurred halos for small things that emit light (a beam, a tablet, a star's core); a big
   blurred halo over a planet or a figure turns the frame muddy beige. Gradients shift hue (plum → rose → orange), never
   go grey or brown.
5. **Depth by value.** A dark foreground cut out against a bright source: `silhouette()` on figures, ledges and dishes
   standing in front of the light, plus a few out-of-focus bokeh dots at a corner. The brightest part of the frame is
   where the eye should go.
6. **People and จุก carry the feeling.** Topic characters watch and act in the scene (seen from behind as silhouettes is
   fine). At the emotional beat, cut to a close-up of จุก or a character for 1-2 s (face filling the frame, out-of-focus
   background in the subject's colours, the subject reflected in the visor), then cut back.
7. **Text and arrows.** Labels only for what hearing alone cannot carry (a name or term the first time, the scene's one
   number, truth tags); the earlier ceiling still holds. No arrows pointing at things; a line on screen is something that
   moves along it (`flowPath`, a beam, a trail).

Budget: a dense hero shot like the worked example took about an hour for 19 s. Make one every 1-2 minutes of graphics;
everything else still follows rules 2-5 and 7, which cost little.

| Call (glow.js) | Does | Notes |
|---|---|---|
| `litDisc(parent, r, {stops, rot, atmo, rim, hot, shade, draw})` → `{g, state({x, y, s, o})}` | planet or ball lit by crisp lines: gradient body, flat terminator, rim on the lit edge | `rot` = light direction in degrees (0 from the right, 90 from below); `draw(g, r)` adds bands, continents, clouds clipped to the disc |
| `silhouette(svg, {fill, rim, dx, dy})` → `'url(#…)'` | filter: dark cut-out with a thin rim on the side facing the light | set on a group of figures/props; `dx, dy` point away from the light |

Worked example: `.mp/podcast_v2_superhabitable-hunt_20261017_085615/graphics/glow/scene_s22_v2.js`
(`out/s22_v2_voice.mp4`; the slide-like original is `out/s22_old_voice.mp4`).

## Look D, paper-collage direction (`paper.js`)

The default for history episodes since 2026-10-26 (นน first chose it on 2026-10-16 from the Hatshepsut S10/S14 test):
torn-paper cut-outs with deckle edges, pencil hatch, papyrus fibre, "boil" (shapes re-jitter every 2 frames, backdrops
every 6), drawn on a Canvas 2D layer under the kit's SVG. It suits stories carried by cut, torn, pasted or rebuilt paper
(erasure, archives, folk tales, history told as a scrapbook). The palette, props and characters are still the
episode's own.

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

## Type (since 2026-10-26)

`type.js`. **Fredoka 600/700 for numbers and Latin, Mitr for Thai** (files in `.mp/fonts`; `template.html` loads them;
new pages set `PAPER.font = 'Mitr'` and build only after `await typeReady()`). Colours teal `#8fd8e6`, gold `#ffd98a` (the scene's one prominent number), white.

| Call | Does | Notes |
|---|---|---|
| `riseLine(parent, x, y, size, runs, t0, {anchor, container, energy})` → `update(t, z)` | a line that rises 1.3x its height through a clip on ease-out-quint (0.55 s), with its container arriving on a spring | `runs [[text, 'th' or 'num' or 'latin', 'teal' or 'gold' or 'white']]`; container by look: A underline bar, B pill `rgb(6,20,40)` at 62 %, C cream sticker, D torn strip (light containers switch to dark ink); pass the camera zoom `z` when the line hangs on a world object |
| `digits(parent, cx, y, size, {color, align})` → `set(str, color)` | numbers in fixed-width slots | a ticking number never jitters; `align: 'right'` when the digit count changes (10:00 → 9:59) |
| `slam(t, t0)` | scale 1.7 → 1 on a spring | numbers that slam in |

Letter-spacing (5 px) only on Latin caps (`LAST LIGHT`, `KM/S`), never on Thai. Text at least 34 px. The label ceiling
and truth rules above still hold: this changes how labels look, not how many there are.

## Story moves (since 2026-10-26)

A menu the producer designs each world from (นน: "เป็นชุดให้เลือก"), numbered so beat sheets can name them:

| # | Move | Example |
|---|---|---|
| 1 | event on its word | the Sun swells and collapses on "หายไป" |
| 2 | scale reveal: pull back until the size or distance shows | 2.4x → 0.45x until the Sun enters frame |
| 3 | make it personal: dive to a viewer stand-in (a YOU pin, จุก, a place in Thailand) | the pin drops onto Thailand |
| 4 | transformation: one object becomes another to carry the idea | the pin becomes a play button |
| 5 | live counter: the consequence counted on screen | 8:20 ticking; 15 → −70 °C |
| 6 | escalation: the consequence grows in steps | dark → cold → Earth leaves its orbit |
| 7 | จุก gag: a reaction beat | sunglasses drop onto จุก |
| 8 | absence: show what is missing | a dotted circle where the Sun was |
| 9 | travelling front: a boundary sweeping across things | night sweeping over Earth |
| 10 | rewind (needs the two clocks) | a 0.8 s rewind on the story clock |
| 11 | callback: an earlier object or number returns with a new meaning | a photon tagged "8:20 OLD" |
| 12 | track or pan through the world (horizontal, vertical, along a path) | sky → sea → seafloor |
| 13 | yardstick: the same everyday object measures each rung of a scale ladder, drawn in the same place each time | the same `โอ่งมังกร` beside each body, filled with as much of it as the jar holds |
| 14 | myth picture: draw the explanation the viewer already holds, then break it on screen | the textbook atom with planet-like electrons smears into a cloud |

Move 12: parallax by depth (about 0.2 / 0.6 / 1 / 1.4 of camera speed); never things on one baseline, the camera passes
through a place with things at different heights and depths; it slows at the thing being named and flows on, never
fully stopping; each thing enters frame about 0.5 s before it is named.

Guard rules (checked by `contact_sheet.cjs`): every beat names a story move and a camera move ("push-in" is not a story
move); every world has at least one 2 and one 3; every move is backed by the narration (no invented events; counters
land on spoken values); "nothing holds still" applies to graphics, holds on real evidence media stay as before.

## Concept devices (since 2026-11-01)

How to draw a claim that has no look of its own (a time running out, a rule that the total stays fixed, a signal that is
no longer heard). Start from the property the viewer must see (finite or endless, same or different, before or after,
inside or outside, broken), then pick a device and an everyday thing that carries that property by itself. Each world's
beat sheet records the choice in its `## CONCEPTS` card (beats_template.md). From three Kurzgesagt teardowns
(`research_notes/teardown_kurz_compare.md`); the count is how many of the three use it. Take the device, never their
drawings.

| # | Device | Example (theirs; find our own) | Seen |
|---|---|---|---|
| C1 | stand-in that carries the property: the object already has it in daily life | time that runs out = an hourglass with sand falling; a hormone that unlocks = a key that clicks | 3/3 |
| C2 | the viewer stand-in suffers the physics in its own body (a topic character; จุก only reacts until นน decides otherwise) | the bird stretched thin into a line, then gone | 3/3 |
| C3 | landmarks make the invisible visible | walking on and passing the same city again = space closes on itself | 2/3 |
| C4 | repeated poses of one figure turn a space axis into a time axis; play it backwards for "back in time" | egg → chick → adult on a line, then the egg reassembles | 2/3 |
| C5 | draw the breaking as a thing | the time bar cracks into a glitch; the signal's plug dangles, missing its socket | 3/3 |
| C6 | one container, different contents | the same capsule universe holding stars, black holes or an empty soup | 3/3 |
| C7 | a diagram stage (see "Scenes, not diagrams") | axes of space and time the character runs inside | 3/3 |
| C8 | the analogy plays out and becomes the real thing in one shot | a squeezed rubber ball bursts into a Big Bang | 2/3 |
| C9 | cut it open, show the inside, close it again | the hole sliced to show a universe, then whole again: "nothing changed outside" | 2/3 |
| C10 | one emptying beat at the story's lowest point (STANDARD "No dead frames" exception) | the frame empties on "is this the end?", one point of light returns | 3/3 |
| C11 | the picture everyone knows, then "this is a lie" (story move 14) | the rubber-sheet funnel, then a plain black ball on a plinth | 2/3 |
| C12 | admit the simplification on screen: the stand-in is puzzled, or a small footnote bubble | "there are other kinds too, not important here" | 3/3 |
| C13 | fixed-length budget bar split between two quantities; one grows, the other shrinks; past the limit it breaks | a Time / Space bar that never changes length | 1/3, new |
| C14 | a clock on each figure, ticking at its own rate | two twins with clocks that drift apart | 1/3, new |

A drawing that would lie more than the narration allows gets C12 instead. Truth rules in sequence-and-review.md apply to
every device: a count, gauge or bar shows only values the narration or sources give.

## Camera (since 2026-10-26)

`cam.js` replaces the per-world hand-rolled cameras: `camPath(keys, {shakes, drift})` → `t => {x, y, z, rot}` (zoom
always in log space; a slow drift during holds so the camera is never fully still), `camApply(cam, [{g, depth}])`
(depth 0 static, 1 the world, above 1 foreground, below 1 far layers), `screenScale(z)` for labels hung on objects.

| Move | Duration | Use |
|---|---|---|
| drift (`hold`) | whenever nothing else moves | 1–2 % zoom per second |
| push | a whole line | slow, contemplative lines |
| punch | 0.5–0.6 s | emphasis on a word; overshoots and lands exactly |
| pull | 2–3 s | scale reveals; zoom ratio at least 3x |
| dive | 0.8–1.2 s | into one point (make it personal) |
| track / tilt | per narration | move 12 |
| whip | about 0.3 s | a fast change of subject; reads through motion blur |
| shake | 0.3–0.5 s | a damped kick on an impact; at most 1–2 per world |

**Energy (นน):** full-energy camera and springs only in the hook and at each world's peak; explanation stretches use
drift, push and track, with the story moves at a calmer pace. Motion blur: a new page sets `window.__MBLUR = 2` and
`record.cjs` blends 2 subframes per MP4 frame (about twice the record time; `--mblur 0` turns it off); list hard steps
(cuts, counter ticks, caption swaps) in `window.__CUTS` so those frames are never double-exposed. Older pages record
sharp, as before.

**One-frame peaks:** under `__MBLUR = 2` a punch shorter than 0.5 s lands its overshoot on one sharp frame between two
blurred ones, and a bloom shaped as `bump(T, cut, .12)` on a cut is brightest for one frame. `gfx_flicker_scan.py`
flags both, with or without the GPU. Bloom on a cut is a flat plateau held for 3 frames.

**Seams:** a world that continues the previous world's shot starts from the previous camera at that world's end time
(`prevCam(tEnd)`), not from its last key: `camPath` keeps drifting after the last key (a 20 dB PSNR jump at the seam
in dinosaurs-never-died).

**Viewpoints (นน 2026-10-27):** `camPath` moves over one flat side view. Each world also has at least one redrawn
viewpoint (a low angle, top-down, over the shoulder, a reverse shot), cut on action.

## Motion (since 2026-10-26)

`spring`/`kick` are in kit.js; `motion.js` has `ENERGY` (`peak` damping 0.45 at 2.4 Hz for the hook and peaks, `calm`
0.7 at 2 Hz for explanation), `squash`, `land`, `anticip`, `enter(t, t0, 'pop' | 'drop' | 'slide')`, `leave`,
`blinkOpen`, `storyTime`.

1. Meaningful entrances have force (pop, drop and squash, slide with overshoot, draw-on, a rising line); no plain fade.
2. Squash and stretch keep volume; light things about 30 %, heavy about 10 %.
3. Anticipation before big moves: 5–10 % the other way for 0.1–0.2 s.
4. Follow-through: hanging parts lag 0.05–0.1 s (จุก's sprout lags 0.07 s by itself).
5. Eyes lead: characters look at what matters 0.2–0.3 s before it happens.
6. Exits are quicker than entrances (about 0.25 s, ease-in), never a slow fade.
7. Nothing is dead still: breathing, a slight bob, a blink every 3–5 s (`jook()` blinks by itself).
8. Stagger pieces 0.06–0.12 s apart; never everything at once.
9. Two clocks: ambient time for twinkle, spin and bob; `storyTime(t, keys)` for events, so a rewind or a retimed event
   does not make the ambience jump.

## Beat sheet and contact sheet (since 2026-10-26)

Each world gets a sidecar `<world>.beats.md` (template: `beats_template.md`) in place of the free-prose SHOTS header:
`## DIRECTION` (look, palette, sizes, light; point at the shared specs), `## BEATS` (one row per line or trigger word:
`time | peak | trigger | story move | camera | what changes | text | sound`) and `## GOTCHAS` (traps met; promote the
general ones here). Fill the times with `venv/Scripts/python.exe scripts/beat_word_times.py <scene.wav> <scene_script.txt>
<world>.beats.md --offset <scene start> --write` (faster-whisper large-v3 per scene, snapped to speech onsets; a
trigger it did not hear keeps its phrase time and is marked "(phrase)").

**Gate (นน):** before recording a world, run `node doc_renderer/gfx_kit/contact_sheet.cjs <page.html> "<scene&f=…>"
<world>.beats.md <outdir>` and send นน `<outdir>/contact.html` (one still per beat at its peak, the guard-rule problems
on top). Record only after นน approves that world.
