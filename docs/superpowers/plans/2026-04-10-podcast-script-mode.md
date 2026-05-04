# Podcast Script Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Script Mode toggle to the Podcast UI so users can paste their own narration text instead of entering a topic; the system auto-splits it into scenes and generates image prompts per scene via LLM.

**Architecture:** Script mode bypasses Phase 5 (`generate_script`) entirely. The raw script text is split into scenes by sentence count (using existing `get_script_sentence_length()` config), then a new `generate_script_from_text()` method generates one image prompt per scene via LLM and writes `script.json` directly. Phases 6–8 (assets, render, upload) are unchanged.

**Tech Stack:** Python 3.12, FastAPI, vanilla JS, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-10-podcast-script-mode-design.md`

---

## File Map

| File | Change |
|------|--------|
| `src/classes/Podcast.py` | Relax 14-scene guard; add `script_mode`/`raw_script` params; add `_generate_image_prompt()` helper; add `generate_script_from_text()` method |
| `src/podcast_server.py` | Update `_build_podcast_instance()`; update `/api/generate` endpoint; branch Phase 5 in `_run_pipeline()` |
| `src/ui/podcast_component.html` | Add Input Mode toggle; wrap topic fields in `#topicModeFields`; add `#scriptModeFields` |
| `src/ui/podcast-api.js` | Update `startGeneration()` to build payload and disable inputs per mode |

---

## Task 1: Relax the hardcoded 14-scene guard in `Podcast.py`

**Files:**
- Modify: `src/classes/Podcast.py:253-254`

- [ ] **Step 1: Edit `_load_script_scenes()`**

  In `src/classes/Podcast.py`, find these two lines (around line 253):
  ```python
  if len(scenes) != 14:
      raise ValueError(f"Expected 14 scenes in script.json, got {len(scenes)}")
  ```
  Replace with:
  ```python
  if not scenes:
      raise ValueError("script.json is empty")
  ```

- [ ] **Step 2: Verify no other 14-scene references remain**

  Run:
  ```bash
  grep -n "14" src/classes/Podcast.py
  ```
  Expected: no remaining lines that enforce exactly 14 scenes (other matches like comment lines or unrelated numbers are fine).

- [ ] **Step 3: Commit**

  ```bash
  git add src/classes/Podcast.py
  git commit -m "fix: relax hardcoded 14-scene guard in _load_script_scenes"
  ```

---

## Task 2: Add script mode support to `Podcast.py`

**Files:**
- Modify: `src/classes/Podcast.py`

- [ ] **Step 1: Add `script_mode` and `raw_script` params to `__init__()`**

  Find `__init__` (around line 184). Change signature from:
  ```python
  def __init__(
      self,
      topic: str = "",
      language: str = "English",
      tts_source: str = "edge",
      creative_direction: str = "",
  ) -> None:
      self.topic = topic
      self.language = language
      self.tts_source = (tts_source or "edge").lower()
      self.creative_direction = (creative_direction or "").strip()
  ```
  To:
  ```python
  def __init__(
      self,
      topic: str = "",
      language: str = "English",
      tts_source: str = "edge",
      creative_direction: str = "",
      script_mode: bool = False,
      raw_script: str = "",
  ) -> None:
      self.topic = topic
      self.language = language
      self.tts_source = (tts_source or "edge").lower()
      self.creative_direction = (creative_direction or "").strip()
      self.script_mode = script_mode
      self.raw_script = (raw_script or "").strip()
  ```

- [ ] **Step 2: Add `_generate_image_prompt()` module-level helper**

  Add this function directly below `_build_topic_interpretation_block()` (before `SCENE_SCHEMA = ...`):
  ```python
  def _generate_image_prompt(narration: str) -> str:
      """Generate a visual image prompt for a single narration scene."""
      raw = generate_text(
          "You generate concise visual image prompts for podcast scenes.\n\n"
          f"Write a vivid visual image prompt for this narration:\n{narration}\n\n"
          "Return only the image prompt, no explanation, no label, no preamble."
      )
      return raw.strip()
  ```

