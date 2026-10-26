// The shared cast, rigged and painted per look (LIBRARY.md "Shared cast identity"). Load after cast.js and motion.js.
// The old kit mascot(), planet(..., 'earth') and sun() stay as they are for finished episodes; new pages use these.
//   jook(parent, {paint, arms, helmet}) -> {root, back, front, handL, handR, update(t, st)}
//     st: kit mascot() fields (in, look, blink, hop, bubble, mouth, wide, sleep) plus x, y, s, rot,
//         armL/armR [deg, reach] (0 = straight out sideways, positive = up), squash (-1..1)
//   earth(parent, r, {paint, light, seed}) -> {g, state({x, y, s, o, spin})}
//   castSun(parent, r, {paint}) -> {g, state({x, y, s, o, t})}   (its own name: library.js sun() stays for stage() pages)
// paint: 'A' gradients + rim (finForm) · 'B' three tones in the body's own hue, no blur · 'C' 6 px ink outlines and an
// offset sticker shadow · 'D' the B paint (paper is for the episode's own props). Defaults to Y.look.style.
// จุก's face never changes between paints: white eyes, #14103a pupils, two highlight dots each, opaque #ff8aa6 cheeks.
const CAST_ID = {
  jook: { body: '#3dd6c0', dark: '#1f9e90', belly: '#25b3a3', leaves: ['#8be05a', '#a8f070', '#4a9e3c'], stem: '#4cb848',
    eye: '#ffffff', pupil: '#14103a', cheek: '#ff8aa6', mouth: '#14103a', arm: '#3dd6c0' },
  earth: { ocean: ['#5fd0ff', '#1f62c9'], land: '#5be08a', desert: '#f5c75f', ice: '#f1f8ff', cloud: '#ffffff', night: '#0b2150' },
  sun: { core: '#fff3b0', mid: '#ffd23f', edge: '#ff8a3d' },
  ink: '#3a2230', sticker: '#1c1236',
};
const RIG_GLOW_DISC = typeof litDisc === 'function' ? litDisc : null;   // glow's litDisc, before flat.js may replace it
const rigPaint = paint => { const s = paint || (Y.look && Y.look.style) || 'A'; return s === 'D' ? 'B' : s; };

// one shape in a paint; returns the group the shape lives in
function rigShape(parent, d, fill, paint, { lw = 6, part = null } = {}) {
  const g = el('g', part ? { 'data-part': part } : {}, parent);
  if (paint === 'B') {   // flat.js math: light band upper-left, dark crescent lower-right, both in the fill's hue
    const t = FL_tone(fill), a = [4.2, 3.5], b = [10.8, 9];
    YP(d, t.light, g);
    const c2 = Y_clipTo(el('g', { transform: `translate(${a[0]},${a[1]})` }, Y_clipTo(g, d)), d);
    YP(d, t.dark, c2);
    YP(d, fill, el('g', { transform: `translate(${-b[0]},${-b[1]})` }, c2));
  } else if (paint === 'C') {
    YP(d, CAST_ID.sticker, g, { opacity: .45, transform: 'translate(8,8)' });
    YP(d, fill, g, { stroke: CAST_ID.ink, 'stroke-width': lw, 'stroke-linejoin': 'round' });
  } else YP(d, fill, g);
  return g;
}
const rigRR = (x, y, w, h, r) => `M${x + r},${y}H${x + w - r}A${r},${r} 0 0 1 ${x + w},${y + r}V${y + h - r}A${r},${r} 0 0 1 ${x + w - r},${y + h}H${x + r}A${r},${r} 0 0 1 ${x},${y + h - r}V${y + r}A${r},${r} 0 0 1 ${x + r},${y}Z`;
const rigCirc = (cx, cy, r) => `M${cx - r},${cy}A${r},${r} 0 1 0 ${cx + r},${cy}A${r},${r} 0 1 0 ${cx - r},${cy}Z`;
const rigEll = (cx, cy, rx, ry) => `M${cx - rx},${cy}A${rx},${ry} 0 1 0 ${cx + rx},${cy}A${rx},${ry} 0 1 0 ${cx - rx},${cy}Z`;

