"""Regression coverage for topic-aware official b-roll discovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_broll_expander import (  # noqa: E402
    VOYAGER_OFFICIAL_BLOCKED_MARKERS,
    VOYAGER_OFFICIAL_RELEVANCE_MARKERS,
    _build_official_queries,
    _is_relevant_official_result,
    _is_voyager_official_profile,
    _runware_broll_prompt,
    _scene_asset_id,
    _select_fresh_official,
    _stock_keyword_pool,
)


VOYAGER_SCENES = [
    {
        "scene_title": "วิธีสอนคนแปลกหน้าให้เปิดฟัง",
        "narration": "ยานวอยเอเจอร์บรรทุกโกลเดนเรคคอร์ดผ่านดาวพฤหัสบดีและดาวเสาร์",
    }
]


class OfficialBrollTopicProfileTests(unittest.TestCase):
    def test_voyager_episode_uses_voyager_queries_instead_of_moon_seeds(self) -> None:
        self.assertTrue(_is_voyager_official_profile(VOYAGER_SCENES))
        queries = _build_official_queries(VOYAGER_SCENES)
        self.assertTrue(queries)
        self.assertGreaterEqual(
            sum(
                "voyager" in query.lower() or "golden record" in query.lower()
                for query in queries
            ),
            len(queries) - 1,
        )
        self.assertFalse(any(query == "Moon" for query in queries))

    def test_voyager_result_passes_and_unrelated_moon_result_fails(self) -> None:
        self.assertTrue(
            _is_relevant_official_result(
                {"title": "Voyager Golden Record mounted on the spacecraft"},
                relevance_markers=VOYAGER_OFFICIAL_RELEVANCE_MARKERS,
                blocked_markers=VOYAGER_OFFICIAL_BLOCKED_MARKERS,
            )
        )

    def test_voyager_scene_uses_topic_specific_stock_keywords(self) -> None:
        scene = {
            "producer_asset_plan_id": "VGR-05",
            "scene_title": "โลกในร่องเสียง",
            "narration": "เสียงคลื่น วาฬ รถไฟ และวัฒนธรรมจากหลายพื้นที่ของโลก",
        }
        self.assertEqual(_scene_asset_id(scene), "VGR-05")
        keywords = _stock_keyword_pool(scene)
        self.assertIn("ocean waves", keywords)
        self.assertNotIn("moon night sky", keywords)

    def test_voyager_runware_prompt_avoids_legacy_topic_language(self) -> None:
        scene = {
            "producer_asset_plan_id": "VGR-11",
            "scene_title": "คำสัญญาของปี 1977",
            "narration": "สารจากประธานาธิบดีคาร์เตอร์เป็นคำสัญญาถึงอนาคต",
        }
        prompt = _runware_broll_prompt(scene, {}, scene_index=10, slot_index=2)
        self.assertIn("no portrait of any president", prompt)
        self.assertNotIn("Moon", prompt)
        self.assertNotIn("Homo", prompt)
        self.assertFalse(
            _is_relevant_official_result(
                {"title": "Apollo Moon lunar surface panorama"},
                relevance_markers=VOYAGER_OFFICIAL_RELEVANCE_MARKERS,
                blocked_markers=VOYAGER_OFFICIAL_BLOCKED_MARKERS,
            )
        )

    def test_fresh_official_selection_is_scoped_to_scene_query(self) -> None:
        launch = {
            "title": "Voyager 2 Launch",
            "fresh_query": "Voyager launch 1977 Titan Centaur",
            "fresh_image_url": "https://example.test/launch.jpg",
        }
        interstellar = {
            "title": "Voyager in Interstellar Space",
            "fresh_query": "Voyager 1 interstellar space",
            "fresh_image_url": "https://example.test/interstellar.jpg",
        }
        selected = _select_fresh_official(
            scene={"producer_asset_plan_id": "VGR-03"},
            scene_index=2,
            slot_index=0,
            section_number=2,
            candidates=[interstellar, launch],
            visual_usage={},
            max_repeats=2,
        )
        self.assertIs(selected, launch)


if __name__ == "__main__":
    unittest.main()
