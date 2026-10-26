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
