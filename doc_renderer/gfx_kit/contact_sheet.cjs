// Contact sheet for one world: a still at each beat's peak plus the beat-sheet checks, as one HTML page for นน to approve
// before the world is recorded (LIBRARY.md "Beat sheet and contact sheet").
//   node doc_renderer/gfx_kit/contact_sheet.cjs <page.html> "<scene&f=...>" <world.beats.md> <outdir>
//   -> <outdir>/beat_<n>.jpg and <outdir>/contact.html; exits 1 when the checks find problems (the page is still written)
// The beat sheet is a sidecar <world>.beats.md with ## DIRECTION, ## BEATS (a table with the columns
// time | peak | trigger | story move | camera | what changes | text | sound) and ## GOTCHAS; see beats_template.md.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const COLS = ['time', 'peak', 'trigger', 'story move', 'camera', 'what changes', 'text', 'sound'];
const CAM_ALIASES = { 'punch-in': 'punch', 'push-in': 'push', 'pull-back': 'pull', drift: 'hold', 'impact': 'shake' };
const CAM = vm.runInNewContext(`${fs.readFileSync(path.join(__dirname, 'cam.js'), 'utf8')}\n;({CAM_RULES, CAM_EASED})`, {});
const CAM_MOVES = [...CAM.CAM_EASED, 'punch', 'cut', 'hold', 'shake'];
const empty = s => !s || /^[-—–\s]*$/.test(s);

