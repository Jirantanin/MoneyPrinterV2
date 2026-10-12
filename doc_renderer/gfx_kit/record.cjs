// Record an explainer-graphic page frame by frame to MP4 (or stills) with the minimal_doc headless Chrome.
// The page must load kit.js, expose window.__ready (Promise) and window.__seek(t), and read ?g=<name>.
//   node doc_renderer/gfx_kit/record.cjs <page.html> <name> <seconds> <out.mp4> [--fps 25]
//   node doc_renderer/gfx_kit/record.cjs <page.html> <name> <seconds> <out_prefix> --stills 1.5,8,14
// Record at the episode render rate (minimal_doc: 25 fps) and to the exact slot length.
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const ROOT = path.resolve(__dirname, '../..');
const puppeteer = require(path.join(ROOT, 'doc_renderer/node_modules/puppeteer-core'));

function findChrome() {
  if (process.env.PRODUCER_MINIMAL_CHROME) return process.env.PRODUCER_MINIMAL_CHROME;
  const base = path.join(ROOT, 'remotion/node_modules/.remotion/chrome-headless-shell');
  const walk = d => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name);
    if (e.isDirectory()) { const r = walk(p); if (r) return r; } else if (/^chrome-headless-shell(\.exe)?$/.test(e.name)) return p; } };
  return walk(base);
}
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };

(async () => {
  const [page_, name, seconds, out] = process.argv.slice(2);
  const fps = Number(arg('--fps', 25)), total = Math.round(Number(seconds) * fps), stills = arg('--stills', null);
  const profile = fs.mkdtempSync(path.join(require('os').tmpdir(), 'gfxkit-'));
  const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, userDataDir: profile,
    args: ['--no-sandbox', '--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb'] });
  const page = await browser.newPage();
  page.on('pageerror', e => { console.error('pageerror', e.message); process.exitCode = 2; });
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto('file:///' + path.resolve(page_).split(path.sep).join('/') + '?g=' + name, { waitUntil: 'networkidle0' });
  await page.evaluate(() => window.__ready);
  if (stills) {
    for (const t of stills.split(',').map(Number)) {
      await page.evaluate(v => window.__seek(v), t);
      await page.screenshot({ path: `${out}_${t}.jpg`, type: 'jpeg', quality: 85 });
    }
  } else {
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < total; i++) {
      await page.evaluate(v => window.__seek(v), i / fps);
      const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  }
  await browser.close();
  fs.rmSync(profile, { recursive: true, force: true });
  console.log('done', name, out);
})().catch(e => { console.error(e); process.exit(1); });
