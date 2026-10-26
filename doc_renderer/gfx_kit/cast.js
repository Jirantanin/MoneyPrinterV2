// Base layers and drawing shorthands for new explainer pages (lifted 2026-10-26 from the copies in cosmic-year-humans and
// dinosaurs-never-died; those episodes keep their own copies). Load after kit.js, library.js, finish.js, glow.js and
// flat.js. SVG only; build once, render(t) only sets attributes.
//
// LOOK  Y_init(look) takes the world's palette plus look.style: 'A' storybook glow, 'B' flat geometric (default for
//   space episodes; installs flat.js), 'C' kawaii sticker, 'D' paper collage (default for history). See LIBRARY.md "Looks".
// LAYERS  Y.bg < Y.cam (world) < Y.fg (foreground) < frame (vignette + grain) < Y.hud < Y.top. Text is fixed to the
//   screen (Y.hud); camera moves come from cam.js.
//
//   Y_init(look)                 page.html calls it. look: {style, rim, shade, light:[dx,dy], warm, warmCore, hot,
//                                glowWarm, accent, cool, deep, vig, vigOpacity, grain}
//   Y_layer(parent) -> g         a parallax layer; Y_par(g, x, y, s, px, py) places it (scale s about px, py)
//   Y_lit(parent, d, fill, o)    look A: rim-in-shape; look B: flat three tones (flat.js). Returns the body group
//   Y_lgrad / Y_rgrad(stops, o)  gradient fills -> 'url(#..)'

const Y = { svg: null, defs: null, bg: null, cam: null, fg: null, frameG: null, hud: null, top: null, frameU: null };
window.Y_SCENES = window.Y_SCENES || {};
let Y_N = 0;
const Y_id = pre => `y${pre}${Y_N++}`;
const Yf = v => (+v).toFixed(1);


function Y_init(look = {}) {
  const L = Object.assign({ style: 'A', rim: '#9fe8ff', shade: '#050818', light: [-14, -10], warm: '#ffb35c', warmCore: '#ffe9c4',
    hot: '#fff6e6', glowWarm: '#ffb35c', accent: '#ff6f61', cool: '#7fb8ff', deep: '#050818', vig: '#03040e',
    vigOpacity: .72, grain: .06 }, look);
  theme({ bg: ['#000', '#000', '#000'], nebula: [], stars: [0, 0, 0] });
  const { svg, defs } = stage();
  finishDefs(svg, { rim: L.rim, shade: L.shade, light: L.light, warm: L.warm, warmCore: L.warmCore, vig: L.vig,
    vigOpacity: L.vigOpacity, dust: [L.hot, L.warm] });
  glowDefs(svg, { hot: L.hot, warm: L.glowWarm, accent: L.accent, cool: L.cool, deep: L.deep, vig: L.vig,
    vigOpacity: L.vigOpacity, grain: L.grain });
  Y.svg = svg; Y.defs = defs; Y.look = L;
  if (L.style === 'B') FL_install();
  Y.bg = el('g', {}, svg); Y.cam = el('g', {}, svg); Y.fg = el('g', {}, svg);
  Y.frameG = el('g', {}, svg); Y.hud = el('g', {}, svg); Y.top = el('g', {}, svg);
  const n0 = svg.childNodes.length, u = glowFrame(svg, {});
  [...svg.childNodes].slice(n0).forEach(e => Y.frameG.appendChild(e));
  Y.frameU = u;
  return svg;
}

// ---------------------------------------------------------------- drawing shorthands
const YP = (d, fill, parent, extra = {}) => el('path', { d, fill, ...extra }, parent);
const YC = (cx, cy, r, fill, parent, extra = {}) => el('circle', { cx, cy, r, fill, ...extra }, parent);
const YE = (cx, cy, rx, ry, fill, parent, extra = {}) => el('ellipse', { cx, cy, rx, ry, fill, ...extra }, parent);
const YS = (d, stroke, w, parent, extra = {}) => el('path', { d, fill: 'none', stroke, 'stroke-width': w,
  'stroke-linecap': 'round', 'stroke-linejoin': 'round', ...extra }, parent);

