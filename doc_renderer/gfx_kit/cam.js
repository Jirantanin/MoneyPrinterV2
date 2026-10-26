// Camera module (LIBRARY.md "Camera"). Load after kit.js and motion.js. Pure in t.
//   camPath(keys, {shakes, drift}) -> t => {x, y, z, rot}
//     keys [{t, x, y, z, rot?, move}], sorted; the segment ending at a key uses that key's move:
//       push | pull | track | tilt | dive | whip   easeInOutCubic between the keys
//       punch                                     peak-energy spring that overshoots, landing exactly on the key
//       cut                                       holds the previous key, jumps at this key's t
//       hold                                      stays on the previous key (drift keeps it alive)
//     Zoom always interpolates in log space. During a hold and after the last key the camera drifts (zoom +drift per
//     second, a few px of slow wander) so it is never fully still; drift 0 turns that off.
//     shakes [{t0, amp = 14, decay = 9, hz = 7}] add damped kicks (an impact; at most CAM_RULES.maxShakesPerWorld).
//   camApply(cam, [{g, depth}])   depth 0 static, 1 the world, > 1 foreground (moves farther), < 1 far layers
//   screenScale(z)                'scale(1/z)' for a label hung on a world object, so its screen size stays constant
const CAM_RULES = { pullMinRatio: 3, punch: [.4, .6], pull: [2, 3], dive: [.8, 1.2], whip: .3, shake: [.3, .5], maxShakesPerWorld: 2 };
const CAM_EASED = ['push', 'pull', 'track', 'tilt', 'dive', 'whip'];

function camPath(keys, { shakes = [], drift = .015 } = {}) {
  for (const k of keys.slice(1)) if (![...CAM_EASED, 'punch', 'cut', 'hold'].includes(k.move)) throw new Error(`camPath: unknown move "${k.move}"`);
  const at = (k, e, a) => ({ x: lerp(a.x, k.x, e), y: lerp(a.y, k.y, e), z: a.z * Math.pow(k.z / a.z, e), rot: lerp(a.rot || 0, k.rot || 0, e) });
  const still = k => ({ x: k.x, y: k.y, z: k.z, rot: k.rot || 0 });
  const wander = (c, dt) => drift ? { ...c, z: c.z * (1 + drift * dt), x: c.x + 400 * drift * Math.sin(.37 * dt), y: c.y + 270 * drift * Math.sin(.29 * dt) } : c;
  const base = t => {
    if (t <= keys[0].t) return still(keys[0]);
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1], k = keys[i];
      if (t >= k.t) continue;
      const u = p(t, a.t, k.t);
      if (k.move === 'cut') return still(a);
      if (k.move === 'hold') return wander(still(a), t - a.t);
      if (k.move === 'punch') { const e = spring(u * .75, ENERGY.peak.zeta, ENERGY.peak.hz) * (1 - u ** 4) + u ** 4; return at(k, e, a); }
      return at(k, eio(u), a);
    }
    const last = keys[keys.length - 1];
    return wander(still(last), t - last.t);
  };
  return t => {
    const c = base(t);
    for (const { t0, amp = 14, decay = 9, hz = 7 } of shakes) { c.x += kick(t - t0, amp, decay, hz); c.y += kick(t - t0 + .05, amp * .6, decay, hz * 1.3); }
    return c;
  };
}

function camApply(cam, layers) {
  const f = v => (+v).toFixed(2);
  for (const { g, depth } of layers) {
    const z = Math.pow(cam.z, depth), cx = cam.x * depth + KW / 2 * (1 - depth), cy = cam.y * depth + KH / 2 * (1 - depth);
    g.setAttribute('transform', `translate(${KW / 2},${KH / 2}) rotate(${f((cam.rot || 0) * depth)}) scale(${z.toFixed(4)}) translate(${f(-cx)},${f(-cy)})`);
  }
}

const screenScale = z => `scale(${(1 / z).toFixed(4)})`;
