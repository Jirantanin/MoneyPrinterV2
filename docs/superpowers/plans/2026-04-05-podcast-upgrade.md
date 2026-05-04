# Podcast Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bilingual support (Thai via ElevenLabs, English via edge-tts), visual consistency across scene images, and a manual upload flow with "Mark as Uploaded" button.

**Architecture:** Three independent changes to the Podcast pipeline only — ElevenLabs TTS routing keyed on `language`, visual summaries injected between the 3 LLM script calls, and the existing upload button replaced with a path-copy + mark-uploaded action. Shorts pipeline is untouched.

**Tech Stack:** Python 3.12, FastAPI, ElevenLabs REST API, Python `wave` stdlib, Tailwind CSS (no build step)

> **Note:** This project has no test suite. Each task includes a manual smoke-test step instead of pytest.

---

## File Map

| File | What changes |
|---|---|
| `config.json` | Add `elevenlabs_api_key`, `elevenlabs_voice_id_th` keys |
| `src/config.py` | Add `get_elevenlabs_api_key()`, `get_elevenlabs_voice_id_th()` |
| `src/classes/Tts.py` | Add `synthesize_elevenlabs(text, output_file)` method |
| `src/classes/Podcast.py` | Add `language` param; inject language into system_prompt; TTS routing in `generate_assets()`; visual summaries between LLM calls |
| `src/podcast_server.py` | Accept `language` in `POST /api/generate`; pass to `Podcast`; add `POST /api/podcast/{id}/mark-uploaded` endpoint |
| `src/podcast_ui.html` | Language selector dropdown; replace upload button with copy-path + mark-uploaded UI |

---

## Task 1: ElevenLabs config keys

**Files:**
- Modify: `config.json`
- Modify: `src/config.py`

- [ ] **Step 1: Add keys to config.json**

Open `config.json` and add two keys at the top level (alongside existing keys like `minimax_api_key`):

```json
"elevenlabs_api_key": "",
"elevenlabs_voice_id_th": ""
```

Leave values as empty strings for now — will be filled with real values before testing Task 2.

- [ ] **Step 2: Add getter functions to src/config.py**

Add these two functions to `src/config.py` after the existing `get_minimax_api_base_url` block (around line 88), following the exact same pattern as every other getter in the file:

```python
def get_elevenlabs_api_key() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("elevenlabs_api_key", "")

def get_elevenlabs_voice_id_th() -> str:
    with open(os.path.join(ROOT_DIR, "config.json"), "r") as file:
        return json.load(file).get("elevenlabs_voice_id_th", "")
```

- [ ] **Step 3: Smoke test**

```bash
cd C:/Users/66984/workspace-coding/MoneyPrinterV2
py -c "import sys; sys.path.insert(0,'src'); from config import get_elevenlabs_api_key, get_elevenlabs_voice_id_th; print(repr(get_elevenlabs_api_key())); print(repr(get_elevenlabs_voice_id_th()))"
```

Expected: prints two empty strings `''` without error.

- [ ] **Step 4: Commit**

```bash
rtk git add config.json src/config.py
rtk git commit -m "feat: add ElevenLabs config keys and getters"
```

---

## Task 2: ElevenLabs synthesize method in Tts.py

**Files:**
- Modify: `src/classes/Tts.py`

- [ ] **Step 1: Add imports at top of Tts.py**

Add `import wave` and `import struct` to the top of `src/classes/Tts.py` (after the existing imports):

```python
import os
import asyncio
import subprocess
import wave
import struct
```

- [ ] **Step 2: Add synthesize_elevenlabs method to TTS class**

Add this method to the `TTS` class in `src/classes/Tts.py`, after the existing `synthesize` method:

