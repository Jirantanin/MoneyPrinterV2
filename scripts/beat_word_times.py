"""Fill a beat sheet's trigger times from one scene's narration WAV (word level, Thai).

    python scripts/beat_word_times.py <scene.wav> <scene_script.txt> <world.beats.md> [--offset S] [--write]

Transcribes with faster-whisper large-v3 (language th, word timestamps, VAD, no initial prompt: a script prompt makes
Whisper recite it), finds each trigger in the script, and snaps its first heard character to a speech onset. A trigger
Whisper did not hear keeps the time already in the sheet (phrase level, from the speech map) and is marked "(phrase)".
Times in the sheet are world seconds: --offset is the scene's start inside the world, and only rows whose time falls
inside this scene (offset .. offset + the WAV length) are touched, so run it once per scene. Triggers are matched in
row order, so a word the script repeats gets the occurrence that follows the previous beat. --write updates in place.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_score import speech_onsets  # noqa: E402
from producer_word_times import squash, trigger_time  # noqa: E402


def transcribe(wav: str, model: str) -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language="th", beam_size=5, word_timestamps=True, vad_filter=True,
                           condition_on_previous_text=False)
    return [(w.word, w.start, w.end) for seg in segs for w in (seg.words or [])]


def wav_seconds(wav: str) -> float:
    import wave
    with wave.open(wav, "rb") as w:
        return w.getnframes() / w.getframerate()


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
    lo, hi = a.offset, a.offset + wav_seconds(a.wav)   # only this scene's rows; other scenes keep theirs
    in_beats, header_seen, start = False, False, 0
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
        if old is not None and not lo <= old <= hi:
            continue
        r = trigger_time(script, words, trig.strip('"“”'), onsets, start=start,
                         phrase_time=None if old is None else round(old - a.offset, 2))
        if r["method"] == "word":
            start = r["index"] + len(squash(trig.strip('"“”')))
        t = None if r["time"] is None else round(r["time"] + a.offset, 2)
        print(f'{trig}\t{r["method"]}\t{t}\tconfidence {r["confidence"]}')
        if r["method"] == "word":
            if old is not None and re.fullmatch(r"[\d.]+", cells[1]):   # an explicit peak moves with its beat
                cells[1] = f"{float(cells[1]) + t - old:.2f}"
            cells[0], cells[2] = f"{t:.2f}", trig
        else:
            cells[2] = f'{trig} ({r["method"]})'
        lines[i] = "| " + " | ".join(cells) + " |"
    if a.write:
        Path(a.beats).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