- [ ] **Step 3: Add `generate_script_from_text()` method to the `Podcast` class**

  Add this method directly after `generate_script()` (after the method ends, before `generate_assets()`):
  ```python
  def generate_script_from_text(self, text: str) -> list:
      """Split a user-provided narration text into scenes and generate image prompts.

      Splits by sentence boundaries, groups by sentence_length config, then
      calls LLM once per scene to generate an image_prompt.

      Writes script.json to episode_dir (must be set before calling).

      Args:
          text: Raw narration text from the user.

      Returns:
          List of scene dicts with 'narration' and 'image_prompt' keys.
      """
      if not self.episode_dir:
          raise ValueError(
              "episode_dir is not set. Set episode_dir before calling generate_script_from_text()."
          )

      sentence_length = max(1, get_script_sentence_length())
      sentences = re.split(r"(?<=[.!?])\s+", text.strip())
      sentences = [s.strip() for s in sentences if s.strip()]

      if not sentences:
          raise ValueError("Script text produced no sentences after splitting.")

      scenes = []
      for i in range(0, len(sentences), sentence_length):
          narration = " ".join(sentences[i : i + sentence_length])
          image_prompt = _generate_image_prompt(narration)
          if self.style_prompt:
              image_prompt = f"{self.style_prompt}, {image_prompt}"
          scenes.append({"narration": narration, "image_prompt": image_prompt})

      script_path = os.path.join(self.episode_dir, "script.json")
      with open(script_path, "w", encoding="utf-8") as f:
          json.dump(scenes, f, ensure_ascii=False, indent=2)

      return scenes
  ```

- [ ] **Step 4: Verify the file parses cleanly**

  ```bash
  cd C:/Users/66984/workspace-coding/MoneyPrinterV2
  py -c "from src.classes.Podcast import Podcast; p = Podcast(script_mode=True, raw_script='Hello world.'); print('OK')"
  ```
  Expected output: `OK`

- [ ] **Step 5: Commit**

  ```bash
  git add src/classes/Podcast.py
  git commit -m "feat: add script mode params and generate_script_from_text() to Podcast"
  ```

---

## Task 3: Update `podcast_server.py`

**Files:**
- Modify: `src/podcast_server.py`

Three changes in this file: `_build_podcast_instance()`, `/api/generate`, and `_run_pipeline()`.

- [ ] **Step 1: Update `_build_podcast_instance()` to pass script mode params**

  Find `_build_podcast_instance()` (around line 742). Change:
  ```python
  def _build_podcast_instance(ep: dict):
      from classes.Podcast import Podcast  # noqa: PLC0415

      podcast = Podcast(
          topic=ep.get("topic", ""),
          language=ep.get("language", "English"),
          tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
          creative_direction=ep.get("creative_direction", ""),
      )
  ```
  To:
  ```python
  def _build_podcast_instance(ep: dict):
      from classes.Podcast import Podcast  # noqa: PLC0415

      podcast = Podcast(
          topic=ep.get("topic", ""),
          language=ep.get("language", "English"),
          tts_source=ep.get("tts_source", _default_tts_source(ep.get("language", "English"))),
          creative_direction=ep.get("creative_direction", ""),
          script_mode=ep.get("script_mode", False),
          raw_script=ep.get("raw_script", ""),
      )
  ```

