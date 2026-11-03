'use strict';
// People on a 2D canvas (LIBRARY.md "People on a code-drawn canvas"). Flat shapes, no outlines, one darker shade per form.
// Pure in t, like every kit piece. Load before the page's own code, then bind it to the page's canvas:
//   const { person, personBack, walker, react, bangOn, jumpAt, toLocal, idle } = People.rig(ctx, { pal, onEvent });
//     pal       colours (defaults below); onEvent(t, kind) receives the sound time of a pop ("!" via bang/bangOn)
//   person(o, t) -> {jl, jr, top}   front figure. o: x, y (feet), s, shirt, pants, hair, hairStyle (short|bun|curly|bald|long),
//       hat (hard|admiral|goggles), skin, seed, look (-1..1), lookY (-1..1, up), mouth (smile|grin|o|wide|flat),
//       brow (calm|up|worry|focus), tilt (head rad), armL/armR {tx, ty, hand: open|point|fist, bend}, armsFront,
//       bob, sq (from jumpAt), noLegs, coat. top = world y of the head top, hat included (put the "!" there).
//   personBack(o, t)                 seen from behind (at a board, at a screen): the head is all hair
//   walker(o, t)                     side view, no foot slide: o.dist = world px walked / o.s, o.dir = 1 | -1
//   react(kind, u, from = HANG)      blend the arms from `from` to POSES[kind] by u (use a spring of t - t0)
//   jumpAt(t, t0, h, d) -> {bob, sq} a reaction hop with squash on take-off and landing
//   bang(x, y, t, t0) / bangOn(p, x, t, t0)   a "!" that pops; bangOn sits it on p.top
//   toLocal(o, wx, wy) -> {tx, ty}  a world point as an arm target (touch or point at something real)
// Local units: a figure 918 high with its feet at y 0; arms are IK tubes 118 / 112 long, 40 / 36 thick.
const People = (() => {
  const PAL = {
    ink: '#2b2d42', red: '#d62828', orange: '#f4a261', navy: '#2e3c5a', teal: '#5b8a8f', blue: '#8d9db6',
    skin: '#f1a28c', shoe: '#2b2d42',
  };
  const POSES = {
    shock: { armL: { tx: -235, ty: -660, hand: 'open' }, armR: { tx: 235, ty: -660, hand: 'open' } },       // hands up beside the face
    flung: { armL: { tx: -330, ty: -560, hand: 'open' }, armR: { tx: 330, ty: -560, hand: 'open' } },       // arms thrown out
    cheeks: { armL: { tx: -150, ty: -640, hand: 'open' }, armR: { tx: 150, ty: -640, hand: 'open' }, armsFront: true },
    point: { armL: { tx: -160, ty: -340 }, armR: { tx: 250, ty: -980, hand: 'point' } },
    shrug: { armL: { tx: -270, ty: -420, hand: 'open' }, armR: { tx: 270, ty: -420, hand: 'open' } },
  };
  const HANG = { armL: { tx: -150, ty: -330 }, armR: { tx: 150, ty: -330 } };

  function rig(ctx, { pal = {}, onEvent = null } = {}) {
    const P = Object.assign({}, PAL, pal);
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    const lerp = (a, b, u) => a + (b - a) * u;
    const rnd = i => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
    function spring(u, z = .45, w = 15) {
      if (u <= 0) return 0;
      const wd = w * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w * u) * (Math.cos(wd * u) + z * w / wd * Math.sin(wd * u));
    }
    const hx = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16));
    const toHex = a => '#' + a.map(v => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0')).join('');
    const _dk = {};
    const dk = (h, k = .84) => _dk[h + k] || (_dk[h + k] = toHex(hx(h).map(v => v * k)));
    const lt = (h, k = .25) => toHex(hx(h).map(v => v + (255 - v) * k));
    function fill(f) { ctx.fillStyle = f; ctx.fill(); }
    function R(x, y, w, h, r, f) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r || 0); fill(f); }
    function O(x, y, r, f) { ctx.beginPath(); ctx.arc(x, y, Math.max(r, 0), 0, Math.PI * 2); fill(f); }
    function E(x, y, rx, ry, f, rot = 0) { ctx.beginPath(); ctx.ellipse(x, y, Math.max(rx, 0), Math.max(ry, 0), rot, 0, Math.PI * 2); fill(f); }
    function RS(x, y, w, h, r, f, amt = .22) {
      R(x, y, w, h, r, f);
      ctx.save(); ctx.beginPath(); ctx.roundRect(x, y, w, h, r || 0); ctx.clip();
      ctx.fillStyle = dk(f); ctx.fillRect(x + w * (1 - amt), y - 1, w * amt + 2, h + 2); ctx.restore();
    }
    function line(x1, y1, x2, y2, w, col, cap = 'round') {
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineWidth = w; ctx.lineCap = cap; ctx.strokeStyle = col; ctx.stroke();
    }
    function puff(x, y, t, t0, size = 60) {
      const u = (t - t0) / .38;
      if (u < 0 || u > 1) return;
      for (let i = 0; i < 8; i++) {
        const a = i / 8 * Math.PI * 2 + .4, d = size * (.35 + u * 1.15);
        O(x + Math.cos(a) * d, y + Math.sin(a) * d * .8, size * .34 * (1 - u) * (.7 + rnd(i + t0 * 7) * .6), '#ffffff');
      }
    }
    function pop(t, t0, px, py, fn, kind = 'pop') {
      if (onEvent) onEvent(t0, kind);
      if (t < t0) return;
      const s = spring(t - t0, .42, 16), q = .16 * Math.sin(clamp((t - t0) / .32, 0, 1) * Math.PI);
      ctx.save(); ctx.translate(px, py); ctx.scale(s * (1 + q), s * (1 - q)); ctx.translate(-px, -py); fn(); ctx.restore();
    }

    // local units: a 918 px tall figure, feet at 0. Arms are two-bone IK tubes (118 / 112, 36 thick) with mitten hands.
    function blinkOn(t, seed) {
      const tt = t + seed * 1.7, n = Math.floor(tt / 3.45);
      for (const m of [n - 1, n]) { const b = m * 3.45 + (rnd(m * 3.1 + seed) - .5) * .75; if (tt >= b && tt < b + .14) return true; }
      return false;
    }
    function ik(sx, sy, tx, ty, bend, a = 118, b = 112) {
      const d = clamp(Math.hypot(tx - sx, ty - sy), Math.abs(a - b) + 1, a + b - .5), ang = Math.atan2(ty - sy, tx - sx);
      const A = Math.acos(clamp((a * a + d * d - b * b) / (2 * a * d), -1, 1)), ua = ang - bend * A;
      const ex = sx + Math.cos(ua) * a, ey = sy + Math.sin(ua) * a, fa = Math.atan2(ty - ey, tx - ex);
      return { ex, ey, hx: ex + Math.cos(fa) * b, hy: ey + Math.sin(fa) * b, fa };
    }
    function hand(kind, x, y, ang, skin) {
      ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
      if (kind === 'point') { R(4, -10, 58, 20, 10, skin); O(0, 0, 25, skin); O(-2, 16, 12, dk(skin, .92)); }
      else if (kind === 'fist') { O(0, 0, 28, skin); E(6, 14, 14, 9, dk(skin, .92)); }
      else { E(14, 0, 34, 27, skin); E(4, -26, 13, 10, skin, -.6); }   // open mitten + thumb
      ctx.restore();
    }
    function arm(sx, sy, a, sleeve, skin, side) {
      const tgt = a || {}, tx = tgt.tx != null ? tgt.tx : sx + side * 40, ty = tgt.ty != null ? tgt.ty : sy + 222;
      const j = ik(sx, sy, tx, ty, tgt.bend != null ? tgt.bend : -side);
      const sv = dk(sleeve, .86);   // a shade darker than the shirt so the arm reads over the torso
      line(sx, sy, j.ex, j.ey, 40, sv);
      line(j.ex, j.ey, j.hx, j.hy, 36, skin);
      hand(tgt.hand || 'open', j.hx, j.hy, j.fa, skin);
      O(sx, sy, 27, sv);   // round shoulder socket
      return j;
    }
    function hairCap(style, hair) {
      if (style === 'short') { ctx.save(); ctx.beginPath(); ctx.ellipse(0, -175, 172, 166, 0, 0, Math.PI * 2); ctx.clip();
        E(0, -305, 205, 105, hair); E(-150, -225, 46, 60, hair); E(150, -225, 46, 60, hair); ctx.restore(); }
      else if (style === 'bun') { O(0, -350, 58, hair); ctx.save(); ctx.beginPath(); ctx.ellipse(0, -175, 172, 166, 0, 0, Math.PI * 2); ctx.clip(); E(0, -305, 205, 105, hair); ctx.restore(); }
      else if (style === 'curly') { for (let i = 0; i < 9; i++) { const a = Math.PI * (1.05 + i * .1); O(Math.cos(a) * 165, -175 + Math.sin(a) * 160, 56, hair); } }
    }
    function hat(kind) {
      if (kind === 'hard') { ctx.save(); ctx.beginPath(); ctx.ellipse(0, -235, 180, 140, 0, Math.PI, 0); fill(P.orange); ctx.restore(); R(-205, -250, 410, 34, 17, dk(P.orange, .88)); R(-24, -372, 48, 120, 20, lt(P.orange, .2)); }
      else if (kind === 'admiral') { R(-190, -300, 380, 70, 30, P.navy); E(0, -320, 175, 70, P.navy); R(-205, -250, 410, 28, 14, '#1f2a40'); O(0, -305, 26, P.orange); }
      else if (kind === 'goggles') { R(-165, -265, 330, 26, 12, P.ink); O(-62, -255, 40, P.teal); O(62, -255, 40, P.teal); }
    }
    // front-facing figure. o: x, y (feet), s, shirt, pants, hair, hairStyle, hat, skin, seed, look (-1..1), lookY (-1..1, up),
    // mouth (smile|grin|o|wide|flat), brow (calm|up|worry|focus), tilt (head rad), armL, armR, armsFront (hands over the face),
    // bob (jump height in local px), sq (squash), noLegs, coat (lab coat). Returns {jl, jr, top}: top = world y of the head top.
    function brows(kind, ex, hatted, col) {
      const by = hatted ? -207 : (kind === 'up' ? -238 : -222);
      for (const sg of [-1, 1]) {
        const r = kind === 'worry' ? sg * .35 : kind === 'focus' ? -sg * .35 : kind === 'up' ? sg * .12 : 0;
        ctx.save(); ctx.translate(ex + sg * 58, by); ctx.rotate(r); R(-24, -6, 48, 12, 6, col); ctx.restore();
      }
    }
    function person(o, t) {
      const { s = .4, shirt = P.teal, pants = P.navy, hair = '#3e3138', hairStyle = 'short', skin = P.skin, seed = 1, look = 0, mouth = 'smile', sq = 0 } = o;
      const bob = o.bob || 0, br = Math.sin(t * 2.4 + seed) * 5, nod = .035 * Math.sin(t * 2.2 + seed * 1.3);
      ctx.save(); ctx.translate(o.x, o.y); ctx.scale(s * (1 + sq), s * (1 - sq));
      E(0, -4, 160 - bob * .15, 22, 'rgba(35,30,55,.18)');
      ctx.translate(0, -bob);
      if (!o.noLegs) { RS(-88, -260, 74, 252, 32, pants); RS(14, -260, 74, 252, 32, pants); E(-55, -10, 62, 26, P.shoe); E(55, -10, 62, 26, P.shoe); }
      const ty = -548 + br;
      if (o.coat) { RS(-140, ty, 280, 400, 70, '#f4f1ea', .2); R(-42, ty + 10, 84, 300, 30, shirt); }
      else RS(-128, ty, 256, 330, 72, shirt, .22);
      const sl = o.coat ? '#f4f1ea' : shirt;
      let jl, jr;
      const arms = () => { jl = arm(-114, ty + 52, o.armL, sl, skin, -1); jr = arm(114, ty + 52, o.armR, sl, skin, 1); };
      if (!o.armsFront) arms();
      ctx.save(); ctx.translate(0, ty); ctx.rotate(nod + (o.tilt || 0));
      R(-34, -44, 68, 64, 22, dk(skin, .9));
      if (o.hairStyle === 'long') R(-190, -300, 380, 300, 120, o.hair || '#3e3138');
      E(-166, -160, 26, 34, dk(skin, .95)); E(166, -160, 26, 34, dk(skin, .95));   // ears
      if (hairStyle === 'bald') { E(-150, -232, 38, 50, hair, .3); E(150, -232, 38, 50, hair, -.3); }
      O(0, -175, 170, skin);
      ctx.save(); ctx.beginPath(); ctx.ellipse(0, -175, 172, 166, 0, 0, Math.PI * 2); ctx.clip(); E(-look * 30 + 150, -150, 70, 190, dk(skin, .93)); ctx.restore();
      hairCap(hairStyle === 'long' ? 'short' : hairStyle, hair);
      if (o.hat) hat(o.hat);
      const ex = look * 42, ey = -168 - (o.lookY || 0) * 22, closed = blinkOn(t, seed);
      for (const sx of [-58, 58]) closed ? R(ex + sx - 16, ey - 4, 32, 7, 3, P.ink) : O(ex + sx, ey, 15, P.ink);
      brows(o.brow || 'calm', ex, o.hat === 'hard' || o.hat === 'admiral', hairStyle === 'bald' ? '#8a7d72' : dk(hair, .8));
      E(ex - 104, -122, 24, 13, '#ec8c7c'); E(ex + 104, -122, 24, 13, '#ec8c7c');
      if (mouth === 'o') E(ex * .8, -94, 30, 40, '#7a2e3a');
      else if (mouth === 'flat') R(ex * .8 - 26, -104, 52, 10, 5, '#7a2e3a');
      else if (mouth === 'wide') { ctx.beginPath(); ctx.ellipse(ex * .8, -112, 46, 40, 0, 0, Math.PI); fill('#7a2e3a'); }
      else if (mouth === 'grin') { ctx.beginPath(); ctx.ellipse(ex * .8, -114, 54, 38, 0, 0, Math.PI); fill('#7a2e3a'); R(ex * .8 - 40, -114, 80, 12, 4, '#ffffff'); }
      else { ctx.beginPath(); ctx.ellipse(ex * .8, -110, 30, 20, 0, 0, Math.PI); fill('#7a2e3a'); }
      ctx.restore();
      if (o.armsFront) arms();
      ctx.restore();
      const crown = o.hat === 'hard' ? 375 : o.hat === 'admiral' ? 390 : hairStyle === 'bun' ? 408 : 345;
      return { jl, jr, top: o.y - s * (1 - sq) * (bob + 548 - br + crown) };
    }
    // seen from behind (writing at a board, looking at a screen): no face, the whole head is hair
    function personBack(o, t) {
      const { s = .4, shirt = P.blue, pants = P.navy, hair = '#3e3138', skin = P.skin, seed = 2 } = o;
      const br = Math.sin(t * 2.4 + seed) * 5, nod = .035 * Math.sin(t * 2.2 + seed);
      ctx.save(); ctx.translate(o.x + Math.sin(t * 1.1 + seed) * 6 * s, o.y); ctx.scale(s, s);
      E(0, -4, 160, 22, 'rgba(35,30,55,.18)');
      if (!o.noLegs) { RS(-88, -260, 74, 252, 32, pants); RS(14, -260, 74, 252, 32, pants); E(-55, -10, 62, 26, P.shoe); E(55, -10, 62, 26, P.shoe); }
      const ty = -548 + br;
      RS(-128, ty, 256, 330, 72, o.coat ? '#f4f1ea' : shirt, .22);
      const sl = o.coat ? '#f4f1ea' : shirt;
      arm(-114, ty + 52, o.armL, sl, skin, -1); arm(114, ty + 52, o.armR, sl, skin, 1);
      ctx.save(); ctx.translate(0, ty); ctx.rotate(nod);
      R(-34, -44, 68, 64, 22, dk(skin, .9));
      E(-168, -168, 24, 34, skin); E(168, -168, 24, 34, skin);
      O(0, -175, 170, hair); ctx.save(); ctx.beginPath(); ctx.arc(0, -175, 170, 0, Math.PI * 2); ctx.clip(); E(150, -150, 70, 190, dk(hair, .85)); ctx.restore();
      if (o.hat) hat(o.hat);
      ctx.restore();
      ctx.restore();
    }
    // side view walking. dist = local units walked. Thighs swing +-0.42 rad; in stance the foot stays planted (the thigh angle
    // follows asin of a linear foot offset), on the swing the knee bends 0.75*sin^2 (0.75*cos^2 of the swing phase); the hips
    // drop to the straight stance leg. One cycle covers 4*L*sin(.42) = 1.63 leg lengths, the stride those angles give.
    function walker(o, t) {
      const { s = .4, dir = 1, shirt = P.teal, pants = P.navy, hair = '#3e3138', skin = P.skin, seed = 3, dist = 0 } = o;
      const T = 128, S = 118, L = T + S, A0 = Math.sin(.42), p = 2 * Math.PI * dist / (4 * L * A0);
      const leg = ph => { ph = ((ph % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
        if (ph < Math.PI) return { th: Math.asin(A0 * (1 - 2 * ph / Math.PI)), k: 0, sw: false };
        const v = (ph - Math.PI) / Math.PI; return { th: -.42 * Math.cos(v * Math.PI), k: .75 * Math.sin(v * Math.PI) ** 2, sw: true }; };
      const A = leg(p), B = leg(p + Math.PI), st = A.sw ? B : A, hipY = -L * Math.cos(st.th) - 22;
      ctx.save(); ctx.translate(o.x, o.y); ctx.scale(dir * s, s);
      E(0, -4, 120, 18, 'rgba(35,30,55,.18)');
      const drawLeg = (g, col) => {
        const kx = Math.sin(g.th) * T, ky = hipY + Math.cos(g.th) * T, fx = kx + Math.sin(g.th - g.k) * S, fy = ky + Math.cos(g.th - g.k) * S;
        line(0, hipY, kx, ky, 64, col); line(kx, ky, fx, fy, 60, col); E(fx + 30, fy + 4, 54, 24, P.shoe);
      };
      drawLeg(B, dk(pants, .85));
      const ty = hipY - 300, sw = -.9 * A.th;
      const armSide = (ang, col, sk) => { const sx = 0, sy = ty + 60, ex = sx + Math.sin(ang) * 118, ey = sy + Math.cos(ang) * 118,
        fa = ang + .35, hx2 = ex + Math.sin(fa) * 112, hy2 = ey + Math.cos(fa) * 112;
        line(sx, sy, ex, ey, 40, col); line(ex, ey, hx2, hy2, 36, sk); hand('fist', hx2, hy2, 0, sk); };
      armSide(-sw, dk(shirt, .72), dk(skin, .9));
      drawLeg(A, pants);
      RS(-78, ty, 156, 330, 64, shirt, .25);
      ctx.save(); ctx.translate(0, ty + Math.sin(p * 2) * 4); ctx.rotate(.035 * Math.sin(t * 2.2 + seed));
      R(-30, -44, 60, 64, 20, dk(skin, .9));
      O(12, -170, 165, skin);
      ctx.save(); ctx.beginPath(); ctx.arc(12, -170, 165, 0, Math.PI * 2); ctx.clip(); E(-150, -170, 130, 230, hair); E(10, -300, 200, 85, hair); ctx.restore();
      if (o.hat) { ctx.save(); ctx.translate(12, 5); hat(o.hat); ctx.restore(); }
      O(150, -150, 24, skin);   // nose
      blinkOn(t, seed) ? R(90, -178, 30, 7, 3, P.ink) : O(105, -175, 15, P.ink);
      E(70, -110, 22, 12, '#ec8c7c');
      ctx.beginPath(); ctx.ellipse(115, -102, 22, 14, 0, 0, Math.PI); fill('#7a2e3a');
      ctx.restore();
      armSide(sw, dk(shirt, .86), skin);
      ctx.restore();
    }
    // a "!" that pops above someone
    function bang(x, y, t, t0, col = P.red) {
      pop(t, t0, x, y, () => { R(x - 16, y - 90, 32, 70, 16, col); O(x, y + 4, 17, col); }, 'pop');
      puff(x, y - 40, t, t0, 40);
    }
    // jump curve for a reaction: height in local px and a squash on take-off and landing
    function jumpAt(t, t0, h = 160, d = .5) {
      const u = (t - t0) / d;
      if (u < -.15 || u > 1.2) return { bob: 0, sq: 0 };
      if (u < 0) return { bob: 0, sq: .12 * Math.sin((u + .15) / .15 * Math.PI) };
      if (u > 1) return { bob: 0, sq: .14 * Math.sin((u - 1) / .2 * Math.PI) };
      return { bob: h * 4 * u * (1 - u), sq: -.06 };
    }

    const sway = (t, k = 1) => Math.sin(t * 2.1 * k) * 10;
    const toLocal = (o, wx, wy) => ({ tx: (wx - o.x) / o.s, ty: (wy - o.y) / o.s });
    function react(kind, u, from = HANG) {
      const Q = POSES[kind], mix = (a, b) => ({ tx: lerp(a.tx, b.tx, u), ty: lerp(a.ty, b.ty, u), hand: u > .3 ? b.hand : a.hand });
      return { armL: mix(from.armL, Q.armL), armR: mix(from.armR, Q.armR), armsFront: !!Q.armsFront && u > .2 };
    }
    const bangOn = (p, x, t, t0) => bang(x, p.top - 40, t, t0);
    const idle = t => ({ armL: { tx: -150, ty: -330 + sway(t) * .3 }, armR: { tx: 150, ty: -330 - sway(t) * .3 } });
    return { person, personBack, walker, ik, hand, arm, brows, hairCap, hat, blinkOn, bang, bangOn, jumpAt, react, toLocal, idle, sway,
      POSES, HANG, pal: P };
  }
  return { rig, POSES, HANG, PAL };
})();
