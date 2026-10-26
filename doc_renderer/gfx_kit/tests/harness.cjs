// Test helpers for the gfx kit (Node 16: plain scripts with assert, run by tests/test_gfx_kit_js.py).
//   loadPure(files, names)        run kit files in a vm (no DOM) and return the named globals
//   withPage(query, fn, {url})    open <gfx_kit>/<url>?<query> in headless Chrome, fail on pageerror, await __ready
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const KIT = path.resolve(__dirname, '..');

function loadPure(files, names) {
  const src = files.map(f => fs.readFileSync(path.join(KIT, f), 'utf8')).join('\n;\n');
  return vm.runInNewContext(`${src}\n;({${names.join(',')}})`, { console }, { filename: files.join('+') });
}

async function withPage(query, fn, { url = 'tests/fixture.html', size = [1920, 1080] } = {}) {
  const { launch } = require('../chrome.cjs');
  const { browser, cleanup } = await launch();
  const errors = [];
  try {
    const page = await browser.newPage();
    page.on('pageerror', e => errors.push(e.message));
    await page.setViewport({ width: size[0], height: size[1] });
    await page.goto('file:///' + path.join(KIT, url).split(path.sep).join('/') + (query ? '?' + query : ''), { waitUntil: 'networkidle0' });
    await page.evaluate(() => window.__ready);
    if (errors.length) throw new Error('pageerror: ' + errors.join(' | '));
    await fn(page);
    if (errors.length) throw new Error('pageerror: ' + errors.join(' | '));
  } finally { await browser.close(); cleanup(); }
}

// run an async test body; exit non-zero on failure so pytest sees it
function run(body) { body().then(() => console.log('ok'), e => { console.error(e && e.stack || e); process.exit(1); }); }

module.exports = { KIT, loadPure, withPage, run };
