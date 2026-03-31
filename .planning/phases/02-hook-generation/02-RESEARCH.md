# Phase 2: Hook Generation - Research

**Researched:** 2026-03-31
**Domain:** LLM hook generation via Ollama structured output; script prepend pattern; edge-tts TTS pipeline; fallback validation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase. Constraints are derived from REQUIREMENTS.md, STATE.md, and prior project research.

### Locked Decisions
- Hook must receive the already-generated `script` text (not just `topic`) to avoid semantic disconnect — documented decision in STATE.md
- Template fallback is mandatory when LLM returns unusable output (empty, over 15 words, malformed)
- Hook sentence is prepended to `self.script` BEFORE `generate_script_to_speech()` is called — that ordering is the single constraint that satisfies HOOK-02
- LLM stays as Ollama (local inference, `llm_provider.py`). No provider change.
- No per-segment prosody in this phase — TTS-03 (hook at higher rate) is a v2 requirement; Phase 2 uses the global `tts_rate` set in Phase 1

### Claude's Discretion
- Whether to use Ollama structured output (`format=model_json_schema()`) or free-text prompting with regex post-processing
- Exact hook archetypes to offer the LLM (recommended: question / stat / bold)
- Template fallback sentences (one per niche category or a single universal fallback)
- Whether to add a `hook_archetype` config key for the operator to bias archetype selection
- Retry count before falling back to template (recommended: 1 retry; no exponential back-off needed at this scale)

### Deferred Ideas (OUT OF SCOPE)
- Hook sentence rendered at higher rate/pitch than body (TTS-03 — v2 requirement; requires multi-call TTS concatenation)
- LLM callback ending that references the opening hook (HOOK-04 — v2 requirement)
- Per-segment prosody of any kind
- Switching TTS provider
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOOK-01 | Pipeline generates a contextual opening hook sentence (question, stat, or payoff-preview archetype) via LLM, matched to topic and script content | Ollama `Client.chat(format=HookOutput.model_json_schema())` forces structured JSON output; verified `format` param present in installed ollama 0.6.1; Pydantic v2 `model_json_schema()` verified working in venv |
| HOOK-02 | Hook sentence is prepended to the script before TTS rendering so it is both spoken and appears in subtitles | `generate_video()` call order: `generate_script()` → (hook injection point) → `generate_script_to_speech()` → `generate_subtitles()`. Inserting `self.script = hook + " " + self.script` between script generation and TTS satisfies requirement |
| HOOK-03 | If LLM hook generation fails or returns output longer than 15 words, pipeline falls back gracefully without crashing | Word-count guard on `hook_text`; try/except around the Ollama call; template hook constants for each of 3 archetypes |
</phase_requirements>

---

## Summary

Phase 2 is a pure Python change — no Remotion, no new npm packages, no new pip packages. The pipeline already generates a script, then synthesizes it to audio, then runs Whisper. The hook sentence must be inserted into `self.script` between those two steps. Because `generate_subtitles()` runs Whisper against the TTS audio (which already includes the hook), subtitles will automatically include the hook from the first block — HOOK-02 is satisfied for free once the prepend happens before TTS.

The implementation requires one new function (`generate_hook()`) in `YouTube.py` that calls Ollama with a structured output schema, validates the result, and falls back to a template string on any failure. The function signature must accept `topic` and `script` — passing the body script to the hook prompt is the critical design constraint that prevents semantic disconnect (the LLM can tease actual content from the body rather than inventing a generic opener).

The `generate_video()` method in `YouTube.py` gets a single new call between `generate_script()` and the image/TTS steps. No other files need modification. The ollama SDK (v0.6.1, installed) and pydantic (v2.12.5, installed) fully support `format=model_json_schema()` without any new dependencies.

**Primary recommendation:** Add `generate_hook(topic, script)` to `YouTube.py`, call it inside `generate_video()` after `generate_script()`, and prepend the result to `self.script` before any downstream step. Use Ollama structured output with a 2-field `HookOutput` Pydantic model. Fallback to a category-matched template string on any exception or validation failure.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ollama` Python SDK | 0.6.1 (installed) | Structured hook generation via `Client.chat(format=...)` | Already used for all LLM calls in `llm_provider.py`; `format=` param confirmed present |
| `pydantic` | 2.12.5 (installed) | `HookOutput` schema for structured Ollama output | `model_json_schema()` confirmed working in venv; v2 API required |

### Supporting

None required. All work is within existing installed dependencies.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ollama `format=model_json_schema()` | Free-text prompt + regex extraction | Free-text is fragile with smaller local models; structured output eliminates parsing risk; both approaches use the same Ollama backend |
| `HookOutput` Pydantic model | Plain `dict` schema | Pydantic gives `.model_validate_json()` for safe deserialisation and IDE type hints; no added cost |

**Installation:** No new packages. All required libraries are already installed in the project venv.

---

## Architecture Patterns

### Files Modified

```
src/
└── classes/
    └── YouTube.py    # Add generate_hook(); add hook call in generate_video()
