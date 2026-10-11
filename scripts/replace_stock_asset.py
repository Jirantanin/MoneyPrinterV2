#!/usr/bin/env python3
"""Download one explicit stock-video replacement for a Producer Mode slot."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _source_url(provider: str, keyword: str) -> str:
    encoded = "+".join(keyword.split())
    if provider == "pexels":
        return f"https://www.pexels.com/search/videos/{encoded}/"
    return f"https://pixabay.com/videos/search/{encoded}/"


def _update_provider_summary(container: dict, counts: Counter[str], total: int) -> None:
    container["provider_counts"] = dict(counts)
    if "provider_ratios" in container:
        container["provider_ratios"] = {
            key: round(value / total, 4) for key, value in counts.items()
        }


def _sync_metadata(
    episode: Path,
    scene_index: int,
    slot_index: int,
    provider: str,
    keyword: str,
    output: Path,
) -> None:
    timeline_path = episode / "visual_timeline.json"
    manifest_path = episode / "asset_manifest.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    size = output.stat().st_size
    repeat_key = f"{provider}:{keyword}"

    slot = next(
        slot
        for scene in timeline.get("scenes", [])
        if int(scene.get("scene_index", -1)) == scene_index
        for slot in scene.get("slots", [])
        if int(slot.get("asset_index", -1)) == slot_index
    )
    slot.update(provider=provider, visual_repeat_key=repeat_key, bytes=size)

    entry = next(
        entry
        for entry in manifest.get("entries", [])
        if int(entry.get("scene_index", -1)) == scene_index
        and int(entry.get("asset_index", -1)) == slot_index
    )
    entry.update(
        provider=provider,
        media_type="video",
        local_path=str(output.resolve()),
        bytes=size,
        status="downloaded",
        timeline_role="stock_video_broll",
        source_url=_source_url(provider, keyword),
        download_url=str(output.resolve()),
        keyword=keyword,
        selected_reason="Manual contact-sheet relevance replacement.",
        visual_repeat_key=repeat_key,
    )

    timeline_slots = [
        slot for scene in timeline.get("scenes", []) for slot in scene.get("slots", [])
    ]
    counts = Counter(str(item.get("provider") or "unknown") for item in timeline_slots)
    total = max(1, len(timeline_slots))
    _update_provider_summary(timeline, counts, total)
    if isinstance(timeline.get("visual_policy"), dict):
        _update_provider_summary(timeline["visual_policy"], counts, total)

    if isinstance(manifest.get("visual_policy"), dict):
        _update_provider_summary(manifest["visual_policy"], counts, total)
    expansion = manifest.get("broll_expansion")
    if isinstance(expansion, dict):
        _update_provider_summary(expansion, counts, total)
        if isinstance(expansion.get("visual_policy"), dict):
            _update_provider_summary(expansion["visual_policy"], counts, total)

    timeline_path.write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("pexels", "pixabay"), required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=7.0)
    parser.add_argument("--asset-index", type=int, required=True)
    parser.add_argument("--episode", type=Path)
    parser.add_argument("--scene-index", type=int)
    parser.add_argument("--slot-index", type=int)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.provider == "pexels":
        from config import _load_config
        from pexels_provider import search_pexels_video

        api_key = str(_load_config().get("pexels_api_key") or "")
        result = search_pexels_video(
            args.keyword,
            api_key,
            str(args.output),
            max(5.0, args.duration),
            asset_index=args.asset_index,
            keyword=args.keyword,
        )
    else:
        from config import _load_config
        from pixabay_provider import search_pixabay_video

        api_key = str(_load_config().get("pixabay_api_key") or "")
        result = search_pixabay_video(
            args.keyword,
            api_key,
            str(args.output),
            max(5.0, args.duration),
            asset_index=args.asset_index,
            keyword=args.keyword,
        )

    path = Path(result) if result else args.output
    ok = path.is_file() and path.stat().st_size > 10_000
    if ok and args.episode is not None:
        if args.scene_index is None or args.slot_index is None:
            parser.error("--episode requires --scene-index and --slot-index")
        _sync_metadata(
            args.episode,
            args.scene_index,
            args.slot_index,
            args.provider,
            args.keyword,
            path,
        )
    print(
        json.dumps(
            {
                "status": "downloaded" if ok else "failed",
                "provider": args.provider,
                "keyword": args.keyword,
                "path": str(path),
                "bytes": path.stat().st_size if path.is_file() else 0,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
