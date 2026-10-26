# Motion and shape spec for explainer graphics

Date: 2026-10-26. Decided by นน in a brainstorm with มิ้ง, started from a viral "Kurzgesagt in 10 minutes" Claude prompt.
Prototypes: `.mp/shape_styles_20261026/` (`compare.html` four looks, `type.html` type system, `out/` stills).

## Intent

นน's verdict on our finished episodes: the art is at level, but three things are not — **creativity** (pictures show
what the narration names instead of transforming it or pulling it toward the viewer), **camera** (one slow push-in per
shot, no scale reveals, no dive toward "you"), and **animation** (things fade or bump in and out with no weight; no
anticipation, overshoot or squash). The viral prompt itself is hype ("Not even close", นน), but its *method* is what we
lack: a spec that fixes shapes in numbers, a beat sheet where every line of narration names its trigger word, story
move, camera move and what changes, and motion rules with numbers. This design brings that method into the gfx_kit,
`LIBRARY.md` and the Producer Mode skill.

Success: the next space episode's beat sheets name a story move and a camera move for every line, the graphics use the
shared camera and motion tools instead of hand-rolled ones, and นน approves each world's contact sheet before recording
without the five-round style tests cosmic-year-humans needed.

## Goals

1. A numeric shape spec per look, with one shared set of headings, so a look is chosen and filled in rather than
   discovered through style-test rounds.
2. One type system (fonts, colours, pills, text motion, number motion).
3. A menu of story moves the producer designs from, with guard rules so the menu does not decay back to slow push-ins.
4. A shared camera module and a named set of camera moves, with an energy rule.
5. Shared motion helpers and nine motion rules.
6. A beat-sheet format that replaces the free-prose SHOTS header, and a contact-sheet gate นน reviews per world.

## Non-goals

- Copying Kurzgesagt's look, palette or characters. Kurzgesagt stays "the reference level, not a look to copy".
- A 30-second automated video generator. Episodes stay producer-made and reviewed.
- Downloaded SFX or music, ElevenLabs voices, English narration. Score and SFX stay composed/synthesised.
- WebGL. The prompt's WebGL Earth is out of scope for this design; the B-look Earth stays SVG. (A WebGL globe can be a
  later, separate piece.)
- Re-rendering or retro-fitting finished episodes.

## Anti-goals (a failure even if it technically works)

- จุก, Earth or the Sun looking different between looks. In the first B prototype จุก got solid black eyes; นน caught
  it. The shared cast keeps its identity in every look.
- Constant high energy for a whole 10–20 minute episode.
- On-screen text growing back toward captions. The label ceiling (about one label per 15–20 s of graphics) and the
  truth rules stay.
- Moves that invent events or numbers the narration does not state.
- Timelines, processions or comparisons on one baseline sneaking back in through the "track" move.

## Constraints

- All graphics stay pure functions of time (`window.__seek(t)`), recorded with `doc_renderer/gfx_kit/record.cjs`.
- Existing rules in `LIBRARY.md` ("Scenes, not diagrams", label ceiling, truth rules, mitten hands, seams) and
  `.mp/podcast_v2_cosmic-year-humans_20261020_235317/STANDARD.md` stay in force; this design adds to them.
- Thai text: no letter-spacing on Thai (marks detach from consonants).
- Fonts render offline: Fredoka and Mitr need local `.ttf` files in `.mp/fonts` (Kanit is already there). Downloading
  them needs นน's go-ahead (file names, source, size).
- Windows, no WSL; helpers นน runs are `.py` or `.bat`.
- The Producer Mode skill is edited through its INBOX and `/skill-retro`, or directly when นน approves this design.

## Decisions

### 1. Looks

