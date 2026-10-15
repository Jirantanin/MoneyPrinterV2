"""Per-episode YouTube review: pull one published episode's numbers and lay its retention curve over the episode's scenes.

The user runs it for a chosen episode (e.g. 7 and 28 days after publishing); nothing here runs on a schedule.
Thumbnail impressions/CTR are not in the Analytics API, so they are read from YouTube Studio separately.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import youtube_upload as yt

REVIEW_DIR = "youtube_review"
STUDIO_FILE = "studio_reach.json"  # thumbnail impressions/CTR copied from YouTube Studio (not in the Analytics API)
TRAFFIC_LABELS = {  # Studio's names; SUBSCRIBER is Browse features (home/feeds), not "views by subscribers"
    "SUBSCRIBER": "ฟีเจอร์การเรียกดู (Home/ฟีด)", "RELATED_VIDEO": "วิดีโอแนะนำ", "YT_SEARCH": "การค้นหาใน YouTube",
    "YT_CHANNEL": "หน้าช่อง", "END_SCREEN": "End Screen", "NOTIFICATION": "การแจ้งเตือน", "PLAYLIST": "เพลย์ลิสต์",
    "EXT_URL": "เว็บภายนอก", "NO_LINK_OTHER": "โดยตรงหรือไม่ทราบ", "YT_OTHER_PAGE": "ฟีเจอร์อื่นๆ ของ YouTube",
    "SHORTS": "ฟีด Shorts",
}
TOTAL_METRICS = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                 "likes,comments,shares,subscribersGained,subscribersLost")


def scene_timeline(episode_dir: Path) -> list[dict[str, Any]]:
    """Scene start/end in final-video seconds, from the rendered scene durations and the script."""
    durations = yt.read_json(episode_dir / "render_props.json").get("sceneDurations") or []
    script = json.loads((episode_dir / "script.json").read_text(encoding="utf-8"))
    if len(durations) != len(script):
        raise ValueError(f"render_props has {len(durations)} scene durations but script.json has {len(script)} scenes")
    scenes, start = [], 0.0
    for index, (scene, seconds) in enumerate(zip(script, durations)):
        scenes.append({
            "scene_index": index, "section_index": scene.get("section_index"),
            "section_title": scene.get("section_title", ""), "scene_title": scene.get("scene_title", ""),
            "start_seconds": round(start, 2), "end_seconds": round(start + seconds, 2),
            "narration_start": " ".join((scene.get("narration") or "").split())[:90],
        })
        start += seconds
    return scenes


def _rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    names = [header["name"] for header in report.get("columnHeaders", [])]
    return [dict(zip(names, row)) for row in report.get("rows") or []]


def _watch_at(curve: list[dict[str, Any]], seconds: float, duration: float) -> float:
    ratio = seconds / duration
    return min(curve, key=lambda row: abs(row["elapsedVideoTimeRatio"] - ratio))["audienceWatchRatio"]


def map_retention(curve: list[dict[str, Any]], scenes: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    """Retention at each scene's start/end, the drop across it, and YouTube's relative performance inside it."""
    mapped = []
    for scene in scenes:
        start, end = scene["start_seconds"], min(scene["end_seconds"], duration)
        inside = [row["relativeRetentionPerformance"] for row in curve
                  if start <= row["elapsedVideoTimeRatio"] * duration < end]
        at_start, at_end = _watch_at(curve, start, duration), _watch_at(curve, end, duration)
        mapped.append({**scene, "retention_start": round(at_start, 3), "retention_end": round(at_end, 3),
                       "drop": round(at_start - at_end, 3),
                       "relative": round(sum(inside) / len(inside), 3) if inside else None})
    return mapped


def section_summary(mapped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: dict[Any, list[dict[str, Any]]] = {}
    for scene in mapped:
        sections.setdefault(scene["section_index"], []).append(scene)
    out = []
    for index, scenes in sections.items():
        relative = [s["relative"] for s in scenes if s["relative"] is not None]
        out.append({"section_index": index, "section_title": scenes[0]["section_title"],
                    "start_seconds": scenes[0]["start_seconds"], "end_seconds": scenes[-1]["end_seconds"],
                    "retention_start": scenes[0]["retention_start"], "retention_end": scenes[-1]["retention_end"],
                    "drop": round(scenes[0]["retention_start"] - scenes[-1]["retention_end"], 3),
                    "relative": round(sum(relative) / len(relative), 3) if relative else None})
    return out


def iso_duration_seconds(value: str) -> float:
    match = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups()) if match else (0, 0, 0, 0)
    return float(((days * 24 + hours) * 60 + minutes) * 60 + seconds)


def fetch(episode_dir: Path, *, days: int | None = None, channel_id: str = yt.DEFAULT_CHANNEL_ID) -> dict[str, Any]:
    receipt = yt.read_json(episode_dir / "upload_pack" / yt.RECEIPT_NAME)
    video_id = receipt.get("video_id")
    if not video_id:
        raise ValueError("episode has no uploaded video id in upload_pack/youtube_upload_receipt.json")
    youtube = yt.youtube_client()
    yt._check_channel(youtube, channel_id)
    items = youtube.videos().list(part="snippet,status,statistics,contentDetails", id=video_id).execute().get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"video {video_id} not found")
    video = items[0]
    published = datetime.fromisoformat(video["snippet"]["publishedAt"].replace("Z", "+00:00"))
    if video["status"].get("publishAt"):
        published = max(published, datetime.fromisoformat(video["status"]["publishAt"].replace("Z", "+00:00")))
    today = datetime.now(timezone.utc).date()
    start = published.date() - timedelta(days=1)  # Analytics days are Pacific time
    end = min(published.date() + timedelta(days=days), today) if days else today

    analytics = yt.analytics_client()

    def query(metrics: str, filters: str = "", **extra: Any) -> list[dict[str, Any]]:
        return _rows(analytics.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
                                               metrics=metrics, filters=f"video=={video_id}{filters}", **extra).execute())

    try:
        comments = [{"author": t["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                     "text": t["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                     "likes": t["snippet"]["topLevelComment"]["snippet"]["likeCount"],
                     "replies": t["snippet"]["totalReplyCount"]}
                    for t in youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=20,
                                                           order="relevance", textFormat="plainText").execute().get("items", [])]
    except Exception:  # comments disabled
        comments = []

    return {
        "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}", "title": video["snippet"]["title"],
        "published_at": published.isoformat(), "fetched_at": yt.utc_now(),
        "window": {"start": start.isoformat(), "end": end.isoformat(), "days_since_publish": (end - published.date()).days},
        "duration_seconds": iso_duration_seconds(video["contentDetails"]["duration"]),
        "statistics": video.get("statistics", {}),
        "totals": (query(TOTAL_METRICS) or [{}])[0],
        "daily": query("views,estimatedMinutesWatched,averageViewPercentage", dimensions="day", sort="day"),
        "traffic_sources": query("views,estimatedMinutesWatched", dimensions="insightTrafficSourceType", sort="-views"),
        "search_terms": query("views", ";insightTrafficSourceType==YT_SEARCH", dimensions="insightTrafficSourceDetail",
                              sort="-views", maxResults=25),
        "retention_curve": query("audienceWatchRatio,relativeRetentionPerformance", ";audienceType==ORGANIC",
                                 dimensions="elapsedVideoTimeRatio"),
        "comments": comments,
    }


def build_review(episode_dir: Path, data: dict[str, Any]) -> dict[str, Any]:
    scenes = scene_timeline(episode_dir)
    duration = data["duration_seconds"] or scenes[-1]["end_seconds"]
    curve = data["retention_curve"]
    review: dict[str, Any] = {**data, "rendered_seconds": scenes[-1]["end_seconds"],
                              "studio": yt.read_json(episode_dir / REVIEW_DIR / STUDIO_FILE)}
    if curve:
        mapped = map_retention(curve, scenes, duration)
        review.update(
            hook={f"{s}s": round(_watch_at(curve, s, duration), 3) for s in (30, 60, 120) if s < duration},
            sections=section_summary(mapped), scenes=mapped,
            # Absolute drops always pile up in the first minutes; relative performance isolates the scenes themselves.
            weakest_scenes=sorted((s for s in mapped if s["relative"] is not None), key=lambda s: s["relative"])[:5],
            strongest_scenes=sorted((s for s in mapped if s["relative"] is not None), key=lambda s: s["relative"], reverse=True)[:3],
        )
    return review


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def render_markdown(review: dict[str, Any]) -> str:
    totals, stats, window = review["totals"], review["statistics"], review["window"]
    lines = [
        f"# YouTube review: {review['title']}",
        "",
        f"{review['url']} · ลงเมื่อ {review['published_at'][:10]} · ข้อมูลถึง {window['end']} (วันที่ {window['days_since_publish']} หลังลง)",
        "",
        "## ตัวเลขรวม",
        "",
        "| วิว | ชม.ดู | ดูเฉลี่ย | % ที่ดู | ไลก์ | คอมเมนต์ | แชร์ | sub +/- |",
        "|---|---|---|---|---|---|---|---|",
        f"| {totals.get('views', stats.get('viewCount', '-'))} | {totals.get('estimatedMinutesWatched', 0) / 60:.1f}"
        f" | {_clock(totals.get('averageViewDuration', 0))} | {totals.get('averageViewPercentage', 0):.1f}%"
        f" | {totals.get('likes', stats.get('likeCount', '-'))} | {totals.get('comments', stats.get('commentCount', '-'))}"
        f" | {totals.get('shares', '-')} | +{totals.get('subscribersGained', 0)}/-{totals.get('subscribersLost', 0)} |",
        "",
        f"Data API ตอนนี้: {stats.get('viewCount', '-')} วิว (Analytics ช้ากว่า 1-3 วัน)",
        "",
        (f"Studio ({review['studio'].get('read_at', '?')}): impressions {review['studio'].get('impressions', '-')}"
         f" · CTR {review['studio'].get('ctr_percent', '-')}% · {review['studio'].get('notes', '')}") if review.get("studio")
        else f"CTR/impressions: ยังไม่ได้จดจาก Studio (ใส่ใน {REVIEW_DIR}/{STUDIO_FILE})",
        "",
        "วิวรายวัน: " + (" · ".join(f"{row['day'][5:]} {row['views']}" for row in review["daily"] if row["views"]) or "-"),
        "",
    ]
    if "sections" not in review:
        lines += ["## Retention", "", "YouTube ยังไม่ให้ retention curve (วิวน้อยเกินหรือข้อมูลยังไม่มา)", ""]
    else:
        lines += ["## Hook", "", " · ".join(f"ที่ {k} เหลือ {_pct(v)}" for k, v in review["hook"].items()), "",
                  "## รายช่วง (relative = เทียบคลิปยาวใกล้กัน, 50% = กลางๆ)", "",
                  "| ช่วง | เวลา | retention | drop | relative |", "|---|---|---|---|---|"]
        lines += [f"| {s['section_title']} | {_clock(s['start_seconds'])}-{_clock(s['end_seconds'])}"
                  f" | {_pct(s['retention_start'])} → {_pct(s['retention_end'])} | {_pct(s['drop'])} | {_pct(s['relative'])} |"
                  for s in review["sections"]]
        lines += ["", "## ฉากที่แย่กว่าคลิปอื่น (relative ต่ำสุด)", ""]
        lines += [f"- **{_clock(s['start_seconds'])}** ฉาก {s['scene_index']} \"{s['scene_title']}\" relative {_pct(s['relative'])},"
                  f" หลุด {_pct(s['drop'])} — {s['narration_start']}…" for s in review["weakest_scenes"]]
        lines += ["", "## ฉากที่ดีกว่าคลิปอื่น", ""]
        lines += [f"- **{_clock(s['start_seconds'])}** ฉาก {s['scene_index']} \"{s['scene_title']}\" relative {_pct(s['relative'])}"
                  f" — {s['narration_start']}…" for s in review["strongest_scenes"]]
        lines.append("")
    lines += ["## คนมาจากไหน", ""]
    lines += [f"- {TRAFFIC_LABELS.get(row['insightTrafficSourceType'], row['insightTrafficSourceType'])}: {row['views']} วิว"
              for row in review["traffic_sources"]] or ["- (ยังไม่มีข้อมูล)"]
    if review["search_terms"]:
        lines += ["", "คำค้นใน YouTube: " + ", ".join(f"{row['insightTrafficSourceDetail']} ({row['views']})"
                                                     for row in review["search_terms"])]
    lines += ["", "## คอมเมนต์", ""]
    lines += [f"- {c['author']} ({c['likes']}👍): {' '.join(c['text'].split())[:200]}" for c in review["comments"]] or ["- (ไม่มี)"]
    if abs(review["rendered_seconds"] - (review["duration_seconds"] or review["rendered_seconds"])) > 2:
        lines += ["", f"⚠️ ความยาวบน YouTube {review['duration_seconds']:.0f}s ไม่ตรงกับ render {review['rendered_seconds']:.0f}s — เวลาฉากอาจเลื่อน"]
    return "\n".join(lines) + "\n"


def write_review(episode_dir: Path, review: dict[str, Any]) -> Path:
    out_dir = episode_dir / REVIEW_DIR
    out_dir.mkdir(exist_ok=True)
    stem = f"d{review['window']['days_since_publish']:02d}_{review['window']['end']}"
    yt.write_json(out_dir / f"{stem}.json", review)
    path = out_dir / f"{stem}.md"
    path.write_text(render_markdown(review), encoding="utf-8")
    return path
