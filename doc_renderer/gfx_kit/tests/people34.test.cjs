// people34.js: feet on the ground line, the returned head top is the drawn top (hair, bun, hat; both head scales),
// dir -1 is an exact mirror, a reachable arm target puts the hand on it, blinks are short and seeded
const assert = require('assert');
const { loadPure, run } = require('./harness.cjs');

// a 2D context stub: keeps the transform and a clip box, samples every path (curves and arcs too) in world coordinates
function stubCtx() {
  let m = [1, 0, 0, 1, 0, 0], clip = null, path = [], cur = [0, 0];
  const stack = [], fills = [], strokes = [];
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
    fills, strokes,
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
    // a stroke keeps its path box; cel's shade fill (fillRect under the clip) is recorded as the clip box, marked rect
    stroke() { strokes.push({ style: this.strokeStyle, ...box(path) }); },
    fillRect() { if (clip) fills.push({ style: this.fillStyle, rect: true, ...clip }); },
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

  // the front view (since 2026-11-05): the same checks for every costume and both head scales
  for (const [s, dir] of [[.4, 1], [.4, -1], [1.3, 1]]) {
    for (const key of Object.keys(C)) for (const hs of [1, 1.28]) {
      const ctx = stubCtx(), P = People34.rig(ctx);
      const r = P.person({ view: 'front', x: 500, y: 900, s, dir, C: C[key], hs, seed: 2, eyes: 'open', mouth: 'grin' }, 1.7);
      const f = body(ctx.fills);
      near(Math.max(...f.map(q => q.y1)), 900, .5, `front ${key} s ${s} hs ${hs}: shoes on the ground line`);
      near(Math.min(...f.map(q => q.y0)), r.top, 2 * s, `front ${key} s ${s} hs ${hs}: returned top is the drawn top`);
    }
  }
  const drawF = dir => { const ctx = stubCtx(); People34.rig(ctx).person({ view: 'front', x: 500, y: 900, s: .5, dir, C: C.dad, seed: 3 }, 2.2); return body(ctx.fills); };
  const RF = drawF(1), LF = drawF(-1);
  near(Math.min(...LF.map(q => q.x0)), 1000 - Math.max(...RF.map(q => q.x1)), .01, 'front mirror, left edge');
  near(Math.max(...LF.map(q => q.x1)), 1000 - Math.min(...RF.map(q => q.x0)), .01, 'front mirror, right edge');
  for (const dir of [1, -1]) {   // armL is the -x arm, armR the +x arm (before dir); a reachable target puts each hand on it
    const r = People34.rig(stubCtx()).person({ view: 'front', x: 400, y: 1000, s: .6, dir, C: C.dad, armR: { x: 150, y: -1000 }, armL: { x: -260, y: -600 } }, .4);
    near(r.handR.x, 400 + dir * .6 * 150, .01, `front dir ${dir}: right hand x`); near(r.handR.y, 1000 - .6 * 1000, .01, `front dir ${dir}: right hand y`);
    near(r.handL.x, 400 - dir * .6 * 260, .01, `front dir ${dir}: left hand x`); near(r.handL.y, 1000 - .6 * 600, .01, `front dir ${dir}: left hand y`);
  }

  // blush: opaque cheek discs on the face in both views, off with C.blush false
  for (const view of ['tq', 'front']) {
    const on = stubCtx(); People34.rig(on).person({ view, x: 500, y: 900, s: .5, C: C.mom, seed: 1 }, 1);
    const cheeks = on.fills.filter(q => q.style === '#ff8aa6');
    assert(cheeks.length >= (view === 'front' ? 2 : 1), `${view}: cheeks drawn`);
    for (const q of cheeks) assert(q.y0 > 900 - .5 * 1000 && q.y1 < 900 - .5 * 800, `${view}: cheek on the face`);
    const off = stubCtx(); People34.rig(off).person({ view, x: 500, y: 900, s: .5, C: { ...C.mom, blush: false }, seed: 1 }, 1);
    assert.strictEqual(off.fills.filter(q => q.style === '#ff8aa6').length, 0, `${view}: blush false draws no cheeks`);
  }

  // a dress reaches the knee (local -300) in both views, with the legs showing below it
  for (const view of ['tq', 'front']) {
    const ctx = stubCtx(); People34.rig(ctx).person({ view, x: 500, y: 900, s: .5, C: { ...C.mom, belly: false }, seed: 1 }, 1);
    const hem = ctx.fills.filter(q => q.style === C.mom.top && Math.abs(q.y1 - (900 - .5 * 300)) < .5 * 12);   // cel's lit copy sits 8 units up
    assert(hem.length >= 1, `${view}: the dress hem at the knee`);
    assert(ctx.fills.some(q => q.style === C.mom.pants && q.y1 > 900 - .5 * 60), `${view}: legs under the dress`);
  }

  // a belly bulges the torso forward (tq) and shows as a lighter disc on the dress (front)
  { const bulge = belly => { const ctx = stubCtx(), P = People34.rig(ctx); P.person({ x: 500, y: 900, s: .5, dir: 1, C: C.mom, belly, seed: 1 }, 1);
      return ctx.fills.filter(q => q.rect && q.style === P.dk(C.mom.top, .86) && q.y0 > 900 - .5 * 620 && q.y1 < 900 - .5 * 420); };
    assert.strictEqual(bulge(false).length, 0, 'no belly, no bulge');
    assert(bulge(true).some(q => q.x1 - 500 >= .5 * 150), 'the belly bulges forward of the dress');
    const ctx = stubCtx(), P = People34.rig(ctx); P.person({ view: 'front', x: 500, y: 900, s: .5, C: C.mom, seed: 1 }, 1);
    assert(ctx.fills.some(q => q.style === P.dk(C.mom.top, .93) && q.x0 < 500 && q.x1 > 500), 'front belly disc on the dress'); }

  // a plain shirt has long sleeves that end in a lighter cuff, one at each hand
  { const ctx = stubCtx(), P = People34.rig(ctx);
    const r = P.person({ view: 'front', x: 500, y: 900, s: .5, C: C.dad, seed: 1 }, 1);
    const cuffs = ctx.fills.filter(q => q.style === P.lt(P.dk(C.dad.top, .9), .35));
    const nearHand = (q, h) => Math.hypot((q.x0 + q.x1) / 2 - h.x, (q.y0 + q.y1) / 2 - h.y) < .5 * 70;
    assert(cuffs.some(q => nearHand(q, r.handL)) && cuffs.some(q => nearHand(q, r.handR)), 'a cuff at each hand'); }

  // world-fixed light (since 2026-11-06): dir 1 and dir -1 under one light are mirror shapes with the lit side unchanged.
  // cel's lit copy is the shape moved toward the light and clipped to it, so it sits flush with the shape on the lit side.
  const litSide = (fills, col, k) => {
    const dark = fills.filter(q => q.rect && q.style === dk(col, k)).sort((a, b) => (b.x1 - b.x0) * (b.y1 - b.y0) - (a.x1 - a.x0) * (a.y1 - a.y0))[0];
    const lit = fills.filter(q => !q.rect && q.style === col && q.x0 >= dark.x0 - .01 && q.x1 <= dark.x1 + .01 && q.y0 >= dark.y0 - .01 && q.y1 <= dark.y1 + .01)
      .sort((a, b) => (b.x1 - b.x0) - (a.x1 - a.x0))[0];
    return (lit.x0 - dark.x0) < (dark.x1 - lit.x1) ? -1 : 1;
  };
  const dk = People34.rig(stubCtx()).dk;
  for (const view of ['tq', 'front']) for (const light of [undefined, -1, 1]) {
    const draw2 = dir => { const ctx = stubCtx(); People34.rig(ctx).person({ view, x: 500, y: 900, s: .5, dir, light, C: C.off, seed: 3 }, 2.2); return body(ctx.fills); };
    const A = draw2(1), B = draw2(-1), want = light > 0 ? 1 : -1, tag = `${view} light ${light}`;
    const shapes = f => f.filter(q => q.rect);
    assert.strictEqual(shapes(A).length, shapes(B).length, `${tag}: same pieces`);
    shapes(A).forEach((q, i) => { const r = shapes(B)[i]; near(r.x0, 1000 - q.x1, .01, `${tag}: piece ${i} mirrored`); near(r.y0, q.y0, .01, `${tag}: piece ${i} same height`); });
    assert.strictEqual(litSide(A, C.off.top, .8), want, `${tag} dir 1: the jacket is lit from the light side`);
    assert.strictEqual(litSide(B, C.off.top, .8), want, `${tag} dir -1: the jacket is lit from the light side`);
    assert.strictEqual(litSide(A, C.off.pants, .8), want, `${tag} dir 1: the trousers too`);
    assert.strictEqual(litSide(B, C.off.pants, .8), want, `${tag} dir -1: the trousers too`);
    if (view === 'tq') for (const [dir, f] of [[1, A], [-1, B]]) {
      const sh = f.filter(q => q.style === dk(C.off.skin, .92));
      assert(sh.length === 1, `${tag} dir ${dir}: one head shade`);
      if (dir === want) {    // facing the light: the shade band is the back of the head, away from the light
        assert(((sh[0].x0 + sh[0].x1) / 2 - 500) * want < 0, `${tag} dir ${dir}: head shade away from the light`);
      } else {               // facing away: the face stays lit, the shade is only a thin rim on the side away from the light
        const face = sh[0], lit = f.filter(q => q.style === C.off.skin && q.x0 >= face.x0 - .01 && q.x1 <= face.x1 + .01 && q.y0 >= face.y0 - .01 && q.y1 <= face.y1 + .01)
          .filter(q => q.x1 - q.x0 > .5 * (face.x1 - face.x0)).pop(), rim = want < 0 ? face.x1 - lit.x1 : lit.x0 - face.x0;
        assert(lit && lit.x1 - lit.x0 > .9 * (face.x1 - face.x0), `${tag} dir ${dir}: the face is lit across`);
        assert(rim > 0 && rim <= .5 * 1.28 * 8, `${tag} dir ${dir}: shade rim ${rim.toFixed(2)} px is thin and away from the light`);
      }
    }
  }
  // cel outside person() keeps the old local +x light
  { const ctx = stubCtx(), P = People34.rig(ctx); P.person({ x: 500, y: 900, s: .5, dir: 1, C: C.off }, 1); ctx.fills.length = 0;
    P.cel(P.ell(0, 0, 50, 50), '#808080'); assert.strictEqual(litSide(ctx.fills, '#808080', .8), 1, 'cel outside person(): lit toward +x'); }

  // the near sleeve (three-quarter) is one shade under the top, so an arm across the chest reads against it
  for (const key of ['off', 'dad', 'sci', 'kid']) {
    const ctx = stubCtx(), P = People34.rig(ctx);
    P.person({ x: 500, y: 900, s: .5, dir: 1, C: C[key], seed: 1, armN: { x: 60, y: -560 } }, 1);
    const sx = 500 + .5 * -58 * (C[key].narrow || 1), sy = 900 - .5 * 768;
    const sleeve = ctx.fills.filter(q => q.style === P.dk(C[key].top, .86) && q.x0 <= sx && q.x1 >= sx && q.y0 <= sy && q.y1 >= sy);
    assert(sleeve.length >= 1, `${key}: near sleeve in dk(top, .86) at the shoulder`);
    assert.notStrictEqual(P.dk(C[key].top, .86), C[key].top, `${key}: sleeve differs from the top`);
  }

  // look moves the pupils (the far eye less), lookY moves them down; flat is a straight mouth
  const eyes = (view, dir, look, lookY) => { const ctx = stubCtx(), P = People34.rig(ctx);
    P.person({ view, x: 500, y: 900, s: .5, dir, C: C.dad, seed: 1, look, lookY }, 1);
    return ctx.fills.filter(q => q.style === '#20182c' && q.y1 - q.y0 > 6).sort((a, b) => (b.x1 - b.x0) - (a.x1 - a.x0)); };
  assert(!People34.rig(stubCtx()).blinkOn(1, 1), 'the eye checks run on an open frame');
  for (const dir of [1, -1]) {
    const e0 = eyes('tq', dir, 0, 0), e1 = eyes('tq', dir, 6, 4), cx = q => (q.x0 + q.x1) / 2, cy = q => (q.y0 + q.y1) / 2;
    const dn = (cx(e1[0]) - cx(e0[0])) * dir, df = (cx(e1[1]) - cx(e0[1])) * dir;
    near(dn, .5 * 1.28 * 6, .3, `tq dir ${dir}: near pupil moves with look`);
    assert(df > .3 && df < dn, `tq dir ${dir}: far pupil moves less (${df.toFixed(2)} < ${dn.toFixed(2)})`);
    near(cy(e1[0]) - cy(e0[0]), .5 * 1.28 * 4, .5, `tq dir ${dir}: lookY moves the pupil down`);
    const byX = e => e.slice(0, 2).sort((p, q) => p.x0 - q.x0), f0 = byX(eyes('front', dir, 0, 0)), f1 = byX(eyes('front', dir, -6, 0));
    for (let i = 0; i < 2; i++) near((cx(f1[i]) - cx(f0[i])) * dir, -.5 * 1.28 * 6, .3, `front dir ${dir}: eye ${i} moves with look`);
  }
  for (const view of ['tq', 'front']) {
    const mouth = m => { const ctx = stubCtx(); People34.rig(ctx).person({ view, x: 500, y: 900, s: .5, C: C.dad, seed: 1, mouth: m }, 1); return ctx.strokes.filter(q => q.style === '#6b1f2b'); };
    const fl = mouth('flat'), sm = mouth('smile');
    assert(fl.length === 1 && fl[0].x1 - fl[0].x0 > 10 && fl[0].y1 - fl[0].y0 < 1, `${view}: flat mouth is one short straight stroke`);
    assert(sm.length === 1 && sm[0].y1 - sm[0].y0 > 4, `${view}: smile still curves`);
  }

  // the walk (o.walk, since 2026-11-13): through a whole cycle a shoe stays on the ground line, the head top is the drawn
  // top, the head never rises above the standing height, and the planted (lowest, flat) shoe does not slide: its world x
  // moves back exactly as far as the body is said to have walked
  for (const key of Object.keys(C)) {
    const CY = 4 * 494 * Math.sin(.38), s = .5, stand = People34.rig(stubCtx()).person({ x: 500, y: 900, s, C: C[key], seed: 2 }, 0).top;
    for (let i = 0; i < 24; i++) {
      const ctx = stubCtx(), r = People34.rig(ctx).person({ x: 500, y: 900, s, C: C[key], seed: 2, walk: CY * i / 24 }, 0), f = body(ctx.fills);
      near(Math.max(...f.map(q => q.y1)), 900, 6 * s + .5, `walk ${key} ${i}: a shoe on the ground line`);
      near(Math.min(...f.map(q => q.y0)), r.top, 2 * s, `walk ${key} ${i}: returned top is the drawn top`);
      assert(r.top >= stand - 4 * s, `walk ${key} ${i}: the head never rises above standing height`);
    }
    const shoeX = d => { const ctx = stubCtx(); People34.rig(ctx).person({ x: 500, y: 900, s, C: C[key], seed: 2, walk: d }, 0);
      return ctx.fills.filter(q => q.style === C[key].shoe && Math.abs(q.y1 - 900) < .5).map(q => q.x0)[0]; };
    const a = shoeX(CY * .05), b = shoeX(CY * .25);   // the near leg is in its stance through both
    near(a - b, s * CY * .2, .5, `walk ${key}: the planted shoe stays where it is on the ground`);
  }

  // walkAmt 0 is the standing figure; a partial amount keeps a shoe on the ground and the swing foot never goes below it
  { const st = (o => { const ctx = stubCtx(); const r = People34.rig(ctx).person(o, 0); return [r.top, body(ctx.fills)]; });
    const [t0, f0] = st({ x: 500, y: 900, s: .5, C: C.off, seed: 2 }), [t1, f1] = st({ x: 500, y: 900, s: .5, C: C.off, seed: 2, walk: 300, walkAmt: 0 });
    near(t1, t0, .01, 'walkAmt 0: standing head top'); assert.strictEqual(f1.length, f0.length, 'walkAmt 0: the standing shapes');
    for (const amt of [.3, .7, 1]) for (let i = 0; i < 40; i++) { const [, f] = st({ x: 500, y: 900, s: .5, C: C.kid, seed: 2, walk: 733 * i / 40, walkAmt: amt });
      const low = Math.max(...f.map(q => q.y1)); assert(low <= 900.6 && low >= 899.4, `walkAmt ${amt} step ${i}: lowest point ${low.toFixed(2)} is the ground line`); } }

  // blinks: 0.14 s every 3.45 s on average, decided by the seed alone
  const P = People34.rig(stubCtx());
  let on = 0; for (let i = 0; i < 6900; i++) on += P.blinkOn(i / 100, 5) ? 1 : 0;
  near(on / 6900, .14 / 3.45, .012, 'blink share');
  assert.strictEqual(P.blinkOn(12.34, 7), People34.rig(stubCtx()).blinkOn(12.34, 7), 'seeded');
});
