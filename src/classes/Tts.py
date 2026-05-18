import os
import asyncio
import subprocess
import wave
import struct

import requests

from config import (
    ROOT_DIR,
    get_tts_provider,
    get_tts_edge_voice,
    get_tts_edge_rate,
    get_tts_edge_thai_voice,
    get_tts_edge_thai_rate,
    get_tts_edge_thai_fallback_voice_id,
    get_gemini_tts_api_key,
    get_tts_gemini_thai_voice,
)
from runtime_trace import append_api_usage

_THAI_ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_GEMINI_TTS_TONE_PRESET = "natural_storyteller"


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
            return (
                "Director's Notes: Speak with urgency and intensity. This is the hook. "
                "Every word must land hard. Drive forward with energy."
            )
        if scene_index >= 0 and scene_index >= total_scenes - 1:
            return (
                "Director's Notes: Slow down slightly. Reflective. Philosophical. "
                "Leave the listener in quiet wonder, like the end of a great documentary."
            )
        if scene_index >= 0 and scene_index >= total_scenes - 7:
            return (
                "Director's Notes: Build intensity scene by scene. Each sentence carries more weight than the last. "
                "The listener should feel something is coming."
            )
        return (
            "Director's Notes: Speak with weight and intention, like a documentarian who knows something "
            "the audience doesn't yet. Natural pace, never dragging. Pause only after major reveals, "
            "0.3 seconds maximum. Build intensity as the scene progresses. Every sentence should feel deliberate."
        )

    if scene_index == 0:
        return (
            "Director's Notes: Start with calm documentary interest and steady energy, "
            "like a standard documentary narrator opening an episode. "
            "Keep it neutral, credible, and composed."
        )
    if scene_index >= 0 and scene_index >= total_scenes - 1:
        return (
            "Director's Notes: Slow down slightly and sound thoughtful, sincere, and steady. "
            "End with quiet reflection, not a dramatic finale or a friendly sign-off."
        )
    if scene_index >= 0 and scene_index >= total_scenes - 7:
        return (
            "Director's Notes: Keep the story engaging with gentle documentary curiosity. "
            "Let important moments feel meaningful without making the voice too bright, suspenseful, or playful."
        )
    return (
        "Director's Notes: Use natural Thai pacing in a standard documentary tone. "
        "Keep the delivery neutral, composed, and lightly engaged. "
        "Vary the rhythm gently, but do not perform the lines. "
        "Keep the emotion subtle and sincere."
    )


def _gemini_audio_profile(preset: str) -> str:
    if preset == "classic_documentary":
        return (
            "Audio Profile: A deep-voiced Thai male documentary narrator. "
            "Calm, measured, and slightly ominous, like a National Geographic narrator revealing a dark cosmic secret.\n\n"
            "Scene: A dimly lit recording booth. The narrator speaks as if revealing something the listener was never meant to know.\n\n"
        )
    return (
        "Audio Profile: A standard Thai documentary narrator with a clear, calm, neutral voice. "
        "Speak clearly and naturally, like narrating a documentary segment for a general audience. "
        "Keep Thai pronunciation clear and natural. "
        "Keep the tone human, measured, lightly engaged, and easy to listen to.\n\n"
        "Scene: A clean documentary narration booth. The narrator sounds neutral, thoughtful, and composed, "
        "with a smooth documentary delivery.\n\n"
    )


async def _edge_tts_synthesize(text: str, output_mp3: str, voice: str, rate: str) -> None:
    import edge_tts
    # rate="+0%" is the edge-tts default; "+20%" for energetic Shorts pacing.
    # NOTE: pitch= is NOT passed — silently ignored by Microsoft since edge-tts v6.0.3.
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_mp3)


