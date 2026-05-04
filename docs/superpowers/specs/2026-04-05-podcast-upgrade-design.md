# Podcast Upgrade — Design Spec
**Date:** 2026-04-05
**Scope:** Podcast pipeline only. Shorts is unchanged.

---

## Goals

1. **Bilingual support** — user selects Thai or English per episode; narration and TTS match
2. **Image consistency** — scene images reference each other visually (same characters, settings, palette) across all 14 scenes
3. **Manual upload flow** — disable auto YouTube upload; user uploads manually; UI has "Mark as Uploaded" button

---

## Out of Scope

- Shorts pipeline (no changes)
- ElevenLabs for English (English stays on edge-tts)
- Multi-language per episode (one language per episode only)

---

## Feature 1: Bilingual + ElevenLabs TTS

### Config additions (`config.json` + `config.py`)

Two new keys:
```json
"elevenlabs_api_key": "...",
"elevenlabs_voice_id_th": "..."
```

Two new getter functions in `config.py`:
- `get_elevenlabs_api_key() -> str`
- `get_elevenlabs_voice_id_th() -> str`

### `Podcast.__init__` — add `language` param

```python
def __init__(self, topic: str = "", language: str = "English") -> None:
    self.language = language
```

`language` is passed through from the server → Podcast instance.

### LLM narration language

`system_prompt` in `generate_script()` gains one sentence:

```
Narrate in {language} language.
```

This covers all 3 LLM calls (same system_prompt is reused).

### TTS routing in `generate_assets()`

```python
if self.language == "Thai":
    tts.synthesize_elevenlabs(narration, audio_path)
else:
    tts.synthesize(narration, audio_path, voice=narrator["tts_voice"], rate=narrator["tts_rate"])
```

### `Tts.synthesize_elevenlabs()` — new method

HTTP POST to ElevenLabs TTS API:
- Endpoint: `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- Auth: `xi-api-key` header
- Body: `{"text": ..., "model_id": "eleven_multilingual_v2"}`
- Response: binary MP3 → write to `output_file` (as-is, rename `.wav` → `.mp3` or convert)

Model `eleven_multilingual_v2` supports Thai natively.

**Audio format:** `render()` in `Podcast.py` hardcodes `scene_XX.wav` paths — output must be WAV. ElevenLabs supports `output_format=pcm_44100` query param which returns raw PCM audio. `synthesize_elevenlabs()` will:
1. Request PCM from ElevenLabs (`?output_format=pcm_44100`)
2. Wrap raw PCM bytes in a WAV header using Python stdlib `wave` module
3. Write to `output_file` (`.wav`) — same path convention as edge-tts

No new dependencies. No FFmpeg conversion step. Files are named `scene_XX.wav` for both languages.

### UI — Language selector in Podcast tab

Add a `<select>` dropdown next to the topic field:
```
Language: [ English ▾ ]  [ Thai ]
```
Sent in the `/api/podcast/generate` POST body as `"language": "Thai"`.

---

## Feature 2: Image Consistency via Visual Summary

### Problem

Currently the 3 LLM calls share only a **narration summary** between them. The `image_prompt` field for each scene is generated fresh with no knowledge of visual elements established in earlier scenes. Result: characters, settings, and color palettes drift across the 14 scenes.

### Solution: inject a visual summary alongside the narration summary

After each LLM call, generate a short visual summary from the image_prompts produced:

```python
visual_summary_1 = generate_text(
    "Summarize the key visual elements from these image descriptions "
    "(main characters and appearance, locations, color palette, lighting mood) "
    "in 2-3 sentences. This will be used as a visual consistency guide for subsequent scenes:\n\n"
    + "\n---\n".join(s["image_prompt"] for s in scenes_1)
)
```

This summary is injected into `prompt_2` and `prompt_3` as a new section:

```
Visual style established in earlier scenes:
{visual_summary_1}

