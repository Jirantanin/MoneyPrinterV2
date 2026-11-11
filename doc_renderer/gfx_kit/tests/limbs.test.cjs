// limbs.js: the spine is exactly `len` long whatever the bend, the tip heading is ang + bend + curl, the width tapers
// as asked, a mirrored limb is an exact mirror, the wave grows toward the tip unless waveAll, the outline is one closed
// shape of the right size for both canvas and SVG, dots stay inside the limb, and nothing depends on anything but options
// (values from the vm are compared as JSON: its arrays belong to another realm, so deepStrictEqual would reject equal ones)
const assert = require('assert');
const { loadPure, run } = require('./harness.cjs');

const near = (a, b, tol, msg) => assert(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b} (tol ${tol})`);
const spineLen = pts => pts.slice(1).reduce((s, p, i) => s + Math.hypot(p.x - pts[i].x, p.y - pts[i].y), 0);
const area = poly => Math.abs(poly.reduce((s, p, i) => { const q = poly[(i + 1) % poly.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0)) / 2;

run(async () => {
  const { Limbs } = loadPure(['limbs.js'], ['Limbs']);
  const HALF = Math.PI / 2;

  // a straight limb: tip where expected, widths from w to w * (1 - taper)
  const straight = Limbs.points({ x: 100, y: 200, ang: 0, len: 300, w: 40, taper: 0.75 });
  const even = Limbs.points({ x: 0, y: 0, ang: 0, len: 100, w: 40, taper: 0.8 });
  assert.strictEqual(straight.length, 31, 'default n is 30 steps');
  near(straight[30].x, 400, 1e-9, 'straight tip x'); near(straight[30].y, 200, 1e-9, 'straight tip y');
  near(straight[0].w, 40, 1e-9, 'root width'); near(straight[30].w, 10, 1e-9, 'tip width');
  near(Limbs.points({ x: 0, y: 0, ang: 0, len: 100, w: 40 })[30].w, 8, 1e-9, 'default taper is 0.8');
  near(Limbs.points({ x: 0, y: 0, ang: 0, len: 100, w: 40, taper: 0 })[30].w, 40, 1e-9, 'taper 0 is a tube');
  const late = Limbs.points({ x: 0, y: 0, ang: 0, len: 100, w: 40, taper: 0.8, tp: 2 });
  assert(late[15].w > even[15].w, 'tp above 1 stays thick longer');

  // length is kept and the heading adds up, however it bends, curls or waves
  for (const o of [{ bend: 1.2 }, { curl: 2.6 }, { bend: -0.5, curl: 2.2 }, { wave: 0.5, ph: 1.3 }, { bend: 0.4, curl: -1.5, wave: 0.4, wf: 9, waveAll: true, n: 60 }]) {
    const pts = Limbs.points(Object.assign({ x: 50, y: 60, ang: HALF, len: 240, w: 36 }, o));
    near(spineLen(pts), 240, 1e-6, `length kept for ${JSON.stringify(o)}`);
    if (!o.wave) near(pts[pts.length - 1].a, HALF + (o.bend || 0) + (o.curl || 0), 1e-9, `tip heading for ${JSON.stringify(o)}`);
  }

  // mirror across the vertical line x = 0
  const L = Limbs.points({ x: -70, y: 10, ang: HALF + 0.6, len: 180, w: 40, bend: 0.5, curl: 2.4, wave: 0.2, ph: 0.7 });
  const R = Limbs.points({ x: 70, y: 10, ang: Math.PI - (HALF + 0.6), len: 180, w: 40, bend: -0.5, curl: -2.4, wave: -0.2, ph: 0.7 });
  L.forEach((p, i) => { near(p.x, -R[i].x, 1e-9, `mirror x at ${i}`); near(p.y, R[i].y, 1e-9, `mirror y at ${i}`); });

  // the wave grows toward the tip by default and is even with waveAll
  const dev = (o, i) => Math.abs(Limbs.points(Object.assign({ x: 0, y: 0, ang: 0, len: 400, w: 20, wave: 0.6, wf: 12, ph: HALF, n: 40 }, o))[i].a);
  assert(dev({}, 4) < dev({ waveAll: true }, 4) * 0.2, 'near the root the default wave is small');
  near(Math.abs(Limbs.points({ x: 0, y: 0, ang: 0, len: 400, w: 20, wave: 0.6, wf: 0, ph: HALF, waveAll: true })[0].a), 0.6, 1e-9, 'waveAll is full strength at the root');

  // the phase moves the shape but nothing else does: same options, same points
  const A = Limbs.points({ x: 0, y: 0, ang: 0, len: 200, w: 30, wave: 0.4, ph: 0.2 }), B = Limbs.points({ x: 0, y: 0, ang: 0, len: 200, w: 30, wave: 0.4, ph: 0.2 });
  assert.deepStrictEqual(JSON.parse(JSON.stringify(A)), JSON.parse(JSON.stringify(B)), 'pure in its options');
  assert(Math.abs(Limbs.points({ x: 0, y: 0, ang: 0, len: 200, w: 30, wave: 0.4, ph: 1.4 })[30].y - A[30].y) > 1, 'phase moves the tip');

  // outline: a closed shape whose area matches a tapering bar with two half-disc ends
  const ol = Limbs.outline(straight);
  const expect = 300 * (40 + 10) / 2 + Math.PI * 20 * 20 / 2 + Math.PI * 5 * 5 / 2;
  near(area(ol), expect, expect * 0.02, 'outline area');
  near(area(Limbs.outline(straight, 1.5)), 300 * (60 + 15) / 2 + Math.PI * 30 * 30 / 2 + Math.PI * 7.5 * 7.5 / 2, expect * 0.05, 'grow widens only');
  assert(Math.min(...ol.map(p => p[0])) < 100 - 19 && Math.max(...ol.map(p => p[0])) > 400 + 4, 'both ends are rounded past the spine');

  // SVG path and canvas fill draw that same outline
  const path = Limbs.d(straight);
  assert(/^M[-\d.]+,[-\d.]+( L[-\d.]+,[-\d.]+)+ Z$/.test(path) && !/NaN/.test(path), 'd() is a closed M/L path');
  assert.strictEqual(path.split(' L').length, ol.length, 'd() has every outline point');
  const calls = [], ctx = { beginPath() { calls.push('b'); }, closePath() { calls.push('c'); }, moveTo(x, y) { calls.push([x, y]); }, lineTo(x, y) { calls.push([x, y]); }, fill() { calls.push('f:' + this.fillStyle); }, arc() { calls.push('a'); } };
  Limbs.fill(ctx, straight, '#f98a2c');
  assert.strictEqual(calls[0], 'b'); assert.strictEqual(calls[calls.length - 1], 'f:#f98a2c'); assert.strictEqual(calls[calls.length - 2], 'c');
  assert.strictEqual(JSON.stringify(calls.filter(Array.isArray)), JSON.stringify(ol), 'fill() traces the outline');

  // at(): root, tip and halfway
  near(Limbs.at(straight, 0).x, 100, 1e-9, 'at 0'); near(Limbs.at(straight, 1).x, 400, 1e-9, 'at 1'); near(Limbs.at(straight, 0.5).x, 250, 1e-9, 'at 0.5');
  near(Limbs.at(straight, 0.5).w, 25, 1e-9, 'at 0.5 width'); near(Limbs.at(straight, 7).x, 400, 1e-9, 'at clamps');

  // dots sit on the asked side, inside the limb, from the asked place on
  const curled = Limbs.points({ x: 0, y: 0, ang: HALF, len: 200, w: 44, curl: 2.5 });
  const ds = Limbs.dots(curled, { side: 1, from: 0.5, every: 4 });
  assert(ds.length >= 3, 'some dots');
  for (const q of ds) {
    const p = curled.reduce((best, c) => (Math.hypot(c.x - q.x, c.y - q.y) < Math.hypot(best.x - q.x, best.y - q.y) ? c : best));
    assert(p.s >= 0.5 - 1e-9, 'dots start at from');
    assert(Math.hypot(p.x - q.x, p.y - q.y) + q.r <= p.w / 2 + 1e-6, 'a dot stays inside the limb');
    assert((q.x - p.x) * Math.cos(p.a + HALF) + (q.y - p.y) * Math.sin(p.a + HALF) > 0, 'dots are on side 1');
  }
  const arcs = []; Limbs.fillDots({ beginPath() {}, fill() {}, arc(x, y, r) { arcs.push([x, y, r]); } }, curled, '#fff', { side: 1, from: 0.5, every: 4 });
  assert.strictEqual(JSON.stringify(arcs), JSON.stringify(ds.map(q => [q.x, q.y, q.r])), 'fillDots draws dots()');
});