// ---------------------------------------------------------------- จุก (geometry from the channel avatar)
const JK_BODY = 'M-48,-46 C-48,-82 -26,-96 0,-96 C26,-96 48,-82 48,-46 C48,-14 28,-4 0,-4 C-28,-4 -48,-14 -48,-46Z';
const JK_BELLY = 'M-48,-46 C-48,-14 -28,-4 0,-4 C28,-4 48,-14 48,-46 C40,-24 20,-16 0,-16 C-20,-16 -40,-24 -48,-46Z';
const JK_LEAF = ['M2,-26 C-14,-44 -36,-34 -34,-22 C-22,-16 -8,-18 2,-26Z', 'M2,-28 C14,-48 36,-42 36,-30 C24,-22 10,-22 2,-28Z'];

function jook(parent, { paint, arms = false, helmet = false, seed = 5 } = {}) {
  const P = rigPaint(paint), J = CAST_ID.jook, ink = P === 'C';
  const root = el('g', {}, parent), g = el('g', {}, root);
  el('ellipse', { cx: 0, cy: 2, rx: 40, ry: 8, fill: '#000', opacity: P === 'C' ? 0 : .22 }, g);
  const back = el('g', {}, g);
  const arm = side => { const a = el('g', {}, back), limb = el('g', {}, a);
    rigShape(limb, rigRR(-8, -8, 46, 16, 8), J.arm, P, { lw: 4 });
    const hand = el('g', { transform: 'translate(44,0)' }, limb); rigShape(hand, rigCirc(0, 0, 11), J.body, P, { lw: 4 });
    return { a, limb, hand, side }; };
  const armsL = arms ? arm(-1) : null, armsR = arms ? arm(1) : null;
  const bodyG = el('g', { 'data-part': 'bodyG' }, g);
  rigShape(bodyG, 'M-28,-8 a13,8 0 1 0 26,0 a13,8 0 1 0 -26,0Z', J.dark, P, { lw: 4 });
  rigShape(bodyG, 'M4,-8 a13,8 0 1 0 26,0 a13,8 0 1 0 -26,0Z', J.dark, P, { lw: 4 });
  const bodyShape = rigShape(bodyG, JK_BODY, J.body, P);
  if (P !== 'B') YP(JK_BELLY, J.belly, bodyG, { opacity: .9 });
  if (P === 'A') litPass(bodyShape);
  const anchor = el('g', { 'data-part': 'sproutAnchor', transform: 'translate(0,-92)' }, bodyG);
  const face = el('g', {}, bodyG);
  for (const cx of [-30, 30]) el('ellipse', { 'data-part': 'cheek', cx, cy: -35, rx: 8.5, ry: 5, fill: J.cheek, opacity: 1 }, face);
  const eyes = [-17, 17].map(ex => ({ ex,
    w: el('ellipse', { 'data-part': 'eyeWhite', cx: ex, cy: -53, rx: 14.3, ry: 15.4, fill: J.eye, stroke: ink ? CAST_ID.ink : 'none', 'stroke-width': 3 }, face),
    p: el('ellipse', { 'data-part': 'pupil', cx: ex, cy: -53, rx: 8.1, ry: 8.8, fill: J.pupil }, face),
    h1: el('circle', { 'data-part': 'hl', r: 3.1, fill: '#ffffff' }, face),
    h2: el('circle', { 'data-part': 'hl', r: 1.2, fill: '#ffffff', opacity: .8 }, face) }));
  const mouth = YP('M-7,-30 Q0,-24 7,-30', 'none', face, { stroke: J.mouth, 'stroke-width': 3.5, 'stroke-linecap': 'round' });
  const sprout = el('g', { 'data-part': 'sprout' }, g);
  YS('M0,4 C-2,-10 4,-18 2,-30', ink ? CAST_ID.ink : J.stem, ink ? 7 : 6, sprout);
  rigShape(sprout, JK_LEAF[0], J.leaves[0], P, { lw: 4 }); rigShape(sprout, JK_LEAF[1], J.leaves[1], P, { lw: 4 });
  const front = el('g', {}, g);
  if (helmet) { el('circle', { cx: 0, cy: -52, r: 66, fill: '#bfe6ff', opacity: .16, stroke: ink ? CAST_ID.ink : 'none', 'stroke-width': 5 }, front);
    YP('M-50,-60 A50,50 0 0 1 -14,-104 L-6,-92 A38,38 0 0 0 -36,-58Z', '#ffffff', front, { opacity: .55 }); }
  const bub = el('g', {}, root);
  el('circle', { cx: -18, cy: 36, r: 7, fill: C.white }, bub); el('circle', { r: 40, fill: C.white, stroke: ink ? CAST_ID.ink : 'none', 'stroke-width': 5 }, bub);
  const bt = el('text', { y: 21, 'text-anchor': 'middle', 'font-size': 60, 'font-weight': 900, fill: C.ink }, bub, '?');

  // body motion at time t: vertical offset and scale about the feet
  const bodyAt = (t, st) => {
    let hop = 0; for (const h of st.hop || []) hop = Math.max(hop, 40 * Math.sin(Math.PI * p(t, h, h + .45)));
    const ein = st.in == null ? 1 : pop(t, st.in, .55), breath = .03 * Math.sin(t * 6.8);
    const [sqx, sqy] = squash(.12 * (st.squash || 0));
    return { ty: -hop - 3 * Math.sin(t * 3.4) * (st.sleep ? .3 : 1), sx: (.4 + .6 * ein) * sqx, sy: (.4 + .6 * ein) * (1 + breath) * sqy, ein };
  };
  return {
    root, back, front, handL: armsL && armsL.hand, handR: armsR && armsR.hand,
    update(t, st = {}) {
      const b = bodyAt(t, st), lag = bodyAt(t - .07, st);
      set(root, { transform: `translate(${st.x ?? 0},${st.y ?? 0}) rotate(${st.rot || 0}) scale(${st.s ?? 1})` });
      set(bodyG, { transform: `translate(0,${b.ty.toFixed(2)}) scale(${b.sx.toFixed(4)},${b.sy.toFixed(4)})` });
      set(sprout, { transform: `translate(0,${(lag.ty - 92 * lag.sy).toFixed(2)}) scale(${lag.sx.toFixed(4)},${lag.sy.toFixed(4)})` });
      set(back, { transform: `translate(0,${b.ty.toFixed(2)})` }); set(front, { transform: `translate(0,${b.ty.toFixed(2)}) scale(${b.sx.toFixed(4)},${b.sy.toFixed(4)})` });
      show(g, b.ein * 4);
      for (const A of [armsL, armsR]) if (A) {
        const [deg, reach] = (A.side < 0 ? st.armL : st.armR) || [-60, 1];
        set(A.a, { transform: `translate(${A.side * 40},-40) scale(${A.side},1) rotate(${-deg})` });
        set(A.limb, { transform: `scale(${Math.max(.3, reach)},1)` });
      }
      const [lx, ly] = st.look || [0, 0];
      let open = st.sleep ? .1 : st.blink ? 1 : blinkOpen(t, seed);
      for (const bt_ of st.blink || []) if (t > bt_ && t < bt_ + .13) open = .1;
      const wide = st.wide ? 1 + .2 * p(t, st.wide, st.wide + .15) : 1;
      for (const e of eyes) {
        set(e.w, { ry: 15.4 * open * wide, rx: 14.3 * wide });
        const px = e.ex + lx * 5.5, py = -53 + ly * 5.5;
        set(e.p, { cx: px, cy: py, ry: 8.8 * open * wide, rx: 8.1 * wide });
        set(e.h1, { cx: px + 2.6, cy: py - 3.6 }); set(e.h2, { cx: px - 2.4, cy: py + 3 });
        show(e.h1, open > .5 ? 1 : 0); show(e.h2, open > .5 ? .8 : 0);
      }
      const m = st.mouth || 'smile';
      set(mouth, { d: m === 'o' ? 'M-6,-30 Q0,-22 6,-30 Q0,-36 -6,-30Z' : m === 'flat' ? 'M-7,-29 L7,-29' : m === 'big' ? 'M-10,-32 Q0,-18 10,-32Z' : 'M-7,-30 Q0,-24 7,-30',
        fill: m === 'o' || m === 'big' ? J.mouth : 'none' });
      const bb = st.bubble;
      if (bb) {
        bt.textContent = bb.ch; set(bt, { fill: bb.color || C.ink, 'font-size': bb.ch.length > 1 ? 34 : 60, y: bb.ch.length > 1 ? 12 : 21 });
        const k = pop(t, bb.tIn, .4) * (1 - p(t, bb.tOut ?? 1e9, (bb.tOut ?? 1e9) + .3));
        set(bub, { transform: `translate(${bb.dx ?? -70},${(bb.dy ?? -150) + b.ty}) scale(${Math.max(0, k)}) rotate(${4 * Math.sin(t * 5)})` }); show(bub, k * 3);
      } else show(bub, 0);
    },
  };
}

