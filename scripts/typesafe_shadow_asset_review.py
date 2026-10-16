#!/usr/bin/env python3
"""Run paid, shadow-only TypeSafe review over a visual asset plan.

The report is advisory. It does not mutate the plan, approve assets, inspect
pixels, authorize rendering, or satisfy Producer Mode visual review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from typesafe_asset_shadow import review_visual_beat_shadow


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum paid beat calls; 0 reviews all beats (default: 3).",
    )
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--min-choice-confidence", type=float, default=0.75)
    parser.add_argument("--risk-threshold", type=float, default=0.50)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Allow replacing an existing report and making the paid calls again.",
    )
    args = parser.parse_args()

    visual_plan_path = args.visual_plan.resolve()
    output_path = (args.output or visual_plan_path.with_name("typesafe_shadow_asset_review.json")).resolve()
    if output_path.exists() and not args.refresh:
        raise FileExistsError(
            f"Refusing to replace {output_path}; pass --refresh to repeat paid API calls."
        )
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY is not configured in this process.")
    if args.offset < 0 or args.limit < 0:
        raise ValueError("--offset and --limit must be zero or greater")

    visual_plan = _read_json(visual_plan_path)
    beat_plans = [item for item in (visual_plan.get("beat_plans") or []) if isinstance(item, dict)]
    selected = beat_plans[args.offset :]
    if args.limit:
        selected = selected[: args.limit]

    from typesafe_sdk import TypeSafeClient

    results: list[dict[str, Any]] = []
    with TypeSafeClient(timeout=30.0) as client:
        for beat in selected:
            try:
                results.append(
                    review_visual_beat_shadow(
                        str(visual_plan.get("topic") or ""),
                        beat,
                        client=client,
                        min_choice_confidence=args.min_choice_confidence,
                        risk_threshold=args.risk_threshold,
                    )
                )
            except Exception as exc:
                results.append(
                    {
                        "asset_plan_id": beat.get("asset_plan_id"),
                        "mode": "shadow",
                        "approval": False,
                        "pixel_inspection_performed": False,
                        "status": "service_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    input_tokens = sum(int((item.get("usage") or {}).get("input_tokens") or 0) for item in results)
    output_tokens = sum(int((item.get("usage") or {}).get("output_tokens") or 0) for item in results)
    counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1

    report = {
        "schema_version": 1,
        "stage": "typesafe_shadow_asset_review",
        "created_at": _utc_now(),
        "advisory_only": True,
        "approves_assets": False,
        "inspects_pixels": False,
        "source_visual_plan": str(visual_plan_path),
        "source_visual_plan_sha256": _sha256(visual_plan_path),
        "topic": visual_plan.get("topic"),
        "requested_offset": args.offset,
        "requested_limit": args.limit,
        "reviewed_beat_count": len(results),
        "status_counts": counts,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "reviewed_beat_count": len(results),
                "status_counts": counts,
                "usage": report["usage"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if not counts.get("service_error") else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
