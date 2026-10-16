"""Vertical all-graphics Short (own narration, flat explainer graphics) that promotes a Producer Mode episode.

A short lives in its own folder, usually .mp/<episode>/shorts_promo_gfx/, holding:
  script.json  {name, lead, tail, keywords, mix: {score_db, sfx_db}, upload: {...},
                scenes: [{id, narration, anchors?: {name: phrase}, captions?: [chunk, ...], gap_after?}]}
               Thai has no spaces between words, so give long beats explicit caption chunks.
  short.html   page built on doc_renderer/gfx_kit/kit.js + shorts.js; it loads timing.js written by `align`
  score_cues.json  cue sheet for src/producer_score.py (times in short seconds, "~t" snaps to a speech onset)

Steps (repo root, project venv):
  python scripts/producer_gfx_short.py tts    --dir <short>   Gemini TTS per beat -> audio_raw/<id>.wav (paid; existing files are kept)
  python scripts/producer_gfx_short.py align  --dir <short>   trim + place beats -> narration.wav, timing.js/json, subtitle.srt
  python scripts/producer_gfx_short.py stills --dir <short> --at 1,5,9  -> stills/s_<t>.jpg + stills/sheet.jpg
  python scripts/producer_gfx_short.py record --dir <short>   1080x1920 30 fps -> video_silent.mp4 (+ .sfx.json from the page)
script.json may set "size": "1920x1080" and "fps": 25 for a landscape test cut; the page then calls bootShort(seed, builders,
{ w: 1920, h: 1080, captions: false }).
  python scripts/producer_gfx_short.py audio  --dir <short>   score + SFX + narration -> mix.wav at -14 LUFS
  python scripts/producer_gfx_short.py mux    --dir <short>   -> <name>.mp4 (+ final.mp4), preview sheet, upload_pack/
  then upload like an episode: python scripts/youtube_upload.py request --plan <short>/script.json --thumbnail ...
Every claim in script.json must come from the episode's reviewed script; nobody hears the score but a person.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

THAI_MARKS = re.compile("[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]")


def load(d: Path) -> dict:
    return json.loads((d / "script.json").read_text(encoding="utf-8-sig"))


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return (a.reshape(-1, ch).mean(1) if ch > 1 else a), sr


def write_mono(path: Path, a: np.ndarray, sr: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def run(cmd: list[str]) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        raise SystemExit(f"failed: {' '.join(cmd[:4])}...\n{out.stderr[-2000:]}")
    return out.stdout + out.stderr


# ---------------------------------------------------------------- tts
def cmd_tts(d: Path, force: bool) -> None:
    from classes.Tts import TTS
    spec, tts = load(d), TTS()
    (d / "audio_raw").mkdir(exist_ok=True)
    scenes = spec["scenes"]
    for i, s in enumerate(scenes):
        out = d / "audio_raw" / f"{s['id']}.wav"
        if out.exists() and not force:
            print("keep", out.name); continue
        tts.synthesize_gemini(s["narration"], str(out), scene_index=i, total_scenes=len(scenes), tone_preset="host_dry")
        print("tts", out.name, round(read_wav(out)[0].size / read_wav(out)[1], 2), "s")
        time.sleep(7)  # Tier 1 allows 10 requests a minute


# ---------------------------------------------------------------- align
def voiced_bounds(a: np.ndarray, sr: int) -> tuple[int, int]:
    hop = int(sr * .01); n = len(a) // hop
    db = 20 * np.log10(np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    thr = np.percentile(db[db > -80], 60) - 24
    v = np.where(db > thr)[0]
    return int(v[0] * hop), int((v[-1] + 1) * hop)


def chunks(text: str, max_base: int = 17) -> list[str]:
    width = lambda s: len(THAI_MARKS.sub("", s.replace(" ", "")))  # noqa: E731
    out: list[str] = []
    for tok in text.split():
        if out and width(out[-1] + tok) <= max_base and not out[-1].endswith("?"):
            out[-1] += " " + tok
        else:
            out.append(tok)
    return out


def squash(s: str) -> str:
    return re.sub(r"[\s?!.,]", "", s)


def char_times(script: str, words: list[tuple[str, float, float]], dur: float) -> list[float]:
    """Time of each non-space script character, by aligning it to Whisper's word-timed characters."""
    heard, times = "", []
    for text, t0, t1 in words:
        w = squash(text)
        for k in range(len(w)):
            times.append(t0 + (t1 - t0) * k / max(1, len(w)))
        heard += w
    s = squash(script)
    known: dict[int, float] = {}
    for a, b, size in difflib.SequenceMatcher(None, s, heard, autojunk=False).get_matching_blocks():
        for k in range(size):
            known[a + k] = times[b + k]
    keys = sorted(known)
    if len(keys) < 2:
        return [dur * i / max(1, len(s)) for i in range(len(s))]
    return [float(np.interp(i, keys, [known[k] for k in keys])) for i in range(len(s))]


