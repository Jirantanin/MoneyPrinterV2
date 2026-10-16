// Paper-collage art direction: a torn-paper Canvas 2D layer under the kit's SVG (decided by นน 2026-10-16 from the
// Hatshepsut S10/S14 test). Load after kit.js. The episode draws its own cut-outs with these tools; the SVG on top keeps
// the shared pieces with fixed looks (truthTag, counter, footer) exactly as in every other episode.
//   paperStage(svg)                 canvas behind the stage() svg; call right after stage()
//   paperFrame(t)                   clear + set the boil clocks for this frame; returns ctx. Call first in render(t)
//   paper(pts, fill, id, o)         a torn cut-out: deckle edge under a jittered fill, then pencil hatch / speckle / fibre
//   pline(pts, color, w, id, o)     a hand-drawn stroke (carved lines, rope, cracks)
//   ptag(text, x, y, k, id, o)      a label on a torn strip (Kanit 900), k = pop scale from the kit's pop()
//   pgrid(pts, step, o)             graph-paper lines clipped to a sheet
//   pflame(x, y, s, t, id)          a cut-paper torch flame that flickers
//   pnight(lights, o)               darkness over the frame with soft holes at the light sources (torch pools)
//   pfinish(o)                      paper grain + vignette, last
//   ellPts / starPts / rectPts / centroid / pbez   point helpers
// Boil: props re-jitter every 2 frames at 25 fps, o.slow pieces (backdrops, walls) every 6. Every frame is a pure
// function of t: jitter comes from prng(id, boil), never Math.random.

const PAPER = { fps: 25, deckle: '#F4EDDC', ink: '#2A1C12', tagPaper: '#F3E9CF', grain: .12, vig: .24, font: 'Kanit' };
let pctx = null, pcv = null, PBOIL = 0, PSLOW = 0, PTEX = null;

function prng(...k) { let h = 2166136261; for (const v of k) { h ^= Math.round(v * 977) | 0; h = Math.imul(h, 16777619); } return rng(h); }
const pbez = (p0, p1, p2, u) => [(1 - u) * (1 - u) * p0[0] + 2 * u * (1 - u) * p1[0] + u * u * p2[0],
                                 (1 - u) * (1 - u) * p0[1] + 2 * u * (1 - u) * p1[1] + u * u * p2[1]];
// spring(t, zeta, hz): 0 -> 1 with overshoot, pure in t (zeta 1 no bounce, .7 premium, .5 playful)
function spring(t, zeta = .7, hz = 2) {
  if (t <= 0) return 0; const w = 2 * Math.PI * hz;
  if (zeta >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * w * t) * (Math.cos(wd * t) + (zeta * w / wd) * Math.sin(wd * t));
}
// kick(t, amp): a decaying wobble that starts at t = 0 (impacts, landings, shakes)
const kick = (t, amp, decay = 5, hz = 3) => t <= 0 ? 0 : amp * Math.exp(-t * decay) * Math.sin(t * hz * 2 * Math.PI);
const ellPts = (cx, cy, rx, ry = rx, n = 30, a0 = 0, a1 = Math.PI * 2) => Array.from({ length: n }, (_, i) => {
  const a = a0 + (a1 - a0) * i / (Math.abs(a1 - a0 - Math.PI * 2) < 1e-6 ? n : n - 1); return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]; });
const starPts = (cx, cy, R, r = R * .42) => Array.from({ length: 10 }, (_, i) => {
  const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r : R; return [cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]; });
const rectPts = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
const centroid = pts => { let x = 0, y = 0; pts.forEach(q => { x += q[0]; y += q[1]; }); return [x / pts.length, y / pts.length]; };