- [ ] **Step 2: Update `/api/generate` to accept script mode params**

  Find the `api_generate` function (around line 912). Replace:
  ```python
  topic = (request_data.get("topic") or "").strip()
  if not topic:
      return JSONResponse({"error": "topic is required"}, status_code=400)

  mode = request_data.get("mode", "auto")
  if mode not in ("auto", "step"):
      mode = "auto"

  language = (request_data.get("language") or "English").strip()
  if language not in ("Thai", "English"):
      language = "English"
  tts_source = _normalize_tts_source(request_data.get("tts_source"), language)
  creative_direction = (request_data.get("creative_direction") or "").strip()

  # Build episode_id matching Podcast.py naming convention
  slug = _slugify_topic(topic)
  date_str = datetime.now().strftime("%Y%m%d")
  episode_id = f"podcast_{slug}_{date_str}"

  # Initialize episode state
  episodes[episode_id] = {
      "episode_id": episode_id,
      "podcast": None,
      "topic": topic,
      "creative_direction": creative_direction,
      "language": language,
      "tts_source": tts_source,
      "mode": mode,
      "status": "idle",
      "current_step": 0,
      "step_states": _make_step_states(),
      "scenes": [],
      "metadata": {},
      "error": None,
      "episode_dir": "",
      "cancelled": False,
      "logs": [],
  }
  ```
  With:
  ```python
  script_mode = bool(request_data.get("script_mode", False))
  raw_script = (request_data.get("raw_script") or "").strip()
  topic = (request_data.get("topic") or "").strip()

  if script_mode:
      if not raw_script:
          return JSONResponse({"error": "raw_script is required in script mode"}, status_code=400)
      # Use title as the slug source; fall back to a hash of the script text
      title = (request_data.get("title") or "Custom Script").strip()
      slug = _slugify_topic(title)
  else:
      if not topic:
          return JSONResponse({"error": "topic is required"}, status_code=400)
      title = topic
      slug = _slugify_topic(topic)

  mode = request_data.get("mode", "auto")
  if mode not in ("auto", "step"):
      mode = "auto"

  language = (request_data.get("language") or "English").strip()
  if language not in ("Thai", "English"):
      language = "English"
  tts_source = _normalize_tts_source(request_data.get("tts_source"), language)
  creative_direction = (request_data.get("creative_direction") or "").strip()

  date_str = datetime.now().strftime("%Y%m%d")
  episode_id = f"podcast_{slug}_{date_str}"

  # Initialize episode state
  episodes[episode_id] = {
      "episode_id": episode_id,
      "podcast": None,
      "topic": title,
      "creative_direction": creative_direction,
      "language": language,
      "tts_source": tts_source,
      "mode": mode,
      "script_mode": script_mode,
      "raw_script": raw_script,
      "status": "idle",
      "current_step": 0,
      "step_states": _make_step_states(),
      "scenes": [],
      "metadata": {},
      "error": None,
      "episode_dir": "",
      "cancelled": False,
      "logs": [],
  }
  ```

- [ ] **Step 3: Branch Phase 5 in `_run_pipeline()`**

  Find this line in `_run_pipeline()` (around line 774):
  ```python
  result = _run_step(episode_id, 0, lambda: podcast.generate_script(ep["topic"]))
  ```
  Replace with:
  ```python
  if ep.get("script_mode"):
      result = _run_step(episode_id, 0, lambda: podcast.generate_script_from_text(ep["raw_script"]))
  else:
      result = _run_step(episode_id, 0, lambda: podcast.generate_script(ep["topic"]))
  ```

- [ ] **Step 4: Verify server imports cleanly**

  ```bash
  cd C:/Users/66984/workspace-coding/MoneyPrinterV2
  py -c "import sys; sys.path.insert(0, 'src'); import podcast_server; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 5: Commit**

  ```bash
  git add src/podcast_server.py
  git commit -m "feat: accept script_mode/raw_script in /api/generate; branch Phase 5 in pipeline"
  ```

---

## Task 4: Update `podcast_component.html` — add Input Mode toggle and script fields

**Files:**
- Modify: `src/ui/podcast_component.html`

- [ ] **Step 1: Add Input Mode toggle row**

  Find the Run Mode toggle row (around line 28):
  ```html
        <!-- Mode toggle row -->
        <div class="flex items-center gap-4 pb-3 border-b border-overlay">
          <span class="text-xs font-medium text-subtext uppercase tracking-wide">Run Mode</span>
  ```
  Insert this block **directly before** that comment (before `<!-- Mode toggle row -->`):
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

  ```

- [ ] **Step 2: Wrap existing topic + creative direction fields in `#topicModeFields`**

  Find the comment `<!-- Topic + buttons row -->` (around line 42). Wrap the topic row AND the creative direction block in a single div:

  Before the `<!-- Topic + buttons row -->` comment, add:
  ```html
        <div id="topicModeFields">
  ```

  After the closing `</div>` of the creative direction block (around line 93, after `</textarea>` and its closing `</div>`), add:
  ```html
        </div><!-- /#topicModeFields -->
  ```

  The wrapped section should contain:
  - The `<!-- Topic + buttons row -->` div (topic input + Generate/Cancel/Resume buttons)
  - The Creative Direction textarea block

