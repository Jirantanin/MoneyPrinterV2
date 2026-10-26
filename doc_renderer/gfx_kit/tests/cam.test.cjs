// cam.js: named moves, log-space zoom, overshooting punch, drift that never stops, damped shakes, parallax by depth
const assert = require('assert');
const { loadPure, withPage, run } = require('./harness.cjs');

run(async () => {
  const { camPath, screenScale, CAM_RULES } = loadPure(['kit.js', 'motion.js', 'cam.js'], ['camPath', 'screenScale', 'CAM_RULES']);
  const c = camPath([{ t: 0, x: 960, y: 540, z: 2.4, move: 'cut' }, { t: 3, x: 960, y: 540, z: .3, move: 'pull' }]);
  assert(Math.abs(c(1.5).z - Math.sqrt(2.4 * .3)) < .02, 'log-space midpoint');
  assert(Math.abs(c(0).z - 2.4) < 1e-9 && Math.abs(c(3).z - .3) < 1e-9);
  const p = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }, { t: .5, x: 0, y: 0, z: 1.15, move: 'punch' }], { drift: 0 });
  const zs = Array.from({ length: 51 }, (_, i) => p(i / 100).z);
  assert(Math.max(...zs) > 1.15, 'punch overshoots');
  assert(Math.abs(p(.5).z - 1.15) < 1e-9 && Math.abs(p(.8).z - 1.15) < 1e-9, 'punch lands exactly and stays');
  const h = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }, { t: 1, x: 0, y: 0, z: 1, move: 'hold' }]);
  assert(h(5).z > h(1).z, 'drift: never still');
  assert(Math.abs(h(1).z - 1) < 1e-9 && Math.abs(h(1).x) < 1e-9, 'drift starts from rest (no jump)');
  const k = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }, { t: 2, x: 500, y: 0, z: 1, move: 'cut' }], { drift: 0 });
  assert.strictEqual(k(1.99).x, 0); assert.strictEqual(k(2).x, 500);
  const s = camPath([{ t: 0, x: 0, y: 0, z: 1, move: 'cut' }], { shakes: [{ t0: 1 }], drift: 0 });
  assert(Math.abs(s(1.05).x) > 1 && Math.abs(s(2).x) < .5 && s(.9).x === 0, 'damped shake');
  assert.strictEqual(screenScale(2), 'scale(0.5000)');
  assert.strictEqual(CAM_RULES.pullMinRatio, 3); assert.strictEqual(CAM_RULES.maxShakesPerWorld, 2);

  await withPage('', async page => {
    const d = await page.evaluate(() => {
      const { svg } = stage();
      const layers = [0, 1, 1.4].map(depth => { const g = el('g', {}, svg); el('circle', { cx: 1200, cy: 540, r: 10 }, g); return { g, depth }; });
      const cx = () => layers.map(l => { const b = l.g.getBoundingClientRect(); return b.x + b.width / 2; });
      camApply({ x: 960, y: 540, z: 1, rot: 0 }, layers); const a = cx();
      camApply({ x: 1060, y: 540, z: 1, rot: 0 }, layers); const b = cx();
      return a.map((v, i) => Math.abs(b[i] - v));
    });
    assert(d[0] < .01, 'depth 0 is static'); assert(Math.abs(d[1] - 100) < .5, 'world moves with the camera');
    assert(d[2] > d[1] + 20, 'foreground moves farther');
  });
});
