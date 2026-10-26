// new pages build only after every type face is loaded (riseLine measures its container at build time)
const assert = require('assert');
const { withPage, run } = require('./harness.cjs');

const spy = () => {
  window.__fontLoads = [];
  const orig = document.fonts.load.bind(document.fonts);
  document.fonts.load = (f, txt) => { window.__fontLoads.push(f); return orig(f, txt); };
};
const NEED = ['600 40px Fredoka', '700 40px Fredoka', '500 40px Mitr', '600 40px Mitr'];

run(async () => {
  const { loadPure } = require('./harness.cjs');
  assert.strictEqual(JSON.stringify(loadPure(['type.js'], ['TYPE_FACES']).TYPE_FACES), JSON.stringify(NEED));
  await withPage('', async page => {
    const loads = await page.evaluate(() => window.__fontLoads);
    for (const f of NEED) assert(loads.includes(f), `motion_demo waits for ${f} (${loads})`);
  }, { url: 'motion_demo.html', onNew: spy });
});
