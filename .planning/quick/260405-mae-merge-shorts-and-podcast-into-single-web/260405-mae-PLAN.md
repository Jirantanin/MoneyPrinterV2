---
phase: quick
plan: 260405-mae
type: execute
wave: 1
depends_on: []
files_modified:
  - src/podcast_server.py
  - src/podcast_ui.html
  - src/main.py
  - src/constants.py
autonomous: true
requirements: [MERGE-UI]

must_haves:
  truths:
    - "Single web app on port 8899 with tab navigation (Podcast | YouTube Shorts)"
    - "Podcast tab works identically to current podcast_ui.html — generate, stream, upload, thumbnail studio, recent episodes"
    - "YouTube Shorts tab works identically to current shorts_ui.html — account select, generate, stream, upload, recent shorts"
    - "Tab switching is instant (pure JS/CSS, no page reload)"
    - "main.py option 5 opens the unified UI, option 6 removed, Quit is option 6"
    - "shorts_server.py and shorts_ui.html are deleted after migration"
  artifacts:
    - path: "src/podcast_server.py"
      provides: "Unified FastAPI server with both Podcast and Shorts routes"
      contains: "/shorts/api/"
    - path: "src/podcast_ui.html"
      provides: "Tabbed UI combining both Podcast and Shorts interfaces"
      contains: "tab-podcast"
    - path: "src/main.py"
      provides: "Menu with option 5 launching unified server, no option 6 for shorts"
    - path: "src/constants.py"
      provides: "OPTIONS list with 6 items (no YouTube Shorts GUI entry)"
  key_links:
    - from: "src/podcast_ui.html (Shorts tab)"
      to: "/shorts/api/*"
      via: "fetch calls with /shorts/ prefix"
      pattern: "fetch.*shorts/api"
    - from: "src/podcast_server.py"
      to: "shorts pipeline (_run_shorts_pipeline)"
      via: "background thread on POST /shorts/api/generate"
---

<objective>
Merge the YouTube Shorts GUI (shorts_server.py + shorts_ui.html) into the existing Podcast GUI (podcast_server.py + podcast_ui.html) as a single tabbed web application on port 8899.

Purpose: Users get one launch point and one browser tab to access both Podcast and Shorts generation instead of two separate servers on different ports.

Output: A single server (podcast_server.py) serving a single HTML page with Podcast/Shorts tabs, accessible via main.py option 5. shorts_server.py and shorts_ui.html are deleted.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@src/podcast_server.py (existing server to expand)
@src/shorts_server.py (routes to migrate, then delete)
@src/podcast_ui.html (existing UI to add tabs to)
@src/shorts_ui.html (UI to merge in, then delete)
@src/main.py (remove option 6)
@src/constants.py (remove "YouTube Shorts GUI" from OPTIONS)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Migrate Shorts routes into podcast_server.py and update main.py/constants.py</name>
  <files>src/podcast_server.py, src/main.py, src/constants.py</files>
  <action>
**podcast_server.py — Add all Shorts backend functionality:**

1. Add module-level storage dicts for Shorts state (same pattern as episodes dict):
   - `shorts: dict = {}` — keyed by short_id
   - `short_events: dict = {}` — SSE events
   - `short_approvals: dict = {}` — threading.Event for step mode

2. Add Shorts constants:
   ```python
   _SHORTS_STEPS = [
       "Generate Topic", "Generate Script", "Generate Hook",
       "Generate Metadata", "Generate Image Prompts", "Generate Images",
       "Text-to-Speech", "Generate Subtitles", "Render Video",
   ]
   ```

3. Copy from shorts_server.py into podcast_server.py (adapting function names to avoid collision with podcast equivalents):
   - `_make_shorts_step_states()` (uses _SHORTS_STEPS)
   - `_ShortsStdoutCapture` class (or reuse _StdoutCapture with a storage param — refactor to accept dict reference)
   - `_push_shorts_event()`, `_wait_for_shorts_approval()`, `_run_shorts_step()` — same logic as podcast versions but operating on `shorts`/`short_events`/`short_approvals` dicts
   - `_run_shorts_pipeline(short_id)` — full pipeline from shorts_server.py lines 140-367

4. Add all Shorts routes under `/shorts/` prefix:
   - `GET  /shorts/api/accounts` — return YouTube accounts from cache (copy from shorts_server.py)
   - `POST /shorts/api/generate` — start Shorts pipeline, return short_id
   - `GET  /shorts/api/stream/{short_id}` — SSE progress stream
   - `GET  /shorts/api/episode/{short_id}` — full short state
   - `POST /shorts/api/approve/{short_id}` — approve step
   - `POST /shorts/api/cancel/{short_id}` — cancel pipeline
   - `POST /shorts/api/upload/{short_id}` — upload to YouTube
   - `GET  /shorts/api/shorts` — list recent shorts
   - `GET  /shorts/static/{short_id}/{filename}` — serve short files

   Each route function name must be unique (e.g., `shorts_api_generate`, `shorts_api_stream`, etc.). The logic is identical to shorts_server.py but routes are prefixed with `/shorts/`.

