"""Minimal documentary renderer for Producer Mode.

An alternative to the Remotion ``VideoPodcast`` composition, selected per episode with
``producer_plan.json`` -> ``"render_settings": {"renderer": "minimal_doc"}``. It consumes the same
prepared render props and audio, so the revision/authorization gate is unchanged.

Look: restrained documentary styling — slow Ken Burns on full-frame images, framed "plates" for
portrait/square/low-resolution images, research figures on a paper card, chapter cards when the scene
title changes, captions built from each asset's on-screen qualification, and a sources end card in
the outro hold.

Rendering: ``doc_renderer/player.html`` is driven frame-by-frame in headless Chrome by
``doc_renderer/render.cjs``; frames are encoded in resumable chunks. Video b-roll is pre-extracted
to 25 fps JPEG frames with ffmpeg and played once through its slot (held on the last frame if the
clip is shorter, never looped). A separate scene-0 intro video is not supported.

Optional per-episode framing overrides live in ``minimal_render_overrides.json``::

    {"assets": {"scene_00_2.jpg": {"kind": "cover", "anchor": [0.93, 0.12], "zoom": [1.32, 1.48],
                                    "min_zoom": 1.07, "caption_title": "ดาวพฤหัสบดี"}},
     "end_card": {"sources": ["..."], "note": "..."}}
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from producer_contract import file_hash, fingerprint, read_json

RENDERER_ID = "minimal_doc"
OVERRIDES_FILE = "minimal_render_overrides.json"
FPS = 25
KINDS = ("cover", "plate", "figure", "slide", "video")
CROSSFADE_MARGIN_SECONDS = 2.0   # player dissolves start up to 0.8 s before a slot; extract a little extra
KNOWN_AGENCIES = ("NASA", "ESA", "CSA", "STScI", "JPL-Caltech", "GSFC", "ESO", "NOIRLab", "JAXA", "NOAA", "USGS")
DEFAULT_END_NOTE = "ภาพประกอบบางส่วนเป็นภาพจำลองหรือภาพจากระบบอื่นเพื่อใช้เปรียบเทียบ ตามที่ระบุไว้บนจอ"


def renderer_dir(root_dir: Path) -> Path:
    return Path(root_dir) / "doc_renderer"


def renderer_files(root_dir: Path) -> list[Path]:
    """Files whose content defines renderer behavior; part of the render revision."""
    folder = renderer_dir(root_dir)
    return [folder / "player.html", folder / "render.cjs", folder / "package.json", Path(__file__)]


def find_chrome(root_dir: Path) -> Path | None:
    configured = os.environ.get("PRODUCER_MINIMAL_CHROME", "").strip()
    if configured:
        return Path(configured) if Path(configured).is_file() else None
    bundled = Path(root_dir) / "remotion" / "node_modules" / ".remotion" / "chrome-headless-shell"
    for name in ("chrome-headless-shell.exe", "chrome-headless-shell"):
        for candidate in sorted(bundled.rglob(name)) if bundled.is_dir() else []:
            if candidate.is_file():
                return candidate
    return None


def environment_checks(root_dir: Path) -> list[dict[str, str]]:
    folder = renderer_dir(root_dir)
    checks = [
        ("player", folder / "player.html"),
        ("driver", folder / "render.cjs"),
        ("puppeteer-core", folder / "node_modules" / "puppeteer-core" / "package.json"),
    ]
    results = [{"name": name, "path": str(path), "status": "pass" if path.is_file() else "fail"} for name, path in checks]
    chrome = find_chrome(root_dir)
    results.append({"name": "chrome", "path": str(chrome or ""), "status": "pass" if chrome else "fail"})
    for tool in ("node", "ffmpeg"):
        results.append({"name": tool, "path": shutil.which(tool) or "", "status": "pass" if shutil.which(tool) else "fail"})
    return results


def _workers() -> int:
    raw = os.environ.get("PRODUCER_MINIMAL_WORKERS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return max(1, min(8, (os.cpu_count() or 2) // 2))


# ---- timeline ---------------------------------------------------------------------------------

def classify_asset(fit: str, width: int, height: int, mean_luma: float) -> str:
    aspect = width / max(1, height)
    if fit == "contain":
        # Episode-made explainer slides are full 16:9 dark frames; research figures are light.
        return "slide" if 1.7 <= aspect <= 1.85 and mean_luma < 70 else "figure"
    if aspect < 0.9 or aspect > 2.2 or width < 1500 or (aspect < 1.3 and min(width, height) < 2000):
        return "plate"      # would be badly cropped or visibly upscaled as a full-frame cover
    return "cover"


def split_caption(qualification: str) -> tuple[str, str]:
    text = str(qualification or "").strip()
    if " — " in text:
        title, sub = text.split(" — ", 1)
        return title.strip(), sub.strip()
    return text, ""


def end_card_sources(credits: list[str]) -> list[str]:
    """Research citations (one line per paper) plus one line of known agencies."""
    citations: dict[tuple[str, str], str] = {}
    agencies: list[str] = []
    for credit in credits:
        credit = str(credit or "").strip()
        year = re.search(r"\((\d{4})\)", credit)
        if year:
            first_author = re.split(r"[;&,]", credit[:year.start()])[0].split()
            if not first_author:
                continue
            key = (first_author[-1], year.group(1))
            clean = re.sub(r",?\s*(Fig\.?|Figure)\s*\d+.*$", "", credit)
            clean = re.sub(r"\s*\|.*$", "", clean)
            clean = re.sub(r",\s*stag\w*.*$", "", clean).strip(" ,")
            if len(clean) > len(citations.get(key, "")):
                citations[key] = clean
            continue
        for agency in KNOWN_AGENCIES:
            if re.search(rf"(?<![A-Za-z]){re.escape(agency)}(?![A-Za-z])", credit) and agency not in agencies:
                agencies.append(agency)
    lines = [citations[key] for key in sorted(citations, key=lambda k: (k[1], k[0]))]
    if agencies:
        lines.append(" · ".join(a for a in KNOWN_AGENCIES if a in agencies))
    return lines


def _file_url(path: Path) -> str:
    return "file:///" + str(path.resolve()).replace("\\", "/")


def _prep_asset(source: Path, kind: str, assets_dir: Path, cache: dict) -> tuple[Path, Path | None, tuple[int, int]]:
    key = (str(source), kind)
    if key in cache:
        return cache[key]
    stem = f"{source.stem}_{file_hash(source)[:10]}"
    with Image.open(source) as opened:
        image = opened.convert("RGBA") if opened.mode in ("RGBA", "LA", "P") else opened.convert("RGB")
    image.thumbnail((2600, 2600) if kind == "cover" else (1800, 1800), Image.LANCZOS)
    if image.mode == "RGBA":
        flat = Image.new("RGB", image.size, (255, 255, 255) if kind == "figure" else (0, 0, 0))
        flat.paste(image, mask=image.split()[3])
        image = flat
    if kind == "figure":
        target = assets_dir / f"{stem}_{kind}.png"
        image.save(target)
    else:
        target = assets_dir / f"{stem}_{kind}.jpg"
        image.save(target, quality=93)
    blur = None
    if kind == "plate":
        small = image.copy()
        small.thumbnail((240, 240))
        small = small.resize((480, 270), Image.BILINEAR).filter(ImageFilter.GaussianBlur(18))
        blur = assets_dir / f"{stem}_blur.jpg"
        small.save(blur, quality=90)
    cache[key] = (target, blur, image.size)
    return cache[key]


def _extract_video_frames(source: Path, seconds: float, frames_root: Path) -> tuple[Path, int]:
    """Decode ``seconds`` of a clip to 1920x1080 cover-cropped JPEG frames at the render fps."""
    wanted = int(round((seconds + CROSSFADE_MARGIN_SECONDS) * FPS))
    target = frames_root / f"{source.stem}_{file_hash(source)[:10]}_{wanted}"
    done = target / "count.txt"
    if done.is_file():
        return target, int(done.read_text())
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-an", "-vf",
                    f"fps={FPS},scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                    "-frames:v", str(wanted), "-q:v", "3", str(target / "f_%05d.jpg")],
                   check=True, capture_output=True)
    count = len(list(target.glob("f_*.jpg")))
    if not count:
        raise ValueError(f"no frames decoded from {source}")
    done.write_text(str(count))
    return target, count


def build_timeline(raw_props: dict[str, Any], *, narration_end: float, assets_dir: Path,
                   overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    asset_overrides = overrides.get("assets") or {}
    assets_dir.mkdir(parents=True, exist_ok=True)
    paths = [Path(str(p)) for p in raw_props.get("imagePaths", [])]
    types = list(raw_props.get("sceneAssetTypes") or ["image"] * len(paths))
    fits = list(raw_props.get("sceneAssetFits") or ["cover"] * len(paths))
    durations = [float(d) for d in raw_props.get("sceneAssetDurations", [])]
    quals = list(raw_props.get("sceneAssetQualifications") or [""] * len(paths))
    credits = list(raw_props.get("sceneAssetCredits") or [""] * len(paths))
    counts = [int(c) for c in raw_props.get("sceneImageCounts", [])]
    scene_durations = [float(d) for d in raw_props.get("sceneDurations", [])]
    titles = list(raw_props.get("sceneTitles") or [""] * len(counts))
    total = round(float(raw_props.get("durationInSeconds") or sum(scene_durations)), 3)
    if not (len(paths) == len(durations) == sum(counts)) or len(counts) != len(scene_durations):
        raise ValueError("render props asset/scene counts are inconsistent")
    unsupported = sorted({t for t in types if t not in ("image", "video")})
    if unsupported:
        raise ValueError(f"minimal_doc cannot render asset types: {', '.join(unsupported)}")
    warnings: list[str] = []

    shots: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    cache: dict = {}
    t, k, previous_title = 0.0, 0, None
    for scene, (scene_duration, title, count) in enumerate(zip(scene_durations, titles, counts)):
        if title and title != previous_title:
            chapters.append({"no": len(chapters) + 1, "title": title, "start": round(t, 3), "scene": scene})
        previous_title = title
        start = t
        for j in range(k, k + count):
            source = paths[j]
            override = asset_overrides.get(source.name) or {}
            cap_title, cap_sub = split_caption(quals[j])
            if override.get("caption_title"):
                cap_title = str(override["caption_title"])
            common = {"i": j, "scene": scene, "start": round(start, 3), "end": round(start + durations[j], 3),
                      "name": source.name, "capTitle": cap_title, "capSub": cap_sub,
                      "credit": str(credits[j] or "").strip(), "move": len(shots) % 4}
            if types[j] == "video":
                frames_dir, frame_count = _extract_video_frames(source, durations[j], assets_dir / "video_frames")
                if frame_count < durations[j] * FPS:
                    warnings.append(f"{source.name}: clip is {frame_count / FPS:.1f}s for a {durations[j]:.1f}s slot; "
                                    "last frame holds")
                shots.append({**common, "kind": "video", "framesBase": _file_url(frames_dir) + "/f_",
                              "frameCount": frame_count, "src": _file_url(frames_dir / "f_00001.jpg"),
                              "blur": None, "w": 1920, "h": 1080, "anchor": [0.5, 0.5], "zoom": None, "minZoom": 0})
                start += durations[j]
                continue
            with Image.open(source) as probe:
                width, height = probe.size
                luma = ImageStat.Stat(probe.convert("L").resize((64, 36))).mean[0]
            kind = override.get("kind") or classify_asset(str(fits[j]), width, height, luma)
            if kind not in KINDS:
                raise ValueError(f"{OVERRIDES_FILE}: unknown kind {kind!r} for {source.name}")
            prepared, blur, size = _prep_asset(source, kind, assets_dir, cache)
            shots.append({
                **common, "kind": kind, "src": _file_url(prepared), "blur": _file_url(blur) if blur else None,
                "w": size[0], "h": size[1],
                "anchor": list(override.get("anchor") or (0.5, 0.5)),
                "zoom": list(override["zoom"]) if override.get("zoom") else None,
                "minZoom": float(override.get("min_zoom") or 0),
            })
            start += durations[j]
        k += count
        t += scene_duration
        if shots:
            shots[-1]["end"] = round(t, 3)      # absorb rounding drift into the scene's last shot
    if not shots:
        raise ValueError("render props contain no visual assets")
    shots[-1]["end"] = total                    # last image holds under the end card

    end_card = overrides.get("end_card") or {}
    sources = end_card.get("sources") if "sources" in end_card else end_card_sources(credits)
    note = end_card.get("note") if "note" in end_card else (
        DEFAULT_END_NOTE if any("ไม่ใช่" in str(q) for q in quals) else "")
    return {"fps": FPS, "total": total, "narrationEnd": round(min(narration_end, total), 3),
            "shots": shots, "chapters": chapters, "sources": list(sources or []), "endNote": note or "",
            "warnings": warnings}


# ---- render -----------------------------------------------------------------------------------

def _run(args: list[str], *, log_path: Path, timeout_seconds: int | None = None, cwd: Path | None = None) -> None:
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\nRUN {' '.join(args)}\n")
        log.flush()
        subprocess.run(args, cwd=str(cwd) if cwd else None, check=True, text=True, stdout=log,
                       stderr=subprocess.STDOUT, timeout=timeout_seconds)


def _prepare_work(root_dir: str | Path, episode_dir: str | Path, raw_props: dict[str, Any],
                  narration_end: float) -> dict[str, Any]:
    """Build the timeline and keyed work folder exactly as a render would (shared by render and stills)."""
    # node runs from doc_renderer/, so every path handed to it must be absolute.
    root_path = Path(root_dir).resolve()
    episode_path = Path(episode_dir)
    episode_path = (episode_path if episode_path.is_absolute() else root_path / episode_path).resolve()
    failed = [c for c in environment_checks(root_path) if c["status"] != "pass"]
    if failed:
        raise RuntimeError("minimal_doc renderer is not installed: " + ", ".join(c["name"] for c in failed)
                           + " (run `npm install` in doc_renderer/)")
    overrides = read_json(episode_path / OVERRIDES_FILE, {}) or {}
    base = episode_path / "minimal_render"
    timeline = build_timeline(raw_props, narration_end=narration_end, assets_dir=base / "assets", overrides=overrides)
    # Chunks are reused on resume, so the work folder is keyed by everything that shapes the frames.
    key = fingerprint({"timeline": timeline, "renderer": {str(p.name): file_hash(p) for p in renderer_files(root_path)}})[:16]
    work = base / key
    work.mkdir(parents=True, exist_ok=True)
    timeline_path = work / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"root_path": root_path, "base": base, "timeline": timeline, "work": work,
            "timeline_path": timeline_path, "overrides": overrides}


def render_minimal_stills(*, root_dir: str | Path, episode_dir: str | Path, raw_props: dict[str, Any],
                          narration_end: float, times: list[float], log_path: Path,
                          timeout_seconds: int = 900) -> Path:
    """Render inspection stills through the same timeline/path handling as the final render."""
    prep = _prepare_work(root_dir, episode_dir, raw_props, narration_end)
    root_path, work = prep["root_path"], prep["work"]
    _run(["node", str(renderer_dir(root_path) / "render.cjs"), "--timeline", str(prep["timeline_path"]),
          "--work", str(work), "--chrome", str(find_chrome(root_path)),
          "--stills", ",".join(f"{t:g}" for t in times)],
         log_path=log_path, timeout_seconds=timeout_seconds, cwd=renderer_dir(root_path))
    return work / "stills"


def render_minimal_doc(*, root_dir: str | Path, episode_dir: str | Path, raw_props: dict[str, Any],
                       narration_end: float, timeout_seconds: int, log_path: Path) -> dict[str, Any]:
    """Render ``raw_props['outputPath']`` (video + lossless audio, normalized later by the caller)."""
    prep = _prepare_work(root_dir, episode_dir, raw_props, narration_end)
    root_path, base, timeline, work = prep["root_path"], prep["base"], prep["timeline"], prep["work"]
    timeline_path, overrides = prep["timeline_path"], prep["overrides"]

    video_only = work / "video.mp4"
    _run(["node", str(renderer_dir(root_path) / "render.cjs"), "--timeline", str(timeline_path), "--work", str(work),
          "--out", str(video_only), "--chrome", str(find_chrome(root_path)), "--workers", str(_workers())],
         log_path=log_path, timeout_seconds=timeout_seconds, cwd=renderer_dir(root_path))
    output = Path(str(raw_props["outputPath"]))
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video_only), "-i", str(raw_props["audioPath"]),
          "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "alac", "-shortest", str(output)], log_path=log_path)
    for leftover in (work / "chunks", work / "profiles", base / "assets" / "video_frames"):
        shutil.rmtree(leftover, ignore_errors=True)
    video_only.unlink(missing_ok=True)
    return {"renderer": RENDERER_ID, "output_path": str(output), "work_dir": str(work),
            "timeline_path": str(timeline_path), "shots": len(timeline["shots"]),
            "chapters": len(timeline["chapters"]), "video_shots": sum(s["kind"] == "video" for s in timeline["shots"]),
            "warnings": timeline["warnings"], "overrides_applied": sorted((overrides.get("assets") or {}).keys())}
