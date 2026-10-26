"""Word-level trigger times for beat sheets: found and snapped, phrase fallback, never a wrong confident time."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import producer_word_times as wt  # noqa: E402

SCRIPT = "แสงนี้ออกจากดวงอาทิตย์แปดนาที"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TriggerTimeTest(unittest.TestCase):
    def test_trigger_found_and_snapped(self) -> None:
        words = [("แสงนี้", 0.0, 0.5), ("ออกจาก", 0.5, 0.9), ("ดวงอาทิตย์", 0.9, 1.6), ("แปดนาที", 1.62, 2.2)]
        r = wt.trigger_time(SCRIPT, words, "แปดนาที", onsets=[0.0, 1.70])
        self.assertEqual(r["method"], "word")
        self.assertEqual(r["time"], 1.70)
        self.assertEqual(r["confidence"], 1.0)

    def test_not_snapped_when_no_onset_is_close(self) -> None:
        words = [("แสงนี้", 0.0, 0.5), ("ออกจาก", 0.5, 0.9), ("ดวงอาทิตย์", 0.9, 1.6), ("แปดนาที", 1.62, 2.2)]
        self.assertEqual(wt.trigger_time(SCRIPT, words, "แปดนาที", onsets=[3.0])["time"], 1.62)

    def test_misheard_trigger_falls_back_to_phrase(self) -> None:
        words = [("แสงนี้", 0.0, 0.5), ("ออกจาก", 0.5, 0.9), ("ดวงอาทิตย์", 0.9, 1.6), ("แปะนะดี", 1.62, 2.2)]
        r = wt.trigger_time(SCRIPT, words, "แปดนาที", onsets=[], phrase_time=0.0)
        self.assertEqual(r["method"], "phrase")
        self.assertEqual(r["time"], 0.0)
        self.assertLess(r["confidence"], 0.6)

    def test_unknown_without_phrase(self) -> None:
        r = wt.trigger_time("ก", [], "แปดนาที", onsets=[])
        self.assertEqual(r["method"], "unknown")
        self.assertIsNone(r["time"])

    def test_trigger_missing_from_script_is_unknown(self) -> None:
        words = [("แสงนี้", 0.0, 0.5)]
        self.assertEqual(wt.trigger_time("แสงนี้", words, "แปดนาที", onsets=[])["method"], "unknown")

    def test_repeated_trigger_takes_the_occurrence_nearest_the_phrase_time(self) -> None:
        script = "ดวงอาทิตย์อยู่ไกลมากแสงจากดวงอาทิตย์ใช้แปดนาที"
        words = [("ดวงอาทิตย์", 0.0, 0.8), ("อยู่", 0.8, 1.0), ("ไกล", 1.0, 1.3), ("มาก", 1.3, 1.6), ("แสง", 1.8, 2.1),
                 ("จาก", 2.1, 2.4), ("ดวงอาทิตย์", 2.4, 3.2), ("ใช้", 3.2, 3.4), ("แปดนาที", 3.4, 4.0)]
        r = wt.trigger_time(script, words, "ดวงอาทิตย์", onsets=[], phrase_time=2.0)
        self.assertEqual((r["method"], r["time"]), ("word", 2.4))

    def test_repeated_trigger_in_order_after_start(self) -> None:
        script = "ดวงอาทิตย์อยู่ไกลมากแสงจากดวงอาทิตย์"
        words = [("ดวงอาทิตย์", 0.0, 0.8), ("อยู่ไกลมาก", 0.8, 1.6), ("แสงจาก", 1.8, 2.4), ("ดวงอาทิตย์", 2.4, 3.2)]
        r = wt.trigger_time(script, words, "ดวงอาทิตย์", onsets=[], start=3)
        self.assertEqual((r["method"], r["time"]), ("word", 2.4))
        self.assertEqual(r["index"], len(wt.squash("ดวงอาทิตย์อยู่ไกลมากแสงจาก")))

    def test_ambiguous_trigger_without_a_hint_is_not_confident(self) -> None:
        script = "คุณภาพดีแล้วคุณล่ะ"
        words = [("คุณภาพ", 0.0, 0.6), ("ดี", 0.6, 0.8), ("แล้ว", 0.8, 1.0), ("คุณ", 1.0, 1.3), ("ล่ะ", 1.3, 1.5)]
        r = wt.trigger_time(script, words, "คุณ", onsets=[])
        self.assertEqual(r["method"], "unknown")
        self.assertTrue(r["ambiguous"])
        self.assertIsNone(r["time"])
        r2 = wt.trigger_time(script, words, "คุณ", onsets=[], phrase_time=1.1)
        self.assertEqual((r2["method"], r2["time"]), ("word", 1.0))

    def test_gfx_short_uses_the_shared_char_times(self) -> None:
        g = load_script("producer_gfx_short")
        self.assertIs(g.char_times, wt.char_times)
        self.assertIs(g.squash, wt.squash)


class BeatSheetWriteTest(unittest.TestCase):
    def test_rows_outside_this_scene_are_left_alone(self) -> None:
        cli = load_script("beat_word_times")
        with tempfile.TemporaryDirectory() as d:
            beats = Path(d) / "w.beats.md"
            shutil.copy(ROOT / "doc_renderer/gfx_kit/tests/beats_fixture.md", beats)
            before = beats.read_text(encoding="utf-8").splitlines()
            script = Path(d) / "s.txt"
            script.write_text("ราวแปดนาทีแล้ว", encoding="utf-8")
            cli.transcribe = lambda wav, model: [("ราว", 0.0, 0.3), ("แปดนาที", 0.3, 1.0), ("แล้ว", 1.0, 1.2)]
            cli.speech_onsets = lambda wav: []
            cli.wav_seconds = lambda wav: 2.0
            self.assertEqual(cli.main([str(Path(d) / "x.wav"), str(script), str(beats), "--offset", "3.0", "--write"]), 0)
            after = beats.read_text(encoding="utf-8").splitlines()
            rows = [i for i, l in enumerate(after) if l.startswith("| ") and "trigger" not in l]
            self.assertTrue(after[rows[0]].startswith("| 3.30 |"), after[rows[0]])
            for i in rows[1:]:   # 5.6, 8.0 and 9.5 are outside [3.0, 5.0]
                self.assertEqual(after[i], before[i])


    def test_write_fills_times_and_marks_fallbacks(self) -> None:
        cli = load_script("beat_word_times")
        with tempfile.TemporaryDirectory() as d:
            beats = Path(d) / "w.beats.md"
            shutil.copy(ROOT / "doc_renderer/gfx_kit/tests/beats_fixture.md", beats)
            script = Path(d) / "s.txt"
            script.write_text("ราวแปดนาทีแล้วคุณก็ไกลออกไปช้าๆ", encoding="utf-8")
            words = [("ราว", 0.0, 0.3), ("แปดนาที", 0.3, 1.0), ("แล้ว", 1.0, 1.2), ("คุณ", 1.2, 1.5), ("ก็", 1.5, 1.6),
                     ("ไกล", 1.6, 2.0), ("ออกไป", 2.0, 2.4), ("พัก", 2.4, 3.0)]
            cli.transcribe = lambda wav, model: words
            cli.speech_onsets = lambda wav: [0.3, 1.21]
            cli.wav_seconds = lambda wav: 30.0
            out = cli.main([str(Path(d) / "x.wav"), str(script), str(beats), "--offset", "0", "--write"])
            self.assertEqual(out, 0)
            rows = [l for l in beats.read_text(encoding="utf-8").splitlines() if l.startswith("| ") and "trigger" not in l]
            self.assertTrue(rows[0].startswith("| 0.30 |"), rows[0])
            self.assertTrue(rows[1].startswith("| 1.21 |"), rows[1])
            self.assertIn('"ช้าๆ" (phrase)', rows[3])
            self.assertTrue(rows[3].startswith("| 9.5 |"), "a misheard trigger keeps its phrase time")


if __name__ == "__main__":
    unittest.main()
