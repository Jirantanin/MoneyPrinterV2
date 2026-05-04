# Kurzgesagt Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply Kurzgesagt – In a Nutshell visual and narrative style as the permanent default across the podcast pipeline (scene images, narration, narrator persona, thumbnail).

**Architecture:** Update 4 prompting strings in two places: `_default_podcast_settings()` in `src/config.py` (new installs / resets) and `podcast_settings.prompting` in `config.json` (running instance). Mirror the same values to `config.example.json`. No new fields, no UI changes, no logic changes.

**Tech Stack:** Python 3.12, `config.py` settings system, `config.json` / `config.example.json`

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `src/config.py` | Modify lines 88, 91–96, 97–103, 118–125 | 4 strings inside `_default_podcast_settings()` |
| `config.json` | Modify `podcast_settings.prompting` | Same 4 keys written in-place |
| `config.example.json` | Modify `podcast_settings.prompting` | Same 4 keys written in-place |

---

## Reference: Exact New Prompt Values

These strings are used verbatim in every task. Do not paraphrase them.

**STYLE_PROMPT:**
```
flat design illustration, Kurzgesagt style, vivid saturated colors, bright solid-color background, cute simple bird and creature characters, bold geometric shapes, clean vector art, no photorealism, no dark cinematic mood, no comic panels --
```

**NARRATOR_PERSONA:**
```
A curious narrator who questions assumptions, builds from simple facts to mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering about your place in the universe
```

**SCRIPT_SYSTEM_PROMPT:**
```
You are {narrator_name}, {narrator_persona}. /no_think Narrate in {language} language. Write in the style of Kurzgesagt – In a Nutshell: open with a big thought-provoking question, use "we" to include the listener in the journey, build from simple everyday concepts to mind-blowing scale, mix short punchy sentences with longer explanatory ones, use vivid surprising analogies, and close with a philosophical reflection that leaves the listener in quiet wonder. Output ONLY valid JSON matching the provided schema. No markdown, no asterisks, no extra commentary.
```

**THUMBNAIL_PROMPT:**
```
YouTube thumbnail for a podcast episode about: {topic}. {creative_direction_block}Kurzgesagt flat design style. Vivid saturated colors, bright bold background. Simple geometric shapes and cute bird or creature characters. One clear striking central image that fills the frame. Clean vector illustration, no photorealism, no dark cinematic mood. No text, no logos.
```

---

## Task 1: Update `src/config.py` defaults

**Files:**
- Modify: `src/config.py` lines 88, 91–125

- [ ] **Step 1: Replace `narrator_persona` default**

In `src/config.py`, inside `_default_podcast_settings()` → `"prompting"` dict, change:

```python
# BEFORE
"narrator_persona": "A curious and engaging narrator who explains complex topics clearly",
```
```python
# AFTER
"narrator_persona": "A curious narrator who questions assumptions, builds from simple facts to mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering about your place in the universe",
```

- [ ] **Step 2: Replace `podcast_style_prompt` default**

In the same `"prompting"` dict, change:

```python
# BEFORE
"podcast_style_prompt": (
    "cinematic documentary illustration, single coherent scene, no comic panels, "
    "no superhero styling, no exaggerated heroic poses, no named characters unless "
    "explicitly requested, restrained realistic composition, moody lighting, subtle "
    "texture, thoughtful atmosphere --"
),
```
```python
# AFTER
"podcast_style_prompt": (
    "flat design illustration, Kurzgesagt style, vivid saturated colors, "
    "bright solid-color background, cute simple bird and creature characters, "
    "bold geometric shapes, clean vector art, no photorealism, "
    "no dark cinematic mood, no comic panels --"
),
```

- [ ] **Step 3: Replace `script_system_prompt` default**

```python
# BEFORE
"script_system_prompt": (
    "You are {narrator_name}, {narrator_persona}. /no_think "
    "Narrate in {language} language. "
    "Narrate in a compelling storytelling voice. "
    "Output ONLY valid JSON matching the provided schema. "
    "No markdown, no asterisks, no extra commentary."
),
```
```python
# AFTER
"script_system_prompt": (
    "You are {narrator_name}, {narrator_persona}. /no_think "
    "Narrate in {language} language. "
    "Write in the style of Kurzgesagt \u2013 In a Nutshell: open with a big thought-provoking question, "
    "use \"we\" to include the listener in the journey, "
    "build from simple everyday concepts to mind-blowing scale, "
    "mix short punchy sentences with longer explanatory ones, "
    "use vivid surprising analogies, and close with a philosophical reflection "
    "that leaves the listener in quiet wonder. "
    "Output ONLY valid JSON matching the provided schema. "
    "No markdown, no asterisks, no extra commentary."
),
```

