"""Offline coverage for mapping a YouTube retention curve onto an episode's scenes (no network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import youtube_review as yr  # noqa: E402


def _curve(points: int = 100) -> list[dict]:
    # Linear fall from 100% to 40%, relative performance rises along the video.
    return [{"elapsedVideoTimeRatio": (i + 1) / points, "audienceWatchRatio": 1.0 - 0.6 * (i + 1) / points,
             "relativeRetentionPerformance": (i + 1) / points} for i in range(points)]


class ReviewTests(unittest.TestCase):
    def _episode(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        episode = Path(temp.name)
        (episode / "render_props.json").write_text(json.dumps({"sceneDurations": [20.0, 30.0, 50.0]}), encoding="utf-8")
        script = [{"section_index": 1, "section_title": "เปิด", "scene_title": "a", "narration": "หนึ่ง"},
                  {"section_index": 1, "section_title": "เปิด", "scene_title": "b", "narration": "สอง"},
                  {"section_index": 2, "section_title": "กลาง", "scene_title": "c", "narration": "สาม"}]
        (episode / "script.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
        return episode

    def test_scene_timeline_accumulates_rendered_durations(self) -> None:
        scenes = yr.scene_timeline(self._episode())
        self.assertEqual([(s["start_seconds"], s["end_seconds"]) for s in scenes], [(0.0, 20.0), (20.0, 50.0), (50.0, 100.0)])

    def test_maps_retention_and_drop_per_scene_and_section(self) -> None:
        mapped = yr.map_retention(_curve(), yr.scene_timeline(self._episode()), 100.0)
        self.assertAlmostEqual(mapped[2]["retention_start"], 0.7, places=2)
        self.assertAlmostEqual(mapped[2]["drop"], 0.3, places=2)
        self.assertGreater(mapped[2]["relative"], mapped[0]["relative"])
        sections = yr.section_summary(mapped)
        self.assertEqual([s["section_title"] for s in sections], ["เปิด", "กลาง"])
        self.assertAlmostEqual(sections[0]["drop"], mapped[0]["drop"] + mapped[1]["drop"], places=2)

    def test_markdown_without_retention_still_renders(self) -> None:
        episode = self._episode()
        data = {"video_id": "x", "url": "u", "title": "t", "published_at": "2026-10-05T11:30:00+00:00",
                "window": {"start": "2026-10-04", "end": "2026-10-12", "days_since_publish": 7}, "duration_seconds": 100.0,
                "statistics": {"viewCount": "5"}, "totals": {}, "daily": [], "traffic_sources": [], "search_terms": [],
                "retention_curve": [], "comments": []}
        text = yr.render_markdown(yr.build_review(episode, data))
        self.assertIn("ยังไม่ให้ retention curve", text)

    def test_iso_duration(self) -> None:
        self.assertEqual(yr.iso_duration_seconds("PT13M7S"), 787.0)
        self.assertEqual(yr.iso_duration_seconds("PT1H2S"), 3602.0)


if __name__ == "__main__":
    unittest.main()
