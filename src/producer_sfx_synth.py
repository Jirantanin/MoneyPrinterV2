"""Designed SFX primitives for explainer graphics and opening stings (pops, ticks, bells, whooshes, booms, alerts), numpy only.

Build one stem per graphic clip with Stem(seconds).add(sound, t, pan) at the clip's animation event
times, then write_wav(stem.finished()) and add it to sfx_cues.json at the slot start (about -21 dB).
Example: .mp/podcast_v2_firstborn-cosmic-silence_20261011_221035_revision_kurz-gfx_01/graphics_kurz/gfx_sfx.py
"""
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y


def pop(f0=420, f1=950, d=.16, lvl=1.0):
    t = tt(d)
    return np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * (t / d) ** .5) / SR) * np.exp(-t * 24) * lvl


def boing(up=True, lvl=1.0):
    t = tt(.35)
    f = (300 + 500 * (t / .35)) if up else (700 - 400 * (t / .35))
    return np.sin(2 * np.pi * np.cumsum(f * (1 + .05 * np.sin(2 * np.pi * 18 * t))) / SR) * np.exp(-t * 9) * lvl


def tick(lvl=.5, bright=3000):
    t = tt(.05)
    return (lp(rng.standard_normal(len(t)), bright) * 2 + np.sin(2 * np.pi * 1700 * t)) * np.exp(-t * 150) * lvl


def bell(m, d=1.6, lvl=.5):
    t = tt(d); f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 3)) * np.exp(-t * 3.2) * np.minimum(1, t / .005) * lvl


def pluck(m, d=.5, lvl=.5):
    t = tt(d); f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 8)) * np.exp(-t * 8) * np.minimum(1, t / .004) * lvl


def whoosh(d, lvl=.4, rise=True):
    t = tt(d)
    env = np.sin(np.pi * t / d) ** 2
    fc = (600 + 4000 * (t / d)) if rise else (4600 - 4000 * (t / d))
    x = rng.standard_normal(len(t))
    out = np.zeros_like(x); seg = 2400
    for i in range(0, len(x), seg):  # piecewise one-pole sweep
        out[i:i + seg] = lp(x[i:i + seg], float(fc[i]))
    return out * env * lvl * 1.6


def thump(lvl=.6):
    t = tt(.3)
    return np.sin(2 * np.pi * np.cumsum(60 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 14) * lvl


def boom(lvl=.7):
    t = tt(1.8)
    return (np.sin(2 * np.pi * np.cumsum(38 + 80 * np.exp(-t * 8)) / SR) * np.exp(-t * 2.4)
            + .4 * lp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 6)) * lvl


def sparkle(n=8, spread=.8, lvl=.25, base=(86, 88, 90, 93, 95, 98)):
    out = np.zeros(int((spread + 1.2) * SR))
    for _ in range(n):
        s = bell(int(rng.choice(base)), 1.0, lvl * rng.uniform(.5, 1))
        i = int(rng.uniform(0, spread) * SR); out[i:i + len(s)] += s[: len(out) - i]
    return out


def engine(d, lvl=.25):
    t = tt(d)
    x = lp(rng.standard_normal(len(t)), 900) * (1 + .3 * np.sin(2 * np.pi * 7 * t)) + .4 * np.sin(2 * np.pi * 110 * t)
    return x * np.minimum(1, t / .4) * np.minimum(1, (d - t) / .4) * lvl


def alert(f=1175.0, d=.24, lvl=.7):
    """Short warning beep ("แป๊น"): a soft square tone that droops slightly, like a console alarm, not a siren."""
    t = tt(d)
    ph = 2 * np.pi * np.cumsum(f * (1 - .03 * t / d)) / SR
    tone = .6 * np.tanh(3 * np.sin(ph)) + .4 * np.sin(2 * ph)
    env = np.minimum(1, t / .006) * np.exp(-t * 6) * np.minimum(1, (d - t) / .02)
    return lp(tone * env, 6000) * lvl


class Stem:
    """A stereo stem as long as a graphic clip; add() places a mono sound at t with constant or moving pan."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.buf = np.zeros((int(seconds * SR) + SR, 2))

    def add(self, sig, t, pan=0.0, pan_end=None):
        i = int(t * SR); s = sig[: max(0, len(self.buf) - i)]
        if pan_end is None:
            l, r = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
        else:
            pp = np.linspace(pan, pan_end, len(s)); l, r = np.sqrt((1 - pp) / 2), np.sqrt((1 + pp) / 2)
        self.buf[i:i + len(s), 0] += s * l; self.buf[i:i + len(s), 1] += s * r

    def finished(self, peak_db=-1.0):
        x = self.buf[: int(self.seconds * SR)]
        return x / max(1e-9, np.abs(x).max()) * 10 ** (peak_db / 20)


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
