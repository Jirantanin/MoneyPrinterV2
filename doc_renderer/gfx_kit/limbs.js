'use strict';
// Curved, tapering limbs from a handful of numbers: tentacles, tails, kelp, coral branches, eel bodies, vessels.
// (LIBRARY.md "Curved limbs"; first drawn for .mp/kurz_style_film_20261110, the octopus film, 2026-11-11.)
// A limb is grown from its root by walking `len` in `n` steps while the heading turns, so bend and curl give natural
// curled tips and a moving phase gives a travelling wave. Pure geometry: no DOM, no canvas state, nothing random, so the
// same options always give the same shape. It serves both kinds of page:
//   const pts = Limbs.points(o)              the spine: [{ x, y, a, w, s }], a = heading (rad), w = width there, s = 0..1
//   Limbs.fill(ctx, pts, fillStyle, grow)    canvas: one closed fill with round ends
//   Limbs.d(pts, grow)                       SVG: the same outline as a path string, for YP(d, fill, parent)
//   Limbs.outline(pts, grow)                 the outline as [[x, y], ...], if you need to clip or measure
//   Limbs.at(pts, s)                         the spine point at s (0 root .. 1 tip), to attach a hand, a leaf, a light
//   Limbs.dots(pts, { side, from, every, offset, size })   [{ x, y, r }] along one side: suckers, spots, studs
//   Limbs.fillDots(ctx, pts, fillStyle, opts)              canvas shortcut for the same
//     o.x, o.y   root in px                     o.ang   heading at the root, rad (0 right, PI/2 down on a canvas)
//     o.len      length along the spine, px     o.w     width at the root, px
//     o.taper    share of the width lost by the tip, 0..1 (default 0.8; 0 = a tube, 1 = a point)
//     o.tp       taper curve: 1 (default) narrows evenly, above 1 stays thick then narrows late
//     o.bend     turn spread evenly along the limb, rad      o.curl   extra turn packed into the tip (rises with s cubed), rad
//     o.wave     wave amplitude, rad            o.wf    how much wave fits along the limb, rad (default 6, about one cycle)
//     o.ph       wave phase; animate it (ph: -t * 3) and the wave travels root to tip
//     o.waveAll  true = the wave is full strength from the root (a swimming body); default = it grows toward the tip
//     o.n        steps (default 30; use 60 for long bodies)
//   grow (default 1) scales the width only: draw the same pts wider and darker first for a fin fringe or a rim.
// Mirror a limb across a vertical line with ang -> PI - ang, bend -> -bend, curl -> -curl, wave -> -wave.
// For arms that bend at a joint (people), use the people rigs instead: this is for shapes with no elbow.
const Limbs = (() => {
  const HALF = Math.PI / 2;

  function points(o) {
    const n = o.n || 30, pts = [], step = o.len / n, taper = o.taper == null ? 0.8 : o.taper, tp = o.tp || 1;
    let x = o.x, y = o.y;
    for (let i = 0; i <= n; i++) {
      const s = i / n;
      const a = o.ang + (o.bend || 0) * s + (o.curl || 0) * s * s * s
        + (o.wave || 0) * Math.sin(s * (o.wf || 6) + (o.ph || 0)) * (o.waveAll ? 1 : s);
      pts.push({ x, y, a, w: o.w * (1 - taper * Math.pow(s, tp)), s });
      x += Math.cos(a) * step; y += Math.sin(a) * step;
    }
    return pts;
  }

  function outline(pts, grow = 1) {
    const out = [], side = (p, sd) => [p.x + Math.cos(p.a + sd * HALF) * p.w * grow / 2, p.y + Math.sin(p.a + sd * HALF) * p.w * grow / 2];
    const cap = (p, a0) => { for (let k = 1; k < 8; k++) { const a = a0 + Math.PI * k / 8; out.push([p.x + Math.cos(a) * p.w * grow / 2, p.y + Math.sin(a) * p.w * grow / 2]); } };
    for (let i = 0; i < pts.length; i++) out.push(side(pts[i], -1));
    cap(pts[pts.length - 1], pts[pts.length - 1].a - HALF);
    for (let i = pts.length - 1; i >= 0; i--) out.push(side(pts[i], 1));
    cap(pts[0], pts[0].a + HALF);
    return out;
  }

  const d = (pts, grow = 1) => outline(pts, grow).map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ') + ' Z';

  function fill(ctx, pts, style, grow = 1) {
    const o = outline(pts, grow);
    ctx.beginPath();
    o.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
    ctx.closePath();
    ctx.fillStyle = style; ctx.fill();
  }

  function at(pts, s) {
    const f = Math.max(0, Math.min(1, s)) * (pts.length - 1), i = Math.min(pts.length - 2, Math.floor(f)), k = f - i, p = pts[i], q = pts[i + 1];
    return { x: p.x + (q.x - p.x) * k, y: p.y + (q.y - p.y) * k, a: p.a + (q.a - p.a) * k, w: p.w + (q.w - p.w) * k, s: p.s + (q.s - p.s) * k };
  }

  // side: 1 or -1 (which edge), from: first s, every: steps between dots, offset: share of the width off the spine,
  // size: dot radius as a share of the width there, min: smallest radius in px
  function dots(pts, { side = 1, from = 0.45, every = 4, offset = 0.22, size = 0.16, min = 2.4 } = {}) {
    const out = [];
    for (let i = Math.ceil(from * (pts.length - 1)); i < pts.length - 1; i += every) {
      const p = pts[i];
      out.push({ x: p.x + Math.cos(p.a + side * HALF) * p.w * offset, y: p.y + Math.sin(p.a + side * HALF) * p.w * offset, r: Math.max(min, p.w * size) });
    }
    return out;
  }

  function fillDots(ctx, pts, style, opts) {
    ctx.fillStyle = style;
    dots(pts, opts).forEach(q => { ctx.beginPath(); ctx.arc(q.x, q.y, q.r, 0, Math.PI * 2); ctx.fill(); });
  }

  return { points, outline, d, fill, at, dots, fillDots };
})();