```

No other files need modification. The hook archetype and fallback text live as constants inside `YouTube.py` (or in `constants.py` if the planner prefers — either is acceptable).

### Pattern 1: Structured Ollama Output with Pydantic Schema

**What:** Call `_client().chat(...)` directly with `format=HookOutput.model_json_schema()` to force JSON output, then deserialise with `HookOutput.model_validate_json()`.

**When to use:** Any LLM call where the required output shape is known and must be validated.

**Source:** Verified against installed ollama 0.6.1 — `format` is an accepted keyword argument to `Client.chat()`.

```python
# Source: .planning/research/STACK.md + verified against installed ollama 0.6.1
from pydantic import BaseModel
from llm_provider import _client   # reuse existing client factory

class HookOutput(BaseModel):
    hook_type: str   # "question" | "stat" | "bold"
    hook_text: str   # the opening sentence

def generate_hook(self) -> str:
    """
    Generates a contextual opening hook sentence via Ollama structured output.
    Falls back to a template hook if the LLM returns unusable output.
    """
    from llm_provider import get_active_model
    model = get_active_model()

    prompt_user = (
        f"Topic: {self.subject}\n\n"
        f"Script body:\n{self.script}\n\n"
        "Write a single opening hook sentence (10-15 words) that teases the content above.\n"
        "Choose the archetype that best fits:\n"
        "  question — rhetorical question (e.g. 'Did you know...' / 'What if...')\n"
        "  stat     — leads with a concrete number or surprising fact\n"
        "  bold     — makes a provocative or counterintuitive claim\n\n"
        f"Output JSON matching this schema:\n{HookOutput.model_json_schema()}"
    )

    try:
        from llm_provider import _client as get_client
        response = get_client().chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write opening hooks for YouTube Shorts. "
                        "Output ONLY valid JSON matching the provided schema. "
                        "hook_text must be under 15 words. No markdown."
                    ),
                },
                {"role": "user", "content": prompt_user},
            ],
            format=HookOutput.model_json_schema(),
        )
        result = HookOutput.model_validate_json(response.message.content)
        hook_text = re.sub(r"[*#\"]", "", result.hook_text).strip()
        word_count = len(hook_text.split())
        if not hook_text or word_count > 15:
            raise ValueError(f"Hook failed validation: {word_count} words")
        return hook_text
    except Exception as e:
        if get_verbose():
            warning(f"Hook generation failed ({e}). Using template fallback.")
        return self._hook_template_fallback()
```

**Key note:** `_client()` is a private function in `llm_provider.py`. The planner must decide whether to call `_client()` directly (import it), or to add a `generate_hook_structured()` function in `llm_provider.py` that wraps the structured call. The simpler approach is to call `_client()` directly from `YouTube.py` since the class already imports from `llm_provider`.

### Pattern 2: Template Fallback by Category

**What:** `_hook_template_fallback()` returns a predefined hook string using the existing `_detect_category()` method (already in `YouTube.py`) to select the most relevant template.

**When to use:** When the LLM call throws, returns empty text, or returns a hook over 15 words.

```python
# Source: YouTube.py _detect_category() already exists — returns
# 'breaking_news' | 'science_facts' | 'weird_viral' | 'default'
_HOOK_TEMPLATES = {
    "breaking_news":   "This just happened and you need to know about it.",
    "science_facts":   "This scientific fact will completely change how you see the world.",
    "weird_viral":     "You will not believe what happened next.",
    "default":         "What you are about to learn will surprise you.",
}

def _hook_template_fallback(self) -> str:
    category = self._detect_category()
    return _HOOK_TEMPLATES.get(category, _HOOK_TEMPLATES["default"])
