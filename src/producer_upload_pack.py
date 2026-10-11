"""Upload pack metadata writer for PodcastV2 Producer Mode."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UPLOAD_PACK_VERSION = 2
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS = 24
MAX_DESCRIPTION_SOURCES = 8
MIN_CHAPTER_COUNT = 3


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


def _clean_multiline(value: Any, fallback: str = "") -> str:
    """Normalize public copy while preserving intentional paragraph breaks."""

    lines: list[str] = []
    previous_blank = True
    for raw_line in str(value or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
            previous_blank = False
        elif lines and not previous_blank:
            lines.append("")
            previous_blank = True
    return "\n".join(lines).strip() or fallback


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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_lines(research: dict[str, Any], *, source_ids: list[Any] | None = None, limit: int = 4) -> list[str]:
    sources = [source for source in _as_list(research.get("sources")) if isinstance(source, dict)]
    if source_ids:
        # Producer-chosen order (seo_packaging.description_source_ids); research order is not a ranking.
        by_id = {_clean_text(source.get("source_id")): source for source in sources}
        sources = [by_id[key] for key in (_clean_text(item) for item in source_ids) if key in by_id]
        limit = MAX_DESCRIPTION_SOURCES
    rows: list[str] = []
    for source in sources[:limit]:
        if not isinstance(source, dict):
            continue
        title = _clean_text(source.get("title"), "Untitled source")
        url = _clean_text(source.get("url") or source.get("source_url"))
        publisher = _clean_text(source.get("publisher") or source.get("source_type"))
        if url:
            publisher_label = f" ({publisher})" if publisher else ""
            rows.append(f"- {title}{publisher_label}\n  {url}".strip())
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
    # Splitting the topic produced fragments such as "#วงแหวนที่มองไม่เห็นของ"; producers set
    # seo_packaging.hashtags, and the fallback stays generic.
    return ["#สารคดี", "#ความรู้"]


def _tags(topic: str, title: str, sections: list[Any]) -> list[str]:
    # Fallback only: section titles are viewer-facing Thai; topic/title fragments and internal
    # labels (e.g. "PodcastV2") are not tags.
    tags = ["สารคดี", "ความรู้", "documentary"]
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
    # No English template suffixes on a Thai channel; a missing title is a packaging warning.
    return [
        {
            "role": "fallback_topic",
            "title": _compact(topic, MAX_TITLE_LENGTH),
            "rationale": "Fallback: write seo_packaging.title_options before publishing.",
        }
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


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _chapters_from_render_props(render_props: dict[str, Any]) -> list[dict[str, Any]]:
    """Build YouTube chapter rows from the final renderer-facing scene contract."""

    titles = _as_list(render_props.get("sceneTitles"))
    durations = _as_list(render_props.get("sceneDurations"))
    if not titles or len(titles) != len(durations):
        return []

    chapters: list[dict[str, Any]] = []
    elapsed = 0.0
    previous_timestamp = ""
    previous_title = ""
    for index, (raw_title, raw_duration) in enumerate(zip(titles, durations), start=1):
        title = _clean_text(raw_title)
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            return []
        if not title or duration <= 0:
            return []
        timestamp = _format_timestamp(elapsed)
        # Render props contain one entry per narration scene.  Consecutive
        # scenes frequently belong to the same editorial chapter, so emit one
        # viewer-facing YouTube marker at the first occurrence rather than a
        # run of identical timestamp labels.
        if timestamp != previous_timestamp and title != previous_title:
            chapters.append(
                {
                    "index": index,
                    "start_seconds": round(elapsed, 3),
                    "timestamp": timestamp,
                    "title": title,
                }
            )
            previous_timestamp = timestamp
            previous_title = title
        elapsed += duration
    return chapters


def _chapter_lines(chapters: list[dict[str, Any]]) -> list[str]:
    return [f"{item['timestamp']} {item['title']}" for item in chapters]


def _fallback_description(
    *,
    topic: str,
    topic_profile: dict[str, Any],
    research: dict[str, Any],
) -> str:
    """Keep the fallback audience-facing; never expose internal section goals."""

    viewer_promise = _clean_text(topic_profile.get("viewer_promise"))
    central_question = _clean_text(topic_profile.get("central_question"))
    # research_summary is internal (often English) and never public copy.
    paragraphs = [viewer_promise] if viewer_promise else []
    if not paragraphs and central_question:
        paragraphs.append(f"ตอนนี้ชวนหาคำตอบว่า {central_question}")
    if not paragraphs:
        paragraphs.append(f"ตอนนี้พาไปสำรวจ {topic} ผ่านข้อมูลและแหล่งอ้างอิงที่ตรวจสอบได้")
    return "\n\n".join(paragraphs)


def _description(
    *,
    topic: str,
    topic_profile: dict[str, Any],
    research: dict[str, Any],
    public_copy: str,
    chapters: list[dict[str, Any]],
    hashtags: list[str],
    source_ids: list[Any] | None = None,
) -> str:
    body = _clean_multiline(public_copy) or _fallback_description(
        topic=topic,
        topic_profile=topic_profile,
        research=research,
    )
    source_rows = _source_lines(research, source_ids=source_ids)

    parts = [body]
    if chapters:
        parts.extend(["", "ช่วงเวลาในคลิป:", *_chapter_lines(chapters)])
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
    render_props: dict[str, Any] | None = None,
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
    render_props = _as_dict(render_props)
    topic = _clean_text(episode.get("topic"), episode_path.name)
    root_metadata_path = episode_path / "metadata.json"
    existing_metadata = _read_json(root_metadata_path)

    title_options = _title_options(seo, topic)
    recommended_title = _clean_text(seo.get("recommended_title")) or title_options[0]["title"]
    recommended_title = _compact(recommended_title, MAX_TITLE_LENGTH)
    custom_hashtags: list[str] = []
    for value in _as_list(seo.get("hashtags")):
        token = _hash_token(_clean_text(value).lstrip("#"))
        hashtag = f"#{token}" if token else ""
        if hashtag and hashtag.lower() not in [item.lower() for item in custom_hashtags]:
            custom_hashtags.append(hashtag)
    hashtags = custom_hashtags[:8] or _hashtags(topic, recommended_title)

    custom_tags: list[str] = []
    for value in _as_list(seo.get("tags")):
        tag = _compact(value, 60)
        if tag and tag.lower() not in [item.lower() for item in custom_tags]:
            custom_tags.append(tag)
    tags = custom_tags[:MAX_TAGS] or _tags(topic, recommended_title, sections)
    public_copy = _clean_multiline(seo.get("upload_description"))
    description_source = "seo_packaging.upload_description"
    if not public_copy and _clean_text(existing_metadata.get("description_source")) in {"authored", "manual"}:
        public_copy = _clean_multiline(existing_metadata.get("description"))
        description_source = "existing_metadata.authored"
    if not public_copy:
        description_source = "generated_fallback"
    chapters = _chapters_from_render_props(render_props)
    description = _description(
        topic=topic,
        topic_profile=topic_profile,
        research=research,
        public_copy=public_copy,
        chapters=chapters,
        hashtags=hashtags,
        source_ids=_as_list(seo.get("description_source_ids")),
    )
    pinned_comment = _clean_multiline(seo.get("pinned_comment")) or _pinned_comment(
        topic_profile,
        topic,
    )
    thumbnail_concepts = _thumbnail_concepts(seo, topic)
    final_video = final_qc.get("final_video_path") or episode_path / "final.mp4"
    final_report = str(final_report_path or episode_path / "final_report.html")

    warnings: list[str] = []
    errors: list[str] = []
    if not Path(str(final_video)).exists():
        errors.append(f"final video missing: {final_video}")
    if final_qc.get("status") not in {"pass", "review"}:
        warnings.append(f"final QC status is {final_qc.get('status') or 'missing'}")
    # A cost report may be in review solely because an external or unmetered
    # provider does not expose a local price signal.  Preserve that disclosure
    # in the handoff manifest, but do not block otherwise complete public
    # upload metadata.  Actual report errors remain a packaging warning.
    cost_status = _clean_text(cost_report.get("status"))
    cost_errors = _as_list(cost_report.get("errors"))
    if cost_status not in {"pass", "ready", "review", ""} or cost_errors:
        warnings.append(f"cost report status is {cost_status or 'missing'}")
    if not seo.get("recommended_title"):
        warnings.append("recommended title came from fallback title options.")
    competitor_results = _as_list(research.get("competitor_results")) or _as_list(
        seo.get("competitor_results")
    )
    if not competitor_results:
        warnings.append("competitor SEO results are missing or empty.")
    if len(_as_list(research.get("sources"))) < int(research.get("minimum_sources") or 3):
        warnings.append("source count is below the research minimum.")
    if description_source == "generated_fallback":
        warnings.append(
            "seo_packaging.upload_description is missing; generated fallback description requires public-copy review."
        )
    if len(chapters) < MIN_CHAPTER_COUNT:
        warnings.append(
            "chapter timestamps are missing or incomplete; final render_props scene titles and durations are required."
        )

    description_review = {
        "status": "ready"
        if description_source != "generated_fallback" and len(chapters) >= MIN_CHAPTER_COUNT
        else "review",
        "source": description_source,
        "chapter_count": len(chapters),
        "uses_generated_fallback": description_source == "generated_fallback",
    }

    metadata = {
        "title": recommended_title,
        "description": description,
        "description_source": description_source,
        "chapters": chapters,
        "tags": tags,
        "hashtags": hashtags,
        "pinned_comment": pinned_comment,
        "language": episode.get("language") or "th",
        "final_video_path": str(final_video),
        "final_report_path": final_report,
        "thumbnail_brief_path": str(pack_dir / "thumbnail_brief.html"),
        "timestamps_path": str(pack_dir / "timestamps.txt"),
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
        "description_review": description_review,
        "chapters": chapters,
        "title_options": title_options,
        "thumbnail_brief": thumbnail_brief,
        "cost_summary": _as_dict(cost_report.get("totals")),
        "cost_reconciliation": {
            "status": cost_status or "missing",
            "review_reason": (
                "External or unmetered provider costs are not available in local manifests."
                if cost_status == "review" and not cost_errors
                else ""
            ),
        },
        "warnings": warnings,
        "errors": errors,
    }

    pack_dir.mkdir(parents=True, exist_ok=True)
    _write_json(pack_dir / "metadata.json", metadata)
    _write_json(pack_dir / "upload_pack_manifest.json", pack_manifest)
    _write_text(pack_dir / "description.txt", description + "\n")
    _write_text(pack_dir / "timestamps.txt", "\n".join(_chapter_lines(chapters)) + "\n")
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
                f"- Description source: {description_source}",
                f"- Timestamps: {pack_dir / 'timestamps.txt'} ({len(chapters)} chapters)",
                f"- Final video: {final_video}",
                f"- Final report: {final_report}",
                "- Use metadata.json for uploader compatibility.",
                "- Use thumbnail_brief.html/json for thumbnail production.",
                "",
            ]
        ),
    )

    merged_metadata = {**existing_metadata, **metadata}
    _write_json(root_metadata_path, merged_metadata)

    files = {
        "upload_pack_dir": str(pack_dir),
        "metadata": str(pack_dir / "metadata.json"),
        "root_metadata": str(root_metadata_path),
        "manifest": str(pack_dir / "upload_pack_manifest.json"),
        "description": str(pack_dir / "description.txt"),
        "timestamps": str(pack_dir / "timestamps.txt"),
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
