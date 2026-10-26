// Motion helpers (motion rules in LIBRARY.md "Motion"). Load after kit.js; every value is a pure function of t.
//   ENERGY                         spring settings: peak (hook and each world's peak) and calm (explanation)
//   squash(k) -> [sx, sy]          volume-keeping stretch (k > 0) or squash (k < 0)
//   land(t, t0, o) -> k            squash amount after a landing at t0 (feed it to squash)
//   anticip(t, t0, dur, o) -> u    progress that first dips back (anticipation), then springs to 1 by t0 + dur
//   enter(t, t0, kind, o)          {s, sx, sy, dx, dy, o} for kind 'pop' | 'drop' | 'slide'
//   leave(t, t1, dur) -> 1..0      exits are quicker than entrances: ease-in over about 0.25 s
//   blinkOpen(t, seed, every)      eyelid openness: 1 open, 0.1 during a 0.13 s blink every 3-5 s
//   storyTime(t, keys)             ambient clock -> story clock; keys [[ambientT, storyT], ...], a falling segment rewinds
const ENERGY = { peak: { zeta: .45, hz: 2.4 }, calm: { zeta: .7, hz: 2 } };
const springE = (t, energy) => spring(t, ENERGY[energy].zeta, ENERGY[energy].hz);

const squash = k => [1 / (1 + k), 1 + k];
function land(t, t0, { amp = .3, decay = 7, hz = 2.5 } = {}) {
  const d = t - t0;
  return d < 0 ? 0 : -amp * Math.exp(-decay * d) * Math.cos(2 * Math.PI * hz * d);
}
function anticip(t, t0, dur, { back = .08, lead = .15, energy = 'peak' } = {}) {
  if (t < t0 - lead) return 0;
  if (t < t0) return -back * eio(p(t, t0 - lead, t0));
  return -back + (1 + back) * springE((t - t0) * (.6 / dur), energy);   // the spring settles in about 0.6 s; scale to dur
}
function enter(t, t0, kind, { energy = 'peak', from = [0, -320], fall = .25 } = {}) {
  const o = t < t0 ? 0 : 1, rest = { s: 1, sx: 1, sy: 1, dx: 0, dy: 0, o };
  if (kind === 'pop') return { ...rest, s: Math.max(0, springE(t - t0, energy)) };
  if (kind === 'slide') { const k = springE(t - t0, energy); return { ...rest, dx: from[0] * (1 - k), dy: from[1] * (1 - k) }; }
  if (kind === 'drop') {
    if (t < t0 + fall) { const [sx, sy] = squash(.2), u = p(t, t0, t0 + fall);
      return { ...rest, sx, sy, dx: from[0] * (1 - u * u * u), dy: from[1] * (1 - u * u * u) }; }
    const [sx, sy] = squash(land(t, t0 + fall)); return { ...rest, sx, sy };
  }
  throw new Error(`enter: unknown kind "${kind}"`);
}
const leave = (t, t1, dur = .25) => 1 - Math.pow(p(t, t1, t1 + dur), 3);
function blinkOpen(t, seed, every = [3, 5]) {
  const R = rng(seed);
  for (let tb = 1 + R() * 2; tb <= t; tb += every[0] + R() * (every[1] - every[0])) if (t < tb + .13) return .1;
  return 1;
}
function storyTime(t, keys) {
  if (t <= keys[0][0]) return keys[0][1] + (t - keys[0][0]);
  for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) {
    const [a0, s0] = keys[i - 1], [a1, s1] = keys[i];
    return lerp(s0, s1, (t - a0) / (a1 - a0));
  }
  const [aL, sL] = keys[keys.length - 1];
  return sL + (t - aL);
}
