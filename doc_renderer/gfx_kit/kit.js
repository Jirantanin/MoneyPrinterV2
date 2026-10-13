// Flat "explainer" motion-graphic kit: pure functions of time t (seconds), deterministic, SVG.
// Each graphic builds once, then render(t) only sets attributes, so any frame can be seeked.
const NS = 'http://www.w3.org/2000/svg';
const C = {
  yellow: '#ffd23f', orange: '#ff8a3d', pink: '#ff4f8b', teal: '#38e0c8', violet: '#7b5cff', blue: '#3fa9ff',
  white: '#fff6e8', ink: '#211a5e', dim: '#b9b2ff', mint: '#3dd6c0', leaf: '#8be05a', red: '#ff5a4f',
};
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const p = (t, a, b) => clamp((t - a) / (b - a));
const eio = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eo = x => 1 - Math.pow(1 - x, 3);
const back = x => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const pop = (t, a, d = .45) => t < a ? 0 : back(p(t, a, a + d));
const lerp = (a, b, k) => a + (b - a) * k;
function rng(seed) { return () => { seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const sparkle = s => `M0,${-s}Q0,0 ${s},0Q0,0 0,${s}Q0,0 ${-s},0Q0,0 0,${-s}Z`;
const polar = (r, deg) => [r * Math.sin(deg * Math.PI / 180), -r * Math.cos(deg * Math.PI / 180)];
const sector = (r, deg) => { if (deg <= .01) return ''; const [x, y] = polar(r, Math.min(deg, 359.99));
  return `M0,0L0,${-r}A${r},${r} 0 ${deg > 180 ? 1 : 0} 1 ${x},${y}Z`; };
const arcPath = (r, a0, a1) => { const [x0, y0] = polar(r, a0), [x1, y1] = polar(r, a1);
  return `M${x0},${y0}A${r},${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1},${y1}`; };

function el(tag, attrs = {}, parent = null, text = null) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}
function set(e, attrs) { for (const k in attrs) e.setAttribute(k, attrs[k]); }
const show = (e, o) => e.setAttribute('opacity', clamp(o).toFixed(3));

// ---------------------------------------------------------------- stage
// Frame size: landscape episode graphics by default; call kitSize(1080, 1920) before building for vertical Shorts
// (and record with --size 1080x1920).
let KW = 1920, KH = 1080;
function kitSize(w, h) { KW = w; KH = h; }
function stage() {
  const svg = el('svg', { viewBox: `0 0 ${KW} ${KH}`, width: KW, height: KH }, document.body);
  const defs = el('defs', {}, svg);
  defs.innerHTML = `
    <radialGradient id="bg" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#2b1f6e"/><stop offset=".55" stop-color="#171245"/><stop offset="1" stop-color="#0a0820"/></radialGradient>
    <radialGradient id="vig" cx="50%" cy="50%" r="70%"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#050414" stop-opacity=".6"/></radialGradient>
    <radialGradient id="flash"><stop offset="0" stop-color="#fffbe6"/><stop offset=".35" stop-color="${C.yellow}"/><stop offset="1" stop-color="${C.orange}" stop-opacity="0"/></radialGradient>
    <radialGradient id="sunG" cx="40%" cy="35%"><stop offset="0" stop-color="#fff3b0"/><stop offset="1" stop-color="${C.orange}"/></radialGradient>
    <radialGradient id="redG" cx="40%" cy="35%"><stop offset="0" stop-color="#ffb08a"/><stop offset="1" stop-color="#e2343f"/></radialGradient>
    <radialGradient id="earthG" cx="35%" cy="30%"><stop offset="0" stop-color="#5fd0ff"/><stop offset="1" stop-color="#1f62c9"/></radialGradient>
    <radialGradient id="coreG"><stop offset="0" stop-color="#fff2c8"/><stop offset=".4" stop-color="#ffcf7a" stop-opacity=".8"/><stop offset="1" stop-color="#ff8a3d" stop-opacity="0"/></radialGradient>
    <filter id="blur70" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="12"/></filter>
    <filter id="soft" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="5"/></filter>`;
  return { svg, defs };
}

function background(svg, seed = 11) {
  const R = rng(seed);
  el('rect', { width: KW, height: KH, fill: 'url(#bg)' }, svg);
  const neb = el('g', { filter: 'url(#blur70)' }, svg);
  [[420, 300, 420, 220, C.pink, .2], [1550, 260, 380, 260, C.violet, .32], [1200, 880, 520, 200, C.teal, .12], [300, 900, 360, 200, C.violet, .22]]
    .forEach(([cx, cy, rx, ry, f, o]) => el('ellipse', { cx: cx * KW / 1920, cy: cy * KH / 1080, rx, ry, fill: f, opacity: o }, neb));
  const layers = [70, 45, 22].map((n, L) => {
    const g = el('g', {}, svg);
    const st = [];
    for (let i = 0; i < n; i++) {
      const s = { x: R() * (KW + 280) - 140, y: R() * (KH + 120) - 60, ph: R() * 6.28, sp: 1 + R() * 2.5, base: .3 + R() * .5 };
      const col = R() < .15 ? C.yellow : R() < .2 ? C.teal : '#ffffff', size = [2, 3.2, 5][L] * (.6 + R() * .8);
      s.e = L > 0 && R() < .35 ? el('path', { d: sparkle(size * 2.6), fill: col, transform: `translate(${s.x},${s.y})` }, g)
        : el('circle', { cx: s.x, cy: s.y, r: size, fill: col }, g);
      st.push(s);
    }
    return { g, st, L };
  });
  return t => {
    set(neb, { transform: `translate(${-8 * t},0)` });
    for (const { g, st, L } of layers) {
      set(g, { transform: `translate(${-(L + 1) * 5 * t},${(L + 1) * 1.2 * t})` });
      for (const s of st) s.e.setAttribute('opacity', (s.base * (.55 + .45 * Math.sin(t * s.sp + s.ph))).toFixed(3));
    }
  };
}

function overlays(svg) {
  el('rect', { width: KW, height: KH, fill: 'url(#vig)', 'pointer-events': 'none' }, svg);
}

// ---------------------------------------------------------------- text
// lines: [{text, size, color, weight}], anchor middle; returns {g, update(t, tIn, tOut)}
function chip(parent, x, y, lines, opt = {}) {
  const g = el('g', {}, parent);
  const bg = el('rect', { rx: 0, fill: opt.fill || C.ink, stroke: opt.stroke || '#5a4bd0', 'stroke-width': 4 }, g);
  const ts = [];
  let yy = 0;
  for (const L of lines) {
    yy += L.size * (ts.length ? 1.12 : .82);
    ts.push(el('text', { x: 0, y: yy, 'text-anchor': opt.align || 'middle', 'font-size': L.size, 'font-weight': L.weight || 700,
      fill: L.color || C.white }, g, L.text));
  }
  let laid = false;
  const layout = () => {
    if (laid) return; laid = true;
    let w = 0; for (const e of ts) w = Math.max(w, e.getComputedTextLength());
    const padX = opt.padX ?? 40, padY = opt.padY ?? 22, h = yy + padY * 2 - lines[lines.length - 1].size * .1;
    const x0 = (opt.align === 'start') ? -padX : -w / 2 - padX;
    set(bg, { x: x0, y: -padY, width: w + padX * 2, height: h, rx: Math.min(h / 2, 46) });
    if (opt.plain) bg.setAttribute('opacity', 0);
    g.dataset.h = h;
  };
  return {
    g, layout,
    update(t, tIn, tOut = 1e9, dx = 0, dy = 0) {
      layout();
      const k = pop(t, tIn, .5) * (1 - p(t, tOut, tOut + .4));
      set(g, { transform: `translate(${x + dx},${y + dy}) scale(${Math.max(0, k)})` });
      show(g, k * 3);
    },
  };
}

function label(parent, x, y, text, size, color = C.white, weight = 700, anchor = 'middle') {
  return el('text', { x, y, 'text-anchor': anchor, 'font-size': size, 'font-weight': weight, fill: color }, parent, text);
}

// qualification footer — must stay readable; returns update(t)
function footer(parent, text, tIn = 1.0) {
  const g = el('g', {}, parent);
  el('rect', { x: 0, y: KH - 62, width: KW, height: 62, fill: '#0a0820', opacity: .55 }, g);
  label(g, 64, KH - 22, text, 26, '#d8d3ff', 500, 'start');
  return t => show(g, p(t, tIn, tIn + .6));
}

// ---------------------------------------------------------------- shapes
function planet(parent, r, kind = 'rock', seed = 1) {
  const R = rng(seed);
  const g = el('g', {}, parent);
  const glow = el('circle', { r: r * 1.5, fill: C.yellow, filter: 'url(#glow)', opacity: 0 }, g);
  const outline = el('circle', { r, fill: 'none', stroke: '#8f86ff', 'stroke-width': 3, 'stroke-dasharray': '6 7', opacity: 0 }, g);
  const body = el('g', {}, g);
  const fills = { rock: ['#c98bff', '#8a54d6'], warm: ['#ffb46b', '#e0663a'], earth: ['url(#earthG)', null], gold: ['#ffe07a', '#e9a23b'] };
  const [f1, f2] = fills[kind] || fills.rock;
  el('circle', { r, fill: f1 }, body);
  if (f2) el('path', { d: `M${-r * .2},${-r * .98} A${r},${r} 0 0 1 ${r * .98},${r * .2} A${r * 1.05},${r * 1.05} 0 0 0 ${-r * .2},${-r * .98}Z`, fill: '#fff', opacity: .25 }, body);
  if (kind === 'earth') {
    el('path', { d: `M${-r * .55},${-r * .2} q${r * .3},${-r * .45} ${r * .6},${-r * .1} q${r * .1},${r * .4} ${-r * .3},${r * .45} q${-r * .4},${r * .05} ${-r * .3},${-r * .35}Z`, fill: '#5be08a' }, body);
    el('path', { d: `M${r * .2},${r * .35} q${r * .3},${-r * .15} ${r * .45},${r * .1} q${-r * .1},${r * .3} ${-r * .45},${r * .2}Z`, fill: '#5be08a' }, body);
  } else {
    for (let i = 0; i < 3; i++) el('circle', { cx: (R() - .5) * r * 1.1, cy: (R() - .3) * r * 1.0, r: r * (.12 + R() * .12), fill: '#000', opacity: .16 }, body);
  }
  el('path', { d: `M${r},0 A${r},${r} 0 0 1 ${-r * .3},${r * .95} A${r * 1.25},${r * 1.25} 0 0 0 ${r},0Z`, fill: '#000', opacity: .22 }, body);
  return {
    g, body, glow, outline,
    state({ x = 0, y = 0, s = 1, born = 1, lit = 0, o = 1 }) {
      set(g, { transform: `translate(${x},${y}) scale(${Math.max(0, s)})` });
      show(g, o);
      show(body, born);
      show(outline, (1 - born) * .9);
      show(glow, lit * .55);
    },
  };
}

function burst(parent, n, seed, cols = [C.yellow, C.orange, C.pink, C.teal, C.white], spread = 300) {
  const R = rng(seed);
  const g = el('g', {}, parent);
  const parts = [];
  for (let i = 0; i < n; i++) {
    const a = R() * 6.283, d = spread * (.35 + R() * .75), r = 4 + R() * 10;
    parts.push({ dx: Math.cos(a) * d, dy: Math.sin(a) * d, e: i % 3 ? el('circle', { r, fill: cols[i % cols.length] }, g) : el('path', { d: sparkle(r * 1.8), fill: cols[i % cols.length] }, g) });
  }
  return (t, t0, dur = 1.3) => {
    const k = eo(p(t, t0, t0 + dur));
    for (const q of parts) { set(q.e, { transform: `translate(${q.dx * k},${q.dy * k}) scale(${1 - .6 * k})` }); show(q.e, t < t0 ? 0 : 1 - p(t, t0 + dur * .5, t0 + dur * 1.1)); }
  };
}

// ---------------------------------------------------------------- mascot "จุก": round mint sprout creature
function mascot(parent, x, y, scale = 1) {
  const root = el('g', {}, parent);
  const g = el('g', {}, root);
  el('ellipse', { cx: 0, cy: 2, rx: 40, ry: 8, fill: '#000', opacity: .25 }, g);
  const body = el('g', {}, g);
  el('ellipse', { cx: -16, cy: -6, rx: 13, ry: 8, fill: '#1f8f84' }, body);
  el('ellipse', { cx: 16, cy: -6, rx: 13, ry: 8, fill: '#1f8f84' }, body);
  const sprout = el('g', { transform: 'translate(0,-92)' }, body);
  el('path', { d: 'M0,4 C-2,-10 4,-18 2,-30', fill: 'none', stroke: '#4cb848', 'stroke-width': 6, 'stroke-linecap': 'round' }, sprout);
  el('path', { d: 'M2,-26 C-14,-44 -36,-34 -34,-22 C-22,-16 -8,-18 2,-26Z', fill: C.leaf }, sprout);
  el('path', { d: 'M2,-28 C14,-48 36,-42 36,-30 C24,-22 10,-22 2,-28Z', fill: '#a8f070' }, sprout);
  el('path', { d: 'M-48,-46 C-48,-82 -26,-96 0,-96 C26,-96 48,-82 48,-46 C48,-14 28,-4 0,-4 C-28,-4 -48,-14 -48,-46Z', fill: C.mint }, body);
  el('path', { d: 'M-48,-46 C-48,-14 -28,-4 0,-4 C28,-4 48,-14 48,-46 C40,-24 20,-16 0,-16 C-20,-16 -40,-24 -48,-46Z', fill: '#25b3a3' }, body);
  el('ellipse', { cx: -22, cy: -76, rx: 10, ry: 6, fill: '#fff', opacity: .35, transform: 'rotate(-30 -22 -76)' }, body);
  el('ellipse', { cx: -30, cy: -36, rx: 8, ry: 5, fill: C.pink, opacity: .55 }, body);
  el('ellipse', { cx: 30, cy: -36, rx: 8, ry: 5, fill: C.pink, opacity: .55 }, body);
  const eyes = [-17, 17].map(ex => ({ w: el('ellipse', { cx: ex, cy: -52, rx: 13, ry: 14, fill: '#fff' }, body),
    p: el('ellipse', { cx: ex, cy: -52, rx: 7, ry: 7.5, fill: '#14103a' }, body),
    h: el('circle', { cx: ex + 2, cy: -56, r: 2.6, fill: '#fff' }, body), ex }));
  const mouth = el('path', { d: 'M-7,-30 Q0,-24 7,-30', fill: 'none', stroke: '#14103a', 'stroke-width': 3.5, 'stroke-linecap': 'round' }, body);
  // speech bubble
  const bub = el('g', {}, root);
  el('circle', { cx: -18, cy: 36, r: 7, fill: C.white }, bub);
  el('circle', { r: 40, fill: C.white }, bub);
  const bt = el('text', { y: 21, 'text-anchor': 'middle', 'font-size': 60, 'font-weight': 900, fill: C.ink }, bub, '?');
  return {
    root,
    // st: {in, look:[dx,dy], blink:[t...], hop:[t...], bubble:{ch, tIn, tOut, color}, mouth:'smile'|'o'|'flat', wide, sleep}
    update(t, st = {}) {
      const ein = st.in == null ? 1 : pop(t, st.in, .55);
      let hop = 0;
      for (const h of st.hop || []) hop = Math.max(hop, 40 * Math.sin(Math.PI * p(t, h, h + .45)));
      const bob = 3 * Math.sin(t * 3.4) * (st.sleep ? .3 : 1);
      set(root, { transform: `translate(${x},${y}) scale(${scale})` });
      set(g, { transform: `translate(0,${-hop - bob}) scale(${.4 + .6 * ein}, ${(.4 + .6 * ein) * (1 + .03 * Math.sin(t * 6.8))})` });
      show(g, ein * 4);
      const [lx, ly] = st.look || [0, 0];
      let blink = st.sleep ? .1 : 1;
      for (const b of st.blink || []) if (t > b && t < b + .13) blink = .1;
      const wide = st.wide ? 1 + .2 * p(t, st.wide, st.wide + .15) : 1;
      for (const e of eyes) {
        set(e.w, { ry: 14 * blink * wide, rx: 13 * wide });
        set(e.p, { cx: e.ex + lx * 5, cy: -52 + ly * 5, ry: 7.5 * blink * wide, rx: 7 * wide });
        set(e.h, { cx: e.ex + 2 + lx * 5, cy: -56 + ly * 5 }); show(e.h, blink > .5 ? 1 : 0);
      }
      const m = st.mouth || 'smile';
      set(mouth, { d: m === 'o' ? 'M-6,-30 Q0,-22 6,-30 Q0,-36 -6,-30Z' : m === 'flat' ? 'M-7,-29 L7,-29' : m === 'big' ? 'M-10,-32 Q0,-18 10,-32Z' : 'M-7,-30 Q0,-24 7,-30',
        fill: m === 'o' || m === 'big' ? '#14103a' : 'none' });
      const b = st.bubble;
      if (b) {
        bt.textContent = b.ch;
        set(bt, { fill: b.color || C.ink, 'font-size': b.ch.length > 1 ? 34 : 60, y: b.ch.length > 1 ? 12 : 21 });
        const k = pop(t, b.tIn, .4) * (1 - p(t, b.tOut ?? 1e9, (b.tOut ?? 1e9) + .3));
        set(bub, { transform: `translate(${b.dx ?? -70},${(b.dy ?? -150) - hop}) scale(${Math.max(0, k)}) rotate(${4 * Math.sin(t * 5)})` });
        show(bub, k * 3);
      } else show(bub, 0);
    },
  };
}

// draw-on helper for paths with pathLength=1
const drawOn = (e, k) => e.setAttribute('stroke-dasharray', `${clamp(k)} 2`);

// ---------------------------------------------------------------- scene scaffolding
// base(seed): stage + animated space background + camera group; finish(svg): vignette + HUD layer on top.
function base(seed = 11) {
  const { svg } = stage();
  const bg = background(svg, seed);
  const cam = el('g', {}, svg);
  return { svg, bg, cam };
}
function finish(svg) { overlays(svg); return el('g', {}, svg); }
// camera(cam, scale, pivotX, pivotY, dx, dy): zoom about a pivot (slow push-ins, focus moves)
function camera(cam, s, px = KW / 2, py = KH / 2, dx = 0, dy = 0) {
  set(cam, { transform: `translate(${px + dx},${py + dy}) scale(${s}) translate(${-px},${-py})` });
}
// miniPlanet(parent, x, y, r, fill): the top arc of a small planet for the mascot to stand on (x, y = top point)
function miniPlanet(parent, x, y, r = 200, fill = '#3fa9ff') {
  const g = el('g', {}, parent);
  el('circle', { cx: x, cy: y + r, r, fill }, g);
  el('circle', { cx: x - r * .45, cy: y + r * .55, r: r * .12, fill: '#000', opacity: .15 }, g);
  el('circle', { cx: x + r * .3, cy: y + r * .35, r: r * .08, fill: '#000', opacity: .15 }, g);
  el('path', { d: `M${x - r * .97},${y + r * 1.2} A${r},${r} 0 0 1 ${x},${y}`, fill: 'none', stroke: '#fff', 'stroke-width': 8, opacity: .25, 'stroke-linecap': 'round' }, g);
  return g;
}
