// Finish layer for explainer graphics: the house level of depth and light every episode gets (นน approved 2026-10-15,
// Hatshepsut v3). Load after kit.js. It adds light, not a look: colours come from each episode's art direction.
//   finishDefs(svg, {...})       gradients/filters below, coloured for this episode; call once after stage()
//   rimForm(parent, d, fill, o)  a filled shape with a thin rim light on one edge (the shape in the rim colour, the body
//                                shifted by dx, dy and clipped to the shape on top)
//   litPass(node)                one light pass over a finished prop or figure: rim on the lit edge, shade band on the far edge
//   glowHalo(parent, r, o)       screen-blended light source halo with optional flicker; returns update(t)
//   lightShaft(parent, d, o)     a soft beam (moon through a slot, a window), screen-blended; returns update(t)
//   dustLayer(parent, seed, o)   drifting particles that catch the light; returns update(t)
//   finishFrame(svg, o)          vignette + film grain over everything; call last, before the HUD. The default vignette
//                                (.75 of a near-black) suits dark scenes; a bright scene wants a lighter vig/vigOpacity
// Ids are prefixed `fin` so they never collide with an episode's own defs.

const FIN = {
  rim: '#a9d2ff', rimOpacity: .75, shade: '#0b0628', shadeOpacity: .42, light: [-16, -12],
  warm: '#ff9a3c', warmCore: '#ffe7a8', vig: '#05030f', vigOpacity: .75, grain: .08,
  dust: ['#d8e8ff', '#ffd9a0'],
};

function finishDefs(svg, o = {}) {
  Object.assign(FIN, o);
  const defs = svg.querySelector('defs') || el('defs', {}, svg);
  if (defs.querySelector('#finForm')) return;
  const [lx, ly] = FIN.light, len = Math.hypot(lx, ly) || 1, ex = -3.5 * lx / len, ey = -3.5 * ly / len;
  defs.insertAdjacentHTML('beforeend', `
    <filter id="finForm" x="-15%" y="-15%" width="130%" height="130%" color-interpolation-filters="sRGB">
      <feOffset in="SourceAlpha" dx="${lx}" dy="${ly}" result="toLight"/>
      <feComposite in="SourceAlpha" in2="toLight" operator="out" result="far"/>
      <feGaussianBlur in="far" stdDeviation="7" result="farB"/>
      <feFlood flood-color="${col(FIN.shade)}" flood-opacity="${FIN.shadeOpacity}"/>
      <feComposite in2="farB" operator="in"/>
      <feComposite in2="SourceAlpha" operator="in" result="shade"/>
      <feOffset in="SourceAlpha" dx="${ex.toFixed(2)}" dy="${ey.toFixed(2)}" result="away"/>
      <feComposite in="SourceAlpha" in2="away" operator="out" result="edge"/>
      <feFlood flood-color="${col(FIN.rim)}" flood-opacity="${FIN.rimOpacity}"/>
      <feComposite in2="edge" operator="in" result="rimL"/>
      <feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="shade"/><feMergeNode in="rimL"/></feMerge>
    </filter>
    <filter id="finBlur3" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>
    <filter id="finBlur12" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="12"/></filter>
    <radialGradient id="finGlow"><stop offset="0" stop-color="${col(FIN.warmCore)}" stop-opacity=".9"/><stop offset=".25" stop-color="${col(FIN.warm)}" stop-opacity=".45"/><stop offset=".6" stop-color="${col(FIN.warm)}" stop-opacity=".12"/><stop offset="1" stop-color="${col(FIN.warm)}" stop-opacity="0"/></radialGradient>
    <radialGradient id="finGlowSoft"><stop offset="0" stop-color="${col(FIN.warm)}" stop-opacity=".35"/><stop offset="1" stop-color="${col(FIN.warm)}" stop-opacity="0"/></radialGradient>
    <radialGradient id="finVig"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="${col(FIN.vig)}" stop-opacity="${FIN.vigOpacity}"/></radialGradient>
    <pattern id="finGrain" patternUnits="userSpaceOnUse" width="256" height="256"><image href="${grainTile(7)}" width="256" height="256"/></pattern>`);
}

