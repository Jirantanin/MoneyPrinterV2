"""Composed score engine and SFX primitives: timing contracts and output shape."""

from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_score import SR, Score, render_score, speech_onsets, write_wav  # noqa: E402
from producer_sfx_synth import Stem, bell, pop  # noqa: E402

CUES = {
    "total_seconds": 6.0, "seed": 1, "snap_tolerance": 1.0,
    "chords": {"D": [38, 45, 54, 61], "G": [31, 38, 47, 54], "fifth": [38, 45]},
    "regions": [{"start": 0.0, "prog": ["D", "G"], "every": 1.5, "bright": 1500, "pad": .8, "shimmer": 1.0},
                {"start": "~3.9", "prog": [], "pad": 0, "drone": 0, "ramp": .06},
                {"start": 4.6, "prog": ["fifth"], "pad": .5}],
    "events": [{"type": "twinkle", "at": "~2.2", "notes": [86]}, {"type": "swell", "to": 4.6, "len": .5}],
}


class ScoreTimingTests(unittest.TestCase):
    def test_tilde_times_snap_to_onsets_within_tolerance(self) -> None:
        s = Score(CUES, [1.0, 2.0, 4.0, 5.5])
        self.assertEqual(s.regions[1]["start"], 4.0)          # "~3.9" -> onset 4.0
        self.assertEqual(s.regions[0]["end"], 4.0)            # regions are contiguous
        self.assertEqual([e for e in s.events if e["type"] == "twinkle"][0]["at"], 2.0)

    def test_far_onset_keeps_estimate(self) -> None:
        s = Score(CUES, [10.0])
        self.assertEqual(s.regions[1]["start"], 3.9)

    def test_chord_changes_wait_for_an_onset(self) -> None:
        s = Score(CUES, [1.0, 2.0, 4.0, 5.5])
        starts = [round(v[0] + .8, 2) for v in s.voices]       # voices start 0.8 s before the change
        self.assertIn(2.0, starts)                              # first change after `every` lands on onset 2.0
        self.assertNotIn(1.5, starts)

    def test_render_is_stereo_peak_normalised_and_quiet_in_snap_region(self) -> None:
        mix = render_score(CUES, [1.0, 2.0, 4.0, 5.5])
        self.assertEqual(mix.shape, (int(6.0 * SR), 2))
        self.assertAlmostEqual(float(np.abs(mix).max()), .9, places=2)
        busy = np.sqrt((mix[int(1.0 * SR):int(3.5 * SR)] ** 2).mean())
        hush = np.sqrt((mix[int(4.15 * SR):int(4.3 * SR)] ** 2).mean())
        self.assertLess(hush, busy * .5)


class OnsetTests(unittest.TestCase):
    def test_onsets_follow_pauses(self) -> None:
        sr = 24000
        t = np.arange(int(3.0 * sr)) / sr
        tone = (np.sin(2 * np.pi * 200 * t) * 8000).astype(np.int16)
        tone[int(1.0 * sr):int(1.5 * sr)] = 0                  # pause, speech resumes at 1.5 s
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "n.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(tone.tobytes())
            self.assertEqual(speech_onsets(path), [1.5])

    def test_write_wav_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "s.wav"
            write_wav(path, np.zeros((SR, 2), np.float32))
            with wave.open(str(path)) as w:
                self.assertEqual((w.getnchannels(), w.getframerate(), w.getnframes()), (2, SR, SR))


class SfxSynthTests(unittest.TestCase):
    def test_stem_length_and_peak(self) -> None:
        st = Stem(2.0)
        st.add(pop(), .2)
        st.add(bell(86), 1.9, pan=.5)                             # tail past the end is cut, not an error
        x = st.finished(-1.0)
        self.assertEqual(x.shape, (2 * 48000, 2))
        self.assertAlmostEqual(float(np.abs(x).max()), 10 ** (-1 / 20), places=3)


if __name__ == "__main__":
    unittest.main()
