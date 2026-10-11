"""Optional episode-local SFX cues mixed over the prepared audio."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_renderer import _mix_sfx_cues, _sfx_filter_complex  # noqa: E402


class SfxFilterTests(unittest.TestCase):
    def test_cue_is_trimmed_faded_and_delayed(self) -> None:
        graph = _sfx_filter_complex(
            [{"path": "a.wav", "start_seconds": 12.5, "duration_seconds": 4, "fade_in_seconds": 1,
              "fade_out_seconds": 1.5, "gain_db": -20}],
            sample_rate=48000, channel_layout="stereo",
        )
        self.assertIn("[1:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:4.000", graph)
        self.assertIn("afade=t=out:st=2.500:d=1.500", graph)
        self.assertIn("volume=-20.0dB,adelay=12500:all=1[sfx1]", graph)
        self.assertTrue(graph.endswith("[base][sfx1]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=disabled[out]"))

    def test_without_cue_file_audio_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "mix.wav"
            result_path, info = _mix_sfx_cues(episode_dir=Path(temp), audio_path=audio, log_path=Path(temp) / "log")
            self.assertEqual(result_path, audio)
            self.assertEqual(info, {"status": "none"})

    def test_missing_cue_file_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "sfx_cues.json").write_text(json.dumps({"cues": [{"path": "sfx/nope.wav", "start_seconds": 1}]}),
                                                   encoding="utf-8")
            with self.assertRaises(RuntimeError):
                _mix_sfx_cues(episode_dir=episode, audio_path=episode / "mix.wav", log_path=episode / "log")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
    def test_mix_keeps_base_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=6", "-ar", "24000",
                            str(episode / "mix.wav")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=10:a=0.2",
                            str(episode / "fx.wav")], check=True)
            (episode / "sfx_cues.json").write_text(json.dumps({"cues": [
                {"path": "fx.wav", "start_seconds": 2, "duration_seconds": 3, "gain_db": -18}]}), encoding="utf-8")
            out, info = _mix_sfx_cues(episode_dir=episode, audio_path=episode / "mix.wav", log_path=episode / "log")
            duration = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                             "csv=p=0", str(out)], check=True, capture_output=True, text=True).stdout)
            self.assertEqual(info["status"], "mixed")
            self.assertAlmostEqual(duration, 6.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
