"""Fill a beat sheet's trigger times from one scene's narration WAV (word level, Thai).

    python scripts/beat_word_times.py <scene.wav> <scene_script.txt> <world.beats.md> [--offset S] [--write]

Transcribes with faster-whisper large-v3 (language th, word timestamps, VAD, no initial prompt: a script prompt makes
Whisper recite it), finds each trigger in the script, and snaps its first heard character to a speech onset. A trigger
Whisper did not hear keeps the time already in the sheet (phrase level, from the speech map) and is marked "(phrase)".
--offset adds the scene's start inside the world; --write updates the sheet's time column in place.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_score import speech_onsets  # noqa: E402
from producer_word_times import trigger_time  # noqa: E402


def transcribe(wav: str, model: str) -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language="th", beam_size=5, word_timestamps=True, vad_filter=True,
                           condition_on_previous_text=False)
    return [(w.word, w.start, w.end) for seg in segs for w in (seg.words or [])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav"), ap.add_argument("script"), ap.add_argument("beats")
    ap.add_argument("--offset", type=float, default=0.0, help="the scene's start inside the world, seconds")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--write", action="store_true", help="update the time column in place")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # Thai triggers on a cp874 console
    script = Path(a.script).read_text(encoding="utf-8")
    words, onsets = transcribe(a.wav, a.model), speech_onsets(a.wav)
    lines = Path(a.beats).read_text(encoding="utf-8").splitlines()
    in_beats, header_seen = False, False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            in_beats = line.strip() == "## BEATS"
            continue
        if not (in_beats and line.startswith("|")):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not header_seen or set(cells[0]) <= set("-: "):
            header_seen = True
            continue
        trig = re.sub(r'\s*\((word|phrase|unknown)\)$', "", cells[2])
        old = float(cells[0]) if re.fullmatch(r"[\d.]+", cells[0]) else None
        r = trigger_time(script, words, trig.strip('"“”'), onsets,
                         phrase_time=None if old is None else round(old - a.offset, 2))
        t = None if r["time"] is None else round(r["time"] + a.offset, 2)
        print(f'{trig}\t{r["method"]}\t{t}\tconfidence {r["confidence"]}')
        if r["method"] == "word":
            cells[0], cells[2] = f"{t:.2f}", trig
        else:
            cells[2] = f'{trig} ({r["method"]})'
        lines[i] = "| " + " | ".join(cells) + " |"
    if a.write:
        Path(a.beats).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
