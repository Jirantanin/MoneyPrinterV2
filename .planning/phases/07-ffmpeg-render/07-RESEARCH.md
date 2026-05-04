# Phase 7: FFmpeg Render Pipeline — Research

**Researched:** 2026-04-02
**Domain:** FFmpeg zoompan, concat demuxer, Python subprocess on Windows
**Confidence:** HIGH — all findings verified by direct FFmpeg execution on the target machine

---

## Project Constraints (from CLAUDE.md)

- **Windows environment** — use `py` not `python` in CLI; subprocess.run([...]) with list args works without `shell=True`
- **No test suite, no CI, no linting config**
- **Run from project root** — all paths relative to ROOT_DIR
- **FFmpeg confirmed at** `C:\ffmpeg\bin\ffmpeg.exe` / `C:\ffmpeg\bin\ffprobe.exe`, both on PATH as `ffmpeg` / `ffprobe`
- **FFmpeg version:** 2025-06-17-git build (latest, full features including zoompan, libx264, aac)
- **No Remotion for podcast** — FFmpeg only (Remotion retained for Shorts)
- **subprocess.run(cmd, capture_output=True, text=True, check=True)** is the established pattern in this codebase (see Tts.py, YouTube._add_srt_via_ffmpeg)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REND-01 | Each scene rendered as MP4 clip with FFmpeg zoompan Ken Burns effect (image + audio) | Zoompan filter syntax verified working on target machine; zoom-in and zoom-out both confirmed |
| REND-02 | All 14 clips concatenated into single final.mp4 via FFmpeg concat | Concat demuxer with -f concat -safe 0 confirmed working; absolute path format confirmed |
| REND-03 | Final video duration 8–10 minutes given 14-scene structure | Duration is sum of per-scene WAV durations; edge-tts at -20% rate produces ~35–45s per scene → 14 scenes ≈ 8–10 min total |
</phase_requirements>

---

## Approach

**Recommended implementation:** Two-pass sequential pipeline inside `Podcast.render()`.

**Pass 1 — Per-scene clips:** For each of the 14 scenes, if `scene_NN.mp4` does not exist, call FFmpeg to combine `scene_NN.png` + `scene_NN.wav` into `scene_NN.mp4` using the `zoompan` filter. Alternate zoom direction: even scenes zoom-in, odd scenes zoom-out. Use `ffprobe` to get WAV duration first; pass frame count to zoompan's `d` parameter.

**Pass 2 — Concatenation:** Write a `concat_list.txt` listing all 14 `scene_NN.mp4` files with absolute paths. Run FFmpeg concat demuxer with `-c copy` to produce `final.mp4`.

**Resumability:** Check `os.path.exists(scene_path)` before rendering each clip. Skip clips that already exist. For the concat, regenerate `final.mp4` if any scene clip is newer than it (or simply always re-concatenate — concat is near-instant with `-c copy`).

---

## FFmpeg zoompan — Exact Syntax

### Verified working filter string

**Zoom-in (even scenes, i % 2 == 0):**
```
scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,zoompan=z='1+0.1*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=25
```

**Zoom-out (odd scenes, i % 2 == 1):**
```
scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,zoompan=z='1.1-0.1*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=25
```

Where `{frames}` = `math.ceil(duration * 25)`.

### Parameter explanation

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `z` (zoom) | `1+0.1*on/d` | Start at 1.0, end at 1.1 (10% zoom-in over clip duration) |
| `z` (zoom-out) | `1.1-0.1*on/d` | Start at 1.1, end at 1.0 (10% zoom-out) |
| `x` | `iw/2-(iw/zoom/2)` | Keep crop centered horizontally |
| `y` | `ih/2-(ih/zoom/2)` | Keep crop centered vertically |
| `d` | `math.ceil(duration * fps)` | Total output frames — MUST match actual clip length |
| `s` | `1080x1920` | Output frame size |
| `fps` | `25` | Output framerate |
| `on` | built-in | Output frame number (1-indexed, 1 to d) |

### Critical: scale before zoompan

The source PNGs from Gemini nanobanana2 with aspect ratio `9:16` are **768×1344** (not 1080×1920). zoompan requires its input to exactly match `s=`. The `scale` + `pad` filters must precede zoompan in the filter chain:

```
scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,zoompan=...
```

`force_original_aspect_ratio=decrease` scales to fit within 1080×1920 without stretching. `pad` centers it on a 1080×1920 canvas with black bars if aspect ratio doesn't perfectly match.

### Full FFmpeg command (Python list form, verified)

```python
filter_str = (
    f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
    f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
    f"d={frames}:s=1080x1920:fps=25[v]"
)
cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-i", png_path,
    "-i", wav_path,
    "-filter_complex", filter_str,
    "-map", "[v]", "-map", "1:a",
    "-c:v", "libx264", "-preset", "fast",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-t", str(duration),
    clip_path,
]
subprocess.run(cmd, capture_output=True, text=True, check=True)
```