Maintain these visual elements consistently in all new image_prompts.
```

After Call 2, a second visual summary is generated from `scenes_1 + scenes_2` combined and injected into `prompt_3`.

**Cost:** +2 `generate_text` calls per episode (cheap, fast, text-only). No schema, no structured output.

### Style prompt

`style_prompt` from config is still prepended to every image_prompt after all scenes are assembled (unchanged behavior). The visual summary lives in the LLM context, not in the final image_prompt string.

---

## Feature 3: Manual Upload Flow

### Backend — remove auto-upload

In `podcast_server.py`, the final pipeline step currently calls `podcast.upload()`. This call is removed. The pipeline ends after `generate_thumbnail()`.

The `upload()` method on `Podcast` class is kept (not deleted) — it may be used later for re-enabling scheduled upload.

### Backend — new endpoint

```
POST /api/podcast/{episode_id}/mark-uploaded
```

Request body: none required.

Response:
```json
{"ok": true, "uploaded_at": "2026-04-05T14:32:00"}
```

Side effects:
- Updates `episodes[episode_id]["status"] = "uploaded"`
- Sets `episodes[episode_id]["uploaded_at"] = datetime.now().isoformat()`
- Persists to episode `metadata.json` in the episode directory

### UI — post-render state

When pipeline reaches "done" status, replace the upload section with:

```
┌─────────────────────────────────────────────────────┐
│  Video ready — upload manually to YouTube           │
│  📂 .mp/podcast_xxx/final.mp4    [Copy path]        │
│                                                     │
│  [ Mark as Uploaded ✓ ]                             │
└─────────────────────────────────────────────────────┘
```

- **Copy path** — copies absolute file path to clipboard
- **Mark as Uploaded** — calls `POST /api/podcast/{id}/mark-uploaded`, button changes to "Uploaded ✓" (green, disabled)
- If episode already has `uploaded_at` (on page load / refresh), show "Uploaded ✓" immediately

---

## Files Changed

| File | Change |
|---|---|
| `config.json` | Add `elevenlabs_api_key`, `elevenlabs_voice_id_th` |
| `src/config.py` | Add `get_elevenlabs_api_key()`, `get_elevenlabs_voice_id_th()` |
| `src/classes/Tts.py` | Add `synthesize_elevenlabs(text, output_file)` method |
| `src/classes/Podcast.py` | Add `language` param; TTS routing; visual summary between LLM calls |
| `src/podcast_server.py` | Remove `upload()` call; add `mark-uploaded` endpoint; pass `language` to Podcast |
| `src/podcast_ui.html` | Language selector; post-render manual upload UI; Mark as Uploaded button |

---

## Data Flow

```
UI (language=Thai)
  → POST /api/podcast/generate {language: "Thai"}
  → Podcast(topic, language="Thai")
      generate_script()
        system_prompt += "Narrate in Thai language."
        Call 1 → scenes_1 (5 scenes, Thai narration + image_prompt)
        visual_summary_1 = generate_text(scenes_1 image_prompts)
        Call 2 → scenes_2 (4 scenes, uses visual_summary_1)
        visual_summary_2 = generate_text(scenes_1+2 image_prompts)
        Call 3 → scenes_3 (5 scenes, uses visual_summary_2)
        prepend style_prompt to all image_prompts
      generate_assets()
        for each scene:
          generate_image(image_prompt) → scene_XX.png
          tts.synthesize_elevenlabs(narration) → scene_XX.wav  (Thai, PCM via ElevenLabs)
      render() → final.mp4
      generate_metadata()
      generate_thumbnail()
      [NO upload()]
  → status = "done"
  → UI shows "Mark as Uploaded" button
```

---

## Open Questions (resolved)

- **ElevenLabs audio format:** MP3 passed directly to FFmpeg (no conversion needed)
- **English TTS:** unchanged — edge-tts
- **Auto-upload for English:** also disabled (same UI for both languages)
- **Shorts:** no changes at all
