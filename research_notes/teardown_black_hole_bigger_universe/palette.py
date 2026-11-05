"""Colour stats of the episode body: per-second brightness/saturation/hue and a global k-means palette."""
import colorsys
import json
import subprocess
import sys

import numpy as np

video, out, t0, t1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
W, H = 160, 90
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", video, "-vf", f"fps=1,scale={W}:{H}",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32) / 255

per_sec = []
for i, f in enumerate(frames):
    mx, mn = f.max(-1), f.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    lum = (0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2])
    per_sec.append({"t": round(t0 + i, 1), "lum": round(float(lum.mean()), 3), "sat": round(float(sat.mean()), 3),
                    "dark_px": round(float((lum < 0.15).mean()), 3)})

# k-means palette on a pixel sample
px = frames.reshape(-1, 3)
rng = np.random.default_rng(0)
px = px[rng.choice(len(px), 60000, replace=False)]
k = 14
c = px[rng.choice(len(px), k, replace=False)]
for _ in range(25):
    lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
    c = np.array([px[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
share = np.bincount(lab, minlength=k) / len(lab)
pal = []
for j in np.argsort(-share):
    r, g, b = c[j]
    h, l, s = colorsys.rgb_to_hls(float(r), float(g), float(b))
    pal.append({"hex": "#%02x%02x%02x" % tuple(int(v * 255) for v in c[j]), "share": round(float(share[j]), 3),
                "hue": round(h * 360), "light": round(l, 2), "sat": round(s, 2)})

lums = np.array([p["lum"] for p in per_sec]); sats = np.array([p["sat"] for p in per_sec])
summary = {"frames": len(per_sec), "lum_mean": round(float(lums.mean()), 3), "lum_p10": round(float(np.percentile(lums, 10)), 3),
           "lum_p90": round(float(np.percentile(lums, 90)), 3), "sat_mean": round(float(sats.mean()), 3),
           "bright_moments": [p["t"] for p in per_sec if p["lum"] > 0.45]}
json.dump({"summary": summary, "palette": pal, "per_sec": per_sec}, open(out, "w"), indent=1)
print(json.dumps(summary, indent=1)); print(json.dumps(pal, indent=0))
