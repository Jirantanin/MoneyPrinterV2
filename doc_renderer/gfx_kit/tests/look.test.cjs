// kit cast.js base layers; look B installs the flat Y_lit (three tones in the body's hue, no rim colour)
const assert = require('assert');
const { withPage, run } = require('./harness.cjs');

const facts = () => ({ style: Y.look.style, paths: Y.cam.querySelectorAll('path').length,
  rim: [...Y.cam.querySelectorAll('path')].some(p => p.getAttribute('fill') === Y.look.rim),
  layers: ['bg', 'cam', 'fg', 'hud', 'top'].every(k => Y[k] && Y[k].parentNode === Y.svg) });

run(async () => {
  await withPage('run=lookB', async page => {
    const r = await page.evaluate(facts);
    assert.strictEqual(r.style, 'B'); assert.strictEqual(r.paths, 3, 'lit band + shade + body'); assert.strictEqual(r.rim, false);
    assert(r.layers);
  });
  await withPage('run=lookA', async page => {
    const r = await page.evaluate(facts);
    assert.strictEqual(r.style, 'A'); assert.strictEqual(r.paths, 2, 'rim + body'); assert.strictEqual(r.rim, true);
  });
});
