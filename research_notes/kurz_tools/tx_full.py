"""Whole-clip transcript with segments and word timestamps: tx_full.py <video> <out.json>"""
import json
import subprocess
import sys

import numpy as np
import whisper

video, out = sys.argv[1], sys.argv[2]
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
res = whisper.load_model("small.en").transcribe(audio, language="en", word_timestamps=True, verbose=None)
segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip(),
         "words": [{"t": round(w["start"], 2), "w": w["word"].strip()} for w in s["words"]]} for s in res["segments"]]
json.dump(segs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(out, len(segs), "segments")