function paperStage(svg, o = {}) {
  Object.assign(PAPER, o);
  pcv = document.createElement('canvas'); pcv.width = KW; pcv.height = KH;
  pcv.style.cssText = 'position:absolute;left:0;top:0';
  document.body.insertBefore(pcv, svg); svg.style.position = 'relative';
  pctx = pcv.getContext('2d');
  PTEX = paperTextures();
  return pctx;
}
function paperTextures() {
  const pat = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d')); return pctx.createPattern(c, 'repeat'); };
  const hatch = pat(260, 260, g => { const r = rng(11); g.lineCap = 'round';
    for (let i = 0; i < 600; i++) { const x = r() * 260, y = r() * 260, l = 6 + r() * 18, a = -1.05 + (r() - .5) * .3;
      g.strokeStyle = r() < .5 ? `rgba(255,255,255,${.05 + r() * .06})` : `rgba(0,0,0,${.05 + r() * .07})`;
      g.lineWidth = .8 + r() * 1.3; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke(); } });
  const speck = pat(200, 200, g => { const r = rng(13);
    for (let i = 0; i < 700; i++) { g.fillStyle = r() < .55 ? `rgba(40,20,15,${.12 + r() * .2})` : `rgba(255,240,230,${.12 + r() * .2})`;
      g.beginPath(); g.arc(r() * 200, r() * 200, .6 + r() * 1.8, 0, 7); g.fill(); } });
  const fiber = pat(320, 320, g => { const r = rng(17);                   // papyrus-like crossed fibre strips
    for (let i = 0; i < 46; i++) { const y = r() * 320; g.strokeStyle = `rgba(90,60,20,${.04 + r() * .05})`; g.lineWidth = 2 + r() * 5;
      g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(100, y + (r() - .5) * 8, 220, y + (r() - .5) * 8, 320, y); g.stroke(); }
    for (let i = 0; i < 30; i++) { const x = r() * 320; g.strokeStyle = `rgba(255,250,235,${.05 + r() * .05})`; g.lineWidth = 2 + r() * 4;
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x + (r() - .5) * 6, 320); g.stroke(); } });
  const grain = document.createElement('canvas'); grain.width = KW; grain.height = KH;
  const g = grain.getContext('2d'), img = g.createImageData(KW, KH), r = rng(23);
  for (let i = 0; i < KW * KH; i++) { const v = 128 + (r() - .5) * 110; img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v; img.data[i * 4 + 3] = 255; }
  g.putImageData(img, 0, 0);
  return { hatch, speck, fiber, grain };
}
function paperFrame(t) {
  const f = Math.max(0, Math.floor(t * PAPER.fps + 1e-6));
  PBOIL = Math.floor(f / 2); PSLOW = Math.floor(f / 6);
  pctx.setTransform(1, 0, 0, 1, 0, 0); pctx.clearRect(0, 0, KW, KH);
  return pctx;
}