function Y_lgrad(stops, o = {}) {
  const id = Y_id('lg');
  Y.defs.insertAdjacentHTML('beforeend', `<linearGradient id="${id}" x1="${o.x1 ?? 0}" y1="${o.y1 ?? 0}" x2="${o.x2 ?? 0}" y2="${o.y2 ?? 1}"${o.user ? ' gradientUnits="userSpaceOnUse"' : ''}>` +
    stops.map(([off, c, op = 1]) => `<stop offset="${off}" stop-color="${c}" stop-opacity="${op}"/>`).join('') + '</linearGradient>');
  return `url(#${id})`;
}
function Y_rgrad(stops, o = {}) {
  const id = Y_id('rg');
  const geo = o.user ? ` gradientUnits="userSpaceOnUse" cx="${o.cx}" cy="${o.cy}" r="${o.r}"${o.fx != null ? ` fx="${o.fx}" fy="${o.fy}"` : ''}`
    : ` cx="${o.cx ?? '50%'}" cy="${o.cy ?? '50%'}" r="${o.r ?? '50%'}"`;
  Y.defs.insertAdjacentHTML('beforeend', `<radialGradient id="${id}"${geo}>` +
    stops.map(([off, c, op = 1]) => `<stop offset="${off}" stop-color="${c}" stop-opacity="${op}"/>`).join('') + '</radialGradient>');
  return `url(#${id})`;
}
function Y_clip(shapeHtml) {
  const id = Y_id('c');
  Y.defs.insertAdjacentHTML('beforeend', `<clipPath id="${id}">${shapeHtml}</clipPath>`);
  return `url(#${id})`;
}
const Y_clipTo = (parent, d) => el('g', { 'clip-path': Y_clip(`<path d="${d}"/>`) }, parent);
function Y_blurF(sd) {
  const id = Y_id('bf');
  Y.defs.insertAdjacentHTML('beforeend', `<filter id="${id}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="${sd}"/></filter>`);
  return `url(#${id})`;
}

// rim-in-shape light (from the 2026-10-19 study): returns the shifted, clipped body group
function Y_lit(parent, d, fill, { rim = Y.look.rim, dx = 10, dy = 8, rimOpacity = 1 } = {}) {
  const g = el('g', {}, parent);
  YP(d, rim, g, { opacity: rimOpacity });
  const body = el('g', { transform: `translate(${dx},${dy})` }, Y_clipTo(g, d));
  YP(d, fill, body);
  return body;
}

// ---------------------------------------------------------------- camera and parallax
const Y_layer = (parent, extra = {}) => el('g', extra, parent);
// place a layer: shift (x, y), then scale s about the screen point (px, py)
function Y_par(g, x = 0, y = 0, s = 1, px = KW / 2, py = KH / 2) {
  set(g, { transform: `translate(${Yf(px)},${Yf(py)}) scale(${(+s).toFixed(4)}) translate(${Yf(-px + x)},${Yf(-py + y)})` });
}

// ---------------------------------------------------------------- random helpers
const Y_pts = (n, seed, box) => { const R = rng(seed); return Array.from({ length: n }, () => [box[0] + R() * box[2], box[1] + R() * box[3], R(), R()]); };
// a smooth closed blob through n points around (cx, cy)
function Y_blob(cx, cy, rx, ry, seed, n = 9, amp = .18) {
  const R = rng(seed), pts = [];
  for (let i = 0; i < n; i++) { const a = i / n * 6.2832, k = 1 + (R() - .5) * 2 * amp; pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); }
  let d = '';
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
    if (!i) d += `M${Yf(p1[0])},${Yf(p1[1])}`;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6], c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${Yf(c1[0])},${Yf(c1[1])} ${Yf(c2[0])},${Yf(c2[1])} ${Yf(p2[0])},${Yf(p2[1])}`;
  }
  return d + 'Z';
}
// a ridge line across [x0, x1] at height y with seeded bumps, closed down to yb
function Y_ridge(x0, x1, y, amp, seed, yb, step = 120) {
  const R = rng(seed); let d = `M${x0},${yb} L${x0},${Yf(y + (R() - .5) * amp)}`;
  let px = x0, py = y;
  for (let x = x0 + step; x <= x1 + step; x += step) {
    const ny = y + (R() - .5) * amp, mx = (px + x) / 2;
    d += ` Q${Yf(px + step * .5)},${Yf(py)} ${Yf(mx + step * .25)},${Yf((py + ny) / 2)}`;
    px = x; py = ny;
  }
  return d + ` L${x1 + step},${yb}Z`;
}

