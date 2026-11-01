# <world name> beat sheet

Copy next to the world's code as `<world>.beats.md`. Times are world seconds, the page time the world is recorded at
(start from the speech-map phrase times, then run `python scripts/beat_word_times.py <scene.wav> <scene_script.txt>
<world>.beats.md --offset <scene start in the world> --write` once per scene). Check with
`node doc_renderer/gfx_kit/contact_sheet.cjs <page.html> "<scene&f=…>" <world>.beats.md <outdir>` and send นน
`<outdir>/contact.html` before recording (LIBRARY.md "Beat sheet and contact sheet").

## DIRECTION
Look (B for space, D for history unless นน chose another), this world's palette, sizes of the main pieces at 1x, the
light direction. Point at the shared shape and type specs in LIBRARY.md instead of restating them.

## CONCEPTS
One card per abstract claim in this world (a claim with no look of its own); leave the section out when there is none.
Fill it before designing the shot (LIBRARY.md "Concept devices"):

- **claim:** the narration line, as spoken
- **property to see:** what the viewer must notice (finite / endless, same / different, before / after, broken …)
- **device and thing:** a device C1–C14, the everyday thing used, and why that thing already carries the property
- **where it lies:** what the picture gets wrong; if it is more than the narration admits, use C12 instead

## BEATS
One row per line or trigger word. `story move` starts with its number from LIBRARY.md "Story moves" (1–14; "push-in"
is not a story move). `camera` starts with a move from cam.js: push, pull, punch, dive, track, tilt, whip, cut, drift
(= hold), shake. A drift row names what changes. `peak` is the second the beat looks fullest (empty = time + 0.4).
Every world has at least one 2 (scale reveal) and one 3 (make it personal).

| time | peak | trigger | story move | camera | what changes | text | sound |
|---|---|---|---|---|---|---|---|
| 3.2 |  | "แปดนาที" | 5 counter | punch-in 1.0→1.15, 0.5 s | 8:20 slams 1.7x→1x and starts ticking | — | tick |
| 5.6 |  | "คุณ" | 3 personal | dive 1x→2.3x, 1 s | pin drops and squashes; จุก looks 0.25 s before | ประเทศไทย | pin tap |

## GOTCHAS
Traps met while building this world (for example: "the darkness front must speed up near Earth or it takes 13 s to
cross"). Move the ones that apply to other worlds into LIBRARY.md.
