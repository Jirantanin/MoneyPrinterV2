import json
import sys

import whisper

wav, out = sys.argv[1], sys.argv[2]
model = whisper.load_model("small.en")
result = model.transcribe(wav, language="en", verbose=False)
segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()} for s in result["segments"]]
with open(out, "w", encoding="utf-8") as f:
    json.dump(segs, f, ensure_ascii=False, indent=1)
print(len(segs), "segments")
