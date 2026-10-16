// Glow direction for explainer graphics: the house default look since 2026-10-16 (นน chose it from the black-hole test).
// Flat vector shapes that emit light: every bright piece is drawn twice (a blurred screen-blended copy under the crisp one),
// light moves through dashes that flow along paths, and depth comes from parallax and an out-of-focus foreground.
// Load after kit.js and finish.js; it keeps finish.js's rim/shade/halo/vignette and adds:
//   glowDefs(svg, {...})            blur filters and the live grain; once, after finishDefs()
//   bloom(parent, draw, o)          draw(g) runs twice: blurred glow copy, then the crisp shapes; returns {g, glow, crisp}
//   flowPath(parent, d, o)          a stroke whose dashes travel along d (currents, orbits, signals, blood, wind); update(t)
//   flowBands(parent, bands, o)     concentric glowing ribbons on an ellipse arc (disks, rings, halos, sound waves); update(t)
//   glowMotes(parent, seed, o)      particles with their own small glow, drifting or orbiting an ellipse; update(t)
//   depthFG(parent, seed, items, o) out-of-focus foreground shapes with a lit edge and fast parallax; update(t)
//   blinkLight(parent, x, y, o)     a blinking nav/status light with glow; update(t)
//   pulseRing(parent, x, y, r, o)   an expanding light ring for a moment of impact or arrival; update(t, t0)
//   glowFrame(svg, o)               vignette + film grain that changes every 2 frames; call last, before the HUD; update(t)
// Colours come from the episode: theme() for the sky, glowDefs() for the light colours. The GLW defaults (mint and amber
// on deep teal, จุก's colours) are only the fallback. Ids are prefixed `glw`.

const GLW = {
  hot: '#fff2cf', warm: '#ffb24a', accent: '#3dd6c0', cool: '#5aa8ff',
  deep: '#06121f', grain: .07, vig: '#020812', vigOpacity: .72,
};

function glowDefs(svg, o = {}) {
  Object.assign(GLW, o);
  const defs = svg.querySelector('defs') || el('defs', {}, svg);
  if (defs.querySelector('#glwBlurL')) return;
  const f = (id, s, pad = 50) => `<filter id="${id}" x="-${pad}%" y="-${pad}%" width="${100 + 2 * pad}%" height="${100 + 2 * pad}%"><feGaussianBlur stdDeviation="${s}"/></filter>`;
  defs.insertAdjacentHTML('beforeend', f('glwBlurL', 16) + f('glwBlurM', 8) + f('glwBlurS', 3.5, 80) + f('glwFG', 7) +
    `<filter id="glwGrain" x="0" y="0" width="100%" height="100%"><feTurbulence id="glwTurb" type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/><feColorMatrix type="saturate" values="0"/></filter>
     <radialGradient id="glwVig" cx="50%" cy="50%" r="72%"><stop offset=".58" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="${col(GLW.vig)}" stop-opacity="${GLW.vigOpacity}"/></radialGradient>`);
}

const glwBlur = b => b === 'S' || b === 'M' || b === 'L' ? `url(#glwBlur${b})` : b;

function bloom(parent, draw, { blur = 'L', opacity = .6, glowScale = 1.5 } = {}) {
  const g = el('g', {}, parent);
  const glow = el('g', { filter: glwBlur(blur), opacity, style: 'mix-blend-mode:screen' }, g), crisp = el('g', {}, g);
  draw(glow, glowScale); draw(crisp, 1);   // draw(g, k): k widens strokes for the glow copy
  return { g, glow, crisp };
}

// dashes: [[dash, gap], ...] or a seed for a random pattern; speed in px/s along the path (negative runs backwards)
function flowPath(parent, d, { color = GLW.hot, width = 4, opacity = .7, speed = 60, dashes = 5, glow = true, cap = 'round' } = {}) {
  const g = el('g', {}, parent);
  let da = dashes;
  if (typeof dashes === 'number') { const R = rng(dashes); da = Array.from({ length: 7 }, () => [6 + R() * 34, 30 + R() * 150]); }
  da = da.flat().join(' ');
  const mk = (p, w, op) => el('path', { d, fill: 'none', stroke: col(color), 'stroke-width': w, 'stroke-opacity': op, 'stroke-dasharray': da, 'stroke-linecap': cap }, p);
  const es = [];
  if (glow) es.push(mk(el('g', { filter: 'url(#glwBlurS)', style: 'mix-blend-mode:screen' }, g), width * 2.6, opacity * .8));
  es.push(mk(g, width, opacity));
  return t => es.forEach(e => e.setAttribute('stroke-dashoffset', (-t * speed).toFixed(1)));
}

