// people.js: planted feet while walking, "!" on the real head top (hat included), poses, sound times
const assert = require('assert');
const { loadPure, run } = require('./harness.cjs');

// a 2D context stub that keeps the transform and clip and records what is filled, in world coordinates
function stubCtx() {
  let m = [1, 0, 0, 1, 0, 0], clipTop = -Infinity; const stack = [], shapes = []; let path = [];
  const topOf = q => q.top != null ? q.top : q.c[1] - (q.ry != null ? q.ry : q.r);
  const mul = (n) => { const [a, b, c, d, e, f] = m; m = [a * n[0] + c * n[1], b * n[0] + d * n[1], a * n[2] + c * n[3], b * n[2] + d * n[3], a * n[4] + c * n[5] + e, b * n[4] + d * n[5] + f]; };
  const pt = (x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  const sc = () => Math.hypot(m[0], m[1]);
  return {
    shapes,
    save() { stack.push([m.slice(), clipTop]); }, restore() { [m, clipTop] = stack.pop(); },
    translate(x, y) { mul([1, 0, 0, 1, x, y]); }, scale(x, y) { mul([x, 0, 0, y, 0, 0]); },
    rotate(r) { mul([Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0]); },
    beginPath() { path = []; }, closePath() {}, moveTo(x, y) { path.push({ c: pt(x, y), r: 0 }); }, lineTo(x, y) { path.push({ c: pt(x, y), r: 0 }); },
    arc(x, y, r) { path.push({ c: pt(x, y), r: r * sc() }); },
    ellipse(x, y, rx, ry) { path.push({ c: pt(x, y), r: Math.max(rx, ry) * sc(), rx: rx * sc(), ry: ry * sc() }); },
    roundRect(x, y, w, h) { path.push({ c: pt(x + w / 2, y + h / 2), r: 0, top: pt(x, y)[1] }); },
    fill() { shapes.push({ style: this.fillStyle, path, top: Math.max(clipTop, Math.min(...path.map(topOf))) }); }, stroke() {},
    clip() { clipTop = Math.max(clipTop, Math.min(...path.map(topOf))); }, fillRect() {},
  };
}

run(async () => {
  const { People } = loadPure(['people.js'], ['People']);
  assert.deepStrictEqual(Object.keys(People.POSES), ['shock', 'flung', 'cheeks', 'point', 'shrug']);

  // walking: the stance foot stays planted. Feet swap every half cycle (2*L*sin(.42) local units of dist); samples
  // 1/120 s apart that straddle a swap are skipped. A 1.5 L cycle (the old spec) slides 0.2-0.5 px per sample.
  const HALF = 2 * (128 + 118) * Math.sin(.42);
  for (const [s, v, dir] of [[.5, 150, 1], [.6, 140, -1], [.44, 140, 1]]) {
    const ctx = stubCtx(), P = People.rig(ctx);
    const shoes = t => { ctx.shapes.length = 0; P.walker({ x: 100 + dir * v * t, y: 1700, s, dir, dist: v * t / s }, t);
      return ctx.shapes.filter(sh => sh.style === P.pal.shoe && sh.path[0].rx > 20 * s).map(sh => sh.path[0].c); };
    let worst = 0, checked = 0;
    for (let i = 0; i < 240; i++) {
      const d0 = v * i / 120 / s, d1 = v * (i + 1) / 120 / s;
      if (Math.floor(d0 / HALF) !== Math.floor(d1 / HALF)) continue;
      const a = shoes(i / 120), b = shoes((i + 1) / 120);
      assert.strictEqual(a.length, 2, 'two shoes');
      worst = Math.max(worst, Math.min(...a.map((p, k) => Math.hypot(p[0] - b[k][0], p[1] - b[k][1])))); checked++;
    }
    assert(checked > 200, 'enough samples');
    assert(worst < .02, `a planted foot slides ${worst.toFixed(3)} px per sample (s ${s}, v ${v})`);
  }

  // the head top it returns is the drawn top, hat or bun included, so a "!" never lands on the hat
  for (const look of [{}, { hat: 'hard' }, { hat: 'admiral' }, { hairStyle: 'bun' }]) {
    const ctx = stubCtx(), P = People.rig(ctx);
    const p = P.person(Object.assign({ x: 500, y: 1700, s: .6, seed: 3 }, look), 2);
    const drawnTop = Math.min(...ctx.shapes.map(sh => sh.top));
    assert(Math.abs(p.top - drawnTop) < 30, `${JSON.stringify(look)}: top ${p.top.toFixed(0)} vs drawn ${drawnTop.toFixed(0)}`);
  }

  // react blends from the hanging arms; bang reports its sound time
  const same = (a, b, msg) => assert.strictEqual(JSON.stringify(a), JSON.stringify(b), msg);   // vm objects: compare as JSON
  const ev = [], P = People.rig(stubCtx(), { onEvent: (t, k) => ev.push([t, k]) });
  same(P.react('shock', 0).armL, { tx: -150, ty: -330 });
  same(P.react('shock', 1).armR, P.POSES.shock.armR);
  assert.strictEqual(P.react('cheeks', 1).armsFront, true);
  P.bangOn({ top: 900 }, 300, 1, 2.5);
  same(ev, [[2.5, 'pop']]);
  same(P.toLocal({ x: 500, y: 1700, s: .5 }, 600, 1200), { tx: 200, ty: -1000 });
  const j = P.jumpAt(1.25, 1, 100, .5);
  assert(j.bob > 99 && j.bob <= 100, 'jump peaks mid-air');
});
