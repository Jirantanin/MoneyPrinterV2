"""Gemini TTS client for Producer Mode narration.

Gemini 3.8 TTS uses the Interactions API: the text is spoken verbatim, and delivery
direction goes into a ``speech_metadata`` annotation instead of being prefixed to the
transcript. Unary responses carry base64 WAV (24 kHz mono 16-bit) in ``steps[].content[].data``.
"""

import base64
import io
import wave

import requests

from config import get_gemini_tts_api_key, get_gemini_tts_model, get_tts_gemini_thai_voice
from runtime_trace import append_api_usage

DEFAULT_GEMINI_TTS_TONE_PRESET = "natural_storyteller"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
PCM_SAMPLE_RATE = 24000
HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False


def normalize_gemini_tts_tone_preset(value: str | None) -> str:
    preset = (value or DEFAULT_GEMINI_TTS_TONE_PRESET).strip().lower().replace("-", "_")
    aliases = {
        "natural": "natural_storyteller",
        "normal": "natural_storyteller",
        "storyteller": "natural_storyteller",
        "natural_storyteller": "natural_storyteller",
        "classic": "classic_documentary",
        "documentary": "classic_documentary",
        "documentary_dread": "classic_documentary",
        "classic_documentary": "classic_documentary",
    }
    return aliases.get(preset, DEFAULT_GEMINI_TTS_TONE_PRESET)


def _gemini_directors_notes(preset: str, scene_index: int, total_scenes: int) -> str:
    if preset == "classic_documentary":
        if scene_index == 0:
            return "Urgent and intense; this is the hook. Every word lands hard, driving forward with energy."
        if scene_index >= 0 and scene_index >= total_scenes - 1:
            return "Slightly slower, reflective and philosophical; leave the listener in quiet wonder."
        if scene_index >= 0 and scene_index >= total_scenes - 7:
            return "Build intensity scene by scene; each sentence carries more weight than the last."
        return ("Weight and intention, like a documentarian who knows something the audience doesn't yet. "
                "Natural pace, never dragging; pause only briefly after major reveals.")

    if scene_index == 0:
        return "Calm documentary interest with steady energy, opening an episode; neutral, credible, composed."
    if scene_index >= 0 and scene_index >= total_scenes - 1:
        return "Slightly slower, thoughtful, sincere and steady; end in quiet reflection, not a dramatic finale."
    if scene_index >= 0 and scene_index >= total_scenes - 7:
        return ("Gentle documentary curiosity; let important moments feel meaningful without sounding "
                "bright, suspenseful or playful.")
    return ("Natural Thai pacing in a standard documentary tone; neutral, composed, lightly engaged. "
            "Vary rhythm gently without performing the lines; subtle, sincere emotion.")


def _gemini_audio_profile(preset: str) -> str:
    if preset == "classic_documentary":
        return ("Deep-voiced Thai male documentary narrator, calm, measured and slightly ominous, "
                "as if revealing a cosmic secret.")
    return ("Standard Thai documentary narrator with a clear, calm, neutral voice and clear, natural Thai "
            "pronunciation; human, measured and easy to listen to.")


def gemini_speech_style(preset: str, scene_index: int = -1, total_scenes: int = 20) -> str:
    """Delivery direction for the ``speech_metadata`` annotation (never spoken)."""
    preset = normalize_gemini_tts_tone_preset(preset)
    return f"{_gemini_audio_profile(preset)} {_gemini_directors_notes(preset, scene_index, total_scenes)}"


def build_interaction_payload(text: str, *, model: str, voice: str, style: str) -> dict:
    return {
        "model": model,
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}],
            }],
        }],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }


def find_audio_b64(body: object) -> str | None:
    """Return the first base64 audio payload in an Interactions response."""
    if isinstance(body, dict):
        steps = body.get("steps")
        if isinstance(steps, list):
            for step in steps:
                for item in (step or {}).get("content") or []:
                    if isinstance(item, dict) and item.get("data"):
                        return str(item["data"])
        for value in body.values():
            found = find_audio_b64(value) if isinstance(value, (dict, list)) else None
            if found:
                return found
    elif isinstance(body, list):
        for value in body:
            found = find_audio_b64(value)
            if found:
                return found
    return None


def write_wav(audio: bytes, output_file: str) -> float:
    """Write Gemini audio (RIFF WAV, or headerless 24 kHz mono PCM) and return its duration."""
    if audio[:4] == b"RIFF":
        with wave.open(io.BytesIO(audio), "rb") as source:
            channels, width, rate = source.getnchannels(), source.getsampwidth(), source.getframerate()
            frames = source.readframes(source.getnframes())
    else:
        channels, width, rate, frames = 1, 2, PCM_SAMPLE_RATE, audio
    if not frames:
        raise RuntimeError("Gemini TTS returned empty audio")
    with wave.open(output_file, "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(width)
        target.setframerate(rate)
        target.writeframes(frames)
    return len(frames) / (channels * width * rate)


class TTS:
    def synthesize_gemini(
        self,
        text: str,
        output_file: str,
        scene_index: int = -1,
        total_scenes: int = 20,
        tone_preset: str | None = None,
        timeout_seconds: int = 180,
    ) -> str:
        """Synthesize Thai narration with Gemini TTS and write ``output_file`` as WAV."""
        api_key = get_gemini_tts_api_key()
        if not api_key:
            raise RuntimeError("gemini_tts_api_key must be set in config.json")

        tone_preset = normalize_gemini_tts_tone_preset(tone_preset)
        model, voice = get_gemini_tts_model(), get_tts_gemini_thai_voice()
        payload = build_interaction_payload(
            text, model=model, voice=voice, style=gemini_speech_style(tone_preset, scene_index, total_scenes))

        response = HTTP_SESSION.post(
            GEMINI_INTERACTIONS_URL,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        append_api_usage("gemini_tts", "chars", float(len(text or "")), model=model, voice=voice,
                         tone_preset=tone_preset)

        audio_b64 = find_audio_b64(response.json())
        if not audio_b64:
            raise RuntimeError("Gemini TTS response contained no audio")
        duration_seconds = write_wav(base64.b64decode(audio_b64), output_file)
        append_api_usage("gemini_tts", "seconds", float(duration_seconds), model=model, voice=voice,
                         tone_preset=tone_preset)
        return output_file
