// gfx_kit/meso.js · the channel's Mesozoic world: one place with depth, at any time of day. Lifted from the
// cosmic-year-humans standard (w_dec.js meso(), นน 2026-10-22: "the art must never drop below the best world") and
// generalised so any episode can put its animals in it (นน 2026-10-26: Hell Creek looked rushed next to it).
// Layers back to front: sky (sun or moon, clouds) · far (ridges, a misty tree line, optional smoke plumes) · mid
// (araucarias, tree ferns, cycads) · haze · mid2 (bushes, young ferns) · main (ground, litter, light pools, ferns,
// long shadows, dew, dust) · your actors · fg (dark fronds at the frame corners). Every shape is keyed to a palette
// slot, so W.paint(a, b, k) mixes two palettes for continuous time-lapses. Needs kit.js, glow.js and cast.js helpers
// (YS, Yf, Y_ridge, Y_pts, Y_rgrad, Y_lgrad, Y_layer, Y_id, Y_blob, mixColor, sparkle, glowMotes).
//   const W = Meso.world({ gy: 860, x0: -2000, x1: 7000, seed: 1, sun: [1600, 200] });   // gy = the main ground line
//   ... build your actors in a layer created now (they sit on y = gy) ...   W.makeFG();   // corner fronds in front
//   W.paint('day', 'day', 0); W.sky_({ day: 1 });          // palettes: night dawn ash morn day chill
//   render: W.cam([cx, cy, z]) (parallax per layer; your actor layer uses the plain transform), W.sway(T)
//   plants for your own use: Meso.fernPlant / araucaria / treeFern / cycad / bush (parent, x, y, size, W, seed)
(() => {
  const PAL = {
    night: { hill: '#163e50', hill2: '#0f3040', treeD: '#0b2834', tree: '#071c24', treeL: '#4a92a2', mg: '#09222c', bush: '#0c2c30', bushL: '#3a7a78', ground: '#0b2222', groundD: '#061414', gT: '#2e625c', fern: '#0f3c34', fernL: '#4a9a7e', fernD: '#082622', fg: '#020a0a', mound: '#0e2826', log: '#1e2e2e', logL: '#6a9a98', haze: '#1a2a30', rim: '#a8dcff', fog: '#3a7a98' },
    dawn: { hill: '#7e4a66', hill2: '#5e3452', treeD: '#3e2240', tree: '#24121e', treeL: '#ff9a72', mg: '#2c1626', bush: '#301a26', bushL: '#d06a5a', ground: '#26161a', groundD: '#140a0e', gT: '#b0645a', fern: '#301c24', fernL: '#b05a4a', fernD: '#301c24', fg: '#0c0608', mound: '#301c1e', log: '#3c2226', logL: '#e08262', haze: '#7a4a50', rim: '#ffa070', fog: '#e08a7a' },
    ash: { hill: '#1e1214', hill2: '#160e10', treeD: '#2a1416', tree: '#120a0c', treeL: '#c8583a', mg: '#1a1012', bush: '#1c1012', bushL: '#8a3a28', ground: '#1c1412', groundD: '#0c0808', gT: '#7a3a26', fern: '#22161a', fernL: '#4a2420', fernD: '#22161a', fg: '#080505', mound: '#2a1a16', log: '#2a1c18', logL: '#b05a3a', haze: '#3a1a16', rim: '#ff8a50', fog: '#8a3424' },
    morn: { hill: '#c89878', hill2: '#aa7c60', treeD: '#5e6c4a', tree: '#2e4628', treeL: '#f0e098', mg: '#5c5a36', bush: '#3c5e2a', bushL: '#b0d064', ground: '#5c4628', groundD: '#3a2a18', gT: '#e0b874', fern: '#2e6c2a', fernL: '#94d058', fernD: '#2e6c2a', fg: '#142410', mound: '#6c502e', log: '#6c4628', logL: '#f0b874', haze: '#c8b0a0', rim: '#d8f09a', fog: '#f0dcc0' },
    // a bright, saturated day for the cute flat cast (green, teal and violet only: no grey, no brown)
    day: { hill: '#8ccfc4', hill2: '#6fbcb2', treeD: '#4fa89a', tree: '#1f6e5e', treeL: '#c8f28a', mg: '#3f9a62', bush: '#2e8650', bushL: '#a6e676', ground: '#58b862', groundD: '#3a9452', gT: '#b2ec8a', fern: '#2a8a4a', fernL: '#b0f27e', fernD: '#1c6640', fg: '#0c3828', mound: '#4caa5c', log: '#7a62c8', logL: '#d0c0ff', haze: '#d8f2ff', rim: '#fff4c4', fog: '#dcf4ff' },
    // the same day under a cool thin haze (the world after the dart missed: colder for a while)
    chill: { hill: '#94a4e0', hill2: '#7c8cd4', treeD: '#5a6cb8', tree: '#2f4a86', treeL: '#c0d4ff', mg: '#3e7a94', bush: '#2e6a8a', bushL: '#94c4ec', ground: '#4a9aa0', groundD: '#2f7a86', gT: '#a8dce0', fern: '#2c7486', fernL: '#9ad8e8', fernD: '#1e5468', fg: '#102a40', mound: '#428a96', log: '#6a5aa8', logL: '#b8a8ec', haze: '#b0b4ec', rim: '#e8f0ff', fog: '#c4ccf4' },
  };
  const MIST = { night: .34, dawn: .32, ash: .06, morn: .22, day: .16, chill: .38 }, POOL = { night: .3, dawn: .2, ash: .04, morn: .4, day: .35, chill: .12 };
  const SH = { dawn: .3, morn: .28, day: .22, chill: .08 }, DEW = { night: 1, dawn: .6, morn: .4, day: .25, chill: .7 }, DUST = { night: .9, dawn: .5, morn: .4, day: .35, chill: .6 };
  const LK = { sky: .12, far: .35, mid: .6, mid2: .8, main: 1, fg: 1.3 };
  const layT = (k, cam) => { const [cx, cy, z] = cam, ez = 1 + (z - 1) * k; return { ez, ex: 960 + (cx - 960) * k, ey: 540 + (cy - 540) * k }; };
  const softDot = (parent, x, y, r, c, op = 1) => YC(x, y, r, Y_rgrad([[0, c, op], [.45, c, op * .35], [1, c, 0]], { user: true, cx: x, cy: y, r }), parent);

  // a fern frond along +x, curling by `curl` radians over its length: filled leaflets in two tones and a lit midrib
  function frond(g, len, curl, W, kM, kL, kR = kL, lob = .17, rim = false) {
    const n = 16, sp = []; let x = 0, y = 0, a = 0;
    for (let i = 0; i <= n; i++) { sp.push([x, y, a]); a = curl * (i + 1) / n; x += Math.cos(a) * len / n; y += Math.sin(a) * len / n; }
    let dU = '', dD = '';
    for (let i = 1; i < n; i++) { const [px, py, pa] = sp[i], [qx, qy] = sp[i + 1], u = i / n, w = len * lob * Math.pow(1 - u, .6) * Math.min(1, u * 4 + .3);
      [-1, 1].forEach(s => { const nx = -Math.sin(pa) * s, ny = Math.cos(pa) * s, tx = px + Math.cos(pa) * w * .55 + nx * w, ty = py + Math.sin(pa) * w * .55 + ny * w;
        const d = `M${Yf(px)},${Yf(py)} Q${Yf(px + nx * w * .7)},${Yf(py + ny * w * .7)} ${Yf(tx)},${Yf(ty)} Q${Yf((qx + tx) / 2 + nx * w * .2)},${Yf((qy + ty) / 2 + ny * w * .2)} ${Yf(qx)},${Yf(qy)}Z `;
        if (s < 0) dU += d; else dD += d; }); }
    W.pz.push([YP(dD, '', g), kM]); W.pz.push([YP(dU, '', g), kL]);
    if (rim) W.pz.push([YP(dU, 'none', g, { 'stroke-width': Yf(Math.max(1.4, len * .011)), opacity: .85 }), 'rim']);
    W.pz.push([YS('M' + sp.map(([px, py]) => `${Yf(px)},${Yf(py)}`).join(' L'), '', Math.max(2, len * .018), g), kR]);
  }
  function fernPlant(parent, x, y, s, seed, W, keys = ['fernD', 'fern', 'fernL'], n = 8) {
    const g = el('g', { transform: `translate(${x},${y}) scale(${s})` }, parent), R = rng(seed), fr = [];
    for (let i = 0; i < n; i++) { const back = i < n / 2, th = -168 + R() * 156, len = (back ? 120 : 100) + R() * 70, f = el('g', { transform: `rotate(${Yf(th)})` }, g);
      const curl = (Math.cos(th * Math.PI / 180) < 0 ? -1 : 1) * (.9 + R() * .8);
      if (back) frond(f, len, curl, W, keys[0], keys[0], keys[0]); else frond(f, len, curl, W, keys[1], keys[2], keys[2], .17, keys[1] === 'fern');
      fr.push({ f, a: th, ph: R() * 6 }); }
    return { g, fr };
  }
  function araucaria(parent, x, y, h, W, seed) {
    const g = el('g', { transform: `translate(${x},${y})` }, parent), R = rng(seed);
    W.pz.push([YP(`M-10,0 C-8,${-h * .5} -5,${-h * .85} -3,${-h} L3,${-h} C5,${-h * .85} 8,${-h * .5} 10,0Z`, '', g), 'tree']);
    W.pz.push([YS(`M-7,-10 C-6,${-h * .5} -4,${-h * .8} -2,${-h * .95}`, '', 2.5, g, { opacity: .6 }), 'treeL']);
    for (let i = 0; i < 4; i++) { const yy = -h * (.45 + i * .1), w = 46 - i * 7; [-1, 1].forEach(sd => W.pz.push([YS(`M0,${yy} q${sd * w * .6},${-12} ${sd * w},${10}`, '', 4, g), 'tree'])); }
    const cl = [[0, -h - 10, 70, 30], [-56, -h + 14, 48, 22], [56, -h + 10, 52, 22], [-30, -h - 34, 46, 22], [32, -h - 30, 44, 20], [0, -h - 52, 34, 16], [-86, -h + 40, 30, 14], [88, -h + 36, 32, 14]];
    cl.forEach(([cx, cy, rx, ry], k) => { W.pz.push([YP(Y_blob(cx, cy, rx, ry, seed * 10 + k, 10, .28), '', g), 'tree']);
      W.pz.push([YP(Y_blob(cx - rx * .15, cy - ry * .4, rx * .7, ry * .35, seed * 10 + k + 5, 9, .25), '', g, { opacity: .55 }), 'treeL']);
      for (let j = 0; j < 5; j++) W.pz.push([YS(`M${Yf(cx - rx + j * rx * .5)},${Yf(cy + ry * .4)} l${Yf((R() - .5) * 8)},${Yf(10 + R() * 14)}`, '', 3, g), 'tree']); });
    return g;
  }
  function cycad(parent, x, y, s, W, seed) {
    const g = el('g', { transform: `translate(${x},${y}) scale(${s})` }, parent), R = rng(seed);
    W.pz.push([YP('M-22,0 C-26,-30 -22,-62 -16,-76 L16,-76 C22,-62 26,-30 22,0Z', '', g), 'tree']);
    for (let i = 0; i < 6; i++) W.pz.push([YS(`M-20,${-8 - i * 12} L0,${-14 - i * 12} L20,${-8 - i * 12}`, '', 2, g, { opacity: .7 }), 'treeL']);
    for (let i = 0; i < 11; i++) { const th = -175 + i * 17 + (R() - .5) * 8, f = el('g', { transform: `translate(0,-76) rotate(${Yf(th)})` }, g);
      frond(f, 90 + R() * 30, (Math.cos(th * Math.PI / 180) < 0 ? -1 : 1) * .55, W, 'tree', 'treeL', 'tree', .12); }
    return g;
  }
  function treeFern(parent, x, y, h, W, seed) {
    const g = el('g', { transform: `translate(${x},${y})` }, parent), R = rng(seed), bend = (R() - .5) * 40;
    W.pz.push([YS(`M0,0 Q${Yf(bend)},${-h * .5} ${Yf(bend * .3)},${-h}`, '', 16, g), 'tree']);
    for (let i = 0; i < 7; i++) W.pz.push([YS(`M${Yf(bend * .5 * (i / 7) - 8)},${Yf(-h * (i + .5) / 8)} l16,-4`, '', 2, g, { opacity: .6 }), 'treeL']);
    for (let i = 0; i < 9; i++) { const th = -178 + i * 22 + (R() - .5) * 10, f = el('g', { transform: `translate(${Yf(bend * .3)},${-h}) rotate(${Yf(th)})` }, g);
      frond(f, 120 + R() * 50, (Math.cos(th * Math.PI / 180) < 0 ? -1 : 1) * (1.0 + R() * .5), W, 'tree', 'treeL', 'tree', .15); }
    return g;
  }
  function bush(parent, x, y, s, W, seed) {
    const g = el('g', { transform: `translate(${x},${y}) scale(${s})` }, parent), R = rng(seed);
    for (let i = 0; i < 6; i++) { const bx = (R() - .5) * 120, by = -20 - R() * 40, rx = 34 + R() * 30, ry = 22 + R() * 16;
      W.pz.push([YP(Y_blob(bx, by, rx, ry, seed * 7 + i, 10, .3), '', g), 'bush']);
      W.pz.push([YP(Y_blob(bx - rx * .2, by - ry * .45, rx * .55, ry * .3, seed * 7 + i + 50, 9, .3), '', g, { opacity: .6 }), 'bushL']); }
    return g;
  }

  // the world: o.gy ground line, o.x0..o.x1 extent of the main ground, o.sun / o.moon [x, y] in the sky layer, o.plumes
  // (smoke columns in the far layer, shown by the ash palette), o.pal extra palettes { name: {...slots} }
  function world(o = {}) {
    const gy = o.gy ?? 760, dy = gy - 760, x0 = o.x0 ?? -1200, x1 = o.x1 ?? 3200, seed = o.seed ?? 1, span = x1 - x0;
    Object.assign(PAL, o.pal || {});
    const W = { pz: [], st: [], gy, x0, x1 };
    for (const n of ['sky', 'far', 'mid', 'haze', 'mid2', 'main']) W[n] = Y_layer(Y.cam);
    const sx0 = x0 - 1500, sw = span + 3000;
    const skyR = (stops) => el('rect', { x: sx0, y: gy - 3260, width: sw, height: 4000, fill: Y_lgrad(stops, { user: true, x1: 0, y1: gy - 1160, x2: 0, y2: gy }), opacity: 0 }, W.sky);
    W.skies = {
      night: skyR([[0, '#030814'], [.45, '#0a1c34'], [.8, '#17405a'], [1, '#2a6070']]),
      dawn: skyR([[0, '#2a2a5a'], [.45, '#7a4a78'], [.75, '#e0786a'], [.9, '#ffb070'], [1, '#ffd890']]),
      ash: skyR([[0, '#0e0a0e'], [.45, '#2a1418'], [.72, '#6a2420'], [.88, '#d0502a'], [1, '#ff9a4a']]),
      morn: skyR([[0, '#4a8ac8'], [.45, '#8ab8d8'], [.8, '#f0d8b0'], [1, '#ffe0a8']]),
      day: skyR([[0, '#2a86e8'], [.5, '#5cc0ff'], [.85, '#b8ecff'], [1, '#e8fbff']]),
      chill: skyR([[0, '#3e52b8'], [.5, '#6e86d8'], [.85, '#aebcf2'], [1, '#d8dcfc']]),
    };
    W.stars = el('g', {}, W.sky); Y_pts(Math.round(220 * span / 4400), 18, [x0 + 600, -900 + dy, span - 1200, 1500]).forEach(([x, y, a, b]) => { if (a > .93) YP(sparkle(5 + a * 4), '#f0f8ff', W.stars, { transform: `translate(${Yf(x)},${Yf(y)})`, opacity: .8 }); else YC(Yf(x), Yf(y), (.7 + a * 1.8).toFixed(2), b < .2 ? '#ffe8c8' : '#e8f4ff', W.stars, { opacity: (.3 + .6 * a).toFixed(2) }); });
    W.st.push([W.stars, { night: 1 }]);
    W.clouds = el('g', {}, W.sky); const RC = rng(seed * 97 + 3); W.st.push([W.clouds, { night: 1, dawn: 1, ash: 1, morn: 1 }]);   // long bands: not in the cartoon day
    for (let i = 0, n = Math.round(span / 900) + 3; i < n; i++) { const x = x0 - 400 + i * 900 + RC() * 300, y = 120 + dy + RC() * 280, l = 300 + RC() * 240, h = 14 + RC() * 12;
      W.pz.push([YP(Y_blob(x, y, l, h, 970 + i, 12, .35), '', W.clouds, { opacity: .5 }), 'hill']); W.pz.push([YP(Y_blob(x - 20, y - h * .5, l * .8, h * .4, 980 + i, 12, .35), '', W.clouds, { opacity: .45 }), 'treeL']); }
    W.cloudsDay = el('g', {}, W.sky); W.st.push([W.cloudsDay, { day: 1, chill: .7, morn: .4 }]);
    for (let i = 0, n = Math.round(span / 700) + 3; i < n; i++) { const x = x0 - 300 + i * 700 + RC() * 250, y = -120 + dy + RC() * 420, s = .7 + RC() * .9, g = el('g', { transform: `translate(${Yf(x)},${Yf(y)}) scale(${s.toFixed(2)})` }, W.cloudsDay);
      YC(-50, 14, 40, '#ffffff', g); YC(10, -8, 56, '#ffffff', g); YC(70, 16, 36, '#ffffff', g);
      YP('M-90,30 C-90,10 110,10 106,30 C110,50 -90,50 -90,30Z', '#ffffff', g); YP('M-84,34 C-40,46 70,46 102,34 C104,46 -84,48 -84,34Z', '#dcefff', g); }
    const mo = o.moon || [x0 + 1760, 150 + dy], su = o.sun || [x0 + 2700, 150 + dy];
    W.moon = el('g', { transform: `translate(${mo[0]},${mo[1]})` }, W.sky); W.st.push([W.moon, { night: 1 }]);
    YC(0, 0, 420, Y_rgrad([[0, '#d8f0f0', .38], [.25, '#a8d0d8', .14], [1, '#a8d0d8', 0]], { user: true, cx: 0, cy: 0, r: 420 }), W.moon);
    YC(0, 0, 60, Y_rgrad([[0, '#fbf6ff'], [.7, '#dcd0ff'], [1, '#a896ee']], { user: true, cx: -14, cy: -14, r: 76 }), W.moon);   // lavender-white, never grey
    [[-16, -10, 10], [14, 12, 8], [8, -22, 6], [-10, 22, 7]].forEach(([x, y, r]) => YC(x, y, r, '#9a86e0', W.moon, { opacity: .5 }));
    W.sun = el('g', { transform: `translate(${su[0]},${su[1]})` }, W.sky); W.st.push([W.sun, { morn: 1, day: 1, chill: .35 }]);
    YC(0, 0, 480, Y_rgrad([[0, '#fff4c8', .55], [.25, '#ffe0a0', .2], [1, '#ffe0a0', 0]], { user: true, cx: 0, cy: 0, r: 480 }), W.sun);
    YC(0, 0, 58, Y_rgrad([[0, '#ffffff'], [.7, '#fff6d8'], [1, '#ffe8b0']], { user: true, cx: 0, cy: 0, r: 58 }), W.sun);
    // far: ridges, smoke plumes (ash), a misty tree line
    W.smoke = el('g', {}, W.far); W.st.push([W.smoke, { ash: 1 }]);
    W.plumes = (o.plumes || []).map(([x, y, s], i) => { const R = rng(1300 + i);
      return { x, y: y + dy, s, ph: R() * 6, puffs: Array.from({ length: 9 }, (_, k) => { const e = el('g', {}, W.smoke);
        YP(Y_blob(0, 0, 70, 52, 1400 + i * 20 + k, 10, .3), '#1e1214', e); YP(Y_blob(-6, 14, 54, 26, 1450 + i * 20 + k, 9, .3), '#7a2a1c', e, { opacity: .55 });
        return { e, k }; }) }; });
    W.hills = el('g', {}, W.far);
    const fx0 = x0 - 1200, fx1 = x1 + 1200;
    W.pz.push([YP(Y_ridge(fx0, fx1, 610 + dy, 120, 31 + seed, 1700 + dy, 160), '', W.hills), 'hill']);
    W.pz.push([YP(Y_ridge(fx0, fx1, 660 + dy, 60, 37 + seed, 1700 + dy, 110), '', W.hills), 'hill2']);
    let tl = `M${fx0},${1700 + dy} L${fx0},${690 + dy}`; const RL = rng(39 + seed);
    for (let x = fx0; x <= fx1; x += 22) { const tall = RL() < .3 ? 40 + RL() * 50 : 10 + RL() * 16; tl += ` L${x},${Yf(690 + dy - tall * .2)} L${x + 6},${Yf(690 + dy - tall)} L${x + 12},${Yf(690 + dy - tall * .2)}`; }
    W.pz.push([YP(tl + ` L${fx1},${1700 + dy}Z`, '', W.hills), 'treeD']);
    const mist = (parent, y, h) => el('rect', { x: fx0, y: y - h / 2, width: fx1 - fx0, height: h, fill: Y_lgrad([[0, '#ffffff', 0], [.5, '#ffffff', .9], [1, '#ffffff', 0]], { user: true, x1: 0, y1: y - h / 2, x2: 0, y2: y + h / 2 }), style: 'mix-blend-mode:screen' }, parent);
    W.mists = [mist(W.far, 690 + dy, 120)];
    // mid: Mesozoic trees
    W.pz.push([el('rect', { x: fx0, y: 716 + dy, width: fx1 - fx0, height: 1200 }, W.mid), 'mg']);
    W.trees = el('g', {}, W.mid); const RT = rng(77 + seed);
    for (let i = 0, n = Math.round((fx1 - fx0) / 205); i < n; i++) { const x = fx0 + 100 + i * 205 + RT() * 90, k = RT();
      if (k < .42) araucaria(W.trees, x, 722 + dy, 380 + RT() * 160, W, 30 + i + seed * 100); else if (k < .72) treeFern(W.trees, x, 722 + dy, 170 + RT() * 90, W, 300 + i + seed * 100); else cycad(W.trees, x, 722 + dy, 1.1 + RT() * .5, W, 400 + i + seed * 100); }
    W.midA = el('g', {}, W.mid);
    W.mists.push(mist(W.mid, 726 + dy, 70)); W.mists.push(mist(W.mid2, 752 + dy, 60));
    W.hazeR = el('rect', { x: sx0, y: -3000 + dy, width: sw, height: 5200, opacity: 0 }, W.haze); W.pz.push([W.hazeR, 'haze']);
    W.st.push([W.hazeR, { day: .2, chill: .3, morn: .14 }]);                // aerial perspective: the far rows lighter than the near
    // light shafts from the sun, through the trees (screen blend, slow sway)
    W.rays = el('g', { style: 'mix-blend-mode:screen' }, W.haze); W.st.push([W.rays, { day: .9, morn: .8, dawn: .6, chill: .25 }]);
    const ro = [su[0] * .6 + 960 * .4, su[1] - 200], RR = rng(seed * 13 + 7);
    W.ray = Array.from({ length: 7 }, (_, i) => { const a = (100 + i * 11 + RR() * 6) * Math.PI / 180, w = .03 + RR() * .04, L_ = 2400;
      const e = YP(`M${Yf(ro[0])},${Yf(ro[1])} L${Yf(ro[0] + Math.cos(a - w) * L_)},${Yf(ro[1] + Math.sin(a - w) * L_)} L${Yf(ro[0] + Math.cos(a + w) * L_)},${Yf(ro[1] + Math.sin(a + w) * L_)}Z`,
        Y_lgrad([[0, '#fff6d8', .5], [.55, '#fff6d8', .16], [1, '#fff6d8', 0]], { user: true, x1: ro[0], y1: ro[1], x2: ro[0], y2: ro[1] + 1400 }), W.rays);
      return { e, ph: RR() * 6 }; });
    // mid2: bushes and young ferns on the near ground
    W.pz.push([el('rect', { x: fx0, y: 744 + dy, width: fx1 - fx0, height: 1200 }, W.mid2), 'mg']);
    const RB = rng(55 + seed);
    for (let i = 0, n = Math.round((fx1 - fx0) / 230); i < n; i++) { const x = fx0 + 200 + i * 230 + RB() * 100; if (RB() < .55) bush(W.mid2, x, 750 + dy, .8 + RB() * .5, W, 500 + i + seed * 100); else fernPlant(W.mid2, x, 752 + dy, .7 + RB() * .4, 520 + i + seed * 100, W, ['fernD', 'fernD', 'fern'], 7); }
    W.mid2A = el('g', {}, W.mid2);
    // main ground: gradient, litter and pebbles, light pools
    const gx0 = x0 - 600, gw = span + 1200;
    W.pz.push([el('rect', { x: gx0, y: gy, width: gw, height: 1600 }, W.main), 'ground']);
    W.pz.push([YP(Y_ridge(gx0, gx0 + gw, gy + 2, 8, 11 + seed, gy + 40, 70), '', W.main), 'gT']);
    W.pz.push([YP(Y_ridge(gx0, gx0 + gw, gy + 8, 8, 12 + seed, gy + 1140, 70), '', W.main), 'ground']);
    el('rect', { x: gx0, y: gy, width: gw, height: 900, fill: Y_lgrad([[0, '#000', 0], [1, '#000', .4]], { user: true, x1: 0, y1: gy, x2: 0, y2: gy + 640 }) }, W.main);
    // aerial perspective: the far ground fades into a coloured fog
    const fm = Y_id('m'); Y.defs.insertAdjacentHTML('beforeend', `<mask id="${fm}" maskUnits="userSpaceOnUse" x="${gx0 - 1000}" y="-3000" width="${gw + 2000}" height="9000"><rect x="${gx0 - 1000}" y="${gy - 4}" width="${gw + 2000}" height="180" fill="${Y_lgrad([[0, '#ffffff'], [1, '#000000']], { user: true, x1: 0, y1: gy, x2: 0, y2: gy + 170 })}"/></mask>`);
    W.fogB = el('rect', { x: gx0, y: gy - 4, width: gw, height: 180, mask: `url(#${fm})` }, W.main); W.pz.push([W.fogB, 'fog']);
    W.st.push([W.fogB, { night: .7, dawn: .5, ash: .45, morn: .35, day: .3, chill: .6 }]);
    W.pools = el('g', { style: 'mix-blend-mode:screen' }, W.main); const RP = rng(61 + seed);
    for (let i = 0, n = Math.round(span / 520); i < n; i++) { const e = softDot(W.pools, 0, 0, 300 + RP() * 120, '#ffffff', .5); set(e, { transform: `translate(${Yf(x0 + i * 520 + RP() * 200)},${Yf(gy + 200 + RP() * 120)}) scale(1,.22)` }); }
    const RLt = rng(81 + seed);
    for (let i = 0, n = Math.round(260 * span / 3200); i < n; i++) { const x = x0 + RLt() * span, y = gy + 10 + Math.pow(RLt(), .8) * 330, l = 4 + (y - gy) * .05, a = (RLt() - .5) * 2;
      if (RLt() < .7) W.pz.push([YS(`M${Yf(x)},${Yf(y)} l${Yf(Math.cos(a) * l)},${Yf(Math.sin(a) * l * .4)}`, '', 1.5 + (y - gy) * .006, W.main, { opacity: .7 }), RLt() < .5 ? 'gT' : 'groundD']);
      else W.pz.push([YE(Yf(x), Yf(y), Yf(l * .5), Yf(l * .25), '', W.main, { opacity: .6 }), 'groundD']); }
    // ground ferns, back rows small, near rows big (o.clear: [[x0, x1], ...] keeps strips free for the actors)
    W.ferns = []; const RF = rng(91 + seed), clear = o.clear || [];
    const rows = [[40, .4], [90, .6], [180, .8], [240, 1.05]];
    rows.forEach(([oy, s], r) => { for (let x = x0 + RF() * 200; x < x1; x += 260 + RF() * 260) { if (clear.some(([a, b]) => x > a && x < b)) continue;
      W.ferns.push({ y: gy + oy + RF() * 20, x, s: s * (.85 + RF() * .35), sd: 600 + W.ferns.length + seed * 1000 }); } });
    W.ferns = W.ferns.sort((a, b) => a.y - b.y).map(q => fernPlant(W.main, Yf(q.x), Yf(q.y), q.s.toFixed(2), q.sd, W));
    // long shadows under the ferns (the sun is to the right)
    if (!document.getElementById('mesoSh')) Y.defs.insertAdjacentHTML('beforeend', '<filter id="mesoSh" x="-30%" y="-60%" width="160%" height="220%"><feFlood flood-color="#000"/><feComposite in2="SourceAlpha" operator="in"/><feGaussianBlur stdDeviation="6"/></filter>');
    W.longSh = el('g', { filter: 'url(#mesoSh)' }, W.main); if (W.ferns[0]) W.main.insertBefore(W.longSh, W.ferns[0].g); W.st.push([W.longSh, SH]);
    W.ferns.forEach(q => { const m = q.g.getAttribute('transform').match(/translate\(([-\d.]+),([-\d.]+)\) scale\(([\d.]+)\)/), x = +m[1], y = +m[2], sc = +m[3];
      const c = q.g.cloneNode(true); c.setAttribute('transform', `translate(${x},${y + 2}) skewX(-55) scale(${sc},${(-.24 * sc).toFixed(3)})`); W.longSh.appendChild(c); });
    W.mainA = el('g', {}, W.main);
    // dew glints and drifting dust
    W.dew = el('g', {}, W.main); W.st.push([W.dew, DEW]);
    W.dw = Y_pts(Math.round(36 * span / 2600), 444 + seed, [x0, gy + 120, span, 130]).map(([x, y, a, b]) => { const g = el('g', { transform: `translate(${Yf(x)},${Yf(y)})` }, W.dew);
      softDot(g, 0, 0, 14, '#e8f8ff', .8); YP(sparkle(7 + a * 6), '#ffffff', g); return { g, x, y, ph: b * 6, sp: 1.5 + a * 2 }; });
    W.dustG = el('g', {}, W.main); W.st.push([W.dustG, DUST]);
    W.dusts = []; for (let x = x0; x < x1; x += 2600) { W.dusts.push(glowMotes(W.dustG, 4545 + x, { n: 40, colors: ['#fff6d8', '#e8f8ff'], size: [.6, 1.8], h: 380, drift: 5 })); set(W.dustG.lastChild, { transform: `translate(${x - 300},${gy - 120})` }); }
    // corner fronds in front of the actors: call after the actor layer exists; they hold the frame corners
    W.makeFG = () => { W.fg = Y_layer(Y.cam); const fgIn = el('g', { filter: 'url(#glwBlurS)' }, W.fg);
      W.fgF = [[-60, 1190, 3.6, 701], [1990, 1200, 3.8, 702], [520, 1330, 2.0, 703], [1430, 1340, 1.9, 704]].map(([x, y, s, sd]) => ({ ...fernPlant(fgIn, x, y, s, sd + seed * 10, W, ['fg', 'fg', 'fernD'], 7), x, y, s }));
      W.pz.forEach(q => { q[2] = q[0].getAttribute('fill') === 'none' ? 'stroke' : 'fill'; }); return W.fg; };
    W.paint = (a, b, k) => { W.pz.forEach(([e, key, at]) => e.setAttribute(at || 'fill', mixColor(PAL[a][key], PAL[b][key], k)));
      const m = lerp(MIST[a], MIST[b], k), pl = lerp(POOL[a], POOL[b], k); W.mists.forEach(e => show(e, m)); show(W.pools, pl);
      W.st.forEach(([e, v]) => show(e, lerp(v[a] || 0, v[b] || 0, k))); };
    W.sky_ = (w) => Object.entries(W.skies).forEach(([n, e]) => show(e, w[n] || 0));
    // parallax: every layer follows the camera by its own factor; fg corner fronds hold the screen with a drift
    W.cam = (cam, anchor = cam[0], hideFG = 0) => {
      for (const n of ['sky', 'far', 'mid', 'haze', 'mid2', 'main']) { const k = LK[n === 'haze' ? 'mid' : n], q = layT(k, cam);
        set(W[n], { transform: `translate(960,540) scale(${q.ez.toFixed(4)}) translate(${Yf(-q.ex)},${Yf(-q.ey)})` }); }
      if (W.onCam) W.onCam(cam);
      if (W.fg) { const dx = -(cam[0] - anchor) * .35; W.fgF.forEach((q, i) => set(q.g, { transform: `translate(${Yf(q.x + dx * (i % 2 ? 1.2 : 1))},${Yf(q.y - 1800 * hideFG)}) scale(${q.s})` })); } };
    W.sway = T => { W.ferns.concat(W.fgF || []).forEach(pl => pl.fr.forEach(f => set(f.f, { transform: `rotate(${Yf(f.a + 2.5 * Math.sin(T * .9 + f.ph))})` })));
      W.ray.forEach(r => show(r.e, .7 + .3 * Math.sin(T * .5 + r.ph)));
      W.dw.forEach(q => set(q.g, { transform: `translate(${Yf(q.x)},${Yf(q.y)}) scale(${(.25 + .75 * Math.max(0, Math.sin(T * q.sp + q.ph)) ** 3).toFixed(3)})` })); W.dusts.forEach(d => d(T));
      W.plumes.forEach(pl => pl.puffs.forEach(q => { const u = ((T * .06 + q.k / 9 + pl.ph) % 1);
        set(q.e, { transform: `translate(${Yf(pl.x + 60 * u * Math.sin(pl.ph + u * 3) + 120 * u)},${Yf(pl.y - 520 * u * pl.s)}) scale(${(pl.s * (.5 + 1.6 * u)).toFixed(3)})`, opacity: (Math.min(1, u * 6) * (1 - u * .6)).toFixed(2) }); })); };
    W.pz.forEach(q => { q[2] = q[0].getAttribute('fill') === 'none' ? 'stroke' : 'fill'; });
    return W;
  }
  // re-key late additions (plants a scene adds after world()) so W.paint colours them too
  const rekey = W => W.pz.forEach(q => { q[2] = q[0].getAttribute('fill') === 'none' ? 'stroke' : 'fill'; });

  // terrain(W, o): a dense mapped valley seen from a fake high angle (นน 2026-10-27: "a map with layers", not an open
  // field; refs: the Kurzgesagt Cretaceous valley and waterfall scenes). Call after world() and makeFG(); day scenes only
  // (fixed colours, W.paint leaves them alone). It hides Meso's own sky, ridges, mid-row trees, bushes and blurred corner
  // fronds, then draws per parallax layer, in that layer's own coordinates, for a camera whose cy puts the horizon near
  // 28 % of the frame and the ground line near 73 % (cy = gy - 220 at z 1.15; gy 860 gives the numbers below):
  //   Values follow LIBRARY "Backgrounds in look B": each layer back is lighter and closer to the horizon colour, the
  //   nearest is the darkest (the main ground gets a dark veil for that).
  //   sky   blue to violet to a pink-peach horizon at y 320, lit cloud banks (scalloped tops, flat base; W.cloudsDay), a
  //         small sun, pterosaurs
  //   far   two rows of pale rounded ranges (dome, mesa, spire, saddle; no two neighbours alike), a far plain with a soft
  //         jungle edge and palms (base y 350-380)
  //   mid   the valley (y 424-750): grass bands lighter with distance and a jungle edge along the top; at each o.cliffs x a
  //         stepped cliff of rounded purple rock columns under overhanging jungle, a wide striped waterfall per tier with
  //         foam into a lake, and a river out of the lake toward the camera (50 -> 420 wide); the water is a gradient with
  //         the sun's column of dashes kept under the sun (W.onCam), two-tone ripples denser toward the camera, rocks with
  //         foam and floating lily pads and leaves; groves, palms, grass tufts, small far herds
  //   mid2  a near bank (bushes, tropical leaf plants, faceted purple rocks, ferns) with gaps behind o.stages
  //   main  a sand stage under each o.stages actor set · fg: crisp broad leaves lower left, a warm bank lower right
  //   o: { seed, cliffs: [mid-layer x of each cliff's left edge], stages: [[world x, width]], sun: [x, y] in the sky layer,
  //        view: { sky, far, mid, mid2: [x0, x1] } the span of each layer the cameras see (the dense detail goes there),
  //        keep: [elements the scene already added to these layers, which terrain must not hide] }
  function terrain(W, o = {}) {
    const R = rng(o.seed ?? 7), x0 = W.x0 - 2000, x1 = W.x1 + 2000, gy = W.gy, d = gy - 860, f = Yf, V = o.view || {};
    const span = n => V[n] || [x0, x1];
    const hide = e => { if (e) e.style.display = 'none'; };
    const keep = [W.midA, W.mid2A, ...(o.keep || [])];   // o.keep: the scene's own pieces already in these layers
    [...W.sky.children, ...W.far.children, ...W.mid.children, ...W.mid2.children].forEach(e => { if (!keep.includes(e)) hide(e); });
    (W.fgF || []).forEach(q => hide(q.g)); W.fgF = []; W.mists = [];
    // a look-B body: the light band on the upper left, a dark crescent on the lower right (as flat.js; the scene may run
    // another look); circles and rounded rects as clockwise subpaths, so a union of them has no holes
    const litB = (parent, dd, fill, light, dark, dx = 8, dy = 7) => { const g = el('g', {}, parent); YP(dd, light, g);
      const g2 = el('g', { transform: `translate(${f(dx * .7)},${f(dy * .7)})` }, Y_clipTo(g, dd)), c2 = Y_clipTo(g2, dd); YP(dd, dark, c2);
      YP(dd, fill, el('g', { transform: `translate(${f(-dx * 1.8)},${f(-dy * 1.8)})` }, c2)); return g; };
    const circD = (cx, cy, r) => `M${f(cx - r)},${f(cy)}A${f(r)},${f(r)} 0 1 1 ${f(cx + r)},${f(cy)}A${f(r)},${f(r)} 0 1 1 ${f(cx - r)},${f(cy)}Z`;
    const rrD = (x, y, w, h, r) => `M${f(x + r)},${f(y)}H${f(x + w - r)}A${f(r)},${f(r)} 0 0 1 ${f(x + w)},${f(y + r)}V${f(y + h - r)}A${f(r)},${f(r)} 0 0 1 ${f(x + w - r)},${f(y + h)}H${f(x + r)}A${f(r)},${f(r)} 0 0 1 ${f(x)},${f(y + h - r)}V${f(y + r)}A${f(r)},${f(r)} 0 0 1 ${f(x + r)},${f(y)}Z`;
    // shared painters: a clump of round crowns (each lit on its upper left), a palm, a broad leaf, a tropical leaf plant
    const clump = (g, x, y, r, n, cs) => { const c = Array.from({ length: n }, () => [x + (R() - .5) * r * n * .5, y - R() * r * .7, r * (.7 + R() * .45)]);
      c.forEach(([cx, cy, rr]) => YC(f(cx), f(cy), f(rr), cs[0], g)); c.forEach(([cx, cy, rr]) => YC(f(cx - rr * .16), f(cy - rr * .2), f(rr * .74), cs[1], g));
      if (cs[2]) c.forEach(([cx, cy, rr]) => { if (rr > 9) YE(f(cx - rr * .36), f(cy - rr * .46), f(rr * .26), f(rr * .14), cs[2], g, { transform: `rotate(-30 ${f(cx - rr * .36)} ${f(cy - rr * .46)})` }); }); };
    const palm = (g, x, y, h, cs = ['#1f7a5a', '#3fae6a', '#2f5a46']) => { const p = el('g', { transform: `translate(${f(x)},${f(y)})` }, g), b = (R() - .5) * h * .5;
      YS(`M0,0 Q${f(b * .1)},${f(-h * .55)} ${f(b)},${f(-h)}`, cs[2], f(Math.max(2, h * .065)), p, { 'stroke-linecap': 'round' });
      const t = el('g', { transform: `translate(${f(b)},${f(-h)})` }, p), w = h * .1;
      for (let k = 0; k < 7; k++) { const a = -172 + k * 27 + (R() - .5) * 12, sg = Math.cos(a * Math.PI / 180) < 0 ? -1 : 1, l = h * (.5 + R() * .18);
        const e = el('g', { transform: `rotate(${f(a)})` }, t);
        YP(`M0,0 Q${f(l * .5)},${f(-sg * (l * .14 + w))} ${f(l)},${f(sg * l * .38)} Q${f(l * .5)},${f(-sg * l * .14 + sg * w * .6)} 0,0Z`, k % 2 ? cs[0] : cs[1], e); }
      if (h > 60) [[-5, 6], [5, 8], [0, 12]].forEach(([dx, dy2]) => YC(f(b + dx * h / 120), f(-h + dy2 * h / 120), f(h * .035), '#e8903a', p)); };
    const bleaf = (g, a, l, w, c, cl, cm) => { const e = el('g', { transform: `rotate(${f(a)})` }, g);
      YP(`M0,0 C${f(l * .2)},${f(-w)} ${f(l * .7)},${f(-w * .8)} ${f(l)},0 C${f(l * .7)},${f(w * .8)} ${f(l * .2)},${f(w)} 0,0Z`, c, e);
      YP(`M0,0 C${f(l * .2)},${f(-w)} ${f(l * .7)},${f(-w * .8)} ${f(l)},0Z`, cl, e); YS(`M6,0 L${f(l * .94)},0`, cm, f(Math.max(2, w * .07)), e, { 'stroke-linecap': 'round' }); };
    const tropic = (g, x, y, s) => { const p = el('g', { transform: `translate(${f(x)},${f(y)}) scale(${s.toFixed(2)})` }, g);
      [-160, -128, -96, -64, -30].forEach((a, k) => bleaf(p, a + (R() - .5) * 12, 120 + R() * 50, 34 + R() * 8, k % 2 ? '#1f7a5a' : '#25866a', '#46b07a', '#145a48')); };
    // ---------------- sky
    const sky = el('g', { transform: `translate(0,${d})` }, W.sky); W.sky.insertBefore(sky, W.sky.firstChild);
    el('rect', { x: x0 - 3000, y: -3000, width: x1 - x0 + 6000, height: 4600, fill: Y_lgrad([[0, '#2446d0'], [.568, '#3a5fe0'], [.73, '#6b8cf2'], [.878, '#b88ae6'], [.932, '#ff9ec4'], [.973, '#ffc49a'], [1, '#ffd8a8']], { user: true, x1: 0, y1: -400, x2: 0, y2: 340 }) }, sky);
    const su = o.sun || [1550, 130];
    YC(su[0], su[1], 150, Y_rgrad([[0, '#fff6c0', .85], [.45, '#ffe08a', .3], [1, '#ffe08a', 0]], { user: true, cx: su[0], cy: su[1], r: 150 }), sky);
    YC(su[0], su[1], 44, '#fffbea', sky);
    W.cloudsDay = el('g', {}, sky);
    const cloud = (x, y, w, c) => { const h = w * .15; let dd = rrD(x - w / 2, y - h, w, h, h / 2), cx = x - w / 2 + w * .13;
      while (cx < x + w / 2 - w * .1) { const r = w * (.08 + R() * .08); dd += circD(cx, y - h * .6 - r * .5, r); cx += r * 1.25; }
      litB(W.cloudsDay, dd, c[0], c[1], c[2], 9, 8); };
    { const [a, b] = span('sky'); for (let x = a + R() * 120; x < b; x += 230 + R() * 230) { const low = R() < .4;
      if (low) cloud(x, 270 + R() * 30, 90 + R() * 70, ['#ffe2ee', '#fff4f8', '#f4bcd6']);   // near the horizon: pinker, closer to its colour
      else cloud(x, 130 + R() * 110, 170 + R() * 130, ['#f6f2ff', '#ffffff', '#d4c6f4']); } }
    const ptero = (x, y, s, c, cl) => { const g = el('g', { transform: `translate(${f(x)},${f(y)}) scale(${s})` }, sky);
      YP('M-6,-2 Q-30,-30 -66,-26 Q-40,-14 -30,2 Q-16,6 -6,4Z', c, g); YP('M6,-2 Q34,-34 72,-30 Q44,-14 32,2 Q16,6 6,4Z', c, g);
      YP('M-8,0 Q-28,-22 -54,-22 Q-34,-12 -26,0Z', cl, g); YP('M8,0 Q30,-26 60,-26 Q38,-12 28,0Z', cl, g);
      YE(0, 0, 18, 7, c, g); YP('M14,-6 L46,-1 L16,3Z', c, g); YP('M12,-6 L-2,-18 L20,-9Z', '#e8608a', g); YC(18, -3, 2, '#ffffff', g); };
    [[su[0] + 820, 112, 1.2], [su[0] + 1000, 156, .8], [su[0] + 2400, 96, 1], [su[0] + 2600, 140, .7]].forEach(([x, y, s]) => ptero(x, y, s, '#5a3fa8', '#7d63d0'));
    // ---------------- far: two rows of angular peaks, a far plain, a dense jungle edge with palms
    const far = el('g', { transform: `translate(0,${d})` }, W.far); W.far.insertBefore(far, W.far.firstChild);
    const hillD = (x, base, w, h, type) => type === 0 ? `M${f(x - w)},${f(base)} C${f(x - w * .7)},${f(base - h * 1.3)} ${f(x + w * .7)},${f(base - h * 1.3)} ${f(x + w)},${f(base)}Z`   // dome
      : type === 1 ? `M${f(x - w)},${f(base)} L${f(x - w * .62)},${f(base - h * .7)} Q${f(x - w * .55)},${f(base - h)} ${f(x - w * .4)},${f(base - h)} L${f(x + w * .36)},${f(base - h)} Q${f(x + w * .52)},${f(base - h)} ${f(x + w * .58)},${f(base - h * .72)} L${f(x + w)},${f(base)}Z`   // mesa
      : type === 2 ? `M${f(x - w)},${f(base)} C${f(x - w * .45)},${f(base - h * .2)} ${f(x - w * .42)},${f(base - h)} ${f(x)},${f(base - h)} C${f(x + w * .42)},${f(base - h)} ${f(x + w * .45)},${f(base - h * .2)} ${f(x + w)},${f(base)}Z`   // rounded spire
      : `M${f(x - w)},${f(base)} C${f(x - w * .8)},${f(base - h * 1.2)} ${f(x - w * .2)},${f(base - h * 1.2)} ${f(x)},${f(base - h * .62)} C${f(x + w * .2)},${f(base - h * .95)} ${f(x + w * .75)},${f(base - h * .95)} ${f(x + w)},${f(base)}Z`;   // saddle
    { const [a, b] = span('far'); let ty = 0;
      [[352, [60, 130], ['#d4c4f4', '#e8defa', '#bcaaec']], [362, [36, 96], ['#c0b2f0', '#d8cef8', '#a698e4']]].forEach(([base, [h0, h1], c], row) => {
        for (let x = a - 200 + row * 80; x < b + 200; x += 150 + R() * 170) { ty = (ty + 1 + Math.floor(R() * 3)) % 4;
          const w = (ty === 2 ? 100 : 110) + R() * 90; litB(far, hillD(x, base, w, h0 + R() * (h1 - h0), ty), c[0], c[1], c[2], 10, 8); } }); }
    el('rect', { x: x0, y: 362, width: x1 - x0, height: 900, fill: '#94d0b0' }, far);
    { const [a, b] = span('far'); for (let x = a; x < b; x += 36 + R() * 40) { clump(far, x, 372 + R() * 14, 9 + R() * 8, 3, ['#88c8a8', '#a6dcc0', '#c8eedc']);
      if (R() < .22) palm(far, x + 10, 376 + R() * 8, 40 + R() * 24, ['#7cbea0', '#9ed4b8', '#6aa88e']); } }
    // ---------------- mid: the valley
    const mid = el('g', { transform: `translate(0,${d})` }, W.mid); W.mid.insertBefore(mid, W.mid.firstChild);
    const [m0, m1] = span('mid');
    const wav = (y, amp, sd) => Array.from({ length: Math.ceil((x1 - x0) / 220) + 1 }, (_, i) => `L${x0 + i * 220},${f(y + amp * Math.sin(i * 1.3 + sd))}`).join(' ');
    [[424, '#84cc88'], [508, '#5cc165'], [600, '#3fae58']].forEach(([y, c], i) => YP(`M${x0},${y} ${wav(y, i ? 9 : 4, i * 2)} L${x1},1300 L${x0},1300Z`, c, mid));
    for (let x = m0; x < m1; x += 26 + R() * 30) clump(mid, x, 430 + R() * 12, 11 + R() * 7, 3, ['#4a9e7e', '#6cbe8e', '#ade6b2']);   // the far jungle edge, lighter than the groves in front
    for (let i = 0; i < (m1 - m0) / 14; i++) { const x = m0 + R() * (m1 - m0), y = 450 + R() * 280, s = .5 + (y - 424) / 220;   // grass tufts
      YS(`M${f(x - 5 * s)},${f(y)} l${f(3 * s)},${f(-8 * s)} M${f(x)},${f(y)} l0,${f(-11 * s)} M${f(x + 5 * s)},${f(y)} l${f(-3 * s)},${f(-8 * s)}`, y < 508 ? '#6cc074' : y < 600 ? '#46a85a' : '#2f9a4e', f(1.6 * s), mid, { 'stroke-linecap': 'round' }); }
    const avoid = [], water = [];
    (o.cliffs || []).forEach(X0 => { const g = el('g', {}, mid), foam = [];
      const tiers = [[0, 470, 214, 450], [96, 610, 352, 566], [190, 740, 484, 676]];
      tiers.forEach(([a, b, ya, yb], i) => { const tg = el('g', {}, g);
        // rounded rock columns, tallest at the back, each lit on its left and shaded on its right
        for (let x = X0 + a; x < X0 + b - 10;) { const w = Math.min(60 + R() * 50, X0 + b - x), top = ya + (R() - .4) * 34, r = w * .42;
          YP(`M${f(x)},${yb} L${f(x)},${f(top + r)} Q${f(x)},${f(top)} ${f(x + r)},${f(top)} L${f(x + w - r)},${f(top)} Q${f(x + w)},${f(top)} ${f(x + w)},${f(top + r)} L${f(x + w)},${yb}Z`, '#7c4fd4', tg);
          YP(`M${f(x)},${yb} L${f(x)},${f(top + r)} Q${f(x)},${f(top)} ${f(x + r)},${f(top)} L${f(x + r)},${f(top + 10)} Q${f(x + w * .18)},${f(top + 14)} ${f(x + w * .2)},${f(top + r)} L${f(x + w * .2)},${yb}Z`, '#a57cf0', tg);
          el('rect', { x: f(x + w * .74), y: f(top + r * .7), width: f(w * .26), height: f(yb - top - r * .7), rx: f(w * .1), fill: '#5c38a8' }, tg);
          YE(f(x + w * .45), f(top + 6), f(w * .3), 6, '#c4a2fa', tg, { opacity: .8 });
          x += w - 2; }
        el('rect', { x: X0 + b - 90, y: ya + 40, width: 90, height: yb - ya - 40, fill: '#4c2c94', opacity: .55 }, tg);   // the shaded side of the tier
        // jungle overhanging the tier's top, vines hanging down its face
        for (let x = X0 + a + 10; x < X0 + b; x += 34 + R() * 26) clump(tg, x, ya + 6 + R() * 10, 16 + R() * 10, 3, ['#1f6f5a', '#35a06e', '#8ad89a']);
        for (let k = 0; k < 5; k++) { const vx = X0 + a + 30 + R() * (b - a - 60), vl = 30 + R() * 70; YS(`M${f(vx)},${ya + 14} q${f((R() - .5) * 16)},${f(vl * .5)} 0,${f(vl)}`, '#2a8a5a', 4, tg, { 'stroke-linecap': 'round' }); }
        if (i === 0) for (let k = 0; k < 3; k++) palm(tg, X0 + 40 + k * 150 + R() * 40, ya + 8, 90 + R() * 40);
        // the waterfall over this tier's front edge: wide, a curved lip, stripes in white, ice blue and a violet sheen
        const wx = X0 + [230, 360, 500][i], ww = [92, 112, 140][i], wb = i < 2 ? tiers[i + 1][2] + 10 : yb + 10;
        const fg_ = el('g', {}, tg);
        el('rect', { x: wx, y: ya - 6, width: ww, height: wb - ya + 6, fill: '#bfeeff' }, fg_);
        for (let x = wx; x < wx + ww - 4;) { const sw = 6 + R() * 14, c = ['#ffffff', '#ffffff', '#86d8ff', '#b4a8f4', '#e2f8ff'][Math.floor(R() * 5)];
          el('rect', { x: f(x), y: ya, width: f(Math.min(sw, wx + ww - x)), height: wb - ya, fill: c }, fg_); x += sw + 2 + R() * 6; }
        el('rect', { x: wx + ww - 12, y: ya, width: 12, height: wb - ya, fill: '#5ab8f0' }, fg_);
        YP(`M${wx - 6},${ya + 4} Q${wx + ww / 2},${ya - 22} ${wx + ww + 6},${ya + 4} L${wx + ww + 6},${ya + 14} Q${wx + ww / 2},${ya - 4} ${wx - 6},${ya + 14}Z`, '#ffffff', fg_);
        foam.push([wx + ww / 2, wb, ww, i]); });
      // the lake at the cliff's foot, and the river out of it toward the camera
      const lk = [X0 + 690, 690];
      const P = [[X0 + 780, 692], [X0 + 1500, 470], [X0 + 2100, 620], [X0 + 2900, 1080]];   // the end runs under the near bank
      const at = t => { const u = 1 - t; return [0, 1].map(j => u * u * u * P[0][j] + 3 * u * u * t * P[1][j] + 3 * u * t * t * P[2][j] + t * t * t * P[3][j]); };
      const wid = t => (20 + (at(t)[1] - 424) * .95) * Math.min(1, .3 + t * 3);   // a narrow outlet, then as wide as its depth
      const band = (pad, k = 1, dy2 = 0) => { const pts = s => Array.from({ length: 49 }, (_, i) => { const t = i / 48, [x, y] = at(t); return [x, y + dy2 + s * (k * wid(t) * .5 + pad * (.25 + t))]; });
        return 'M' + pts(-1).concat(pts(1).reverse()).map(([x, y]) => `${f(x)},${f(y)}`).join(' L') + 'Z'; };
      const wet = Y_lgrad([[0, '#8adcff'], [.45, '#46b4f4'], [1, '#2378d8']], { user: true, x1: 0, y1: 440, x2: 0, y2: 1000 });
      YP(band(20), '#e0a050', g); YP(band(13), '#ffcf6a', g); YP(band(6), '#7fe0f0', g); YP(band(0), wet, g, { opacity: .92 });
      YE(lk[0], lk[1] + 10, 330, 62, '#e0a050', g); YE(lk[0], lk[1] + 4, 318, 54, '#ffcf6a', g); YE(lk[0], lk[1], 300, 46, '#7fe0f0', g); YE(lk[0] + 8, lk[1] + 4, 276, 36, wet, g, { opacity: .92 });
      water.push(band(0), `M${lk[0] - 268},${lk[1] + 4} A276,36 0 1 1 ${lk[0] + 284},${lk[1] + 4} A276,36 0 1 1 ${lk[0] - 268},${lk[1] + 4}Z`);
      const rip = el('g', {}, g);
      for (let k = 0, n = 0; k < 900 && n < 150; k++) { const t = R(), [x, y] = at(t), w = wid(t); if (R() > (y - 424) / 520) continue; n++;   // denser toward the camera
        const ox = (R() - .5) * w * 1.1, oy = (R() - .5) * w * .7, l = 8 + (y - 424) * .16 * (.6 + R()), dark = R() < .5;
        YS(`M${f(x + ox)},${f(y + oy)} q${f(l / 2)},${f(-2 - l * .06)} ${f(l)},0`, dark ? '#1f6ed0' : '#c4f2ff', f(dark ? 2 + w * .012 : 1.6 + w * .01), rip, { 'stroke-linecap': 'round', opacity: dark ? .7 : .85 }); }
      for (let k = 0; k < 14; k++) { const x = lk[0] - 240 + R() * 480, y = lk[1] - 24 + R() * 50, l = 14 + R() * 26, dark = k % 2;
        YS(`M${f(x)},${f(y)} q${f(l / 2)},-3 ${f(l)},0`, dark ? '#1f6ed0' : '#c4f2ff', dark ? 2.5 : 2, rip, { 'stroke-linecap': 'round', opacity: dark ? .7 : .85 }); }
      // rocks standing in the river, with foam where they meet the water; lily pads and leaves floating
      [.34, .58, .74, .86].forEach((t, k) => { const [x, y] = at(t), w = wid(t), s = .4 + (y - 424) / 360, rx = x + (k % 2 ? .22 : -.26) * w, ry = y + (k % 2 ? -.1 : .14) * w;
        const rg = el('g', { transform: `translate(${f(rx)},${f(ry)}) scale(${s.toFixed(2)})` }, g);
        YP('M-40,0 L-30,-30 L-4,-44 L26,-34 L40,0Z', '#6a46b8', rg); YP('M-40,0 L-30,-30 L-4,-44 L-6,-20 L-18,0Z', '#9a7ae0', rg); YP('M26,-34 L40,0 L18,0 L12,-20Z', '#4a2c8e', rg);
        YS('M-52,2 Q-40,-6 -26,2 Q-12,-6 2,2 Q16,-6 30,2 Q42,-6 54,2', '#eefaff', 7, rg, { 'stroke-linecap': 'round', opacity: .9 }); YE(0, 6, 60, 7, '#d8f6ff', rg, { opacity: .6 }); });
      for (let k = 0; k < 16; k++) { const t = .2 + R() * .75, [x, y] = at(t), w = wid(t), sd = R() < .5 ? -1 : 1, px = x + (R() - .5) * w * .5, py = y + sd * w * (.28 + R() * .14), s = .35 + (y - 424) / 400;
        const pg = el('g', { transform: `translate(${f(px)},${f(py)}) scale(${s.toFixed(2)})` }, g);
        if (k % 4 === 3) { YP('M-22,0 Q0,-10 24,-2 Q4,6 -22,0Z', '#e8a03a', pg, { transform: `rotate(${f(R() * 360)})` }); }   // a fallen leaf
        else { YP('M0,0 L20,-5 A21,12 0 1 1 18,4Z', '#3fae6a', pg); YP('M0,0 L20,-5 A21,12 0 0 0 -20,-4Z', '#6cd08a', pg, { opacity: .8 });
          if (k % 5 === 0) { YC(-4, -6, 6, '#ff8ab8', pg); YC(-4, -7, 3, '#fff2a0', pg); } } }
      foam.forEach(([x, y, ww, i]) => { YE(f(x), f(y + 4), f(ww * .9), 14 + i * 4, '#e8fbff', g, { opacity: .85 });
        for (let k = 0; k < 7; k++) YC(f(x - ww * .65 + k * ww * 1.3 / 6 + (R() - .5) * 8), f(y - (k % 2) * 8 - R() * 6), f(14 + i * 4 + R() * 8), '#ffffff', g);
        for (let k = 0; k < 5; k++) YC(f(x + (R() - .5) * ww * 1.4), f(y - 26 - R() * 22), f(3 + R() * 4), '#ffffff', g, { opacity: .8 }); });
      // bushes and palms on the river banks
      for (let i = 4; i < 40; i += 5) { const t = i / 48, [x, y] = at(t), w = wid(t), sd = R() < .5 ? -1 : 1, by = y + sd * (w / 2 + 26 + R() * 16);
        if (by > 744) continue; if (R() < .4) palm(g, f(x + (R() - .5) * 60), f(by), 50 + (by - 424) * .5); else clump(g, x + (R() - .5) * 60, by, 12 + (by - 424) * .07, 4, ['#1f7a5a', '#3fae6a', '#a6e676']); }
      avoid.push((x, y) => x > X0 - 80 && x < X0 + 980 && y > 150 && y < 740);
      for (let i = 0; i <= 48; i++) { const t = i / 48, [px, py] = at(t), w = wid(t); avoid.push((x, y) => Math.abs(x - px) < w * .6 + 60 && y > py - w * .5 - 30 && y < py + w * .5 + 40); } });
    if (water.length) { const cp = el('clipPath', { id: 'mesoWater', clipPathUnits: 'userSpaceOnUse' }, Y.defs); water.forEach(dd => YP(dd, '#fff', cp));
      const refl = el('g', { 'clip-path': 'url(#mesoWater)' }, mid), col = el('g', {}, refl);
      for (let y = 440; y < 1060; y += 8 + R() * 8) { const k = (y - 424) / 600, w = 50 + 260 * k;
        el('rect', { x: f(-w / 2 + (R() - .5) * 30), y: f(y), width: f(w), height: f(5 + 6 * k), rx: 3, fill: '#fff6d8', opacity: f(.22 * (1 - k * .5)) }, col);
        if (R() < .8) el('rect', { x: f(-w * .2 + (R() - .5) * w * .3), y: f(y + 3), width: f(w * (.15 + R() * .25)), height: f(3 + 3 * k), rx: 2, fill: '#ffffff', opacity: f(.85 - k * .4) }, col); }
      const ssx = su[0], q = (k, cam) => layT(k, cam);
      W.onCam = cam => { const s_ = q(LK.sky, cam), m_ = q(LK.mid, cam), sx = 960 + (ssx - s_.ex) * s_.ez; set(col, { transform: `translate(${f(m_.ex + (sx - 960) / m_.ez)},0)` }); }; }
    const gr = [];
    for (let i = 0; i < (m1 - m0) / 75; i++) { const x = m0 + R() * (m1 - m0), y = 448 + Math.pow(R(), 1.2) * 290;
      if (!avoid.some(q => q(x, y))) gr.push([x, y, R()]); }
    gr.sort((a, b) => a[1] - b[1]).forEach(([x, y, k]) => { const r = 9 + (y - 424) * .16;
      if (k < .3) palm(mid, x, y, 36 + (y - 424) * .55);
      else { YE(f(x), f(y + 2), f(r * 2.2), f(r * .3), '#2f8a4a', mid, { opacity: .45 }); const n = 2 + Math.floor(k * 5);
        for (let j = 0; j < n; j++) YS(`M${f(x + (j - (n - 1) / 2) * r * .45)},${f(y)} l0,${f(-r * 1.2)}`, '#145a48', f(Math.max(2, r * .18)), mid);
        clump(mid, x, y - r * 1.1, r, n, k < .65 ? ['#1f7a5a', '#3fae6a', '#a6e676'] : ['#2a8a6a', '#5cc07e', '#c4f09a']); } });
    for (let x = m0 + 200; x < m1; x += 900 + R() * 700) { if (avoid.some(q => q(x, 470))) continue;
      for (let k = 0; k < 4; k++) { const hx = x + k * 30 + R() * 10, hy = 470 + R() * 8; YE(f(hx), f(hy), 11, 6, '#c0508a', mid); YC(f(hx + 10), f(hy - 5), 4.5, '#c0508a', mid); YS(`M${f(hx - 9)},${f(hy)} l-8,-3`, '#c0508a', 3, mid); } }
    // ---------------- mid2: the near bank, with gaps behind the actors
    const bank = el('g', { transform: `translate(0,${d})` }, W.mid2); W.mid2.insertBefore(bank, W.mid2A);
    const gaps = (o.stages || []).map(([x, w]) => { const c = 960 + (x - 960) * LK.mid2; return [c - w * .45, c + w * .45]; });
    YP(`M${x0},724 ${wav(724, 10, 4)} L${x1},1500 L${x0},1500Z`, '#2f9a4e', bank);
    YP(`M${x0},718 ${wav(718, 10, 4)} L${x1},732 L${x0},732Z`, '#46b85a', bank);
    { const [a, b] = span('mid2'); for (let x = a; x < b; x += 120 + R() * 170) { if (gaps.some(([p, q]) => x > p - 120 && x < q + 120)) continue; const y = 752 + R() * 60, k = R();
      if (k < .32) { const g = el('g', { transform: `translate(${f(x)},${f(y)}) scale(${(.75 + R() * .5).toFixed(2)})` }, bank);
        YP('M-118,4 C-118,-24 118,-24 124,4Z', '#1c6640', g);
        [[-60, -40, 64], [12, -66, 80], [72, -34, 58]].forEach(([dx, dy2, r]) => { YC(dx, dy2, r, '#2e8650', g); YC(f(dx - r * .24), f(dy2 - r * .28), f(r * .6), '#4caa5c', g); YC(f(dx - r * .36), f(dy2 - r * .42), f(r * .26), '#a6e676', g); }); }
      else if (k < .55) tropic(bank, x, y + 4, .9 + R() * .5);
      else if (k < .72) { const g = el('g', { transform: `translate(${f(x)},${f(y)}) scale(${(.9 + R() * .4).toFixed(2)})` }, bank); const j = () => (R() - .5) * 14;
        YE(6, 2, 80, 12, '#1c6640', g, { opacity: .6 });
        YP(`M-74,2 L${f(-62 + j())},${f(-44 + j())} L${f(-22 + j())},-74 L${f(32 + j())},${f(-66 + j())} L${f(70 + j())},${f(-30 + j())} L78,2Z`, '#6a46b8', g);
        YP('M-74,2 L-62,-44 L-22,-74 L-8,-40 L-30,2Z', '#9a7ae0', g); YP('M32,-66 L70,-30 L78,2 L36,2 L22,-30Z', '#4a2c8e', g); }
      else if (k < .82) palm(bank, x, y + 4, 200 + R() * 80);
      else fernPlant(bank, f(x), f(y + 6), (1 + R() * .4).toFixed(2), 3000 + Math.round(x) % 997, W, ['fernD', 'fern', 'fernL'], 8);
      if (R() < .35) { const c = ['#ff6fa8', '#ffd23a', '#ff8a4a'][Math.floor(R() * 3)]; for (let q = 0; q < 3; q++) { const fx = x + 60 + q * 22, fy = y + 8 - (q % 2) * 10;
        YS(`M${f(fx)},${f(fy)} l0,-16`, '#1c6640', 3, bank); for (let p = 0; p < 5; p++) YC(f(fx + Math.cos(p * 1.257) * 6), f(fy - 18 + Math.sin(p * 1.257) * 6), 5, c, bank); YC(f(fx), f(fy - 18), 3, '#fff2a0', bank); } } } }
    // ---------------- main: a sand stage under each actor set
    const veil = el('rect', { x: x0, y: gy - 4, width: x1 - x0, height: 1700, fill: '#14603a', opacity: .42 }); W.main.insertBefore(veil, W.fogB);
    const main = el('g', {}, W.main); W.main.insertBefore(main, W.mainA);
    (o.stages || []).forEach(([x, w]) => { YE(x, gy + 74, w * .54, 78, '#e0a050', main); YE(x, gy + 64, w * .52, 68, '#ffcf6a', main); YE(x - w * .06, gy + 48, w * .4, 34, '#ffe7a8', main); });
    // ---------------- fg: crisp broad leaves lower left, a warm bank lower right (W.cam drifts them with the camera)
    if (W.fg) { const Lg = el('g', {}, W.fg); [[-62, 460, 96], [-28, 400, 84], [-96, 360, 76]].forEach(([a, l, w]) => bleaf(Lg, a, l, w, '#0f5a4a', '#2f8a5a', '#083c34'));
      const Rg = el('g', {}, W.fg); YE(150, 60, 520, 170, '#b85a2a', Rg); YE(130, 40, 500, 150, '#e07a3a', Rg); YE(60, 8, 360, 70, '#ff9a4a', Rg); bleaf(Rg, -152, 360, 74, '#0f5a4a', '#2f8a5a', '#083c34');
      W.fgF.push({ g: Lg, x: -40, y: 1120, s: 1, fr: [] }, { g: Rg, x: 1880, y: 1070, s: 1, fr: [] }); }
  }
  window.Meso = { PAL, world, frond, fernPlant, araucaria, cycad, treeFern, bush, softDot, rekey, layT, terrain };
})();