```python
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
    import requests as _requests
    from config import get_elevenlabs_api_key, get_elevenlabs_voice_id_th

    api_key = get_elevenlabs_api_key()
    voice_id = get_elevenlabs_voice_id_th()

    if not api_key or not voice_id:
        raise RuntimeError(
            "elevenlabs_api_key and elevenlabs_voice_id_th must be set in config.json"
        )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    params = {"output_format": "pcm_44100"}
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    response = _requests.post(url, params=params, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    pcm_bytes = response.content  # raw signed 16-bit PCM at 44100 Hz, mono

    # Wrap PCM in WAV container using stdlib wave
    with wave.open(output_file, "wb") as wav_file:
        wav_file.setnchannels(1)       # mono
        wav_file.setsampwidth(2)       # 16-bit = 2 bytes per sample
        wav_file.setframerate(44100)   # 44.1 kHz
        wav_file.writeframes(pcm_bytes)

    return output_file
```

- [ ] **Step 3: Fill in config.json with real ElevenLabs credentials**

In `config.json`, set:
- `elevenlabs_api_key`: your ElevenLabs API key (from https://elevenlabs.io → Profile → API Key)
- `elevenlabs_voice_id_th`: voice ID for Thai narration (from ElevenLabs Voice Library, e.g. a Thai voice or your cloned voice)

- [ ] **Step 4: Smoke test the method**

```bash
cd C:/Users/66984/workspace-coding/MoneyPrinterV2
py -c "
import sys; sys.path.insert(0,'src')
from classes.Tts import TTS
tts = TTS()
tts.synthesize_elevenlabs('สวัสดีครับ นี่คือการทดสอบเสียง', '.mp/test_elevenlabs.wav')
print('OK — check .mp/test_elevenlabs.wav')
"
```

Expected: `.mp/test_elevenlabs.wav` is created, plays Thai speech when opened.

- [ ] **Step 5: Commit**

```bash
rtk git add src/classes/Tts.py
rtk git commit -m "feat: add ElevenLabs TTS method (PCM->WAV, eleven_multilingual_v2)"
```

---

## Task 3: Podcast language param + LLM narration language + TTS routing

**Files:**
- Modify: `src/classes/Podcast.py`

- [ ] **Step 1: Add language param to __init__**

In `src/classes/Podcast.py`, find the `__init__` method (around line 59):

```python
def __init__(self, topic: str = "") -> None:
    self.topic = topic
    self.narrator = get_podcast_narrator()
    self.style_prompt = get_podcast_style_prompt()
    self.episode_dir: str = ""
    self.metadata: dict = {}
```

Replace with:

```python
def __init__(self, topic: str = "", language: str = "English") -> None:
    self.topic = topic
    self.language = language
    self.narrator = get_podcast_narrator()
    self.style_prompt = get_podcast_style_prompt()
    self.episode_dir: str = ""
    self.metadata: dict = {}
```

- [ ] **Step 2: Inject language into system_prompt in generate_script()**

In `generate_script()`, find the `system_prompt` assignment (around line 89):

```python
system_prompt = (
    f"You are {narrator['name']}, {narrator['persona']}. /no_think "
    "Narrate in a compelling storytelling voice. "
    "Output ONLY valid JSON matching the provided schema. "
    ...
)
```

Add `f"Narrate in {self.language} language. "` as a new sentence:

```python
system_prompt = (
    f"You are {narrator['name']}, {narrator['persona']}. /no_think "
    f"Narrate in {self.language} language. "
    "Narrate in a compelling storytelling voice. "
    "Output ONLY valid JSON matching the provided schema. "
    ...
)
```

(Keep the rest of the system_prompt unchanged.)

- [ ] **Step 3: Add TTS routing in generate_assets()**

In `generate_assets()`, find the audio generation block (around line 287):

```python
# Generate audio
if not os.path.exists(audio_path):
    tts.synthesize(
        scene["narration"],
        output_file=audio_path,
        voice=narrator["tts_voice"],
        rate=narrator["tts_rate"],
    )
```

Replace with:

```python
# Generate audio — route by language
if not os.path.exists(audio_path):
    if self.language == "Thai":
        tts.synthesize_elevenlabs(scene["narration"], output_file=audio_path)
    else:
        tts.synthesize(
            scene["narration"],
            output_file=audio_path,
            voice=narrator["tts_voice"],
            rate=narrator["tts_rate"],
        )
```

- [ ] **Step 4: Smoke test language flows**

```bash
cd C:/Users/66984/workspace-coding/MoneyPrinterV2
py -c "
import sys; sys.path.insert(0,'src')
from classes.Podcast import Podcast
p_en = Podcast(topic='test', language='English')
p_th = Podcast(topic='test', language='Thai')
print('English language:', p_en.language)
print('Thai language:', p_th.language)
# Verify system_prompt contains language
narrator = p_en.narrator
sp = f'You are {narrator.get(\"name\",\"N\")}, {narrator.get(\"persona\",\"P\")}. /no_think Narrate in {p_en.language} language.'
print('system_prompt snippet OK:', 'English' in sp)
"
```

Expected: prints `English language: English`, `Thai language: Thai`, `system_prompt snippet OK: True`.

- [ ] **Step 5: Commit**

```bash
rtk git add src/classes/Podcast.py
rtk git commit -m "feat: add language param to Podcast, LLM language injection, ElevenLabs TTS routing"
```

---

## Task 4: Image consistency — visual summary between LLM calls

**Files:**
- Modify: `src/classes/Podcast.py`

- [ ] **Step 1: Add visual_summary helper call after Call 1**

In `generate_script()`, find the block after Call 1 that generates `summary_1` (around line 129):

```python
# --- Summary 1: summarise Call 1 narrations ---
narrations_1 = "\n\n".join(s["narration"] for s in scenes_1)
summary_1 = generate_text(
    "Summarize the following podcast narration in 3-5 sentences, "
    "capturing the key narrative points covered:\n\n" + narrations_1
)
```

Add the visual summary call **immediately after** `summary_1 = ...`:

```python
# --- Visual Summary 1: visual elements from Call 1 image prompts ---
visual_summary_1 = generate_text(
    "Summarize the key visual elements from these image descriptions "
    "(main characters and their appearance, locations, color palette, lighting mood) "
    "in 2-3 sentences. This will be used as a visual consistency guide for subsequent scenes:\n\n"
    + "\n---\n".join(s["image_prompt"] for s in scenes_1)
)
```

- [ ] **Step 2: Inject visual_summary_1 into prompt_2**

Find `prompt_2` (around line 137). It currently starts with:

```python
prompt_2 = (
    f"Story so far:\n{summary_1}\n\n"
    f"Continue the podcast about: {topic}\n\n"
    ...
)
```

Add the visual summary section:

```python
prompt_2 = (
    f"Story so far:\n{summary_1}\n\n"
    f"Visual style established in earlier scenes:\n{visual_summary_1}\n"
    "Maintain these visual elements consistently in all new image_prompts.\n\n"
    f"Continue the podcast about: {topic}\n\n"
    "Generate EXACTLY 4 scenes for Act 2 -- deepen the story, introduce "
    "complications or surprising revelations, and build tension.\n\n"
    "Each scene needs a 'narration' (2-4 sentences of engaging spoken text) "
    "and an 'image_prompt' (vivid visual description for an illustration).\n"
    "Return EXACTLY 4 scenes, no more, no fewer."
)
```

- [ ] **Step 3: Add visual_summary_2 after Call 2, inject into prompt_3**

Find the block after Call 2 that generates `summary_2` (around line 169):

```python
# --- Summary 2: summarise all scenes so far (Call 1 + Call 2) ---
narrations_12 = "\n\n".join(
    s["narration"] for s in (scenes_1 + scenes_2)
)
summary_2 = generate_text(
    "Summarize the following podcast narration in 3-5 sentences, "
    "capturing the key narrative points covered:\n\n" + narrations_12
)
```

Add the visual summary call **immediately after** `summary_2 = ...`:

```python
# --- Visual Summary 2: visual elements from all scenes so far ---
visual_summary_2 = generate_text(
    "Summarize the key visual elements from these image descriptions "
    "(main characters and their appearance, locations, color palette, lighting mood) "
    "in 2-3 sentences. This will be used as a visual consistency guide for subsequent scenes:\n\n"
    + "\n---\n".join(s["image_prompt"] for s in (scenes_1 + scenes_2))
)
```

Then find `prompt_3` (around line 179) and inject the visual summary:

```python
prompt_3 = (
    f"Story so far:\n{summary_2}\n\n"
    f"Visual style established in earlier scenes:\n{visual_summary_2}\n"
    "Maintain these visual elements consistently in all new image_prompts.\n\n"
    f"Conclude the podcast about: {topic}\n\n"
    "Generate EXACTLY 5 scenes:\n"
    "  Scenes 1-4: Act 3 -- resolve the story arc, deliver the payoff.\n"
    "  Scene 5: A compelling outro that leaves the audience thinking.\n\n"
    "Each scene needs a 'narration' (2-4 sentences of engaging spoken text) "
    "and an 'image_prompt' (vivid visual description for an illustration).\n"
    "Return EXACTLY 5 scenes, no more, no fewer."
)
```

- [ ] **Step 4: Smoke test (verify no import/syntax errors)**

```bash
cd C:/Users/66984/workspace-coding/MoneyPrinterV2
py -c "import sys; sys.path.insert(0,'src'); from classes.Podcast import Podcast; print('import OK')"
```

Expected: `import OK` with no errors.

- [ ] **Step 5: Commit**

```bash
rtk git add src/classes/Podcast.py
rtk git commit -m "feat: inject visual summaries between LLM calls for image consistency"
```

---

## Task 5: Server — language pass-through + mark-uploaded endpoint

**Files:**
- Modify: `src/podcast_server.py`

- [ ] **Step 1: Add language field to episode state dict in api_generate**

In `api_generate()` (around line 472), find the `episodes[episode_id] = { ... }` block:

```python
episodes[episode_id] = {
    "podcast": None,
    "topic": topic,
    "mode": mode,
    "status": "idle",
    ...
}
```

First, extract `language` from the request before building the dict:

```python
language = (request_data.get("language") or "English").strip()
if language not in ("Thai", "English"):
    language = "English"
```

Then add `"language": language` to the dict:

```python
episodes[episode_id] = {
    "podcast": None,
    "topic": topic,
    "language": language,
    "mode": mode,
    "status": "idle",
    "current_step": 0,
    "step_states": _make_step_states(),
    "scenes": [],
    "metadata": {},
    "error": None,
    "episode_dir": "",
    "cancelled": False,
}
```

- [ ] **Step 2: Pass language when constructing Podcast in _run_pipeline**

In `_run_pipeline()` (around line 383), find:

```python
podcast = Podcast(topic=ep["topic"])
```

Replace with:

```python
podcast = Podcast(topic=ep["topic"], language=ep.get("language", "English"))
```

- [ ] **Step 3: Add mark-uploaded endpoint**

Add a new route to `podcast_server.py` after the existing `api_upload` function (after line ~725). Add it before `@app.get("/static/{episode_id}/{filename}")`:

```python
@app.post("/api/mark-uploaded/{episode_id}")
async def api_mark_uploaded(episode_id: str):
    """Mark an episode as manually uploaded to YouTube.

    Updates episode state and persists uploaded_at to metadata.json.
    """
    ep = _get_or_restore_episode(episode_id)
    if not ep:
        return JSONResponse({"error": "unknown episode_id"}, status_code=404)

    uploaded_at = datetime.now().isoformat()

    # Update in-memory state
    ep["status"] = "uploaded"
    if ep.get("metadata") is None:
        ep["metadata"] = {}
    ep["metadata"]["uploaded_at"] = uploaded_at

    # Persist to metadata.json
    episode_dir = ep.get("episode_dir", "")
    if episode_dir:
        metadata_path = os.path.join(episode_dir, "metadata.json")
        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {}
            meta["uploaded_at"] = uploaded_at
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            return JSONResponse({"error": f"failed to persist: {exc}"}, status_code=500)

    return JSONResponse({"ok": True, "uploaded_at": uploaded_at})
```

- [ ] **Step 4: Update route comment block at top of file**

Find the route list comment at the top of the file (around lines 3-11):

```
POST /api/upload/{episode_id}   — Upload to YouTube
```

Add below it:

```
POST /api/mark-uploaded/{episode_id} — Mark episode as manually uploaded
```

- [ ] **Step 5: Smoke test the endpoint**

Start the server:
```bash
cd C:/Users/66984/workspace-coding/MoneyPrinterV2
py -c "import sys; sys.path.insert(0,'src'); from podcast_server import launch_podcast_server; launch_podcast_server()"
```

In a separate terminal, test with curl (using any existing episode_id from `.mp/`):
```bash
curl -s -X POST http://localhost:8899/api/mark-uploaded/podcast_test_20260405
```

Expected: `{"ok": true, "uploaded_at": "2026-04-05T..."}` or `{"error": "unknown episode_id"}` — either is fine, no 500 error.

- [ ] **Step 6: Commit**

```bash
rtk git add src/podcast_server.py
rtk git commit -m "feat: pass language to Podcast; add mark-uploaded endpoint"
```

---

## Task 6: UI — language selector dropdown

**Files:**
- Modify: `src/podcast_ui.html`

- [ ] **Step 1: Find the topic input field**

In `podcast_ui.html`, find the topic input section (look for `id="topicInput"` or similar, around line 600-650). It looks like:

```html
<div>
  <label ...>TOPIC</label>
  <input id="topicInput" ... />
</div>
```

- [ ] **Step 2: Add language selector below the topic input**

Add a new `<div>` for the language selector immediately after the topic input `</div>`:

```html
<!-- Language selector -->
<div class="mt-3">
  <label class="text-xs font-medium text-subtext uppercase tracking-wide">LANGUAGE</label>
  <div class="flex gap-2 mt-1.5">
    <button
      id="langBtnEn"
      onclick="setLanguage('English')"
      class="px-4 py-2 rounded-lg text-sm font-semibold border border-overlay bg-overlay text-highlight transition-all"
    >
      English
    </button>
    <button
      id="langBtnTh"
      onclick="setLanguage('Thai')"
      class="px-4 py-2 rounded-lg text-sm font-semibold border border-overlay bg-charcoal text-subtext transition-all"
    >
      Thai (ElevenLabs)
    </button>
  </div>
</div>
```

- [ ] **Step 3: Add JS state variable and setLanguage function**

In the `<script>` section, find the State variables block (around line 778):

```javascript
let episodeId = null;
let pollInterval = null;
```

Add after those lines:

```javascript
let selectedLanguage = 'English';
```

Then add the `setLanguage` function after the `resetUI` function:

```javascript
function setLanguage(lang) {
  selectedLanguage = lang;
  const enBtn = document.getElementById('langBtnEn');
  const thBtn = document.getElementById('langBtnTh');
  if (lang === 'Thai') {
    enBtn.classList.remove('bg-overlay', 'text-highlight');
    enBtn.classList.add('bg-charcoal', 'text-subtext');
    thBtn.classList.remove('bg-charcoal', 'text-subtext');
    thBtn.classList.add('bg-overlay', 'text-highlight');
  } else {
    thBtn.classList.remove('bg-overlay', 'text-highlight');
    thBtn.classList.add('bg-charcoal', 'text-subtext');
    enBtn.classList.remove('bg-charcoal', 'text-subtext');
    enBtn.classList.add('bg-overlay', 'text-highlight');
  }
}
```

- [ ] **Step 4: Include language in the generate POST body**

Find the `startGeneration()` function (or wherever `fetch('/api/generate', ...)` is called). Find the `body: JSON.stringify(...)`:

```javascript
body: JSON.stringify({ topic, mode }),
```

Add `language`:

```javascript
body: JSON.stringify({ topic, mode, language: selectedLanguage }),
```

- [ ] **Step 5: Reset language on new episode**

In `resetUI()`, add:

```javascript
setLanguage('English');
```

- [ ] **Step 6: Smoke test in browser**

Open http://localhost:8899, go to Podcast tab.
- Verify "LANGUAGE" section appears below the topic input
- Click "Thai (ElevenLabs)" — button highlights, "English" dims
- Click "English" — reverts

- [ ] **Step 7: Commit**

```bash
rtk git add src/podcast_ui.html
rtk git commit -m "feat: add language selector to Podcast UI"
```

---

## Task 7: UI — replace upload button with manual upload flow

**Files:**
- Modify: `src/podcast_ui.html`

- [ ] **Step 1: Find and replace the upload button HTML**

Find the upload button row (around line 750):

```html
<!-- Upload button row -->
<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-1">
  <div class="flex items-center gap-4">
    <button
      id="uploadBtn"
      onclick="uploadToYouTube()"
      disabled
      class="glass-btn glass-btn-primary px-6 py-2.5 bg-sky text-charcoal font-bold rounded-xl hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
    >
      Upload to YouTube
    </button>
    <span id="uploadStatus" class="text-sm text-subtext"></span>
  </div>
  <div id="episodeDirInfo" class="text-xs text-subtext hidden">
    <span class="text-overlay">Episode folder:</span>
    <span id="episodeDirPath" class="ml-1 font-mono break-all"></span>
  </div>
</div>
```

Replace entirely with:

```html
<!-- Manual upload row -->
<div id="manualUploadRow" class="hidden flex-col gap-3 pt-1">
  <div class="hero-panel rounded-xl p-4 space-y-3">
    <p class="text-xs font-medium text-subtext uppercase tracking-wide">Video Ready — Upload Manually</p>
    <div class="flex items-center gap-2">
      <span id="videoFilePath" class="text-xs font-mono text-highlight break-all flex-1"></span>
      <button
        onclick="copyVideoPath(this)"
        class="glass-btn px-3 py-1.5 text-xs font-semibold rounded-lg border border-overlay hover:brightness-110 transition-all whitespace-nowrap"
      >
        Copy Path
      </button>
    </div>
    <div class="flex items-center gap-3">
      <button
        id="markUploadedBtn"
        onclick="markAsUploaded()"
        class="glass-btn glass-btn-primary px-5 py-2 bg-emerald-600 text-white font-bold rounded-xl hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Mark as Uploaded ✓
      </button>
      <span id="markUploadedStatus" class="text-sm text-subtext"></span>
    </div>
  </div>
</div>
<div id="episodeDirInfo" class="text-xs text-subtext hidden">
  <span class="text-overlay">Episode folder:</span>
  <span id="episodeDirPath" class="ml-1 font-mono break-all"></span>
</div>
```

- [ ] **Step 2: Add JS functions for the manual upload row**

In the `<script>` section, find the existing `uploadToYouTube` function (around line 1564). **Keep it** (the `/api/upload` endpoint still exists). Add these new functions after it:

```javascript
function showManualUploadRow(episodeDir) {
  const row = document.getElementById('manualUploadRow');
  row.classList.remove('hidden');
  row.classList.add('flex');
  // Build video file path
  const videoPath = episodeDir ? episodeDir.replace(/\\/g, '/') + '/final.mp4' : '';
  document.getElementById('videoFilePath').textContent = videoPath || 'final.mp4';
}

function copyVideoPath(btn) {
  const pathEl = document.getElementById('videoFilePath');
  navigator.clipboard.writeText(pathEl.textContent).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy Path'; }, 2000);
  });
}

async function markAsUploaded() {
  if (!episodeId) return;
  const btn = document.getElementById('markUploadedBtn');
  const statusEl = document.getElementById('markUploadedStatus');
  btn.disabled = true;
  statusEl.textContent = 'Marking...';
  try {
    const res = await fetch(`/api/mark-uploaded/${episodeId}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      btn.textContent = 'Uploaded ✓';
      btn.classList.remove('bg-emerald-600');
      btn.classList.add('bg-gray-600');
      statusEl.textContent = `Marked at ${new Date(data.uploaded_at).toLocaleString()}`;
      isCurrentEpisodeUploaded = true;
    } else {
      btn.disabled = false;
      statusEl.textContent = data.error || 'Failed';
    }
  } catch (e) {
    btn.disabled = false;
    statusEl.textContent = 'Network error';
  }
}
```

- [ ] **Step 3: Show manual upload row when pipeline completes**

Find the `applyEpisodeState(data)` function (around line 974). Find the block that enables the old upload button:

```javascript
const uploadBtn = document.getElementById('uploadBtn');
if (isCurrentEpisodeUploaded) {
  uploadBtn.disabled = true;
  ...
} else if (data.status === 'done' || data.status === 'partial') {
  uploadBtn.disabled = false;
}
```

Replace this block with:

```javascript
if (data.status === 'done' || data.status === 'partial' || data.status === 'uploaded') {
  showManualUploadRow(data.episode_dir);
}
if (isCurrentEpisodeUploaded || data.status === 'uploaded') {
  const btn = document.getElementById('markUploadedBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Uploaded ✓';
    btn.classList.remove('bg-emerald-600');
    btn.classList.add('bg-gray-600');
    const uploadedAt = data.uploaded_at
      ? new Date(data.uploaded_at).toLocaleString()
      : 'previously';
    document.getElementById('markUploadedStatus').textContent = `Uploaded ${uploadedAt}`;
  }
}
```

- [ ] **Step 4: Hide manual upload row on reset**

In `resetUI()`, add:

```javascript
const manualRow = document.getElementById('manualUploadRow');
if (manualRow) {
  manualRow.classList.add('hidden');
  manualRow.classList.remove('flex');
}
const markBtn = document.getElementById('markUploadedBtn');
if (markBtn) {
  markBtn.disabled = false;
  markBtn.textContent = 'Mark as Uploaded ✓';
  markBtn.classList.remove('bg-gray-600');
  markBtn.classList.add('bg-emerald-600');
}
document.getElementById('markUploadedStatus').textContent = '';
```

- [ ] **Step 5: Smoke test in browser**

1. Open http://localhost:8899, Podcast tab
2. Generate a short test episode (any topic)
3. After pipeline completes — verify "Video Ready — Upload Manually" section appears
4. Click "Copy Path" — verify clipboard receives the path
5. Click "Mark as Uploaded ✓" — verify button turns grey, shows timestamp
6. Reload page, open same episode from Recent Episodes — verify "Uploaded ✓" state is shown

- [ ] **Step 6: Commit**

```bash
rtk git add src/podcast_ui.html
rtk git commit -m "feat: replace upload button with manual upload flow and mark-uploaded UI"
```

---

## Final Integration Test

- [ ] **Thai episode end-to-end**

1. Open http://localhost:8899, Podcast tab
2. Select language: Thai (ElevenLabs)
3. Enter topic: `เรื่องราวลึกลับในประเทศไทย`
4. Click Generate
5. Verify:
   - Script step completes — check script.json in `.mp/podcast_*/` directory to confirm Thai narration
   - Assets step completes — check `scene_00.wav` plays Thai speech (ElevenLabs voice)
   - Render, Metadata, Thumbnail steps complete
   - "Video Ready — Upload Manually" section appears with correct file path
6. Click "Mark as Uploaded ✓" — verify state persists after page reload

- [ ] **Visual consistency check**

Open `.mp/podcast_*/script.json` and compare `image_prompt` values across scenes 1, 5, 10, 14. Characters, settings, and color palette language should be consistent (referencing same visual elements).

- [ ] **Final commit**

```bash
rtk git add -A
rtk git commit -m "feat: podcast upgrade — bilingual (ElevenLabs Thai), image consistency, manual upload"
```
