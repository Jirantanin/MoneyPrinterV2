"""Regression coverage for public upload-pack metadata."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from producer_upload_pack import write_upload_pack  # noqa: E402


def _plan(*, upload_description: str = "") -> dict:
    return {
        "episode": {"topic": "โลกปิดทดสอบ", "language": "th"},
        "topic_profile": {
            "viewer_promise": "คำอธิบายจากแผน ไม่ควรถูกยกเป็น public copy ทั้งก้อน",
            "central_question": "ระบบปิดทำงานอย่างไร?",
        },
        "research": {
            "minimum_sources": 1,
            "research_summary": "สรุปผลการวิจัยสำหรับใช้ภายใน",
            "sources": [
                {
                    "title": "Primary source",
                    "publisher": "Example University",
                    "url": "https://example.edu/source",
                }
            ],
            "competitor_results": [{"title": "Comparable documentary"}],
        },
        "sections": [
            {
                "title": "บทนำ",
                "narrative_goal": "โน้ตภายในที่ไม่ควรแสดงในคำบรรยาย",
            }
        ],
        "seo_packaging": {
            "recommended_title": "โลกปิดทดสอบ: ทำไมสมดุลถึงเปลี่ยน",
            "upload_description": upload_description,
            "competitor_results": [{"title": "Comparable documentary"}],
        },
    }


class UploadPackTests(unittest.TestCase):
    def _write_pack(
        self,
        *,
        upload_description: str = "",
        render_props: dict | None = None,
    ) -> tuple[Path, dict]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        episode_dir = Path(temp_dir.name) / "episode"
        episode_dir.mkdir()
        final_video = episode_dir / "final.mp4"
        final_video.write_bytes(b"video")
        manifest = write_upload_pack(
            episode_dir=episode_dir,
            plan=_plan(upload_description=upload_description),
            final_qc={"status": "pass", "final_video_path": str(final_video)},
            cost_report={"status": "pass", "totals": {}},
            final_report_path=episode_dir / "final_report.html",
            render_props=render_props,
        )
        return episode_dir, manifest

    def test_uses_curated_copy_and_final_render_chapters(self) -> None:
        episode_dir, manifest = self._write_pack(
            upload_description=(
                "นี่คือคำอธิบายสาธารณะที่คนดูกวาดตาอ่านได้ทันที\n\n"
                "เนื้อหาชวนดูต่อโดยไม่เอาโน้ตของทีมผลิตมาแปะ"
            ),
            render_props={
                "sceneTitles": ["บทนำ", "หลักฐาน", "บทสรุป"],
                "sceneDurations": [60.0, 60.0, 60.0],
            },
        )

        self.assertEqual(manifest["status"], "ready")
        self.assertEqual(manifest["description_review"]["status"], "ready")
        self.assertEqual(manifest["description_review"]["chapter_count"], 3)
        description = (episode_dir / "upload_pack" / "description.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("นี่คือคำอธิบายสาธารณะ", description)
        self.assertNotIn("โน้ตภายใน", description)
        self.assertIn("0:00 บทนำ", description)
        self.assertIn("1:00 หลักฐาน", description)
        self.assertIn("2:00 บทสรุป", description)
        self.assertEqual(
            (episode_dir / "upload_pack" / "timestamps.txt").read_text(encoding="utf-8"),
            "0:00 บทนำ\n1:00 หลักฐาน\n2:00 บทสรุป\n",
        )
        metadata = json.loads((episode_dir / "upload_pack" / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["description_source"], "seo_packaging.upload_description")
        self.assertEqual(metadata["chapters"][1]["timestamp"], "1:00")

    def test_description_sources_follow_producer_selection(self) -> None:
        plan = _plan(upload_description="คำอธิบายสาธารณะ")
        plan["research"]["sources"] = [
            {"source_id": f"src_{i}", "title": f"Source {i}", "url": f"https://example.org/{i}"} for i in range(6)
        ]
        plan["seo_packaging"]["description_source_ids"] = ["src_5", "src_0", "src_missing"]
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        episode_dir = Path(temp_dir.name)
        write_upload_pack(episode_dir=episode_dir, plan=plan, final_qc={"status": "pass"}, render_props={})
        description = (episode_dir / "upload_pack" / "description.txt").read_text(encoding="utf-8")
        self.assertLess(description.index("Source 5"), description.index("Source 0"))
        self.assertNotIn("Source 1", description)

    def test_blocks_a_thai_description_over_youtube_byte_limit(self) -> None:
        _, manifest = self._write_pack(
            upload_description="ดาวเคราะห์น้อย " * 120,       # ~1,800 characters but over 5,000 UTF-8 bytes
            render_props={"sceneTitles": ["บทนำ", "หลักฐาน", "บทสรุป"], "sceneDurations": [60.0, 60.0, 60.0]},
        )
        self.assertEqual(manifest["status"], "blocked")
        self.assertGreater(manifest["description_review"]["bytes"], 5000)
        self.assertTrue(any("bytes" in error and "upload_description" in error for error in manifest["errors"]))

    def test_marks_pack_for_review_when_public_copy_or_chapters_are_missing(self) -> None:
        _, manifest = self._write_pack(render_props={})

        self.assertEqual(manifest["status"], "review")
        self.assertEqual(manifest["description_review"]["status"], "review")
        self.assertTrue(manifest["description_review"]["uses_generated_fallback"])
        self.assertTrue(any("upload_description" in warning for warning in manifest["warnings"]))
        self.assertTrue(any("chapter timestamps" in warning for warning in manifest["warnings"]))

    def test_fallback_never_leaks_internal_or_english_template_copy(self) -> None:
        episode_dir, _ = self._write_pack(render_props={})
        pack = episode_dir / "upload_pack"
        description = (pack / "description.txt").read_text(encoding="utf-8")
        self.assertNotIn("สรุปผลการวิจัยสำหรับใช้ภายใน", description)  # research_summary is internal
        tags = (pack / "tags.txt").read_text(encoding="utf-8")
        self.assertNotIn("PodcastV2", tags)
        self.assertNotIn("What Are", (pack / "title_options.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
