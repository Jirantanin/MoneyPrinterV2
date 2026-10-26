// Fixtures for tests/fixture.html?run=<name>: each builds a scene and may set window.FIX_RENDER(t) and facts for the tests.

// Task 2: the base layers and a look; one Y_lit shape on the camera layer
const litFixture = style => () => { Y_init({ style }); Y_lit(Y.cam, 'M20,0H180A20,20 0 0 1 200,20V100A20,20 0 0 1 180,120H20A20,20 0 0 1 0,100V20A20,20 0 0 1 20,0Z', '#5fc47a'); };
FIXTURES.lookA = litFixture('A');
FIXTURES.lookB = litFixture('B');

// Task 4: the rigged cast in one look (?paint=A|B|C|D); facts read back from the built DOM
FIXTURES.rig = () => {
  const paint = Q.get('paint') || 'B';
  Y_init({ style: paint });
  const j = jook(Y.cam, { arms: true }), e = earth(Y.cam, 220, { seed: 9 }), s = sun(Y.cam, 160);
  e.state({ x: 1300, y: 500 }); s.state({ x: 200, y: 300, t: 1 });
  const parts = n => [...Y.cam.querySelectorAll(`[data-part="${n}"]`)];
  const yOf = n => parts(n)[0].getCTM().f;
  // the sprout at t sits where the body's sprout anchor was at t - 0.07
  const lagGap = t => { j.update(t, { x: 600, y: 800, hop: [1] }); const sp = yOf('sprout'); j.update(t - .07, { x: 600, y: 800, hop: [1] }); return sp - yOf('sproutAnchor'); };
  const restGap = lagGap(.5), hopGap = lagGap(1.2);
  j.update(1.2, { x: 600, y: 800, hop: [1] }); const noLag = yOf('sprout') - yOf('sproutAnchor');
  j.update(2, { x: 600, y: 800, look: [1, 0] });
  const eye = parts('eyeWhite')[0], pupil = parts('pupil')[0];
  window.RIG_FACTS = {
    eyeWhites: parts('eyeWhite').length, eyeWhiteFill: eye.getAttribute('fill'),
    pupils: parts('pupil').length, pupilFill: pupil.getAttribute('fill'), highlights: parts('hl').length,
    cheekFill: parts('cheek')[0].getAttribute('fill'), cheekOpacity: +(parts('cheek')[0].getAttribute('opacity') ?? 1),
    pupilDx: +pupil.getAttribute('cx') - +eye.getAttribute('cx'),
    clouds: parts('cloud').map(c => c.getAttribute('stroke-linecap')),
    hands: !!(j.handL && j.handR && j.handL.parentNode && j.handR.parentNode),
    restGap, hopGap, noLag,
    night: parts('night').length,
  };
};

// Task 5: type module facts at look B
FIXTURES.type = () => {
  Y_init({ style: 'B' });
  const L = riseLine(Y.hud, 960, 300, 40, [['แสงนี้ออกจาก ', 'th', 'teal'], ['8', 'num', 'gold'], [' LAST LIGHT', 'latin', 'white']], 1);
  const tspans = [...L.g.querySelectorAll('tspan')];
  const pill = L.g.querySelector('[data-part="container"]'), textG = L.g.querySelector('[data-part="lineText"]');
  const ty = () => +(/translate\(0,([-\d.]+)\)/.exec(textG.getAttribute('transform')) || [0, 0])[1];
  const sc = () => +(/scale\(([-\d.]+)/.exec(pill.getAttribute('transform')) || [0, 1])[1];
  L.update(.99); const before = { o: +L.g.getAttribute('opacity'), pill: sc() };
  L.update(1.0); const atT0 = ty();
  L.update(1.6); const offsetAtEnd = ty();
  const D = digits(Y.hud, 1500, 600, 120, { align: 'right' });
  const xs = () => [...D.g.querySelectorAll('text')].filter(e => e.getAttribute('opacity') !== '0').map(e => +e.getAttribute('x'));
  D.set('10:00'); const a = xs(); D.set('9:59'); const b = xs();
  D.set('−70°C'); const w = D.g.getBBox().width;
  window.TYPE_FACTS = {
    thaiLetterSpacing: +(tspans[0].getAttribute('letter-spacing') || 0), latinLetterSpacing: tspans[2].getAttribute('letter-spacing'),
    thaiFont: tspans[0].getAttribute('font-family'), numFont: tspans[1].getAttribute('font-family'), numFill: tspans[1].getAttribute('fill'),
    hiddenBeforeT0: before.o === 0, pillBeforeT0: before.pill, atT0, offsetAtEnd, container: pill.getAttribute('data-kind'),
    lastTwoA: a.slice(-2), lastTwoB: b.slice(-2), widthMinus70: w, widthBudget: 120 * (.42 + .58 + .58 + .34 + .62) + 24,
    slam0: slam(1, 1), slamEnd: slam(4, 1),
  };
};

// Task 6/7: a 200x400 white bar on black moving right at 600 px/s from x = 300
FIXTURES.whip = () => {
  const { svg } = stage();
  el('rect', { width: KW, height: KH, fill: '#000' }, svg);
  const bar = el('rect', { y: 340, width: 200, height: 400, fill: '#fff' }, svg);
  window.FIX_RENDER = t => set(bar, { x: (300 + 600 * t).toFixed(2) });
  FIX_RENDER(0);
};
