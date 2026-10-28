// gfx_kit/cosmos.js · the channel's space world: one deep sky with a light source in frame, so every planet, rock and
// character has a lit side and a rim (นน 2026-10-26: the dinosaurs episode's space shots fell below the cosmic-year
// standard, "the art must never drop below the best world"). Layers back to front: base (a radial glow centred on the
// sun) · nebula (soft translucent ribbons) · stars (a few twinkle) · the sun (bloom, halo, spikes) · your bodies · near
// rocks (dark silhouettes with a rim band on the side facing the sun, fast parallax). Needs kit.js, glow.js and the
// episode's cast.js helpers (el, set, show, YC, YP, Y_blob, Y_pts, Y_rgrad, Y_layer, silhouette, rng).
//   const S = Cosmos.space(Y_layer(Y.bg), { sun: [330, 120], seed: 3 });          // pal: 'violet' (default) or 'veiled'
//   ... your bodies in Y.cam; Cosmos.atmo(earthGroup, R, { rot }) for an atmosphere rim on the lit side ...
//   const N = Cosmos.rocks(Y_layer(Y.cam), [[x, y, r, seed], ...], { sun: S.sunAt });   // after the bodies
//   render: S.update(t, { cam: [cx, cy, z], dim }); N.update(t, [cx, cy, z])
(() => {
  const PAL = {
    violet: { deep: '#04021a', mid: '#140a48', core: '#3c1f8e', neb: ['#7a3ab8', '#c84a9a', '#3a5ad8', '#5a2aa8', '#2a8ac8'],
      star: '#cfe8ff', starW: '#ffe9c4', sun: '#fff6e6', sunGlow: '#ffd29a', rock: '#0a0620', rim: '#ffc890' },
    // the sky after the impact: the sun starved behind soot, colder ribbons
    veiled: { deep: '#03020e', mid: '#0c0828', core: '#24123e', neb: ['#3a2a6a', '#5a2a5a', '#22306a', '#3a2050', '#1e3a5a'],
      star: '#9fb4d8', starW: '#d8c8b0', sun: '#ffd8b0', sunGlow: '#ff9a5a', rock: '#070414', rim: '#ff9a6a' },
  };
  const f = v => (+v).toFixed(1);

  // a star seen from close: wide bloom, hot halo, thin spikes, a white core; update(t, {k, s})
  function star(parent, { x = 0, y = 0, r = 14, glow = '#ffd29a', core = '#fff6e6', spikes = 300, rays = 6, seed = 1 } = {}) {
    const g = el('g', { transform: `translate(${f(x)},${f(y)})` }, parent), inner = el('g', {}, g), R = rng(seed);
    YC(0, 0, r * 26, Y_rgrad([[0, glow, .42], [.25, glow, .14], [1, glow, 0]], { user: true, cx: 0, cy: 0, r: r * 26 }), inner);
    YC(0, 0, r * 6, Y_rgrad([[0, core, .9], [.4, glow, .35], [1, glow, 0]], { user: true, cx: 0, cy: 0, r: r * 6 }), inner);
    const sp = el('g', { style: 'mix-blend-mode:screen' }, inner);
    for (let i = 0; i < rays; i++) { const a = i / rays * Math.PI + .3, L = spikes * (i % 2 ? .55 : 1) * (.85 + R() * .3), w = r * .22;
      const c = Math.cos(a), s = Math.sin(a), d = `M${f(c * L)},${f(s * L)} L${f(-s * w)},${f(c * w)} L${f(-c * L)},${f(-s * L)} L${f(s * w)},${f(-c * w)}Z`;
      YP(d, Y_rgrad([[0, core, .95], [1, core, 0]], { user: true, cx: 0, cy: 0, r: L }), sp); }
    YC(0, 0, r * 2.2, '#ffffff', inner, { opacity: .55, filter: 'url(#glwBlurS)' });   // a hot white heart so it reads as the light source
    YC(0, 0, r, '#ffffff', inner);
    return { g, update(t, { k = 1, s = 1 } = {}) {
      set(inner, { transform: `scale(${(s * (1 + .025 * Math.sin(t * 2.1))).toFixed(4)})` });
      set(sp, { transform: `rotate(${f(3 * Math.sin(t * .4))})` }); show(g, k); } };
  }

  // soft ribbons across the sky (closed bands with wavy edges, blurred, layered): the nebula of the house space look
  function nebula(parent, seed, { cx = 960, cy = 520, w = 3400, h = 560, cols = PAL.violet.neb, n = 5, op = .3 } = {}) {
    const g = el('g', { filter: 'url(#glwBlurM)' }, parent), R = rng(seed);
    const bands = Array.from({ length: n }, (_, i) => {
      const off = (i - (n - 1) / 2) * h / n + (R() - .5) * 60, th = 90 + R() * 160, ph = R() * 6, fr = .0016 + R() * .0016, amp = 70 + R() * 120;
      const top = [], bot = [];
      for (let x = cx - w / 2; x <= cx + w / 2; x += 120) {
        const yy = cy + off + amp * Math.sin(x * fr + ph) + 30 * Math.sin(x * fr * 3.1 + ph * 2);
        top.push([x, yy]); bot.push([x, yy + th * (.55 + .45 * Math.sin(x * fr * 1.7 + ph))]); }
      const sm = pts => pts.map((q, k) => k ? `Q${f(pts[k - 1][0])},${f(pts[k - 1][1])} ${f((pts[k - 1][0] + q[0]) / 2)},${f((pts[k - 1][1] + q[1]) / 2)}` : `M${f(q[0])},${f(q[1])}`).join(' ');
      const d = sm(top) + ' L' + bot.slice().reverse().map(q => `${f(q[0])},${f(q[1])}`).join(' L') + 'Z';
      return YP(d, cols[i % cols.length], g, { opacity: (op * (.7 + R() * .5)).toFixed(2) }); });
    return { g, bands, update(t) { set(g, { transform: `translate(${f(14 * Math.sin(t * .07))},${f(5 * Math.sin(t * .05))})` }); } };
  }

  function stars(parent, seed, n, box, pal = PAL.violet) {
    const g = el('g', {}, parent), tw = [];
    Y_pts(n, seed, box).forEach(([x, y, a, b], i) => { const e = YC(f(x), f(y), (.5 + a * 1.7).toFixed(2), a > .86 ? pal.starW : pal.star, g, { opacity: (.22 + .6 * b).toFixed(2) });
      if (i % 11 === 0) tw.push([e, .22 + .6 * b, i]); });
    return { g, update(t) { tw.forEach(([e, o, i]) => show(e, o * (.55 + .45 * Math.sin(t * (1.3 + i % 5 * .3) + i)))); } };
  }

  // the whole sky; sun = [x, y] in screen space (it rides the sky layer, so it stays near where you put it)
  function space(parent, { sun = [330, 120], sunR = 18, seed = 1, pal = 'violet', nebOp = .3 } = {}) {
    const P = typeof pal === 'string' ? PAL[pal] : pal, root = el('g', {}, parent);
    el('rect', { x: -1200, y: -1000, width: 4320, height: 3080, fill: Y_rgrad([[0, P.core], [.38, P.mid], [1, P.deep]], { user: true, cx: sun[0], cy: sun[1], r: 2300 }) }, root);
    const skyL = el('g', {}, root), nebL = el('g', {}, root), sunL = el('g', {}, root);
    const st = stars(skyL, seed + 11, 300, [-900, -700, 3700, 2500], P);
    const nb = nebula(nebL, seed + 21, { cols: P.neb, op: nebOp, cy: 420 + (sun[1] - 120) * .3 });
    const sn = star(sunL, { x: sun[0], y: sun[1], r: sunR, glow: P.sunGlow, core: P.sun, seed: seed + 31 });
    return { root, pal: P, sunAt: sun, sun: sn, neb: nb, stars: st,
      update(t, { cam = [960, 540, 1], dim = 0 } = {}) {
        const [cx, cy, z] = cam, par = (g, k) => set(g, { transform: `translate(960,540) scale(${(1 + (z - 1) * k).toFixed(4)}) translate(${f(-960 - (cx - 960) * k)},${f(-540 - (cy - 540) * k)})` });
        par(skyL, .06); par(nebL, .1); par(sunL, .04);
        st.update(t); nb.update(t); sn.update(t, { k: 1 - .75 * dim, s: 1 - .4 * dim }); show(nebL, 1 - .5 * dim); } };
  }

  // near-plane rocks: dark cut-outs with a lit band on the side facing the sun; items [x, y, r, seed, stack]
  // stack > 1 piles blobs into a pillar (the standard's rock stacks). They move with fast parallax (k 1.5).
  // flat look (an episode that loads flat.js, Y_lit): a violet body with a lit band toward the sun and a dark crescent
  // away from it, no outline; otherwise a dark silhouette with a rim band (glow look)
  function rocks(parent, items, { sun = [330, 120], fill = '#1c1248', light = '#5a3aa8', dark = '#0a0620', rim = PAL.violet.rim, band = 13, k = 1.5, soft = true } = {}) {
    const svg = parent.ownerSVGElement || Y.svg, flat = !!window.FL_tone;
    const list = items.map(([x, y, r, seed, stack = 1], i) => {
      const dx = sun[0] - x, dy = sun[1] - y, n = Math.hypot(dx, dy) || 1;
      const g = el('g', soft ? { filter: 'url(#glwBlurS)' } : {}, parent), R = rng(seed);
      const b = flat ? g : el('g', { filter: silhouette(svg, { fill: '#0a0620', rim, dx: f(-dx / n * band), dy: f(-dy / n * band) }) }, g);
      for (let s = 0; s < stack; s++) { const rr = r * (1 - s * .16) * (.85 + R() * .3), ox = (R() - .5) * r * .3, oy = -s * r * 1.15, d = Y_blob(ox, oy, rr, rr * .82, seed * 7 + s, 9, .3);
        const body = flat ? Y_lit(b, d, fill, { light, dark, dx: -dx / n * rr * .16, dy: -dy / n * rr * .16 }) : (YP(d, '#000', b), g);
        // a few craters, toward the lit side
        for (let c = 0; c < 3; c++) YC(f(ox + (R() - .5) * rr + dx / n * rr * .2), f(oy + (R() - .5) * rr * .6 + dy / n * rr * .2), f(rr * (.08 + R() * .08)), flat ? dark : '#ffffff', body, { opacity: flat ? .45 : .05 }); }
      return { g, x, y, ph: i * 1.9 };
    });
    return { list, update(t, [cx, cy, z] = [960, 540, 1]) {
      const ez = 1 + (z - 1) * k;
      list.forEach(q => set(q.g, { transform: `translate(960,540) scale(${ez.toFixed(4)}) translate(${f(q.x - 960 - (cx - 960) * k + 8 * Math.sin(t * .3 + q.ph))},${f(q.y - 540 - (cy - 540) * k + 6 * Math.sin(t * .4 + q.ph))})` })); } };
  }

  // a planet's atmosphere: a thin glowing crescent on the lit limb; rot = light direction in degrees (litDisc's rot)
  function atmo(parent, R, { rot = 0, color = '#8fe8ff', width = .07, span = 150 } = {}) {
    const g = el('g', { transform: `rotate(${rot})`, style: 'mix-blend-mode:screen' }, parent), a0 = -span / 2 * Math.PI / 180, a1 = -a0;
    const arc = rr => `M${f(Math.cos(a0) * rr)},${f(Math.sin(a0) * rr)} A${f(rr)},${f(rr)} 0 0 1 ${f(Math.cos(a1) * rr)},${f(Math.sin(a1) * rr)}`;
    const fade = Y_lgrad([[0, color, 0], [.5, color, 1], [1, color, 0]], { user: true, x1: 0, y1: -R, x2: 0, y2: R });
    YS(arc(R * 1.03), fade, R * width * 2.6, g, { opacity: .45, filter: 'url(#glwBlurM)', 'stroke-linecap': 'round' });
    YS(arc(R * 1.005), fade, R * width * .5, g, { opacity: .9, 'stroke-linecap': 'round' });
    return g;
  }

  window.Cosmos = { PAL, star, nebula, stars, space, rocks, atmo };
})();
