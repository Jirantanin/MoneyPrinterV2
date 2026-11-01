"""Colour QC of a rendered video against the house colour rules (src/producer_palette_qc.py).

  python scripts/palette_qc.py <video.mp4> [--from 10] [--to 600] [--skip 120-135 --skip 300-310]

--skip leaves out real media (photos, footage) whose colours are not ours. Exit code 1 when a rule fails.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from producer_palette_qc import measure, problems  # noqa: E402

W, H = 160, 90


def read_frames(video: str, t0: float, t1: float | None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t0)] + (["-to", str(t1)] if t1 else []) + [
        "-i", video, "-vf", f"fps=1,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32) / 255


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--skip", action="append", default=[], help="start-end seconds (video time) to leave out")
    a = ap.parse_args()
    skip = [tuple(float(x) - a.t0 for x in s.split("-")) for s in a.skip]
    m = measure(read_frames(a.video, a.t0, a.t1), skip)
    found = problems(m)
    print(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()}))
    print("\n".join(found) if found else "colour OK")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