- [ ] **Step 4: Replace `thumbnail_system_prompt` default**

```python
# BEFORE
"thumbnail_system_prompt": (
    "YouTube thumbnail for a podcast episode about: {topic}. "
    "{creative_direction_block}"
    "Single dramatic scene, no comic panels, no borders, no gutters. "
    "Dark cinematic mood, bold colors, high contrast. "
    "One striking central subject that fills the frame. "
    "Photorealistic or painterly illustration style. No text, no logos."
),
```
```python
# AFTER
"thumbnail_system_prompt": (
    "YouTube thumbnail for a podcast episode about: {topic}. "
    "{creative_direction_block}"
    "Kurzgesagt flat design style. Vivid saturated colors, bright bold background. "
    "Simple geometric shapes and cute bird or creature characters. "
    "One clear striking central image that fills the frame. "
    "Clean vector illustration, no photorealism, no dark cinematic mood. "
    "No text, no logos."
),
```

- [ ] **Step 5: Verify `config.py` reads back correctly**

```bash
cd <repo-root>
py -c "
import sys; sys.path.insert(0,'src')
from config import get_podcast_settings
s = get_podcast_settings()['prompting']
assert 'Kurzgesagt' in s['podcast_style_prompt'], 'style_prompt wrong'
assert 'cosmic scale' in s['narrator_persona'], 'persona wrong'
assert 'Kurzgesagt' in s['script_system_prompt'], 'script_prompt wrong'
assert 'Kurzgesagt flat design' in s['thumbnail_system_prompt'], 'thumbnail_prompt wrong'
print('config.py defaults OK')
"
```

Expected output: `config.py defaults OK`

- [ ] **Step 6: Commit**

```bash
git add src/config.py
git commit -m "feat: apply Kurzgesagt style to podcast defaults in config.py"
```

---

## Task 2: Update `config.json` (live instance)

**Files:**
- Modify: `config.json` → `podcast_settings.prompting`

- [ ] **Step 1: Write updated prompting values into `config.json`**

Run this script from the repo root (reads the file, patches the 4 keys, writes back with 2-space indent):

```bash
py -c "
import json, os
path = 'config.json'
with open(path, 'r', encoding='utf-8') as f:
    c = json.load(f)
c.setdefault('podcast_settings', {}).setdefault('prompting', {})
p = c['podcast_settings']['prompting']
p['narrator_persona'] = (
    'A curious narrator who questions assumptions, builds from simple facts to '
    'mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering '
    'about your place in the universe'
)
p['podcast_style_prompt'] = (
    'flat design illustration, Kurzgesagt style, vivid saturated colors, '
    'bright solid-color background, cute simple bird and creature characters, '
    'bold geometric shapes, clean vector art, no photorealism, '
    'no dark cinematic mood, no comic panels --'
)
p['script_system_prompt'] = (
    'You are {narrator_name}, {narrator_persona}. /no_think '
    'Narrate in {language} language. '
    'Write in the style of Kurzgesagt \u2013 In a Nutshell: open with a big thought-provoking question, '
    'use \"we\" to include the listener in the journey, '
    'build from simple everyday concepts to mind-blowing scale, '
    'mix short punchy sentences with longer explanatory ones, '
    'use vivid surprising analogies, and close with a philosophical reflection '
    'that leaves the listener in quiet wonder. '
    'Output ONLY valid JSON matching the provided schema. '
    'No markdown, no asterisks, no extra commentary.'
)
p['thumbnail_system_prompt'] = (
    'YouTube thumbnail for a podcast episode about: {topic}. '
    '{creative_direction_block}'
    'Kurzgesagt flat design style. Vivid saturated colors, bright bold background. '
    'Simple geometric shapes and cute bird or creature characters. '
    'One clear striking central image that fills the frame. '
    'Clean vector illustration, no photorealism, no dark cinematic mood. '
    'No text, no logos.'
)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('config.json updated')
"
```

