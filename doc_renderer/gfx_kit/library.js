// Shared cast for explainer graphics: only things that are the same thing in every episode (see LIBRARY.md).
// Load after kit.js. Everything else (the episode's metaphor, props, characters, layouts) is drawn fresh per episode.

// ---------------------------------------------------------------- the Sun
// sun(parent, r): glowing disc; state({x, y, s, o, t}) with t driving a slow breathing glow.
function sun(parent, r) {
  const g = el('g', {}, parent);
  const halo = el('circle', { r: r * 1.9, fill: C.orange, opacity: .28, filter: 'url(#blur70)' }, g);
  const glow = el('circle', { r: r * 1.25, fill: C.yellow, opacity: .45, filter: 'url(#glow)' }, g);
  el('circle', { r, fill: 'url(#sunG)' }, g);
  el('circle', { cx: -r * .3, cy: -r * .32, r: r * .32, fill: '#fff', opacity: .3 }, g);
  return {
    g,
    state({ x = 0, y = 0, s = 1, o = 1, t = 0 }) {
      set(g, { transform: `translate(${x},${y}) scale(${Math.max(0, s)})` });
      show(g, o);
      set(halo, { r: r * (1.9 + .06 * Math.sin(t * 1.3)) });
      set(glow, { r: r * (1.25 + .04 * Math.sin(t * 1.7 + 1)) });
    },
  };
}

// ---------------------------------------------------------------- rocks
// rock(parent, r, {seed, fill, craters}): a seeded asteroid/boulder outline. A new seed gives a new rock, so two
// episodes never share the same one: pick a seed and a fill that suit this episode's palette.
function rock(parent, r, { seed = 3, fill = '#9a8fb8', craters = 4 } = {}) {
  const R = rng(seed), g = el('g', {}, parent), pts = [];
  const n = 11 + Math.floor(R() * 5);
  for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2, rr = r * (.76 + R() * .32); pts.push([Math.cos(a) * rr, Math.sin(a) * rr]); }
  const d = 'M' + pts.map(q => q.map(v => v.toFixed(1)).join(',')).join('L') + 'Z';
  el('path', { d, fill: col(fill) }, g);
  el('path', { d, fill: '#000', opacity: .22, transform: `translate(${r * .12},${r * .1}) scale(.92)` }, g);
  for (let i = 0; i < craters; i++) el('circle', { cx: (R() - .5) * r, cy: (R() - .5) * r, r: r * (.08 + R() * .1), fill: '#000', opacity: .18 }, g);
  return g;
}

// ---------------------------------------------------------------- truth tags (fixed look, never themed)
// The viewer must recognise these in every episode, so they ignore theme() and keep one style.
//   truthTag(parent, 'compare', x, y)  analogy that could be read as data       -> เปรียบเทียบ
//   truthTag(parent, 'suppose', x, y)  hypothetical, on screen for all of it   -> สมมติ
//   truthTag(parent, 'scale')          orbit/map/size not to scale (footer)     -> ภาพประกอบ ไม่ตามสเกล
// update(t, tIn, tOut) pops it in and out.
const TRUTH_TAGS = {
  compare: { text: 'เปรียบเทียบ', size: 28, fill: '#211a5e', stroke: '#5a4bd0', color: '#d8d3ff' },
  suppose: { text: 'สมมติ', size: 44, fill: '#3a1430', stroke: '#ff5a4f', color: '#fff6e8' },
};
function truthTag(parent, kind, x, y) {
  if (kind === 'scale') {
    const g = el('g', {}, parent);
    el('rect', { x: 0, y: KH - 62, width: KW, height: 62, fill: '#0a0820', opacity: .55 }, g);
    label(g, 64, KH - 22, 'ภาพประกอบ ไม่ตามสเกล', 26, '#d8d3ff', 500, 'start');
    return { g, update: (t, tIn = 0, tOut = 1e9) => show(g, p(t, tIn, tIn + .6) * (1 - p(t, tOut, tOut + .4))) };
  }
  const s = TRUTH_TAGS[kind];
  if (!s) throw new Error(`truthTag: unknown kind ${kind}`);
  const c = chip(parent, x, y, [{ text: s.text, size: s.size, color: s.color, weight: 900 }],
    { fill: s.fill, stroke: s.stroke, padX: s.size * .7, padY: s.size * .35 });
  return { g: c.g, update: (t, tIn = 0, tOut = 1e9) => c.update(t, tIn, tOut) };
}
// supposeFrame(parent): dashed inner border that marks the whole frame as hypothetical; update(t, k) with k 0..1.
function supposeFrame(parent) {
  const r = el('rect', { x: 18, y: 18, width: KW - 36, height: KH - 36, rx: 22, fill: 'none', stroke: '#ff5a4f',
    'stroke-width': 5, 'stroke-dasharray': '22 16', opacity: 0 }, parent);
  return (t, k) => { show(r, .75 * clamp(k)); set(r, { 'stroke-dashoffset': (-t * 14).toFixed(1) }); };
}

