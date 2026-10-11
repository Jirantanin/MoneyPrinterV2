"""Offline tests for the Gemini 3.8 TTS client (Interactions API); no network calls."""
from __future__ import annotations

import base64
import io
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from classes import Tts
from classes.Tts import TTS, build_interaction_payload, find_audio_b64, gemini_speech_style, write_wav


def wav_bytes(seconds: float, rate: int = 24000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x01" * int(seconds * rate))
    return buffer.getvalue()


class PayloadTests(unittest.TestCase):
    def test_transcript_is_verbatim_and_style_is_an_annotation(self):
        payload = build_interaction_payload("สวัสดี", model="gemini-3.8-flash-tts", voice="Enceladus", style="calm")
        content = payload["input"][0]["content"][0]
        self.assertEqual(content["text"], "สวัสดี")
        self.assertEqual(content["annotations"], [{"type": "speech_metadata", "style": "calm"}])
        self.assertEqual(payload["generation_config"]["speech_config"], [{"voice": "Enceladus"}])
        self.assertEqual(payload["response_format"], {"type": "audio"})

    def test_style_varies_by_position_and_preset(self):
        self.assertNotEqual(gemini_speech_style("natural", 0, 10), gemini_speech_style("natural", 9, 10))
        self.assertIn("ominous", gemini_speech_style("classic", 3, 20))
        self.assertNotIn("Director", gemini_speech_style("natural", 3, 20))


class AudioTests(unittest.TestCase):
    def test_find_audio_in_steps(self):
        body = {"id": "x", "steps": [{"type": "thought"}, {"content": [{"type": "audio", "data": "QUJD"}]}]}
        self.assertEqual(find_audio_b64(body), "QUJD")
        self.assertIsNone(find_audio_b64({"steps": [{"content": [{"type": "text", "text": "no"}]}]}))

    def test_write_wav_accepts_riff_and_raw_pcm(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "a.wav"
            self.assertAlmostEqual(write_wav(wav_bytes(1.5), str(out)), 1.5, places=3)
            self.assertAlmostEqual(write_wav(b"\x00\x00" * 24000, str(out)), 1.0, places=3)
            with wave.open(str(out)) as check:
                self.assertEqual((check.getframerate(), check.getnchannels()), (24000, 1))
            with self.assertRaises(RuntimeError):
                write_wav(b"", str(out))

    def test_synthesize_posts_interaction_and_writes_wav(self):
        response = MagicMock()
        response.json.return_value = {"steps": [{"content": [{"type": "audio",
                                                              "data": base64.b64encode(wav_bytes(0.5)).decode()}]}]}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(Tts, "get_gemini_tts_api_key", return_value="k"), \
             patch.object(Tts, "get_gemini_tts_model", return_value="gemini-3.8-flash-tts"), \
             patch.object(Tts, "get_tts_gemini_thai_voice", return_value="Enceladus"), \
             patch.object(Tts, "append_api_usage"), \
             patch.object(Tts.HTTP_SESSION, "post", return_value=response) as post:
            out = Path(tmp) / "scene_00.wav"
            TTS().synthesize_gemini("ข้อความ", str(out), scene_index=0, total_scenes=3)
            url, kwargs = post.call_args[0][0], post.call_args[1]
            self.assertEqual(url, Tts.GEMINI_INTERACTIONS_URL)
            self.assertEqual(kwargs["headers"]["x-goog-api-key"], "k")
            self.assertEqual(kwargs["json"]["model"], "gemini-3.8-flash-tts")
            self.assertEqual(kwargs["json"]["input"][0]["content"][0]["text"], "ข้อความ")
            with wave.open(str(out)) as check:
                self.assertAlmostEqual(check.getnframes() / check.getframerate(), 0.5, places=3)


if __name__ == "__main__":
    unittest.main()
