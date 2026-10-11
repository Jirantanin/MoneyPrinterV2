"""New episodes default to the host-led narration voice; the LLM drafter carries the host and analogy rules."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from producer_mode import default_producer_plan
from producer_script_writer import _section_prompt


class HostVoiceDefaultsTests(unittest.TestCase):
    def test_new_plan_records_host_dry_tone_preset(self):
        rules = default_producer_plan("Test", "fixture_episode")["audio_rules"]
        self.assertEqual(rules["tone_preset"], "host_dry")
        self.assertEqual(rules["tone"], "host_led_dry")

    def test_section_prompt_carries_host_and_analogy_rules(self):
        prompt = _section_prompt({"episode": {"topic": "Mars"}}, {"section_index": 0}, [{}], "", 600)
        self.assertIn("ครับ", prompt)
        self.assertIn("ค่ะ", prompt)
        self.assertIn("analogy", prompt.lower())
        self.assertNotIn("calm, factual", prompt)


if __name__ == "__main__":
    unittest.main()
