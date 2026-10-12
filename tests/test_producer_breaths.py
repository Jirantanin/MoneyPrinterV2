"""Breath pauses and the opening-sting lead are rebuilt from the raw take every run."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_breaths import pad_breaths  # noqa: E402


def write_wav(path: Path, seconds: float, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x01\x00" * int(seconds * rate))


def seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


class PadBreathsTests(unittest.TestCase):
    def test_breaths_and_opening_lead_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "script.json").write_text(json.dumps([{"breath_after_seconds": 0.5}, {}]), encoding="utf-8")
            (episode / "minimal_render_overrides.json").write_text(json.dumps({"opening": {"seconds": 2.0}}), encoding="utf-8")
            write_wav(episode / "scene_00.wav", 1.0)
            write_wav(episode / "scene_01.wav", 1.0)
            for _ in range(2):
                result = pad_breaths(episode)
                self.assertAlmostEqual(seconds(episode / "scene_00.wav"), 3.5)
                self.assertAlmostEqual(seconds(episode / "scene_01.wav"), 1.0)
            self.assertAlmostEqual(seconds(episode / "audio_raw" / "scene_00.wav"), 1.0)
            self.assertEqual(result["opening_seconds"], 2.0)
            with wave.open(str(episode / "scene_00.wav"), "rb") as w:
                self.assertEqual(w.readframes(10), b"\x00" * 20)        # the lead is silence before the voice

    def test_no_overrides_means_no_lead(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "script.json").write_text(json.dumps([{}]), encoding="utf-8")
            write_wav(episode / "scene_00.wav", 1.0)
            self.assertEqual(pad_breaths(episode)["scenes"][0]["lead_seconds"], 0.0)
            self.assertAlmostEqual(seconds(episode / "scene_00.wav"), 1.0)


if __name__ == "__main__":
    unittest.main()
