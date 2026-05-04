from __future__ import annotations

import base64
import json
import subprocess
import urllib.error
import urllib.request
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from space_automation.config import SpaceAutomationConfig
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config import SpaceAutomationConfig


@dataclass(slots=True)
class TtsOutput:
    audio_path: str
    duration_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


def _gemini_tts_payload(text: str, voice_name: str) -> dict:
    return {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Audio profile: A cinematic documentary narrator for short-form space videos. "
                            "Clear, grounded, and emotionally controlled. Never cheesy. "
                            "Read naturally with dramatic restraint.\n\n"
                            "Transcript:\n"
                            f"{text}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name},
                }
            },
        },
    }


def _request_gemini_pcm(text: str, config: SpaceAutomationConfig) -> bytes:
    if not config.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY or gemini_tts_api_key is not configured.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={config.gemini_api_key}"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(_gemini_tts_payload(text, config.gemini_tts_voice)).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=max(config.request_timeout_seconds, 120)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS API error {exc.code}: {detail}") from exc

    try:
        audio_b64 = payload["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini TTS response did not include inline audio data.") from exc

    return base64.b64decode(audio_b64)


def _write_wav_from_pcm(pcm_data: bytes, wav_path: Path) -> None:
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)


def _convert_wav_to_mp3(wav_path: Path, mp3_path: Path, config: SpaceAutomationConfig) -> None:
    command = [
        config.ffmpeg_path,
        "-y",
        "-i",
        str(wav_path),
        "-vn",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        str(mp3_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed to convert WAV to MP3: "
            f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        )


def probe_audio_duration(audio_path: Path, config: SpaceAutomationConfig) -> float:
    command = [
        config.ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffprobe failed to read duration: "
            f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        )

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid ffprobe duration output: {result.stdout!r}") from exc


def synthesize_speech_to_mp3(text: str, output_path: Path, config: SpaceAutomationConfig) -> TtsOutput:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_wav_path = output_path.with_suffix(".wav")

    pcm_data = _request_gemini_pcm(text=text, config=config)
    _write_wav_from_pcm(pcm_data, temp_wav_path)
    try:
        _convert_wav_to_mp3(temp_wav_path, output_path, config)
        duration_seconds = probe_audio_duration(output_path, config)
    finally:
        if temp_wav_path.exists():
            temp_wav_path.unlink()

    return TtsOutput(
        audio_path=str(output_path),
        duration_seconds=duration_seconds,
    )