Expected output: `config.json updated`

- [ ] **Step 2: Verify `config.json` values**

```bash
py -c "
import json
c = json.load(open('config.json'))
p = c['podcast_settings']['prompting']
assert 'Kurzgesagt' in p['podcast_style_prompt']
assert 'cosmic scale' in p['narrator_persona']
assert 'Kurzgesagt' in p['script_system_prompt']
assert 'Kurzgesagt flat design' in p['thumbnail_system_prompt']
print('config.json OK')
"
```

Expected output: `config.json OK`

- [ ] **Step 3: Commit**

```bash
git add config.json
git commit -m "feat: apply Kurzgesagt style prompts to config.json (live instance)"
```

---

## Task 3: Update `config.example.json`

**Files:**
- Modify: `config.example.json` → `podcast_settings.prompting`

- [ ] **Step 1: Write updated prompting values into `config.example.json`**

Same script as Task 2 Step 1 but targeting `config.example.json`:

```bash
py -c "
import json
path = 'config.example.json'
with open(path, 'r', encoding='utf-8') as f:
    c = json.load(f)
c.setdefault('podcast_settings', {}).setdefault('prompting', {})
p = c['podcast_settings']['prompting']
p['narrator_persona'] = (
    'A curious narrator who questions assumptions, builds from simple facts to '
    'mind-blowing cosmic scale, uses vivid analogies, and leaves you wondering '
    'about your place in the universe'
)
p['podcast_style_prompt'] = (
    'flat design illustration, Kurzgesagt style, vivid saturated colors, '
    'bright solid-color background, cute simple bird and creature characters, '
    'bold geometric shapes, clean vector art, no photorealism, '
    'no dark cinematic mood, no comic panels --'
)
p['script_system_prompt'] = (
    'You are {narrator_name}, {narrator_persona}. /no_think '
    'Narrate in {language} language. '
    'Write in the style of Kurzgesagt \u2013 In a Nutshell: open with a big thought-provoking question, '
    'use \"we\" to include the listener in the journey, '
    'build from simple everyday concepts to mind-blowing scale, '
    'mix short punchy sentences with longer explanatory ones, '
    'use vivid surprising analogies, and close with a philosophical reflection '
    'that leaves the listener in quiet wonder. '
    'Output ONLY valid JSON matching the provided schema. '
    'No markdown, no asterisks, no extra commentary.'
)
p['thumbnail_system_prompt'] = (
    'YouTube thumbnail for a podcast episode about: {topic}. '
    '{creative_direction_block}'
    'Kurzgesagt flat design style. Vivid saturated colors, bright bold background. '
    'Simple geometric shapes and cute bird or creature characters. '
    'One clear striking central image that fills the frame. '
    'Clean vector illustration, no photorealism, no dark cinematic mood. '
    'No text, no logos.'
)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('config.example.json updated')
"
```

Expected output: `config.example.json updated`

- [ ] **Step 2: Verify**

```bash
py -c "
import json
c = json.load(open('config.example.json'))
p = c['podcast_settings']['prompting']
assert 'Kurzgesagt' in p['podcast_style_prompt']
assert 'cosmic scale' in p['narrator_persona']
print('config.example.json OK')
"
```

Expected output: `config.example.json OK`

- [ ] **Step 3: Commit**

```bash
git add config.example.json
git commit -m "feat: apply Kurzgesagt style prompts to config.example.json"
```

---

## Manual Smoke Test

After all 3 tasks committed, confirm end-to-end by checking what the running server will serve:

```bash
py -c "
import sys; sys.path.insert(0,'src')
from config import get_podcast_settings, get_podcast_style_prompt, get_podcast_narrator
s = get_podcast_settings()
print('style_prompt :', s['prompting']['podcast_style_prompt'][:60])
print('persona      :', get_podcast_narrator()['persona'][:60])
print('script_prompt:', s['prompting']['script_system_prompt'][:60])
print('thumb_prompt :', s['prompting']['thumbnail_system_prompt'][:60])
"
```

All four lines should contain `Kurzgesagt` or `cosmic scale`.