5. Update `app = FastAPI(title="MPV2 Studio")` — rename from "Podcast Generator" to reflect unified nature.

6. Rename `launch_podcast_server` to keep the same name (for backward compat with main.py import) but update the internal print message if any.

**constants.py:**
Change OPTIONS list to remove "YouTube Shorts GUI" entry:
```python
OPTIONS = [
    "YouTube Shorts Automation",
    "Twitter Bot",
    "Affiliate Marketing",
    "Outreach",
    "Studio",      # was "Podcast", now unified
    "Quit"
]
```
(6 items total, Quit is option 6.)

**main.py:**
- Remove the `elif user_input == 6:` block that launches shorts_server (lines 469-471)
- Change option 5 info message from "Launching Podcast Generator GUI..." to "Launching Studio..."
- Change `elif user_input == 7:` (quit) to `elif user_input == 6:` since there are now only 6 options
- Remove the `from shorts_server import launch_shorts_server` import line
  </action>
  <verify>
    <automated>cd C:/Users/66984/workspace-coding/MoneyPrinterV2 && py -c "import sys; sys.path.insert(0,'src'); from podcast_server import app; routes=[r.path for r in app.routes]; assert '/shorts/api/generate' in routes, f'missing shorts generate route, have: {routes}'; assert '/shorts/api/accounts' in routes; print('OK: all shorts routes registered')"</automated>
  </verify>
  <done>podcast_server.py contains all Shorts routes under /shorts/ prefix, constants.py has 6 options with Quit last, main.py launches unified server from option 5 only</done>
</task>

<task type="auto">
  <name>Task 2: Add tab navigation to podcast_ui.html and embed Shorts UI</name>
  <files>src/podcast_ui.html</files>
  <action>
**Add tab navigation bar below the header, above main content:**

1. Replace the header content:
   - Title: "MPV2 Studio" (instead of "Podcast Generator")
   - Subtitle: "Powered by Ollama + Gemini + Remotion"

2. Add a tab bar immediately after the header (inside body, before main):
   ```html
   <nav class="border-b border-overlay px-6 flex gap-0">
     <button id="tab-btn-podcast" onclick="switchTab('podcast')"
       class="px-5 py-3 text-sm font-medium border-b-2 transition-colors">
       Podcast
     </button>
     <button id="tab-btn-shorts" onclick="switchTab('shorts')"
       class="px-5 py-3 text-sm font-medium border-b-2 transition-colors">
       YouTube Shorts
     </button>
   </nav>
   ```
   Active tab style: `border-accent text-accent`
   Inactive tab style: `border-transparent text-subtext hover:text-text`

3. Wrap the existing podcast `<main>` content in `<div id="tab-podcast">`. Keep all existing podcast HTML, JS variables, and functions untouched inside this div.

4. Create `<div id="tab-shorts" class="hidden">` and paste the Shorts UI `<main>` content from shorts_ui.html into it. This includes:
   - Account selector, niche/topic/language fields
   - Mode toggle (auto/step)
   - Generate button
   - Step progress panel (9 steps)
   - Log output area
   - Video preview section
   - Recent Shorts sidebar
   - All the Shorts-specific inline JS

5. **Critical JS changes for the Shorts tab:**
   - ALL fetch URLs in the Shorts JS must be prefixed with `/shorts/` — e.g., `fetch('/api/generate',...)` becomes `fetch('/shorts/api/generate',...)`
   - `fetch('/api/accounts')` becomes `fetch('/shorts/api/accounts')`
   - `fetch('/api/stream/...')` becomes `fetch('/shorts/api/stream/...')`
   - `fetch('/api/episode/...')` becomes `fetch('/shorts/api/episode/...')`
   - `fetch('/api/approve/...')` becomes `fetch('/shorts/api/approve/...')`
   - `fetch('/api/cancel/...')` becomes `fetch('/shorts/api/cancel/...')`
   - `fetch('/api/upload/...')` becomes `fetch('/shorts/api/upload/...')`
   - `fetch('/api/shorts')` becomes `fetch('/shorts/api/shorts')`
   - Static file URLs: `/static/` references in Shorts JS become `/shorts/static/`