Four looks are kept; each episode picks one. **B flat geometric is the default for space episodes; D paper collage is
the default for history episodes** (the Saturday slot). A storybook glow and C kawaii sticker, and swapping a default,
are per-episode choices (ask นน). The story moves, camera, energy and motion rules apply to every look and slot
(มิ้ง's call); D keeps its own boil and avoids whips and fast tracks, where the boiling edges read as noise. `flat.js` moves from
`.mp/podcast_v2_dinosaurs-never-died_20261024_210648/graphics/glow/` into `doc_renderer/gfx_kit/`.

**Shared cast identity (all looks).** จุก keeps white eyes, dark pupils, the highlight dot and opaque pink cheeks, its
body outline, sprout and proportions; Earth keeps its ocean/land colours; the Sun keeps its colours. A look changes only
how bodies are painted and lit.

**Shape spec headings (every look fills the same ones):** 0 shared cast · 1 primitives · 2 colour and light ·
3 depth · 4 sizes in frame · 5 detail by on-screen size · 6 banned (with the reason) · 7 rig (pieces, pivots, what
moves).

**B flat geometric, filled in** (numbers from the prototype `page.html?g=B`):

0. Shared cast as above.
1. Circles, capsules, rounded rects and rounded-corner polygons. Corner radius 12 px on every piece regardless of size;
   limbs are full capsules. No outlines. A line on screen is an object (cloud, antenna, beam): thick, round-capped.
2. Every colour has three tones: lit band on the upper-left, base, hard shade crescent on the lower-right (offset about
   7, 6 px), all in the body's own hue (`flat.js` `Y_lit`). No gradient inside a piece except sky and ocean. At most
   five hues per episode plus one warm accent.
3. Depth by value only. No blur on characters or foreground; blur only on far background, and at most 4 px on a
   planet's day/night edge.
4. At 1x: main planet radius 200–260, a topic character about 330 px tall, จุก about 130 px.
5. Below 100 px on screen: one shape, one colour. Above 300 px: full three tones.
6. Banned: straight capsule clouds (read as loading-skeleton bars; clouds are arched strokes following the sphere);
   highlight ellipses over continents; translucent cheeks or overlays on flat colour (turn grey); large bright nebula
   discs (read as bokeh).
7. Rig: see "Motion" rule 4 and the builder's notes; every character is built from separate pieces with pivots.

A, C and D get the same headings filled in by the builder from the prototype (`page.html?g=A|C|D`), `glow.js`,
`w_style.js` and `paper.js`.

**One rigged shared cast in the kit (มิ้ง's call).** The kit gets one rigged จุก, Earth and Sun that take the look as a
paint parameter; no look draws its own copy. The identity reference is the channel avatar
(`.mp/channel_logo_20261021/jook.js`) and kit.js `mascot()`: body outline, sprout, eyes, highlight, opaque cheeks.
Mitten arms are an optional rig part (as in dinosaurs' `w_jook_flat.js`, which นน accepted), not a required one. The old
`mascot()`, `planet(…,'earth')` and `sun()` stay unchanged so finished episode pages (cosmic-year-humans) re-record
exactly as before; new pages use the rigged versions.

**Base layer system (มิ้ง's call).** Recent episodes copy `cast.js` (`Y_*` helpers, `Y.bg/Y.cam/Y.fg/Y.hud` layers,
`Y_par`) from cosmic-year; `flat.js` depends on it. Lift `cast.js` into the kit as the base for new pages (this also
resolves the skill INBOX item about copied helpers); the camera module's parallax attaches to its layers. kit.js keeps
`stage()`/`base()`/`camera()` for old pages.

**dinosaurs-never-died (มิ้ง's call).** It is in production; it keeps its own `flat.js` and current process. The kit
`flat.js` starts as a copy and is generalised there; the next new episode is the first to use this design.

### 2. Type

- **Fredoka 600/700 for numbers and Latin; Mitr for Thai** (นน chose Mitr over Kanit and Mali). Mixed runs: digits in
  Fredoka inside Thai lines.
- Colours: teal `#8fd8e6`, gold `#ffd98a`, white. The scene's one prominent number is gold.
- Pills: `rgb(6,20,40)` at 62 %, fully rounded; the pill arrives with its text (spring), never empty.
- Every line rises 1.3x its own height through a clip on ease-out-quint (about 0.55 s); never fades in whole.
- Letter-spacing 3–6 px only on Latin caps (`LAST LIGHT`, `KM/S`), never on Thai.
- Numbers slam from 1.7x to 1x on a spring; ticking numbers sit in fixed-width digit slots so they never jitter;
  counters still land on spoken values and swap on drops (existing rule).
- On-screen text at least 34 px (existing rule). This changes how labels look, not how many there are.
- **Scope across looks (มิ้ง's call):** fonts, colour roles, text rise and number motion are shared by all four looks;
  only the container is per look: A an underline bar, B the dark pill, C a cream sticker with dark ink, D a torn paper
  strip (`ptag` switched from Kanit 900 to Mitr). Kanit stays loaded for old pages.

Prototype: `.mp/shape_styles_20261026/type.html` (`riseLine`, `digits`).

### 3. Story moves (a menu; the producer designs per world)

1 event on its word · 2 scale reveal (pull back) · 3 make it personal (dive to a viewer stand-in: a YOU pin, จุก, a
place in Thailand) · 4 transformation (one object becomes another to carry the idea) · 5 live counter · 6 escalation ·
7 จุก gag · 8 absence (show what is missing) · 9 travelling front (a boundary sweeping across things) · 10 rewind (needs
the two clocks) · 11 callback · 12 track/pan through the world (horizontal, vertical or along a path).

Move 12 rules: parallax by depth (about 0.2 / 0.6 / 1 / 1.4 of camera speed); never items on one baseline — the camera
passes through a place with things at different heights and depths; it slows at the thing being named and flows on,
never fully stopping; each thing enters frame about 0.5 s before it is named.

Guard rules:
1. Every beat-sheet row names its story move and its camera move; "slow push-in" is not a story move.
2. Every world has at least one scale reveal (2) and one make-it-personal (3). (มิ้ง's call; นน did not object.)
3. Every move is backed by the narration; no invented events; counters land on spoken values.
4. "Nothing holds still" applies to graphics; holds on real evidence media stay as today.

### 4. Camera

A shared camera module in the kit replaces the per-world hand-rolled ones: keyframes `[t, x, y, zoom]` with a move per
segment, zoom interpolated in log space, automatic parallax per layer depth, and a residual drift so the camera is never
fully still.

| Move | Duration | Character |
|---|---|---|
| drift | whenever no other move | 1–2 % per second |
| push-in | a whole line | slow; contemplative lines |
| punch-in | 0.4–0.6 s | fast, overshoot and settle; emphasis on a word |
| pull-back | 2–3 s | zoom ratio at least 3x (e.g. 2.4x → 0.6x); scale reveals |
| dive | 0.8–1.2 s | into one point, with speed streaks |
| track / tilt | per narration | move 12 |
| whip | about 0.3 s | fast lateral change of subject; needs motion blur |
| impact shake | 0.3–0.5 s | damped; at most 1–2 per world |

Easing easeInOutCubic; springy moves damping 0.42–0.5 at about 2–2.5 Hz. Text stays fixed to the screen; labels
attached to objects counter-scale so their screen size stays constant.

**Energy (นน):** full-energy camera and springs only in the hook and at each world's peak. Explanation stretches use
drift, push-in and track; story moves still apply there at a calmer pace.

**Motion blur:** `record.cjs` gains subframe blending (2 subframes, shutter 0.6). It roughly doubles record time.

### 5. Motion

Move `spring`/`kick` from `paper.js` into `kit.js` (paper.js keeps working) and add helpers for the rules below.

1. Meaningful entrances have force: spring pop, drop-and-squash, slide with overshoot, draw-on, or (text) rise through a
   clip. No plain fade for things that matter.
2. Squash and stretch keep volume (one axis grows, the other shrinks); light things about 30 %, heavy about 10 %.
3. Anticipation before big moves: 5–10 % the other way for 0.1–0.2 s.
4. Follow-through: hanging or protruding parts lag 0.05–0.1 s (จุก's sprout, antennas).
5. Eyes lead: characters look at what matters 0.2–0.3 s before it happens.
6. Exits are quicker than entrances (about 0.25 s, ease-in, shrink or leave frame), never a slow fade.
7. Nothing is ever dead still: breathing, a slight bob, a blink every 3–5 s.
8. Stagger: never everything at once; 0.06–0.12 s between pieces.
9. Two clocks: an ambient clock (twinkle, spin, bob) and a story clock (events), so rewinds work and events can be
   retimed without the ambience jumping.

Energy follows the camera rule: hook and peaks damping 0.42–0.5; explanation about 0.7.

**Word timing:** events fire on their word. Use per-scene faster-whisper large-v3 with `vad_filter` and no
`initial_prompt`, snap to speech onsets (lessons from dinosaurs-never-died, see the skill INBOX); where a word cannot be
placed reliably, fall back to the phrase time from the speech map and mark it. **(มิ้ง's call)** This is a separate
helper that writes trigger times into beat sheets; it does not replace the speech-map step, its `speech_map.json`
format or the Gemini cut check.

### 6. Beat sheet and the contact-sheet gate

Each world's SHOTS header is replaced by a beat sheet with three parts:

1. **DIRECTION** — the look, this world's palette, sizes of the main pieces, light direction; it references the shared
   shape and type specs instead of restating them.
2. **BEATS** — one row per line or trigger word: `time | trigger word | story move | camera move (from→to, duration) |
   what changes | text | sound`. Story move and camera move are never empty; a "drift" row must name what changes.
3. **GOTCHAS** — traps met while building this world; ones that apply elsewhere are promoted to `LIBRARY.md`.

Example rows:

| time | trigger | story move | camera | what changes | text | sound |
|---|---|---|---|---|---|---|
| 3.2 | "แปดนาที" | 5 counter | punch-in 1.0→1.15, 0.5 s | 8:20 slams 1.7x→1x and starts ticking | — | tick |
| 5.6 | "คุณ" | 3 personal | dive 1x→2.3x, 1 s | pin drops and squashes; จุก looks 0.25 s before | ประเทศไทย | pin tap |

**Gate (นน):** before recording any world, มิ้ง sends นน a contact sheet with one still per beat at its peak, as a live
HTML page (the standing preference: HTML previews for iteration, MP4 only for final/listening/motion review). Recording
waits for นน's approval of that world.

## Deliverables

1. `doc_renderer/gfx_kit/flat.js` (moved and generalised from the dinosaurs episode) and `LIBRARY.md` updated: B is the
   space default, the four looks and their shape specs, shared-cast identity rule.
2. Type: Fredoka and Mitr in `.mp/fonts` (after นน's go-ahead to download), `template.html` loads them, a shared
   `riseLine`/`digits` text helper in the kit.
3. Camera module in the kit (moves, log zoom, parallax, drift) with a check page.
4. Motion helpers in the kit (`spring`, `kick`, squash, anticipation, stagger, two clocks) with a check page.
5. `record.cjs` subframe motion blur (flag, default on for finals).
6. Beat-sheet template plus a contact-sheet tool that renders one still per beat into an HTML page.
7. Word-level timing helper (per-scene large-v3, onset snap, phrase fallback).
8. Producer Mode skill (`SKILL.md` and `sequence-and-review.md`; both carry "glow is the default" today) updated: default look B, story-move menu and guard rules, camera
   energy rule, motion rules, beat-sheet format, the contact-sheet gate; the stale "glow is the default" line removed;
   the INBOX line of 2026-10-26 resolved.

## Left to the builder

- Module and function names, file split inside `doc_renderer/gfx_kit/`, check-page design.
- Exact helper signatures, as long as every frame stays a pure function of `t`.
- How the contact-sheet tool finds beat peaks (e.g. a `peak` column in the beat sheet).
- Filling in the A, C and D shape specs from the prototypes.
- Whether the beat sheet lives as a comment header in each world file or as a sidecar file, as long as it is next to
  the world's code and the contact-sheet tool can read it.
