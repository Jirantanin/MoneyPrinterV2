"""Thai word timing against a script: per-character times from Whisper words, and trigger times for beat sheets.

Thai has no spaces between words, so a trigger is found in the squashed script and timed through the characters that
Whisper heard. A trigger whose characters were mostly not heard gets the phrase time instead, never a guessed time.
"""

from __future__ import annotations

import difflib
import re

import numpy as np


def squash(s: str) -> str:
    return re.sub(r"[\s?!.,]", "", s)


def _heard_times(script: str, words: list[tuple[str, float, float]]) -> dict[int, float]:
    """Script character index -> time, for the characters Whisper's words match."""
    heard, times = "", []
    for text, t0, t1 in words:
        w = squash(text)
        for k in range(len(w)):
            times.append(t0 + (t1 - t0) * k / max(1, len(w)))
        heard += w
    known: dict[int, float] = {}
    for a, b, size in difflib.SequenceMatcher(None, squash(script), heard, autojunk=False).get_matching_blocks():
        for k in range(size):
            known[a + k] = times[b + k]
    return known


def char_times(script: str, words: list[tuple[str, float, float]], dur: float) -> list[float]:
    """Time of each non-space script character, by aligning it to Whisper's word-timed characters."""
    s = squash(script)
    known = _heard_times(script, words)
    keys = sorted(known)
    if len(keys) < 2:
        return [dur * i / max(1, len(s)) for i in range(len(s))]
    return [float(np.interp(i, keys, [known[k] for k in keys])) for i in range(len(s))]


def trigger_time(script: str, words: list[tuple[str, float, float]], trigger: str, onsets: list[float], *,
                 phrase_time: float | None = None, snap: float = .15, min_match: float = .6) -> dict:
    """When the trigger word starts: {"trigger", "time", "method": word | phrase | unknown, "confidence"}.

    The time is the first heard character of the trigger, snapped to the nearest speech onset within `snap` seconds.
    Below `min_match` of the trigger's characters heard, it falls back to `phrase_time` (or None)."""
    s, tr = squash(script), squash(trigger)
    idx = s.find(tr) if tr else -1
    known = _heard_times(script, words) if idx >= 0 else {}
    hit = [i for i in range(idx, idx + len(tr)) if i in known] if idx >= 0 else []
    conf = round(len(hit) / len(tr), 3) if tr else 0.0
    if hit and conf >= min_match:
        t = known[hit[0]]
        near = [o for o in onsets if abs(o - t) <= snap]
        if near:
            t = min(near, key=lambda o: abs(o - t))
        return {"trigger": trigger, "time": round(t, 2), "method": "word", "confidence": conf}
    if phrase_time is not None:
        return {"trigger": trigger, "time": phrase_time, "method": "phrase", "confidence": conf}
    return {"trigger": trigger, "time": None, "method": "unknown", "confidence": conf}
