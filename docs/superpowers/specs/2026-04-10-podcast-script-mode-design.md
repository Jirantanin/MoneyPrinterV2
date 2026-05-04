# Podcast Script Mode — Design Spec

**Date:** 2026-04-10  
**Status:** Approved  

## Summary

Add a "Script Mode" input option to the Podcast UI. Instead of entering a topic and letting the LLM generate a script, the user pastes their own pre-written narration text. The system auto-splits it into scenes and generates an image prompt per scene via LLM. All downstream phases (assets, render, upload) are unchanged.

---

## Architecture & Data Flow

```
[User pastes script text + episode title]
         ↓
   UI sends: { script_mode: true, raw_script: "...", title: "..." }
         ↓
  POST /start-podcast
  → stores script_mode + raw_script in episode state
  → Phase 5: generate_script_from_text() instead of generate_script(topic)
         ↓
  generate_script_from_text(text):
    1. Split text into sentences (regex on . ! ?)
    2. Group sentences into scenes by sentence_length config
    3. For each scene → LLM generates image_prompt from narration
    4. Write script.json → return list[{narration, image_prompt}]
         ↓
  Phase 6–8 (generate_assets, render, upload) — unchanged
```

**Scene count:** Flexible. No hardcoded minimum/maximum. One scene per sentence group.

---

## Backend Changes

### `src/classes/Podcast.py`

**`Podcast.__init__()` — add 2 params:**
```python
def __init__(
    self,
    topic: str = "",
    language: str = "English",
    tts_source: str = "edge",
    creative_direction: str = "",
    script_mode: bool = False,   # NEW
    raw_script: str = "",        # NEW
) -> None:
    ...
    self.script_mode = script_mode
    self.raw_script = raw_script
```

**New module-level helper `_generate_image_prompt()`:**
```python
def _generate_image_prompt(narration: str, language: str) -> str:
    raw = generate_text(
        f"Write a vivid visual image prompt for this narration:\n{narration}\n"
        "Return only the image prompt, no explanation.",
        system_prompt="You generate concise visual image prompts for podcast scenes.",
    )
    return raw.strip()
```

**New method `Podcast.generate_script_from_text()`:**
```python
def generate_script_from_text(self, text: str) -> list:
    sentence_length = max(1, get_script_sentence_length())
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    scenes = []
    for i in range(0, len(sentences), sentence_length):
        narration = " ".join(sentences[i:i + sentence_length])
        image_prompt = _generate_image_prompt(narration, self.language)
        scenes.append({"narration": narration, "image_prompt": image_prompt})
    script_path = os.path.join(self.episode_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    return scenes
```

**`_load_script_scenes()` — relax hardcoded 14-scene guard:**
```python
# Remove:
if len(scenes) != 14:
    raise ValueError(f"Expected 14 scenes in script.json, got {len(scenes)}")
# Replace with:
if not scenes:
    raise ValueError("script.json is empty")
```

### `src/podcast_server.py`

**`POST /start-podcast`:**
- Accept `script_mode: bool` and `raw_script: str` from request body.
- Store both in episode state alongside `topic`.
- `title` in script mode: use `title` field from request, fallback to `"Custom Script"`.
- Phase 5 branch:
```python
if ep.get("script_mode"):
    result = _run_step(episode_id, 0, lambda: podcast.generate_script_from_text(ep["raw_script"]))
else:
    result = _run_step(episode_id, 0, lambda: podcast.generate_script(ep["topic"]))
```

---

## Frontend Changes

### `src/ui/podcast_component.html`

Add Input Mode toggle row inside the hero panel, above the existing Topic input row:

```html
<!-- Input mode toggle -->
<div class="flex items-center gap-4 pb-3 border-b border-overlay">
  <span class="text-xs font-medium text-subtext uppercase tracking-wide">Input Mode</span>
  <label class="flex items-center gap-3 cursor-pointer select-none">
    <span id="inputModeTopicLabel" class="text-sm font-medium text-accent">Topic</span>
    <div class="relative">
      <input id="inputModeToggle" type="checkbox" class="sr-only" onchange="onInputModeChange()" />
      <div class="w-12 h-6 bg-overlay rounded-full transition-colors duration-200"></div>
      <div id="inputModeThumb" class="absolute top-1 left-1 w-4 h-4 bg-subtext rounded-full transition-all duration-200"></div>
    </div>
    <span id="inputModeScriptLabel" class="text-sm font-medium text-subtext">Script</span>
  </label>
</div>

<!-- Wrap existing Topic + Creative Direction in: -->
<div id="topicModeFields">
  <!-- ... existing topic input + creative direction textarea ... -->
</div>

<!-- Script mode fields (hidden by default) -->
<div id="scriptModeFields" class="hidden flex flex-col gap-4">
  <div>
    <label class="block text-xs font-medium text-subtext mb-1 uppercase tracking-wide">Episode Title</label>
    <input id="scriptTitleInput" type="text" placeholder="e.g. The Rise and Fall of Nikola Tesla"
      class="w-full bg-charcoal border border-overlay rounded-xl px-4 py-2.5 text-text placeholder-subtext focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors" />
  </div>
  <div>
    <label class="block text-xs font-medium text-subtext mb-1 uppercase tracking-wide">Script</label>
    <textarea id="scriptInput" rows="10"
      placeholder="Paste your full narration script here. The system will split it into scenes automatically."
      class="w-full bg-charcoal border border-overlay rounded-xl px-4 py-3 text-text placeholder-subtext focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors resize-y"></textarea>
  </div>
</div>
```

### `src/ui/podcast-main.js`

**Toggle handler:**
```js
function onInputModeChange() {
  const isScript = document.getElementById('inputModeToggle').checked;
  document.getElementById('topicModeFields').classList.toggle('hidden', isScript);
  document.getElementById('scriptModeFields').classList.toggle('hidden', !isScript);
  // Update label styles
  document.getElementById('inputModeTopicLabel').className =
    `text-sm font-medium ${isScript ? 'text-subtext' : 'text-accent'}`;
  document.getElementById('inputModeScriptLabel').className =
    `text-sm font-medium ${isScript ? 'text-accent' : 'text-subtext'}`;
}
```

**`startGeneration()` — build payload by mode:**
```js
const isScript = document.getElementById('inputModeToggle').checked;
const payload = isScript
  ? {
      script_mode: true,
      raw_script: document.getElementById('scriptInput').value.trim(),
      title: document.getElementById('scriptTitleInput').value.trim() || 'Custom Script',
      language: currentLanguage,
    }
  : {
      topic: document.getElementById('topicInput').value.trim(),
      creative_direction: document.getElementById('creativeDirectionInput').value.trim(),
      language: currentLanguage,
    };
```

---

## Out of Scope

- No validation of script length (warn only in log if 0 scenes produced)
- No editing of individual scenes in the UI before generation
- No image prompt preview or override in script mode
- Creative Direction field is hidden (not used) in script mode

---

## Files Modified

| File | Change |
|------|--------|
| `src/classes/Podcast.py` | Add `script_mode`/`raw_script` params; new `generate_script_from_text()`; new `_generate_image_prompt()`; relax scene count guard |
| `src/podcast_server.py` | Accept `script_mode`/`raw_script` in `/start-podcast`; branch Phase 5 |
| `src/ui/podcast_component.html` | Add Input Mode toggle; wrap topic fields; add script mode fields |
| `src/ui/podcast-main.js` | Add `onInputModeChange()`; update `startGeneration()` payload |
