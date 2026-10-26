// Look B, flat geometric (the space default since 2026-10-26; first drawn for dinosaurs-never-died, นน 2026-10-25).
// No outlines: every body is its fill plus a lighter band on the lit (upper-left) edge and a darker crescent on the far
// edge, both in the body's own hue. Load before cast.js; Y_init({style: 'B'}) calls FL_install(), which replaces Y_lit and
// litDisc, so scene code keeps its calls and loses its white rim lines. Nothing is replaced at load time.
(() => {
  const hex = c => { const m = /^#([0-9a-f]{6})$/i.exec(c || ''); return m ? [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16)) : null; };
  const mix = (c, to, k) => { const a = hex(c), b = hex(to); if (!a || !b) return null;
    return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * k).toString(16).padStart(2, '0')).join(''); };
  window.FL_tone = (c, light = '#ffffff', dark = '#140a30') => ({ light: mix(c, light, .28), dark: mix(c, dark, .38) });

  // Y_lit(parent, d, fill, {dx, dy, light, dark, band, shade}) -> body group (details drawn in it move with the surface)
  // light band = base minus the shape moved by a; dark crescent = shape(a) minus shape(a - b)
  const flatLit = (parent, d, fill, o = {}) => {
    const dx = o.dx ?? 6, dy = o.dy ?? 5, t = FL_tone(fill), light = o.light || t.light || '#ffffff', dark = o.dark || t.dark || '#000000';
    const a = [dx * (o.band ?? .7), dy * (o.band ?? .7)], b = [dx * (o.shade ?? 1.8), dy * (o.shade ?? 1.8)];
    const g = el('g', {}, parent);
    YP(d, light, g, (o.light || t.light) ? {} : { opacity: .3 });
    const g2 = el('g', { transform: `translate(${a[0].toFixed(1)},${a[1].toFixed(1)})` }, Y_clipTo(g, d)), c2 = Y_clipTo(g2, d);
    YP(d, dark, c2, (o.dark || t.dark) ? {} : { opacity: .35 });
    const body = el('g', { transform: `translate(${(-b[0]).toFixed(1)},${(-b[1]).toFixed(1)})` }, c2);
    YP(d, fill, body);
    return body;
  };

  // litDisc, same signature: a soft halo instead of the atmosphere ring, the shade crescents, and a thick soft highlight
  // curve on the lit side instead of the thin rim arcs
  const flatDisc = (parent, r, { stops, rot = 0, atmo = null, draw = null, halo = null } = {}) => {
    const f = v => (+v).toFixed(1), g = el('g', {}, parent);
    if (atmo || halo) YC(0, 0, r * 1.1, atmo || halo, g, { opacity: .28, filter: 'url(#glwBlurM)' });
    const b = el('g', { transform: `rotate(${rot})` }, g);
    YC(0, 0, r, Y_rgrad(stops, { cx: '64%', cy: '50%', r: '72%' }), b);
    const inside = Y_clipTo(b, `M${-r},0 A${r},${r} 0 1 0 ${r},0 A${r},${r} 0 1 0 ${-r},0Z`);
    if (draw) draw(el('g', {}, inside), r);
    // lit side is +x (the gradient's bright side): light crescent there, two shade crescents opposite
    const circ = (cx, rr) => `M${f(cx - rr)},0 A${f(rr)},${f(rr)} 0 1 0 ${f(cx + rr)},0 A${f(rr)},${f(rr)} 0 1 0 ${f(cx - rr)},0Z`;
    YP(circ(0, r) + circ(-r * .14, r), '#ffffff', inside, { opacity: .12, 'fill-rule': 'evenodd' });
    YP(`M0,${-r} A${r},${r} 0 0 0 0,${r} A${f(r * .82)},${r} 0 0 1 0,${-r}Z`, '#0a0620', inside, { opacity: .22 });
    YP(`M0,${-r} A${r},${r} 0 0 0 0,${r} A${f(r * .55)},${r} 0 0 1 0,${-r}Z`, '#0a0620', inside, { opacity: .42 });
    const arc = (rr, d0, d1) => { const q = d => [f(rr * Math.cos(d * Math.PI / 180)), f(rr * Math.sin(d * Math.PI / 180))], [x0, y0] = q(d0), [x1, y1] = q(d1);
      return `M${x0},${y0} A${f(rr)},${f(rr)} 0 0 1 ${x1},${y1}`; };
    YP(arc(r * .86, -48, 14), 'none', inside, { stroke: '#ffffff', 'stroke-width': f(Math.max(4, r * .07)), 'stroke-linecap': 'round', opacity: .3 });
    return { g, state({ x = 0, y = 0, s = 1, o = 1 } = {}) {
      set(g, { transform: `translate(${f(x)},${f(y)}) scale(${Math.max(0, s).toFixed(4)})` }); show(g, o); } };
  };
  window.FL_install = () => { window.Y_lit = flatLit; window.litDisc = flatDisc; };
  // round-capped stroke: the flat look's "thick line" (an object, never an outline)
  window.FL_rs = (d, c, w, p, x = {}) => YS(d, c, w, p, { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', ...x });
})();
