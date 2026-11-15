// Headless Chrome for the gfx kit tools (record.cjs, contact_sheet.cjs, tests): the minimal_doc chrome-headless-shell.
//   findChrome() -> path    PRODUCER_MINIMAL_CHROME overrides; otherwise the Remotion download under remotion/node_modules
//   launch({gpu}) -> {browser, cleanup()}   gpu defaults to PRODUCER_CHROME_GPU=1 (GPU raster instead of SwiftShader)
const path = require('path');
const fs = require('fs');
const os = require('os');
const ROOT = path.resolve(__dirname, '../..');
const puppeteer = require(path.join(ROOT, 'doc_renderer/node_modules/puppeteer-core'));

function findChrome() {
  if (process.env.PRODUCER_MINIMAL_CHROME) return process.env.PRODUCER_MINIMAL_CHROME;
  const base = path.join(ROOT, 'remotion/node_modules/.remotion/chrome-headless-shell');
  const walk = d => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name);
    if (e.isDirectory()) { const r = walk(p); if (r) return r; } else if (/^chrome-headless-shell(\.exe)?$/.test(e.name)) return p; } };
  return walk(base);
}

async function launch({ gpu = process.env.PRODUCER_CHROME_GPU === '1' } = {}) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'gfxkit-'));
  const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, userDataDir: profile,
    args: ['--no-sandbox', '--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb',
      // three.js pages: without a GPU, Chrome only gives WebGL through SwiftShader when asked (local trusted pages only)
      ...(gpu ? ['--ignore-gpu-blocklist', '--use-angle=d3d11', '--enable-gpu-rasterization', '--enable-zero-copy']
        : ['--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--use-gl=angle'])] });
  return { browser, cleanup: () => fs.rmSync(profile, { recursive: true, force: true }) };
}

module.exports = { findChrome, launch };