def cmd_align(d: Path, model_size: str) -> None:
    from faster_whisper import WhisperModel
    from producer_score import speech_onsets
    spec = load(d)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    (d / "audio").mkdir(exist_ok=True)
    pieces, beats, captions, anchors, words_log = [], [], [], {}, {}
    sr0 = None
    cursor = float(spec.get("lead", 0.12))
    for s in spec["scenes"]:
        a, sr = read_wav(d / "audio_raw" / f"{s['id']}.wav")
        sr0 = sr0 or sr
        assert sr == sr0, "all beats must share one sample rate"
        i0, i1 = voiced_bounds(a, sr)
        a = a[max(0, i0 - int(.05 * sr)): min(len(a), i1 + int(.1 * sr))]
        write_mono(d / "audio" / f"{s['id']}.wav", a, sr)
        dur = len(a) / sr
        segs, _ = model.transcribe(str(d / "audio" / f"{s['id']}.wav"), language="th", beam_size=5, word_timestamps=True)
        words = [(w.word, w.start, w.end) for seg in segs for w in (seg.words or [])]
        words_log[s["id"]] = [[w, round(t0, 2), round(t1, 2)] for w, t0, t1 in words]
        ct = char_times(s["narration"], words, dur)
        flat = squash(s["narration"])
        pos = 0
        caps = s.get("captions") or chunks(s["narration"])
        if squash("".join(caps)) != flat:
            raise SystemExit(f"captions of beat {s['id']} do not spell its narration")
        for c in caps:
            k = flat.find(squash(c), pos); pos = k + len(squash(c))
            captions.append({"beat": s["id"], "t0": round(cursor + max(0.0, ct[k] - .06), 3), "text": c})
        for name, phrase in (s.get("anchors") or {}).items():
            k = flat.find(squash(phrase))
            if k < 0:
                raise SystemExit(f"anchor {name!r}: {phrase!r} not in beat {s['id']}")
            anchors[name] = round(cursor + ct[k], 3)
        beats.append({"id": s["id"], "start": round(cursor, 3), "speech_end": round(cursor + dur, 3)})
        pieces.append((cursor, a))
        cursor += dur + float(s.get("gap_after", 0.28))
    total = round(cursor - float(spec["scenes"][-1].get("gap_after", 0.28)) + float(spec.get("tail", 1.6)), 3)
    for i, b in enumerate(beats):
        b["end"] = beats[i + 1]["start"] if i + 1 < len(beats) else total
    for i, c in enumerate(captions):
        beat = next(b for b in beats if b["id"] == c["beat"])
        nxt = captions[i + 1]["t0"] if i + 1 < len(captions) and captions[i + 1]["beat"] == c["beat"] else beat["speech_end"] + .2
        c["t1"] = round(min(nxt, beat["end"]), 3)
    mix = np.zeros(int(total * sr0) + 1)
    for t0, a in pieces:
        i = int(t0 * sr0); mix[i:i + len(a)] += a
    write_mono(d / "narration.wav", mix, sr0)
    timing = {"dur": total, "fps": frame(spec)[2], "beats": beats, "captions": captions, "at": anchors,
              "onsets": speech_onsets(d / "narration.wav"), "keywords": spec.get("keywords", [])}
    (d / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "timing.js").write_text("window.SHORT = " + json.dumps(timing, ensure_ascii=False) + ";\n", encoding="utf-8")
    (d / "whisper_words.json").write_text(json.dumps(words_log, ensure_ascii=False, indent=1), encoding="utf-8")
    srt = []
    for n, c in enumerate(captions, 1):
        f = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"  # noqa: E731
        srt.append(f"{n}\n{f(c['t0'])} --> {f(c['t1'])}\n{c['text']}\n")
    (d / "subtitle.srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"[OK] {len(beats)} beats, {len(captions)} captions, {total:.2f} s")
    for b in beats:
        print(f"  {b['id']}: {b['start']:.2f} -> {b['speech_end']:.2f} (next {b['end']:.2f})")
    for k, v in anchors.items():
        print(f"  @{k} = {v:.2f}")


# ---------------------------------------------------------------- page
RECORD = ROOT / "doc_renderer" / "gfx_kit" / "record.cjs"


def timing(d: Path) -> dict:
    return json.loads((d / "timing.json").read_text(encoding="utf-8"))


def frame(spec: dict) -> tuple[int, int, int]:
    w, h = map(int, spec.get("size", "1080x1920").split("x"))
    return w, h, int(spec.get("fps", 30))


def cmd_stills(d: Path, at: str) -> None:
    (d / "stills").mkdir(exist_ok=True)
    W, H, _ = frame(load(d))
    run(["node", str(RECORD), str(d / "short.html"), "main", "1", str(d / "stills" / "s"), "--stills", at, "--size", f"{W}x{H}"])
    ts = at.split(",")
    ins = sum([["-i", str(d / "stills" / f"s_{t}.jpg")] for t in ts], [])
    n = len(ts)
    fc = "".join(f"[{i}:v]scale=-2:640[v{i}];" for i in range(n)) + "".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}"
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, str(d / "stills" / "sheet.jpg")])
    print(d / "stills" / "sheet.jpg")


