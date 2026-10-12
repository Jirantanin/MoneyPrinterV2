"""Composed episode score: a procedural ambient bed (numpy only) driven by a JSON cue sheet.

No melody: drone + additive pads following a per-section chord/mood cue sheet, sparse bell
shimmer, air noise, optional arpeggio, tension pulse, dissonant cluster, swells and booms.
Rendered in 10 s blocks so a full episode fits in memory. CLI: scripts/producer_score.py.

Cue sheet (score_cues.json):
  total_seconds, seed, snap_tolerance
  chords:  {name: [midi, ...]}            first note is the bass/drone
  regions: [{start, prog: [names], every, ramp, level, bright, pad, drone, air,
             shimmer, arp, pulse: {bpm, from, to}, cluster: {notes, level},
             tremolo: {hz, depth}}]       a region ends where the next one starts
  events:  [{type: twinkle|swell|boom|chord, at|to, ...}]
Times are absolute episode seconds; a string "~t" snaps to the nearest speech onset within
snap_tolerance. Chord changes inside a region wait for the next onset at least `every` seconds
after the previous change, so pads never move mid-word. Onsets come from speech_onsets(), which is
more reliable for Thai TTS than Whisper segment starts (small models skip long stretches).
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

SR = 48000
BLOCK = 10.0
MARGIN = 0.25


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


class Score:
    def __init__(self, cues, phrases):
        self.c = cues
        self.total = float(cues["total_seconds"])
        self.N = int(self.total * SR)
        self.rng = np.random.default_rng(int(cues.get("seed", 1950)))
        self.chords = {k: list(v) for k, v in cues["chords"].items()}
        self.phrase_starts = sorted({round(float(p["start"] if isinstance(p, dict) else p), 2) for p in phrases})
        self.tol = float(cues.get("snap_tolerance", 1.6))
        self.snap_log = []
        self.regions = [dict(r, start=self.when(r["start"])) for r in cues["regions"]]
        self.regions.sort(key=lambda r: r["start"])
        for i, r in enumerate(self.regions):
            r["end"] = self.regions[i + 1]["start"] if i + 1 < len(self.regions) else self.total
        self.events = []
        for e in cues.get("events", []):
            e = dict(e)
            for k in ("at", "to"):
                if k in e:
                    e[k] = self.when(e[k])
            if e["type"] == "swell" and "to" in e:
                e["start"], e["end"] = e["to"] - e.get("len", 1.6), e["to"]
            self.events.append(e)
        self._build_chord_timeline()
        self._build_automation()

    # ------------------------------------------------------------ timeline
    def when(self, v):
        """Numbers are exact; "~t" snaps to the nearest phrase start within tolerance."""
        if not isinstance(v, str):
            return float(v)
        t = float(v.lstrip("~"))
        near = min(self.phrase_starts, key=lambda p: abs(p - t), default=t)
        res = near if abs(near - t) <= self.tol else t
        self.snap_log.append((t, res))
        return res

    def _snap(self, t, limit):
        for p in self.phrase_starts:
            if p >= t:
                return p if p < limit - 1.5 else None
        return None

    def _build_chord_timeline(self):
        changes = []  # (time, notes, level)
        for r in self.regions:
            prog, every = r.get("prog", []), float(r.get("every", 8.0))
            if not prog:
                changes.append((r["start"], None, 0))
                continue
            t, k = r["start"], 0
            while t is not None and t < r["end"]:
                changes.append((t, self.chords[prog[k % len(prog)]], r.get("level", 1.0)))
                k += 1
                t = self._snap(t + every, r["end"])
        for e in self.events:
            if e["type"] == "chord":
                changes.append((e["at"], self.chords[e["chord"]], e.get("level", 1.0)))
        changes.sort(key=lambda x: x[0])
        self.voices = []  # (t0, t1, notes, level)
        for i, (t, notes, lvl) in enumerate(changes):
            if notes is None:
                continue
            nxt = changes[i + 1][0] if i + 1 < len(changes) else self.total + 4
            self.voices.append((t - 0.8, nxt + 2.2, notes, lvl))

    def _build_automation(self):
        keys = ["bright", "pad", "drone", "air"]
        defaults = {"bright": 1200, "pad": .8, "drone": .5, "air": .07}
        self.auto = {}
        for k in keys:
            pts, prev = [], None
            for r in self.regions:
                v = r.get(k, defaults[k])
                ramp = float(r.get("ramp", 1.5))
                if prev is None:
                    pts.append((0.0, v))
                else:
                    pts += [(r["start"], prev), (r["start"] + ramp, v)]
                prev = v
            pts.append((self.total + 10, prev))
            ts, vs = zip(*sorted(pts, key=lambda x: x[0]))
            self.auto[k] = (np.array(ts), np.array(vs, float))

    def curve(self, k, t):
        ts, vs = self.auto[k]
        return np.interp(t, ts, vs)

    # ------------------------------------------------------------ dsp helpers
    @staticmethod
    def fir_lowpass(fc, taps=2047):
        n = np.arange(taps) - taps // 2
        h = np.sinc(2 * fc / SR * n) * np.blackman(taps)
        return h / h.sum()

    @staticmethod
    def conv_same(x, h):
        L = x.shape[0] + len(h) - 1
        F = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x, F, axis=0) * np.fft.rfft(h, F)[:, None], F, axis=0)
        o = len(h) // 2
        return y[o: o + x.shape[0]]

    def idx(self, t):
        return int(round(t * SR))

    def place(self, buf, sig, t, pan=0.0, gain=1.0):
        i = self.idx(t)
        if i >= self.N or i + len(sig) <= 0:
            return
        s = sig[max(0, -i): self.N - i] * gain
        i = max(0, i)
        buf[i: i + len(s), 0] += (s * np.sqrt((1 - pan) / 2)).astype(np.float32)
        buf[i: i + len(s), 1] += (s * np.sqrt((1 + pan) / 2)).astype(np.float32)

    # ------------------------------------------------------------ layers
    def render_pad_and_drone(self, pad_out, drone_out):
        dark_h, bright_h = self.fir_lowpass(600), self.fir_lowpass(4500)
        nb = int(np.ceil(self.total / BLOCK))
        for b in range(nb):
            a0, a1 = b * BLOCK - MARGIN, min(self.total, (b + 1) * BLOCK) + MARGIN
            t = np.arange(int((a1 - a0) * SR)) / SR + a0
            pad = np.zeros((len(t), 2))
            drone = np.zeros(len(t))
            for vi, (t0, t1, notes, lvl) in enumerate(self.voices):
                if t1 <= a0 or t0 >= a1:
                    continue
                tt = t - t0
                env = np.clip(tt / 2.4, 0, 1) ** 1.5 * np.clip((t1 - t0 - tt) / 3.0, 0, 1) ** 1.2
                live = env > 0
                if not live.any():
                    continue
                vr = np.random.default_rng(vi * 7919 + 13)
                for m in notes:
                    f = float(hz(m))
                    low = m < 45
                    for ch, det in enumerate((-0.07, 0.08)):
                        ff = f * 2 ** (det / 12)
                        ph = vr.uniform(0, 6.28, 12)
                        acc = np.zeros(live.sum())
                        for h in range(1, 5 if low else 11):
                            if ff * h > 9000:
                                break
                            acc += np.sin(2 * np.pi * ff * h * t[live] + ph[h]) / h ** 1.35
                        pad[live, ch] += acc * env[live] * lvl / 4.5  # equal per-note level: sparse chords sit quieter
                bf = float(hz(notes[0]))
                while bf > 75:
                    bf /= 2
                ph = 2 * np.pi * bf * t[live] + vi
                drone[live] += (np.sin(ph) + .35 * np.sin(2 * ph) + .12 * np.sin(3 * ph + .5)) * env[live]
            k = np.clip((np.log(self.curve("bright", t)) - np.log(600)) / (np.log(4500) - np.log(600)), 0, 1)[:, None]
            pad = self.conv_same(pad, dark_h) * (1 - k) + self.conv_same(pad, bright_h) * k
            pad *= (0.85 + 0.15 * np.sin(2 * np.pi * t / 9.0))[:, None] * self.curve("pad", t)[:, None]
            drone *= self.curve("drone", t)
            for r in self.regions:  # tremolo regions
                tr = r.get("tremolo")
                if tr:
                    m = (t >= r["start"]) & (t < r["end"])
                    pad[m] *= (1 - tr["depth"] * (0.5 + 0.5 * np.sin(2 * np.pi * tr["hz"] * t[m])))[:, None]
            c0 = self.idx(max(0.0, a0 + MARGIN)) if b else 0
            c1 = self.idx(min(self.total, a1 - MARGIN))
            off = c0 - self.idx(a0)
            pad_out[c0:c1] = pad[off: off + c1 - c0]
            drone_out[c0:c1, 0] = drone[off: off + c1 - c0]
            drone_out[c0:c1, 1] = drone[off: off + c1 - c0]
            print(f"\r  pad block {b + 1}/{nb}", end="", flush=True)
        print()

    def air(self, out):
        loop_n = int(23.7 * SR)
        f = np.fft.rfftfreq(loop_n, 1 / SR)
        g = 1 / np.sqrt(1 + (1800 / np.maximum(f, 1)) ** 2) / np.sqrt(1 + (f / 7000) ** 2)
        loops = []
        for _ in range(2):  # circular filtering -> seamless loop
            x = np.fft.irfft(np.fft.rfft(self.rng.standard_normal(loop_n)) * g, loop_n)
            loops.append(x / np.abs(x).max())
        reps = int(np.ceil(self.N / loop_n))
        for ch in range(2):
            col = np.tile(loops[ch], reps)[: self.N]
            for s in range(0, self.N, int(BLOCK * SR)):
                e = min(self.N, s + int(BLOCK * SR))
                tt = np.arange(s, e) / SR
                out[s:e, ch] += (col[s:e] * self.curve("air", tt)).astype(np.float32)

    def bell(self, f, dur=4.0):
        tt = np.arange(int(dur * SR)) / SR
        e = np.exp(-tt * 1.6) * np.minimum(1, tt / 0.01)
        return (np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt * 3)
                + .12 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt * 6)) * e

    def pluck(self, f, dur=1.4):
        tt = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * f * tt) + .25 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 6)) \
            * np.exp(-tt * 3.2) * np.minimum(1, tt / 0.006)

    def chord_at(self, t):
        live = [v for v in self.voices if v[0] + 0.8 <= t < v[1] - 2.2]
        return live[-1][2] if live else [62, 69]

    def events_layers(self, dry, send):
        rng = self.rng
        for r in self.regions:
            a, b = r["start"], min(r["end"], self.total)
            if b - a < 0.1:
                continue
            rate = r.get("shimmer", 0)
            if rate:
                t = a + rng.exponential(1 / rate)
                while t < b:
                    tones = [m for m in self.chord_at(t) if m >= 50] or [62, 69]
                    m = min(int(rng.choice(tones)) + int(rng.choice([12, 24])), 98)
                    self.place(send, self.bell(float(hz(m))), t, rng.uniform(-.8, .8), rng.uniform(.05, .12))
                    t += rng.exponential(1 / rate)
            arp = r.get("arp", 0)
            if arp:
                t, k = a + 0.5, 0
                step = 1 / arp
                while t < b - 0.3:
                    tones = sorted(m for m in self.chord_at(t) if m >= 50)[:5] or [62, 69]
                    seq = tones + tones[-2:0:-1]
                    m = seq[k % len(seq)] + 12
                    fade = min(1, (t - a) / 2, (b - t) / 2)
                    sig = self.pluck(float(hz(m)))
                    pan = .5 * np.sin(k * .9)
                    self.place(dry, sig, t, pan, .05 * fade)
                    self.place(send, sig, t, pan, .07 * fade)
                    t += step
                    k += 1
            pu = r.get("pulse")
            if pu:
                beat = 60 / pu.get("bpm", 64)
                t = a + 0.3
                while t < b - 0.1:
                    x = (t - a) / max(1e-3, b - a)
                    level = pu.get("from", .35) + (pu.get("to", .9) - pu.get("from", .35)) * x
                    for off, g in ((0, 1.0), (0.24, .6)):
                        tt = np.arange(int(0.45 * SR)) / SR
                        s = np.sin(2 * np.pi * np.cumsum(46 + 40 * np.exp(-tt * 18)) / SR) * np.exp(-tt * 9)
                        self.place(dry, s, t + off, 0, level * g * .9)
                    t += beat
            cl = r.get("cluster")
            if cl:
                i0, i1 = self.idx(a), min(self.N, self.idx(b))
                tt = np.arange(i1 - i0) / SR
                sw = sum(np.sin(2 * np.pi * float(hz(m)) * tt * (1 + .001 * j)) for j, m in enumerate(cl["notes"]))
                shape = (tt / max(tt[-1], 1e-3)) ** 2 * np.clip((tt[-1] - tt) / 0.06, 0, 1)
                sw = sw * shape * cl.get("level", .2) / len(cl["notes"]) * 2
                dry[i0:i1, 0] += sw.astype(np.float32)
                dry[i0:i1, 1] += (sw * .9).astype(np.float32)
        for e in self.events:
            if e["type"] == "twinkle":
                for j, m in enumerate(e["notes"]):
                    self.place(send, self.bell(float(hz(m)), 5.0), e["at"] + .4 * j, rng.uniform(-.3, .3), e.get("gain", .16))
            elif e["type"] == "swell":
                n = self.idx(e["end"]) - self.idx(e["start"])
                tt = np.arange(n) / SR
                x = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) *
                                 (1 / np.sqrt(1 + (400 / np.maximum(np.fft.rfftfreq(n, 1 / SR), 1)) ** 2))
                                 / np.sqrt(1 + (np.fft.rfftfreq(n, 1 / SR) / 5000) ** 2), n)
                x = x / np.abs(x).max() * (tt / tt[-1]) ** 3 * e.get("gain", .35)
                self.place(send, x, e["start"], 0, 1.0)
                self.place(dry, x, e["start"], 0, .4)
            elif e["type"] == "boom":
                tt = np.arange(int(3.0 * SR)) / SR
                s = np.sin(2 * np.pi * np.cumsum(36 + 80 * np.exp(-tt * 8)) / SR) * np.exp(-tt * 1.8)
                nz = rng.standard_normal(len(tt))
                nz = self.conv_same(nz[:, None], self.fir_lowpass(1800, 511))[:, 0] * np.exp(-tt * 5)
                g = e.get("gain", .6)
                self.place(dry, s + .5 * nz, e["at"], 0, g)
                self.place(send, .6 * nz + .3 * s, e["at"], 0, g)

    def reverb(self, send, secs=6.0):
        n = int(secs * SR)
        tt = np.arange(n) / SR
        h = self.fir_lowpass(6000, 511)
        irs = []
        for _ in range(2):
            ir = self.rng.standard_normal(n) * np.exp(-tt * 6.9 / secs)
            ir[: int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))
            ir = self.conv_same(ir[:, None], h)[:, 0]
            irs.append(ir / np.sqrt((ir ** 2).sum()))
        B = 1 << 19
        F = 1 << (B + n - 1).bit_length()
        wet = np.zeros_like(send)
        IR = [np.fft.rfft(ir, F) for ir in irs]
        for s in range(0, self.N, B):
            e = min(self.N, s + B)
            for ch in range(2):
                y = np.fft.irfft(np.fft.rfft(send[s:e, ch], F) * IR[ch], F)[: e - s + n]
                end = min(self.N, s + len(y))
                wet[s:end, ch] += y[: end - s].astype(np.float32)
        return wet

    # ------------------------------------------------------------ mix
    def render(self):
        N = self.N
        pad = np.zeros((N, 2), np.float32)
        drone = np.zeros((N, 2), np.float32)
        print("pad + drone")
        self.render_pad_and_drone(pad, drone)
        pad /= max(1e-6, np.abs(pad).max())
        drone /= max(1e-6, np.abs(drone).max())
        dry = .75 * pad + .45 * drone
        del drone
        print("air / events")
        self.air(dry)
        send = .6 * pad
        del pad
        self.events_layers(dry, send)
        print("reverb")
        wet = self.reverb(send)
        dry += .55 * wet + .35 * send
        del wet, send
        lo = self.fir_lowpass(35, 4095)
        for s in range(0, N, int(30 * SR)):  # gentle 35 Hz high-pass via (x - lowpass(x))
            e = min(N, s + int(30 * SR))
            a0, a1 = max(0, s - 4096), min(N, e + 4096)
            seg = dry[a0:a1].astype(np.float64)
            hp = seg - self.conv_same(seg, lo)
            dry[s:e] = hp[s - a0: s - a0 + e - s]
        t = np.arange(N) / SR
        dry *= np.minimum(1, t / 2.0)[:, None].astype(np.float32)
        dry *= np.clip((self.total - t) / 3.0, 0, 1)[:, None].astype(np.float32)
        dry /= np.abs(dry).max() / 0.9
        return dry


def speech_onsets(audio_path: str | Path, min_pause_seconds: float = 0.16) -> list[float]:
    """Speech onsets (seconds) that follow a pause, from a narration WAV (16-bit PCM)."""
    with wave.open(str(audio_path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64)
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    hop = int(sr * 0.01)
    frames = len(a) // hop
    rms = np.sqrt((a[: frames * hop].reshape(frames, hop) ** 2).mean(1))
    db = 20 * np.log10(rms / 32768 + 1e-9)
    floor = db[db > -80]
    threshold = (np.percentile(floor, 60) if floor.size else -40.0) - 22
    onsets, silent, need = [], 0, int(round(min_pause_seconds / 0.01))
    for i, voiced in enumerate(db > threshold):
        if not voiced:
            silent += 1
            continue
        if silent >= need:
            onsets.append(round(i * 0.01, 2))
        silent = 0
    return onsets


def render_score(cues: dict, onsets: list) -> np.ndarray:
    """Render the cue sheet to a (samples, 2) float32 array at SR, peak 0.9."""
    return Score(cues, onsets).render()


def write_wav(path: str | Path, mix: np.ndarray) -> None:
    with wave.open(str(path), "wb") as o:
        o.setnchannels(2)
        o.setsampwidth(2)
        o.setframerate(SR)
        o.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
