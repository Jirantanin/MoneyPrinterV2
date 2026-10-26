// Fixtures for tests/fixture.html?run=<name>: each builds a scene and may set window.FIX_RENDER(t) and facts for the tests.

// Task 2: the base layers and a look; one Y_lit shape on the camera layer
const litFixture = style => () => { Y_init({ style }); Y_lit(Y.cam, 'M20,0H180A20,20 0 0 1 200,20V100A20,20 0 0 1 180,120H20A20,20 0 0 1 0,100V20A20,20 0 0 1 20,0Z', '#5fc47a'); };
FIXTURES.lookA = litFixture('A');
FIXTURES.lookB = litFixture('B');
