"""The episode's own source policy (producer_plan.json visual_rules.source_policy) sets the graphic cap."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_mode import default_producer_plan  # noqa: E402
from producer_visual_policy import (  # noqa: E402
    default_visual_source_policy, explainer_visual_source_policy, plan_visual_source_policy, visual_policy_report)


def slots(graphics: int, footage: int) -> list[dict]:
    return ([{"provider": "remotion_graphic", "media_type": "video", "slot_duration_seconds": 6.0}] * graphics
            + [{"provider": "official_media", "media_type": "image", "slot_duration_seconds": 6.0}] * footage)


class PlanCapTests(unittest.TestCase):
    def test_default_cap_blocks_a_mostly_graphic_cut(self) -> None:
        self.assertEqual(visual_policy_report(slots(7, 3))["status"], "blocked")

    def test_plan_override_raises_the_graphic_cap(self) -> None:
        plan = {"visual_rules": {"source_policy": {"caps": {"graphic_max_ratio": 0.8}}}}
        report = visual_policy_report(slots(7, 3), policy=plan_visual_source_policy(plan))
        self.assertNotEqual(report["status"], "blocked")
        self.assertEqual(report["limits"]["graphic_max_ratio"], 0.8)
        self.assertEqual(visual_policy_report(slots(9, 1), policy=plan_visual_source_policy(plan))["status"], "blocked")

    def test_missing_or_malformed_policy_falls_back_to_default(self) -> None:
        for plan in ({}, {"visual_rules": {}}, {"visual_rules": {"source_policy": {"caps": "x"}}}, None):
            self.assertIsNone(plan_visual_source_policy(plan))


class ExplainerDefaultTests(unittest.TestCase):
    """Since 2026-10-13 new episodes default to flat explainer graphics with real evidence kept (user direction)."""

    def test_new_plans_carry_the_explainer_policy(self) -> None:
        policy = plan_visual_source_policy(default_producer_plan("topic", Path("ep")))
        self.assertEqual(policy["caps"]["graphic_max_ratio"], 0.8)
        report = visual_policy_report(slots(7, 3), policy=policy)
        self.assertNotEqual(report["status"], "blocked")
        self.assertFalse(any(w["category"] == "graphic_run" for w in report["review_warnings"]))
        self.assertEqual(visual_policy_report(slots(9, 1), policy=policy)["status"], "blocked")

    def test_legacy_default_is_unchanged_for_plans_without_a_policy(self) -> None:
        self.assertEqual(default_visual_source_policy()["caps"]["graphic_max_ratio"], 0.2)
        report = visual_policy_report(slots(2, 8) + slots(3, 0))
        self.assertTrue(any(w["category"] == "graphic_run" for w in report["review_warnings"]))

    def test_new_plans_have_an_art_direction_to_fill(self) -> None:
        art = default_producer_plan("topic", Path("ep"))["visual_rules"]["art_direction"]
        self.assertEqual(set(art), {"palette", "background", "recurring_metaphor", "camera_motion", "topic_characters"})

    def test_explainer_policy_keeps_the_generated_image_cap(self) -> None:
        self.assertEqual(explainer_visual_source_policy()["caps"]["generated_image_max_ratio"], 0.5)


if __name__ == "__main__":
    unittest.main()
