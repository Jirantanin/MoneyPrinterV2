# Technical paths for "Claude makes a video" (state as of 2026-10-14)

## 1. claude.ai (web/desktop/mobile) with code execution / file creation and no connectors: can Claude render .mp4/.gif? Is ffmpeg there? What are the sandbox limits? Can it make audio?

### Takeaway
GIFs: yes, with zero setup. Claude can draw frames with Pillow or matplotlib in the claude.ai sandbox, and Anthropic's own GIF skill works this way. MP4: plausible but not documented. Anthropic never says whether ffmpeg is preinstalled in the claude.ai sandbox. On Free/Pro/Max, though, the sandbox can install packages from PyPI/npm/Ubuntu archives by default, so Claude can probably pull in an encoder itself (not verified). Real narration or music can't be made without an outside TTS/audio service: Claude has no speech or audio model, and the network allowlist blocks TTS APIs.

### Cited Findings
- **Who has it, and where:** Code execution and file creation are "available to all Claude users (Free, Pro, Max, Team, and Enterprise)" on web, Claude Desktop and Claude Mobile (iOS and Android). — [Claude Help Center: Create and edit files with Claude](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)
- **Documented output types:** .xlsx, .pptx, .docx, PDF, PNG images for data visualizations, Python scripts, and artifacts (HTML/React, Markdown, Mermaid, SVG). Video, audio, MP4, ffmpeg and fonts are never mentioned. GIFs come up once, in the FAQ, as "fun tasks like gif-creation." — [Help Center 12111783](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)
- **File size cap:** "The maximum file size is 30MB per file for both uploads and downloads." — [Help Center 12111783](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude). Simon Willison noted that ChatGPT's limit is 512MB by comparison. — [Simon Willison, Sep 9 2025](https://simonwillison.net/2025/Sep/9/claude-code-interpreter)
- **Runtime and resources:** The Help Center gives no numbers. It says network, container and storage resources are "intentionally limited," and that Anthropic has "Limited the duration of tasks that can be completed by Claude and the length of time you can use a single sandbox container." — [Help Center 12111783](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)
- **Network defaults by plan:**
  - Free/Pro/Max: network access is on by default, so packages can be installed from approved sources.
  - Enterprise: off by default for new organizations. Owners can choose package managers only, a domain allowlist, or all domains.
  - Team: the article contradicts itself, saying both "disabled by default" and "package managers only."
  - Approved domains: Anthropic services, GitHub, npm, PyPI, crates.io, Ubuntu archives, Yarn.

  — [Help Center 12111783](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)
