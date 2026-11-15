// Look at your own graphic before you report it: seeks the page to a few times and writes ONE contact-sheet JPEG.
// For the agent that draws a world (or a Short scene): run it, open the sheet with Read, fix what looks wrong, run again.
// One sheet instead of one image per frame keeps the look cheap: every image an agent opens stays in its context.
//   node doc_renderer/gfx_kit/peek.cjs <page.html> <name> --dur 12            six frames from 0 to 12 s
//   node doc_renderer/gfx_kit/peek.cjs <page.html> <name> --at 0,3.5,7,11     exactly these times
//   options: --n 6 (frames with --dur) · --out <sheet.jpg> (default <page dir>/peek_<name>.jpg) · --size 1080x1920
// Same page contract as record.cjs: loads with ?g=<name>, exposes window.__ready and window.__seek(t).
// Prints one line per frame (seek time), warns when neighbouring frames are the same picture (a seek that does
// nothing, a frozen animation, or a loop drawing over the seeked frame), and exits 1 on any page error.
const fs = require('fs');
const path = require('path');

const MAX_W = 1560, GAP = 8;   // the Read tool keeps images up to 1568 px on the long side without shrinking them

function peekTimes({ at = null, n = 6, dur = null } = {}) {
  if (at != null) {
    const ts = String(at).split(',').map(s => s.trim()).filter(Boolean).map(Number);
    if (!ts.length || ts.some(t => !Number.isFinite(t))) throw new Error(`--at takes comma-separated seconds (got "${at}")`);
    return ts;
  }
  if (dur == null || !(Number(dur) > 0)) throw new Error('give --at or --dur: --at <t,t,...> or --dur <seconds>');
  n = Math.max(1, Math.round(Number(n)));
  if (n === 1) return [0];
  return Array.from({ length: n }, (_, i) => +(Number(dur) * i / (n - 1)).toFixed(3));
}

// landscape pages: up to 3 per row; vertical pages: up to 6 in a row
function sheetLayout(n, w, h) {
  const cols = Math.min(n, w >= h ? 3 : 6), rows = Math.ceil(n / cols);
  const cellW = Math.floor((MAX_W - GAP * (cols - 1)) / cols), cellH = Math.round(cellW * h / w);
  return { cols, rows, cellW, cellH, width: cols * cellW + GAP * (cols - 1), height: rows * cellH + GAP * (rows - 1) };
}

const main = async () => {
  const argv = process.argv.slice(2), opt = k => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : null; };
  const [page_, name] = argv;
  if (!page_ || !name || name.startsWith('--')) throw new Error('usage: peek.cjs <page.html> <name> (--dur <s> | --at <t,...>) [--n 6] [--out sheet.jpg] [--size WxH]');
  const times = peekTimes({ at: opt('--at'), n: opt('--n') || 6, dur: opt('--dur') });
  const [width, height] = (opt('--size') || '1920x1080').split('x').map(Number);
  const out = path.resolve(opt('--out') || path.join(path.dirname(path.resolve(page_)), `peek_${name.split('&')[0].replace(/[^\w.-]+/g, '_')}.jpg`));

  process.env.PUPPETEER_DISABLE_HEADLESS_WARNING = 'true';   // the agent reads this output: keep it to the frames
  const { launch } = require('./chrome.cjs');
  const { browser, cleanup } = await launch();
  const errors = [];
  try {
    const page = await browser.newPage();
    page.on('pageerror', e => errors.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
    await page.setViewport({ width, height });
    await page.goto('file:///' + path.resolve(page_).split(path.sep).join('/') + '?g=' + name, { waitUntil: 'networkidle0' });
    await page.evaluate(() => window.__ready);
    const shots = [];
    for (const t of times) {
      let ms = null;
      try { ms = await page.evaluate(v => { const s = performance.now(); window.__seek(v); return performance.now() - s; }, t); }
      catch (e) { errors.push(`seek ${t}: ${String(e.message).split('\n')[0]}`); }
      const buf = await page.screenshot({ type: 'jpeg', quality: 90 });
      shots.push({ t, buf });
      console.log(`t=${t} s  seek ${ms == null ? 'FAILED' : ms.toFixed(1) + ' ms'}`);
    }
    for (let i = 1; i < shots.length; i++) {
      if (shots[i].buf.equals(shots[i - 1].buf)) console.log(`warning: t=${shots[i - 1].t} s and t=${shots[i].t} s are the same picture`);
    }

    // compose the sheet in the same browser: frames scaled into cells, time label in the corner
    const L = sheetLayout(shots.length, width, height);
    const cells = shots.map(s => `<figure><img src="data:image/jpeg;base64,${s.buf.toString('base64')}"><figcaption>t=${s.t} s</figcaption></figure>`).join('');
    const sheet = await browser.newPage();
    await sheet.setViewport({ width: L.width, height: L.height });
    await sheet.setContent(`<!doctype html><style>
      html,body{margin:0;background:#111} main{display:grid;grid-template-columns:repeat(${L.cols},${L.cellW}px);gap:${GAP}px}
      figure{margin:0;position:relative;width:${L.cellW}px;height:${L.cellH}px} img{width:100%;height:100%;display:block}
      figcaption{position:absolute;left:6px;top:6px;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,.72);color:#fff;font:600 15px system-ui,sans-serif}
      </style><main>${cells}</main>`, { waitUntil: 'load' });
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await sheet.screenshot({ path: out, type: 'jpeg', quality: 85 });
    console.log(`sheet -> ${out} (${L.width}x${L.height}, ${shots.length} frames)`);
  } finally { await browser.close(); cleanup(); }
  if (errors.length) { console.log('ERRORS:\n' + errors.join('\n')); process.exitCode = 1; }
  else console.log('page errors: none');
};

if (require.main === module) main().catch(e => { console.error(e.message || e); process.exit(1); });
module.exports = { peekTimes, sheetLayout };
