// Record an explainer-graphic page frame by frame to MP4 (or stills) with the minimal_doc headless Chrome.
// The page must load kit.js, expose window.__ready (Promise) and window.__seek(t), and read ?g=<name>.
//   node doc_renderer/gfx_kit/record.cjs <page.html> <name> <seconds> <out.mp4> [--fps 25]
//   node doc_renderer/gfx_kit/record.cjs <page.html> <name> <seconds> <out_prefix> --stills 1.5,8,14
//   --png writes the stills as lossless PNG (thumbnails) instead of JPEG
//   --from -0.8 starts at page time -0.8 s (crossfade handles); window.__SFX is saved next to the MP4 as <out>.sfx.json
//   --size 1080x1920 sets the viewport for a vertical page (the page calls kitSize(1080, 1920))
//   Motion blur is opt-in: a page sets window.__MBLUR = 2 (new pages built on the motion spec), or --mblur N overrides
//   it (0 or 1 = off). N subframes per MP4 frame are blended over --shutter of the frame (default 0.6), so whips, dives
//   and fast moves read as motion; it roughly doubles record time. Stills never blur. Frames within half a shutter of a
//   time in window.__CUTS (hard cuts, counter ticks, caption swaps) are not blended, so they never double-expose.
// Record at the episode render rate (minimal_doc: 25 fps) and to the exact slot length.
// PRODUCER_CHROME_GPU=1 rasterizes on the GPU instead of SwiftShader (same flag as render.cjs).
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { launch } = require('./chrome.cjs');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };

// page times of the subframes of frame i: the midpoints of `sub` equal slices of the open shutter, centred on the frame
function subframeTimes(i, fps, from, { sub = 2, shutter = .6 } = {}) {
  const t = from + i / fps;
  return Array.from({ length: sub }, (_, j) => t + ((j + .5) / sub - .5) * shutter / fps);
}

const main = async () => {
  const [page_, name, seconds, out] = process.argv.slice(2);
  const fps = Number(arg('--fps', 25)), total = Math.round(Number(seconds) * fps), stills = arg('--stills', null);
  const from = Number(arg('--from', 0));   // page time of the first frame (negative = lead-in handle)
  const [width, height] = arg('--size', '1920x1080').split('x').map(Number);
  const { browser, cleanup } = await launch();
  const page = await browser.newPage();
  page.on('pageerror', e => { console.error('pageerror', e.message); process.exitCode = 2; });
  await page.setViewport({ width, height });
  await page.goto('file:///' + path.resolve(page_).split(path.sep).join('/') + '?g=' + name, { waitUntil: 'networkidle0' });
  await page.evaluate(() => window.__ready);
  if (stills) {
    for (const t of stills.split(',').map(Number)) {
      await page.evaluate(v => window.__seek(v), t);
      if (process.argv.includes('--png')) await page.screenshot({ path: `${out}_${t}.png`, type: 'png' });   // thumbnails
      else await page.screenshot({ path: `${out}_${t}.jpg`, type: 'jpeg', quality: 85 });
    }
  } else {
    const { pageBlur, cuts } = await page.evaluate(() => ({ pageBlur: window.__MBLUR || 1, cuts: window.__CUTS || [] }));
    const sub = Math.max(1, Math.round(Number(arg('--mblur', pageBlur))) || 1), shutter = Number(arg('--shutter', .6));
    const onCut = t => cuts.some(c => Math.abs(c - t) <= shutter / (2 * fps) + 1e-9);
    const blend = sub > 1 ? ['-vf', `tmix=frames=${sub},select=not(mod(n+1\\,${sub})),setpts=N/(${fps}*TB)`, '-r', String(fps)] : [];
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps * sub), '-c:v', 'mjpeg', '-i', '-', ...blend,
      '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const sfx = await page.evaluate(() => window.__SFX || null);
    if (sfx) fs.writeFileSync(out.replace(/\.mp4$/i, '') + '.sfx.json', JSON.stringify(sfx));
    for (let i = 0; i < total; i++) for (const t of onCut(from + i / fps) ? Array(sub).fill(from + i / fps) : subframeTimes(i, fps, from, { sub, shutter })) {
      await page.evaluate(v => window.__seek(v), t);
      const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  }
  await browser.close();
  cleanup();
  console.log('done', name, out);
};

if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
module.exports = { subframeTimes };