class TTS:
    def __init__(self) -> None:
        self._provider = get_tts_provider()
        self._voice = get_tts_edge_voice()  # e.g. "en-US-ChristopherNeural"

    def _resolve_provider(self) -> str:
        provider = (self._provider or "edge").lower()
        if provider != "edge":
            raise ValueError(
                f"Unsupported TTS provider '{provider}'. Only 'edge' is implemented right now."
            )
        return provider

    def synthesize(self, text, output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav"), voice=None, rate=None):
        provider = self._resolve_provider()
        mp3_path = output_file.replace(".wav", ".mp3")
        _voice = voice if voice is not None else self._voice
        _rate = rate if rate is not None else get_tts_edge_rate()

        if provider == "edge":
            asyncio.run(_edge_tts_synthesize(text, mp3_path, _voice, _rate))
            append_api_usage("edge_tts", "chars", float(len(text or "")), voice=_voice, rate=_rate)

        # Convert mp3 -> wav using ffmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, output_file],
            check=True,
            capture_output=True,
        )
        os.remove(mp3_path)

        return output_file

    def synthesize_elevenlabs(self, text: str, output_file: str) -> str:
        """Synthesize speech using ElevenLabs API and write to output_file as WAV.

        Requests PCM audio (pcm_44100) from ElevenLabs and wraps it in a WAV
        header using the stdlib wave module — no extra dependencies.

        Args:
            text (str): Text to synthesize.
            output_file (str): Destination .wav path.

        Returns:
            output_file (str): Same path passed in.
        """
        from config import get_elevenlabs_api_key, get_elevenlabs_voice_id_th

        api_key = get_elevenlabs_api_key()
        voice_id = get_elevenlabs_voice_id_th()

        if not api_key or not voice_id:
            raise RuntimeError(
                "elevenlabs_api_key and elevenlabs_voice_id_th must be set in config.json"
            )

        mp3_path = output_file.replace(".wav", ".mp3")
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
        }

        last_error = None
        fallback_voice_id = get_tts_edge_thai_fallback_voice_id()
        for attempt_voice_id in [voice_id, fallback_voice_id]:
            try:
                response = requests.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{attempt_voice_id}",
                    params={"output_format": _THAI_ELEVENLABS_OUTPUT_FORMAT},
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                with open(mp3_path, "wb") as mp3_file:
                    mp3_file.write(response.content)
                append_api_usage(
                    "elevenlabs_tts",
                    "chars",
                    float(len(text or "")),
                    voice_id=attempt_voice_id,
                    model_id="eleven_multilingual_v2",
                )
                subprocess.run(
                    ["ffmpeg", "-y", "-i", mp3_path, output_file],
                    check=True,
                    capture_output=True,
                )
                os.remove(mp3_path)
                return output_file
            except requests.RequestException as exc:
                last_error = exc
                if attempt_voice_id != fallback_voice_id:
                    print(
                        "Warning: ElevenLabs Thai voice failed, retrying with accessible premade voice: "
                        f"{exc}"
                    )
                    continue
            except subprocess.CalledProcessError as exc:
                last_error = exc
                break
            finally:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)

        print(f"Warning: ElevenLabs failed for Thai TTS, falling back to Edge TTS: {last_error}")
        return self.synthesize(
            text,
            output_file=output_file,
            voice=get_tts_edge_thai_voice(),
            rate=get_tts_edge_thai_rate(),
        )

    def synthesize_gemini(
        self,
        text: str,
        output_file: str,
        scene_index: int = -1,
        total_scenes: int = 20,
        tone_preset: str | None = None,
    ) -> str:
        """Synthesize Thai speech via Google Gemini 3.1 Flash TTS Preview.

        Receives base64 PCM at 24 kHz/16-bit mono and writes a WAV file directly
        using the stdlib wave module — no ffmpeg conversion needed.

        Args:
            text (str): Text to synthesize.
            output_file (str): Destination .wav path.
            scene_index (int): 0-based scene index. -1 = default exposition style.
            total_scenes (int): Total scene count for climax/outro detection.

        Returns:
            output_file (str): Same path passed in.
        """
        import base64

        api_key = get_gemini_tts_api_key()
        if not api_key:
            raise RuntimeError("gemini_tts_api_key must be set in config.json")

        tone_preset = normalize_gemini_tts_tone_preset(tone_preset)
        directors_notes = _gemini_directors_notes(tone_preset, scene_index, total_scenes)
        audio_profile = _gemini_audio_profile(tone_preset)

        voice = get_tts_gemini_thai_voice()
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-3.1-flash-tts-preview:generateContent?key={api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                audio_profile +
                                f"{directors_notes}\n\n"
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
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                },
            },
        }

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        append_api_usage(
            "gemini_tts",
            "chars",
            float(len(text or "")),
            model="gemini-3.1-flash-tts-preview",
            voice=voice,
            tone_preset=tone_preset,
        )

        audio_b64 = response.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        pcm_data = base64.b64decode(audio_b64)

        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)   # 16-bit
            wf.setframerate(24000)
            wf.writeframes(pcm_data)

        return output_file