- [ ] **Step 3: Add `#scriptModeFields` block**

  Immediately after the `</div><!-- /#topicModeFields -->` closing tag, insert:
  ```html
        <!-- Script mode fields (hidden by default) -->
        <div id="scriptModeFields" class="hidden flex-col gap-4">
          <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
            <div class="flex-1 w-full">
              <label class="block text-xs font-medium text-subtext mb-1 uppercase tracking-wide">Episode Title</label>
              <input
                id="scriptTitleInput"
                type="text"
                placeholder="e.g. The Rise and Fall of Nikola Tesla"
                class="w-full bg-charcoal border border-overlay rounded-xl px-4 py-2.5 text-text placeholder-subtext focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
              />
            </div>
            <div class="flex flex-wrap gap-2 shrink-0">
              <button
                id="scriptGenerateBtn"
                onclick="startGeneration()"
                class="glass-btn glass-btn-primary px-6 py-2.5 bg-accent text-charcoal font-bold rounded-xl hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
              >
                Generate
              </button>
              <button
                id="scriptCancelBtn"
                onclick="cancelGeneration()"
                class="glass-btn glass-btn-danger hidden px-4 py-2.5 bg-charcoal border border-rose text-rose font-semibold rounded-xl hover:bg-rose hover:text-charcoal transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-subtext mb-1 uppercase tracking-wide">Script</label>
            <textarea
              id="scriptInput"
              rows="10"
              placeholder="Paste your full narration script here. The system will split it into scenes automatically based on sentence count."
              class="w-full bg-charcoal border border-overlay rounded-xl px-4 py-3 text-text placeholder-subtext focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors resize-y"
            ></textarea>
          </div>
        </div><!-- /#scriptModeFields -->
  ```

- [ ] **Step 4: Verify HTML renders without errors**

  Start the server:
  ```bash
  cd C:/Users/66984/workspace-coding/MoneyPrinterV2
  py -c "import sys; sys.path.insert(0, 'src'); from podcast_server import launch_podcast_server; launch_podcast_server()"
  ```
  Open `http://127.0.0.1:8899` and confirm the Input Mode toggle appears above the Run Mode toggle. Check browser console for errors.

- [ ] **Step 5: Commit**

  ```bash
  git add src/ui/podcast_component.html
  git commit -m "feat: add Input Mode toggle and script mode fields to podcast UI"
  ```

---

## Task 5: Update `podcast-api.js` — script mode payload and input handling

**Files:**
- Modify: `src/ui/podcast-api.js`

- [ ] **Step 1: Update `startGeneration()` to handle script mode**

  Find `startGeneration()` (around line 37). Replace the entire function body with:
  ```js
  async function startGeneration() {
    const isScript = document.getElementById('inputModeToggle').checked;

    let topic, creativeDirection, rawScript, scriptTitle;
    if (isScript) {
      rawScript = document.getElementById('scriptInput').value.trim();
      scriptTitle = document.getElementById('scriptTitleInput').value.trim() || 'Custom Script';
      if (!rawScript || isGenerating) return;
    } else {
      topic = document.getElementById('topicInput').value.trim();
      creativeDirection = document.getElementById('creativeDirectionInput').value.trim();
      if (!topic || isGenerating) return;
    }

    const mode = document.getElementById('modeToggle').checked ? 'step' : 'auto';
    const language = selectedLanguage;
    const ttsSource = selectedTtsSource;

    isGenerating = true;
    shouldLoadVideoPreview = true;

    // Disable inputs for active mode
    if (isScript) {
      document.getElementById('scriptInput').disabled = true;
      document.getElementById('scriptTitleInput').disabled = true;
      document.getElementById('scriptGenerateBtn').disabled = true;
      document.getElementById('scriptCancelBtn').classList.remove('hidden');
    } else {
      document.getElementById('topicInput').disabled = true;
      document.getElementById('creativeDirectionInput').disabled = true;
      document.getElementById('generateBtn').disabled = true;
      document.getElementById('cancelBtn').classList.remove('hidden');
    }
    lockModeToggle(true);
    resetUI();

    const payload = isScript
      ? { script_mode: true, raw_script: rawScript, title: scriptTitle, mode, language, tts_source: ttsSource, system_settings: getPodcastSystemSettingsPayload() }
      : { topic, creative_direction: creativeDirection, mode, language, tts_source: ttsSource, system_settings: getPodcastSystemSettingsPayload() };

    let res;
    try {
      res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      showError('Failed to connect to server: ' + err.message);
      onGenerationEnd();
      return;
    }

    const data = await res.json();
    if (data.error) {
      showError(data.error);
      onGenerationEnd();
      return;
    }
  ```
  
  Leave the rest of the function (SSE connection setup etc.) unchanged — only replace up to the `data.error` check.

