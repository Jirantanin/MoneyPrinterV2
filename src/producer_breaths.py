"""Breath pauses and the opening-sting lead for Producer Mode scene audio.

scene_NN.wav is rebuilt from the raw TTS take (kept once in audio_raw/) on every run, so the step is idempotent:
  - script.json scene ``breath_after_seconds`` -> silence appended after that scene
  - minimal_render_overrides.json ``opening.seconds`` -> silence prepended to scene 0, so the narration starts after
    the opening sting (the same number marks the sting slot for the renderer)
Run after produce-tts/audio-qc and before the speech map: scripts/producer_pad_breaths.py --plan <plan>.
"""
from __future__ import annotations

import json
import shutil
import wave
from pathlib import Path
from typing import Any

from producer_contract import read_json


def pad_breaths(episode_dir: str | Path) -> dict[str, Any]:
    episode = Path(episode_dir)
    scenes = json.loads((episode / "script.json").read_text(encoding="utf-8"))
    opening = float(((read_json(episode / "minimal_render_overrides.json", {}) or {}).get("opening") or {}).get("seconds") or 0.0)
    raw_dir = episode / "audio_raw"
    raw_dir.mkdir(exist_ok=True)
    report = []
    for index, scene in enumerate(scenes):
        wav_path = episode / f"scene_{index:02d}.wav"
        raw_path = raw_dir / wav_path.name
        if not raw_path.exists():
            shutil.copy2(wav_path, raw_path)
        with wave.open(str(raw_path), "rb") as src:
            params = src.getparams()
            frames = src.readframes(params.nframes)
        lead = opening if index == 0 else 0.0
        pad = float(scene.get("breath_after_seconds") or 0.0)
        silence = lambda s: b"\x00" * (int(round(s * params.framerate)) * params.sampwidth * params.nchannels)
        with wave.open(str(wav_path), "wb") as dst:
            dst.setparams(params)
            dst.writeframes(silence(lead) + frames + silence(pad))
        report.append({"scene_index": index, "speech_seconds": round(params.nframes / params.framerate, 3),
                       "lead_seconds": lead, "breath_after_seconds": pad})
    result = {"opening_seconds": opening, "scenes": report}
    (episode / "breath_pauses.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