6. **Namespace JS to avoid collisions:**
   - Podcast JS functions and variables keep their original names (they are already in the DOM)
   - Shorts JS functions MUST be renamed with a `shorts_` prefix to avoid collision. Key functions to rename:
     - `loadAccounts()` -> `shorts_loadAccounts()`
     - `startGeneration()` -> `shorts_startGeneration()`
     - `connectSSE()` -> `shorts_connectSSE()`
     - `pollEpisode()` -> `shorts_pollEpisode()`
     - `approveStep()` -> `shorts_approveStep()`
     - `cancelPipeline()` -> `shorts_cancelPipeline()`
     - `uploadToYouTube()` -> `shorts_uploadToYouTube()`
     - `loadRecentShorts()` -> `shorts_loadRecentShorts()`
     - Any other function names that collide
   - Global variables in Shorts JS: prefix with `shorts_` (e.g., `shorts_currentShortId`, `shorts_eventSource`)
   - Element IDs in Shorts HTML: prefix with `shorts-` to avoid collision (e.g., `shorts-topicInput`, `shorts-generateBtn`, `shorts-logOutput`, `shorts-stepsList`)
   - Update all `document.getElementById(...)` and `document.querySelector(...)` calls in Shorts JS to match renamed IDs

7. **Tab switching JS function:**
   ```javascript
   function switchTab(tab) {
     const tabs = ['podcast', 'shorts'];
     tabs.forEach(t => {
       document.getElementById('tab-' + t).classList.toggle('hidden', t !== tab);
       const btn = document.getElementById('tab-btn-' + t);
       btn.classList.toggle('border-accent', t === tab);
       btn.classList.toggle('text-accent', t === tab);
       btn.classList.toggle('border-transparent', t !== tab);
       btn.classList.toggle('text-subtext', t !== tab);
     });
   }
   // Initialize on load — default to Podcast tab
   switchTab('podcast');
   ```

8. **On Shorts tab activation:** Call `shorts_loadAccounts()` and `shorts_loadRecentShorts()` if not already loaded (use a flag like `shorts_initialized`). This avoids fetching account data until the user actually clicks the Shorts tab.

9. Remove any duplicate `<style>` blocks — the Shorts UI uses the same Tailwind config and custom CSS (step-spinner, fade-in, etc.) as Podcast, so no duplication needed.
  </action>
  <verify>
    <automated>cd C:/Users/66984/workspace-coding/MoneyPrinterV2 && py -c "
with open('src/podcast_ui.html','r',encoding='utf-8') as f: html=f.read()
assert 'tab-podcast' in html, 'missing tab-podcast div'
assert 'tab-shorts' in html, 'missing tab-shorts div'
assert 'switchTab' in html, 'missing switchTab function'
assert '/shorts/api/generate' in html, 'shorts fetch URLs not prefixed'
assert 'shorts_startGeneration' in html or 'shorts_start' in html, 'shorts JS not namespaced'
assert 'MPV2 Studio' in html, 'title not updated'
print('OK: tabbed UI structure verified')
"</automated>
  </verify>
  <done>podcast_ui.html has tab navigation with Podcast (default) and YouTube Shorts tabs, all Shorts JS is namespaced and uses /shorts/ API prefix, no page reload on tab switch</done>
</task>

<task type="auto">
  <name>Task 3: Delete shorts_server.py and shorts_ui.html</name>
  <files>src/shorts_server.py, src/shorts_ui.html</files>
  <action>
Delete both files that are now fully migrated:
```bash
rm src/shorts_server.py src/shorts_ui.html
```

Then verify no remaining imports reference these deleted files:
- Check main.py does not import from shorts_server
- Check no other Python files import from shorts_server
- If any references remain, remove them
  </action>
  <verify>
    <automated>cd C:/Users/66984/workspace-coding/MoneyPrinterV2 && test ! -f src/shorts_server.py && test ! -f src/shorts_ui.html && ! grep -r "shorts_server\|shorts_ui" src/*.py && echo "OK: deleted and no dangling refs"</automated>
  </verify>
  <done>shorts_server.py and shorts_ui.html are deleted, no remaining imports or references to them in the codebase</done>
</task>

</tasks>

<verification>
1. `py -c "import sys; sys.path.insert(0,'src'); from podcast_server import app"` — server module loads without error
2. All `/shorts/api/*` routes are registered on the unified FastAPI app
3. podcast_ui.html contains tab navigation, both tab content divs, and namespaced JS
4. main.py has 6 menu options (no Shorts GUI entry, Quit at 6)
5. shorts_server.py and shorts_ui.html do not exist
</verification>

<success_criteria>
- Single server on port 8899 serves both Podcast and Shorts functionality
- Tab navigation switches between Podcast and YouTube Shorts views without page reload
- Each tab's JS is namespaced to avoid variable/function collisions
- Shorts API calls use /shorts/ prefix
- main.py option 5 launches unified Studio, option 6 is Quit
- No orphaned files (shorts_server.py, shorts_ui.html deleted)
</success_criteria>

<output>
After completion, create `.planning/quick/260405-mae-merge-shorts-and-podcast-into-single-web/260405-mae-SUMMARY.md`
</output>
