"""Bridge warnings: timeline repairs that never reach props, and fake variety from reframes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_render_preflight import _chapter_caption_warnings, _slot_bridge_warnings  # noqa: E402


class SlotBridgeWarningTests(unittest.TestCase):
    def test_flags_timeline_assets_missing_from_props_and_repeated_reframes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            episode = Path(temp)
            (episode / "visual_timeline.json").write_text(
                json.dumps({"scenes": [{"slots": [{"local_path": "a.jpg"}, {"local_path": "fix.mp4"}]}]}),
                encoding="utf-8",
            )
            slots = [
                {"local_path": "a.jpg", "media_type": "image", "slot_duration_seconds": 4.0},
                {"local_path": "r1.jpg", "media_type": "image", "slot_duration_seconds": 4.0,
                 "provider": "local_reframe", "source_url": "https://x/still"},
                {"local_path": "r2.jpg", "media_type": "image", "slot_duration_seconds": 4.0,
                 "provider": "local_reframe", "source_url": "https://x/still"},
            ]
            warnings = _slot_bridge_warnings(episode, slots)
        self.assertTrue(any("fix.mp4" in warning for warning in warnings))
        self.assertTrue(any("2 local_reframe" in warning for warning in warnings))

    def test_clean_bridge_has_no_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            slots = [{"local_path": "a.jpg", "media_type": "image", "slot_duration_seconds": 4.0}]
            self.assertEqual(_slot_bridge_warnings(Path(temp), slots), [])


class ChapterCaptionWarningTests(unittest.TestCase):
    TITLES, COUNTS, DURS = ["A", "A", "B"], [2, 1, 2], [4.0, 6.0, 5.0, 5.0, 5.0]
    PATHS = ["sting.mp4", "real.jpg", "x.jpg", "ai.png", "y.jpg"]

    def test_flags_labelled_image_that_opens_a_chapter(self) -> None:
        quals = ["", "", "", "ภาพจำลอง สร้างด้วย AI — ไม่ใช่ภาพจริง", ""]
        warnings = _chapter_caption_warnings(self.TITLES, self.COUNTS, self.DURS, quals, self.PATHS)
        self.assertEqual(len(warnings), 1)
        self.assertIn("ai.png (scene 2)", warnings[0])

    def test_opening_sting_moves_chapter_one_card_to_the_next_shot(self) -> None:
        quals = ["", "ภาพ CGI ประกอบ — ไม่ใช่ภาพถ่ายจริง", "", "ภาพประกอบ", ""]   # plain ภาพประกอบ stock is not flagged
        self.assertEqual(_chapter_caption_warnings(self.TITLES, self.COUNTS, self.DURS, quals, self.PATHS), [])
        warnings = _chapter_caption_warnings(self.TITLES, self.COUNTS, self.DURS, quals, self.PATHS, opening=4.0)
        self.assertIn("real.jpg (scene 0)", warnings[0])


if __name__ == "__main__":
    unittest.main()
