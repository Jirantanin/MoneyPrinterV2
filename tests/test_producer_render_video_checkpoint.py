from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import producer_mode  # noqa: E402
import producer_renderer  # noqa: E402


class RenderVideoCheckpointTests(unittest.TestCase):
    def test_keeps_plan_edits_made_while_the_render_runs(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        episode_dir = Path(temp_dir.name)
        plan_file = producer_mode.producer_plan_path(episode_dir)
        plan_file.write_text(json.dumps({"topic": "t", "seo_packaging": {}}), encoding="utf-8")
        producer_mode.render_preflight_path(episode_dir).write_text("{}", encoding="utf-8")

        def fake_render(**_: object) -> dict:
            # The producer writes public copy into the plan while the long render runs.
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
            plan["seo_packaging"] = {"recommended_title": "ชื่อที่เขียนระหว่างเรนเดอร์"}
            plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            return {"status": "pass", "warnings": [], "errors": []}

        with mock.patch.object(producer_renderer, "orchestrate_render", side_effect=fake_render), \
                mock.patch.object(producer_mode, "write_checkpoint_html", return_value=episode_dir / "c.html"):
            producer_mode.run_render_video_checkpoint(plan_file, no_render=True)

        saved = json.loads(plan_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["seo_packaging"]["recommended_title"], "ชื่อที่เขียนระหว่างเรนเดอร์")
        self.assertEqual(saved["render"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