function pdensify(pts, step, closed = true) {
  const out = [], n = pts.length, m = closed ? n : n - 1;
  for (let i = 0; i < m; i++) { const a = pts[i], b = pts[(i + 1) % n], k = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let j = 0; j < k; j++) out.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]); }
  if (!closed) out.push(pts[n - 1]);
  return out;
}
const pjit = (pts, amp, r) => pts.map(q => [q[0] + (r() - .5) * 2 * amp, q[1] + (r() - .5) * 2 * amp]);
function ppath(pts) { pctx.beginPath(); pts.forEach((q, i) => i ? pctx.lineTo(q[0], q[1]) : pctx.moveTo(q[0], q[1])); pctx.closePath(); }
function ptexture(o) {
  const c = pctx; c.save();
  c.globalAlpha = o.tex ?? 1; c.fillStyle = PTEX.hatch; c.fill();
  if (o.speck) { c.globalAlpha = 1; c.fillStyle = PTEX.speck; c.fill(); }
  if (o.fiber) { c.globalAlpha = 1; c.fillStyle = PTEX.fiber; c.fill(); }
  c.restore();
}
// o: {edge: false, edgeW 5, edgeAmp 2.8, edgeColor, amp 1.2, step 8, tex 1, speck, fiber, slow}
function paper(pts, fill, id, o = {}) {
  const b = o.slow ? PSLOW : PBOIL, dense = pdensify(pts, o.step || 8);
  if (o.edge !== false) {
    ppath(pjit(dense, o.edgeAmp ?? 2.8, prng(id, b, 1)));
    pctx.lineJoin = 'round'; pctx.lineWidth = o.edgeW ?? 5; pctx.strokeStyle = o.edgeColor || PAPER.deckle; pctx.stroke();
  }
  ppath(pjit(dense, o.amp ?? 1.2, prng(id, b, 2)));
  pctx.fillStyle = fill; pctx.fill(); ptexture(o);
}
// o: {amp 1, slow, dash: [on, off]}
function pline(pts, color, width, id, o = {}) {
  const d = pjit(pdensify(pts, 7, false), o.amp ?? 1, prng(id, o.slow ? PSLOW : PBOIL, 3)), c = pctx;
  c.save(); if (o.dash) c.setLineDash(o.dash);
  c.beginPath(); d.forEach((q, i) => i ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1]));
  c.lineCap = 'round'; c.lineJoin = 'round'; c.strokeStyle = color; c.lineWidth = width; c.stroke(); c.restore();
}
// o: {size 46, rot -.02, paper, ink}
function ptag(text, x, y, k, id, o = {}) {
  if (k <= 0) return;
  const size = o.size || 46, c = pctx;
  c.save(); c.translate(x, y); c.rotate(o.rot ?? -.02); c.scale(k, k);
  c.font = `900 ${size}px ${PAPER.font}`; const w = c.measureText(text).width + size * 1.1, h = size * 1.55;
  paper(rectPts(-w / 2, -h / 2, w / 2, h / 2), o.paper || PAPER.tagPaper, id, { edgeW: 4, edgeAmp: 2.6, amp: 1.4, step: 9, tex: .6, edgeColor: '#FFF8EA' });
  c.fillStyle = o.ink || PAPER.ink; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, 0, size * .06);
  c.restore();
}
// o: {color '#A9B3D3', alpha .7, width 2}
function pgrid(pts, step = 48, o = {}) {
  const c = pctx, xs = pts.map(q => q[0]), ys = pts.map(q => q[1]);
  c.save(); ppath(pts); c.clip(); c.strokeStyle = o.color || '#A9B3D3'; c.globalAlpha = o.alpha ?? .7; c.lineWidth = o.width || 2;
  for (let x = Math.min(...xs); x < Math.max(...xs); x += step) { c.beginPath(); c.moveTo(x, Math.min(...ys)); c.lineTo(x, Math.max(...ys)); c.stroke(); }
  for (let y = Math.min(...ys); y < Math.max(...ys); y += step) { c.beginPath(); c.moveTo(Math.min(...xs), y); c.lineTo(Math.max(...xs), y); c.stroke(); }
  c.restore();
}
// A flame cut from three papers; flickers on the boil clock. (x, y) = base of the flame.
function pflame(x, y, s, t, id) {
  const c = pctx, fl = 1 + .08 * Math.sin(t * 17 + id) + .05 * Math.sin(t * 29 + id * 2);
  c.save(); c.translate(x, y); c.scale(s, s * fl);
  const tongue = (w, h, lean) => [[-w, 0], [-w * .8, -h * .35], [lean * .4 - w * .3, -h * .7], [lean, -h], [w * .35 + lean * .3, -h * .62], [w * .9, -h * .3], [w, 0], [0, w * .5]];
  const lean = 6 * Math.sin(t * 9 + id);
  paper(tongue(26, 96, lean), '#E8743B', id, { edgeW: 3, edgeAmp: 2, amp: 2.4, step: 5, tex: .4, edgeColor: '#F8C470' });
  paper(tongue(17, 66, lean * .8), '#F2A93E', id + 1, { edge: false, amp: 2, step: 5, tex: .3 });
  paper(tongue(9, 36, lean * .5), '#FBE3A0', id + 2, { edge: false, amp: 1.4, step: 4, tex: .2 });
  c.restore();
}
// Darkness with soft light pools. lights: [[x, y, r, strength 0..1]]. o: {dark '#0b0a1f', alpha .5, warm '#ffb460', warmAlpha .16}
function pnight(lights, o = {}) {
  const c = pctx;
  if (!pnight.buf) { pnight.buf = document.createElement('canvas'); pnight.buf.width = KW; pnight.buf.height = KH; }
  const b = pnight.buf.getContext('2d');
  b.globalCompositeOperation = 'source-over'; b.clearRect(0, 0, KW, KH);
  b.globalAlpha = o.alpha ?? .5; b.fillStyle = o.dark || '#0b0a1f'; b.fillRect(0, 0, KW, KH); b.globalAlpha = 1;
  b.globalCompositeOperation = 'destination-out';
  for (const [x, y, r, k = 1] of lights) { const g = b.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(0,0,0,${k})`); g.addColorStop(.55, `rgba(0,0,0,${k * .55})`); g.addColorStop(1, 'rgba(0,0,0,0)');
    b.fillStyle = g; b.fillRect(x - r, y - r, r * 2, r * 2); }
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(pnight.buf, 0, 0);
  c.globalCompositeOperation = 'soft-light';
  for (const [x, y, r, k = 1] of lights) { const g = c.createRadialGradient(x, y, 0, x, y, r * .8);
    g.addColorStop(0, o.warm || '#ffb460'); g.addColorStop(1, 'rgba(255,180,96,0)');
    c.globalAlpha = (o.warmAlpha ?? .5) * k; c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2); }
  c.restore();
}
function pfinish(o = {}) {
  const c = pctx; c.save(); c.setTransform(1, 0, 0, 1, 0, 0);
  c.globalCompositeOperation = 'overlay'; c.globalAlpha = o.grain ?? PAPER.grain;
  c.drawImage(PTEX.grain, (PBOIL % 3) * -7, (PBOIL % 2) * -5, KW + 14, KH + 10);
  c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
  const vg = c.createRadialGradient(KW / 2, KH / 2, KH * .45, KW / 2, KH / 2, KW * .62);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, `rgba(0,0,0,${o.vig ?? PAPER.vig})`); c.fillStyle = vg; c.fillRect(0, 0, KW, KH);
  c.restore();
}
