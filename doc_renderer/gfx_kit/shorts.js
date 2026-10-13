// Vertical Shorts (or, with opt { w: 1920, h: 1080, captions: false }, a landscape test cut) on top of kit.js: one continuous 1080x1920 stage, one layer per narration beat (crossfaded at beat
// boundaries) and burned-in captions with keyword highlights. Load order: kit.js, timing.js (window.SHORT from
// scripts/producer_gfx_short.py align), shorts.js, then the page calls bootShort(seed, { b1: build, ... }).
// build(layer, hud, beat) returns render(tl, t): tl = seconds since the beat started (negative during its fade-in).
// Shorts UI covers the top ~200 px, the bottom ~460 px and, from y 900 down, the right ~140 px (buttons):
// keep text and key objects inside SAFE; captions sit at SAFE.capY.
const SAFE = { x0: 70, x1: 950, y0: 230, y1: 1180, cx: 510, capY: 1310 };
const SFX = [];
const sfx = (t, kind, o = {}) => SFX.push([+t.toFixed(3), kind, o]);
// beat-local helpers: k(tl, a, b) pops in at a and out at b; at(name) = absolute time of a script anchor
const kio = (t, a, b = 1e9, d = .5) => Math.max(0, pop(t, a, d) * (1 - p(t, b, b + .35)));
const at = name => { const v = window.SHORT.at[name]; if (v == null) throw new Error('no anchor ' + name); return v; };
function put(g, x, y, s = 1, r = 0) { set(g, { transform: `translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${r.toFixed(2)}) scale(${Math.max(0, s).toFixed(4)})` }); }

function captions(parent, list, keywords, size = 68) {
  const kw = [...keywords].sort((a, b) => b.length - a.length);
  const items = list.map(c => {
    const g = el('g', {}, parent);
    const tx = el('text', { x: 0, y: 0, 'text-anchor': 'middle', 'font-size': size, 'font-weight': 900, fill: C.white,
      stroke: '#0a0820', 'stroke-width': 16, 'stroke-linejoin': 'round', 'paint-order': 'stroke' }, g);
    let rest = c.text;
    while (rest) {
      let best = null;
      for (const k of kw) { const i = rest.indexOf(k); if (i >= 0 && (!best || i < best.i)) best = { i, k }; }
      if (!best) { el('tspan', {}, tx, rest); break; }
      if (best.i) el('tspan', {}, tx, rest.slice(0, best.i));
      el('tspan', { fill: C.yellow }, tx, best.k);
      rest = rest.slice(best.i + best.k.length);
    }
    return { c, g, tx, fit: null };
  });
  return t => {
    for (const it of items) {
      const { t0, t1 } = it.c;
      // the next chunk starts at t1 in the same spot, so the old one leaves within a frame or two (no mushed overlap)
      if (t < t0 - .01 || t > t1 + .04) { show(it.g, 0); continue; }
      if (it.fit == null) { const w = it.tx.getComputedTextLength(); it.fit = Math.min(1, (SAFE.x1 - SAFE.x0) / Math.max(1, w)); }
      const k = back(p(t, t0, t0 + .22)), out = p(t, t1 - .03, t1 + .04);
      put(it.g, SAFE.cx, SAFE.capY + 10 * (1 - k), it.fit * (.86 + .14 * k));
      show(it.g, p(t, t0, t0 + .05) * (1 - out));
    }
  };
}

function shortPage(seed, builders, opt = {}) {
  kitSize(opt.w ?? 1080, opt.h ?? 1920);
  const cx = KW / 2, cy = KH * 900 / 1920;
  const S = window.SHORT, XF = opt.xf ?? .35;
  const { svg } = stage();
  const bg = background(svg, seed);
  const world = el('g', {}, svg);
  overlays(svg);
  const hud = el('g', {}, svg);
  const layers = S.beats.map((b, i) => {
    const wrap = el('g', {}, world), layer = el('g', {}, wrap), lhud = el('g', {}, hud);
    return { b, i, wrap, layer, lhud, r: builders[b.id] ? builders[b.id](layer, lhud, b) : () => {} };
  });
  const cap = opt.captions === false ? () => {} : captions(el('g', {}, hud), S.captions, S.keywords || []);
  const last = layers.length - 1;
  return t => {
    bg(t);
    for (const L of layers) {
      const { b, i } = L;
      const kin = i === 0 ? 1 : eio(p(t, b.start - XF, b.start + .05));
      const kout = i === last ? 0 : eio(p(t, b.end - XF * .5, b.end + XF * .5));
      const o = kin * (1 - kout);
      const vis = o > .001;
      L.wrap.style.display = L.lhud.style.display = vis ? '' : 'none';
      if (!vis) continue;
      set(L.wrap, { transform: `translate(${cx},${cy}) scale(${(.97 + .03 * kin) * (1 + .05 * kout)}) translate(${-cx},${-cy})` });
      show(L.wrap, o); show(L.lhud, o);
      L.r(t - b.start, t);
    }
    cap(t);
  };
}

function bootShort(seed, builders, opt) {
  let render = null;
  window.__ready = document.fonts.load('900 40px Kanit').then(() => document.fonts.load('700 40px Kanit'))
    .then(() => { render = shortPage(seed, builders, opt); render(0); window.__SFX = SFX; return true; });
  window.__seek = t => render(t);
}
