"""Word-level timestamps for chosen ranges: words.py <video> <out.json> start-end [start-end ...] (seconds)."""
import json
import subprocess
import sys

import numpy as np
import whisper

video, out, ranges = sys.argv[1], sys.argv[2], sys.argv[3:]
model = whisper.load_model("small.en")
words = []
for r in ranges:
    t0, t1 = (float(x) for x in r.split("-"))
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", video, "-vn", "-ac", "1",
                          "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    res = model.transcribe(audio, language="en", word_timestamps=True, verbose=None)
    for seg in res["segments"]:
        for w in seg["words"]:
            words.append({"t": round(t0 + w["start"], 2), "end": round(t0 + w["end"], 2), "w": w["word"].strip()})
json.dump(words, open(out, "w", encoding="utf-8"), indent=0)
print(len(words), "words")