```

### Pattern 3: Script Prepend and Cleanup

**What:** The hook sentence is prepended to `self.script` using string concatenation. The separator must be a single space (or period + space if the hook does not already end with punctuation). The existing `generate_script_to_speech()` already strips non-word characters with `re.sub(r"[^\w\s.?!]", "", self.script)` — this runs AFTER the prepend and will handle any stray punctuation the hook may contain.

**When to use:** After `generate_hook()` succeeds or falls back, before `generate_script_to_speech()`.

```python
# In generate_video(), between generate_script() and generate_script_to_speech():
hook = self.generate_hook()
# Ensure hook ends with punctuation so TTS pauses before the body
if hook and hook[-1] not in ".?!":
    hook = hook + "."
self.script = hook + " " + self.script
```

### Insertion Point in `generate_video()`

The current call order in `generate_video()` (lines 806-846 of `YouTube.py`):

```
generate_topic()
generate_script()
generate_metadata()
generate_prompts()
for prompt: generate_image()
generate_script_to_speech()   # <-- TTS must see the hook
generate_subtitles()          # <-- Whisper must see the audio that includes the hook
combine_remotion()
```

The hook call and prepend belong between `generate_script()` and `generate_metadata()`. Placing it before `generate_metadata()` means the metadata LLM call also sees the hook-prepended script, which is desirable (title and description will be hook-aware).

### Anti-Patterns to Avoid

- **Generating hook from topic only:** If the hook prompt only receives `self.subject`, the LLM invents a generic opener that may contradict the script. Pass both `self.subject` and `self.script` body.
- **Calling `generate_text()` from `llm_provider.py` for the hook:** `generate_text()` does not accept a `format=` argument — it wraps `client.chat()` with only `messages`. For structured output, call `_client().chat()` directly or add a `generate_text_structured()` function in `llm_provider.py`.
- **Word count after Ollama sanitisation:** Count words from the cleaned string (after stripping markdown), not the raw Ollama response. A response like `"**Did you know this?**"` is 4 words after stripping but looks longer before.
- **Prepending after `generate_script_to_speech()`:** If the hook is added after TTS runs, it will not be in the audio and HOOK-02 fails.
- **Storing the hook on `self` before falling back:** Do not expose `self.hook` publicly before the fallback path is resolved — the only thing that must be written to `self.script` is the final (possibly fallback) hook string.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured JSON output from LLM | Regex parsing of free-text LLM response | `format=HookOutput.model_json_schema()` in Ollama chat | Local models (Mistral 7B, Llama 3.1 8B) frequently add "Hook:", quotes, markdown in free-text mode; structured output enforces schema at the token generation level |
| JSON deserialisation with validation | Manual `json.loads()` + key checks | `HookOutput.model_validate_json(response.message.content)` | Pydantic validates types and raises `ValidationError` on bad schema — one exception handler covers all bad output cases |
| Template fallback selection | `if/elif` on `self._niche` string | Reuse `_detect_category()` already in `YouTube.py` | Method already correctly maps niche + subject keywords to 4 category buckets; no duplication needed |

**Key insight:** The Ollama SDK's `format=` parameter enforces the output schema at the token sampling level. This is categorically different from post-processing: if the model is constrained to emit valid JSON matching the schema, the only failure mode left is semantic (hook is valid JSON but over 15 words or empty). Those two cases are trivially caught by a word-count guard.

---

## Common Pitfalls

### Pitfall 1: Hook Semantically Disconnected from Script Body

**What goes wrong:** Hook says "This will change your life forever" but the script is a mild factual summary about black holes. Viewer watches 3 seconds, realises they were baited, leaves. YouTube measures this as a drop at 3 seconds which suppresses distribution.

**Why it happens:** Hook generation is a separate LLM call; if only `topic` is passed, the hook has no knowledge of what the script actually says.

**How to avoid:** Pass both `self.subject` and `self.script` body text to the hook prompt. Use the instruction "Write a hook that teases the content above" — "above" anchors the LLM to the provided script content.

**Warning signs:** When reading hook + script together, the hook question is never answered in the body; the hook uses superlatives ("shocking") but the script is factual and mild.

### Pitfall 2: LLM Returns Formatting Marks or Wrapping Text

**What goes wrong:** Even with `format=`, small local models (Mistral 7B, Llama 3.2 3B) sometimes return `{"hook_type": "question", "hook_text": "**Did you know this?**"}` with markdown bold inside the JSON string. When prepended to the script and passed to edge-tts, the `**` is either spoken aloud or causes an unexpected pause.

**Why it happens:** `format=` enforces JSON structure but not the content of string values. Formatting characters are valid inside a JSON string.

**How to avoid:** After deserialising `HookOutput`, apply `re.sub(r"[*#\"]", "", result.hook_text).strip()`. The existing script post-processing (`re.sub(r"\*", "", completion)`) in `generate_script()` does the same thing — the hook needs its own strip because it takes a separate path.

**Warning signs:** Generated audio for the hook contains robotic pauses between words; subtitle SRT shows asterisks or hash marks in the first block.

### Pitfall 3: Hook Added After TTS Synthesis

**What goes wrong:** HOOK-02 fails. The spoken audio does not begin with the hook, and the SRT generated by Whisper does not contain it. The video plays the body narration from frame 0 with no hook at the audio or subtitle level.

**Why it happens:** Inserting the hook call after `generate_script_to_speech()` in `generate_video()`, or between TTS and Whisper. Easy mistake if the ordering is not explicitly verified.

**How to avoid:** The hook must be prepended to `self.script` BEFORE `generate_script_to_speech()` is called. The single correct placement: after `generate_script()`, before `generate_script_to_speech()`.

**Warning signs:** Verification check — transcribe the output WAV and confirm the hook text appears as the first words; inspect the SRT and confirm block 1 contains the hook.

### Pitfall 4: Word Count Guard on Raw Ollama Response

**What goes wrong:** Raw Ollama response `"hook_text": "**Breaking news this fact will completely destroy your understanding**"` contains 11 words but looks like 12+ if the `**` markers are counted. The guard strips the markdown first, then counts — but if the guard runs against the un-stripped string, it under-counts by missing the markers.

**Why it happens:** Strip and word-count steps run in the wrong order.

**How to avoid:** Strip markdown characters before counting words. Order: (1) deserialise JSON, (2) strip formatting marks, (3) count words, (4) reject if > 15.

### Pitfall 5: `generate_text()` Does Not Support `format=`

**What goes wrong:** Developer calls `self.generate_response(prompt)` (which wraps `generate_text()` in `llm_provider.py`), expecting structured JSON output. `generate_text()` internally calls `_client().chat()` without passing `format=`, so the model returns free text and `model_validate_json()` raises `ValidationError`.

**Why it happens:** `generate_text()` was designed for free-text generation. Its signature is `(prompt: str, model_name: str = None) -> str` — no `format=` parameter.

**How to avoid:** Import `_client` from `llm_provider` and call `_client().chat(..., format=HookOutput.model_json_schema())` directly. Alternatively, add a `generate_text_structured(prompt, schema, model_name=None)` function to `llm_provider.py` that threads the `format=` argument through.

**Warning signs:** Hook generation always falls through to the template fallback despite Ollama being healthy; a `ValidationError` or `json.JSONDecodeError` appears in logs.

---

## Code Examples

Verified patterns from installed libraries and existing codebase:

### HookOutput Pydantic Model

```python
# Source: pydantic v2.12.5 verified in venv; model_json_schema() confirmed working
from pydantic import BaseModel

