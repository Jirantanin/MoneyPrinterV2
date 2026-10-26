// beat sheet parsing, the guard-rule checker, and the contact-sheet page
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { KIT, run } = require('./harness.cjs');

run(async () => {
  const { parseBeats, checkBeats } = require('../contact_sheet.cjs');
  const b = parseBeats(fs.readFileSync(path.join(__dirname, 'beats_fixture.md'), 'utf8'));
  assert.strictEqual(b.beats.length, 4);
  assert.strictEqual(b.beats[0].trigger, 'แปดนาที'); assert.strictEqual(b.beats[0].storyNo, 5);
  assert.strictEqual(b.beats[0].cameraMove, 'punch'); assert.strictEqual(b.beats[1].cameraMove, 'dive');
  assert.strictEqual(b.beats[2].cameraMove, 'hold', 'drift is the camera holding');
  assert.strictEqual(b.beats[0].peak, 3.6, 'empty peak -> time + 0.4'); assert.strictEqual(b.beats[1].peak, 6.4);
  assert(/Look B/.test(b.direction) && /none yet/.test(b.gotchas));
  const probs = checkBeats(b.beats);
  assert(probs.some(s => /no scale reveal/.test(s)), 'world has no story move 2');
  assert(!probs.some(s => /no make-it-personal/.test(s)), 'story move 3 is there');
  assert(probs.some(s => /drift.*what changes/.test(s)));
  assert(probs.some(s => /push-in is not a story move/.test(s)));
  assert.strictEqual(probs.length, 3, probs.join(' | '));

  // a sheet without a BEATS table says so; bad times are flagged; --write's timing marks are not part of the trigger
  assert.throws(() => parseBeats(['# x', '', '## DIRECTION', 'no table'].join('\n')), /no BEATS table/);
  const odd = parseBeats(['## BEATS', '| time | peak | trigger | story move | camera | what changes | text | sound |', '|---|---|---|---|---|---|---|---|',
    '| ? |  | "ไกล" (phrase) | 2 scale | pull 1→.3, 2 s | out | — | — |', '| 4.0 | soon | "คุณ" | 3 personal | dive 1→2, 1 s | in | — | — |'].join('\n'));
  assert.strictEqual(odd.beats[0].trigger, 'ไกล'); assert.strictEqual(odd.beats[0].timing, 'phrase');
  const oddP = checkBeats(odd.beats);
  assert(oddP.some(s => /beat 1.*time/.test(s)) && oddP.some(s => /beat 2.*peak/.test(s)), oddP.join(' | '));

  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'contact-'));
  const r = spawnSync('node', [path.join(KIT, 'contact_sheet.cjs'), path.join(KIT, 'tests/fixture.html'), 'x&run=whip', path.join(__dirname, 'beats_fixture.md'), out], { encoding: 'utf8' });
  assert.notStrictEqual(r.status, 0, 'problems make the tool exit non-zero');
  const html = fs.readFileSync(path.join(out, 'contact.html'), 'utf8');
  assert.strictEqual((html.match(/<figure/g) || []).length, 4);
  assert(fs.existsSync(path.join(out, 'beat_1.jpg')) && fs.existsSync(path.join(out, 'beat_4.jpg')));
  assert(/no scale reveal/.test(html), 'problems are on the page');
  fs.rmSync(out, { recursive: true, force: true });
});
