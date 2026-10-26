// Old pages render as before: a cosmic-year-humans world and the glow demo match stills recorded from main (5f7d989)
// before this branch; the new demo world loads cleanly and its beat sheet passes the checks.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');
const { KIT, run } = require('./harness.cjs');
const ROOT = path.resolve(KIT, '../..');

const gray = png => execFileSync('ffmpeg', ['-v', 'error', '-i', png, '-vf', 'scale=480:270,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], { maxBuffer: 1 << 22 });
const mad = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - b[i]); return s / a.length; };
const still = (page, name, out) => execFileSync('node', [path.join(KIT, 'record.cjs'), page, name, '1', out, '--stills', '2', '--png'], { stdio: 'pipe' });

run(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'compat-'));
  const cases = [
    ['cosmic', path.join(ROOT, '.mp/podcast_v2_cosmic-year-humans_20261020_235317/graphics/glow/page.html'), 'sp_light&f=w_space.js'],
    ['glow', path.join(KIT, 'glow_demo.html'), 'space'],
  ];
  for (const [n, page, name] of cases) {
    if (!fs.existsSync(page)) { console.log('skip (episode folder missing):', n); continue; }
    still(page, name, path.join(dir, n));
    const d = mad(gray(path.join(dir, `${n}_2.png`)), gray(path.join(__dirname, 'ref', `${n}_2.png`)));
    assert(d < 1.0, `${n}: mean abs difference ${d.toFixed(3)} against main`);
  }
  const demo = spawnSync('node', [path.join(KIT, 'contact_sheet.cjs'), path.join(KIT, 'motion_demo.html'), 'demo', path.join(KIT, 'motion_demo.beats.md'), path.join(dir, 'contact')], { encoding: 'utf8' });
  assert.strictEqual(demo.status, 0, demo.stdout + demo.stderr);
  fs.rmSync(dir, { recursive: true, force: true });
});
