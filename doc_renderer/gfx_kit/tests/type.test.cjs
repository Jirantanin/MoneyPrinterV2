// type.js: Fredoka for numbers/Latin, Mitr for Thai, tracking only on Latin, lines rise through a clip, fixed digit slots
const assert = require('assert');
const { withPage, run } = require('./harness.cjs');

run(async () => {
  await withPage('run=type', async page => {
    const r = await page.evaluate(() => window.TYPE_FACTS);
    assert.strictEqual(r.thaiLetterSpacing, 0, 'no tracking on Thai');
    assert.strictEqual(r.latinLetterSpacing, '5');
    assert.strictEqual(r.thaiFont, 'Mitr'); assert.strictEqual(r.numFont, 'Fredoka'); assert.strictEqual(r.numFill, '#ffd98a');
    assert(r.hiddenBeforeT0, 'nothing before t0'); assert.strictEqual(r.pillBeforeT0, 0, 'no empty pill');
    assert(r.atT0 > 40, `starts 1.3x its height below (${r.atT0})`);
    assert(Math.abs(r.offsetAtEnd) < .5, 'risen by t0 + 0.55');
    assert.strictEqual(r.container, 'pill', 'look B uses the dark pill');
    assert.deepStrictEqual(r.lastTwoA, r.lastTwoB, 'the last two digits never move when the count shrinks');
    assert(r.widthMinus70 <= r.widthBudget, `−70°C fits its slots (${r.widthMinus70} > ${r.widthBudget})`);
    assert(r.thaiThrows, 'digits refuses Thai (its marks would land in their own slots) and points to riseLine');
    assert(Math.abs(r.slam0 - 1.7) < 1e-9 && Math.abs(r.slamEnd - 1) < .01, 'slam 1.7x -> 1x');
  });
});
