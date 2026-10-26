// Type (LIBRARY.md "Type"): Fredoka 600/700 for numbers and Latin, Mitr for Thai. Load after cast.js, motion.js and
// cam.js; the C sticker container also uses cast_rig.js (call time only).
//   riseLine(parent, x, y, size, runs, t0, o) -> {g, update(t, z)}
//     runs [[text, kind, color]]: kind 'th' | 'num' | 'latin'; color a TYPE key ('teal' | 'gold' | 'white').
//     The line rises 1.3x its height through a clip on ease-out-quint (0.55 s) and never fades in whole. Its container
//     arrives with it on a spring: by look A underline bar, B dark pill, C cream sticker, D torn paper strip.
//     update(t, z) counter-scales by the camera zoom z when the line hangs on a world object (z = 1 on the HUD).
//   digits(parent, cx, y, size, {color, weight, align}) -> {g, set(str, color?)}   fixed-width slots, so a ticking number
//     never jitters; align 'right' pins the last slot at cx (counters whose digit count changes)
//   slam(t, t0, energy) -> scale    a number slams from 1.7x to 1x on a spring
// Letter-spacing only on Latin caps; never on Thai (the marks detach from their consonants).
const TYPE = { teal: '#8fd8e6', gold: '#ffd98a', white: '#ffffff', pill: 'rgb(6,20,40)', pillOpacity: .62, th: 'Mitr', num: 'Fredoka',
  thWeight: 500, thHeadWeight: 600, numWeight: 700, latinWeight: 600, tracking: 5,
  onLight: { white: '#3a2230', teal: '#1f7f8f', gold: '#a8740c' } };   // C and D put dark ink on a light container
const TYPE_CONTAINER = { A: 'underline', B: 'pill', C: 'sticker', D: 'paper' };
let TYPE_N = 0;

function riseLine(parent, x, y, size, runs, t0, { anchor = 'middle', container, padX = 30, energy = 'peak' } = {}) {
  const kind = container || TYPE_CONTAINER[(Y.look && Y.look.style) || 'A'], light = kind === 'sticker' || kind === 'paper';
  const g = el('g', { opacity: 0 }, parent), h = size * 1.25;
  const txt = el('text', { x: 0, y: 0, 'text-anchor': anchor, 'font-size': size });
  for (const [s, k, c] of runs) {
    const a = { 'font-family': k === 'th' ? TYPE.th : TYPE.num, fill: light ? TYPE.onLight[c] || c : TYPE[c] || c,
      'font-weight': k === 'th' ? (size >= 56 ? TYPE.thHeadWeight : TYPE.thWeight) : k === 'num' ? TYPE.numWeight : TYPE.latinWeight };
    if (k === 'latin') a['letter-spacing'] = TYPE.tracking;
    el('tspan', a, txt, s);
  }
  g.appendChild(txt); const bb = txt.getBBox(); g.removeChild(txt);
  const bx = bb.x - padX, bw = bb.width + padX * 2, by = -h * .78 - 10, bh = h + 20, cx = bx + bw / 2;
  const box = el('g', { 'data-part': 'container', 'data-kind': kind }, g);
  if (kind === 'pill') el('rect', { x: bx, y: by, width: bw, height: bh, rx: bh / 2, fill: TYPE.pill, 'fill-opacity': TYPE.pillOpacity }, box);
  if (kind === 'underline') el('rect', { x: bx + 20, y: by + bh - 8, width: bw - 40, height: 5, rx: 2.5, fill: TYPE.gold }, box);
  if (kind === 'sticker') { YP(rigRR(bx, by, bw, bh, 18), CAST_ID.sticker, box, { opacity: .45, transform: 'translate(7,8)' });
    YP(rigRR(bx, by, bw, bh, 18), '#fffaf2', box, { stroke: CAST_ID.ink, 'stroke-width': 5 }); }
  if (kind === 'paper') { const R = rng(97 + TYPE_N), pts = [];
    for (let i = 0; i <= 12; i++) pts.push([bx + bw * i / 12, by + (R() - .5) * 5]);
    for (let i = 12; i >= 0; i--) pts.push([bx + bw * i / 12, by + bh + (R() - .5) * 5]);
    YP('M' + pts.map(q => q.map(v => v.toFixed(1)).join(',')).join('L') + 'Z', '#F3E9CF', box, { transform: 'rotate(-1.2)' }); }
  const clipped = Y_clipTo(g, rigRR(bx, by - 6, bw, bh + 6, 0)), textG = el('g', { 'data-part': 'lineText' }, clipped);
  textG.appendChild(txt); TYPE_N++;
  return { g, update(t, z = 1) {
    const k = eoq(p(t, t0, t0 + .55)), s = t < t0 ? 0 : clamp(spring(t - t0 + .05, ENERGY[energy].zeta, ENERGY[energy].hz), 0, 1.2);
    set(g, { opacity: t < t0 ? 0 : 1, transform: `translate(${x},${y}) ${screenScale(z)}` });
    set(textG, { transform: `translate(0,${(h * 1.3 * (1 - k)).toFixed(2)})` });
    set(box, { transform: kind === 'underline' ? `translate(${cx},0) scale(${s.toFixed(3)},1) translate(${-cx},0)` : `translate(${cx},${by + bh / 2}) scale(${s.toFixed(3)}) translate(${-cx},${-(by + bh / 2)})` });
  } };
}
const eoq = x => 1 - Math.pow(1 - x, 5);

function digits(parent, cx, y, size, { color = 'white', weight = 700, align = 'center' } = {}) {
  const g = el('g', {}, parent), slots = [];
  const w = c => c === ':' || c === '.' ? .3 : c === '°' ? .34 : c === '-' || c === '−' ? .42 : /[A-Z]/.test(c) ? .62 : .58;
  return { g, set(str, c = color) {
    const chars = [...str];
    while (slots.length < chars.length) slots.push(el('text', { 'font-family': TYPE.num, 'font-weight': weight, 'font-size': size, 'text-anchor': 'middle' }, g));
    const ws = chars.map(ch => w(ch) * size), tot = ws.reduce((a, b) => a + b, 0);
    let x = align === 'right' ? cx - tot : cx - tot / 2;
    slots.forEach((e, i) => { if (i < chars.length) { e.textContent = chars[i]; set(e, { x: (x + ws[i] / 2).toFixed(1), y, fill: TYPE[c] || c, opacity: 1 }); x += ws[i]; }
      else set(e, { opacity: 0 }); });
  } };
}

const slam = (t, t0, energy = 'peak') => 1.7 - .7 * spring(t - t0, ENERGY[energy].zeta, ENERGY[energy].hz);
