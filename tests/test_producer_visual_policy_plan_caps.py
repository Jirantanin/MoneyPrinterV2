"""The episode's own source policy (producer_plan.json visual_rules.source_policy) sets the graphic cap."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_visual_policy import plan_visual_source_policy, visual_policy_report  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
