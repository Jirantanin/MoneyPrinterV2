import os
import asyncio
import subprocess

from config import ROOT_DIR, get_tts_voice, get_tts_rate


async def _edge_tts_synthesize(text: str, output_mp3: str, voice: str, rate: str) -> None:
    import edge_tts
    # rate="+0%" is the edge-tts default; "+20%" for energetic Shorts pacing.
    # NOTE: pitch= is NOT passed — silently ignored by Microsoft since edge-tts v6.0.3.
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_mp3)


class TTS:
    def __init__(self) -> None:
        self._voice = get_tts_voice()  # e.g. "en-US-ChristopherNeural"

    def synthesize(self, text, output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav")):
        mp3_path = output_file.replace(".wav", ".mp3")
        rate = get_tts_rate()  # re-read config on every call per project convention
        asyncio.run(_edge_tts_synthesize(text, mp3_path, self._voice, rate))

        # Convert mp3 -> wav using ffmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, output_file],
            check=True,
            capture_output=True,
        )
        os.remove(mp3_path)

        return output_file
