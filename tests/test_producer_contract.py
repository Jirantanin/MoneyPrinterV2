"""Offline regressions for evidence, duration, revision and output acceptance."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from producer_contract import (claim_id, claim_report, default_episode_spec, episode_spec, file_hash,
                               fingerprint, narrative_review, production_review, render_revision,
                               script_revision, validate_render_authorization)
from producer_script_writer import _script_length_qc, expand_script_package
from producer_visual_policy import visual_policy_report
from producer_render_preflight import build_render_preflight
from producer_renderer import orchestrate_render
from producer_final_qc import build_final_qc
from producer_mode import default_producer_plan, run_asset_production_checkpoint, run_tts_production_checkpoint, validate_producer_plan


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def reviewed_fixture():
    scenes = [{"narration": "ก" * 5500, "key_claims": ["A supported claim"], "source_ids": ["s1"], "section_index": 1}]
    revision = script_revision(scenes)
    plan = {"episode_spec": default_episode_spec(), "research": {"sources": [{"id": "s1", "url": "https://example.org/evidence"}]}}
    plan["claim_reviews"] = {claim_id(1, "A supported claim"): {
        "claim": "A supported claim", "script_revision": revision, "status": "verified",
        "reviewer": "fixture", "reviewed_at": "2026-09-18", "allowed_wording": "A supported claim", "limitations": "fixture",
        "evidence": [{"source_id": "s1", "source_url": "https://example.org/evidence", "excerpt": "Supporting passage",
                      "locator": "section 1", "accessed_at": "2026-09-18", "support_reason": "Fixture evidence relationship"}],
    }}
    plan["editorial_review"] = {"status": "pass", "script_revision": revision, "reviewer": "fixture", "reviewed_at": "2026-09-18",
                                "opening_test": "Specific promise", "section_progression": ["New evidence"], "ending_payoff": "Answers promise",
                                "redundancy_review": "No repeated premise", "claim_coverage_review": "All factual statements extracted"}
    return plan, scenes


class DurationAndEvidenceTests(unittest.TestCase):
    def test_new_plan_uses_one_spec_and_validates(self):
        plan = default_producer_plan("Test", "fixture_episode")
        self.assertEqual(plan["episode_spec"]["narrative"]["minimum"], 5500)
        self.assertNotIn("script_length_chars_no_space", plan["episode"])
        self.assertFalse(validate_producer_plan(plan)[0])
    def test_thai_count_excludes_english_metadata_and_whitespace(self):
        report = narrative_review("ก" * 5500 + " NASA 123 \n", {})
        self.assertEqual(report["thai_narrative_chars"], 5500)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(_script_length_qc("ก" * 5500)["status"], "pass")

    def test_inclusive_bounds_and_override(self):
        for count, status in ((5499, "blocked"), (5500, "pass"), (8000, "pass"), (8001, "blocked")):
            self.assertEqual(narrative_review("ก" * count, {})["status"], status)
        plan = {"episode_spec": {"narrative": {"minimum": 10, "maximum": 20}}}
        self.assertEqual(narrative_review("ก" * 15, plan)["status"], "pass")

    def test_test_cut_still_honors_explicit_runtime(self):
        plan = {"episode_spec": {"duration_class": "test_cut", "minimum_runtime_seconds": 60}}
        self.assertEqual(narrative_review("ก", plan, 59)["runtime_gate"], "fail")
        self.assertFalse(narrative_review("ก", plan)["ready_for_final_render_review"])
        self.assertTrue(narrative_review("ก", plan, 60)["ready_for_final_render_review"])

    def test_invalid_spec_rejected(self):
        with self.assertRaises(ValueError):
            episode_spec({"episode_spec": {"narrative": {"minimum": 9000}}})

    def test_source_mapping_does_not_pass_verification(self):
        plan, scenes = reviewed_fixture()
        plan.pop("claim_reviews")
        report = claim_report(plan, scenes)
        self.assertEqual(report["claims"][0]["status"], "mapped")
        self.assertEqual(report["status"], "needs_review")

    def test_unknown_source_is_unsupported(self):
        plan, scenes = reviewed_fixture()
        scenes[0]["source_ids"] = ["invented"]
        self.assertEqual(claim_report(plan, scenes)["claims"][0]["status"], "unsupported")

    def test_complete_current_evidence_passes_and_rewrite_invalidates_it(self):
        plan, scenes = reviewed_fixture()
        self.assertEqual(production_review(plan, scenes)["status"], "pass")
        scenes[0]["narration"] += "ข"
        self.assertEqual(production_review(plan, scenes)["status"], "blocked")

    def test_missing_extraction_or_evidence_cannot_pass(self):
        plan, scenes = reviewed_fixture()
        next(iter(plan["claim_reviews"].values()))["evidence"] = []
        self.assertEqual(claim_report(plan, scenes)["status"], "needs_review")
        scenes[0]["key_claims"] = []
        self.assertTrue(claim_report(plan, scenes)["claims"][0]["extraction_required"])

    def test_expansion_preserves_other_topics_and_does_not_pad(self):
        plan = {"episode": {"topic": "Antarctica"}, "episode_spec": {"duration_class": "test_cut"}}
        scenes = [{"narration": "กขค", "scene_title": "ทดสอบ", "image_prompt": "Ice", "producer_asset_plan_id": "S01B00"}]
        package = expand_script_package(plan, scenes)
        self.assertEqual(package["scenes"], scenes)
        self.assertTrue(package["warnings"])


class VisualTests(unittest.TestCase):
    def test_twenty_percent_slots_can_be_fifty_percent_time(self):
        slots = [{"provider": "remotion_graphic", "slot_duration_seconds": 8, "section_index": 1} for _ in range(2)]
        slots += [{"provider": "pexels", "media_type": "video", "slot_duration_seconds": 2, "section_index": 2} for _ in range(8)]
        report = visual_policy_report(slots)
        self.assertEqual(report["category_ratios"]["graphic"], 0.2)
        self.assertEqual(report["time_exposure"]["category_ratios"]["graphic"], 0.5)
        self.assertEqual(report["status"], "review")

    def test_unknown_durations_are_not_complete(self):
        self.assertEqual(visual_policy_report([{"provider": "pexels"}])["time_exposure"]["coverage"], "incomplete")

    def test_preflight_counts_selected_props_not_cached_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with wave.open(str(folder / "scene_00.wav"), "wb") as audio:
                audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 24000 * 6)
            media = folder / "scene_00_0.png"
            media.write_bytes(b"fixture" * 1000)
            manifest = {"visual_policy": {"status": "pass"}, "entries": [{
                "scene_index": 0, "asset_index": 0, "status": "generated", "local_path": str(media),
                "media_type": "image", "provider": "remotion_graphic", "slot_duration_seconds": 6,
            }]}
            with patch("producer_render_preflight._remotion_checks", return_value=[]), patch("config.get_podcast_outro_hold_seconds", return_value=0):
                report = build_render_preflight(root_dir=ROOT, episode_dir=folder, script=[{"narration": "x"}], asset_manifest=manifest)
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["visual_policy"]["category_counts"]["graphic"], 1)
            self.assertEqual(report["props_preview"]["sceneAssetDurations"], [6])


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        plan, scenes = reviewed_fixture()
        write(self.folder / "producer_plan.json", plan)
        write(self.folder / "script.json", scenes)
        (self.folder / "image.png").write_bytes(b"image one")
        (self.folder / "mix.wav").write_bytes(b"audio")
        self.preflight = {"status": "ready", "summary": {"narration_duration_seconds": 60},
                          "props_preview": {"imagePaths": [str(self.folder / "image.png")], "audioPath": str(self.folder / "mix.wav")}}
        self.revision = render_revision(self.folder, self.preflight, self.folder)
        self.authorization = {"revision": self.revision, "authorized_by": "user", "user_message": "Render this revision", "authorized_at": "2026-09-18"}
        write(self.folder / "render_authorization.json", self.authorization)

    def tearDown(self):
        self.temp.cleanup()

    def test_unchanged_revision_and_log_changes_allow_retry(self):
        attempt = validate_render_authorization(self.folder, self.preflight, self.folder)
        write(self.folder / "render_attempts.json", attempt)
        (self.folder / "producer_render.log").write_text("retrying", encoding="utf-8")
        self.assertEqual(validate_render_authorization(self.folder, self.preflight, self.folder)["count"], 2)

    def test_changed_asset_same_path_invalidates_consent(self):
        (self.folder / "image.png").write_bytes(b"image two")
        with self.assertRaisesRegex(ValueError, "authorization"):
            validate_render_authorization(self.folder, self.preflight, self.folder)

    def test_changed_props_invalidates_consent(self):
        self.preflight["props_preview"]["sceneTitles"] = ["new title"]
        with self.assertRaisesRegex(ValueError, "authorization"):
            validate_render_authorization(self.folder, self.preflight, self.folder)

    def test_retry_limit_is_bounded(self):
        write(self.folder / "render_attempts.json", {"authorization_id": fingerprint(self.authorization), "count": 3})
        with self.assertRaisesRegex(ValueError, "retries exhausted"):
            validate_render_authorization(self.folder, self.preflight, self.folder)

    def test_force_without_consent_does_not_touch_existing_output(self):
        (self.folder / "render_authorization.json").unlink()
        final = self.folder / "final.mp4"
        final.write_bytes(b"keep me")
        result = orchestrate_render(root_dir=self.folder, episode_dir=self.folder, preflight=self.preflight, force=True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(final.read_bytes(), b"keep me")

    def test_production_checkpoints_stop_before_provider_calls(self):
        plan = json.loads((self.folder / "producer_plan.json").read_text(encoding="utf-8"))
        plan.pop("claim_reviews")
        write(self.folder / "producer_plan.json", plan)
        write(self.folder / "visual_asset_plan.json", {"beat_plans": []})
        with self.assertRaisesRegex(ValueError, "unverified claims"):
            run_tts_production_checkpoint(self.folder / "producer_plan.json")
        with self.assertRaisesRegex(ValueError, "unverified claims"):
            run_asset_production_checkpoint(self.folder / "producer_plan.json")


class PrepareIntegrationTests(unittest.TestCase):
    def test_prepare_local_audio_then_authorize_in_fixture_without_rendering(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from producer_review import main
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            plan = default_producer_plan("Fixture", folder)
            evidence_plan, scenes = reviewed_fixture()
            plan.update(evidence_plan)
            write(folder / "producer_plan.json", plan)
            write(folder / "script.json", scenes)
            with wave.open(str(folder / "scene_00.wav"), "wb") as audio:
                audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 24000 * 6)
            media = folder / "scene_00_0.png"
            media.write_bytes(b"fixture" * 1000)
            write(folder / "asset_manifest.json", {"entries": [{"scene_index": 0, "asset_index": 0, "status": "downloaded", "provider": "official_media", "media_type": "image", "local_path": str(media), "source_url": "https://example.org", "slot_duration_seconds": 6}]})
            write(folder / "tts_manifest.json", {"entries": [{"scene_index": 0}]})
            with patch("producer_render_preflight._remotion_checks", return_value=[]), patch("config.get_podcast_outro_hold_seconds", return_value=0), patch("producer_renderer._background_settings", return_value={}), patch.dict("os.environ", {"PODCAST_BACKGROUND_BED_ENABLED": "false"}), patch("producer_renderer._render_remotion") as render, patch("sys.stdout"):
                with patch.object(sys, "argv", ["producer_review", "prepare", "--plan", str(folder / "producer_plan.json")]):
                    self.assertEqual(main(), 0)
                self.assertTrue((folder / "merged_audio.wav").exists())
                self.assertTrue((folder / "prepared_revision.json").exists())
                self.assertFalse((folder / "final.mp4").exists())
                with patch.object(sys, "argv", ["producer_review", "authorize", "--plan", str(folder / "producer_plan.json"), "--user-message", "TEST FIXTURE CONSENT ONLY"]):
                    self.assertEqual(main(), 0)
                preflight = json.loads((folder / "render_preflight.json").read_text(encoding="utf-8"))
                attempt = validate_render_authorization(folder, preflight, ROOT)
                self.assertEqual(attempt["count"], 1)
                render.assert_not_called()


class FinalAcceptanceTests(unittest.TestCase):
    def test_probe_success_alone_cannot_approve_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            final = folder / "final.mp4"
            final.write_bytes(b"fixture video")
            probe = {"format": {"duration": "60", "size": "10000000"}, "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "avg_frame_rate": "25/1"},
                {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"},
            ]}
            kwargs = {"episode_dir": folder, "asset_manifest": {"entries": [{"provider": "pexels", "media_type": "video", "source_url": "https://example.org"}]}, "tts_manifest": {"entries": [{}]}}
            with patch("producer_final_qc._ffprobe", return_value=(probe, "")), patch("producer_final_qc._minimum_render_bytes", return_value=0), patch("producer_final_qc.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                report = build_final_qc(**kwargs)
                self.assertNotEqual(report["status"], "pass")
                for category, mode in (("visual", "video"), ("listening", "audio"), ("editorial", "story")):
                    write(folder / f"{category}_qc.json", {"status": "pass", "reviewed_sha256": file_hash(final), "reviewer": "fixture", "reviewed_at": "2026-09-18", "coverage_notes": "Full fixture inspected", "unreviewed_ranges": [], "samples": [{"start_seconds": 0, "end_seconds": 60, "mode": mode, "status": "pass", "observation": "Fixture inspection"}]})
                accepted = build_final_qc(**kwargs)
                self.assertEqual(accepted["status"], "pass")
                final.write_bytes(b"changed output")
                self.assertEqual(build_final_qc(**kwargs)["acceptance"]["listening"]["status"], "review")


if __name__ == "__main__":
    unittest.main()