- **What Simon Willison observed in Sep 2025 (over a year old):**
  - System: Ubuntu 24.04.2 LTS, x86_64, about 9.0GB RAM, about 4.9GB disk, Claude running as root in `/home/claude`.
  - Languages: Bash 5.2.21, Python 3.12.3 with pip, Node.js v18.19.1.
  - Network: egress goes through an Envoy proxy with a strict allowlist. Requests to google.com and httpbin.org returned 403.
  - Installs: `pip install sqlite-utils` worked.
  - Not mentioned: ffmpeg, ImageMagick and fonts.

  — [Simon Willison, "Claude's new Code Interpreter"](https://simonwillison.net/2025/Sep/9/claude-code-interpreter)
- **Anthropic's own GIF skill:** `slack-gif-creator` in anthropics/skills uses Pillow (plus imageio and numpy) with a `GIFBuilder` class. It recommends 128x128 for emoji GIFs and 480x480 for message GIFs, 10–30 fps, 48–128 colors, and under 3 s for emoji. It doesn't mention ffmpeg, and it says "Don't use: Emoji fonts (unreliable across platforms)." — [anthropics/skills slack-gif-creator SKILL.md](https://raw.githubusercontent.com/anthropics/skills/main/skills/slack-gif-creator/SKILL.md)
- **No official ffmpeg confirmation:** No official or reliable source confirms ffmpeg in the claude.ai sandbox. Search results suggest checking with `which ffmpeg && ffmpeg -version`. — [search synthesis; no primary source found]. A third-party explainer says Claude "cannot generate video footage" and renders MP4 "through Claude Code with Remotion or FFmpeg," which points to local execution, not claude.ai. — [ScreenApp: Can Claude Create Videos?](https://screenapp.io/blog/can-claude-create-videos)
- **No image or audio generation:** "Claude is an image understanding model only… it cannot generate, produce, edit, manipulate, or create images" (generative pixels; images drawn by code are a separate thing). — [Claude Docs: Vision FAQ](https://platform.claude.com/docs/en/build-with-claude/vision)

### Inferences
- **GIF is a confirmed zero-setup path in claude.ai.** Pillow-drawn frames, or matplotlib's `PillowWriter`, need no ffmpeg. Anthropic ships a skill for exactly this, and its FAQ names "gif-creation."
- **MP4 is likely zero-setup on Free/Pro/Max, but unverified.** Even if ffmpeg isn't preinstalled, Claude can probably fetch a static binary:
  - `pip install imageio-ffmpeg` or `moviepy` from PyPI, or
  - `apt-get install ffmpeg` from the allowlisted Ubuntu archives (Claude runs as root).

  This is an inference from the allowlist and root access. Nobody has tested it in a source I found. On Team/Enterprise orgs with egress off, MP4 depends on whether ffmpeg ships in the image, which is unknown.
- **The 30MB download cap makes claude.ai short-clip territory.** A 1080p H.264 file at about 5 Mbps hits 30MB in roughly 48 s. That's arithmetic, not a measured limit.
- **Headless-browser recording of HTML (Playwright/Puppeteer) will probably fail in the claude.ai sandbox.** Both download browser binaries from CDNs (Playwright CDN, storage.googleapis.com) that aren't on the allowlist. This is an inference, not tested.
- **Thai fonts:** not documented anywhere. If none are installed, Thai text drawn with Pillow or matplotlib renders as tofu boxes. Claude could try fetching a font file from GitHub (allowlisted), e.g., Noto Sans Thai from a GitHub repo. Inference.
- **Audio without a TTS service:**
  - Claude can synthesize tones, beeps, simple procedural music or SFX with numpy and write WAV files. This is plain DSP, not a voice.
  - Offline TTS packages (espeak-ng via apt, Piper via pip) might install, but neural voice models usually download from Hugging Face, which isn't allowlisted.
  - Thai quality from espeak-type engines is robotic.

  All inference. No source tested TTS in the claude.ai sandbox.

### Gaps
- **Image contents:** no official list of preinstalled packages or binaries for the claude.ai sandbox, and no confirmation either way on ffmpeg, ImageMagick, fonts, Thai fonts or LibreOffice.
- **Runtime limits:** no published per-command or per-task time limit for claude.ai (only "limited").
- **Environment drift:** Simon Willison's environment details date from Sep 2025, and the Python/Node versions and RAM may have changed.
- **No 2026 test of MP4 or audio in claude.ai:** I found no 2026 first-hand blog post that rendered an MP4, or produced any audio, inside claude.ai (as opposed to Claude Code).

## 2. Can Claude Artifacts (HTML/JS/canvas/SVG/CSS animation) serve as "video", and can they be exported to a real video file without extra tools?

### Takeaway
An artifact can play an animation in the browser (HTML/CSS/JS/canvas/SVG), but it is a live web page, not a video file, and there's no built-in "export as MP4" for artifacts. With no extra tools, the closest path is code inside the artifact: canvas `captureStream()` plus `MediaRecorder`, which produces a WebM the user downloads. That works only if the artifact iframe allows downloads, and the WebM often lacks duration metadata. Claude Design, a separate claude.ai surface, officially lists no video export, though some third parties claim one.

### Cited Findings
- **Artifact types:** the Help Center's creatable artifacts include "HTML or React apps, Markdown, Mermaid diagrams, and SVGs." No video export is listed. — [Help Center 12111783](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude)
- **The standard browser recording pattern:** `canvas.captureStream(fps)` → `MediaRecorder` with `video/webm` → Blob → download via `<a download>`. — [Theodo: Saving canvas animations](https://blog.theodo.com/2023/03/saving-canvas-animations); [canvas-record README](https://cdn.jsdelivr.net/npm/canvas-record@5.5.1/README.md)
- **Pitfalls of that pattern:**
  - Downloads inside an iframe may be blocked.
  - `codecs=h264` isn't universally supported in WebM, so vp9 is the safer choice.
  - MediaRecorder WebM often lacks duration/seek metadata, and remuxing with ffmpeg.wasm fixes it.
  - Frame-stepped rendering beats wall-clock recording for smoothness.

  — [Theodo](https://blog.theodo.com/2023/03/saving-canvas-animations); [DEV: Turn an animated SVG into a video file](https://dev.to/lenra/turn-an-animated-svg-into-a-video-file-p49)
- **Claude Design exports (official):** .zip, PDF, PPTX, Google Slides, standalone HTML, sends to Canva, Miro, Netlify, Vercel, etc., and "Handoff to Claude Code." The article never mentions video, MP4, animation or motion. Claude Design is on Free/Pro/Max/Team/Enterprise. — [Help Center: Get started with Claude Design](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- **Conflicting claims on Claude Design MP4 export:**
  - Third-party tutorials and a browser-extension listing claim the Share menu has a "Video (.mp4)" export. — [xray.tech: animations with Claude Design](https://www.xray.tech/post/build-fluid-on-brand-animations-with-claude-design); [Contra: Quick Video Export for Claude Design](https://contra.com/community/axi0DpBJ-quick-video-export-for-claude-design)
  - A May 2026 guide says there is no native MP4 export. — [notebooklm-guide.com](https://notebooklm-guide.com/notebooklm-claude-design-video-export/)
  - The official help article lists no video format.
- **Open-source "Claude Video Export" CLI:** turns a Stage-based Claude Design project into a silent 4K/60fps H.264 MP4 by rendering frames in headless Chromium and encoding with bundled `ffmpeg-static`. It needs Node 18+ and `npx playwright install chromium` (~500MB), and can mux a voiceover file. This is a local tool. — [GitHub: dawoodtrumboo/claude-video-export](https://github.com/dawoodtrumboo/claude-video-export)

### Inferences
- **For a deliverable .mp4 file, an artifact is a preview or storyboard medium, not a render target.**
  - Zero-setup option: WebM via MediaRecorder, if the iframe permits download. Quality and timing depend on the viewer's machine, and it records in real time, not deterministic frame-by-frame.
  - Deterministic option: export the HTML and render locally with headless Chrome + ffmpeg (Claude Code, HyperFrames, Remotion), or use a connector (section 5).
- **Claude Design MP4 export:** treat as unverified/possibly-gated until checked in-app, since the official docs and third parties disagree.
- **A related surface observed in this environment:** the Claude in Chrome extension exposes a `gif_creator` tool (GIF recordings of browser actions). That's a GIF of browsing, not an authored video. (Observation from the tool list in this Claude Code session; no public doc fetched.)

### Gaps
- No official Anthropic statement on whether claude.ai artifact iframes allow programmatic downloads (Blob/`<a download>`) or `MediaRecorder` in 2026.
- Couldn't confirm Claude Design's MP4 export from a primary source.

## 3. Claude Code (local CLI/desktop): common pipelines (Remotion, Manim, Motion Canvas, HTML-to-video, ffmpeg). What must be installed, and what are the licensing gotchas?

### Takeaway
Claude Code is the main, best-documented path to real MP4s. Claude writes code (React/Remotion, HTML+GSAP/HyperFrames, Python/Manim, or raw ffmpeg commands) and runs the renderer on the user's machine. The user has to install the toolchain locally: Node and a headless Chrome for the browser-based renderers, Python for Manim, and ffmpeg for some tools. The big licensing gotcha is Remotion: it's free only for individuals, non-profits and for-profit companies of up to 3 employees, and paid otherwise. HyperFrames (Apache-2.0) and Manim (MIT) don't have that restriction.

### Cited Findings
- **Remotion Agent Skills (official):**
  - Install with `npx skills add remotion-dev/skills`, or opt in during `bun create video`.
  - Skills: `/remotion-best-practices`, `/remotion-create`, `/remotion-markup`, `/remotion-studio`, `/remotion-render`, `/remotion-maps`, `/remotion-captions`, `/remotion-saas`, `/remotion-interactivity`, `/remotion-docs`, `/remotion-upgrade`, `/remotion-multimedia`.
  - Remotion says they work with "AI agents like Claude Code, Codex, Kimi Code or Cursor."

  — [Remotion docs: AI skills](https://www.remotion.dev/docs/ai/skills)
- **Install command conflicts:**
  - A Tella tutorial uses `npx create-video --yes --blank my-video` → `npx remotion skills add`. — [Tella blog](https://www.tella.com/blog/how-to-use-remotion-agent-skills-with-claude-code)
  - A Portuguese guide mentions a `remotion-dev/claude-code-plugin` marketplace plugin. Unverified against Remotion's own docs. — [horadecodar.com.br](https://horadecodar.com.br/?p=44180)
- **Remotion system requirements:**
  - Since v4, FFmpeg/FFprobe don't need separate installation; Remotion bundles them (`npx remotion ffmpeg`), limited to H.264, H.265, VP8, VP9 and ProRes. — [Remotion v4.0 migration](https://www.remotion.dev/docs/4-0-migration)
  - Remotion auto-installs "Chrome Headless Shell" into node_modules. Linux x64 needs extra system libraries. — [Remotion: Chrome Headless Shell](https://www.remotion.dev/docs/miscellaneous/chrome-headless-shell)
  - Minimum Node version: not found in an official page. Third-party sources say Node 18+ or Node 20+. — [search synthesis; conflicting, unofficial]
- **Remotion license:** the free license covers "an individual," "a for-profit organization with up to 3 employees," "a non-profit or not-for-profit organization," or anyone "evaluating whether Remotion is a good fit, and are not yet using it in a commercial way." Everyone else needs a Company License. The license file is © 2026 and notes "In Remotion 5.0, the license will slightly change." — [Remotion LICENSE.md](https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md)
- **Remotion pricing (via search summary of the official pages; the page itself didn't render for me):**
  - Creators: $25/mo per seat.
  - Automators: $0.01 per render, $100/mo minimum; meant for products that render automatically (prompt-to-video apps, etc.).
  - Enterprise: from $500/mo.

  — [remotion.dev/docs/license/pricing (search summary)](https://www.remotion.dev/docs/license/pricing); [companies.remotion.dev](https://companies.remotion.dev/license). Treat the numbers as needing confirmation on the live page.
- **HyperFrames (HeyGen):**
  - Apache-2.0, open source, turns HTML/CSS/media plus seekable animations (GSAP, Lottie, Three.js) into deterministic MP4.
  - Launched about April 17, 2026. Requires Node.js ≥ 22 and FFmpeg.
  - Skills install with `npx skills add heygen-com/hyperframes`, giving the `/hyperframes`, `/hyperframes-cli` and `/gsap` commands.

  — [Noqta: HeyGen HyperFrames](https://www.noqta.tn/en/blog/heygen-hyperframes-html-to-mp4-ai-agent-video-2026); [silenceper.com](https://silenceper.com/en/article/2026-05-02-hyperframes-html-video-rendering/); [themenonlab.blog](https://themenonlab.blog/blog/hyperframes-claude-code-writes-renders-videos)
- **HyperFrames in practice:** tutorials pair Claude Code + HyperFrames with ElevenLabs for narration. — [MindStudio](https://www.mindstudio.ai/blog/ai-video-generation-claude-code-hyperframes-elevenlabs)
- **Manim Community v0.19.0 (Jan 2025):** replaced the external FFmpeg dependency with PyAV, whose wheels bundle FFmpeg, so a separate FFmpeg CLI install isn't needed. LaTeX stays optional (only for equations); MiKTeX is suggested on Windows. — [Manim 0.19.0 changelog](https://docs.manim.community/en/stable/changelog/0.19.0-changelog.html); [Manim Windows install docs](https://docs.manim.community/en/stable/installation/windows.html)
- **Generic ffmpeg + Claude Code:** community skills such as `claude-ffmpeg-skill` assume ffmpeg is installed on the user's system. — [GitHub: ychoi-kr/claude-ffmpeg-skill](https://github.com/ychoi-kr/claude-ffmpeg-skill). A general pattern: an HTML/canvas page draws each time t, headless Chrome screenshots each frame, and ffmpeg encodes MP4. — [Vincent Schmalbach: How to make videos with Claude Code](https://www.vincentschmalbach.com/how-to-make-videos-with-claude-code/)
- **Local working example (this repo):** MoneyPrinterV2 runs a production Thai-documentary pipeline under Claude Code:
  - Default renderer: `src/producer_minimal_renderer.py` + `doc_renderer/`.
  - Optional Remotion compositions: `VideoPodcast.tsx`, `ClipShort.tsx`.
  - Narration: Gemini TTS (`src/classes/Tts.py`).
  - Procedural score/SFX generated in Python (`src/producer_score.py`, `src/producer_sfx_synth.py`).

  — [local: MoneyPrinterV2/CLAUDE.md](C:/Users/66984/workspace-coding/MoneyPrinterV2/CLAUDE.md)

### Inferences
- **What to install, by pipeline:**
  - Remotion: Node + npm/bun. Chrome Headless Shell and ffmpeg are auto-handled.
  - HyperFrames: Node ≥22 + FFmpeg.
  - Manim CE: Python + `pip/uv install manim` (bundled ffmpeg via PyAV), plus LaTeX optional and Cairo/Pango system libs on some OSes.
  - Motion Canvas: Node (I didn't research its specifics; see Gaps).
  - Raw pipelines: ffmpeg on PATH plus Python libs (Pillow, moviepy).
- **All of these are "needs local install."** None needs an external API unless you want voice or generative footage.
- **Commercial channels must decide on Remotion licensing.** A one-person or ≤3-employee channel qualifies as free. A company over 3 employees, or a product that auto-renders for others (Automators tier), needs a paid license. HyperFrames and Manim avoid this.
- **Thai text works locally** whenever the renderer uses system or web fonts with Thai coverage (Chrome-based renderers handle Thai shaping well). Pillow/matplotlib need an explicit Thai TTF. Inference from general font behavior, consistent with the local repo's practice.

### Gaps
- No official minimum Node version for Remotion v4 (third-party claims conflict: 18+ vs 20+).
- I didn't research Motion Canvas install specifics or its maintenance status in 2026.
- Couldn't fetch the live Remotion pricing table directly. The prices come from a search summary of the official page.
- The size and contents of Remotion 5.0's license change weren't checked.

## 4. Via the Claude API (code execution tool, Files API, Skills): can a developer get a rendered video back purely through the API?

### Takeaway
Partly. The API code execution container returns any file Claude writes to `$OUTPUT_DIR` as a `file_id`, downloadable through the Files API, so an animated GIF from matplotlib/Pillow comes back purely through the API. MP4 is doubtful with the stock container: it has no internet access, packages can't be installed, and ffmpeg isn't among the listed tools. This sandbox is more locked down than claude.ai's.

### Cited Findings
- **Container specs:**
  - Python 3.11, Linux x86_64.
  - 5 GiB RAM, 5 GiB disk, 1 CPU.
  - A tool invocation that runs too long returns `execution_time_exceeded`. With programmatic tool calling, each REPL cell has a 90-second wall-clock limit.

  — [Claude Docs: Code execution tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- **No network:** "Internet access: Completely disabled for security… No outbound network requests permitted," and "Claude can't download or install additional packages at runtime: only the pre-installed libraries are available." — [Code execution tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- **Preinstalled libraries:**
  - Python: pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, seaborn, pyarrow, openpyxl, xlsxwriter, xlrd, pillow, python-pptx, python-docx, pypdf, pdfplumber, pypdfium2, pdf2image, pdfkit, tabula-py, reportlab[pycairo], img2pdf, sympy, mpmath, tqdm, python-dateutil, pytz, joblib.
  - CLI tools: unzip, unrar, 7zip, bc, rg, fd, sqlite.
  - ffmpeg, moviepy, imageio and any TTS library are not listed.

  — [Code execution tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- **Getting files back:** "Each `bash_code_execution` call gets a new, empty directory, available to the command as `$OUTPUT_DIR`… files at the top level of that directory are captured and returned as the `file_id` entries," downloadable with `client.files.download(file_id)`. — [Code execution tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- **C2PA credentials:** image, video and audio files that Claude produces in the sandbox carry C2PA Content Credentials when downloaded via the Files API. Supported signing formats include GIF, MP4, MOV, MP3, WAV, FLAC and M4A. — [Code execution tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- **Versions and pricing:**
  - Tool versions are `code_execution_20250825` (Bash + files), `_20260120` (REPL persistence + programmatic tool calling) and `_20260521` (latest). None needs a beta header.
  - Containers expire 30 days after creation and are checkpointed after about 5 minutes idle.
  - 1,550 free container-hours per org per month, then $0.05/hour per container, with a 5-minute minimum. Free when used alongside web_search/web_fetch `_20260209`+.

  — [Code execution tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)

### Inferences
- **Through the API alone with the stock container:**
  - **Animated GIF works:** matplotlib `FuncAnimation` + `PillowWriter`, or Pillow `save(..., save_all=True)`.
  - **Silent WAV works:** numpy + Python's `wave` stdlib.
  - **MP4 is not expected to work:** no ffmpeg listed, no network to install it. The C2PA list naming MP4/MOV/MP3 says what gets signed if produced, not that an encoder exists.
- **Possible workarounds (unverified):**
  - Upload a static ffmpeg binary as a file through the Files API and run it in the container. The docs only say the Python environment "can process" uploaded files, so this is untested and may be restricted.
  - Ship ffmpeg inside a custom Agent Skill. I didn't verify size limits for skill uploads.
- **The practical developer pattern:** Claude (API) writes the composition code or JSON, and the developer's own server or a render service (Remotion Lambda/Cloud Run, HyperFrames CLI, ffmpeg) does the actual rendering. That's "needs your own infrastructure," not pure API.
- **No outbound network** means the API container can't call TTS or video-generation APIs. Audio and footage have to be generated outside and uploaded, or fetched by the developer's own tool calls.

### Gaps
- Didn't verify whether ffmpeg is present but undocumented in the API container. The docs list "command-line tools such as…", which is not necessarily exhaustive.
- Didn't research Agent Skills API upload limits (max bundle size, whether binaries are allowed) or whether "Managed Agents" (server-hosted agents with a managed sandbox) have a different, network-enabled environment that could render MP4.
- No exact maximum execution time per tool invocation is published (only the error code).

## 5. What Claude cannot do natively (photoreal footage, voice/music, lip-sync), and which external services people pair it with via MCP/API

### Takeaway
Claude produces text and code. It can't generate photoreal pixels, video footage, voice, music or lip-sync. Everything in a Claude-made video is either drawn by code (charts, motion graphics, text, procedural audio) or comes from an external generator. In 2026 those generators plug in as claude.ai connectors (remote MCP with OAuth) or as local MCP/API calls from Claude Code:
- **Footage:** HeyGen, Runway, Higgsfield (which aggregates Veo/Kling/etc.), HyperFrames.
- **Voice/SFX:** ElevenLabs.
- **TTS:** Gemini TTS via API.

### Cited Findings
- **No generative imagery:** "Claude is an image understanding model only… it cannot generate, produce, edit, manipulate, or create images." — [Claude Docs: Vision](https://platform.claude.com/docs/en/build-with-claude/vision). Claude "cannot generate video footage"; it writes scripts, storyboards and per-scene prompts, codes SVG/CSS animations, and renders MP4 via Remotion/FFmpeg. — [ScreenApp](https://screenapp.io/blog/can-claude-create-videos)
- **HyperFrames by HeyGen connector:**
  - Listed in Claude's connector directory as a remote MCP (`https://mcp.heygen.com/mcp/hyperframes`), "Added June 2026," "Anthropic verified," sign-in required.
  - Tools: `compose` and `render_video`.
  - The listing doesn't state the output format, pricing or limits.

  — [claude.com/connectors/hyperframes-heygen](https://claude.com/connectors/hyperframes-heygen)
- **HeyGen avatar connector:**
  - Claude "writes the script, calls HeyGen's video tools via MCP, monitors rendering, and returns a shareable link." It can re-render in "175+ languages with HeyGen's lip-sync translation" (Thai not specifically confirmed).
  - claude.ai/Desktop: add from Connectors via OAuth, "No API key needed." Claude Code: skills package + `HEYGEN_API_KEY`.
  - Uses "your existing premium credit balance."

  — [HeyGen x Claude](https://www.heygen.com/integrations/claude)
- **Runway hosted MCP:** reportedly brings Gen-4.5, Seedance 2.5, Veo 3.1, Kling, etc. into Claude without an API key. — [hermes-ai.net (third-party news)](https://hermes-ai.net/news/runway-brings-ai-video-and-image-generation-directly-into-claude/); not verified against Runway's own docs.
- **Higgsfield connector:** added as a custom connector in claude.ai Settings → Connectors with a Higgsfield login. Gives access to many video models (reportedly 30+, incl. Kling, Runway Gen-4, Veo 3, Minimax), credit-based. — [Higgsfield: Claude AI video generator](https://higgsfield.ai/claude-ai-video-generator); [agent-signal.ai comparison](https://agent-signal.ai/en/blog/claude-video-generation-workflows). Third-party/vendor sources.
- **ElevenLabs MCP (official `elevenlabs/elevenlabs-mcp`):**
  - Covers TTS (voice, stability, speed, style), transcription, voice cloning/design, sound effects and agents.
  - Setup: API key + `uvx elevenlabs-mcp` in `claude_desktop_config.json`. Free tier is about 10k credits/month.
  - One directory lists `npx -y @elevenlabs/mcp` as an alternative install.

  — [Glama: ElevenLabs MCP](https://glama.ai/mcp/servers/elevenlabs/elevenlabs-mcp); [mcpservers.org](https://mcpservers.org/fr/servers/elevenlabs/elevenlabs-mcp). Directory sources; I didn't fetch the GitHub README directly.
- **Veo has no standalone Claude connector** in what I found; people reach it through Higgsfield or Runway. — [search synthesis of vibetoolstack.com / agent-signal.ai](https://vibetoolstack.com/blog/best-claude-creative-connectors)
- **Gemini TTS in a working pipeline:** this repo calls Gemini TTS directly from Python as the narration engine in a Claude Code-driven pipeline. — [local: MoneyPrinterV2/CLAUDE.md](C:/Users/66984/workspace-coding/MoneyPrinterV2/CLAUDE.md)

### Inferences

**Path classification summary for the report writer:**

| Path | Output | Setup class |
|---|---|---|
| claude.ai sandbox: Pillow/matplotlib GIF | Animated GIF ≤30MB | Zero setup in claude.ai |
| claude.ai sandbox: MP4 via ffmpeg | MP4 ≤30MB | Probably zero setup on Free/Pro/Max (self-install from PyPI/apt); unverified; may fail on Team/Enterprise with egress off |
| claude.ai Artifact: live animation | Playable HTML page, no file | Zero setup |
| claude.ai Artifact: MediaRecorder → WebM | WebM | Zero setup, if the iframe permits download; unverified |
| Claude Design: MP4 export | MP4? | Disputed; official docs list no video export |
| claude.ai + connectors | Hosted video (HyperFrames/HeyGen render, HeyGen avatars, Runway/Higgsfield generative clips) | Needs external connector + account/credits |
| API code execution | GIF/WAV via `$OUTPUT_DIR` + Files API; MP4 not expected (no ffmpeg, no network) | Zero setup for GIF |
| Claude Code + Remotion / HyperFrames / Manim / ffmpeg | Full-length MP4 with any audio you supply | Needs local install; Remotion license if company >3 employees |
| Voice / music / lip-sync | Voice (ElevenLabs MCP, Gemini TTS API), lip-sync avatars (HeyGen) | Needs external API/MCP; code can only make procedural tones/SFX/music beds |

- **A complete narrated explainer video today** typically means: Claude Code (script + composition code + render) + a TTS API/MCP + optionally a footage generator. claude.ai alone tops out at short silent GIFs/MP4s or connector-hosted renders.

### Gaps
- Didn't confirm official Runway or Higgsfield connector pages on claude.com/connectors (only third-party and vendor pages).
- No sources on Sora, Kling or Veo direct MCP servers from the vendors themselves.
- Pricing per minute for HeyGen, Runway and Higgsfield through Claude isn't captured.
- Thai language/voice support across these services isn't verified.

## 6. Can Claude watch/understand video as input (for self-review of renders)?

### Takeaway
No native video input. Claude reads still images only, and for animated GIFs only the first frame. Self-review of a render means extracting frames (ffmpeg) and sending them as multiple images, plus a separate transcript or audio check, since Claude can't hear audio.

### Cited Findings
- **Formats:** "Claude supports JPEG, PNG, GIF, and WebP images… Animations are unsupported, and only the first frame is used." — [Claude Docs: Vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Limits:**
  - Up to 20 images per message on claude.ai; 100 per API request for 200k-context models, 600 for others.
  - Max 8000x8000 px per image, or 2000 px per side when a request has more than 20 images.
  - 10 MB per image; 32 MB request size limit.

  — [Claude Docs: Vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Resolution:** Claude 4.7+ models use a high-resolution tier (2576 px long edge, 4784 visual tokens); a 1920x1080 frame isn't resized there and costs about 2691 tokens. — [Claude Docs: Vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Third-party agreement:** blogs agree there's no native video input as of mid/late 2026. Common workarounds are ffmpeg frame extraction + transcripts, or plugins (e.g., claude-video-vision) that use Gemini or Whisper for audio. — [animspec.com](https://animspec.com/blog/can-claude-watch-videos); [screenapp.io](https://screenapp.io/blog/can-claude-watch-videos); [GitHub: fabriqaai/ffmpeg-analyse-video-skill](https://github.com/fabriqaai/ffmpeg-analyse-video-skill)

### Inferences
- **Self-review is feasible but sampled.** A contact sheet or a few dozen keyframes per render fits within limits; everything between sampled frames is missed (motion smoothness, flicker, A/V sync).
- **Audio review needs a separate tool:** transcription (Whisper/Gemini) or loudness analysis via ffmpeg. Claude can read the numeric output but can't listen.

### Gaps
- No Anthropic roadmap statement on native video or audio input was found.
