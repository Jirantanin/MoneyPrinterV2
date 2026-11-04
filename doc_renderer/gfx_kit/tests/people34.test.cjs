// people34.js: feet on the ground line, the returned head top is the drawn top (hair, bun, hat; both head scales),
// dir -1 is an exact mirror, a reachable arm target puts the hand on it, blinks are short and seeded
const assert = require('assert');
const { loadPure, run } = require('./harness.cjs');

// a 2D context stub: keeps the transform and a clip box, samples every path (curves and arcs too) in world coordinates
function stubCtx() {
  let m = [1, 0, 0, 1, 0, 0], clip = null, path = [], cur = [0, 0];
  const stack = [], fills = [];
  const mul = n => { const [a, b, c, d, e, f] = m; m = [a * n[0] + c * n[1], b * n[0] + d * n[1], a * n[2] + c * n[3], b * n[2] + d * n[3], a * n[4] + c * n[5] + e, b * n[4] + d * n[5] + f]; };
  const pt = (x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  const add = (x, y) => { path.push(pt(x, y)); cur = [x, y]; };
  const box = pts => ({ x0: Math.min(...pts.map(p => p[0])), x1: Math.max(...pts.map(p => p[0])), y0: Math.min(...pts.map(p => p[1])), y1: Math.max(...pts.map(p => p[1])) });
  const arcPts = (x, y, rx, ry, rot, a0, a1, ccw) => {
    let span = a1 - a0; if (ccw && span > 0) span -= Math.PI * 2; if (!ccw && span < 0) span += Math.PI * 2;
    if (Math.abs(a1 - a0) >= Math.PI * 2 - 1e-9) span = Math.PI * 2;
    for (let i = 0; i <= 32; i++) { const a = a0 + span * i / 32, ex = Math.cos(a) * rx, ey = Math.sin(a) * ry;
      add(x + ex * Math.cos(rot) - ey * Math.sin(rot), y + ex * Math.sin(rot) + ey * Math.cos(rot)); }
  };
  return {
    fills,
    save() { stack.push([m.slice(), clip]); }, restore() { [m, clip] = stack.pop(); },
    translate(x, y) { mul([1, 0, 0, 1, x, y]); }, scale(x, y) { mul([x, 0, 0, y, 0, 0]); },
    rotate(r) { mul([Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0]); },
    beginPath() { path = []; }, closePath() {}, moveTo: add, lineTo: add,
    bezierCurveTo(a, b, c, d, x, y) { const [x0, y0] = cur; for (let i = 1; i <= 16; i++) { const u = i / 16, v = 1 - u;
      add(v * v * v * x0 + 3 * v * v * u * a + 3 * v * u * u * c + u * u * u * x, v * v * v * y0 + 3 * v * v * u * b + 3 * v * u * u * d + u * u * u * y); } },
    quadraticCurveTo(a, b, x, y) { const [x0, y0] = cur; for (let i = 1; i <= 12; i++) { const u = i / 12, v = 1 - u; add(v * v * x0 + 2 * v * u * a + u * u * x, v * v * y0 + 2 * v * u * b + u * u * y); } },
    arc(x, y, r, a0, a1, ccw) { arcPts(x, y, r, r, 0, a0, a1, ccw); },
    ellipse(x, y, rx, ry, rot, a0, a1, ccw) { arcPts(x, y, rx, ry, rot, a0, a1, ccw); },
    fill() { let b = box(path); if (clip) b = { x0: Math.max(b.x0, clip.x0), x1: Math.min(b.x1, clip.x1), y0: Math.max(b.y0, clip.y0), y1: Math.min(b.y1, clip.y1) };
      fills.push({ style: this.fillStyle, ...b }); },
    clip() { const b = box(path); clip = clip ? { x0: Math.max(b.x0, clip.x0), x1: Math.min(b.x1, clip.x1), y0: Math.max(b.y0, clip.y0), y1: Math.min(b.y1, clip.y1) } : b; },
    stroke() {}, fillRect() {},
  };
}
const body = f => f.filter(s => !String(s.style).startsWith('rgba'));   // drop the floor shadow
const near = (a, b, tol, msg) => assert(Math.abs(a - b) <= tol, `${msg}: ${a.toFixed(2)} vs ${b.toFixed(2)}`);

run(async () => {
  const { People34 } = loadPure(['people34.js'], ['People34']);
  const C = People34.CAST;

  for (const [s, dir] of [[.4, 1], [.4, -1], [1.3, 1]]) {
    for (const key of Object.keys(C)) for (const hs of [1, 1.28]) {
      const ctx = stubCtx(), P = People34.rig(ctx);
      const r = P.person({ x: 500, y: 900, s, dir, C: C[key], hs, seed: 2, eyes: 'open', mouth: 'grin' }, 1.7);
      const f = body(ctx.fills);
      near(Math.max(...f.map(q => q.y1)), 900, .5, `${key} s ${s} hs ${hs}: shoes on the ground line`);
      near(Math.min(...f.map(q => q.y0)), r.top, 2 * s, `${key} s ${s} hs ${hs}: returned top is the drawn top`);
    }
  }

  // dir -1 mirrors the whole figure about x
  const draw = dir => { const ctx = stubCtx(); People34.rig(ctx).person({ x: 500, y: 900, s: .5, dir, C: C.sci, seed: 3 }, 2.2); return body(ctx.fills); };
  const R = draw(1), L = draw(-1);
  near(Math.min(...L.map(q => q.x0)), 1000 - Math.max(...R.map(q => q.x1)), .01, 'mirror, left edge');
  near(Math.max(...L.map(q => q.x1)), 1000 - Math.min(...R.map(q => q.x0)), .01, 'mirror, right edge');

  // a reachable target puts the near hand on it (world = feet + dir * s * local)
  for (const dir of [1, -1]) {
    const P = People34.rig(stubCtx()), r = P.person({ x: 400, y: 1000, s: .6, dir, C: C.off, armN: { x: 120, y: -610, bend: -1 } }, .4);
    near(r.nearHand.x, 400 + dir * .6 * 120, .01, `dir ${dir}: hand x`); near(r.nearHand.y, 1000 - .6 * 610, .01, `dir ${dir}: hand y`);
  }

  // blinks: 0.14 s every 3.45 s on average, decided by the seed alone
  const P = People34.rig(stubCtx());
  let on = 0; for (let i = 0; i < 6900; i++) on += P.blinkOn(i / 100, 5) ? 1 : 0;
  near(on / 6900, .14 / 3.45, .012, 'blink share');
  assert.strictEqual(P.blinkOn(12.34, 7), People34.rig(stubCtx()).blinkOn(12.34, 7), 'seeded');
});