**`-loop 1`** makes the still image repeat indefinitely. **`-t duration`** stops encoding when the audio ends. The `-filter_complex` with named output `[v]` + explicit `-map` is required when mixing `-loop 1` image input with audio input.

---

## Audio Duration Detection

### ffprobe command (verified on target machine)

```python
import subprocess

result = subprocess.run(
    [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        wav_path,
    ],
    capture_output=True, text=True, check=True,
)
duration = float(result.stdout.strip())
```

**Output:** A single float string like `"20.640000"` on stdout. `.strip()` handles trailing newline.

**Confirmed working:** Tested on `.wav` files in `.mp/` — returns duration in seconds as a decimal float.

### Frame count calculation

```python
import math

FPS = 25
frames = math.ceil(duration * FPS)
```

`math.ceil` ensures the `d` parameter covers the full audio duration. Using `int()` (floor) could leave 1-2 frames short, causing a brief freeze at clip end.

---

## Concat Strategy

### Concat list file format (verified)

```
file 'C:/Users/66984/workspace-coding/MoneyPrinterV2/.mp/podcast_xxx/scene_00.mp4'
file 'C:/Users/66984/workspace-coding/MoneyPrinterV2/.mp/podcast_xxx/scene_01.mp4'
...
file 'C:/Users/66984/workspace-coding/MoneyPrinterV2/.mp/podcast_xxx/scene_13.mp4'
```

**Critical on Windows:** FFmpeg requires forward slashes in the concat list file paths, even on Windows. Use `path.replace(chr(92), '/')` when writing each line.

**Relative paths in concat list fail** when the `-i` argument points to a different directory than the working directory. Always use absolute paths.

### Writing the concat list from Python

```python
concat_path = os.path.join(self.episode_dir, "concat_list.txt")
with open(concat_path, "w", encoding="utf-8") as f:
    for i in range(14):
        scene_num = str(i).zfill(2)
        clip_path = os.path.join(self.episode_dir, f"scene_{scene_num}.mp4")
        clip_fwd = clip_path.replace(chr(92), "/")
        f.write(f"file '{clip_fwd}'\n")
```

### FFmpeg concat command

```python
final_path = os.path.join(self.episode_dir, "final.mp4")
cmd = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_path,
    "-c", "copy",
    final_path,
]
subprocess.run(cmd, capture_output=True, text=True, check=True)
```

