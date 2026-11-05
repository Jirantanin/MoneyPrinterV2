"""Contact sheets every 0.5 s with the words spoken around each frame, plus an image-change curve.

word_sheets.py <video> <words.json> <outdir> start-end [start-end ...]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

video, words_path, outdir, ranges = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
os.makedirs(outdir, exist_ok=True)
words = json.load(open(words_path, encoding="utf-8"))
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
W, H, COLS, ROWS = 384, 216, 5, 4


def grab(t0, t1, fps, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", video, "-vf",
                          f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


change = []
for r in ranges:
    t0, t1 = (float(x) for x in r.split("-"))
    frames = grab(t0, t1, 2, W, H)
    per = COLS * ROWS
    for s in range(0, len(frames), per):
        sheet = Image.new("RGB", (COLS * W, ROWS * (H + 40)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(frames[s:s + per]):
            t = t0 + (s + i) / 2
            x, y = (i % COLS) * W, (i // COLS) * (H + 40)
            sheet.paste(Image.fromarray(f), (x, y))
            said = " ".join(w["w"] for w in words if t - 0.5 <= w["t"] < t + 0.5)
            m, sec = divmod(t, 60)
            d.rectangle([x, y, x + 62, y + 18], fill=(0, 0, 0))
            d.text((x + 3, y + 1), f"{int(m)}:{sec:04.1f}", font=font, fill=(255, 230, 0))
            d.text((x + 3, y + H + 2), said[:48], font=font, fill=(255, 255, 255))
            d.text((x + 3, y + H + 20), said[48:96], font=font, fill=(255, 255, 255))
        sheet.save(os.path.join(outdir, f"w_{int(t0):03d}_{s // per:02d}.jpg"), quality=85)
    # image change every 0.1 s (mean abs diff on small frames)
    small = grab(t0, t1, 10, 96, 54).astype(np.int16)
    diff = np.abs(np.diff(small, axis=0)).mean(axis=(1, 2, 3))
    change += [{"t": round(t0 + (i + 1) / 10, 1), "d": round(float(v), 2)} for i, v in enumerate(diff)]

# image events = local peaks of change; pair each with the nearest word onset
d = np.array([c["d"] for c in change])
thr = max(np.percentile(d, 85), 2.0)
events = [change[i]["t"] for i in range(1, len(d) - 1) if d[i] >= thr and d[i] >= d[i - 1] and d[i] >= d[i + 1]]
merged = []
for t in events:
    if not merged or t - merged[-1] > 0.6:
        merged.append(t)
lags = []
for t in merged:
    near = min(words, key=lambda w: abs(w["t"] - t))
    lags.append({"event": t, "word": near["w"], "word_t": near["t"], "lag": round(t - near["t"], 2)})
json.dump({"change": change, "events": lags}, open(os.path.join(outdir, "image_events.json"), "w"), indent=0)
la = np.array([l["lag"] for l in lags])
spans = sum(float(r.split("-")[1]) - float(r.split("-")[0]) for r in ranges)
print(f"{len(merged)} image events in {spans:.0f} s = one per {spans / len(merged):.1f} s")
print(f"lag image - nearest word onset: median {np.median(la):+.2f}s, p25 {np.percentile(la, 25):+.2f}, p75 {np.percentile(la, 75):+.2f}")
print(f"image before word: {(la < -0.1).mean():.0%}, within 0.1s: {(abs(la) <= 0.1).mean():.0%}, after: {(la > 0.1).mean():.0%}")