- [ ] **Step 2: Update `onGenerationEnd()` to re-enable script mode inputs**

  Find `onGenerationEnd()` (search for `topicInput.disabled = false` in `podcast-main.js` around line 287). Add re-enabling of script mode inputs in the same block:
  ```js
  document.getElementById('scriptInput').disabled = false;
  document.getElementById('scriptTitleInput').disabled = false;
  document.getElementById('scriptGenerateBtn').disabled = false;
  document.getElementById('scriptCancelBtn').classList.add('hidden');
  ```

- [ ] **Step 3: Add `onInputModeChange()` function**

  Add this function to `podcast-main.js` (after `onModeChange()` or at end of file):
  ```js
  function onInputModeChange() {
    const isScript = document.getElementById('inputModeToggle').checked;
    document.getElementById('topicModeFields').classList.toggle('hidden', isScript);
    document.getElementById('scriptModeFields').classList.toggle('hidden', !isScript);
    // Use flex display for script fields (not block)
    if (!isScript) {
      document.getElementById('scriptModeFields').style.display = '';
    } else {
      document.getElementById('scriptModeFields').style.display = 'flex';
    }
    document.getElementById('inputModeTopicLabel').className =
      `text-sm font-medium ${isScript ? 'text-subtext' : 'text-accent'}`;
    document.getElementById('inputModeScriptLabel').className =
      `text-sm font-medium ${isScript ? 'text-accent' : 'text-subtext'}`;
  }
  ```

- [ ] **Step 4: Manual end-to-end test**

  Start the server:
  ```bash
  py -c "import sys; sys.path.insert(0, 'src'); from podcast_server import launch_podcast_server; launch_podcast_server()"
  ```
  
  Open `http://127.0.0.1:8899`. Test the following:
  
  1. Toggle "Input Mode" to Script → verify Topic + Creative Direction hide, Script textarea + Title input appear.
  2. Toggle back to Topic → verify Topic fields reappear.
  3. In Script mode, enter title `"Test Script"` and paste 3–4 sentences of narration text. Click Generate.
  4. Verify progress steps advance normally in the UI.
  5. After completion, check `.mp/podcast_test-script_YYYYMMDD/script.json` — confirm each entry has `narration` and `image_prompt` keys and the narration matches the input text split by sentence groups.

- [ ] **Step 5: Commit**

  ```bash
  git add src/ui/podcast-api.js src/ui/podcast-main.js
  git commit -m "feat: wire script mode toggle and payload in podcast UI JS"
  ```

---

## Self-Review

**Spec coverage:**
- ✅ Input: narration text only → `generate_script_from_text()` splits and LLM generates image_prompt
- ✅ Scene splitting: by sentence count → `re.split(r"(?<=[.!?])\s+", ...)` grouped by `get_script_sentence_length()`
- ✅ Scene count: flexible → 14-scene guard removed in Task 1
- ✅ Image prompts: auto-generated by LLM → `_generate_image_prompt()` in Task 2
- ✅ UI: toggle switch → Task 4; show/hide fields → Task 5
- ✅ `script_mode`/`raw_script` in episode state → Task 3
- ✅ Phase 5 branch → Task 3 Step 3

**Placeholder scan:** No TBDs or TODOs in any task.

**Type consistency:**
- `generate_script_from_text(text: str)` — defined in Task 2, called in Task 3 Step 3 ✅
- `_generate_image_prompt(narration: str)` — defined in Task 2, used inside `generate_script_from_text()` ✅
- `ep["script_mode"]` / `ep["raw_script"]` — stored in Task 3 Step 2, read in Task 3 Step 3 ✅
- `#inputModeToggle` / `#scriptModeFields` / `#topicModeFields` — created in Task 4, read in Task 5 ✅
- `scriptGenerateBtn` / `scriptCancelBtn` — created in Task 4, referenced in Task 5 ✅
