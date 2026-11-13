'use strict';
// Three-quarter people on a 2D canvas: the house people since 2026-11-04 (LIBRARY.md "Three-quarter people", นน picked T2
// from .mp/people_tis_20261104/). Construction learnt from The Infographics Show frames, our own cast and colours: an adult
// body with the head at 1/4 (hs 1.28 over the 1/5 TIS head), the head and body turned three-quarters, the nose sticking out
// past the face line, one ear at the back, dot eyes, short stroke brows, a D mouth with upper teeth, cuffs and collars, and
// one big shade plane per piece. Flat shapes, no outlines. Pure in t. Load before the page's own code, then bind it:
//   const { person, hand, fill, cel, stroke, ell, cap, CAST } = People34.rig(ctx);
//   person(o, t) -> { top, nearHand, farHand }   world px; top = the drawn head top (hair, bun or hat), for a "!" or a label;
//                   each hand point carries .a, the forearm's world angle, to draw a hand or prop over someone drawn later
//     o.x, o.y      feet in world px          o.s     px per local unit (the figure is ~1000 units tall at hs 1)
//     o.dir         1 faces right, -1 left    o.C     a costume: one of CAST or your own (see CAST for the fields)
//     o.view        tq (default, three-quarter) | front (since 2026-11-05, toward the Kurzgesagt frame นน sent: the face
//                   straight on with no nose, two ears, both arms lit). In front, person() reads o.armL / o.armR (the -x and
//                   +x arms before o.dir) in place of armN / armF, and returns { top, handL, handR } (nearHand = handR).
//     o.hs          head scale, default 1.28 (the house 1/4 head); 1 gives the TIS 1/5 head
//     o.dotEyes     default true (bigger dots with a catch light); false gives the small TIS eyes
//     o.light       the world side of the scene light: -1 upper left (default, the house light) | 1 upper right. The shade
//                   planes (cel), the head shade (a thin rim when the face turns away) and the two-tone lapels and vest panels stay on the side away from
//                   it whatever o.dir is, so two people facing each other are lit from the same side (since 2026-11-06)
//     o.eyes        open | happy (closed arcs) | wide       o.mouth  smile | talk (opens with t) | grin | grit | o | flat
//     o.look/lookY  pupil offset in local units (about +-6 / +-4; +x toward the face before o.dir, +y down); the far eye
//                   moves less; ignored on closed and happy eyes. flat = a short straight mouth (worry, doubt, deadpan)
//     o.brow        calm | up | worry          o.sweat  a falling drop       o.nod  extra head tilt (rad)
//     o.belly       a pregnant belly (default C.belly): a bulge forward in tq, a lighter disc on the garment in front
//     o.armN/armF   near / far arm target {x, y (local units), hand: mitt|fingers, big, bend (1 | -1), hold(api)}
//                   hold(api, j) draws a prop in hand space (+x along the forearm) instead of the hand; j.fa is the forearm
//                   angle (rotate by -j.fa for an upright prop; undo j.flip with scale(1, -1) first) ; the far arm is behind the body
//     o.walk        (tq only, since 2026-11-13) local units walked so far (world px / o.s): the legs step with the foot
//                   planted through the stance, the hips drop onto the standing leg, and an arm with no target swings
//                   against its leg. One cycle = 4 * 494 * sin(.38) = 733 units. o.walkAmt (0..1, default 1) eases the
//                   stride, knee lift, hip drop and arm swing to nothing, to start or stop: ramp it over ~0.4 s while the
//                   figure's speed ramps with it; at 0 the standing legs are drawn. o.slope (rad): the ground rises that much
//                   ahead; legs, shoes and the floor shadow follow it, the body stays upright
//     o.ground      false drops the floor shadow (mid and close shots)      o.seed  blinks and breathing phase
// Local units: feet at y 0, shoulders near y -770, the neck at -812; facing +x before o.dir.
const People34 = (() => {
  const CAST = {
    // look: suit | coat | vest | tee | shirt (plain long sleeves, a lighter crew band and cuffs) | dress (to the knee, the legs
    // in `pants` below it); hairStyle: quiff | bun | hat | bob; narrow < 1 slims the torso; blush: the cheek colour (default
    // pink, false for none); belly: a pregnant belly
    off: { skin: '#e9a77f', top: '#2e3c5a', shirt: '#ffffff', tie: '#e63946', pants: '#283149', hair: '#1d1a24', shoe: '#1d1a24', look: 'suit', hairStyle: 'quiff' },
    sci: { skin: '#f3c4a2', top: '#f4f1ea', shirt: '#2a9d8f', pants: '#3d405b', hair: '#2b1d2a', shoe: '#7a2e3a', look: 'coat', hairStyle: 'bun', narrow: .9 },
    wrk: { skin: '#b9774e', top: '#4c7fd1', vest: '#ff8a1f', pants: '#5b4a3a', hair: '#5a5560', shoe: '#2a1d18', look: 'vest', hairStyle: 'hat', stache: '#2a1d18' },
    kid: { skin: '#c98a5e', top: '#ffb703', pants: '#1d7bd8', hair: '#1d1a24', shoe: '#e63946', look: 'tee', hairStyle: 'quiff', narrow: .92 },
    // the couple from the Kurzgesagt reference frame (2026-11-05): a white dress over leggings, a plain blue top
    mom: { skin: '#c98a5e', top: '#fff6ec', pants: '#5b2a86', hair: '#3a1f4e', shoe: '#5b2a86', look: 'dress', hairStyle: 'bob', belly: true },
    dad: { skin: '#c98a5e', top: '#2f7fe6', pants: '#2a2a3a', hair: '#3a1f4e', shoe: '#2a2a3a', look: 'shirt', hairStyle: 'quiff' },
  };
  const TOP = { quiff: 1006, bun: 1016, hat: 1000, bob: 1006 };   // local head top per hair style at hs 1 (checked by the test)
  const LONG = { suit: 1, coat: 1, shirt: 1, dress: 1 };          // looks with long sleeves that end in a cuff
  const BLUSH = '#ff8aa6';                                        // opaque cheeks, the pink of จุก

  function rig(ctx) {
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    const lerp = (a, b, u) => a + (b - a) * u;
    const rnd = i => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
    const hx = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16));
    const toHex = a => '#' + a.map(v => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0')).join('');
    const dk = (h, k = .82) => toHex(hx(h).map(v => v * k));
    const lt = (h, k = .25) => toHex(hx(h).map(v => v + (255 - v) * k));

    // a shape is an SVG-style path string (absolute M L C Q Z only) or a function that adds to the current path
    const _cache = {};
    function parse(d) {
      if (_cache[d]) return _cache[d];
      const tk = d.replace(/([MLCQZ])/g, ' $1 ').trim().split(/[\s,]+/), out = [];
      for (let i = 0; i < tk.length;) { const c = tk[i++], n = { M: 2, L: 2, C: 6, Q: 4, Z: 0 }[c], a = tk.slice(i, i + n).map(Number); i += n; out.push([c, a]); }
      return (_cache[d] = out);
    }
    function trace(sh) {
      if (typeof sh === 'function') return sh();
      for (const [c, a] of parse(sh)) {
        if (c === 'M') ctx.moveTo(a[0], a[1]); else if (c === 'L') ctx.lineTo(a[0], a[1]);
        else if (c === 'C') ctx.bezierCurveTo(a[0], a[1], a[2], a[3], a[4], a[5]); else if (c === 'Q') ctx.quadraticCurveTo(a[0], a[1], a[2], a[3]);
        else ctx.closePath();
      }
    }
    function fill(sh, col) { ctx.beginPath(); trace(sh); ctx.fillStyle = col; ctx.fill(); }
    // flat colour plus one big shade plane: the part of the shape not covered by itself moved toward the light (up, and to
    // the world side o.light while person() draws; local +x outside it, as before)
    function cel(sh, col, d = 16, k = .8) {
      ctx.save(); ctx.beginPath(); trace(sh); ctx.clip();
      ctx.fillStyle = dk(col, k); ctx.fillRect(-4000, -4000, 8000, 8000);
      ctx.translate(d * curLX, -d * .5); fill(sh, col); ctx.restore();
    }
    function stroke(sh, col, w) { ctx.beginPath(); trace(sh); ctx.strokeStyle = col; ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke(); }
    const ell = (cx, cy, rx, ry, rot = 0) => () => ctx.ellipse(cx, cy, rx, ry, rot, 0, Math.PI * 2);
    const cap = (x1, y1, x2, y2, r1, r2 = r1) => () => {
      const a = Math.atan2(y2 - y1, x2 - x1), n = a + Math.PI / 2;
      ctx.moveTo(x1 + Math.cos(n) * r1, y1 + Math.sin(n) * r1); ctx.lineTo(x2 + Math.cos(n) * r2, y2 + Math.sin(n) * r2);
      ctx.arc(x2, y2, r2, n, n - Math.PI, true); ctx.lineTo(x1 - Math.cos(n) * r1, y1 - Math.sin(n) * r1);
      ctx.arc(x1, y1, r1, n + Math.PI, n, true); ctx.closePath();
    };
    let curT = 0, curSeed = 1;   // the person being drawn, for the idle sway of hanging arms
    let curLX = 1;               // the light's local x side (o.light * o.dir) while person() draws; 1 outside it, as before
    function blinkOn(t, seed) {
      const tt = t + seed * 1.7, n = Math.floor(tt / 3.45);
      for (const m of [n - 1, n]) { const b = m * 3.45 + (rnd(m * 3.1 + seed) - .5) * .75; if (tt >= b && tt < b + .14) return true; }
      return false;
    }
    function ik(sx, sy, tx, ty, bend, a, b) {
      const d = clamp(Math.hypot(tx - sx, ty - sy), Math.abs(a - b) + 1, a + b - .5), ang = Math.atan2(ty - sy, tx - sx);
      const A = Math.acos(clamp((a * a + d * d - b * b) / (2 * a * d), -1, 1)), ua = ang - bend * A;
      const ex = sx + Math.cos(ua) * a, ey = sy + Math.sin(ua) * a, fa = Math.atan2(ty - ey, tx - ex);
      return { ex, ey, hx: ex + Math.cos(fa) * b, hy: ey + Math.sin(fa) * b, fa };
    }
    const cheeks = C => C.blush === false ? null : (C.blush || BLUSH);
    const pair = (neg, pos) => curLX > 0 ? [neg, pos] : [pos, neg];   // tones of the -x and +x piece, given for light on +x

    // ---- body, three-quarter ----
    function legs(C, far) {
      const pc = far ? dk(C.pants, .78) : C.pants, sc = far ? dk(C.shoe, .8) : C.shoe;
      ctx.save(); ctx.translate(far ? -56 : 0, 0);
      cel('M -14 -530 L 74 -530 C 76 -400 68 -200 64 -36 L 10 -36 C 6 -200 -10 -400 -14 -530 Z', pc, 12);
      if (C.look === 'tee') {   // shorts: the leg below the knee is bare, a darker hem at the shorts' edge
        fill('M 4 -300 L 70 -300 C 69 -200 66 -110 64 -36 L 10 -36 C 8 -110 6 -200 4 -300 Z', dk(C.skin, far ? .85 : 1));
        fill('M -2 -318 L 76 -318 L 75 -296 L -1 -296 Z', dk(pc, .85));
      } else if (!far) stroke('M 40 -500 C 42 -360 40 -210 37 -60', lt(pc, .12), 3);   // the trouser crease
      fill('M 2 -42 L 66 -42 C 100 -40 118 -26 118 -6 L 118 0 L 0 0 Z', sc);
      ctx.restore();
    }
    // ---- walking legs, three-quarter (o.walk). Thigh 250 + shin 244 = the standing leg (hip -530 to ankle -36). In the
    // stance the thigh angle follows asin of a linear foot offset, so the planted foot does not slide; on the swing the knee
    // bends and the shoe tips toe-down, then toe-up, and is level again as it lands.
    const WT = 250, WS = 244, WL = WT + WS, WA = Math.sin(.38), SHOE = 'M 2 -42 L 66 -42 C 100 -40 118 -26 118 -6 L 118 0 L 0 0 Z';
    function gait(d, amt = 1) {
      const p = 2 * Math.PI * d / (4 * WL * WA);
      const leg = ph => { ph = ((ph % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
        if (ph < Math.PI) return { th: amt * Math.asin(WA * (1 - 2 * ph / Math.PI)), k: 0, sw: false, v: ph / Math.PI };
        const v = (ph - Math.PI) / Math.PI; return { th: -.38 * amt * Math.cos(v * Math.PI), k: .8 * amt * Math.sin(v * Math.PI) ** 1.2, sw: true, v, amt }; };   // the knee stays bent late, so the foot clears the ground until it lands
      const near = leg(p), far = leg(p + Math.PI), st = near.sw ? far : near, hipY = -36 - WL * Math.cos(st.th);
      return { near, far, hipY, bob: hipY + 530 };
    }
    function legW(C, g, far, hipY) {
      // the far leg: darker, but lighter on trousers already too dark to darken, so the two legs never merge as they pass
      const dark = hx(C.pants).reduce((a, v) => a + v, 0) < 200, pc = !far ? C.pants : dark ? lt(C.pants, .16) : dk(C.pants, .78), sc = far ? dk(C.shoe, .8) : C.shoe, hx0 = far ? -22 : 34;
      const kx = hx0 + Math.sin(g.th) * WT, ky = hipY + Math.cos(g.th) * WT, ax = kx + Math.sin(g.th - g.k) * WS, ay = ky + Math.cos(g.th - g.k) * WS;
      if (C.look === 'tee') {   // shorts: a bare shin, the hem a darker band above the knee
        fill(cap(kx, ky, ax, ay, 31, 26), dk(C.skin, far ? .85 : 1)); fill(cap(hx0, hipY, kx, ky, 47, 39), pc);
        fill(cap(lerp(hx0, kx, .9), lerp(hipY, ky, .9), lerp(hx0, kx, .97), lerp(hipY, ky, .97), 40, 39), dk(pc, .85));
      } else { fill(cap(kx, ky, ax, ay, 35, 29), pc); fill(cap(hx0, hipY, kx, ky, 47, 37), pc); }
      const pitch = g.sw ? g.amt * Math.sin(g.v * Math.PI) * .5 * (1 - g.v) : 0;   // flat through the stance, so the heel never sinks
      // a tipped shoe is lifted just enough that neither the toe nor the heel goes below the ground line
      const up = Math.max(0, ay + 36 * Math.cos(pitch) + Math.max(81 * Math.sin(pitch), -37 * Math.sin(pitch)));
      ctx.save(); ctx.translate(ax, ay - up); ctx.rotate(pitch); ctx.translate(-37, 36); fill(SHOE, sc); ctx.restore();
    }
    function torso(C, br, belly) {
      ctx.save(); ctx.translate(0, br); ctx.scale(C.narrow || 1, 1);
      // a shirt collar that wraps the neck; the chin, drawn after, sits in front of it
      const collar = (col, band = true) => {
        if (band) fill('M -14 -808 C -8 -832 42 -836 54 -816 L 50 -798 C 36 -814 6 -814 -8 -796 Z', col);
        fill('M 4 -812 L 26 -786 L 14 -778 Z M 50 -814 L 34 -786 L 46 -778 Z', col);
      };
      const crew = (col, thick) => fill(thick ? 'M -2 -816 C 14 -792 40 -792 56 -818 L 50 -824 C 38 -806 16 -806 4 -822 Z'
        : 'M 0 -814 C 14 -796 40 -796 54 -816 L 50 -820 C 38 -806 16 -806 4 -818 Z', col);
      if (C.look === 'coat') {   // a slight waist, then the coat flares to the hem
        cel('M -16 -812 C -80 -810 -108 -790 -112 -748 C -106 -660 -98 -600 -100 -560 C -104 -480 -108 -420 -108 -360 C -30 -350 40 -350 108 -362 C 106 -430 100 -500 98 -560 C 98 -620 104 -680 106 -740 C 102 -790 80 -810 44 -814 Z', C.top, 18, .86);
        fill('M 4 -814 L 50 -816 L 40 -600 L 22 -600 Z', C.shirt);
        collar(dk(C.shirt, .9), false);
        { const [la, lb] = pair('#d9d4c8', '#e6e2d8'); fill('M 4 -814 L -8 -760 L 22 -600 Z', la); fill('M 50 -816 L 68 -770 L 40 -600 Z', lb); }   // lapels
        fill('M 52 -560 L 92 -560 L 90 -500 L 54 -500 Z', '#e2ded3');                                            // breast pocket
        stroke('M 31 -600 C 30 -500 30 -430 29 -360', '#d9d4c8', 4);                                             // the front edge
      } else if (C.look === 'suit') {
        cel('M -18 -814 C -86 -810 -112 -788 -114 -746 C -108 -660 -100 -610 -102 -560 C -104 -520 -106 -490 -106 -468 C -20 -452 50 -452 104 -470 C 102 -500 98 -530 98 -560 C 98 -620 104 -690 108 -742 C 104 -790 80 -810 46 -816 Z', C.top, 18);
        fill('M 0 -816 L 52 -818 L 34 -628 Z', C.shirt);
        collar('#f2f2f5');
        if (C.tie) { fill('M 18 -806 L 34 -806 L 40 -690 L 28 -664 L 16 -690 Z', C.tie); fill('M 16 -812 L 36 -812 L 32 -796 L 20 -796 Z', dk(C.tie, .8)); }
        { const [la, lb] = pair(.72, .86); fill('M 0 -816 L -14 -770 L 6 -760 L 32 -628 Z', dk(C.top, la)); fill('M 52 -818 L 70 -774 L 56 -764 L 34 -628 Z', dk(C.top, lb)); }   // lapels
        stroke('M 33 -628 C 32 -560 32 -500 30 -462', dk(C.top, .7), 4);                                                                       // the front edge
        fill(ell(40, -560, 6, 6), dk(C.top, .6)); fill(ell(41, -520, 6, 6), dk(C.top, .6));
      } else if (C.look === 'dress') {   // one garment to the knee: a slight waist, then the skirt flares
        cel('M -16 -812 C -80 -810 -108 -790 -112 -748 C -106 -660 -98 -600 -100 -570 C -112 -480 -134 -390 -142 -300 L 152 -300 C 136 -390 112 -480 98 -570 C 98 -620 104 -680 106 -740 C 102 -790 80 -810 44 -814 Z', C.top, 18, .86);
        crew(lt(C.top, .35), true);
      } else {
        cel('M -18 -812 C -84 -810 -110 -790 -112 -748 C -106 -660 -100 -600 -102 -560 C -103 -520 -104 -490 -104 -470 C -20 -456 50 -456 104 -472 C 102 -500 100 -530 100 -560 C 100 -620 104 -690 106 -742 C 102 -790 80 -810 46 -814 Z', C.top, 16);
        if (C.look === 'vest') {
          collar(dk(C.top, .86));
          fill('M 6 -812 L 48 -814 L 36 -770 L 18 -770 Z', dk(C.top, .78));   // polo placket
          const [va, vb] = pair(.82, .9);
          cel('M -104 -770 C -100 -790 -70 -800 -52 -800 L -40 -470 L -104 -478 Z', C.vest, 10, va);
          cel('M 40 -804 C 70 -800 100 -790 106 -760 L 104 -480 L 54 -470 Z', C.vest, 10, vb);
          for (const y of [-640, -560]) { fill(`M -104 ${y} L -40 ${y - 4} L -40 ${y + 14} L -104 ${y + 18} Z`, '#e6e9ef'); fill(`M 52 ${y - 4} L 105 ${y} L 105 ${y + 18} L 52 ${y + 14} Z`, '#e6e9ef'); }
        } else if (C.look === 'shirt') crew(lt(C.top, .35), true);   // a plain top: a lighter crew band
        else crew(dk(C.top, .78));                                    // tee neckline
      }
      if (belly) cel(ell(60, -530, 100, 78), C.top, 14, .86);   // the belly bulges forward of the garment
      ctx.restore();
    }
    function hand(kind, skin, sz) {   // drawn at the wrist, pointing along +x; the thumb is on -y
      if (kind === 'fingers') {
        cel(ell(sz * .55, 0, sz * .62, sz * .56), skin, 4, .9);
        for (const [a, L] of [[-.42, .95], [-.14, 1.1], [.14, 1.05], [.42, .85]]) {
          const bx = sz * .9 + Math.cos(a) * sz * .1, by = Math.sin(a) * sz * .55;
          fill(cap(bx, by, bx + Math.cos(a * .6) * sz * L, by + Math.sin(a * .6) * sz * L, sz * .19, sz * .17), skin);
        }
        fill(cap(sz * .25, -sz * .4, sz * .7, -sz * 1.05, sz * .2, sz * .17), skin);
      } else {   // mitten: a palm, the four fingers as one curled block with two split lines, a thumb toward the front
        cel(ell(sz * .5, 0, sz * .58, sz * .54), skin, 4, .9);
        cel(ell(sz * 1.02, sz * .06, sz * .5, sz * .5), skin, 4, .9);
        stroke(`M ${sz * .92} ${-sz * .14} L ${sz * 1.32} ${-sz * .12}`, dk(skin, .82), sz * .06);
        stroke(`M ${sz * .92} ${sz * .16} L ${sz * 1.3} ${sz * .2}`, dk(skin, .82), sz * .06);
        fill(cap(sz * .3, -sz * .36, sz * .78, -sz * .72, sz * .21, sz * .18), skin);
      }
    }
    // F = { side } draws a front-view arm: both arms lit, the elbow out from the body, the +x hand's thumb inward
    function arm(C, sx, sy, a, far, F) {
      const side = F ? F.side : 0;
      // a hanging arm sways a little and sits just behind the body line, so the hand reads clear of the hip
      const sway = Math.sin(curT * 1.6 + curSeed + (far || side > 0 ? 1.3 : 0)) * 7;
      // (the far hand hangs a little forward of the thigh so it reads as a hand, not a stub poking out)
      const tx = a && a.x != null ? a.x : F ? side * 150 + sway : sx + (far ? 22 : -14) + sway;
      const ty = a && a.y != null ? a.y : F ? -430 : sy + 340;
      const bend = a && a.bend != null ? a.bend : F ? (ty < sy ? -1 : 1) * side : -1;
      const j = ik(sx, sy, tx, ty, bend, 185, 170);
      const sl = F ? dk(C.top, .9) : dk(C.top, far ? .78 : .86), skin = F ? C.skin : dk(C.skin, far ? .85 : 1);
      fill(cap(sx, sy, j.ex, j.ey, 34, 29), sl);
      if (LONG[C.look]) {
        fill(cap(j.ex, j.ey, j.hx, j.hy, 29, 24), sl);
        const cuff = C.look === 'suit' ? '#f2f2f5' : C.look === 'coat' ? dk(sl, .92) : lt(sl, .35);
        fill(cap(lerp(j.ex, j.hx, .9), lerp(j.ey, j.hy, .9), j.hx, j.hy, 25, 25), cuff);
      } else {
        const mx = lerp(sx, j.ex, .55), my = lerp(sy, j.ey, .55);
        fill(cap(sx, sy, mx, my, 36, 33), sl);   // short sleeve over the upper arm
        fill(cap(mx, my, j.ex, j.ey, 25, 23), skin); fill(cap(j.ex, j.ey, j.hx, j.hy, 23, 20), skin);
      }
      ctx.save(); ctx.translate(j.hx, j.hy); ctx.rotate(j.fa); if (side > 0) ctx.scale(1, -1);
      if (a && a.hold) a.hold(api, { ex: j.ex, ey: j.ey, hx: j.hx, hy: j.hy, fa: j.fa, flip: side > 0 }); else hand((a && a.hand) || 'mitt', skin, a && a.big ? 64 : 52);
      ctx.restore();
      return j;
    }

    // ---- head, facing +x ----
    const FACE = 'M 28 -806 C 0 -808 -30 -820 -48 -846 C -70 -870 -80 -905 -74 -935 C -66 -970 -30 -990 5 -990 C 40 -990 62 -968 66 -935 L 68 -906 C 74 -896 92 -880 92 -868 C 92 -859 82 -856 72 -856 C 74 -846 76 -836 70 -826 C 64 -812 48 -806 28 -806 Z';
    const BUN_CAP = 'M 68 -940 C 64 -988 26 -1008 -10 -1006 C -56 -1002 -86 -968 -84 -922 C -82 -884 -72 -862 -56 -852 C -52 -880 -46 -904 -32 -914 C -6 -930 30 -930 48 -948 C 56 -944 62 -940 68 -940 Z';
    const QUIFF_TQ = 'M 60 -944 C 76 -950 84 -972 76 -990 C 68 -1008 40 -1010 14 -1004 C -30 -998 -70 -982 -84 -944 C -88 -915 -80 -885 -66 -866 C -56 -878 -48 -898 -44 -916 L -16 -912 C -16 -904 -11 -897 -3 -896 C 3 -912 9 -930 22 -938 C 36 -944 50 -942 60 -944 Z';
    const BOB_TQ = 'M 68 -940 C 66 -990 28 -1010 -10 -1006 C -60 -1002 -100 -968 -102 -920 C -104 -880 -100 -846 -92 -822 C -84 -806 -40 -804 -24 -822 C -14 -850 -12 -890 -6 -918 C 14 -936 44 -938 68 -940 Z';
    function head(C, o, t) {
      const sk = C.skin, eyeMode = o.eyes || 'open', closed = blinkOn(t, o.seed || 1) && eyeMode !== 'happy', dots = o.dotEyes !== false;
      if (C.hairStyle === 'bun') cel(ell(-62, -982, 36, 34), C.hair, 6);
      ctx.save(); ctx.beginPath(); trace(FACE); ctx.clip(); fill(FACE, sk);
      // the shade side of the head: the back when the face is toward the light. Turned away from it, the face stays lit (it
      // carries the beat): only a thin rim along the nose, the mouth corner and the jaw, never a plane across the mouth
      if (curLX > 0) fill('M -120 -1000 L -38 -1000 C -60 -930 -50 -860 -6 -800 L -120 -800 Z', dk(sk, .92));
      else { fill(FACE, dk(sk, .92)); ctx.translate(-7, -3.5); fill(FACE, sk); }
      ctx.restore();
      if (C.hairStyle !== 'bob') { fill(ell(-26, -886, 14, 21), sk); fill(ell(-24, -884, 7, 12), dk(sk, .82)); }   // the one ear, at the back
      if (C.hairStyle === 'quiff') {
        // seen turned, not the front cap with its tuft: the lift overhangs the forehead, the crown slopes down to the back
        // of the skull, and the hairline runs from the nape round the ear to a sideburn and up the temple
        cel(QUIFF_TQ, C.hair, 8);
        fill('M 58 -992 C 32 -1001 -8 -997 -40 -980 C -12 -987 22 -987 52 -978 Z', lt(C.hair, .22));   // one sheen streak, along the sweep
      } else if (C.hairStyle === 'bun') {
        cel(BUN_CAP, C.hair, 8);
        fill('M 44 -980 C 16 -1000 -18 -1001 -46 -986 C -20 -991 10 -988 36 -970 Z', lt(C.hair, .2));   // pulled back toward the bun
      } else if (C.hairStyle === 'bob') {   // its own turned shape, not the bun cap: one mass from the fringe over the brows,
        // round the back of the skull and down to the jaw, its front edge framing the near cheek (the ear is under it)
        cel(BOB_TQ, C.hair, 8);
        fill('M -20 -998 C 10 -1004 40 -996 58 -978 C 30 -986 0 -988 -20 -984 Z', lt(C.hair, .2));
      } else if (C.hairStyle === 'hat') {
        fill('M -78 -930 C -82 -900 -76 -880 -66 -868 C -56 -880 -50 -900 -46 -920 Z', C.hair);
        const dome = 'M -86 -944 C -88 -1010 72 -1022 78 -948 Z', hc = C.hat || '#ffd23f';
        cel(dome, hc, 10, .85);
        ctx.save(); ctx.beginPath(); trace(dome); ctx.clip(); fill('M -10 -1030 L 30 -1030 L 26 -948 L -8 -948 Z', lt(hc, .3)); ctx.restore();   // ridge
        fill('M -98 -952 L 104 -952 C 108 -940 102 -932 94 -932 L -92 -932 C -100 -936 -102 -944 -98 -952 Z', dk(hc, .9));
      }
      const bc = C.hairStyle === 'hat' ? (C.stache || dk(C.hair, .6)) : dk(C.hair, .8), up = o.brow === 'up' ? -8 : 0;
      if (o.brow === 'worry') { stroke('M 22 -914 L 48 -922', bc, 8); stroke('M 62 -922 L 76 -916', bc, 7); }
      else { stroke(`M 22 ${-918 + up} Q 36 ${-926 + up} 50 ${-920 + up}`, bc, 8); stroke(`M 62 ${-921 + up} Q 70 ${-925 + up} 77 ${-920 + up}`, bc, 6); }
      const ink = '#20182c', es = dots ? 1.5 : 1;   // the near eye full, the far one narrow by the nose
      const lx = o.look || 0, ly = o.lookY || 0;     // pupils: the near eye moves the full offset, the far eye .6 of it
      if (closed) { stroke('M 30 -896 L 46 -896', ink, 5); stroke('M 66 -896 L 74 -896', ink, 4); }
      else if (eyeMode === 'happy') { stroke('M 28 -892 Q 38 -906 48 -892', ink, 5.5); stroke('M 64 -893 Q 70 -903 76 -893', ink, 4.5); }
      else if (eyeMode === 'wide') {   // the pupil moves inside the white
        fill(ell(38, -896, 10, 12), '#fff'); fill(ell(38 + clamp(3 + lx * .6, -3, 3), -896 + clamp(ly * .8, -4, 4), 6, 7), ink);
        fill(ell(71, -896, 6, 11), '#fff'); fill(ell(71 + clamp(2 + lx * .4, -2, 2), -896 + clamp(ly * .6, -4, 4), 4, 6), ink);
      } else { fill(ell(38 + lx, -896 + ly, 6.5 * es, 8.5 * es), ink); fill(ell(71 + lx * .6, -896 + ly * .6, 4.5 * es, 8 * es), ink); if (dots) fill(ell(40 + lx, -900 + ly, 2.6, 2.6), '#fff'); }
      const blush = cheeks(C);   // the near cheek under the eye, a sliver of the far one by the nose
      if (blush) { fill(ell(22, -866, 15, 10), blush); fill(ell(60, -863, 6, 7), blush); }
      if (C.stache) fill('M 46 -846 C 58 -856 76 -856 90 -848 C 86 -836 74 -836 66 -840 C 58 -834 48 -836 46 -846 Z', C.stache);
      const m = o.mouth || 'smile', mc = '#6b1f2b';
      if (m === 'grin' || m === 'talk') {
        const op = m === 'grin' ? 1 : .35 + .65 * Math.abs(Math.sin(t * 9));
        const d = `M 34 -846 L 76 -848 C 76 ${-848 + 30 * op} 64 ${-846 + 36 * op} 52 ${-846 + 34 * op} C 40 ${-846 + 32 * op} 34 ${-846 + 18 * op} 34 -846 Z`;
        ctx.save(); ctx.beginPath(); trace(d); ctx.clip(); fill(d, mc);
        fill('M 20 -852 L 90 -852 L 90 -840 L 20 -840 Z', '#fff'); fill(ell(54, -846 + 34 * op, 16, 9), '#d9566a'); ctx.restore();
      } else if (m === 'grit') {
        fill('M 28 -846 L 80 -848 C 82 -836 80 -824 76 -820 L 32 -818 C 28 -826 27 -836 28 -846 Z', mc);
        fill('M 32 -843 L 77 -844 L 75 -823 L 34 -821 Z', '#fff'); stroke('M 33 -832 L 76 -833', '#c9c4d0', 2.5);
        for (const x of [44, 55, 66]) stroke(`M ${x} -843 L ${x} -822`, '#c9c4d0', 2);
      } else if (m === 'o') fill(ell(56, -832, 10, 13), mc);
      else if (m === 'flat') stroke('M 42 -838 L 70 -839', mc, 6);
      else stroke('M 36 -842 Q 56 -828 74 -844', mc, 6);
      if (o.sweat) { const y = -930 + ((t * .9) % 1) * 40;
        fill(`M -46 ${y - 22} C -40 ${y - 8} -34 ${y} -40 ${y + 8} C -46 ${y + 12} -54 ${y + 6} -52 ${y} C -51 ${y - 6} -48 ${y - 12} -46 ${y - 22} Z`, '#8fd8e6'); }
    }

    // ---- the front view (since 2026-11-05): symmetric about x, no nose, two ears, the face straight on ----
    function legsF(C) {
      const leg = 'M -34 -530 L 34 -530 C 35 -400 31 -200 28 -36 L -28 -36 C -31 -200 -35 -400 -34 -530 Z';
      for (const side of [-1, 1]) {
        ctx.save(); ctx.translate(side * 42, 0);
        cel(leg, C.pants, 10);
        if (C.look === 'tee') { fill('M -31 -300 L 31 -300 C 31 -200 29 -110 28 -36 L -28 -36 C -29 -110 -31 -200 -31 -300 Z', C.skin); fill('M -36 -318 L 36 -318 L 35 -296 L -35 -296 Z', dk(C.pants, .85)); }
        else stroke('M 0 -500 C 1 -360 1 -210 0 -60', lt(C.pants, .12), 3);
        fill('M -46 -8 C -46 -30 -30 -42 0 -42 C 30 -42 46 -30 46 -8 L 46 0 L -46 0 Z', C.shoe);
        ctx.restore();
      }
    }
    const BODY_F = 'M -114 -760 C -114 -796 -90 -812 -60 -814 L 60 -814 C 90 -812 114 -796 114 -760 C 108 -690 102 -620 102 -560 C 103 -520 106 -490 106 -470 C 40 -456 -40 -456 -106 -470 C -106 -490 -103 -520 -102 -560 C -102 -620 -108 -690 -114 -760 Z';
    const DRESS_F = 'M -114 -760 C -114 -796 -90 -812 -60 -814 L 60 -814 C 90 -812 114 -796 114 -760 C 108 -690 102 -620 102 -580 C 118 -500 146 -400 154 -300 L -154 -300 C -146 -400 -118 -500 -102 -580 C -102 -620 -108 -690 -114 -760 Z';
    function torsoF(C, br, belly) {
      ctx.save(); ctx.translate(0, br); ctx.scale(C.narrow || 1, 1);
      const crew = col => fill('M -44 -816 C -24 -790 24 -790 44 -816 L 50 -808 C 28 -778 -28 -778 -50 -808 Z', col);
      const collar = col => fill('M -46 -818 C -28 -800 -10 -796 0 -796 C 10 -796 28 -800 46 -818 L 36 -784 L 0 -800 L -36 -784 Z', col);   // two collar points
      if (C.look === 'dress') { cel(DRESS_F, C.top, 16, .86); crew(lt(C.top, .35)); }
      else if (C.look === 'coat') {
        cel(BODY_F, C.top, 16, .86);
        fill('M -22 -814 L 22 -814 L 16 -470 L -16 -470 Z', C.shirt); collar(dk(C.shirt, .9));
        { const [la, lb] = pair('#d9d4c8', '#e6e2d8'); fill('M -22 -814 L -42 -760 L -8 -640 Z', la); fill('M 22 -814 L 42 -760 L 8 -640 Z', lb); }   // lapels
        fill('M 44 -560 L 84 -560 L 84 -500 L 46 -500 Z', '#e2ded3');                                           // breast pocket
      } else if (C.look === 'suit') {
        cel(BODY_F, C.top, 16);
        fill('M -34 -816 L 34 -816 L 0 -640 Z', C.shirt); collar('#f2f2f5');
        if (C.tie) { fill('M -8 -806 L 8 -806 L 12 -690 L 0 -664 L -12 -690 Z', C.tie); fill('M -10 -812 L 10 -812 L 6 -796 L -6 -796 Z', dk(C.tie, .8)); }
        { const [la, lb] = pair(.72, .86); fill('M -34 -816 L -54 -770 L -30 -760 L 0 -640 Z', dk(C.top, la)); fill('M 34 -816 L 54 -770 L 30 -760 L 0 -640 Z', dk(C.top, lb)); }   // lapels
        stroke('M 0 -640 C 0 -560 0 -500 0 -462', dk(C.top, .7), 4);
        fill(ell(8, -560, 6, 6), dk(C.top, .6)); fill(ell(8, -520, 6, 6), dk(C.top, .6));
      } else {
        cel(BODY_F, C.top, 16);
        if (C.look === 'vest') {
          collar(dk(C.top, .86)); fill('M -14 -812 L 14 -812 L 10 -770 L -10 -770 Z', dk(C.top, .78));   // polo placket
          const [va, vb] = pair(.82, .9);
          cel('M -112 -770 C -108 -790 -80 -800 -62 -800 L -46 -470 L -108 -478 Z', C.vest, 10, va);
          cel('M 112 -770 C 108 -790 80 -800 62 -800 L 46 -470 L 108 -478 Z', C.vest, 10, vb);
          for (const y of [-640, -560]) { fill(`M -108 ${y} L -46 ${y - 4} L -46 ${y + 14} L -108 ${y + 18} Z`, '#e6e9ef'); fill(`M 46 ${y - 4} L 108 ${y} L 108 ${y + 18} L 46 ${y + 14} Z`, '#e6e9ef'); }
        } else if (C.look === 'shirt') crew(lt(C.top, .35));
        else crew(dk(C.top, .78));
      }
      if (belly) {   // a lighter disc low on the garment, as in the reference; kept inside a short garment
        if (C.look === 'dress') fill(ell(0, -500, 104, 92), dk(C.top, .93));
        else { ctx.save(); ctx.beginPath(); trace(BODY_F); ctx.clip(); fill(ell(0, -500, 104, 92), dk(C.top, .93)); ctx.restore(); }
      }
      ctx.restore();
    }
    const FACE_F = 'M 0 -992 C 52 -992 90 -956 90 -900 C 90 -846 56 -806 0 -806 C -56 -806 -90 -846 -90 -900 C -90 -956 -52 -992 0 -992 Z';
    function headF(C, o, t) {
      const sk = C.skin, eyeMode = o.eyes || 'open', closed = blinkOn(t, o.seed || 1) && eyeMode !== 'happy', dots = o.dotEyes !== false;
      if (C.hairStyle === 'bun') cel(ell(0, -986, 34, 30), C.hair, 6);
      if (C.hairStyle !== 'bob') for (const sd of [-1, 1]) { fill(ell(sd * 92, -890, 13, 20), sk); fill(ell(sd * 92, -888, 6, 11), dk(sk, .82)); }   // two ears
      fill(FACE_F, sk);
      if (C.hairStyle === 'quiff') {
        cel('M -90 -920 C -90 -980 -50 -1006 0 -1006 C 50 -1006 90 -980 90 -920 C 86 -932 70 -944 40 -944 C 16 -950 -20 -948 -46 -932 C -62 -920 -80 -916 -90 -920 Z', C.hair, 8);
        fill('M 10 -1002 C 50 -1016 84 -996 76 -960 C 60 -968 40 -966 24 -960 Z', C.hair);
        fill('M -40 -990 C -10 -1000 20 -998 40 -992 C 14 -990 -14 -986 -40 -976 Z', lt(C.hair, .22));
      } else if (C.hairStyle === 'bun') {
        cel('M -90 -916 C -90 -984 -46 -1006 0 -1006 C 46 -1006 90 -984 90 -916 C 80 -930 60 -940 40 -936 C 10 -948 -30 -946 -60 -930 C -72 -922 -82 -916 -90 -916 Z', C.hair, 8);
        fill('M -30 -996 C 0 -1002 30 -996 50 -980 C 24 -986 0 -988 -30 -982 Z', lt(C.hair, .2));
      } else if (C.hairStyle === 'bob') {   // one cap with both side masses hanging beside the face, over the ears
        cel('M -98 -830 C -102 -870 -100 -940 -94 -960 C -80 -1000 -40 -1006 0 -1006 C 40 -1006 80 -1000 94 -960 C 100 -940 102 -870 98 -830 C 90 -816 78 -816 72 -832 C 78 -870 76 -900 70 -920 C 60 -938 30 -944 0 -944 C -30 -944 -60 -938 -70 -920 C -76 -900 -78 -870 -72 -832 C -78 -816 -90 -816 -98 -830 Z', C.hair, 8);
        fill('M -40 -992 C -10 -1000 20 -998 44 -990 C 16 -988 -14 -984 -40 -976 Z', lt(C.hair, .2));
      } else if (C.hairStyle === 'hat') {
        for (const sd of [-1, 1]) fill(`M ${sd * 90} -930 C ${sd * 94} -900 ${sd * 90} -880 ${sd * 80} -868 C ${sd * 72} -880 ${sd * 66} -900 ${sd * 64} -920 Z`, C.hair);
        const dome = 'M -90 -940 C -92 -1020 92 -1020 90 -940 Z', hc = C.hat || '#ffd23f';
        cel(dome, hc, 10, .85);
        ctx.save(); ctx.beginPath(); trace(dome); ctx.clip(); fill('M -14 -1030 L 26 -1030 L 22 -940 L -10 -940 Z', lt(hc, .3)); ctx.restore();
        fill('M -104 -952 L 104 -952 C 108 -940 102 -932 94 -932 L -94 -932 C -102 -936 -108 -944 -104 -952 Z', dk(hc, .9));
      }
      const bc = C.hairStyle === 'hat' ? (C.stache || dk(C.hair, .6)) : dk(C.hair, .8), up = o.brow === 'up' ? -8 : 0;
      if (o.brow === 'worry') { stroke('M -58 -916 L -30 -924', bc, 8); stroke('M 30 -924 L 58 -916', bc, 8); }
      else for (const sd of [-1, 1]) stroke(`M ${sd * 58} ${-918 + up} Q ${sd * 44} ${-926 + up} ${sd * 30} ${-920 + up}`, bc, 8);
      const ink = '#20182c', es = dots ? 1.5 : 1, lx = o.look || 0, ly = o.lookY || 0;
      for (const sd of [-1, 1]) {
        if (closed) stroke(`M ${sd * 28} -896 L ${sd * 44} -896`, ink, 5);
        else if (eyeMode === 'happy') stroke(`M ${sd * 26} -892 Q ${sd * 36} -906 ${sd * 46} -892`, ink, 5.5);
        else if (eyeMode === 'wide') { fill(ell(sd * 36, -896, 10, 12), '#fff'); fill(ell(sd * 36 + clamp(2 + lx * .6, -4, 4), -896 + clamp(ly * .8, -4, 4), 6, 7), ink); }
        else { fill(ell(sd * 36 + lx, -896 + ly, 6.5 * es, 8.5 * es), ink); if (dots) fill(ell(sd * 36 + 2 + lx, -900 + ly, 2.6, 2.6), '#fff'); }
      }
      const blush = cheeks(C);
      if (blush) for (const sd of [-1, 1]) fill(ell(sd * 56, -862, 15, 10), blush);
      if (C.stache) fill('M -26 -852 C -12 -862 12 -862 26 -852 C 18 -840 8 -838 0 -844 C -8 -838 -18 -840 -26 -852 Z', C.stache);
      const m = o.mouth || 'smile', mc = '#6b1f2b';
      if (m === 'grin' || m === 'talk') {
        const op = m === 'grin' ? 1 : .35 + .65 * Math.abs(Math.sin(t * 9));
        const d = `M -22 -846 L 22 -846 C 24 ${-846 + 28 * op} 12 ${-846 + 32 * op} 0 ${-846 + 32 * op} C -12 ${-846 + 32 * op} -24 ${-846 + 28 * op} -22 -846 Z`;
        ctx.save(); ctx.beginPath(); trace(d); ctx.clip(); fill(d, mc);
        fill('M -30 -852 L 30 -852 L 30 -840 L -30 -840 Z', '#fff'); fill(ell(0, -846 + 30 * op, 16, 9), '#d9566a'); ctx.restore();
      } else if (m === 'grit') {
        fill('M -26 -846 L 26 -846 C 28 -834 26 -822 22 -818 L -22 -818 C -26 -822 -28 -834 -26 -846 Z', mc);
        fill('M -22 -843 L 22 -843 L 20 -821 L -20 -821 Z', '#fff'); stroke('M -21 -832 L 21 -832', '#c9c4d0', 2.5);
        for (const x of [-11, 0, 11]) stroke(`M ${x} -843 L ${x} -822`, '#c9c4d0', 2);
      } else if (m === 'o') fill(ell(0, -832, 10, 13), mc);
      else if (m === 'flat') stroke('M -14 -838 L 14 -838', mc, 6);
      else stroke('M -18 -842 Q 0 -826 18 -842', mc, 6);
      if (o.sweat) { const y = -930 + ((t * .9) % 1) * 40;
        fill(`M -74 ${y - 22} C -68 ${y - 8} -62 ${y} -68 ${y + 8} C -74 ${y + 12} -82 ${y + 6} -80 ${y} C -79 ${y - 6} -76 ${y - 12} -74 ${y - 22} Z`, '#8fd8e6'); }
    }

    function person(o, t) {
      const C = o.C || CAST.off, seed = o.seed || 1, hs = o.hs != null ? o.hs : 1.28, dir = o.dir || 1, s = o.s, front = o.view === 'front';
      const belly = o.belly != null ? o.belly : !!C.belly;
      const wa = o.walkAmt != null ? clamp(o.walkAmt, 0, 1) : 1, W = !front && o.walk != null && wa > 0 ? gait(o.walk, wa) : null, sl = Math.tan(o.slope || 0);
      const onGround = fn => { if (!sl) return fn(); ctx.save(); ctx.transform(1, -sl, 0, 1, 0, 0); fn(); ctx.restore(); };
      const br = W ? W.bob + Math.sin(t * 2.3 + seed) * 1.2 : Math.sin(t * 2.3 + seed) * 3.5, nod = (o.nod || 0) + .025 * Math.sin(t * 1.9 + seed * 1.7), nx = C.narrow || 1;
      curT = t; curSeed = seed; curLX = (o.light > 0 ? 1 : -1) * dir;   // world-fixed light: the mirror must not carry it
      ctx.save(); ctx.translate(o.x, o.y); ctx.scale(s * dir, s);
      if (o.ground !== false) onGround(() => fill(ell(front ? 0 : 10, -2, 150, 16), 'rgba(40,25,30,.16)'));
      // a walking arm with no target swings against its own leg (the near arm goes back as the near leg comes forward)
      const swing = (a, sx, sy, g) => a || !W ? a : { x: sx - Math.sin(g.th) * 300 + 20, y: sy + 330 - Math.abs(Math.sin(g.th)) * 40, bend: -1 };
      const headSpace = fn => { ctx.save(); ctx.translate(0, br - 812); ctx.rotate(nod); ctx.scale(hs, hs); ctx.translate(0, 812); fn(); ctx.restore(); };
      // the neck goes under the collar: narrow, skin, the top in the chin's shadow
      const neck = (nk, shade) => headSpace(() => { fill(nk, C.skin); ctx.save(); ctx.beginPath(); trace(nk); ctx.clip(); fill(shade, dk(C.skin, .8)); ctx.restore(); });
      let jn, jf;
      if (front) {
        legsF(C);
        neck('M -18 -760 L 18 -760 L 18 -852 L -18 -852 Z', 'M -60 -900 L 60 -900 L 60 -826 C 30 -812 -30 -812 -60 -826 Z');
        torsoF(C, br, belly);
        headSpace(() => headF(C, o, t));
        jf = arm(C, -104 * nx, -770 + br, o.armL, false, { side: -1 });
        jn = arm(C, 104 * nx, -770 + br, o.armR, false, { side: 1 });
      } else {
        jf = arm(C, 64 * nx, -772 + br, swing(o.armF, 64 * nx, -772 + br, W && W.far), true);
        if (W) onGround(() => { legW(C, W.far, true, W.hipY); legW(C, W.near, false, W.hipY); fill(cap(-22, W.hipY, 34, W.hipY, 47, 47), C.pants); });
        else { legs(C, true); legs(C, false); }
        neck('M -10 -760 L 30 -760 L 28 -852 L -8 -852 Z', 'M -40 -900 L 60 -900 L 60 -824 C 30 -812 0 -814 -40 -826 Z');
        torso(C, br, belly);
        headSpace(() => head(C, o, t));
        jn = arm(C, -58 * nx, -768 + br, swing(o.armN, -58 * nx, -768 + br, W && W.near), false);
      }
      ctx.restore(); curLX = 1;
      const w = (x, y, fa) => ({ x: o.x + dir * s * x, y: o.y + s * y, a: Math.atan2(Math.sin(fa), dir * Math.cos(fa)) });
      const top = o.y + s * (br - 812 - hs * ((TOP[C.hairStyle] || TOP.quiff) - 812));
      const out = { top, nearHand: w(jn.hx, jn.hy, jn.fa), farHand: w(jf.hx, jf.hy, jf.fa) };
      if (front) { out.handR = out.nearHand; out.handL = out.farHand; }
      return out;
    }
    const api = { person, hand, fill, cel, stroke, ell, cap, ik, blinkOn, dk, lt, CAST };
    return api;
  }
  return { rig, CAST, TOP };
})();
