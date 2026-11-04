'use strict';
// Three-quarter people on a 2D canvas: the house people since 2026-11-04 (LIBRARY.md "Three-quarter people", นน picked T2
// from .mp/people_tis_20261104/). Construction learnt from The Infographics Show frames, our own cast and colours: an adult
// body with the head at 1/4 (hs 1.28 over the 1/5 TIS head), the head and body turned three-quarters, the nose sticking out
// past the face line, one ear at the back, dot eyes, short stroke brows, a D mouth with upper teeth, cuffs and collars, and
// one big shade plane per piece. Flat shapes, no outlines. Pure in t. Load before the page's own code, then bind it:
//   const { person, hand, fill, cel, stroke, ell, cap, CAST } = People34.rig(ctx);
//   person(o, t) -> { top, nearHand, farHand }   world px; top = the drawn head top (hair, bun or hat), for a "!" or a label
//     o.x, o.y      feet in world px          o.s     px per local unit (the figure is ~1000 units tall at hs 1)
//     o.dir         1 faces right, -1 left    o.C     a costume: one of CAST or your own (see CAST for the fields)
//     o.hs          head scale, default 1.28 (the house 1/4 head); 1 gives the TIS 1/5 head
//     o.dotEyes     default true (bigger dots with a catch light); false gives the small TIS eyes
//     o.eyes        open | happy (closed arcs) | wide       o.mouth  smile | talk (opens with t) | grin | grit | o
//     o.brow        calm | up | worry          o.sweat  a falling drop       o.nod  extra head tilt (rad)
//     o.armN/armF   near / far arm target {x, y (local units), hand: mitt|fingers, big, bend (1 | -1), hold(api)}
//                   hold() draws a prop in hand space (+x along the forearm) instead of the hand; the far arm is behind the body
//     o.ground      false drops the floor shadow (mid and close shots)      o.seed  blinks and breathing phase
// Local units: feet at y 0, shoulders near y -770, the neck at -812; facing +x before o.dir.
const People34 = (() => {
  const CAST = {
    // look: suit | coat | vest | tee; hairStyle: quiff | bun | hat; narrow < 1 slims the torso
    off: { skin: '#e9a77f', top: '#2e3c5a', shirt: '#ffffff', tie: '#e63946', pants: '#283149', hair: '#1d1a24', shoe: '#1d1a24', look: 'suit', hairStyle: 'quiff' },
    sci: { skin: '#f3c4a2', top: '#f4f1ea', shirt: '#2a9d8f', pants: '#3d405b', hair: '#2b1d2a', shoe: '#7a2e3a', look: 'coat', hairStyle: 'bun', narrow: .9 },
    wrk: { skin: '#b9774e', top: '#4c7fd1', vest: '#ff8a1f', pants: '#5b4a3a', hair: '#5a5560', shoe: '#2a1d18', look: 'vest', hairStyle: 'hat', stache: '#2a1d18' },
    kid: { skin: '#c98a5e', top: '#ffb703', pants: '#1d7bd8', hair: '#1d1a24', shoe: '#e63946', look: 'tee', hairStyle: 'quiff', narrow: .92 },
  };
  const TOP = { quiff: 1006, bun: 1016, hat: 1000 };   // local head top per hair style at hs 1 (checked by the test)

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
    // flat colour plus one big shade plane: the part of the shape not covered by itself moved toward the light (front, up)
    function cel(sh, col, d = 16, k = .8) {
      ctx.save(); ctx.beginPath(); trace(sh); ctx.clip();
      ctx.fillStyle = dk(col, k); ctx.fillRect(-4000, -4000, 8000, 8000);
      ctx.translate(d, -d * .5); fill(sh, col); ctx.restore();
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

    // ---- body ----
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
    function torso(C, br) {
      ctx.save(); ctx.translate(0, br); ctx.scale(C.narrow || 1, 1);
      // a shirt collar that wraps the neck; the chin, drawn after, sits in front of it
      const collar = (col, band = true) => {
        if (band) fill('M -14 -808 C -8 -832 42 -836 54 -816 L 50 -798 C 36 -814 6 -814 -8 -796 Z', col);
        fill('M 4 -812 L 26 -786 L 14 -778 Z M 50 -814 L 34 -786 L 46 -778 Z', col);
      };
      if (C.look === 'coat') {   // a slight waist, then the coat flares to the hem
        cel('M -16 -812 C -80 -810 -108 -790 -112 -748 C -106 -660 -98 -600 -100 -560 C -104 -480 -108 -420 -108 -360 C -30 -350 40 -350 108 -362 C 106 -430 100 -500 98 -560 C 98 -620 104 -680 106 -740 C 102 -790 80 -810 44 -814 Z', C.top, 18, .86);
        fill('M 4 -814 L 50 -816 L 40 -600 L 22 -600 Z', C.shirt);
        collar(dk(C.shirt, .9), false);
        fill('M 4 -814 L -8 -760 L 22 -600 Z', '#d9d4c8'); fill('M 50 -816 L 68 -770 L 40 -600 Z', '#e6e2d8');   // lapels
        fill('M 52 -560 L 92 -560 L 90 -500 L 54 -500 Z', '#e2ded3');                                            // breast pocket
        stroke('M 31 -600 C 30 -500 30 -430 29 -360', '#d9d4c8', 4);                                             // the front edge
      } else if (C.look === 'suit') {
        cel('M -18 -814 C -86 -810 -112 -788 -114 -746 C -108 -660 -100 -610 -102 -560 C -104 -520 -106 -490 -106 -468 C -20 -452 50 -452 104 -470 C 102 -500 98 -530 98 -560 C 98 -620 104 -690 108 -742 C 104 -790 80 -810 46 -816 Z', C.top, 18);
        fill('M 0 -816 L 52 -818 L 34 -628 Z', C.shirt);
        collar('#f2f2f5');
        if (C.tie) { fill('M 18 -806 L 34 -806 L 40 -690 L 28 -664 L 16 -690 Z', C.tie); fill('M 16 -812 L 36 -812 L 32 -796 L 20 -796 Z', dk(C.tie, .8)); }
        fill('M 0 -816 L -14 -770 L 6 -760 L 32 -628 Z', dk(C.top, .72)); fill('M 52 -818 L 70 -774 L 56 -764 L 34 -628 Z', dk(C.top, .86));   // lapels
        stroke('M 33 -628 C 32 -560 32 -500 30 -462', dk(C.top, .7), 4);                                                                       // the front edge
        fill(ell(40, -560, 6, 6), dk(C.top, .6)); fill(ell(41, -520, 6, 6), dk(C.top, .6));
      } else {
        cel('M -18 -812 C -84 -810 -110 -790 -112 -748 C -106 -660 -100 -600 -102 -560 C -103 -520 -104 -490 -104 -470 C -20 -456 50 -456 104 -472 C 102 -500 100 -530 100 -560 C 100 -620 104 -690 106 -742 C 102 -790 80 -810 46 -814 Z', C.top, 16);
        if (C.look === 'vest') {
          collar(dk(C.top, .86));
          fill('M 6 -812 L 48 -814 L 36 -770 L 18 -770 Z', dk(C.top, .78));   // polo placket
          cel('M -104 -770 C -100 -790 -70 -800 -52 -800 L -40 -470 L -104 -478 Z', C.vest, 10, .82);
          cel('M 40 -804 C 70 -800 100 -790 106 -760 L 104 -480 L 54 -470 Z', C.vest, 10, .9);
          for (const y of [-640, -560]) { fill(`M -104 ${y} L -40 ${y - 4} L -40 ${y + 14} L -104 ${y + 18} Z`, '#e6e9ef'); fill(`M 52 ${y - 4} L 105 ${y} L 105 ${y + 18} L 52 ${y + 14} Z`, '#e6e9ef'); }
        } else fill('M 0 -814 C 14 -796 40 -796 54 -816 L 50 -820 C 38 -806 16 -806 4 -818 Z', dk(C.top, .78));   // tee neckline
      }
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
    function arm(C, sx, sy, a, far) {
      // a hanging arm sways a little and sits just behind the body line, so the hand reads clear of the hip
      const sway = Math.sin(curT * 1.6 + curSeed + (far ? 1.3 : 0)) * 7;
      // (the far hand hangs a little forward of the thigh so it reads as a hand, not a stub poking out)
      const tx = a && a.x != null ? a.x : sx + (far ? 22 : -14) + sway, ty = a && a.y != null ? a.y : sy + 340;
      const j = ik(sx, sy, tx, ty, a && a.bend != null ? a.bend : -1, 185, 170);
      const sl = dk(C.top, far ? .78 : 1), skin = dk(C.skin, far ? .85 : 1);
      fill(cap(sx, sy, j.ex, j.ey, 34, 29), sl);
      if (C.look === 'suit' || C.look === 'coat') {
        fill(cap(j.ex, j.ey, j.hx, j.hy, 29, 24), sl);
        fill(cap(lerp(j.ex, j.hx, .9), lerp(j.ey, j.hy, .9), j.hx, j.hy, 25, 25), C.look === 'suit' ? '#f2f2f5' : dk(sl, .92));   // cuff
      } else {
        const mx = lerp(sx, j.ex, .55), my = lerp(sy, j.ey, .55);
        fill(cap(sx, sy, mx, my, 36, 33), sl);   // short sleeve over the upper arm
        fill(cap(mx, my, j.ex, j.ey, 25, 23), skin); fill(cap(j.ex, j.ey, j.hx, j.hy, 23, 20), skin);
      }
      ctx.save(); ctx.translate(j.hx, j.hy); ctx.rotate(j.fa);
      if (a && a.hold) a.hold(api); else hand((a && a.hand) || 'mitt', skin, a && a.big ? 64 : 52);
      ctx.restore();
      return j;
    }

    // ---- head, facing +x ----
    const FACE = 'M 28 -806 C 0 -808 -30 -820 -48 -846 C -70 -870 -80 -905 -74 -935 C -66 -970 -30 -990 5 -990 C 40 -990 62 -968 66 -935 L 68 -906 C 74 -896 92 -880 92 -868 C 92 -859 82 -856 72 -856 C 74 -846 76 -836 70 -826 C 64 -812 48 -806 28 -806 Z';
    function head(C, o, t) {
      const sk = C.skin, eyeMode = o.eyes || 'open', closed = blinkOn(t, o.seed || 1) && eyeMode !== 'happy', dots = o.dotEyes !== false;
      if (C.hairStyle === 'bun') cel(ell(-62, -982, 36, 34), C.hair, 6);
      ctx.save(); ctx.beginPath(); trace(FACE); ctx.clip(); fill(FACE, sk);
      fill('M -120 -1000 L -38 -1000 C -60 -930 -50 -860 -6 -800 L -120 -800 Z', dk(sk, .92)); ctx.restore();   // back of the head
      fill(ell(-26, -886, 14, 21), sk); fill(ell(-24, -884, 7, 12), dk(sk, .82));   // the one ear, at the back
      if (C.hairStyle === 'quiff') {
        cel('M 64 -946 C 64 -980 40 -1004 0 -1006 C -50 -1004 -84 -976 -84 -930 C -84 -905 -78 -885 -66 -870 C -56 -880 -48 -900 -44 -918 L -24 -912 C -14 -932 10 -948 40 -944 C 50 -948 58 -950 64 -946 Z', C.hair, 8);
        fill('M 20 -1002 C 56 -1012 84 -990 76 -958 C 68 -966 54 -966 40 -960 Z', C.hair);
        fill('M -40 -990 C -10 -1000 20 -998 40 -992 C 14 -990 -14 -986 -40 -976 Z', lt(C.hair, .22));   // one sheen streak
      } else if (C.hairStyle === 'bun') {
        cel('M 68 -940 C 64 -988 26 -1008 -10 -1006 C -56 -1002 -86 -968 -84 -922 C -82 -884 -72 -862 -56 -852 C -52 -880 -46 -904 -32 -914 C -6 -930 30 -930 48 -948 C 56 -944 62 -940 68 -940 Z', C.hair, 8);
        fill('M -20 -998 C 10 -1004 40 -996 58 -978 C 30 -986 0 -988 -20 -984 Z', lt(C.hair, .2));      } else if (C.hairStyle === 'hat') {
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
      if (closed) { stroke('M 30 -896 L 46 -896', ink, 5); stroke('M 66 -896 L 74 -896', ink, 4); }
      else if (eyeMode === 'happy') { stroke('M 28 -892 Q 38 -906 48 -892', ink, 5.5); stroke('M 64 -893 Q 70 -903 76 -893', ink, 4.5); }
      else if (eyeMode === 'wide') { fill(ell(38, -896, 10, 12), '#fff'); fill(ell(41, -896, 6, 7), ink); fill(ell(71, -896, 6, 11), '#fff'); fill(ell(73, -896, 4, 6), ink); }
      else { fill(ell(38, -896, 6.5 * es, 8.5 * es), ink); fill(ell(71, -896, 4.5 * es, 8 * es), ink); if (dots) fill(ell(40, -900, 2.6, 2.6), '#fff'); }
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
      else stroke('M 36 -842 Q 56 -828 74 -844', mc, 6);
      if (o.sweat) { const y = -930 + ((t * .9) % 1) * 40;
        fill(`M -46 ${y - 22} C -40 ${y - 8} -34 ${y} -40 ${y + 8} C -46 ${y + 12} -54 ${y + 6} -52 ${y} C -51 ${y - 6} -48 ${y - 12} -46 ${y - 22} Z`, '#8fd8e6'); }
    }

    function person(o, t) {
      const C = o.C || CAST.off, seed = o.seed || 1, hs = o.hs != null ? o.hs : 1.28, dir = o.dir || 1, s = o.s;
      const br = Math.sin(t * 2.3 + seed) * 3.5, nod = (o.nod || 0) + .025 * Math.sin(t * 1.9 + seed * 1.7), nx = C.narrow || 1;
      curT = t; curSeed = seed;
      ctx.save(); ctx.translate(o.x, o.y); ctx.scale(s * dir, s);
      if (o.ground !== false) fill(ell(10, -2, 150, 16), 'rgba(40,25,30,.16)');
      const jf = arm(C, 64 * nx, -772 + br, o.armF, true);
      legs(C, true); legs(C, false);
      const headSpace = fn => { ctx.save(); ctx.translate(0, br - 812); ctx.rotate(nod); ctx.scale(hs, hs); ctx.translate(0, 812); fn(); ctx.restore(); };
      headSpace(() => {   // the neck goes under the collar: narrow, skin, the top in the chin's shadow
        const nk = 'M -10 -760 L 30 -760 L 28 -852 L -8 -852 Z';
        fill(nk, C.skin); ctx.save(); ctx.beginPath(); trace(nk); ctx.clip(); fill('M -40 -900 L 60 -900 L 60 -824 C 30 -812 0 -814 -40 -826 Z', dk(C.skin, .8)); ctx.restore();
      });
      torso(C, br);
      headSpace(() => head(C, o, t));
      const jn = arm(C, -58 * nx, -768 + br, o.armN, false);
      ctx.restore();
      const w = (x, y) => ({ x: o.x + dir * s * x, y: o.y + s * y });
      return { top: o.y + s * (br - 812 - hs * ((TOP[C.hairStyle] || TOP.quiff) - 812)), nearHand: w(jn.hx, jn.hy), farHand: w(jf.hx, jf.hy) };
    }
    const api = { person, hand, fill, cel, stroke, ell, cap, ik, blinkOn, dk, lt, CAST };
    return api;
  }
  return { rig, CAST, TOP };
})();
