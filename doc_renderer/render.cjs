// Frame-locked render of player.html for Producer Mode's minimal documentary renderer.
//
//   node render.cjs --timeline <timeline.json> --work <dir> --out <video.mp4> --chrome <exe> [--workers N]
//   node render.cjs --timeline <timeline.json> --work <dir> --chrome <exe> --stills 4,120.5
//
// Frames are piped as JPEG into one ffmpeg encode per 500-frame chunk; finished chunks are kept in
// <work>/chunks so an interrupted render resumes. The output is video-only; Python muxes the audio.
const fs = require('fs'), path = require('path'), { spawn, spawnSync } = require('child_process');
const puppeteer = require('puppeteer-core');

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
for (const key of ['timeline', 'work', 'chrome']) if (!args[key]) throw new Error(`--${key} is required`);

const TL = JSON.parse(fs.readFileSync(args.timeline, 'utf8'));
const FPS = TL.fps, FRAMES = Math.round(TL.total * FPS), CHUNK = 500;
const WORK = path.resolve(args.work);
const PLAYER = 'file:///' + path.join(__dirname, 'player.html').replace(/\\/g, '/');
// PRODUCER_CHROME_GPU=1 rasterizes on the GPU (ANGLE/D3D11) instead of SwiftShader; frames match CPU to ~45 dB PSNR.
const GPU_FLAGS = process.env.PRODUCER_CHROME_GPU === '1' ? ['--ignore-gpu-blocklist', '--use-angle=d3d11', '--enable-gpu-rasterization', '--enable-zero-copy'] : [];

async function openPage(id) {
  const browser = await puppeteer.launch({
    executablePath: args.chrome, headless: true, userDataDir: path.join(WORK, 'profiles', String(id)),
    args: ['--no-sandbox', '--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb', ...GPU_FLAGS],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await page.goto(PLAYER, { waitUntil: 'load', timeout: 90000 });
  return { browser, page };
}

async function stills(times) {
  const dir = path.join(WORK, 'stills'); fs.mkdirSync(dir, { recursive: true });
  const { browser, page } = await openPage('stills');
  try {
    for (const t of times) {
      await page.evaluate((tl, a, b) => window.__init(tl, a, b), TL, t, t);
      await page.evaluate(t => window.__seek(t), t);
      await page.screenshot({ path: path.join(dir, `t${t}.jpg`), type: 'jpeg', quality: 92 });
      console.log('still', t);
    }
  } finally { await browser.close(); }
}

function encoder(out) {
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), out]);
  ff.stderr.on('data', d => process.stderr.write('[ffmpeg] ' + d));
  return ff;
}

async function render(workers) {
  const cdir = path.join(WORK, 'chunks'); fs.mkdirSync(cdir, { recursive: true });
  const all = [], jobs = [];
  for (let c = 0; c * CHUNK < FRAMES; c++) {
    const out = path.join(cdir, `c${String(c).padStart(4, '0')}.mp4`);
    all.push(out);
    if (!fs.existsSync(out)) jobs.push({ c, f0: c * CHUNK, f1: Math.min(FRAMES, (c + 1) * CHUNK), out });
  }
  console.log(`frames ${FRAMES}, chunks ${all.length}, todo ${jobs.length}, workers ${workers}, ${GPU_FLAGS.length ? 'gpu' : 'cpu'}`);
  const t0 = Date.now(), todo = jobs.length; let done = 0;
  await Promise.all(Array.from({ length: Math.min(workers, jobs.length) }, async (_, w) => {
    const { browser, page } = await openPage(w);
    try {
      for (let job; (job = jobs.shift());) {
        await page.evaluate((tl, a, b) => window.__init(tl, a, b), TL, job.f0 / FPS, job.f1 / FPS);
        const tmp = job.out + '.part.mp4', ff = encoder(tmp);
        const closed = new Promise((res, rej) => ff.on('close', code => code === 0 ? res() : rej(new Error('ffmpeg exited ' + code))));
        for (let f = job.f0; f < job.f1; f++) {
          await page.evaluate(t => window.__seek(t), f / FPS);
          const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
          if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
        }
        ff.stdin.end(); await closed; fs.renameSync(tmp, job.out);
        console.log(`chunk ${job.c} done (${++done}/${todo}) ${((Date.now() - t0) / 1000).toFixed(0)}s`);
      }
    } finally { await browser.close(); }
  }));

  const list = path.join(WORK, 'chunks.txt');
  fs.writeFileSync(list, all.map(f => `file '${f.replace(/\\/g, '/')}'`).join('\n') + '\n');
  const cat = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', args.out], { stdio: 'inherit' });
  if (cat.status !== 0) throw new Error('chunk concat failed');
  console.log(`video ready ${args.out} in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}

(args.stills ? stills(args.stills.split(',').map(Number))
  : args.out ? render(Number(args.workers || 6))
  : Promise.reject(new Error('--out or --stills is required')))
  .catch(e => { console.error('ERR', e && e.stack || e); process.exit(1); });
