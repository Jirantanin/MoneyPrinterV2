"""Offline tests for the advisory TypeSafe asset shadow reviewer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from typesafe_asset_shadow import build_shadow_state, review_visual_beat_shadow


def answer(**values):
    return SimpleNamespace(**values)


class FakeClient:
    def __init__(self, *, misleading: float = 0.1, source_confidence: float = 0.95):
        self.misleading = misleading
        self.source_confidence = source_confidence

    def system_one(self, *, state, questions):
        answers = {
            "visual_function": answer(
                choice="mechanism", confidence=0.92, probabilities={"mechanism": 0.9}
            ),
            "source_class": answer(
                choice="explanatory_graphic",
                confidence=self.source_confidence,
                probabilities={"explanatory_graphic": 0.91},
            ),
            "specific_subject_required": answer(noul=0.8),
            "generic_stock_safe": answer(noul=0.2),
            "generated_safe_if_labeled": answer(noul=0.6),
            "current_strategy_suitable": answer(noul=0.85),
            "current_strategy_misleading": answer(noul=self.misleading),
        }
        for candidate in state["candidates"]:
            index = candidate["index"]
            answers[f"candidate_{index}_suitable"] = answer(noul=0.9 - index * 0.1)
            answers[f"candidate_{index}_misleading"] = answer(noul=0.1 + index * 0.2)
        return SimpleNamespace(
            model="jev-fixture",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            answers=answers,
        )


def fixture_beat():
    return {
        "asset_plan_id": "S01B01",
        "section_title": "แรงดันใต้ทะเล",
        "role": "mechanism",
        "beat_type": "explanation",
        "visual_type": "diagram",
        "intent": "อธิบายว่าแรงดันเพิ่มตามความลึกอย่างไร",
        "duration_seconds": 7,
        "specific_match_required": True,
        "selected_provider": "remotion_graphic",
        "selected_media_type": "graphic",
        "selected_title": "Pressure diagram",
        "selected_reason": "Explain a sourced physical relationship.",
        "source_urls": ["https://example.org/source"],
        "candidates": [
            {
                "provider": "remotion_graphic",
                "media_type": "graphic",
                "title": "Pressure diagram",
                "reason": "Explain the mechanism.",
                "source_url": "https://example.org/source",
            },
            {
                "provider": "pexels",
                "media_type": "video",
                "title": "Ocean waves",
                "reason": "Generic atmosphere.",
            },
        ],
    }


class TypeSafeAssetShadowTests(unittest.TestCase):
    def test_state_is_bounded_and_marks_text_only_boundary(self):
        beat = fixture_beat()
        beat["candidates"] = beat["candidates"] * 4
        state = build_shadow_state("Ocean pressure", beat)
        self.assertLessEqual(len(state["candidates"]), 5)
        self.assertIn("No image or video pixels were inspected", state["task_boundary"])

    def test_good_result_is_never_asset_approval(self):
        result = review_visual_beat_shadow(
            "Ocean pressure", fixture_beat(), client=FakeClient()
        )
        self.assertEqual(result["status"], "shadow_recommendation")
        self.assertFalse(result["approval"])
        self.assertFalse(result["pixel_inspection_performed"])
        self.assertEqual(result["recommended_source_class"], "explanatory_graphic")

    def test_misleading_risk_routes_to_review(self):
        result = review_visual_beat_shadow(
            "Ocean pressure", fixture_beat(), client=FakeClient(misleading=0.8)
        )
        self.assertEqual(result["status"], "review_required")
        self.assertIn("current_strategy_may_mislead_as_evidence", result["review_reasons"])

    def test_candidate_rank_penalizes_misleading_strategy(self):
        result = review_visual_beat_shadow(
            "Ocean pressure", fixture_beat(), client=FakeClient()
        )
        reviews = result["candidate_reviews"]
        self.assertEqual(reviews[0]["candidate_index"], 0)
        self.assertGreater(reviews[0]["shadow_rank_score"], reviews[1]["shadow_rank_score"])


if __name__ == "__main__":
    unittest.main()
