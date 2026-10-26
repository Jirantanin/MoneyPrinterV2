// record.cjs motion blur: subframes centred on the frame time, blended by ffmpeg; stills never blur
const assert = require('assert');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { execFileSync } = require('child_process');
const { KIT, run } = require('./harness.cjs');

// one row of frame n as gray bytes
const row = (mp4, n) => execFileSync('ffmpeg', ['-v', 'error', '-i', mp4, '-vf', `select=eq(n\\,${n}),crop=1920:2:0:540`, '-vsync', '0', '-frames:v', '1',
  '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], { maxBuffer: 1 << 24 }).subarray(0, 1920);   // 4:2:0 needs an even crop
const centroid = r => { let s = 0, w = 0; r.forEach((v, i) => { s += v * i; w += v; }); return s / w; };
const soft = r => r.filter(v => v > 40 && v < 215).length;

run(async () => {
  const { subframeTimes } = require('../record.cjs');
  assert.deepStrictEqual(subframeTimes(10, 25, 0).map(v => +v.toFixed(4)), [.394, .406]);
  assert.deepStrictEqual(subframeTimes(0, 25, -.8, { sub: 1 }), [-.8]);
  assert.strictEqual(+subframeTimes(10, 25, 0, { sub: 3 }).reduce((a, b) => a + b, 0).toFixed(6), 1.2, 'centred on the frame');

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mblur-')), page = path.join(KIT, 'tests/fixture.html');
  const rec = (out, extra) => execFileSync('node', [path.join(KIT, 'record.cjs'), page, 'x&run=whip', '1', out, ...extra], { stdio: 'pipe' });
  rec(path.join(dir, 'blur.mp4'), []); rec(path.join(dir, 'sharp.mp4'), ['--mblur', '0']);
  const b = row(path.join(dir, 'blur.mp4'), 12), s = row(path.join(dir, 'sharp.mp4'), 12);
  assert(soft(b) > soft(s) + 6, `blurred edges are wider (${soft(b)} vs ${soft(s)})`);
  assert(Math.abs(centroid(b) - centroid(s)) < 2, `no time shift (${centroid(b)} vs ${centroid(s)})`);
  assert(Math.abs(centroid(s) - (300 + 600 * .48 + 100)) < 2, 'frame 12 is t = 0.48');
  fs.rmSync(dir, { recursive: true, force: true });
});
