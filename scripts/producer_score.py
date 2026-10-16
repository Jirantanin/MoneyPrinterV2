"""Composed score tools for a Producer Mode episode (see src/producer_score.py).

  python scripts/producer_score.py onsets --episode <dir>
      writes <dir>/score/onsets.json from merged_audio.wav (speech onsets after pauses)
  python scripts/producer_score.py render --episode <dir> [--cues score/score_cues.json] [--target-lufs -14.8]
      renders the cue sheet to <dir>/score/score_bed.wav, loudness-matched for the -18 dB bed chain

Use the bed by adding to producer_plan.json:
  "render_settings": {"background_bed": {"path": "score/score_bed.wav", "volume_db": -18.0, "stereo": true}}
The score is never heard by the tool; a person must listen before render consent.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_score import render_score, speech_onsets, write_wav  # noqa: E402


def _lufs(path: Path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def cmd_onsets(episode: Path) -> None:
    onsets = speech_onsets(episode / "merged_audio.wav")
    (episode / "score").mkdir(exist_ok=True)
    out = episode / "score" / "onsets.json"
    out.write_text(json.dumps([{"start": t} for t in onsets]), encoding="utf-8")
    print(f"[OK] {len(onsets)} onsets -> {out}")


def cmd_render(episode: Path, cues_rel: str, target_lufs: float) -> None:
    score_dir = episode / "score"
    cues = json.loads((episode / cues_rel).read_text(encoding="utf-8"))
    onsets = json.loads((score_dir / "onsets.json").read_text(encoding="utf-8"))
    raw = score_dir / "score_bed_raw.wav"
    write_wav(raw, render_score(cues, onsets))
    bed = score_dir / "score_bed.wav"
    gain = target_lufs - _lufs(raw)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.97:level=disabled", str(bed)], check=True)
    raw.unlink()
    print(f"[OK] {bed} ({_lufs(bed):.1f} LUFS)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("onsets"); o.add_argument("--episode", required=True, type=Path)
    r = sub.add_parser("render"); r.add_argument("--episode", required=True, type=Path)
    r.add_argument("--cues", default="score/score_cues.json")
    r.add_argument("--target-lufs", type=float, default=-14.8,
                   help="integrated loudness of the bed before the -18 dB chain (-14.8 matched the approved A/B sample)")
    a = ap.parse_args()
    if a.cmd == "onsets":
        cmd_onsets(a.episode)
    else:
        cmd_render(a.episode, a.cues, a.target_lufs)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    main()