// ---------------------------------------------------------------- number counter
// counter(parent, x, y, {size, suffix}): a big number that only shows values the narration says.
//   update(t, steps, climb)
//     steps: [{at, text, color}] spoken values; the latest step with at <= t is shown and pops when it arrives.
//            A drop or a rewind is a step (swap), never a count down through values nobody says.
//     climb: optional {from, to, a, b, digits}: a rise toward a spoken value (narration says it climbs). It must
//            count up and land on a step's value at exactly b; anything else throws, so a page cannot break the rule.
function counter(parent, x, y, { size = 180, suffix = '%' } = {}) {
  const g = el('g', { transform: `translate(${x},${y})` }, parent);
  const tx = el('text', { 'text-anchor': 'middle', 'font-size': size, 'font-weight': 900, fill: C.white }, g);
  const num = el('tspan', {}, tx, ''), suf = el('tspan', { 'font-size': size * .6, dx: size * .05 }, tx, suffix);
  let checked = null;
  const check = (steps, climb) => {
    if (!(climb.to > climb.from)) throw new Error('counter: a climb must count up; show a drop as a step');
    const land = steps.find(s => s.at === climb.b);
    if (!land || parseFloat(land.text) !== climb.to) throw new Error('counter: a climb must land on a spoken step value at b');
  };
  return {
    g,
    update(t, steps, climb = null) {
      if (climb && checked !== climb) { check(steps, climb); checked = climb; }
      let i = -1;
      for (let k = 0; k < steps.length; k++) if (steps[k].at <= t) i = k;
      const cur = steps[Math.max(0, i)];
      let text = cur.text, fill = col(cur.color || C.white);
      if (climb && t >= climb.a && t < climb.b) {
        const k = eio(p(t, climb.a, climb.b));
        text = (climb.from + (climb.to - climb.from) * k).toFixed(climb.digits ?? 1);
        const last = steps.find(s => s.at === climb.b);
        fill = mixColor(cur.color || C.white, last.color || C.white, k);
      }
      num.textContent = text;
      set(tx, { fill });
      const s = 1 + .14 * (i >= 0 ? bump(t, steps[i].at, .35) : 0);
      set(tx, { transform: `scale(${s.toFixed(3)})` });
    },
  };
}

// ---------------------------------------------------------------- จุก's outfits
// spaceHelmet(m): clear fishbowl dome over จุก and its sprout, with a collar ring and a small antenna light; the eyes stay
// visible. Part of จุก's own kit (the same helmet in every space episode, user decision 2026-10-13); other outfits
// (diving gear, a hard hat…) are drawn per episode on m.back / m.front. update(t, o) fades it, e.g. while putting it on.
function spaceHelmet(m) {
  const fr = el('g', {}, m.front);
  el('ellipse', { cx: 0, cy: -70, rx: 74, ry: 84, fill: '#bfefff', opacity: .14 }, fr);            // glass
  el('ellipse', { cx: 0, cy: -70, rx: 74, ry: 84, fill: 'none', stroke: '#eafcff', 'stroke-width': 4, opacity: .75 }, fr);
  el('path', { d: 'M-52,-104 A62,72 0 0 1 -6,-146', fill: 'none', stroke: '#fff', 'stroke-width': 7, 'stroke-linecap': 'round', opacity: .55 }, fr);
  el('circle', { cx: -58, cy: -82, r: 4, fill: '#fff', opacity: .5 }, fr);
  el('ellipse', { cx: 0, cy: -2, rx: 58, ry: 13, fill: '#8f88c4' }, fr);                          // collar
  el('ellipse', { cx: 0, cy: -6, rx: 58, ry: 9, fill: '#d6d1f2' }, fr);
  el('line', { x1: 40, y1: -138, x2: 52, y2: -166, stroke: '#d6d1f2', 'stroke-width': 4, 'stroke-linecap': 'round' }, fr);
  const lamp = el('circle', { cx: 53, cy: -169, r: 7, fill: C.red }, fr);
  return {
    update(t, o = 1) {
      show(fr, o);
      show(lamp, o * (.55 + .45 * (Math.sin(t * 4) > 0 ? 1 : 0)));
    },
  };
}
