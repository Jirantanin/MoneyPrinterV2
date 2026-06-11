"""Final read-only HTML report for PodcastV2 Producer Mode."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FINAL_REPORT_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _path_text(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(Path(str(value)).resolve())
    except (OSError, TypeError, ValueError):
        return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _render_kv(items: dict[str, Any]) -> str:
    rows: list[str] = []
    for key, value in items.items():
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            text = str(value or "")
        rows.append(
            f"<dt>{_html(str(key).replace('_', ' ').title())}</dt>"
            f"<dd>{_html(text)}</dd>"
        )
    return "<dl>" + "".join(rows) + "</dl>"


def _render_items(items: list[Any], empty: str) -> str:
    if not items:
        return f'<p class="empty">{_html(empty)}</p>'
    rows = []
    for item in items:
        if isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("name")
                or item.get("concept")
                or item.get("provider")
                or item.get("asset_plan_id")
                or "item"
            )
            detail = (
                item.get("summary")
                or item.get("description")
                or item.get("rationale")
                or item.get("reason")
                or item.get("source_url")
                or item.get("url")
                or item.get("detail")
                or ""
            )
            rows.append(
                "<li>"
                f"<strong>{_html(title)}</strong>"
                f"{f'<span>{_html(detail)}</span>' if detail else ''}"
                "</li>"
            )
        else:
            rows.append(f"<li>{_html(item)}</li>")
    return "<ul>" + "".join(rows) + "</ul>"


def _badge(status: Any) -> str:
    text = str(status or "pending")
    cls = "ok" if text in {"pass", "ready", "complete"} else "bad" if text in {"blocked", "stop_required"} else "warn"
    return f'<span class="badge {cls}">{_html(text.replace("_", " ").title())}</span>'


def _sections_summary(sections: list[Any]) -> list[dict[str, Any]]:
    result = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        beats = _as_list(section.get("beats"))
        result.append(
            {
                "title": f"{section.get('section_index', '')}. {section.get('title', 'Untitled')}",
                "summary": (
                    f"{section.get('narrative_goal', '')} "
                    f"({len(beats)} visual beats)"
                ).strip(),
            }
        )
    return result


def _artifact_status(episode_dir: Path, names: list[str]) -> list[dict[str, Any]]:
    rows = []
    for name in names:
        path = episode_dir / name
        rows.append(
            {
                "name": name,
                "status": "present" if path.exists() else "missing",
                "path": str(path),
                "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            }
        )
    return rows


def _render_artifact_table(rows: list[dict[str, Any]]) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{_html(row.get('name'))}</td>"
            f"<td>{_html(row.get('status'))}</td>"
            f"<td>{_html(row.get('bytes'))}</td>"
            f"<td>{_html(row.get('path'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Artifact</th><th>Status</th><th>Bytes</th><th>Path</th></tr></thead>"
        "<tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def build_final_report(
    *,
    episode_dir: str | Path,
    plan: dict[str, Any] | None = None,
    cost_report: dict[str, Any] | None = None,
    final_qc: dict[str, Any] | None = None,
    asset_manifest: dict[str, Any] | None = None,
    tts_manifest: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a final read-only delivery report as an HTML string plus summary."""

    episode_path = Path(episode_dir)
    plan = _as_dict(plan)
    cost_report = _as_dict(cost_report)
    final_qc = _as_dict(final_qc)
    asset_manifest = _as_dict(asset_manifest)
    tts_manifest = _as_dict(tts_manifest)
    render_manifest = _as_dict(render_manifest)

    episode = _as_dict(plan.get("episode"))
    seo = _as_dict(plan.get("seo_packaging"))
    budget = _as_dict(cost_report.get("budget"))
    totals = _as_dict(cost_report.get("totals"))
    fmt = _as_dict(final_qc.get("format"))
    video = _as_dict(final_qc.get("video"))
    audio = _as_dict(final_qc.get("audio"))
    asset_entries = _as_list(asset_manifest.get("entries"))
    tts_entries = _as_list(tts_manifest.get("entries"))
    sections = _as_list(plan.get("sections"))
    final_video_path = (
        final_qc.get("final_video_path")
        or render_manifest.get("final_video_path")
        or str(episode_path / "final.mp4")
    )

    errors = []
    warnings = []
    errors.extend(str(item) for item in _as_list(final_qc.get("errors")))
    errors.extend(str(item) for item in _as_list(cost_report.get("errors")))
    warnings.extend(str(item) for item in _as_list(final_qc.get("warnings")))
    warnings.extend(str(item) for item in _as_list(cost_report.get("warnings")))
    if not Path(str(final_video_path)).exists():
        errors.append(f"final video is missing: {final_video_path}")
    if final_qc.get("status") != "pass":
        warnings.append(f"final_qc status is {final_qc.get('status') or 'missing'}")
    if not seo.get("recommended_title"):
        warnings.append("recommended title is still pending.")

    if errors:
        status = "blocked"
    elif warnings:
        status = "review"
    else:
        status = "ready"

    artifact_rows = _artifact_status(
        episode_path,
        [
            "final.mp4",
            "producer_plan.json",
            "checkpoint.html",
            "script.json",
            "script_qc.json",
            "fact_check_report.json",
            "asset_manifest.json",
            "asset_qc.json",
            "tts_manifest.json",
            "tts_qc.json",
            "render_manifest.json",
            "final_qc.json",
            "cost_report.json",
            "final_report.html",
        ],
    )
    for row in artifact_rows:
        if row.get("name") == "final_report.html" and row.get("status") == "missing":
            row["status"] = "will_write"
    upload_pack_path = episode_path / "upload_pack"
    artifact_rows.append(
        {
            "name": "upload_pack",
            "status": "present" if upload_pack_path.exists() else "pending",
            "path": str(upload_pack_path),
            "bytes": 0,
        }
    )

    provider_counts: dict[str, int] = {}
    for entry in asset_entries:
        if isinstance(entry, dict):
            provider = str(entry.get("provider") or "unknown")
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

    title = episode.get("topic") or episode_path.name
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html(title)} - Producer Final Report</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101316;
      --panel: #181d22;
      --panel2: #20262d;
      --line: #323b45;
      --text: #eef2f4;
      --muted: #9aa8b5;
      --accent: #77d1c5;
      --ok: #92d67d;
      --warn: #f1c36a;
      --bad: #ee7d7d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.55 "Segoe UI", Arial, sans-serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 44px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 20px;
    }}
    h1, h2, h3 {{ margin: 0; line-height: 1.22; }}
    h1 {{ font-size: 30px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    p {{ margin: 0 0 10px; }}
    .muted, .empty {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      grid-column: span 6;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .panel.full {{ grid-column: 1 / -1; }}
    .panel.third {{ grid-column: span 4; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel2);
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .badge.ok {{ color: var(--ok); border-color: rgba(146, 214, 125, .45); }}
    .badge.warn {{ color: var(--warn); border-color: rgba(241, 195, 106, .45); }}
    .badge.bad {{ color: var(--bad); border-color: rgba(238, 125, 125, .45); }}
    .meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    dl {{
      display: grid;
      grid-template-columns: minmax(140px, 230px) 1fr;
      gap: 8px 14px;
      margin: 0;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 7px 0; }}
    li span {{ display: block; color: var(--muted); margin-top: 2px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    @media (max-width: 820px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 18px; }}
      header {{ grid-template-columns: 1fr; }}
      .panel, .panel.third {{ grid-column: 1 / -1; }}
      dl {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{_html(title)}</h1>
        <p class="muted">PodcastV2 Producer Mode final read-only report.</p>
        <div class="meta">
          {_badge(status)}
          {_badge(final_qc.get("status") or "final qc missing")}
          {_badge(budget.get("status") or "budget pending")}
        </div>
      </div>
      <div>
        <strong>{_html(fmt.get("duration_seconds") or 0)}s</strong>
        <p class="muted">{_html(video.get("width"))}x{_html(video.get("height"))} / {_html(video.get("fps"))}fps</p>
      </div>
    </header>

    <section class="grid">
      <div class="panel full">
        <h2>Delivery Summary</h2>
        {_render_kv({
            "episode_dir": str(episode_path),
            "final_video_path": _path_text(final_video_path),
            "recommended_title": seo.get("recommended_title"),
            "recommended_title_rationale": seo.get("recommended_title_rationale"),
            "status": status,
        })}
      </div>

      <div class="panel">
        <h2>Final QC</h2>
        {_render_kv({
            "status": final_qc.get("status"),
            "duration_seconds": fmt.get("duration_seconds"),
            "format_name": fmt.get("format_name"),
            "file_bytes": final_qc.get("file_bytes"),
            "video": video,
            "audio": audio,
        })}
      </div>

      <div class="panel">
        <h2>Cost And Runtime</h2>
        {_render_kv({
            "budget_status": budget.get("status"),
            "warning_at": budget.get("warning_at"),
            "stop_at": budget.get("stop_at"),
            "new_cost_this_run_usd": totals.get("new_cost_this_run_usd"),
            "remaining_estimated_cost_usd": totals.get("remaining_estimated_cost_usd"),
            "estimated_total_cost_usd": totals.get("estimated_total_cost_usd"),
            "unknown_cost_item_count": totals.get("unknown_cost_item_count"),
        })}
      </div>

      <div class="panel">
        <h2>Narration</h2>
        {_render_kv({
            "provider": tts_manifest.get("provider"),
            "model": tts_manifest.get("model"),
            "status": tts_manifest.get("status"),
            "scene_count": len(tts_entries),
            "total_duration_seconds": tts_manifest.get("total_duration_seconds"),
            "estimated_cost_usd": tts_manifest.get("estimated_cost_usd"),
        })}
      </div>

      <div class="panel">
        <h2>Visual Assets</h2>
        {_render_kv({
            "status": asset_manifest.get("status"),
            "entry_count": len(asset_entries),
            "provider_counts": provider_counts,
        })}
      </div>

      <div class="panel">
        <h2>Title Options</h2>
        {_render_items(_as_list(seo.get("title_options")), "Title options pending.")}
      </div>

      <div class="panel">
        <h2>Thumbnail Concepts</h2>
        {_render_items(_as_list(seo.get("thumbnail_concept_options")), "Thumbnail concepts pending.")}
      </div>

      <div class="panel full">
        <h2>Sections</h2>
        {_render_items(_sections_summary(sections), "Sections pending.")}
      </div>

      <div class="panel">
        <h2>Warnings</h2>
        {_render_items(warnings, "No warnings.")}
      </div>

      <div class="panel">
        <h2>Errors</h2>
        {_render_items(errors, "No blocking errors.")}
      </div>

      <div class="panel full">
        <h2>Artifact Checklist</h2>
        {_render_artifact_table(artifact_rows)}
      </div>
    </section>
  </main>
</body>
</html>
"""

    return {
        "schema_version": FINAL_REPORT_VERSION,
        "stage": "final_report",
        "created_at": _utc_now(),
        "status": status,
        "html": html_text,
        "summary": {
            "episode_dir": str(episode_path),
            "final_video_path": _path_text(final_video_path),
            "final_qc_status": final_qc.get("status") or "missing",
            "budget_status": budget.get("status") or "pending",
            "estimated_total_cost_usd": round(_to_float(totals.get("estimated_total_cost_usd")), 6),
            "artifact_count": len(artifact_rows),
        },
        "warnings": warnings,
        "errors": errors,
    }