function section(md, name) {
  const m = new RegExp(`^## ${name}\\s*$([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, 'm').exec(md);
  return m ? m[1].trim() : '';
}
function parseBeats(md) {
  const rows = section(md, 'BEATS').split(/\r?\n/).filter(l => l.trim().startsWith('|')).map(l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
  if (!rows.length) throw new Error('no BEATS table: the sheet needs a "## BEATS" section with the table (see beats_template.md)');
  const head = rows[0].map(h => h.toLowerCase());
  if (COLS.some((c, i) => head[i] !== c)) throw new Error(`BEATS columns must be: ${COLS.join(' | ')}`);
  const beats = rows.slice(2).map(r => {
    const [time, peak, trig, story, camera, changes, text, sound] = r, t = empty(time) ? NaN : Number(time);
    const word = (camera.split(/[\s,]/)[0] || '').toLowerCase();
    const mark = /\s*\((word|phrase|unknown)\)$/.exec(trig), trigger = (mark ? trig.slice(0, mark.index) : trig).replace(/^["“]|["”]$/g, '');
    return { time: t, peak: empty(peak) ? +(t + .4).toFixed(2) : Number(peak), trigger, timing: mark ? mark[1] : '', story,
      storyNo: /^\d+/.test(story) ? parseInt(story, 10) : null, camera, cameraMove: CAM_ALIASES[word] || word, changes: empty(changes) ? '' : changes,
      text: empty(text) ? '' : text, sound: empty(sound) ? '' : sound };
  });
  return { direction: section(md, 'DIRECTION'), beats, gotchas: section(md, 'GOTCHAS') };
}
// the guard rules: every row names a story move and a camera move; a drift row names what changes; every world has a
// scale reveal (2) and a make-it-personal (3); impact shakes stay rare
function checkBeats(beats) {
  const out = [], at = (b, i) => `beat ${i + 1} (${b.time} s)`;
  beats.forEach((b, i) => {
    if (!Number.isFinite(b.time)) out.push(`${at(b, i)}: time is not a number of seconds`);
    else if (!Number.isFinite(b.peak)) out.push(`${at(b, i)}: peak is not a number of seconds`);
    else if (b.peak < b.time) out.push(`${at(b, i)}: peak ${b.peak} is before the beat's time`);
    if (empty(b.story)) out.push(`${at(b, i)}: empty story move`);
    else if (/^push/i.test(b.story)) out.push(`${at(b, i)}: push-in is not a story move`);
    else if (b.storyNo == null || b.storyNo < 1 || b.storyNo > 12) out.push(`${at(b, i)}: story move must start with its number 1-12`);
    if (empty(b.camera)) out.push(`${at(b, i)}: empty camera move`);
    else if (!CAM_MOVES.includes(b.cameraMove)) out.push(`${at(b, i)}: unknown camera move "${b.cameraMove}"`);
    if (b.cameraMove === 'hold' && !b.changes) out.push(`${at(b, i)}: drift with nothing in "what changes"`);
  });
  if (!beats.some(b => b.storyNo === 2)) out.push('no scale reveal (story move 2) in this world');
  if (!beats.some(b => b.storyNo === 3)) out.push('no make-it-personal (story move 3) in this world');
  const shakes = beats.filter(b => /shake|impact/i.test(b.camera)).length;
  if (shakes > CAM.CAM_RULES.maxShakesPerWorld) out.push(`${shakes} impact shakes (at most ${CAM.CAM_RULES.maxShakesPerWorld} per world)`);
  return out;
}

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function page(title, sheet, problems) {
  const card = (b, i) => `<figure><img src="beat_${i + 1}.jpg" alt="beat ${i + 1}"><figcaption><b>${i + 1} · ${b.time}s</b> (peak ${b.peak}s) “${esc(b.trigger)}”${b.timing === 'word' || !b.timing ? '' : ` <i>(${b.timing} time)</i>`}
<div><span>เล่า</span>${esc(b.story)}</div><div><span>กล้อง</span>${esc(b.camera)}</div><div><span>เปลี่ยน</span>${esc(b.changes || '—')}</div>
${b.text ? `<div><span>ข้อความ</span>${esc(b.text)}</div>` : ''}</figcaption></figure>`;
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title><style>
body{margin:0;padding:16px;background:#0e1420;color:#e8eef6;font:15px/1.45 'Leelawadee UI',sans-serif}
h1{font-size:20px;margin:0 0 8px}.dir{opacity:.75;white-space:pre-wrap;margin-bottom:12px}
.probs{background:#3a1218;color:#ffb3b3;padding:8px 12px;border-radius:8px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px}
figure{margin:0;background:#16202f;border-radius:8px;overflow:hidden}img{width:100%;display:block}
figcaption{padding:8px 10px}figcaption span{display:inline-block;min-width:58px;opacity:.6}
</style></head><body><h1>${esc(title)}</h1><div class="dir">${esc(sheet.direction)}</div>
${problems.length ? `<div class="probs"><b>ปัญหา</b><ul>${problems.map(p => `<li>${esc(p)}</li>`).join('')}</ul></div>` : ''}
<div class="grid">${sheet.beats.map(card).join('\n')}</div>
${sheet.gotchas ? `<h1>GOTCHAS</h1><div class="dir">${esc(sheet.gotchas)}</div>` : ''}</body></html>`;
}

async function main() {
  const [page_, name, beatsFile, outdir] = process.argv.slice(2);
  const sheet = parseBeats(fs.readFileSync(beatsFile, 'utf8')), problems = checkBeats(sheet.beats);
  fs.mkdirSync(outdir, { recursive: true });
  const { launch } = require('./chrome.cjs');
  const { browser, cleanup } = await launch();
  try {
    const pg = await browser.newPage();
    pg.on('pageerror', e => problems.push('pageerror: ' + e.message));
    await pg.setViewport({ width: 1920, height: 1080 });
    await pg.goto('file:///' + path.resolve(page_).split(path.sep).join('/') + '?g=' + name, { waitUntil: 'networkidle0' });
    await pg.evaluate(() => window.__ready);
    for (const [i, b] of sheet.beats.entries()) {
      await pg.evaluate(v => window.__seek(v), b.peak);
      await pg.screenshot({ path: path.join(outdir, `beat_${i + 1}.jpg`), type: 'jpeg', quality: 82 });
    }
  } finally { await browser.close(); cleanup(); }
  fs.writeFileSync(path.join(outdir, 'contact.html'), page(path.basename(beatsFile), sheet, problems));
  console.log(problems.length ? `${problems.length} problem(s):\n- ${problems.join('\n- ')}` : 'no problems');
  console.log('contact sheet:', path.join(outdir, 'contact.html'));
  if (problems.length) process.exitCode = 1;
}

if (require.main === module) main().catch(e => { console.error(e); process.exit(2); });
module.exports = { parseBeats, checkBeats };