class HookOutput(BaseModel):
    hook_type: str   # "question" | "stat" | "bold"
    hook_text: str   # opening sentence, target 10-15 words
```

### Ollama Structured Call

```python
# Source: ollama 0.6.1 installed; 'format' param confirmed in Client.chat() signature
from llm_provider import _client, get_active_model

response = _client().chat(
    model=get_active_model(),
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": prompt_user},
    ],
    format=HookOutput.model_json_schema(),
)
result = HookOutput.model_validate_json(response.message.content)
```

### Template Fallback Map

```python
# Category keys match _detect_category() return values (already in YouTube.py)
_HOOK_TEMPLATES = {
    "breaking_news":   "This just happened and you need to know about it.",
    "science_facts":   "This scientific fact will completely change how you see the world.",
    "weird_viral":     "You will not believe what happened next.",
    "default":         "What you are about to learn will surprise you.",
}
```

### Script Prepend

```python
# After generate_hook() returns, before generate_script_to_speech()
hook = self.generate_hook()
if hook and hook[-1] not in ".?!":
    hook = hook + "."
self.script = hook + " " + self.script
```

### generate_video() Call Order (after Phase 2)

```python
def generate_video(self, tts_instance: TTS) -> str:
    self.generate_topic()
    self.generate_script()
    hook = self.generate_hook()          # NEW — must come before TTS
    if hook and hook[-1] not in ".?!":
        hook = hook + "."
    self.script = hook + " " + self.script
    self.generate_metadata()             # sees hook-prepended script (desirable)
    self.generate_prompts()
    for prompt in self.image_prompts:
        self.generate_image(prompt)
    self.generate_script_to_speech(tts_instance)  # TTS now includes hook
    self.srt_path = self.generate_subtitles(self.tts_path)
    path = self.combine_remotion()
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-text LLM + regex extraction | Ollama `format=model_json_schema()` structured output | Ollama SDK v0.5+ | No fragile regex; schema enforced at sampling level |
| Hard-coded opening templates | LLM-selected archetype + topic-matched text | 2024 Shorts creator ecosystem shift | Generic templates ("Did you know?") are now viewer-pattern-recognised; LLM can match tone to content |

