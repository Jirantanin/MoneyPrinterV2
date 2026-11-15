// peek.cjs: the drawing agent's own look — times, sheet layout, one JPEG, frozen-frame warning, page errors fail
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync, execFileSync } = require('child_process');
const { KIT, run } = require('./harness.cjs');

const peek = args => spawnSync('node', [path.join(KIT, 'peek.cjs'), ...args], { encoding: 'utf8' });
const size = jpg => execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', jpg],
  { encoding: 'utf8' }).trim().split(',').map(Number);

run(async () => {
  const { peekTimes, sheetLayout } = require('../peek.cjs');
  assert.deepStrictEqual(peekTimes({ at: '0, 2.5,9' }), [0, 2.5, 9]);
  assert.deepStrictEqual(peekTimes({ n: 6, dur: 10 }), [0, 2, 4, 6, 8, 10]);
  assert.deepStrictEqual(peekTimes({ dur: 10 }), [0, 2, 4, 6, 8, 10], 'six frames by default');
  assert.deepStrictEqual(peekTimes({ n: 1, dur: 4 }), [0]);
  assert.throws(() => peekTimes({}), /--at or --dur/);
  assert.throws(() => peekTimes({ at: '1,x' }), /--at/);

  const land = sheetLayout(6, 1920, 1080);
  assert.strictEqual(land.cols, 3); assert.strictEqual(land.rows, 2);
  assert(land.width <= 1568, 'fits the image size the Read tool keeps without downscaling');
  assert.strictEqual(Math.round(land.cellW * 1080 / 1920), land.cellH, 'cells keep the page aspect');
  const tall = sheetLayout(6, 1080, 1920);
  assert.strictEqual(tall.cols, 6); assert.strictEqual(tall.rows, 1, 'vertical pages sit in one row');
  assert.strictEqual(sheetLayout(2, 1920, 1080).cols, 2);

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'peek-'));
  const fixture = path.join(KIT, 'tests/fixture.html');

  // a moving page: one sheet, sized for the Read tool, one line per frame
  const out = path.join(dir, 'sheet.jpg');
  const ok = peek([fixture, 'x&run=whip', '--at', '0.1,0.5,0.9', '--out', out]);
  assert.strictEqual(ok.status, 0, ok.stderr);
  assert(fs.existsSync(out));
  const [w, h] = size(out);
  assert(w <= 1568 && h < w, `sheet ${w}x${h}`);
  assert(/t=0\.1 s/.test(ok.stdout) && /t=0\.9 s/.test(ok.stdout), ok.stdout);
  assert(!/same picture/.test(ok.stdout), 'whip moves between frames');

  // a page whose seek does nothing: still a sheet, but it says the frames did not change
  const frozen = path.join(dir, 'frozen.html');
  fs.writeFileSync(frozen, '<!doctype html><body style="margin:0;background:#246"><script>window.__ready=Promise.resolve(true);window.__seek=()=>{};</script></body>');
  const fr = peek([frozen, 'x', '--at', '0,1,2', '--out', path.join(dir, 'frozen.jpg')]);
  assert.strictEqual(fr.status, 0, fr.stderr);
  assert(/same picture/.test(fr.stdout), fr.stdout);

  // a page that throws fails the look, with the error printed
  const broken = path.join(dir, 'broken.html');
  fs.writeFileSync(broken, '<!doctype html><body><script>window.__ready=Promise.resolve(true);window.__seek=t=>{if(t>0.5)throw new Error("boom at "+t)};</script></body>');
  const br = peek([broken, 'x', '--at', '0,1', '--out', path.join(dir, 'broken.jpg')]);
  assert.notStrictEqual(br.status, 0);
  assert(/boom at 1/.test(br.stdout + br.stderr), br.stdout + br.stderr);

  fs.rmSync(dir, { recursive: true, force: true });
});
