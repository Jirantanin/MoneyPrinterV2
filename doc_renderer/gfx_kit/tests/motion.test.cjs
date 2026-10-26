// springs live in kit.js; motion.js helpers; paper pages still load after the move
const assert = require('assert');
const { loadPure, withPage, run } = require('./harness.cjs');

run(async () => {
  const { spring, kick } = loadPure(['kit.js'], ['spring', 'kick']);
  assert.strictEqual(spring(0), 0);
  assert(Math.abs(spring(5) - 1) < 1e-3);
  assert(spring(.25, .45, 2.4) > 1, 'peak spring overshoots');
  assert.strictEqual(kick(0, 10), 0);

  const M = loadPure(['kit.js', 'motion.js'], ['squash', 'land', 'anticip', 'enter', 'leave', 'blinkOpen', 'storyTime', 'ENERGY']);
  assert.strictEqual(JSON.stringify(M.ENERGY), JSON.stringify({ peak: { zeta: .45, hz: 2.4 }, calm: { zeta: .7, hz: 2 } }));   // vm objects: compare as JSON
  const [sx, sy] = M.squash(-.3);
  assert(Math.abs(sx * sy - 1) < 1e-9 && sy < 1 && sx > 1, 'squash keeps volume');
  assert.strictEqual(M.land(1, 2), 0);
  assert(M.land(2.0, 2) < 0, 'squashed at the landing');
  assert(Math.abs(M.land(3, 2)) < .01, 'settled after a second');
  assert(M.anticip(2, 2, .6) < -.07, 'dipped back at t0');
  assert(Math.abs(M.anticip(2, 2, .6) + .08) < 1e-6);
  assert.strictEqual(M.anticip(1.8, 2, .6), 0, 'nothing before the lead');
  assert(Math.abs(M.anticip(4.6, 2, .6) - 1) < .01, 'settled');
  assert(Math.max(...Array.from({ length: 60 }, (_, i) => M.anticip(2 + i / 100, 2, .6))) > 1, 'peak energy overshoots');
  assert.strictEqual(M.leave(.9, 1), 1);
  assert.strictEqual(M.leave(1.25, 1), 0);
  assert(M.leave(1.1, 1) > M.leave(1.2, 1));
  assert.deepStrictEqual([0, 1, 2].map(t => +M.storyTime(t, [[0, 0], [1, 1], [1.8, .2]]).toFixed(3)), [0, 1, .4]);
  assert.strictEqual(+M.storyTime(-1, [[0, 5], [1, 6]]).toFixed(3), 4);
  const closed = Array.from({ length: 2000 }, (_, i) => M.blinkOpen(i / 100, 7)).filter(v => v < .5).length;
  assert(closed > 30 && closed < 120, `blinks: ${closed} closed samples in 20 s`);
  assert.strictEqual(M.blinkOpen(3.3, 7), M.blinkOpen(3.3, 7), 'pure in t');
  const pop = M.enter(0, 1, 'pop'), popEnd = M.enter(4, 1, 'pop');
  assert.strictEqual(pop.s, 0); assert(Math.abs(popEnd.s - 1) < .01);
  const drop0 = M.enter(1.05, 1, 'drop'), dropEnd = M.enter(4, 1, 'drop');
  assert(drop0.dy < -100 && drop0.sy > 1, 'falls stretched');
  assert(Math.abs(dropEnd.dy) < .01 && Math.abs(dropEnd.sy - 1) < .01);
  const sl = M.enter(1.05, 1, 'slide', { from: [-400, 0] });
  assert(sl.dx < 0);
  assert(Math.min(...Array.from({ length: 100 }, (_, i) => M.enter(1 + i / 50, 1, 'slide', { from: [-400, 0] }).dx)) > -401);
  assert(Math.max(...Array.from({ length: 100 }, (_, i) => M.enter(1 + i / 50, 1, 'slide', { from: [-400, 0] }).dx)) > 0, 'slide overshoots');

  // Review Focus 1: a page that loads kit.js and paper.js must still load
  await withPage('g=night', async page => {
    assert.strictEqual(await page.evaluate(() => typeof kick + typeof spring), 'functionfunction');
  }, { url: 'paper_demo.html' });
});