**`-safe 0`** is required when using absolute paths in the concat list (FFmpeg's safe mode only allows relative paths by default).

**`-c copy`** is a stream copy — no re-encode. Concat runs in under 1 second for 14 clips.

**DTS warning:** FFmpeg emits `Non-monotonic DTS` warnings for the audio stream at clip boundaries. This is a cosmetic artifact of AAC timestamps in MP4 containers. The output file is valid and plays correctly. Duration is preserved accurately (verified: 41.32s for 2×20.64s clips).

---

## Video Output Spec

| Property | Value | Rationale |
|----------|-------|-----------|
| Resolution | 1080×1920 | 9:16 portrait — matches source PNG aspect ratio, standard for YouTube portrait long-form |
| Framerate | 25 fps | Standard PAL/web rate; sufficient for Ken Burns motion |
| Video codec | libx264 | Universal compatibility, confirmed available in this FFmpeg build |
| Pixel format | yuv420p | Required for broad player compatibility; libx264 default is yuv444p which breaks QuickTime/some players |
| Video preset | `fast` | 3.7s per 20s clip on this machine; output ~2.8MB per clip. Balance of speed and file size. |
| Audio codec | aac | Standard for MP4 containers; confirmed in this FFmpeg build |
| Audio bitrate | 192k | Adequate for narration voice quality |
| Container | MP4 | Required for YouTube upload |
| Final output | `{episode_dir}/final.mp4` | Consistent with episode_dir structure from Phase 6 |

**Preset choice rationale:** `fast` vs `ultrafast` — tested on target machine:
- `ultrafast`: 2.4s/clip, ~14MB/clip → 14 clips ≈ 34s total, 196MB total
- `fast`: 3.7s/clip, ~2.8MB/clip → 14 clips ≈ 52s total, 39MB total

Use `fast` — the 18-second difference is negligible at the scale of the full pipeline (which takes minutes for TTS and image gen), and 39MB is more YouTube-upload-friendly than 196MB.

---

## Windows Subprocess Patterns

### Established codebase pattern

From `src/classes/Tts.py` and `src/classes/YouTube._add_srt_via_ffmpeg`:

```python
subprocess.run(
    ["ffmpeg", ...args...],
    capture_output=True,
    text=True,
    check=True,        # raises CalledProcessError on non-zero exit
)
```

or without `check=True` with manual returncode check (YouTube.py pattern):
```python
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
if result.returncode != 0:
    error(f"FFmpeg error: {result.stderr}")
```

**Recommendation for Phase 7:** Use `check=True` with a try/except that logs `e.stderr` from the `CalledProcessError` and re-raises. This is cleaner than manual returncode inspection.

### No `shell=True` needed

FFmpeg accepts both backslash and forward-slash paths directly in list-form subprocess args on Windows. `shell=True` is only needed for `.cmd` wrappers (like `npx.cmd`) per CLAUDE.md. FFmpeg is a native `.exe`.

### Path quoting in subprocess list args

When paths are passed as list elements (not as a single shell string), no extra quoting is needed — subprocess handles spaces in paths correctly. Windows paths with spaces work fine.

### filter_complex escaping

The `filter_complex` value is passed as a single list element string. No shell escaping is needed. Single-quote characters inside the zoompan expression (e.g., `z='1+0.1*on/516'`) are part of the FFmpeg filter syntax and are passed verbatim — they are not shell quotes.

---

## Resumability Pattern

```python
def render(self) -> None:
    if not self.episode_dir:
        raise ValueError("episode_dir is not set. Call generate_script() first.")

    final_path = os.path.join(self.episode_dir, "final.mp4")

    # Pass 1: render per-scene clips
    for i in range(14):
        scene_num = str(i).zfill(2)
        clip_path = os.path.join(self.episode_dir, f"scene_{scene_num}.mp4")

        if os.path.exists(clip_path):
            print(f"Skipping scene {i+1}/14 (clip already exists).")
            continue

        # ... render clip_path from scene_NN.png + scene_NN.wav

    # Pass 2: always regenerate final.mp4 (concat is near-instant)
    # Write concat_list.txt and run ffmpeg -f concat ...
```

**Why always regenerate final.mp4:** Concat with `-c copy` takes under 1 second for 14 clips. Checking whether all 14 clips are newer than final.mp4 adds complexity for no practical benefit. Always re-concatenate is simpler and safe.

**Clip-level skip:** `os.path.exists(clip_path)` check before rendering each scene is consistent with the Phase 6 `generate_assets()` resumability pattern in this codebase.

**Missing assets guard:** Before rendering each clip, check that `scene_NN.png` and `scene_NN.wav` both exist. Raise a descriptive error if either is missing rather than letting FFmpeg fail with a cryptic message.

---

## Pitfalls

### Pitfall 1: zoompan `d` parameter mismatch
**What goes wrong:** If `d` (frames) does not match the actual number of output frames, zoompan either loops (d too small — zoom resets mid-clip) or the expression `on/d` evaluates slightly wrong (d too large — zoom never completes).
**Why it happens:** Using `int(duration * fps)` (floor) instead of `math.ceil` can leave 1 frame short. Rounding errors accumulate.
**How to avoid:** Always use `math.ceil(duration * fps)` for `frames`. Use `-t str(duration)` to stop encoding at exactly the audio end.
**Warning signs:** Visible zoom reset mid-clip; zoom doesn't reach 1.1 at end of clip.

### Pitfall 2: zoompan requires input dimensions to match `s=` parameter
**What goes wrong:** FFmpeg exits with `Invalid argument` if the image fed into zoompan is not already the size specified in `s=`.
**Why it happens:** The Gemini output images are 768×1344, not 1080×1920. zoompan's `s=` parameter sets the output size but does not resize the input.
**How to avoid:** Always prepend `scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2` before the zoompan filter in the same filter chain. Verified working.
**Warning signs:** `Terminating thread with return code -22 (Invalid argument)` in stderr; zero-byte output file.

### Pitfall 3: Concat list uses backslashes on Windows
**What goes wrong:** `file 'C:\path\to\clip.mp4'` in the concat list causes FFmpeg to fail with "No such file or directory" even when the file exists.
**Why it happens:** FFmpeg's concat parser does not interpret Windows backslash paths in the list file correctly.
**How to avoid:** Always write forward slashes in the concat list: `path.replace(chr(92), '/')`. Verified: `C:/Users/.../scene_00.mp4` works; `C:\Users\...\scene_00.mp4` does not.
**Warning signs:** FFmpeg errors on concat with "No such file or directory" for a path that definitely exists.

### Pitfall 4: `-shortest` vs `-t duration` for loop+audio
**What goes wrong:** Using `-shortest` with `-loop 1` and an audio input should theoretically stop at audio end, but in practice can produce clips that are 1-2 frames shorter than the audio, causing a tiny audio cutoff at the last clip.
**Why it happens:** `-shortest` stops at the first stream's end; timing boundary conditions differ by build version.
**How to avoid:** Use `-t str(duration)` explicitly (duration from ffprobe) instead of `-shortest`. Verified working.
**Warning signs:** Last second of audio cut off in final clip.

### Pitfall 5: concat `-c copy` with zoompan-encoded clips emits DTS warnings
**What goes wrong:** FFmpeg emits `Non-monotonic DTS; previous: X, current: Y; changing to Z` during concat.
**Why it happens:** AAC audio timestamps don't perfectly align at clip boundaries in the MP4 container when stream-copying. This is a known, benign artifact of AAC priming frames.
**How to avoid:** No action needed — this warning is cosmetic. The output file is valid and plays correctly. Duration is accurate (verified).
**Warning signs:** Only a warning, not an error. returncode is 0. If you see returncode != 0 on concat, that's a different issue (usually a path problem).

### Pitfall 6: episode_dir not set before render()
**What goes wrong:** `self.episode_dir` is `""` if `generate_script()` was never called (or `run()` is called fresh without a prior script step).
**Why it happens:** The Podcast instance is stateful — episode_dir is set by generate_script().
**How to avoid:** Guard at top of `render()`: `if not self.episode_dir: raise ValueError(...)`. Already the pattern used in `generate_assets()`.

---

## Validation Architecture

`nyquist_validation` is `false` in `.planning/config.json` — validation section is SKIPPED per config.

**Manual validation commands for the implementer:**

```bash
# Verify a single scene clip rendered correctly
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 \
  ".mp/podcast_<slug>/scene_00.mp4"
# Expected: duration near WAV duration, size > 0

# Verify final.mp4 duration is sum of all clips (8-10 minutes)
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \
  ".mp/podcast_<slug>/final.mp4"
# Expected: 480–600 (8–10 minutes in seconds)

# Quick playback check (Windows)
start .mp/podcast_<slug>/final.mp4
```

**Post-render assertions in code:**

```python
# After render(), verify final.mp4 exists and is non-empty
assert os.path.exists(final_path), f"final.mp4 not found at {final_path}"
assert os.path.getsize(final_path) > 1_000_000, "final.mp4 suspiciously small (<1MB)"
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| ffmpeg | All rendering | Yes | 2025-06-17 build | None — blocking |
| ffprobe | Audio duration detection | Yes | 2025-06-17 build | None — blocking |
| libx264 | Video codec | Yes | Confirmed in build flags | None |
| aac | Audio codec | Yes | Confirmed in build flags | None |

Both `ffmpeg` and `ffprobe` are confirmed on PATH (resolved from `C:\ffmpeg\bin\`). No installation step needed.

---

## Sources

### Primary (HIGH confidence — verified by direct execution)
- FFmpeg on target machine (`ffmpeg -version`) — zoompan filter, libx264, aac confirmed in this build
- ffprobe duration extraction — tested on real `.wav` files in `.mp/`, output format confirmed
- zoompan zoom-in filter — tested on real 768×1344 PNG + 20.64s WAV, produced valid 14MB MP4
- zoompan zoom-out filter — tested on same assets, produced valid 14MB MP4
- concat demuxer — tested with 2 clips (both relative and absolute paths), confirmed Windows forward-slash path requirement
- Python subprocess patterns — tested full pipeline end-to-end from Python, `check=True` with Windows paths confirmed working
- Preset timing — `ultrafast` (2.4s, 14MB/clip) vs `fast` (3.7s, 2.8MB/clip) benchmarked on target machine

### Secondary (MEDIUM confidence — code reading)
- `src/classes/Tts.py` subprocess pattern — established codebase FFmpeg invocation style
- `src/classes/YouTube._add_srt_via_ffmpeg` — established error handling pattern
- `src/test_ken_burns.py` — prior Ken Burns implementation (MoviePy-based, not FFmpeg zoompan)
- Phase 6 SUMMARY.md — asset naming convention (`scene_00.png` / `scene_00.wav` through `scene_13.*`)
- `config.json` `nanobanana2_aspect_ratio: "9:16"` — confirms source PNG is 9:16 format, actual dimensions 768×1344

---

## Metadata

**Confidence breakdown:**
- zoompan syntax: HIGH — executed and verified on target machine with real assets
- ffprobe duration extraction: HIGH — executed and verified
- concat demuxer: HIGH — executed and verified; Windows path requirement confirmed
- Subprocess patterns: HIGH — consistent with existing codebase patterns, verified end-to-end
- Duration estimate (REND-03): MEDIUM — based on edge-tts at -20% rate typical output; actual duration depends on narration text length

**Research date:** 2026-04-02
**Valid until:** 2026-07-02 (90 days — FFmpeg filter syntax is very stable)

---

## RESEARCH COMPLETE
