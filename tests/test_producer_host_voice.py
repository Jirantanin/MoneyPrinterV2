"""New episodes keep the Knox host_dry delivery; since 2026-10-13 the LLM drafter writes for a เรา narrator (no ผม)
with analogies, one recurring metaphor and labelled what-if frames."""
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

    def test_section_prompt_carries_narrator_and_analogy_rules(self):
        prompt = _section_prompt({"episode": {"topic": "Mars"}}, {"section_index": 0}, [{}], "", 600)
        self.assertIn("ครับ", prompt)
        self.assertIn("ค่ะ", prompt)
        self.assertIn("analogy", prompt.lower())
        self.assertNotIn("calm, factual", prompt)
        self.assertIn("never use ผม", prompt.lower())
        self.assertNotIn("male Thai host", prompt)
        self.assertIn("recurring metaphor", prompt)
        self.assertIn("สมมติว่า", prompt)


if __name__ == "__main__":
    unittest.main()