// deterministic grey noise tile as a data URL (no image file next to the page)
function grainTile(seed, n = 256) {
  const c = document.createElement('canvas'); c.width = c.height = n;
  const x = c.getContext('2d'), img = x.createImageData(n, n), R = rng(seed);
  for (let i = 0; i < n * n; i++) { const v = 128 + (R() + R() + R() - 1.5) * 150 | 0; img.data.set([v, v, v, 255], i * 4); }
  x.putImageData(img, 0, 0);
  return c.toDataURL('image/png');
}

let FIN_N = 0;
// dx, dy default to a 3.6 px shift away from FIN.light, so the rim sits on the lit side like litPass's rim
function rimForm(parent, d, fill, { rim = FIN.rim, dx = null, dy = null, rimOpacity = .85, extra = {} } = {}) {
  const [lx, ly] = FIN.light, len = Math.hypot(lx, ly) || 1;
  if (dx == null) dx = +(-3.6 * lx / len).toFixed(2);
  if (dy == null) dy = +(-3.6 * ly / len).toFixed(2);
  const g = el('g', {}, parent);
  if (!rim) { el('path', { d, fill, ...extra }, g); return g; }
  const id = `finClip${FIN_N++}`;
  el('defs', {}, g).innerHTML = `<clipPath id="${id}"><path d="${d}"/></clipPath>`;
  el('path', { d, fill: col(rim), opacity: rimOpacity }, g);
  el('path', { d, fill, transform: `translate(${dx},${dy})`, ...extra }, el('g', { 'clip-path': `url(#${id})` }, g));
  return g;
}

// accepts an element or a kit object with .g; returns what it was given
const litPass = o => { const g = o && (o.g || o); if (g && g.setAttribute) g.setAttribute('filter', 'url(#finForm)'); return o; };

function glowHalo(parent, r, { flicker = 0, seed = 1, soft = false } = {}) {
  const e = el('circle', { r, fill: soft ? 'url(#finGlowSoft)' : 'url(#finGlow)', style: 'mix-blend-mode:screen' }, parent);
  return t => set(e, { r: (r * (1 + flicker * (Math.sin(t * 9 + seed) + .6 * Math.sin(t * 13.3 + seed * 2)))).toFixed(1) });
}

function lightShaft(parent, d, { color = '#8fc0ff', opacity = .34, dir = [.4, 1], breathe = .2 } = {}) {
  const id = `finShaft${FIN_N++}`;
  el('defs', {}, parent).innerHTML = `<linearGradient id="${id}" x1="0" y1="0" x2="${dir[0]}" y2="${dir[1]}"><stop offset="0" stop-color="${col(color)}" stop-opacity="${opacity}"/><stop offset="1" stop-color="${col(color)}" stop-opacity="0"/></linearGradient>`;
  const e = el('path', { d, fill: `url(#${id})`, style: 'mix-blend-mode:screen' }, parent);
  return t => show(e, 1 - breathe + breathe * Math.sin(t * .7));
}

function dustLayer(parent, seed, { n = 60, h = 900, colors = FIN.dust, drift = 12 } = {}) {
  const R = rng(seed);
  const d = Array.from({ length: n }, () => ({ e: el('circle', { r: .8 + R() * 2.2, fill: col(colors[R() * colors.length | 0]) }, parent),
    x: R() * KW, y: R() * h, ph: R() * 6.28, v: .2 + R() * .5 }));
  return t => d.forEach(q => set(q.e, { cx: (q.x + 30 * Math.sin(t * q.v + q.ph)).toFixed(1),
    cy: (((q.y - drift * t * q.v) % h + h) % h).toFixed(1), opacity: (.3 + .35 * Math.sin(t * 2 + q.ph)).toFixed(2) }));
}

function finishFrame(svg, { vignette = true, grain = FIN.grain } = {}) {
  if (vignette) el('rect', { width: KW, height: KH, fill: 'url(#finVig)', 'pointer-events': 'none' }, svg);
  if (grain) el('rect', { width: KW, height: KH, fill: 'url(#finGrain)', opacity: grain, style: 'mix-blend-mode:overlay', 'pointer-events': 'none' }, svg);
}
