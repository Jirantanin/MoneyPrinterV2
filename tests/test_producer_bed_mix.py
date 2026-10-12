"""Background bed: global Songs/ bed by default, or a per-episode composed score from render_settings."""

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

from producer_renderer import _bed_filter_complex, _episode_bed_override, _mix_background_bed  # noqa: E402


def _probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                          "stream=sample_rate,channels:format=duration", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


class BedFilterTests(unittest.TestCase):
    def test_default_graph_is_unchanged_mono_chain(self) -> None:
        graph = _bed_filter_complex(total_duration=100, narration_pad_seconds=3, volume_db=-18,
                                    ducking_ratio=2, fade_seconds=2)
        self.assertTrue(graph.startswith("[0:a]apad=pad_dur=3.000,"))
        self.assertIn("[1:a]atrim=0:100.000,asetpts=PTS-STARTPTS,volume=-18.0dB,afade=t=in:st=0:d=2.000", graph)
        self.assertNotIn("aformat", graph)

    def test_stereo_formats_both_inputs(self) -> None:
        graph = _bed_filter_complex(total_duration=100, narration_pad_seconds=3, volume_db=-18,
                                    ducking_ratio=2, fade_seconds=2, stereo=True)
        self.assertTrue(graph.startswith("[0:a]aformat=sample_rates=48000:channel_layouts=stereo,apad"))
        self.assertIn("[1:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim", graph)

    def test_override_read_from_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            self.assertIsNone(_episode_bed_override(episode))
            (episode / "producer_plan.json").write_text(json.dumps(
                {"render_settings": {"renderer": "minimal_doc", "background_bed": {"path": "score/bed.wav", "stereo": True}}}),
                encoding="utf-8")
            self.assertEqual(_episode_bed_override(episode), {"path": "score/bed.wav", "stereo": True})

    def test_missing_episode_bed_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "producer_plan.json").write_text(json.dumps(
                {"render_settings": {"background_bed": {"path": "score/nope.wav"}}}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                _mix_background_bed(root_dir=episode, episode_dir=episode, narration_audio=episode / "n.wav",
                                    total_duration=5, narration_pad_seconds=1, force=True, log_path=episode / "log")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
    def test_episode_score_mix_is_stereo_48k_with_pad(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "score").mkdir()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=6", "-ar", "24000",
                            "-ac", "1", str(episode / "narr.wav")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=9:a=0.2", "-ar", "48000",
                            "-ac", "2", str(episode / "score" / "bed.wav")], check=True)
            (episode / "producer_plan.json").write_text(json.dumps(
                {"render_settings": {"background_bed": {"path": "score/bed.wav", "volume_db": -18, "stereo": True}}}),
                encoding="utf-8")
            out, info = _mix_background_bed(root_dir=episode, episode_dir=episode, narration_audio=episode / "narr.wav",
                                            total_duration=8, narration_pad_seconds=2, force=True,
                                            log_path=episode / "log")
            self.assertEqual(info["status"], "mixed")
            self.assertEqual(info["source"], "episode_render_settings")
            meta = _probe(out)
            self.assertEqual(meta["streams"][0]["channels"], 2)
            self.assertEqual(meta["streams"][0]["sample_rate"], "48000")
            self.assertAlmostEqual(float(meta["format"]["duration"]), 8.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
