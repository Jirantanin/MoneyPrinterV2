// cast_rig.js: one จุก, Earth and Sun painted per look; จุก's face never changes; sprout follows the body 0.07 s late
const assert = require('assert');
const { withPage, run } = require('./harness.cjs');

run(async () => {
  for (const paint of ['A', 'B', 'C', 'D']) await withPage(`run=rig&paint=${paint}`, async page => {
    const r = await page.evaluate(() => window.RIG_FACTS);
    const m = `paint ${paint}`;
    assert.strictEqual(r.eyeWhites, 2, m); assert.strictEqual(r.eyeWhiteFill, '#ffffff', m);
    assert.strictEqual(r.pupils, 2, m); assert.strictEqual(r.pupilFill, '#14103a', m); assert.strictEqual(r.highlights, 4, m);
    assert.strictEqual(r.cheekFill, '#ff8aa6', m); assert.strictEqual(r.cheekOpacity, 1, m);
    assert(r.pupilDx > 0, `${m}: looks right`);
    assert(r.clouds.length >= 3 && r.clouds.every(c => c === 'round'), `${m}: arched round-capped clouds`);
    assert(r.hands, `${m}: mitten hands`);
    if (paint === 'B' || paint === 'D') assert.strictEqual(r.night, 1, `${m}: D uses the B paint (hard night side)`);
    assert(Math.abs(r.restGap) < .5 && Math.abs(r.hopGap) < .5, `${m}: sprout follows 0.07 s late (${r.restGap}, ${r.hopGap})`);
    assert(Math.abs(r.noLag) > 1, `${m}: the lag is visible mid-hop`);
  });
});