def cmd_record(d: Path) -> None:
    dur = timing(d)["dur"]
    W, H, fps = frame(load(d))
    out = d / "video_silent.mp4"
    run(["node", str(RECORD), str(d / "short.html"), "main", str(dur), str(out), "--size", f"{W}x{H}", "--fps", str(fps)])
    print("[OK]", out)


# ---------------------------------------------------------------- audio
def sfx_sound(fx, kind: str, o: dict) -> np.ndarray:
    if kind == "pop":
        return fx.pop(lvl=o.get("lvl", .8))
    if kind == "boing":
        return fx.boing(o.get("up", True), lvl=.7)
    if kind == "tick":
        return fx.tick(lvl=.6)
    if kind == "chime":
        notes = o.get("notes", [81])
        out = np.zeros(int((1.8 + .12 * len(notes)) * fx.SR))
        for i, m in enumerate(notes):
            b = fx.bell(m, 1.6, .5); k = int(i * .12 * fx.SR); out[k:k + len(b)] += b
        return out
    if kind in ("whoosh", "rise", "fall"):
        return fx.whoosh(o.get("d", .8), lvl=.4, rise=kind != "fall")
    if kind == "thump":
        return fx.thump(.7)
    if kind == "boom":
        return fx.boom(.7)
    if kind == "sparkle":
        return fx.sparkle()
    if kind == "engine":
        return fx.engine(o.get("d", 1.5))
    if kind == "alert":
        return fx.alert()
    raise ValueError(kind)


def lufs(path: Path) -> float:
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"]))[-1])


def cmd_audio(d: Path) -> None:
    import producer_sfx_synth as fx
    from producer_score import render_score, write_wav
    spec, tm = load(d), timing(d)
    dur, levels = tm["dur"], {"score_db": -17.0, "sfx_db": -13.0, **spec.get("mix", {})}
    # narration -> 48 kHz stereo
    run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "narration.wav"), "-ar", "48000", "-ac", "2", str(d / "narr48.wav")])
    # score, loudness-matched to the narration before the bed gain
    cues = json.loads((d / "score_cues.json").read_text(encoding="utf-8"))
    cues["total_seconds"] = dur
    write_wav(d / "score.wav", render_score(cues, tm["onsets"]))
    # sfx stem from the page's cue log
    log = d / "video_silent.sfx.json"
    stem = fx.Stem(dur)
    for c in json.loads(log.read_text(encoding="utf-8")) if log.exists() else []:
        t, kind, o = (c[0], c[1], c[2] if len(c) > 2 else {}) if isinstance(c, list) else (c["t"], c["kind"], c)
        if 0 <= t < dur:
            stem.add(sfx_sound(fx, kind, o), t, pan=float(o.get("pan", .15 * np.sin(t * 1.7))))
    fx.write_wav(d / "sfx.wav", stem.finished())
    narr_lufs, score_lufs = lufs(d / "narr48.wav"), lufs(d / "score.wav")
    score_gain = narr_lufs - score_lufs + levels["score_db"]
    run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "narr48.wav"), "-i", str(d / "score.wav"), "-i", str(d / "sfx.wav"),
         "-filter_complex",
         f"[1:a]volume={score_gain:.2f}dB[s];[2:a]volume={levels['sfx_db']:.2f}dB[x];"
         "[0:a][s][x]amix=inputs=3:normalize=0:duration=first[m]", "-map", "[m]", "-ar", "48000", str(d / "premix.wav")])
    pre = lufs(d / "premix.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "premix.wav"), "-af",
         f"volume={-14.0 - pre:.2f}dB,alimiter=limit=0.84:level=false", "-ar", "48000", str(d / "mix.wav")])
    print(f"[OK] mix.wav  narration {narr_lufs:.1f} LUFS, score gain {score_gain:.1f} dB, premix {pre:.1f} -> mix {lufs(d / 'mix.wav'):.1f} LUFS")


