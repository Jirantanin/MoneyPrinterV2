"""Episode-level b-roll search terms and Pexels rendition selection."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pexels_provider
import producer_broll_expander as expander

# Narration containing "คืน"/"เงา" used to trigger the sleep-episode stock table.
SCENES = [{"producer_asset_plan_id": "S01B00", "section_index": 1, "section_title": "ดาว",
           "scene_title": "ดาว", "narration": "คืนนั้นเงาของวงแหวนผ่านหน้าดาว"}]


class EpisodeKeywordTests(unittest.TestCase):
    def test_without_file_builtin_tables_still_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenes = expander._apply_episode_broll_keywords(Path(tmp), SCENES)
        self.assertIn("alarm clock bedroom night", expander._stock_keyword_pool(scenes[0]))

    def test_episode_file_overrides_stock_and_official_queries(self):
        config = {"official_queries": ["Chariklo"], "official_markers": ["chariklo"], "official_blocked": ["mars"],
                  "stock_by_section": {"1": ["observatory telescope night"]}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "broll_keywords.json").write_text(json.dumps(config), encoding="utf-8")
            scenes = expander._apply_episode_broll_keywords(Path(tmp), SCENES)
        self.assertEqual(expander._stock_keyword_pool(scenes[0]), ["observatory telescope night"])
        self.assertEqual(expander._build_official_queries(scenes), ["Chariklo"])
        self.assertNotIn("_episode_stock_keywords", SCENES[0])  # source script is not mutated


class PexelsRenditionTests(unittest.TestCase):
    def test_null_quality_falls_back_to_largest_1080p_landscape(self):
        files = [{"quality": None, "width": w, "height": h, "link": f"https://x/{w}.mp4"}
                 for w, h in ((640, 360), (1920, 1080), (3840, 2160), (1080, 1920))]
        search = MagicMock(); search.json.return_value = {"videos": [{"id": 42, "url": "https://www.pexels.com/video/ice-42/",
                                                 "user": {"name": "Ann"}, "video_files": files}]}
        download = MagicMock(); download.iter_content.return_value = [b"x" * 20_000]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pexels_provider, "_http_get", side_effect=[search, download]) as get, \
             patch.object(pexels_provider, "append_api_usage"), \
             patch.object(pexels_provider.subprocess, "run",
                          side_effect=lambda cmd, **kw: (Path(cmd[-1]).write_bytes(b"y" * 20_000), MagicMock(returncode=0))[1]):
            selection: dict = {}
            out = pexels_provider.search_pexels_video("x", "key", str(Path(tmp) / "o.mp4"), 7.0, keyword="ice",
                                                      selection=selection)
        self.assertTrue(out)
        self.assertEqual(selection["source_url"], "https://www.pexels.com/video/ice-42/")
        self.assertEqual(selection["credit"], "Ann / Pexels")
        self.assertEqual(get.call_args_list[1].args[0], "https://x/1920.mp4")


class MissingKeywordFileTests(unittest.TestCase):
    def test_stock_expansion_stops_without_episode_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                expander.expand_broll_timeline(episode_dir=tmp, script=SCENES, asset_manifest={"entries": []},
                                               allow_stock=True)
        self.assertIn("broll_keywords.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
