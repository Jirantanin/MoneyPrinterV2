"""Offline tests for the minimal documentary renderer: timeline building, revision binding, dispatch."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from producer_contract import render_revision
from producer_minimal_renderer import OVERRIDES_FILE, build_timeline, classify_asset, end_card_sources
import producer_minimal_renderer
import producer_renderer


def make_image(path: Path, size: tuple[int, int], color=(20, 30, 40)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def props_for(paths: list[Path], *, counts, scene_durations, titles, fits=None, types=None, outro=3.0):
    per_asset = []
    for count, duration in zip(counts, scene_durations):
        per_asset += [round(duration / count, 3)] * count
    return {
        "imagePaths": [str(p) for p in paths], "sceneImageCounts": counts, "sceneDurations": scene_durations,
        "sceneTitles": titles, "sceneAssetDurations": per_asset, "durationInSeconds": sum(scene_durations),
        "sceneAssetFits": fits or ["cover"] * len(paths), "sceneAssetTypes": types or ["image"] * len(paths),
        "sceneAssetQualifications": ["ภาพจำลอง — ไม่ใช่ภาพจริง"] * len(paths),
        "sceneAssetCredits": ["NASA/JPL-Caltech"] * len(paths),
    }


class ClassifyTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify_asset("cover", 1920, 1080, 40), "cover")
        self.assertEqual(classify_asset("cover", 3600, 4500, 40), "plate")      # portrait
        self.assertEqual(classify_asset("cover", 1600, 1600, 40), "plate")      # small square
        self.assertEqual(classify_asset("cover", 3300, 3300, 40), "cover")      # large square crops fine
        self.assertEqual(classify_asset("cover", 1500, 558, 40), "plate")       # very wide
        self.assertEqual(classify_asset("cover", 1041, 585, 40), "plate")       # would be upscaled
        self.assertEqual(classify_asset("contain", 1920, 1080, 30), "slide")    # dark explainer slide
        self.assertEqual(classify_asset("contain", 850, 500, 230), "figure")    # light research figure


class EndCardTests(unittest.TestCase):
    def test_citations_deduplicated_and_agencies_collected(self):
        lines = end_card_sources([
            "K. L. Luhman; C. Alves de Oliveira (2025), Fig. 1 | CC BY 4.0",
            "Luhman & Alves de Oliveira (2025), ApJL 986 L14, Fig. 12",
            "Richard J. Parker; Catarina Alves de Oliveira (2026), Fig. 5",
            "NASA, ESA, CSA, STScI",
            "NASA/JPL-Caltech/UCLA",
            "",
        ])
        self.assertEqual(lines, ["Luhman & Alves de Oliveira (2025), ApJL 986 L14",
                                 "Richard J. Parker; Catarina Alves de Oliveira (2026)",
                                 "NASA · ESA · CSA · STScI · JPL-Caltech"])


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.images = [make_image(self.dir / f"a{i}.png", (1920, 1080)) for i in range(4)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_chapters_follow_title_changes_and_last_shot_holds(self):
        props = props_for(self.images, counts=[2, 1, 1], scene_durations=[10.0, 5.0, 8.0], titles=["A", "A", "B"])
        tl = build_timeline(props, narration_end=20.0, assets_dir=self.dir / "assets")
        self.assertEqual([(c["no"], c["title"], c["start"]) for c in tl["chapters"]], [(1, "A", 0.0), (2, "B", 15.0)])
        self.assertEqual(tl["shots"][-1]["end"], 23.0)
        self.assertEqual(tl["narrationEnd"], 20.0)
        self.assertEqual((tl["shots"][0]["capTitle"], tl["shots"][0]["capSub"]), ("ภาพจำลอง", "ไม่ใช่ภาพจริง"))
        self.assertTrue(tl["endNote"])
        self.assertTrue(all(Path(s["src"].replace("file:///", "")).is_file() for s in tl["shots"]))

    def test_overrides_apply(self):
        props = props_for(self.images[:1], counts=[1], scene_durations=[5.0], titles=["A"])
        overrides = {"assets": {"a0.png": {"kind": "plate", "anchor": [0.9, 0.1], "zoom": [1.3, 1.4], "caption_title": "X"}},
                     "end_card": {"sources": ["S"], "note": ""}}
        shot = build_timeline(props, narration_end=5.0, assets_dir=self.dir / "assets", overrides=overrides)
        self.assertEqual((shot["shots"][0]["kind"], shot["shots"][0]["anchor"], shot["shots"][0]["zoom"],
                          shot["shots"][0]["capTitle"]), ("plate", [0.9, 0.1], [1.3, 1.4], "X"))
        self.assertIsNotNone(shot["shots"][0]["blur"])
        self.assertEqual((shot["sources"], shot["endNote"]), (["S"], ""))

    def test_video_frames_play_once_and_short_clips_warn(self):
        clip = self.dir / "b.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=2",
                        "-pix_fmt", "yuv420p", str(clip)], check=True)
        props = props_for([self.images[0], clip], counts=[2], scene_durations=[8.0], titles=["A"], types=["image", "video"])
        tl = build_timeline(props, narration_end=8.0, assets_dir=self.dir / "assets")
        video = tl["shots"][1]
        self.assertEqual(video["kind"], "video")
        self.assertEqual(video["frameCount"], 50)                       # 2 s at 25 fps, not looped
        self.assertTrue(Path(video["src"].replace("file:///", "")).is_file())
        self.assertTrue(any("last frame holds" in w for w in tl["warnings"]))
        with Image.open(video["src"].replace("file:///", "")) as frame:
            self.assertEqual(frame.size, (1920, 1080))
        self.assertIsNone(video["zoom"])                                 # player default push 1.00 -> 1.03
        held = build_timeline(props, narration_end=8.0, assets_dir=self.dir / "assets",
                              overrides={"assets": {"b.mp4": {"zoom": [1, 1]}}})["shots"][1]
        self.assertEqual(held["zoom"], [1, 1])

    def test_rejects_unknown_types_and_inconsistent_props(self):
        props = props_for(self.images[:2], counts=[2], scene_durations=[6.0], titles=["A"], types=["image", "audio"])
        with self.assertRaises(ValueError):
            build_timeline(props, narration_end=6.0, assets_dir=self.dir / "assets")
        props = props_for(self.images[:2], counts=[2], scene_durations=[6.0], titles=["A"])
        props["sceneImageCounts"] = [3]
        with self.assertRaises(ValueError):
            build_timeline(props, narration_end=6.0, assets_dir=self.dir / "assets")


class RevisionAndDispatchTests(unittest.TestCase):
    def test_renderer_choice_and_overrides_are_bound_into_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            episode = Path(tmp)
            base = {"props_preview": {"imagePaths": []}, "summary": {}}
            minimal = {"props_preview": {"imagePaths": [], "renderer": "minimal_doc"}, "summary": {}}
            r_default, r_minimal = render_revision(episode, base, ROOT), render_revision(episode, minimal, ROOT)
            self.assertNotEqual(r_default, r_minimal)
            (episode / OVERRIDES_FILE).write_text(json.dumps({"assets": {}}), encoding="utf-8")
            self.assertNotEqual(render_revision(episode, minimal, ROOT), r_minimal)
            self.assertEqual(render_revision(episode, base, ROOT), r_default)   # remotion revisions untouched

    def test_orchestrate_dispatches_to_minimal_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            episode = Path(tmp)
            audio = episode / "merged_audio_with_bed.wav"
            audio.write_bytes(b"0" * 1000)
            preflight = {"status": "ready", "summary": {"scene_count": 1, "render_duration_seconds": 13.0,
                                                         "outro_hold_seconds": 3.0},
                         "props_preview": {"renderer": "minimal_doc", "audioPath": str(audio), "imagePaths": []}}
            calls = {}

            def fake_minimal(**kwargs):
                calls.update(kwargs)
                Path(kwargs["raw_props"]["outputPath"]).write_bytes(b"0" * 2_000_000)
                return {"renderer": "minimal_doc"}

            def fake_normalize(src, dst, log, minimum):
                Path(dst).write_bytes(Path(src).read_bytes())

            with patch("producer_contract.validate_render_authorization", return_value={"revision": "r"}), \
                 patch.object(producer_minimal_renderer, "render_minimal_doc", side_effect=fake_minimal), \
                 patch.object(producer_renderer, "_render_remotion") as remotion, \
                 patch.object(producer_renderer, "_normalize_rendered_audio", side_effect=fake_normalize):
                manifest = producer_renderer.orchestrate_render(root_dir=ROOT, episode_dir=episode, preflight=preflight)
            remotion.assert_not_called()
            self.assertEqual(manifest["status"], "complete", manifest.get("errors"))
            self.assertEqual(manifest["renderer"], "minimal_doc")
            self.assertEqual(calls["narration_end"], 10.0)


class RelativeEpisodePathTests(unittest.TestCase):
    def test_node_receives_absolute_paths_for_a_relative_episode_dir(self):
        calls = []
        timeline = {"shots": [], "chapters": [], "warnings": []}
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp,              patch.object(producer_minimal_renderer, "environment_checks", return_value=[]),              patch.object(producer_minimal_renderer, "build_timeline", return_value=timeline),              patch.object(producer_minimal_renderer, "find_chrome", return_value=Path("chrome.exe")),              patch.object(producer_minimal_renderer, "_run", side_effect=lambda args, **kw: calls.append(args)):
            relative = Path(tmp).relative_to(ROOT)
            producer_minimal_renderer.render_minimal_doc(
                root_dir=ROOT, episode_dir=relative, raw_props={"outputPath": "o.mp4", "audioPath": "a.wav"},
                narration_end=1.0, timeout_seconds=10, log_path=Path(tmp) / "log.txt")
        node = calls[0]
        for flag in ("--timeline", "--work", "--out"):
            self.assertTrue(Path(node[node.index(flag) + 1]).is_absolute(), flag)


if __name__ == "__main__":
    unittest.main()
