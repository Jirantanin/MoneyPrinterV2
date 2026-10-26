# Producer Mode skill update for the motion spec (apply right after the merge)

The skill lives outside git (`.claude/skills/moneyprinter-producer-mode` is a junction to `~/.codex/skills`, shared live
with every session and Codex), so it is edited only once the kit changes are on `main`. Each item is an exact
replacement; after applying, mark the 2026-10-26 INBOX line (and the `cast.js` part of "helper กลางของ pipeline") done.

## 1. `SKILL.md` (the "Tell the episode mainly with explainer graphics" paragraph)

Replace

> The default look (since 2026-10-16) is glow: flat SVG with the shared finish layer plus `doc_renderer/gfx_kit/glow.js` ("Glow direction" in `gfx_kit/LIBRARY.md`), and every shot is a scene rather than a diagram (since 2026-10-18, "Scenes, not diagrams" in the same file). Choose paper-collage (`doc_renderer/gfx_kit/paper.js`, "Paper-collage direction") instead only when cut, torn or rebuilt paper carries the story.

with

> The look is chosen per episode from four (นน 2026-10-26, `gfx_kit/LIBRARY.md` "Looks"): B flat geometric is the default for space episodes and D paper collage for history episodes; A storybook glow or C kawaii sticker, or swapping a default, only when นน agrees. The shared cast (จุก, Earth, the Sun) keeps its identity in every look. Every shot is a scene rather than a diagram (since 2026-10-18, "Scenes, not diagrams"), and each world is designed as a beat sheet from the story moves, camera moves and motion rules in LIBRARY.md; นน approves each world's contact sheet before it is recorded.

## 2. `references/sequence-and-review.md` (the finish-level paragraph)

Replace

> On top of it the default look since 2026-10-16 is glow (`doc_renderer/gfx_kit/glow.js`, already loaded by `template.html`): `bloom` only small light sources and hot shapes (big bodies get `litDisc`, never a big blurred halo), move light with `flowPath`/`flowBands`, add `glowMotes`, two or three `depthFG` pieces at the frame edges, and `glowFrame` in place of `finishFrame`; check page `glow_demo.html`. Paper-collage (`paper.js`) replaces it only in an episode chosen for paper.

with

> On top of it each episode uses one of four looks (นน 2026-10-26; shape specs in `gfx_kit/LIBRARY.md` "Looks"): B flat geometric (`flat.js`, `Y_init({style: 'B'})`) is the default for space, D paper collage (`paper.js`) for history; A storybook glow (`glow.js`: `bloom` only small light sources, `litDisc` for big bodies, `flowPath`/`flowBands`, `glowMotes`, `depthFG`, `glowFrame`; check page `glow_demo.html`) and C kawaii sticker only when นน agrees. New pages use the kit's `cast.js` base layers, `cast_rig.js` for จุก/Earth/Sun (identity fixed in every look), `cam.js` for the camera, `motion.js` for entrances and springs, and `type.js` (Fredoka for numbers and Latin, Mitr for Thai); demo world `doc_renderer/gfx_kit/motion_demo.html`. Energy: full-energy camera and springs only in the hook and at each world's peak; explanation stretches drift, push and track.

## 3. `references/sequence-and-review.md` (the "Write the beat-by-beat design" sentence)

Replace

> Write the beat-by-beat design anchored to speech times anyway,

with

> Write each world's beat sheet (`<world>.beats.md` from `doc_renderer/gfx_kit/beats_template.md`: DIRECTION, BEATS with `time | peak | trigger | story move | camera | what changes | text | sound`, GOTCHAS; every row names a story move 1–12 and a camera move, every world has a scale reveal and a make-it-personal; trigger times from `python scripts/beat_word_times.py … --write`), then render `node doc_renderer/gfx_kit/contact_sheet.cjs <page> "<scene&f=…>" <world>.beats.md <outdir>` and send นน `contact.html`; record the world only after นน approves it (นน 2026-10-26). Write this design anchored to speech times anyway,

## 4. `references/sequence-and-review.md` (same paragraph, after item 2)

Add

> New pages load the kit's `cast.js`; do not copy `cast.js` into the episode folder any more (a second copy redeclares `const Y` and the page fails to load). Episode-only helpers go in their own file with their own names.