// bands: [[r, width, colour], ...] inner to outer; o.ry = vertical squash (1 = circle, .2 = a disk seen edge-on);
// a0..a1 in radians (0 = right, PI/2 = bottom), so a disk is two calls: back half (PI..2PI) and front half (0..PI)
function flowBands(parent, bands, { cx = KW / 2, cy = KH / 2, ry = 1, a0 = 0, a1 = 2 * Math.PI, glow = .6, speed = 50,
  streaks = true, seed = 1 } = {}) {
  const g = el('g', {}, parent);
  const gGlow = el('g', { filter: 'url(#glwBlurL)', opacity: glow, style: 'mix-blend-mode:screen' }, g), gC = el('g', {}, g);
  const full = a1 - a0 >= 2 * Math.PI - 1e-6;
  const arc = (rx, ryy) => {
    if (full) return `M${cx - rx},${cy} a${rx},${ryy} 0 1 0 ${2 * rx},0 a${rx},${ryy} 0 1 0 ${-2 * rx},0`;
    const q = a => [cx + rx * Math.cos(a), cy + ryy * Math.sin(a)], s = q(a0), e = q(a1);
    return `M${s[0].toFixed(1)},${s[1].toFixed(1)} A${rx},${ryy} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${e[0].toFixed(1)},${e[1].toFixed(1)}`;
  };
  const flows = [];
  bands.forEach(([r, w, c], i) => {
    const d = arc(r, r * ry), sw = ry < 1 ? w * Math.max(ry, .3) * 1.45 + 6 : w;
    el('path', { d, fill: 'none', stroke: col(c), 'stroke-width': w * 1.5 }, gGlow);
    el('path', { d, fill: 'none', stroke: col(c), 'stroke-width': sw }, gC);
    el('path', { d: arc(r - w * .35, (r - w * .35) * ry), fill: 'none', stroke: '#ffffff', 'stroke-opacity': i < bands.length / 2 ? .32 : .12, 'stroke-width': 1.6 }, gC);
    if (streaks) {
      const sp = speed * Math.pow(bands[0][0] / r, 1.2);   // inner bands run faster
      flows.push(flowPath(gC, d, { color: i < 3 ? '#ffffff' : GLW.deep, width: Math.max(2.5, sw * .14), opacity: .5, speed: sp, dashes: seed * 31 + i, glow: false }));
      flows.push(flowPath(gC, d, { color: GLW.hot, width: 1.8, opacity: .45, speed: sp * 1.4, dashes: seed * 31 + i + 77, glow: false }));
    }
  });
  const u = t => flows.forEach(f => f(t));
  u.g = g;
  return u;
}

// o.orbit = {cx, cy, rx, ry, r0, r1}: motes circle that ellipse at Kepler-ish speeds (inner faster), hidden by
// o.hide(x, y, a) when it returns true (e.g. behind a planet); without orbit they drift like finish.js dustLayer
function glowMotes(parent, seed, { n = 60, colors = [GLW.hot, GLW.warm, GLW.accent], size = [.8, 3.4], orbit = null,
  h = KH, drift = 14, hide = null } = {}) {
  const R = rng(seed), g = el('g', {}, parent);
  const ms = Array.from({ length: n }, () => {
    const c = col(colors[R() * colors.length | 0]), s = size[0] + R() * (size[1] - size[0]), e = el('g', {}, g);
    el('circle', { r: s * 3, fill: c, opacity: .35, filter: 'url(#glwBlurS)' }, e); el('circle', { r: s, fill: c }, e);
    return { e, k: R(), a0: R() * 6.283, x: R() * KW, y: R() * h, ph: R() * 6.283, v: .2 + R() * .6, dy: (R() - .5) * 14 };
  });
  return t => ms.forEach(m => {
    let x, y, a = 0;
    if (orbit) { const r = orbit.r0 + m.k * (orbit.r1 - orbit.r0); a = m.a0 + t * 180 / Math.pow(r, 1.5) * (orbit.speed ?? 1);
      x = orbit.cx + r * Math.cos(a); y = orbit.cy + r * (orbit.ry ?? 1) * Math.sin(a) + m.dy; }
    else { x = m.x + 30 * Math.sin(t * m.v + m.ph); y = ((m.y - drift * t * m.v) % h + h) % h; }
    set(m.e, { transform: `translate(${x.toFixed(1)},${y.toFixed(1)})`, opacity: hide && hide(x, y, a) ? 0 : (.55 + .45 * Math.sin(t * 2 + m.ph)).toFixed(2) });
  });
}

