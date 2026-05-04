# Design: Kurzgesagt Style for Podcast Pipeline

**Date:** 2026-04-10
**Status:** Approved

## Summary

Apply the Kurzgesagt – In a Nutshell visual and narrative style as the permanent default across the entire podcast pipeline: scene images, script narration, narrator persona, and thumbnail.

## Scope

Change 4 prompt fields in `_default_podcast_settings()` (`src/config.py`) and mirror those changes into the active `config.json` and `config.example.json`.

No new fields, no UI changes, no preset system — style is hardcoded as the new default.

## Approach

**A (chosen):** Update `_default_podcast_settings()` in `config.py` + write new values directly into `config.json` `podcast_settings.prompting` section. Both files change together so the style takes effect immediately on the running instance and for future installs.

## Changes

### 1. `podcast_style_prompt` — Scene image prefix

Prepended to every `image_prompt` before image generation.

**Before:**
```
cinematic documentary illustration, single coherent scene, no comic panels,
no superhero styling, no exaggerated heroic poses, no named characters unless
explicitly requested, restrained realistic composition, moody lighting, subtle
texture, thoughtful atmosphere --
```

**After:**
```
flat design illustration, Kurzgesagt style, vivid saturated colors,
bright solid-color background, cute simple bird and creature characters,
bold geometric shapes, clean vector art, no photorealism,
no dark cinematic mood, no comic panels --
```

### 2. `narrator_persona`

**Before:**
```
A curious and engaging narrator who explains complex topics clearly
```

**After:**
```
A curious narrator who questions assumptions, builds from simple facts to
mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering
about your place in the universe
```

### 3. `script_system_prompt`

Only the narration style instruction changes. Schema/JSON constraints stay identical.

**Before (relevant line):**
```
Narrate in a compelling storytelling voice.
```

**After (relevant line):**
```
Write in the style of Kurzgesagt – In a Nutshell: open with a big
thought-provoking question, use "we" to include the listener in the journey,
build from simple everyday concepts to mind-blowing scale, mix short punchy
sentences with longer explanatory ones, use vivid surprising analogies, and
close with a philosophical reflection that leaves the listener in quiet wonder.
```

### 4. `thumbnail_system_prompt`

**Before (relevant excerpt):**
```
Single dramatic scene, no comic panels, no borders, no gutters.
Dark cinematic mood, bold colors, high contrast.
One striking central subject that fills the frame.
Photorealistic or painterly illustration style. No text, no logos.
```

**After:**
```
Kurzgesagt flat design style. Vivid saturated colors, bright bold background.
Simple geometric shapes and cute bird or creature characters.
One clear striking central image that fills the frame.
Clean vector illustration, no photorealism, no dark cinematic mood.
No text, no logos.
```

## Files Modified

| File | Change |
|------|--------|
| `src/config.py` | `_default_podcast_settings()` → `prompting` section |
| `config.json` | `podcast_settings.prompting` → 4 keys updated in-place |
| `config.example.json` | Same 4 keys updated to match new defaults |

## What Does NOT Change

- `metadata_system_prompt` — YouTube title/description/tags format is unaffected
- All voice settings (TTS voices, rates)
- All model settings
- All advanced settings (retry counts, sentence length)
- UI layout and controls
- Pipeline logic (`Podcast.py`, `llm_provider.py`, etc.)

## Error Handling

No new error paths. All changed fields are strings consumed by existing prompt
interpolation (`_safe_format`). If `config.json` does not have a
`podcast_settings` key yet, it will be created.

## Testing

Manual verification after implementation:
1. Run a podcast episode on any topic
2. Confirm scene images come back flat/vivid (not dark/cinematic)
3. Confirm narration reads as Kurzgesagt-style (opens with question, uses "we")
4. Confirm thumbnail is flat/bright (not dark)
