"""Upload pack metadata writer for PodcastV2 Producer Mode."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UPLOAD_PACK_VERSION = 1
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS = 24


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or fallback


def _compact(value: Any, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _compact_multiline(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _source_lines(research: dict[str, Any], *, limit: int = 8) -> list[str]:
    sources = _as_list(research.get("sources"))
    rows: list[str] = []
    for source in sources[:limit]:
        if not isinstance(source, dict):
            continue
        title = _clean_text(source.get("title"), "Untitled source")
        url = _clean_text(source.get("url") or source.get("source_url"))
        publisher = _clean_text(source.get("publisher") or source.get("source_type"))
        if url:
            rows.append(f"- {title} ({publisher})\n  {url}".strip())
    return rows


def _section_lines(sections: list[Any], *, limit: int = 8) -> list[str]:
    rows: list[str] = []
    for section in sections[:limit]:
        if not isinstance(section, dict):
            continue
        title = _clean_text(section.get("title"), "Untitled section")
        goal = _clean_text(section.get("narrative_goal"))
        rows.append(f"- {title}{f': {goal}' if goal else ''}")
    return rows


def _hash_token(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u0E00-\u0E7F]+", "", str(value or ""))
    return text[:40]


def _topic_tokens(topic: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9\u0E00-\u0E7F]{3,}", topic)
    stop = {"the", "and", "for", "with", "จาก", "และ", "หรือ", "คือ"}
    result: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered in stop or lowered in result:
            continue
        result.append(lowered)
    return result[:8]


def _hashtags(topic: str, title: str) -> list[str]:
    base = ["สารคดี", "เล่าเรื่อง", "ความรู้"]
    for token in _topic_tokens(f"{topic} {title}")[:5]:
        clean = _hash_token(token)
        if clean and clean not in base:
            base.append(clean)
    tags = [f"#{item}" for item in base if item]
    return tags[:8]


def _tags(topic: str, title: str, sections: list[Any]) -> list[str]:
    tags = ["สารคดี", "เล่าเรื่อง", "ความรู้", "PodcastV2", "documentary"]
    for token in _topic_tokens(f"{topic} {title}"):
        if token not in tags:
            tags.append(token)
    for section in sections[:6]:
        if isinstance(section, dict):
            title_text = _clean_text(section.get("title"))
            if title_text and title_text.lower() not in [item.lower() for item in tags]:
                tags.append(title_text)
    cleaned: list[str] = []
    for tag in tags:
        text = _compact(tag, 60)
        if text and text.lower() not in [item.lower() for item in cleaned]:
            cleaned.append(text)
    return cleaned[:MAX_TAGS]


def _title_options(seo: dict[str, Any], topic: str) -> list[dict[str, str]]:
    options = [
        item for item in _as_list(seo.get("title_options")) if isinstance(item, dict)
    ]
    if options:
        return [
            {
                "role": _clean_text(item.get("role"), "option"),
                "title": _compact(item.get("title"), MAX_TITLE_LENGTH),
                "rationale": _clean_text(item.get("rationale")),
            }
            for item in options[:3]
        ]
    return [
        {
            "role": "curiosity_question",
            "title": _compact(f"{topic}: What Are We Missing?", MAX_TITLE_LENGTH),
            "rationale": "Fallback curiosity angle; replace after SEO research if needed.",
        },
        {
            "role": "concrete_stakes",
            "title": _compact(f"{topic}: The Part That Changes the Story", MAX_TITLE_LENGTH),
            "rationale": "Fallback stakes angle; replace after SEO research if needed.",
        },
        {
            "role": "documentary_trust",
            "title": _compact(f"{topic}, Explained Without Hype", MAX_TITLE_LENGTH),
            "rationale": "Fallback documentary trust angle.",
        },
    ]


def _thumbnail_concepts(seo: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    concepts = [
        item for item in _as_list(seo.get("thumbnail_concept_options")) if isinstance(item, dict)
    ]
    if concepts:
        return concepts[:3]
    return [
        {
            "concept": "curiosity",
            "composition": f"One clear focal visual for {topic}, high contrast, clean empty area for short Thai text.",
            "text_overlay": "คำถามสั้น",
            "avoid": ["fake evidence", "crowded text", "misleading logos"],
        },
        {
            "concept": "stakes",
            "composition": f"Show scale or consequence connected to {topic}, with a before/after or near/far contrast.",
            "text_overlay": "จุดเปลี่ยน",
            "avoid": ["fearmongering", "red alert styling", "brand clutter"],
        },
        {
            "concept": "documentary_trust",
            "composition": f"Use factual source-led imagery for {topic}; restrained documentary tone.",
            "text_overlay": "อธิบายให้ชัด",
            "avoid": ["sensational expressions", "fake documents", "overdesigned collage"],
        },
    ]


def _description(
    *,
    topic: str,
    title: str,
    topic_profile: dict[str, Any],
    research: dict[str, Any],
    sections: list[Any],
    hashtags: list[str],
) -> str:
    viewer_promise = _clean_text(topic_profile.get("viewer_promise"))
    central_question = _clean_text(topic_profile.get("central_question"))
    summary = _clean_text(research.get("research_summary"))
    section_rows = _section_lines(sections)
    source_rows = _source_lines(research)

    parts = [
        title,
        "",
        viewer_promise or f"ตอนนี้เล่าเรื่อง {topic} ด้วยโทนสารคดีที่อิงจากแหล่งข้อมูลจริง",
    ]
    if central_question:
        parts.extend(["", f"คำถามหลัก: {central_question}"])
    if summary:
        parts.extend(["", _compact(summary, 900)])
    if section_rows:
        parts.extend(["", "ในตอนนี้:", *section_rows])
    if source_rows:
        parts.extend(["", "แหล่งอ้างอิงหลัก:", *source_rows])
    parts.extend(["", " ".join(hashtags)])
    return _compact_multiline("\n".join(parts).strip(), MAX_DESCRIPTION_LENGTH)


def _pinned_comment(topic_profile: dict[str, Any], topic: str) -> str:
    question = _clean_text(topic_profile.get("central_question"))
    if question:
        return f"คุณคิดว่าแก่นของเรื่องนี้คืออะไร: {question}"
    return f"คุณคิดว่าเรื่อง {topic} มีมุมไหนที่ควรเล่าต่ออีก?"


def _thumbnail_html(concepts: list[dict[str, Any]]) -> str:
    cards = []
    for concept in concepts:
        avoid = concept.get("avoid") if isinstance(concept.get("avoid"), list) else []
        cards.append(
            "<article>"
            f"<h2>{html.escape(str(concept.get('concept') or 'concept'))}</h2>"
            f"<p>{html.escape(str(concept.get('composition') or ''))}</p>"
            f"<p><strong>Text:</strong> {html.escape(str(concept.get('text_overlay') or ''))}</p>"
            f"<p><strong>Avoid:</strong> {html.escape(', '.join(str(item) for item in avoid))}</p>"
            "</article>"
        )
    return """<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Thumbnail Brief</title>
  <style>
    body { margin: 0; background: #101316; color: #eef2f4; font: 15px/1.55 "Segoe UI", Arial, sans-serif; }
    main { width: min(980px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 44px; }
    article { border: 1px solid #323b45; border-radius: 8px; background: #181d22; padding: 16px; margin: 14px 0; }
    h1, h2 { line-height: 1.2; }
    h1 { font-size: 28px; }
    h2 { font-size: 18px; }
    p { margin: 8px 0; }
  </style>
</head>
<body>
  <main>
    <h1>Thumbnail Brief</h1>
    """ + "\n".join(cards) + """
  </main>
</body>
</html>
"""


def write_upload_pack(
    *,
    episode_dir: str | Path,
    plan: dict[str, Any],
    final_qc: dict[str, Any] | None = None,
    cost_report: dict[str, Any] | None = None,
    final_report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write upload-ready metadata files under upload_pack/."""

    episode_path = Path(episode_dir)
    pack_dir = episode_path / "upload_pack"
    topic_profile = _as_dict(plan.get("topic_profile"))
    research = _as_dict(plan.get("research"))
    seo = _as_dict(plan.get("seo_packaging"))
    episode = _as_dict(plan.get("episode"))
    sections = _as_list(plan.get("sections"))
    final_qc = _as_dict(final_qc)
    cost_report = _as_dict(cost_report)
    topic = _clean_text(episode.get("topic"), episode_path.name)

    title_options = _title_options(seo, topic)
    recommended_title = _clean_text(seo.get("recommended_title")) or title_options[0]["title"]
    recommended_title = _compact(recommended_title, MAX_TITLE_LENGTH)
    hashtags = _hashtags(topic, recommended_title)
    tags = _tags(topic, recommended_title, sections)
    description = _description(
        topic=topic,
        title=recommended_title,
        topic_profile=topic_profile,
        research=research,
        sections=sections,
        hashtags=hashtags,
    )
    pinned_comment = _pinned_comment(topic_profile, topic)
    thumbnail_concepts = _thumbnail_concepts(seo, topic)
    final_video = final_qc.get("final_video_path") or episode_path / "final.mp4"
    final_report = str(final_report_path or episode_path / "final_report.html")

    warnings: list[str] = []
    errors: list[str] = []
    if not Path(str(final_video)).exists():
        errors.append(f"final video missing: {final_video}")
    if final_qc.get("status") not in {"pass", "review"}:
        warnings.append(f"final QC status is {final_qc.get('status') or 'missing'}")
    if cost_report.get("status") not in {"pass", "ready", ""}:
        warnings.append(f"cost report status is {cost_report.get('status') or 'missing'}")
    if not seo.get("recommended_title"):
        warnings.append("recommended title came from fallback title options.")
    competitor_results = _as_list(research.get("competitor_results")) or _as_list(
        seo.get("competitor_results")
    )
    if not competitor_results:
        warnings.append("competitor SEO results are missing or empty.")
    if len(_as_list(research.get("sources"))) < int(research.get("minimum_sources") or 3):
        warnings.append("source count is below the research minimum.")

    metadata = {
        "title": recommended_title,
        "description": description,
        "tags": tags,
        "hashtags": hashtags,
        "pinned_comment": pinned_comment,
        "language": episode.get("language") or "th",
        "final_video_path": str(final_video),
        "final_report_path": final_report,
        "thumbnail_brief_path": str(pack_dir / "thumbnail_brief.html"),
    }
    thumbnail_brief = {
        "topic": topic,
        "recommended_title": recommended_title,
        "concepts": thumbnail_concepts,
        "source_policy": "Prefer official/verified media for factual thumbnails; do not fake evidence.",
        "generated_thumbnail_default": False,
    }
    pack_manifest = {
        "schema_version": UPLOAD_PACK_VERSION,
        "stage": "upload_pack",
        "created_at": _utc_now(),
        "status": "blocked" if errors else ("review" if warnings else "ready"),
        "episode_dir": str(episode_path),
        "metadata": metadata,
        "title_options": title_options,
        "thumbnail_brief": thumbnail_brief,
        "cost_summary": _as_dict(cost_report.get("totals")),
        "warnings": warnings,
        "errors": errors,
    }

    pack_dir.mkdir(parents=True, exist_ok=True)
    _write_json(pack_dir / "metadata.json", metadata)
    _write_json(pack_dir / "upload_pack_manifest.json", pack_manifest)
    _write_text(pack_dir / "description.txt", description + "\n")
    _write_text(pack_dir / "tags.txt", ", ".join(tags) + "\n")
    _write_text(pack_dir / "hashtags.txt", " ".join(hashtags) + "\n")
    _write_text(pack_dir / "pinned_comment.txt", pinned_comment + "\n")
    _write_text(
        pack_dir / "title_options.txt",
        "\n".join(f"{item['role']}: {item['title']}" for item in title_options) + "\n",
    )
    _write_json(pack_dir / "thumbnail_brief.json", thumbnail_brief)
    _write_text(pack_dir / "thumbnail_brief.html", _thumbnail_html(thumbnail_concepts))
    _write_text(
        pack_dir / "README.md",
        "\n".join(
            [
                "# Upload Pack",
                "",
                f"- Title: {recommended_title}",
                f"- Final video: {final_video}",
                f"- Final report: {final_report}",
                "- Use metadata.json for uploader compatibility.",
                "- Use thumbnail_brief.html/json for thumbnail production.",
                "",
            ]
        ),
    )

    root_metadata_path = episode_path / "metadata.json"
    existing: dict[str, Any] = {}
    if root_metadata_path.exists():
        try:
            with root_metadata_path.open("r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
            existing = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            existing = {}
    merged_metadata = {**existing, **metadata}
    _write_json(root_metadata_path, merged_metadata)

    files = {
        "upload_pack_dir": str(pack_dir),
        "metadata": str(pack_dir / "metadata.json"),
        "root_metadata": str(root_metadata_path),
        "manifest": str(pack_dir / "upload_pack_manifest.json"),
        "description": str(pack_dir / "description.txt"),
        "tags": str(pack_dir / "tags.txt"),
        "hashtags": str(pack_dir / "hashtags.txt"),
        "pinned_comment": str(pack_dir / "pinned_comment.txt"),
        "title_options": str(pack_dir / "title_options.txt"),
        "thumbnail_brief_json": str(pack_dir / "thumbnail_brief.json"),
        "thumbnail_brief_html": str(pack_dir / "thumbnail_brief.html"),
        "readme": str(pack_dir / "README.md"),
    }
    pack_manifest["files"] = files
    _write_json(pack_dir / "upload_pack_manifest.json", pack_manifest)
    return pack_manifest