// items: [[x, y, r], ...]; vx/vy px/s parallax (faster than the scene), rim = lit-edge colour
function depthFG(parent, seed, items, { fill = GLW.deep, rim = GLW.warm, vx = -70, vy = 0, spin = 7 } = {}) {
  const g = el('g', { filter: 'url(#glwFG)' }, parent), R = rng(seed);
  const fs = items.map(([x, y, r], k) => {
    const e = el('g', {}, g), pts = [];
    for (let i = 0; i < 9; i++) { const a = i / 9 * 6.283, q = r * (.75 + R() * .35); pts.push(`${(Math.cos(a) * q).toFixed(1)},${(Math.sin(a) * q * .8).toFixed(1)}`); }
    el('polygon', { points: pts.join(' '), fill: col(fill) }, e);
    el('polygon', { points: pts.join(' '), fill: 'none', stroke: col(rim), 'stroke-width': 7, 'stroke-dasharray': `${r * 1.6} ${r * 9}`, 'stroke-dashoffset': r * .4 }, e);
    return { e, x, y, s: .6 + .4 * R(), dir: k % 2 ? -1 : 1 };
  });
  const u = t => fs.forEach(f => set(f.e, { transform: `translate(${(f.x + vx * t * f.s).toFixed(1)},${(f.y + vy * t * f.s).toFixed(1)}) rotate(${(t * spin * f.dir).toFixed(1)})` }));
  u.g = g;
  return u;
}

function blinkLight(parent, x, y, { color = '#ff5a4f', r = 5, period = .6, on = .12, phase = 0 } = {}) {
  const halo = el('circle', { cx: x, cy: y, r: r * 2.8, fill: col(color), filter: 'url(#glwBlurS)' }, parent);
  const dot = el('circle', { cx: x, cy: y, r, fill: col(color) }, parent);
  return t => { const k = ((t + phase) % period + period) % period < on ? 1 : .15; show(dot, k); show(halo, k * .8); };
}

function pulseRing(parent, x, y, r, { color = GLW.hot, width = 30, grow = 40, decay = 3.2 } = {}) {
  const e = el('circle', { cx: x, cy: y, r, fill: 'none', stroke: col(color), 'stroke-width': width, filter: 'url(#glwBlurL)', opacity: 0 }, parent);
  // returns the pulse level 0..1 too, so the caller can flare something else (a photon ring, a halo) with it
  return (t, t0) => { const k = t >= t0 ? Math.exp(-(t - t0) * decay) : 0; set(e, { opacity: (.9 * k).toFixed(3), r: (r + grow * (1 - k)).toFixed(1) }); return k; };
}

function glowFrame(svg, { vignette = true, grain = GLW.grain, fps = 25 } = {}) {
  if (vignette) el('rect', { width: KW, height: KH, fill: 'url(#glwVig)', 'pointer-events': 'none' }, svg);
  if (grain) el('rect', { width: KW, height: KH, filter: 'url(#glwGrain)', opacity: grain, style: 'mix-blend-mode:overlay', 'pointer-events': 'none' }, svg);
  const turb = svg.querySelector('#glwTurb');
  return t => turb && turb.setAttribute('seed', String(1 + Math.floor(t * fps / 2) % 8));   // grain changes on 2s
}