// ---------------------------------------------------------------- Earth
function earth(parent, r, { paint, light = 215, seed = 9 } = {}) {
  const P = rigPaint(paint), E = CAST_ID.earth, R = rng(seed);
  const g = el('g', {}, parent), spin = [];
  const lands = Array.from({ length: 4 }, (_, i) => { const a = R() * 6.28, d = r * (.15 + R() * .45);
    return { d: Y_blob(Math.cos(a) * d, Math.sin(a) * d, r * (.22 + R() * .16), r * (.16 + R() * .12), seed * 10 + i, 9, .3), desert: i === 3 }; });
  const clouds = Array.from({ length: 5 }, () => { const x = (R() - .5) * r * 1.3, y = (R() - .5) * r * 1.3, l = r * (.3 + R() * .3);
    return `M${(x - l / 2).toFixed(1)},${y.toFixed(1)} Q${x.toFixed(1)},${(y - r * .07).toFixed(1)} ${(x + l / 2).toFixed(1)},${y.toFixed(1)}`; });
  const drawSurface = (q, w) => { const s = el('g', {}, q); spin.push(s);
    lands.forEach(L => rigShape(s, L.d, L.desert ? E.desert : E.land, P === 'A' ? 'A' : P, { lw: 4 }));
    clouds.forEach(d => { if (P === 'C') YS(d, CAST_ID.ink, w + 9, s);
      YS(d, E.cloud, w, s, { 'data-part': 'cloud', opacity: P === 'A' ? .8 : 1, 'stroke-linecap': 'round' }); }); };
  const away = (light + 180) * Math.PI / 180;
  if (P === 'A' && RIG_GLOW_DISC) {
    RIG_GLOW_DISC(g, r, { stops: [[0, '#7fe0ff'], [.55, '#2f9fe0'], [1, '#164a9a']], rot: light, atmo: '#9fe8ff', rim: '#bff0ff', hot: '#ffffff', shade: '#061226',
      draw: (q, rr) => drawSurface(el('g', { transform: `rotate(${-light})` }, q), rr * .09) }).state({});
  } else {
    if (P === 'C') YC(0, 0, r, CAST_ID.sticker, g, { opacity: .45, transform: 'translate(9,10)' });
    YC(0, 0, r * 1.07, E.ocean[0], g, { opacity: P === 'B' ? .16 : 0 });
    const body = Y_clipTo(g, rigCirc(0, 0, r));
    YC(0, 0, r, P === 'C' ? E.ocean[0] : Y_lgrad([[0, E.ocean[0]], [1, E.ocean[1]]], { x2: .6, y2: 1 }), body);
    drawSurface(body, r * .09);
    if (P === 'B') YC(Math.cos(away) * r * .62, Math.sin(away) * r * .52, r * 1.12, E.night, body, { 'data-part': 'night', opacity: .55, filter: Y_blurF(4) });
    if (P === 'C') YC(0, 0, r, 'none', g, { stroke: CAST_ID.ink, 'stroke-width': 7 });
  }
  return { g, state({ x = 0, y = 0, s = 1, o = 1, spin: sp = 0 } = {}) {
    set(g, { transform: `translate(${x},${y}) scale(${Math.max(0, s).toFixed(4)})` }); show(g, o);
    spin.forEach(e => set(e, { transform: `rotate(${(+sp).toFixed(2)})` })); } };
}

