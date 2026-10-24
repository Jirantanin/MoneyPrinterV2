"""Scan recorded graphics for single-frame layer drops and white-outs before they reach an episode.

A flicker is a frame that differs from both neighbours while the neighbours match each other (the GPU flag
`PRODUCER_CHROME_GPU=1` occasionally drops a layer for one frame). A white-out is a run of more than
--max-bright frames whose whole-screen mean luma is above --bright (full-screen bloom should last 2-3 frames).

Usage (repo root):
  python scripts/gfx_flicker_scan.py <file.mp4 | folder> [...]   folders are searched for *.mp4
Exit code 1 when anything is found; re-record only the flagged scene without the GPU.
Designed flickers (a deliberate strobe) show up too: check the reported times against the scene.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

W, H = 96, 54


def fps_of(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    num, den = json.loads(out)["streams"][0]["r_frame_rate"].split("/")
    return float(num) / float(den or 1)


def frames_of(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def flicker_frames(x: np.ndarray, jump: float = 6.0) -> list[int]:
    if len(x) < 3:
        return []
    a = np.abs(x[1:-1] - x[:-2]).mean((1, 2))
    b = np.abs(x[2:] - x[1:-1]).mean((1, 2))
    c = np.abs(x[2:] - x[:-2]).mean((1, 2))
    return [int(i) + 1 for i in np.where((a > jump) & (b > jump) & (c < 0.5 * np.minimum(a, b)))[0]]


def bright_runs(x: np.ndarray, bright: float = 200.0, max_frames: int = 3) -> list[tuple[int, int]]:
    hot = x.mean((1, 2)) > bright
    runs, start = [], None
    for i, h in enumerate(list(hot) + [False]):
        if h and start is None:
            start = i
        elif not h and start is not None:
            if i - start > max_frames:
                runs.append((start, i - start))
            start = None
    return runs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--bright", type=float, default=200.0, help="whole-screen mean luma counted as white (0-255)")
    ap.add_argument("--max-bright", type=int, default=3, help="longest allowed run of white frames")
    args = ap.parse_args(argv)
    files: list[Path] = []
    for p in map(Path, args.paths):
        files += sorted(p.rglob("*.mp4")) if p.is_dir() else [p]
    found = 0
    for f in files:
        fps, x = fps_of(f), frames_of(f)
        flick = [round(i / fps, 2) for i in flicker_frames(x)]
        white = [(round(s / fps, 2), n) for s, n in bright_runs(x, args.bright, args.max_bright)]
        found += bool(flick or white)
        status = "OK" if not (flick or white) else "CHECK"
        print(f"{status} {f.as_posix()} {len(x)} frames"
              + (f"; flickers at {flick[:40]}" if flick else "")
              + (f"; white runs (s, frames) {white[:20]}" if white else ""))
    print(f"{found} of {len(files)} files need a look")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
