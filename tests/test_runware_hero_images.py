"""Generated section openers (codex_imagegen slots) are fulfilled by Runware only with --allow-runware."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
import unittest.mock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import runware_provider
from producer_asset_producer import produce_assets

PLAN = {"beat_plans": [{"asset_plan_id": "S01B00", "selected_provider": "codex_imagegen",
                        "selected_media_type": "image", "selected_prompt": "wide nebula, no text"}]}
SCRIPT = [{"producer_asset_plan_id": "S01B00", "scene_title": "Opener", "narration": "x"}]


class RunwareHeroTests(unittest.TestCase):
    def test_without_flag_stays_a_pending_task_and_spends_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runware_provider, "generate_flux1_image") as gen:
            result = produce_assets(episode_dir=tmp, visual_asset_plan=PLAN, script=SCRIPT)
        gen.assert_not_called()
        manifest = result["asset_manifest"] if "asset_manifest" in result else result
        entry = manifest["entries"][0]
        self.assertEqual(entry["status"], "task_pending")
        self.assertIn("--allow-runware", entry["issue"])

    def test_with_flag_generates_at_hero_size(self):
        def fake_generate(prompt, output_path, api_key=None, *, width=None, height=None, model=None):
            Path(output_path).write_bytes(b"png" * 100)
            fake_generate.size = (width, height)
            return output_path

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runware_provider, "generate_flux1_image", side_effect=fake_generate):
            result = produce_assets(episode_dir=tmp, visual_asset_plan=PLAN, script=SCRIPT, allow_runware=True)
        manifest = result["asset_manifest"] if "asset_manifest" in result else result
        entry = manifest["entries"][0]
        self.assertEqual((entry["status"], entry["fulfilled_by"]), ("generated", "runware"))
        self.assertTrue(entry["generated_or_illustrative"])
        self.assertEqual(fake_generate.size[0] % 64, 0)
        self.assertGreaterEqual(fake_generate.size[0], 1920)


if __name__ == "__main__":
    unittest.main()


class RunwarePayloadTests(unittest.TestCase):
    def _task_for(self, model):
        response = unittest.mock.MagicMock()
        response.json.return_value = {"errors": [{"message": "stop here"}]}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runware_provider, "get_runware_api_key", return_value="k"), \
             patch.object(runware_provider, "get_verbose", return_value=False), \
             patch.object(runware_provider, "_http_post", return_value=response) as post:
            runware_provider.generate_flux1_image("nebula", str(Path(tmp) / "x.png"), model=model,
                                                  width=1920, height=1088)
        return post.call_args[1]["json"][0]

    def test_bfl_models_omit_sampler_controls(self):
        task = self._task_for("bfl:5@1")
        self.assertEqual((task["model"], task["width"], task["height"]), ("bfl:5@1", 1920, 1088))
        for key in ("steps", "CFGScale", "negativePrompt"):
            self.assertNotIn(key, task)

    def test_runware_models_keep_sampler_controls(self):
        task = self._task_for("runware:101@1")
        for key in ("steps", "CFGScale", "negativePrompt"):
            self.assertIn(key, task)