// ---------------------------------------------------------------- the Sun (no flares or loops on the edge)
function castSun(parent, r, { paint } = {}) {
  const P = rigPaint(paint), S = CAST_ID.sun;
  const g = el('g', {}, parent), halo = el('g', {}, g);
  [1.23, 1.48, 1.76].forEach((k, i) => YC(0, 0, r * k, S.mid, halo, { opacity: [.16, .1, .06][i], filter: P === 'A' ? Y_blurF(8) : null }));
  if (P === 'A') YC(0, 0, r, Y_rgrad([[0, S.core], [.55, S.mid], [1, S.edge]], { cx: '42%', cy: '40%', r: '60%' }), g);
  else {
    if (P === 'C') YC(0, 0, r, CAST_ID.sticker, g, { opacity: .45, transform: 'translate(9,10)' });
    YC(0, 0, r, S.edge, g, P === 'C' ? { stroke: CAST_ID.ink, 'stroke-width': 7 } : {});
    YC(-r * .08, -r * .08, r * .82, S.mid, g); YC(-r * .2, -r * .2, r * .5, S.core, g);
  }
  return { g, state({ x = 0, y = 0, s = 1, o = 1, t = 0 } = {}) {
    set(g, { transform: `translate(${x},${y}) scale(${(Math.max(0, s) * (1 + .01 * Math.sin(t * 1.3))).toFixed(4)})` }); show(g, o);
    show(halo, .85 + .15 * Math.sin(t * .9)); } };
}
