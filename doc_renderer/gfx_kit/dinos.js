// gfx_kit/dinos.js · the channel's own cute flat dinosaur cast (นน 2026-10-26, for every episode that needs animals).
// Style: no outlines; each animal is ONE continuous outline (body, neck and head in a single path, so no seams), short
// rounded stub legs behind the body (the far pair a shade darker), a pale band along the underside computed once over
// the outline, darker spots, a big round eye with a highlight, ridges/frills/horns behind the outline so they peek out.
// The neck bends by weighting the outline's points (w = 0 body ... 1 head) and rotating them about a pivot, so grazing
// and nodding keep the outline whole. Side views facing +x, feet on y = 0. Needs kit.js (el, YP, YC, YE, set, show, lerp,
// eio, Y.defs). No episode code: episodes pick colours and poses.
//   const d = Dino.hadro(parent, { c, crest: 'comb'|'spike'|'flat', crestC })   Dino.cera(parent, { c, kind: 'tri'|'toro' })
//   Dino.sauro(parent, { c })   Dino.rex(parent, { c })   Dino.bird(parent, { c, wing, kind: 'plain'|'tail'|'crest' })   Dino.ptero(parent, { c })
//   Dino.mam(parent, { c, kind: 'plain'|'climb'|'gnaw'|'insect' })   Dino.repeno(parent, { c, stripe })   Dino.psitta(parent, { c, beak, quill })
//   d.update(t, { x, y, s, flip, walk: steps/s (0 = still), head: deg (+ = down), chew: 0..1, jaw: 0..1, look: [dx, dy],
//                 shiver: 0..1, hop: px, squash: 0..1, blink: [t...], shadow: 0..1 })   mammals also take lid (0..1) and ears (0..1)
// Every four-legged or walking animal casts a soft ground shadow. Each returns { g, update, ... }; hadro also gives mouthAt(head) -> [x, y] (local) for breath puffs at the mouth.
(() => {
  const f = v => (+v).toFixed(1);
  let UID = 0;
  const NS = 'http://www.w3.org/2000/svg';
  const use = (id, parent) => { const u = document.createElementNS(NS, 'use'); u.setAttribute('href', '#' + id); parent.appendChild(u); return u; };
  const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const mix = (a, b, k) => '#' + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * k).toString(16).padStart(2, '0')).join('');
  const stroke = (d, c, w, p, o = {}) => el('path', { d, fill: 'none', stroke: c, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', ...o }, p);
  const rot = (x, y, a, px, py) => { const c = Math.cos(a), s = Math.sin(a); return [px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c]; };

  // ---------------------------------------------------------------- one animal: outline, legs, band, spots, details
  // spec.outline = [start, ...segments]; start = [x, y, w]; segment = [[x, y, w], [x, y, w], [x, y, w]] (a cubic)
  function make(parent, c, spec) {
    const A = { c, far: mix(c, '#1a1040', .2), spot: mix(c, '#1a1040', .15), pale: mix(c, '#fff8d0', .5), spec };
    A.root = el('g', {}, parent);
    A.shadow = YE(spec.shadow[0], 0, spec.shadow[1], spec.shadow[1] * .09, '#1a1040', A.root, { opacity: .16 });   // stays on the ground on a hop
    A.inner = el('g', {}, A.root);
    A.back = el('g', {}, A.inner);                         // far legs, ridges, frills, horns: behind the outline
    A.legsG = el('g', {}, A.inner);                        // near legs (behind the outline too)
    A.bodyG = el('g', { fill: c }, A.inner);
    A.id = 'dn' + (++UID); A.body = el('path', { id: A.id }, A.bodyG);
    A.front = el('g', {}, A.inner);                        // parts in front of the body (rex's leg and arm)
    A.ov = el('g', {}, A.inner); A.det = el('g', {}, A.inner);
    A.frontIds = [];
    A.frontFill = el('g', { fill: c }, A.front);
    A.frontPart = d => { const id = 'dn' + (++UID), e = el('path', { d, id }, A.frontFill); A.frontIds.push(id); return e; };
    A.finish = () => {
      const k = ++UID, cid = 'dnc' + k, mid = 'dnm' + k, ids = [A.id, ...A.frontIds], band = spec.band;
      const cp = el('clipPath', { id: cid }, Y.defs); ids.forEach(id => use(id, cp));
      const m = el('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -4000, y: -4000, width: 8000, height: 8000 }, Y.defs);
      el('rect', { x: -4000, y: -4000, width: 8000, height: 8000, fill: '#fff' }, m);
      const g = el('g', { transform: `translate(${-band * .3},${-band})`, fill: '#000' }, m); ids.forEach(id => use(id, g));
      el('rect', { x: -4000, y: -4000, width: 8000, height: 8000, fill: A.pale }, el('g', { 'clip-path': `url(#${cid})`, mask: `url(#${mid})` }, A.ov));
      // rim light: a thin warm band along the top edge (the outline minus itself shifted down), like the sun catching the back
      const rm = 'dnr' + k, m2 = el('mask', { id: rm, maskUnits: 'userSpaceOnUse', x: -4000, y: -4000, width: 8000, height: 8000 }, Y.defs);
      el('rect', { x: -4000, y: -4000, width: 8000, height: 8000, fill: '#fff' }, m2);
      const g2 = el('g', { transform: `translate(${band * .25},${band * .45})`, fill: '#000' }, m2); ids.forEach(id => use(id, g2));
      A.rim = el('rect', { x: -4000, y: -4000, width: 8000, height: 8000, fill: '#fffbe0', opacity: .55 }, el('g', { 'clip-path': `url(#${cid})`, mask: `url(#${rm})` }, A.ov));
      const cb = 'dnb' + k, cpb = el('clipPath', { id: cb }, Y.defs); use(A.id, cpb);
      A.inBody = el('g', { 'clip-path': `url(#${cb})` }, A.det);        // spots etc. (inside the outline only)
      A.clipAll = cid; };
    A.headG = el('g', {}, A.det);                          // eye, nostril: they turn with the head
    A.legs = []; A.ridges = []; A.headBack = [];
    A.outline = a => {                                       // the outline with the neck bent by angle a (radians)
      const [px, py] = spec.pivot, P = ([x, y, w]) => (w ? rot(x, y, a * w, px, py) : [x, y]);
      const o = spec.outline, s = P(o[0]); let d = `M${f(s[0])},${f(s[1])}`;
      for (let i = 1; i < o.length; i++) { const [a1, a2, a3] = o[i].map(P); d += ` C${f(a1[0])},${f(a1[1])} ${f(a2[0])},${f(a2[1])} ${f(a3[0])},${f(a3[1])}`; }
      return d; };
    return A;
  }
  // a stub leg behind the body: a rounded column to the ground (optional forward foot and toes); steps by lifting
  function stub(A, S, near) {
    const e = el('path', { fill: near ? A.c : A.far }, near ? A.legsG : A.back);
    const toes = S.toes ? Array.from({ length: S.toes }, () => YP('', A.pale, near ? A.legsG : A.back)) : [];
    const L = { upd(t, rate) {
      let dx = 0, lift = 0;
      if (rate) { const ph = ((t * rate + S.off) % 1 + 1) % 1; if (ph < .55) dx = lerp(S.step, -S.step, ph / .55); else { const u = (ph - .55) / .45; dx = lerp(-S.step, S.step, eio(u)); lift = S.lift * Math.sin(Math.PI * u); } }
      const x0 = S.x + dx - S.w / 2, x1 = S.x + dx + S.w / 2, b = -lift, r = S.w * .4, ft = S.foot || 0, fh = S.w * .42;
      const fl = S.w * .08, rr = S.w * .42;
      const th = S.w * .22, mid = S.top + (b - S.top) * .45;
      if (!ft) { set(e, { d: `M${f(x0 - th)},${S.top} L${f(x1 + th)},${S.top} C${f(x1 + th)},${f(mid - 10)} ${f(x1)},${f(mid)} ${f(x1)},${f(Math.min(mid + 20, b - rr * 2))} L${f(x1)},${f(b - rr * 2)} C${f(x1)},${f(b - rr * 1.3)} ${f(x1 + fl)},${f(b - rr * 1.2)} ${f(x1 + fl)},${f(b - rr * .8)} Q${f(x1 + fl)},${f(b)} ${f(x1 + fl - rr)},${f(b)} L${f(x0 - fl + rr)},${f(b)} Q${f(x0 - fl)},${f(b)} ${f(x0 - fl)},${f(b - rr * .8)} C${f(x0 - fl)},${f(b - rr * 1.2)} ${f(x0)},${f(b - rr * 1.3)} ${f(x0)},${f(b - rr * 2)} L${f(x0)},${f(Math.min(mid + 20, b - rr * 2))} C${f(x0)},${f(mid)} ${f(x0 - th)},${f(mid - 10)} ${f(x0 - th)},${S.top}Z` }); }
      else set(e, { d: `M${f(x0)},${S.top} L${f(x1)},${S.top} L${f(x1)},${f(b - (ft ? fh : r))}` + (ft ? ` L${f(x1 + ft - fh / 2)},${f(b - fh)} Q${f(x1 + ft)},${f(b - fh)} ${f(x1 + ft)},${f(b - fh / 2)}` : '') +
        ` Q${f(x1 + ft)},${f(b)} ${f(x1 + ft - Math.min(r, fh / 2 || r))},${f(b)} L${f(x0 + r)},${f(b)} Q${f(x0)},${f(b)} ${f(x0)},${f(b - r)}Z` });
      toes.forEach((tl, i) => { const tx = ft ? x1 + ft - S.w * .12 - i * S.w * .24 : x1 + fl - S.w * .2 - i * S.w * .26; set(tl, { d: `M${f(tx - 6)},${f(b)} Q${f(tx)},${f(b - 12)} ${f(tx + 6)},${f(b)}Z` }); });
    } };
    A.legs.push(L); return L;
  }
  // bumps or stripes behind the outline between two fractions of its length, poking out along the outward normal
  function ridge(A, f0, f1, n, size, kind, inside, fill) {
    const els = Array.from({ length: n }, () => YP('', fill || A.spot, A.back));
    A.ridges.push(() => { const L = A.body.getTotalLength();
      els.forEach((e, i) => { const k = f0 + (f1 - f0) * (i + .5) / n, p = A.body.getPointAtLength(L * k), q = A.body.getPointAtLength(L * Math.min(1, k + .003));
        let nx = -(q.y - p.y), ny = q.x - p.x; const m = Math.hypot(nx, ny) || 1; nx /= m; ny /= m;
        if ((p.x - inside[0]) * nx + (p.y - inside[1]) * ny < 0) { nx = -nx; ny = -ny; }
        const tx = -ny, ty = nx, s = size * (kind === 'stripe' ? 1 : 1 - .35 * Math.abs(i - (n - 1) / 2) / ((n - 1) / 2 || 1));
        const bx = p.x - nx * s * .6, by = p.y - ny * s * .6;
        if (kind === 'stripe') { const w = s * .32, h = s * 1.5;
          set(e, { d: `M${f(bx - tx * w)},${f(by - ty * w)} L${f(bx - tx * w + nx * h)},${f(by - ty * w + ny * h)} Q${f(bx + nx * (h + w))},${f(by + ny * (h + w))} ${f(bx + tx * w + nx * h)},${f(by + ty * w + ny * h)} L${f(bx + tx * w)},${f(by + ty * w)}Z` }); }
        else set(e, { d: `M${f(bx - tx * s * .8)},${f(by - ty * s * .8)} C${f(bx - tx * s * .7 + nx * s * 1.7)},${f(by - ty * s * .7 + ny * s * 1.7)} ${f(bx + tx * s * .7 + nx * s * 1.7)},${f(by + ty * s * .7 + ny * s * 1.7)} ${f(bx + tx * s * .8)},${f(by + ty * s * .8)}Z` }); }); });
  }
  function eye(p, x, y, r) {
    const g = el('g', {}, p);
    YC(x, y, r, '#ffffff', g); const ir = el('g', {}, g); YC(x + r * .16, y + r * .04, r * .6, '#1a1424', ir); YC(x + r * .36, y - r * .18, r * .22, '#ffffff', ir);
    const lid = YC(x, y, r * 1.04, '#000', g, { opacity: 0 });
    return { g, ir, lid, r };
  }
  const blinkK = (t, bl = []) => { for (const b of bl) if (t > b && t < b + .14) return 1; return 0; };
  function driver(A, o, P) {
    return (t, st = {}) => {
      const { x = 0, y = 0, s = 1, flip = 1, walk = 0, head = 0, shiver = 0, hop = 0, squash = 0 } = st;
      const sh = shiver * 3 * Math.sin(t * 60);
      set(A.root, { transform: `translate(${f(x + sh)},${f(y - hop)}) scale(${(s * flip).toFixed(4)},${s.toFixed(4)}) scale(${(1 + .1 * squash).toFixed(3)},${(1 - .12 * squash).toFixed(3)})` });
      const hk = 1 / (1 + hop / 300); set(A.shadow, { transform: `translate(0,${f(hop / (s || 1))}) scale(${hk.toFixed(3)},1)`, opacity: (.16 * hk * (st.shadow ?? 1)).toFixed(3) });   // shadow: 0 off the ground
      const bob = walk ? P.bob * Math.abs(Math.sin(t * walk * Math.PI * 2)) : 0;
      set(A.inner, { transform: `translate(0,${f(-bob + P.breath * Math.sin(t * 2.4))})` });
      A.legs.forEach(L => L.upd(t, walk));
      const hd = head + (walk ? P.nod * Math.sin(t * walk * Math.PI * 4) : 0) + 1.2 * Math.sin(t * 1.3) + (st.chew || 0) * 2.5 * Math.sin(t * 9);
      const a = hd * Math.PI / 180;
      set(A.body, { d: A.outline(a) });
      const tr = `rotate(${f(hd)} ${A.spec.pivot[0]} ${A.spec.pivot[1]})`;
      set(A.headG, { transform: tr }); A.headBack.forEach(e => set(e, { transform: tr }));
      A.ridges.forEach(r => r());
      if (o.eye) { const lk = st.look || [0, 0]; set(o.eye.ir, { transform: `translate(${f(lk[0] * o.eye.r * .25)},${f(lk[1] * o.eye.r * .25)})` });
        set(o.eye.lid, { fill: A.c }); show(o.eye.lid, blinkK(t, st.blink)); }
      if (o.extra) o.extra(t, st, a);
    };
  }
  const spots = (p, list, c) => list.forEach(([x, y, r]) => YC(x, y, r, c, p));

  window.Dino = {
    // ------------------------------------------------------------ duckbill: hump over the hips, a thick raised neck, a broad
    // rounded duck snout, a fleshy comb on the head, stripes down the back of the neck
    hadro(parent, { c = '#3fbf8f', crest = 'comb', crestC = null } = {}) {
      const spec = { band: 16, shadow: [0, 400], pivot: [200, -200], outline: [[-440, -150, 0],
        [[-360, -176, 0], [-250, -300, 0], [-130, -322, 0]], [[-20, -340, 0], [80, -300, 0], [130, -262, 0]],
        [[160, -250, .2], [176, -276, .5], [194, -300, .8]], [[210, -340, 1], [256, -362, 1], [306, -358, 1]],
        [[370, -354, 1], [420, -336, 1], [444, -308, 1]], [[466, -282, 1], [462, -246, 1], [430, -240, 1]],
        [[390, -234, 1], [340, -244, 1], [306, -246, 1]], [[278, -244, .9], [264, -226, .7], [262, -200, .5]],
        [[260, -166, .2], [244, -124, 0], [200, -108, 0]], [[156, -92, 0], [60, -88, 0], [-40, -92, 0]],
        [[-150, -96, 0], [-260, -116, 0], [-350, -138, 0]], [[-390, -144, 0], [-420, -148, 0], [-440, -150, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root };
      // big hind legs under the hips, slim front legs: a duckbill, not a sauropod
      stub(A, { x: -60, top: -200, w: 100, step: 24, lift: 20, off: .5, toes: 3 }, false); stub(A, { x: 186, top: -170, w: 44, step: 18, lift: 14, off: 0, toes: 3 }, false);
      stub(A, { x: -140, top: -200, w: 106, step: 24, lift: 20, off: 0, toes: 3 }, true); stub(A, { x: 150, top: -170, w: 48, step: 18, lift: 14, off: .5, toes: 3 }, true);
      if (crest === 'comb') { const cm = YP('M236,-346 C236,-400 300,-416 330,-366 C300,-364 266,-358 236,-346Z', crestC || '#ff7a8a', A.back); A.headBack.push(cm); }
      if (crest === 'spike') { const cm = YP('M262,-358 C232,-388 204,-408 172,-420 C184,-394 222,-362 304,-364Z', crestC || '#ffd23a', A.back); A.headBack.push(cm); }
      ridge(A, .14, .31, 11, 15, 'bump', [0, -200]);
      A.finish();
      spots(A.inBody, [[-280, -150, 16], [-210, -190, 24], [-120, -236, 12], [-60, -186, 20], [20, -230, 14], [70, -150, 10], [-340, -152, 8]], A.spot);
      const hs = el('g', {}, A.headG); spots(hs, [[232, -270, 12], [220, -232, 8], [262, -306, 8]], A.spot);
      YE(440, -300, 7, 4, A.spot, A.headG);
      o.eye = eye(A.headG, 318, -318, 28);
      o.mouthAt = hd => rot(462, -256, hd * Math.PI / 180, 200, -200);
      o.update = driver(A, o, { bob: 6, breath: 2, nod: 2 });
      return o;
    },
    // ------------------------------------------------------------ sauropod: one outline from tail tip to snout, the long neck
    // bends as part of it (no seam at the shoulder), a small round head, pillar legs, the hind pair bigger
    sauro(parent, { c = '#8a7ad8' } = {}) {
      const spec = { band: 18, shadow: [-20, 430], pivot: [200, -280], outline: [[-560, -120, 0],
        [[-440, -170, 0], [-300, -300, 0], [-140, -330, 0]], [[0, -350, 0], [110, -330, 0], [170, -300, 0]],
        [[230, -330, .3], [300, -450, .7], [360, -560, .95]], [[390, -610, 1], [430, -640, 1], [470, -636, 1]],
        [[510, -632, 1], [532, -610, 1], [528, -588, 1]], [[524, -568, 1], [496, -562, 1], [470, -566, 1]],
        [[440, -570, 1], [420, -566, .95], [402, -540, .95]], [[350, -440, .7], [296, -310, .3], [264, -232, 0]],
        [[240, -170, 0], [180, -130, 0], [100, -120, 0]], [[-60, -110, 0], [-200, -120, 0], [-320, -130, 0]],
        [[-420, -130, 0], [-500, -120, 0], [-560, -120, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root };
      stub(A, { x: -20, top: -200, w: 90, step: 22, lift: 18, off: .5, toes: 3 }, false); stub(A, { x: 178, top: -140, w: 74, step: 20, lift: 16, off: 0, toes: 3 }, false);   // the far front leg's top stays under the chest, not above the neck's underside
      stub(A, { x: -100, top: -200, w: 98, step: 22, lift: 18, off: 0, toes: 3 }, true); stub(A, { x: 168, top: -190, w: 80, step: 20, lift: 16, off: .5, toes: 3 }, true);
      A.finish();
      spots(A.inBody, [[-320, -170, 16], [-220, -230, 26], [-110, -280, 14], [-40, -210, 22], [60, -280, 14], [120, -190, 12], [-440, -150, 9]], A.spot);
      spots(el('g', {}, A.headG), [[330, -470, 10], [360, -520, 8], [300, -400, 9]], A.spot);
      YE(516, -604, 6, 3.5, A.spot, A.headG);
      o.eye = eye(A.headG, 478, -606, 17);
      o.update = driver(A, o, { bob: 7, breath: 2, nod: 2 });
      return o;
    },
    // ------------------------------------------------------------ horned dinosaur: a high hump, a big round face with the eye
    // low, a darker frill behind, small yellow horns, a rounded snout with a little nose horn
    cera(parent, { c = '#ff8a4a', kind = 'tri', frillC = null } = {}) {
      const big = kind === 'toro' || kind === 'chasmo';
      const spec = { band: 14, shadow: [-30, 360], pivot: [140, -170], outline: [[-410, -78, 0],
        [[-340, -104, 0], [-260, -228, 0], [-130, -250, 0]], [[-30, -266, 0], [60, -236, .1], [102, -204, .5]],
        [[112, -252, 1], [168, -284, 1], [230, -280, 1]], [[292, -276, 1], [334, -238, 1], [342, -190, 1]],
        [[350, -158, 1], [354, -128, 1], [336, -116, 1]], [[310, -102, 1], [242, -102, 1], [200, -110, .8]],
        [[170, -116, .4], [152, -98, 0], [128, -80, 0]], [[84, -62, 0], [-60, -58, 0], [-170, -64, 0]],
        [[-260, -70, 0], [-350, -76, 0], [-410, -78, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root }, fc = frillC || mix(c, '#ff3a7a', .45);
      stub(A, { x: -130, top: -150, w: 64, step: 18, lift: 14, off: .5, toes: 3 }, false); stub(A, { x: 100, top: -150, w: 62, step: 18, lift: 14, off: 0, toes: 3 }, false);
      stub(A, { x: -190, top: -150, w: 68, step: 18, lift: 14, off: 0, toes: 3 }, true); stub(A, { x: 50, top: -150, w: 66, step: 18, lift: 14, off: .5, toes: 3 }, true);
      const fr = YP(big ? 'M30,-190 C20,-320 110,-380 196,-366 C262,-354 290,-306 276,-262 L130,-150Z' : 'M44,-192 C40,-300 112,-350 184,-336 C240,-326 264,-284 254,-250 L130,-152Z', fc, A.back);
      if (big) YE(150, -300, 22, 28, mix(c, '#1a1040', .32), A.back);
      const h1 = YP('M196,-272 L214,-322 L232,-270Z', '#ffd23a', A.back), h2 = YP('M248,-268 L272,-312 L284,-262Z', '#ffd23a', A.back);
      const h3 = YP('M318,-224 L342,-250 L346,-212Z', '#ffd23a', A.back);
      A.headBack.push(fr, h1, h2, h3);
      A.finish();
      spots(A.inBody, [[-280, -130, 14], [-200, -186, 22], [-110, -222, 12], [-60, -170, 18], [20, -214, 10], [-350, -94, 8]], A.spot);
      spots(el('g', {}, A.headG), [[160, -230, 9], [180, -256, 6]], A.spot);
      YE(338, -170, 5, 3, A.spot, A.headG);
      o.eye = eye(A.headG, 250, -186, 29);
      o.update = driver(A, o, { bob: 5, breath: 1.5, nod: 2 });
      return o;
    },
    // ------------------------------------------------------------ tyrannosaur: body and tail held level (the tail balances
    // the head, it never drags), a short S-neck up to a big round-cornered head with a rounded snout, a bent leg with
    // the knee forward and the ankle back (นน 2026-10-26: the upright pose broke the house anatomy rule), tiny two-finger
    // arms, bumps along the neck and back
    rex(parent, { c = '#7a5ad8' } = {}) {
      const spec = { band: 16, shadow: [-40, 330], pivot: [150, -370], outline: [[-620, -300, 0],
        [[-500, -320, 0], [-280, -372, 0], [-130, -384, 0]], [[0, -396, 0], [90, -384, .05], [140, -358, .2]],
        [[168, -372, .45], [188, -410, .8], [218, -440, 1]], [[250, -472, 1], [330, -480, 1], [380, -462, 1]],
        [[420, -448, 1], [432, -414, 1], [428, -390, 1]], [[424, -364, 1], [402, -352, 1], [370, -352, 1]],
        [[322, -352, 1], [274, -354, 1], [248, -342, .9]], [[222, -328, .6], [200, -300, .3], [178, -272, 0]],
        [[152, -240, 0], [92, -224, 0], [20, -226, 0]], [[-80, -228, 0], [-200, -250, 0], [-320, -268, 0]],
        [[-420, -282, 0], [-520, -292, 0], [-620, -300, 0]]] };
      const UP = 40, up = q => [q[0], q[1] - UP, q[2]];                 // the body rides 40 higher than drawn above
      spec.outline = spec.outline.map((seg, i) => i ? seg.map(up) : up(seg));
      const A = make(parent, c, spec), o = { A, g: A.root }, pale = mix(c, '#fff8d0', .5);
      // a bent leg from the hip: thigh down and forward to the knee, shin down and back to the ankle, then the long foot
      // bone down and forward to the toes; the knee stays forward whatever the foot does
      const legD = (H, F) => {
        const An = [F[0] - 62, F[1] - 86], K = [H[0] + 110, H[1] + .6 * (An[1] - H[1])];
        // thigh: an ellipse along hip -> knee, thick at the hip
        const mx = (H[0] + K[0]) / 2, my = (H[1] + K[1]) / 2, a = Math.atan2(K[1] - H[1], K[0] - H[0]), rx = Math.hypot(K[0] - H[0], K[1] - H[1]) / 2 + 56, ry = 74;
        let thigh = ''; for (let k = 0; k < 28; k++) { const u = k / 28 * 6.2832, ex = Math.cos(u) * rx, ey = Math.sin(u) * ry * (Math.cos(u) < 0 ? 1.15 : .8);
          thigh += (k ? 'L' : 'M') + f(mx + ex * Math.cos(a) - ey * Math.sin(a)) + ',' + f(my + ex * Math.sin(a) + ey * Math.cos(a)) + ' '; }
        thigh += 'Z';
        const pts = [K, An, [F[0] + 4, F[1] - 18]], ws = [46, 32, 28], L = [], R = [];
        pts.forEach((q, i) => { const p0 = pts[Math.max(0, i - 1)], p1 = pts[Math.min(pts.length - 1, i + 1)];
          let nx = -(p1[1] - p0[1]), ny = p1[0] - p0[0]; const m = Math.hypot(nx, ny) || 1; nx /= m; ny /= m;
          L.push([q[0] + nx * ws[i], q[1] + ny * ws[i]]); R.push([q[0] - nx * ws[i], q[1] - ny * ws[i]]); });
        const path = ps => ps.map((q, i) => (i ? 'L' : 'M') + f(q[0]) + ',' + f(q[1])).join(' ');
        const shin = path(L) + ' ' + path(R.slice().reverse()).replace('M', 'L') + 'Z';
        const foot = `M${f(F[0] - 34)},${f(F[1] - 30)} L${f(F[0] + 58)},${f(F[1] - 26)} Q${f(F[0] + 82)},${f(F[1] - 24)} ${f(F[0] + 82)},${f(F[1] - 10)} Q${f(F[0] + 82)},${f(F[1])} ${f(F[0] + 66)},${f(F[1])} L${f(F[0] - 40)},${f(F[1])} Q${f(F[0] - 54)},${f(F[1])} ${f(F[0] - 54)},${f(F[1] - 14)} Q${f(F[0] - 54)},${f(F[1] - 30)} ${f(F[0] - 34)},${f(F[1] - 30)}Z`;
        return { thigh, shin, foot };
      };
      const HIP = [-110, -310];
      // far leg and far arm behind the body
      o.farLeg = ['thigh', 'shin', 'foot'].map(() => YP('', A.far, A.back));
      o.farToes = Array.from({ length: 3 }, () => YP('', mix(A.far, '#fff8d0', .4), A.back));
      YP('M162,-308 C180,-298 194,-284 206,-276 L216,-282 L212,-270 L224,-268 L208,-260 C190,-268 172,-282 154,-296Z', A.far, A.back);
      ridge(A, .05, .3, 13, 14, 'bump', [0, -340]);
      // near leg and near arm in front of the body (part of the outline's shading); both arms sit 30 up, rooted in the chest
      // that rides UP higher (they hung below it with a gap: whole-cut round 2)
      o.leg = ['thigh', 'shin', 'foot'].map(() => A.frontPart(''));
      o.arm = A.frontPart('M144,-316 C166,-306 184,-290 196,-278 L208,-284 L204,-270 L218,-268 L200,-258 C180,-266 160,-282 140,-298Z');
      o.toes = Array.from({ length: 3 }, () => YP('', pale, A.front));
      A.finish();
      spots(A.inBody, [[-460, -340, 10], [-360, -360, 14], [-250, -370, 18], [-150, -390, 13], [-60, -370, 22], [20, -390, 12], [70, -340, 10]], A.spot);
      spots(el('g', {}, A.headG), [[256, -476, 11], [232, -440, 8], [290, -498, 7]], A.spot);
      YE(410, -472, 6, 3.5, A.spot, A.headG);
      o.mouth = stroke('', mix(c, '#1a1040', .45), 5, A.headG);
      o.eye = eye(A.headG, 322, -468, 27);
      o.extra = (t, st) => { const rate = st.walk || 0;
        const step = (off) => { let dx = 0, lift = 0;
          if (rate) { const ph = ((t * rate + off) % 1 + 1) % 1; if (ph < .55) dx = lerp(70, -70, ph / .55); else { const u = (ph - .55) / .45; dx = lerp(-70, 70, eio(u)); lift = 40 * Math.sin(Math.PI * u); } }
          return [dx, -lift]; };
        const put = (els, toes, H, off, fx) => { const [dx, ly] = step(off), F = [fx + dx, ly], d = legD(H, F);
          set(els[0], { d: d.thigh }); set(els[1], { d: d.shin }); set(els[2], { d: d.foot });
          toes.forEach((tl, i) => { const tx = F[0] + 74 - i * 22; set(tl, { d: `M${f(tx - 7)},${f(F[1])} Q${f(tx)},${f(F[1] - 14)} ${f(tx + 7)},${f(F[1])}Z` }); }); };
        put(o.farLeg, o.farToes, [HIP[0] + 46, HIP[1] + 4], .5, -10);
        put(o.leg, o.toes, HIP, 0, -60);
        const j = st.jaw || 0; set(o.mouth, { d: `M300,-408 C340,${f(-406 + 14 * j)} 380,${f(-406 + 14 * j)} 418,-412` }); };
      o.update = driver(A, o, { bob: 8, breath: 2, nod: 2 });
      return o;
    },
    bird(parent, { c = '#ffd23a', wing = '#ff8a3a', kind = 'plain' } = {}) {
      const o = { g: el('g', {}, parent) };
      if (kind === 'tail') { stroke('M-24,0 C-50,6 -74,4 -96,14', wing, 6, o.g); stroke('M-24,2 C-50,14 -70,18 -90,30', wing, 6, o.g); }
      if (kind === 'crest') YP('M20,-18 C16,-38 30,-44 40,-36 C34,-30 30,-22 30,-16Z', '#ff5a8a', o.g);
      const w2 = YP('', mix(wing, '#1a1040', .2), o.g); YE(0, 0, 26, 16, c, o.g); YE(2, 7, 20, 7, mix(c, '#fff8d0', .5), o.g); YC(24, -8, 12, c, o.g); YP('M34,-10 L48,-6 L34,-2Z', '#ff7a3a', o.g);
      YC(28, -11, 4.5, '#ffffff', o.g); YC(29, -11, 2.6, '#1a1424', o.g);
      YP('M-24,-2 L-44,-10 L-40,4Z', wing, o.g); const w1 = YP('', wing, o.g);
      o.update = (t, { x = 0, y = 0, s = 1, flip = 1, rate = 3, ph = 0 } = {}) => { const k = Math.sin(t * rate * 6.2832 + ph);
        set(o.g, { transform: `translate(${f(x)},${f(y)}) scale(${(s * flip).toFixed(3)},${s.toFixed(3)})` });
        set(w1, { d: `M-6,-4 C-14,${f(-30 * k - 6)} 6,${f(-44 * k - 4)} 14,${f(-36 * k - 4)} C10,${f(-16 * k)} 6,-4 -6,-4Z` });
        set(w2, { d: `M-10,-4 C-20,${f(-26 * k - 6)} -2,${f(-38 * k - 4)} 6,${f(-30 * k - 4)} C2,${f(-12 * k)} 0,-4 -10,-4Z` }); };
      return o;
    },
    ptero(parent, { c = '#ff6fa0' } = {}) {
      const o = { g: el('g', {}, parent) }, cd = mix(c, '#1a1040', .2);
      const wing = YP('', cd, o.g), wingF = YP('', c, o.g);
      YP('M-30,-8 C-14,-18 22,-18 40,-10 L120,-22 L44,2 C26,10 -14,10 -30,-8Z', c, o.g);
      YP('M40,-14 L20,-52 L58,-14Z', mix(c, '#1a1040', .2), o.g); YC(46, -10, 6.5, '#ffffff', o.g); YC(47, -10, 3.6, '#1a1424', o.g);
      o.update = (t, { x = 0, y = 0, s = 1, flip = 1, rate = .7, ph = 0 } = {}) => { const k = Math.sin(t * rate * 6.2832 + ph), yy = -70 * k;
        set(o.g, { transform: `translate(${f(x)},${f(y)}) scale(${(s * flip).toFixed(3)},${s.toFixed(3)})` });
        set(wing, { d: `M-6,-6 C-60,${f(yy * .7 - 20)} -170,${f(yy - 30)} -250,${f(yy - 10)} C-170,${f(yy * .4)} -60,6 -6,6Z` });
        set(wingF, { d: `M6,-6 C40,${f(yy * .6 - 20)} 120,${f(yy - 26)} 200,${f(yy - 6)} C120,${f(yy * .4 + 4)} 40,8 6,6Z` }); };
      return o;
    },
    // ------------------------------------------------------------ small mammals: one body-and-head outline, ear set into the
    // head, stub legs behind, a big eye, whiskers, a pink nose; each kind has its own build, pattern and food
    mam(parent, { c = '#ff9a3c', kind = 'plain' } = {}) {
      const long = kind === 'climb', round = kind === 'gnaw', snout = kind === 'insect';
      const nose = snout ? 156 : 132, top = round ? -88 : long ? -62 : -72;
      const spec = { band: 5, shadow: [20, 80], pivot: [60, -40], outline: [[-58, -28, 0],
        [[-62, top + 18, 0], [-34, top, 0], [4, top, 0]], [[34, top, .1], [52, top + 10, .4], [64, -60, .8]],
        [[74, -72, 1], [92, -78, 1], [104, -74, 1]], [[122, -68, 1], [nose - 6, -54, 1], [nose, -46, 1]],
        [[nose + 4, -38, 1], [nose - 4, -30, 1], [nose - 16, -28, 1]], [[100, -26, 1], [90, -26, .8], [80, -22, .5]],
        [[64, -14, 0], [40, -12, 0], [10, -12, 0]], [[-20, -12, 0], [-40, -12, 0], [-48, -14, 0]], [[-56, -16, 0], [-58, -22, 0], [-58, -28, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root };
      o.tail = stroke(long ? 'M-52,-32 C-96,-36 -126,-64 -122,-104 C-118,-130 -92,-134 -86,-118' : 'M-52,-26 C-82,-28 -100,-40 -112,-58', A.far, long ? 9 : 8, A.back);
      stub(A, { x: -16, top: -24, w: 13, step: 5, lift: 6, off: .5 }, false); stub(A, { x: 62, top: -24, w: 11, step: 5, lift: 6, off: 0 }, false);
      stub(A, { x: -32, top: -24, w: 15, step: 5, lift: 6, off: 0 }, true); stub(A, { x: 48, top: -24, w: 13, step: 5, lift: 6, off: .5 }, true);
      o.ear = el('g', {}, A.back); YP('M74,-66 C66,-92 80,-106 94,-102 C106,-98 106,-82 96,-66Z', c, o.ear); YP('M80,-72 C76,-88 84,-96 92,-94 C98,-90 98,-80 92,-72Z', '#ff93a8', o.ear);
      A.headBack.push(o.ear);
      A.finish();
      if (long) for (let i = 0; i < 4; i++) YP(`M${-40 + i * 22},${top + 2} l10,0 l-4,${-top - 22} l-10,0Z`, A.spot, A.inBody);   // stripes
      else if (round) spots(A.inBody, [[-30, -56, 9], [0, -70, 7], [24, -50, 8], [-12, -36, 6]], A.spot);
      else spots(A.inBody, [[-30, -48, 6], [-6, -58, 5], [16, -42, 5]], A.spot);
      const tip = [nose, -46];
      YE(tip[0] - 18, tip[1] + 8, 15, 8, A.pale, A.headG);
      YC(tip[0], tip[1] - 2, 5, '#ff6f8a', A.headG);
      [[-2, -4], [0, 2], [2, 7]].forEach(([dy, k]) => stroke(`M${tip[0] - 12},${tip[1] + dy} l${18 + k},${dy * 1.5 - 3}`, '#ffffff', 1.6, A.headG, { opacity: .7 }));
      if (round) YP(`M${tip[0] - 7},${tip[1] + 8} l5,0 l-1,10 l-5,0Z`, '#ffffff', A.headG);
      o.eye = eye(A.headG, nose - 34, -56, 8.5);
      o.lid = YP('', c, A.headG);
      o.hold = el('g', {}, A.headG);
      if (round) { YE(tip[0] + 6, tip[1] + 16, 9, 11, '#7ad04a', o.hold); stroke(`M${tip[0] + 6},${tip[1] + 5} l0,-6`, '#4c9a3a', 3, o.hold); }
      if (long) { YC(tip[0] + 2, tip[1] + 12, 6, '#ff3b5a', o.hold); YC(tip[0] + 10, tip[1] + 16, 6, '#e02a4a', o.hold); YC(tip[0] - 2, tip[1] + 20, 5, '#ff5a7a', o.hold); }
      if (snout) { o.snack = el('g', { opacity: 0 }, A.headG); YE(tip[0] + 8, tip[1] + 2, 16, 3.5, '#3a3aa8', o.snack); YE(tip[0] + 6, tip[1] - 6, 5, 10, '#cfefff', o.snack, { opacity: .8 }); }
      o.extra = (t, st) => { const lk = st.lid || 0, ex = nose - 34;
        set(o.lid, { d: lk < .02 ? '' : `M${ex - 9},-65 L${ex + 9},-65 L${ex + 9},${f(-65 + 16 * lk)} C${ex + 3},${f(-61 + 16 * lk)} ${ex - 3},${f(-61 + 16 * lk)} ${ex - 9},${f(-65 + 16 * lk)}Z` });
        const ea = -45 * (st.ears || 0); set(o.ear, { transform: `${o.ear.getAttribute('transform') || ''}`.replace(/ ?rotate\([^)]*\) ?rotate\([^)]*\)$/, '') });
        set(o.ear.firstChild, { transform: `rotate(${f(ea)} 86 -68)` }); set(o.ear.lastChild, { transform: `rotate(${f(ea)} 86 -68)` });
        set(o.tail, { transform: `rotate(${f(5 * Math.sin(t * 3))} -52 -28)` }); };
      o.update = driver(A, o, { bob: 3, breath: 1, nod: 3 });
      return o;
    },
    // ------------------------------------------------------------ Repenomamus: a stocky, low, badger-like hunter, about
    // twice a small mammal's length; broad head, a pale stripe from the nose over the crown, a dark mask, a slanted brow
    // and two fangs over the lip (it never reads cute-round). Nose at x 220, top of the back at -128.
    repeno(parent, { c = '#5a46b8', stripe = '#efe8ff' } = {}) {
      const spec = { band: 16, shadow: [20, 190], pivot: [110, -80], outline: [[-150, -40, 0],
        [[-158, -90, 0], [-110, -130, 0], [-30, -130, 0]], [[40, -130, 0], [90, -122, .2], [112, -108, .6]],
        [[130, -122, 1], [172, -120, 1], [198, -100, 1]], [[214, -88, 1], [222, -70, 1], [212, -58, 1]],
        [[198, -46, 1], [160, -42, 1], [136, -44, .8]], [[112, -46, .5], [100, -34, 0], [80, -30, 0]],
        [[40, -24, 0], [-60, -24, 0], [-110, -28, 0]], [[-140, -30, 0], [-150, -34, 0], [-150, -40, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root }, dk = mix(c, '#1a1040', .45);
      o.tail = stroke('M-146,-70 C-180,-70 -206,-58 -222,-40', A.far, 22, A.back);
      stub(A, { x: -96, top: -40, w: 32, step: 12, lift: 14, off: .5, toes: 3 }, false); stub(A, { x: 70, top: -40, w: 30, step: 12, lift: 14, off: 0, toes: 3 }, false);
      stub(A, { x: -118, top: -40, w: 34, step: 12, lift: 14, off: 0, toes: 3 }, true); stub(A, { x: 48, top: -40, w: 32, step: 12, lift: 14, off: .5, toes: 3 }, true);
      const ear = YC(126, -122, 15, dk, A.back); A.headBack.push(ear);
      A.finish();
      spots(A.inBody, [[-90, -96, 12], [-40, -112, 9], [10, -94, 11], [-120, -64, 7]], A.spot);
      YP('M-150,-40 C-150,-20 -60,-18 40,-20 C90,-22 120,-34 130,-46 C100,-40 40,-34 -40,-34 C-100,-34 -140,-36 -150,-40Z', dk, A.inBody, { opacity: .45 });   // shade along the lower right
      YP('M214,-78 C190,-96 160,-116 126,-122 C150,-124 186,-118 214,-92Z', stripe, A.headG);                    // the pale stripe
      YP('M150,-104 C162,-112 184,-106 192,-94 C184,-84 162,-84 148,-92Z', dk, A.headG);                         // the mask
      YE(176, -50, 22, 7, mix(c, '#fff8d0', .55), A.headG);                                                    // pale chin
      YP('M196,-58 L200,-44 L205,-58Z', '#ffffff', A.headG); YP('M206,-60 L210,-47 L214,-61Z', '#ffffff', A.headG);   // fangs
      YC(219, -72, 6, '#1a1424', A.headG);
      o.eye = eye(A.headG, 172, -98, 9);
      o.brow = stroke('M158,-114 L186,-106', '#1a1424', 5, A.headG);
      o.update = driver(A, o, { bob: 4, breath: 1.5, nod: 3 });
      return o;
    },
    // ------------------------------------------------------------ Psittacosaurus: a two-legged plant eater with a deep
    // parrot beak, a small cheek horn, short arms and a fringe of quills along the top of the tail. Beak tip at x 258,
    // hips at -160 (the adult is drawn about 590 long; the young one is the same animal scaled down).
    psitta(parent, { c = '#4ab89a', beak = '#fff2c8', quill = '#c8f0a0' } = {}) {
      const spec = { band: 12, shadow: [-30, 210], pivot: [118, -168], outline: [[-330, -150, 0],
        [[-250, -172, 0], [-140, -202, 0], [-40, -202, 0]], [[40, -202, 0], [90, -184, .1], [110, -172, .3]],
        [[130, -180, .7], [150, -216, 1], [184, -222, 1]], [[222, -228, 1], [250, -208, 1], [256, -188, 1]],
        [[262, -172, 1], [256, -156, 1], [242, -158, 1]], [[226, -160, 1], [200, -152, 1], [176, -150, .8]],
        [[150, -146, .4], [130, -120, 0], [100, -104, 0]], [[60, -88, 0], [-20, -86, 0], [-80, -100, 0]],
        [[-160, -122, 0], [-260, -142, 0], [-330, -150, 0]]] };
      const A = make(parent, c, spec), o = { A, g: A.root };
      ridge(A, .02, .2, 9, 22, 'stripe', [-160, -150], quill);
      // jointed hind legs (thigh, shin with the knee forward and the ankle back, a long foot, three toes) and small
      // forearms with a three-fingered hand: it stands on two legs like a person, not on a post
      const pale = mix(c, '#fff8d0', .5), HIP = [-20, -122];
      const legD = (H, F) => { const An = [F[0] - 36, F[1] - 46], K = [H[0] + 52, H[1] + .55 * (An[1] - H[1])];
        const mx = (H[0] + K[0]) / 2, my = (H[1] + K[1]) / 2, a = Math.atan2(K[1] - H[1], K[0] - H[0]), rx = Math.hypot(K[0] - H[0], K[1] - H[1]) / 2 + 30, ry = 40;
        let thigh = ''; for (let k = 0; k < 24; k++) { const u = k / 24 * 6.2832, ex = Math.cos(u) * rx, ey = Math.sin(u) * ry * (Math.cos(u) < 0 ? 1.1 : .8);
          thigh += (k ? 'L' : 'M') + f(mx + ex * Math.cos(a) - ey * Math.sin(a)) + ',' + f(my + ex * Math.sin(a) + ey * Math.cos(a)) + ' '; }
        const pts = [K, An, [F[0] + 2, F[1] - 10]], ws = [30, 20, 15], Lf = [], Rt = [];
        pts.forEach((q, i) => { const p0 = pts[Math.max(0, i - 1)], p1 = pts[Math.min(2, i + 1)]; let nx = -(p1[1] - p0[1]), ny = p1[0] - p0[0]; const m = Math.hypot(nx, ny) || 1; nx /= m; ny /= m;
          Lf.push([q[0] + nx * ws[i], q[1] + ny * ws[i]]); Rt.push([q[0] - nx * ws[i], q[1] - ny * ws[i]]); });
        const path = ps => ps.map((q, i) => (i ? 'L' : 'M') + f(q[0]) + ',' + f(q[1])).join(' ');
        const foot = `M${f(F[0] - 22)},${f(F[1] - 18)} L${f(F[0] + 34)},${f(F[1] - 16)} Q${f(F[0] + 50)},${f(F[1] - 14)} ${f(F[0] + 50)},${f(F[1] - 6)} Q${f(F[0] + 50)},${f(F[1])} ${f(F[0] + 40)},${f(F[1])} L${f(F[0] - 24)},${f(F[1])} Q${f(F[0] - 34)},${f(F[1])} ${f(F[0] - 34)},${f(F[1] - 9)} Q${f(F[0] - 34)},${f(F[1] - 18)} ${f(F[0] - 22)},${f(F[1] - 18)}Z`;
        return { thigh: thigh + 'Z', shin: path(Lf) + ' ' + path(Rt.slice().reverse()).replace('M', 'L') + 'Z', foot }; };
      o.farLeg = ['thigh', 'shin', 'foot'].map(() => YP('', A.far, A.back));
      o.farToes = Array.from({ length: 3 }, () => YP('', mix(A.far, '#fff8d0', .4), A.back));
      YP('M96,-120 C112,-102 120,-92 132,-88 L138,-94 L140,-84 L130,-80 C116,-86 104,-100 90,-112Z', A.far, A.back);   // far forearm
      o.leg = ['thigh', 'shin', 'foot'].map(() => A.frontPart(''));
      o.arm = A.frontPart('M108,-116 C124,-98 132,-88 146,-84 L152,-90 L154,-80 L144,-76 L148,-70 L136,-72 C122,-80 110,-94 98,-108Z');
      o.toes = Array.from({ length: 3 }, () => YP('', pale, A.front));
      A.finish();
      spots(A.inBody, [[-120, -150, 12], [-60, -170, 16], [0, -150, 10], [-200, -152, 8], [40, -170, 9]], A.spot);
      YP('M230,-222 C252,-212 262,-190 260,-172 C258,-160 250,-156 242,-158 C238,-176 232,-196 222,-212Z', beak, A.headG);   // the beak
      YP('M196,-164 L188,-142 L208,-160Z', beak, A.headG);                                                         // cheek horn
      o.eye = eye(A.headG, 198, -196, 13);
      o.extra = (t, st) => { const rate = st.walk || 0;
        const step = off => { let dx = 0, lift = 0;
          if (rate) { const ph = ((t * rate + off) % 1 + 1) % 1; if (ph < .55) dx = lerp(40, -40, ph / .55); else { const u = (ph - .55) / .45; dx = lerp(-40, 40, eio(u)); lift = 26 * Math.sin(Math.PI * u); } }
          return [dx, -lift]; };
        const put = (els, toes, H, off, fx) => { const [dx, ly] = step(off), F = [fx + dx, ly], d = legD(H, F);
          set(els[0], { d: d.thigh }); set(els[1], { d: d.shin }); set(els[2], { d: d.foot });
          toes.forEach((tl, i) => { const tx = F[0] + 44 - i * 14; set(tl, { d: `M${f(tx - 5)},${f(F[1])} Q${f(tx)},${f(F[1] - 10)} ${f(tx + 5)},${f(F[1])}Z` }); }); };
        put(o.farLeg, o.farToes, [HIP[0] + 26, HIP[1] + 2], .5, 6);
        put(o.leg, o.toes, HIP, 0, -10); };
      o.update = driver(A, o, { bob: 7, breath: 2, nod: 3 });
      return o;
    },
  };
})();