# ---------------------------------------------------------------- mux + pack
def probe(path: Path) -> dict:
    j = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return {"width": v["width"], "height": v["height"], "fps": v["r_frame_rate"], "duration": float(j["format"]["duration"]),
            "size_mb": round(int(j["format"]["size"]) / 1e6, 2), "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def cmd_mux(d: Path) -> None:
    spec, tm = load(d), timing(d)
    name = spec["name"]
    out = d / f"{name}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "video_silent.mp4"), "-i", str(d / "mix.wav"), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)])
    up = spec.get("upload", {})
    pack = d / "upload_pack"
    pack.mkdir(exist_ok=True)
    shutil.copy2(out, pack / "video.mp4")
    shutil.copy2(d / "subtitle.srt", pack / "subtitle.srt")
    for key, t in (("thumbnail.jpg", up.get("thumbnail_at", 2.0)), ("preview_keyword_pop.jpg", up.get("preview_at", 6.0))):
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(out), "-frames:v", "1", "-q:v", "2", str(pack / key)])
    ts = [round(tm["dur"] * k / 6, 2) for k in range(6)]
    ins = sum([["-ss", str(t), "-i", str(out)] for t in ts], [])
    fc = "".join(f"[{i}:v]scale=-2:480[v{i}];" for i in range(6)) + "".join(f"[v{i}]" for i in range(6)) + "hstack=inputs=6"
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-frames:v", "1", str(d / "preview_sheet.jpg")])
    (pack / "title.txt").write_text(up.get("title", ""), encoding="utf-8")
    (pack / "description.txt").write_text(up.get("description", ""), encoding="utf-8")
    (pack / "hashtags.txt").write_text(" ".join(up.get("hashtags", [])), encoding="utf-8")
    (pack / "keywords.txt").write_text(", ".join(spec.get("keywords", [])), encoding="utf-8")
    info = probe(out)
    manifest = {"name": name, "episode": spec.get("episode"), "full_episode_url": spec.get("full_episode_url"),
                "video": str(out.relative_to(ROOT)), "probe": info, "narration": [s["narration"] for s in spec["scenes"]],
                "made_with": "scripts/producer_gfx_short.py + doc_renderer/gfx_kit (kit.js, shorts.js)",
                "audio": "Gemini TTS en-us-knox host_dry; score and SFX synthesized for this short"}
    (pack / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # the folder doubles as an "episode" for scripts/youtube_upload.py (--plan <short>/script.json)
    shutil.copy2(out, d / "final.mp4")
    (pack / "metadata.json").write_text(json.dumps(
        {"title": up.get("title", ""), "description": up.get("description", ""), "description_source": "short_script_upload",
         "tags": [h.lstrip("#") for h in up.get("hashtags", [])] + ["รู้ดีกว่า"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK]", out, info)
    print("     ", pack)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["tts", "align", "stills", "record", "audio", "mux"])
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="tts: re-synthesize existing beats")
    ap.add_argument("--model", default="medium", help="align: faster-whisper size")
    ap.add_argument("--at", default="1,4,8,12,16,20", help="stills: page times")
    a = ap.parse_args()
    d = a.dir.resolve()
    {"tts": lambda: cmd_tts(d, a.force), "align": lambda: cmd_align(d, a.model), "stills": lambda: cmd_stills(d, a.at),
     "record": lambda: cmd_record(d), "audio": lambda: cmd_audio(d), "mux": lambda: cmd_mux(d)}[a.step]()
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Windows cp874 consoles cannot print every character
        _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