**Deprecated/outdated:**
- Regex-based extraction of hook from free-text: fragile with small local models; replaced by `format=` structured output where possible; retained only as second-level fallback

---

## Open Questions

1. **Whether to expose `hook_archetype` config option**
   - What we know: The three archetypes (question / stat / bold) are the dominant Shorts hook patterns; LLM can be biased toward a specific one
   - What's unclear: Whether operators want to control this; the LLM-selected archetype should work for most niches without operator input
   - Recommendation: Do NOT add a config option for v1 — keep the prompt open to all three archetypes; defer per-niche archetype tuning to v2 if analytics show a pattern preference

2. **Whether `_client` should be imported directly or wrapped**
   - What we know: `_client()` in `llm_provider.py` is a private factory (underscore-prefixed); importing it across module boundaries is a minor convention violation but is functionally safe
   - What's unclear: Whether the planner prefers adding a `generate_text_structured()` function to `llm_provider.py` to keep structured calls in one place
   - Recommendation: Add a thin `generate_text_structured(prompt, schema, model_name=None)` function in `llm_provider.py` — this keeps `YouTube.py` from depending on the `_client` internal, and makes the pattern reusable for future structured calls

3. **Retry count before template fallback**
   - What we know: Ollama with `format=` rarely fails on schema validation, but small models may return hook_text with zero words or > 15 words
   - What's unclear: Whether one retry is enough, or if the overhead of a second Ollama call is worth it
   - Recommendation: 1 retry (if validation fails, call once more with a stricter prompt); fall back to template on second failure. No exponential back-off — the cron job has no retry budget.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `ollama` Python SDK | Structured hook generation | Yes | 0.6.1 | — |
| `pydantic` | `HookOutput` schema + deserialisation | Yes | 2.12.5 | — |
| Ollama server | LLM inference | Assumed running (existing requirement) | — | Template fallback covers server-down case |
| `re` module | Markdown stripping from hook text | Yes | stdlib | — |

No missing dependencies. All required tools are already installed.

---

## Validation Architecture

Validation is disabled (`workflow.nyquist_validation: false` in `.planning/config.json`). This section is skipped per configuration.

---

## Sources

### Primary (HIGH confidence)
- `src/classes/YouTube.py` — read directly; `generate_video()` call order confirmed; `_detect_category()` confirmed; script cleanup regex confirmed
- `src/llm_provider.py` — read directly; `_client()` factory and `generate_text()` signature confirmed; `format=` not currently passed
- `src/config.py` — read directly; getter pattern confirmed; no `hook_*` keys currently exist
- `venv/Lib/site-packages/ollama/_client.py` — inspected directly; `format` param confirmed in `Client.chat()` signature
- Pydantic v2.12.5 `model_json_schema()` — verified in venv via `python -c`
- `.planning/research/STACK.md` — Hook Generation section (Ollama structured output pattern, HIGH confidence, originally sourced from docs.ollama.com)
- `.planning/research/PITFALLS.md` — Pitfall 4 (LLM hook formatting), Pitfall 5 (semantic disconnect), Pitfall table (Ollama retry without back-off)
- `.planning/research/FEATURES.md` — Hook generation roadmap section; injection point confirmed as `generate_script()`

### Secondary (MEDIUM confidence)
- [docs.ollama.com/capabilities/structured-outputs](https://docs.ollama.com/capabilities/structured-outputs) — `format=model_json_schema()` pattern; verified by local SDK inspection (MEDIUM: docs may diverge from installed 0.6.1 but local code is authoritative)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ollama 0.6.1 and pydantic 2.12.5 confirmed installed; `format` param verified in SDK source
- Architecture: HIGH — `generate_video()` call order read directly from source; insertion point is unambiguous
- Pitfalls: HIGH — pitfalls 1-3 sourced from pre-existing `.planning/research/PITFALLS.md` (itself researched 2026-03-30); pitfalls 4-5 derived from direct code inspection

**Research date:** 2026-03-31
**Valid until:** 2026-06-30 (ollama SDK API and pydantic v2 API are stable; hook archetype patterns are stable)
