# Explainer graphics library

Rule (นน, 2026-10-13): "ไม่หยิบของเดิมมาใช้ตลอด ใช้แค่เฉพาะที่เหมือนกันจริงๆ เท่านั้น เพื่อกันซ้ำกันของแต่ละคลิป
อยากให้แต่ละคลิปมีแนวทางของตัวเอง ไม่ใช่เหมือนกันหมด"

Reuse a piece only when it is the same thing in every episode. Each episode draws its own metaphor, props,
characters and compositions, and picks its own look with `theme()`.

## Three layers

| Layer | Where | Reuse |
|---|---|---|
| Tools the viewer never sees: easing, `lerpPt`, `bump`, `mixColor`, `track`, `camera`, `chip`, `burst` | `kit.js` | Always |
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
| Truth tags | `truthTag(parent, 'compare'/'suppose', x, y)`, `truthTag(parent, 'scale')`, `.update(t, tIn, tOut)`; `supposeFrame(parent)` | `เปรียบเทียบ` on an analogy that could be read as data, `สมมติ` for the whole hypothetical, `ภาพประกอบ ไม่ตามสเกล` on orbits, maps, sizes | restyling them: their fixed look ignores `theme()` so viewers recognise them |
| Counter | `counter(parent, x, y, {size, suffix})`, `.update(t, steps, climb)` | numbers the narration says; a drop or rewind is a step (swap) | counting through values nobody says; the climb guard throws if a climb counts down or misses its spoken landing value |

## Each episode's own look

`theme({...})` before building sets the background gradient, nebula blobs (or none), star counts and colours, and
palette overrides. Without it the kit draws its original violet space, so older pages render unchanged.
`library_demo.html` shows the same cast under three example themes (`space`, `ocean`, `dusk`); they are examples,
not presets to pick from.

Record the choice in the plan as `visual_rules.art_direction` (palette, background, recurring metaphor, camera and
motion language, topic characters) and make it visibly different from the last three episodes; see the
producer-mode skill, sequence-and-review.md.
