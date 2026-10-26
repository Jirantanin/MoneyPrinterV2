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
                 phrase_time: float | None = None, start: int = 0, snap: float = .15, min_match: float = .6) -> dict:
    """When the trigger word starts: {"trigger", "time", "method": word | phrase | unknown, "confidence", "index",
    "ambiguous"}.

    Only occurrences at or after squashed index `start` count (beat sheets pass the previous match, so triggers land in
    order). When the trigger occurs more than once, the occurrence nearest `phrase_time` wins; with no phrase time and no
    `start`, the choice is ambiguous and no time is guessed. The time is the first heard character of the occurrence,
    snapped to the nearest speech onset within `snap` seconds. Below `min_match` of its characters heard, it falls back
    to `phrase_time` (or None). `index` is the chosen occurrence's squashed start, for chaining."""
    s, tr = squash(script), squash(trigger)
    occ = [i for i in range(start, len(s) - len(tr) + 1) if tr and s.startswith(tr, i)]
    known = _heard_times(script, words) if occ else {}
    cands, best = [], 0.0
    for i in occ:
        hit = [k for k in range(i, i + len(tr)) if k in known]
        conf = round(len(hit) / len(tr), 3)
        best = max(best, conf)
        if hit and conf >= min_match:
            cands.append((i, known[hit[0]], conf))
    out = {"trigger": trigger, "index": None, "ambiguous": len(occ) > 1}

    def fallback(conf: float) -> dict:
        if phrase_time is not None:
            return {**out, "time": phrase_time, "method": "phrase", "confidence": conf}
        return {**out, "time": None, "method": "unknown", "confidence": conf}

    if not cands:
        return fallback(best)
    if len(occ) > 1 and phrase_time is not None:
        i, t, conf = min(cands, key=lambda c: abs(c[1] - phrase_time))
    elif len(occ) > 1 and start == 0:
        return fallback(best)
    else:
        i, t, conf = cands[0]
    near = [o for o in onsets if abs(o - t) <= snap]
    if near:
        t = min(near, key=lambda o: abs(o - t))
    return {**out, "time": round(t, 2), "method": "word", "confidence": conf, "index": i}
