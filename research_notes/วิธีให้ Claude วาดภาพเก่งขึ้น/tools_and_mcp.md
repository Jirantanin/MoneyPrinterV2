# Tools and MCP servers for agent-made flat vector explainer art (Claude Code on Windows, 2025–2026)

Research date: 2026-10-26. About 18 tool calls. Most pricing figures come from third-party aggregators and conflict with each other; primary sources are marked where used. Local checks were run on this machine (VectorCraft / EffectCraft installs).

## Image-generation models that output vector or flat art (Recraft, Ideogram, FLUX/Kontext, gpt-image, Imagen/Nano Banana)

### Takeaway
Recraft is the only mainstream model with native SVG output. It also has an official MCP server with generate, vectorize and custom-style tools, so it fits an HTML/SVG pipeline best. Nano Banana Pro (Gemini 3 Pro Image) is the most-cited option for keeping a character consistent across images, but it outputs raster only, so its frames would need tracing. Commercial rights depend on plan or licence: Recraft's free plan gives none, and FLUX dev open weights run locally are non-commercial unless BFL licenses them.

### Cited Findings
**Recraft (V3 / V4 / V4.1)**
- Recraft V4 Vector returns SVG at 1:1, 4:3, 3:4, 16:9 and **9:16**, up to 6 images per request. OpenRouter lists it at $0.08/image, released 2026-05-13 — [OpenRouter](https://openrouter.ai/recraft/recraft-v4-vector)
- There is also a V4.1 Pro Vector variant — [OpenRouter](https://openrouter.ai/recraft/recraft-v4.1-pro-vector)
- Invideo, citing Recraft's docs as of Aug 2026, lists V4.1 at $0.035/image and V4.1 Pro at $0.21/image after price cuts on 2026-06-20. This conflicts with OpenRouter's $0.08 for V4.1 Vector, and it is unclear whether Invideo's figures are for raster or vector — [Invideo](https://invideo.io/blog/recraft-ai-image-generator/); [OpenRouter V4.1](https://api3.shopot.ai/recraft/recraft-v4.1-vector)
- Recraft's official pricing page says: **Free plan → Recraft owns the images, they are public in the community gallery, and they are not licensed for commercial use. Paid plans → you own the images and have commercial rights while subscribed, which still applies after cancellation.** API use is billed in prepaid, non-expiring "API Units", and V2, V3, V4 and V4.1 are all on the API — [Recraft pricing](https://www.recraft.ai/pricing)
- **Official Recraft MCP server**: a hosted remote server at `https://mcp.recraft.ai/mcp`, or local via npm `@recraft-ai/mcp-recraft-server` (MIT). Tools include `generate_image` (raster or vector, with style/size/model options), `vectorize_image` (raster→SVG, ~$0.01/call), image-to-image editing, **custom style creation**, background removal/replacement, upscaling and balance check. The npm page gives ~$0.04 raster / $0.08 vector per image (may be stale). It needs a Recraft API key — [Recraft MCP docs](https://recraft.ai/docs/mcp-reference/getting-started); [npm package](https://classic.yarnpkg.com/en/package/@recraft-ai/mcp-recraft-server)
- One 2026 comparison names Recraft V4.1's strength as "logos and vector art" — [Coverr 2026](https://coverr.co/blog/ai-image-generator-for-creators-2026)

**Google Nano Banana Pro (Gemini 3 Pro Image)**
- About $0.134/image at 1K/2K and $0.24 at 4K on the Gemini API. Reference images are charged separately at about $0.067 each, and there is no free tier for the Pro image models. Fal.ai charges $0.15 — [myarchitectai](https://www.myarchitectai.com/blog/nano-banana-api-pricing); [benchlm](https://benchlm.ai/media-pricing/nano-banana); [pricepertoken](https://pricepertoken.com/pricing-page/model/google-gemini-3-pro-image-preview)
- 2026 creator guides say it holds character consistency across many images better than most competitors — [Coverr 2026](https://coverr.co/blog/ai-image-generator-for-creators-2026); [Picsart](https://picsart.com/blog/?p=259498)

**OpenAI GPT Image**
- Described as "the strongest general-purpose option for editorial and storytelling", with strong prompt accuracy, but not the leader on consistency — [Coverr 2026](https://coverr.co/blog/ai-image-generator-for-creators-2026)

**FLUX (Black Forest Labs)**
- Images generated through the BFL API carry full commercial usage rights. **Local FLUX.1 Kontext [dev] weights are under the FLUX Non-Commercial licence**, and commercial use needs a licence from bfl.ai/licensing — [BFL help](https://help.bfl.ai/articles/3670520907-can-i-use-the-api-for-a-commercial-application); [BFL Kontext dev blog](https://bfl.ai/blog/flux-1-kontext-dev)
- It is disputed whether the v1.1 licence also restricts the outputs of local dev weights. An open Hugging Face discussion has no official answer — [HF discussion](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/discussions/6); [Invideo FLUX guide](https://invideo.io/blog/flux-ai-image-generator/)
- FLUX 2 Pro is credited with strong multi-reference composition, which is useful for style or character reference — [Coverr 2026](https://coverr.co/blog/ai-image-generator-for-creators-2026)

**YouTube monetisation and disclosure (applies to all generators)**
- YouTube's altered/synthetic disclosure (March 2024) covers **realistic** content. It is **not required for content that is clearly unrealistic or animated**, or for gen-AI used as production assistance — [9to5Google](https://9to5google.com/2024/03/18/youtube-altered-content-disclosure/); [NBC](https://www.nbcnews.com/tech/tech-news/youtube-says-will-require-creators-label-ai-content-rcna143937)
- The YPP "inauthentic content" update (2025-07-15) demonetises mass-produced or repetitive content. AI-generated videos stay eligible if they add to original content. YouTube has not published a full definition of "mass-produced" — [Gulf News](https://gulfnews.com/technology/youtube-updates-monetisation-policies-ai-and-repetitive-content-ban-begins-july-15-1.500192660); [AlternativeTo](https://alternativeto.net/news/2025/7/youtube-updates-its-policy-to-demonetize-inauthentic-mass-produced-ai-generated-content)

### Inferences
- For this pipeline, where headless Chrome renders HTML/SVG, Recraft vector output can go straight into the page and be animated per path. It is also the only option here with an official MCP server that is Windows-neutral (remote HTTP). Its custom-style tool is the closest thing to a "house style" lock.
- Kurzgesagt-style flat art in documentary explainers counts as animated/unrealistic, so the YouTube AI-disclosure toggle is probably not required. The bigger monetisation risk is the "inauthentic / repetitive" rule, so per-episode original composition matters more than the generator choice.
- Generating on Recraft's free plan would be unusable for a monetised channel, because Recraft owns those images.

### Gaps
- No primary-source data found for **Ideogram** (3.0 or later) on flat style, character reference, API price or MCP. It was not researched within the call budget.
- No current official price or terms page fetched for **gpt-image-1 / gpt-image-1.5**, and no official OpenAI image MCP confirmed.
- No head-to-head test found of flat, Kurzgesagt-like output quality across models. Every quality claim above comes from general creator guides.
- Whether Recraft API-only users without a subscription get commercial rights is not stated on the pricing page. The API pricing docs were not fetched.
- I did not verify whether SynthID or C2PA watermarks on Gemini/OpenAI outputs affect YouTube labelling.

## Raster-to-vector tools (vtracer, potrace, Inkscape trace, Vectorizer.ai, Recraft vectorize, StarVector)

### Takeaway
VTracer is the practical free local option. It handles colour, produces stacked shapes and installs via pip, so an agent can call it from Python. Potrace is black-and-white only. StarVector is a research model, trained for icons, logos and charts rather than illustrations. Recraft `vectorize_image` costs about $0.01 per call through MCP. None of the sources show that a trace yields semantically layered SVG (a group per arm or head) ready for rigging.

### Cited Findings
- VTracer handles colour high-resolution input, while Potrace accepts only binarised black-and-white bitmaps. VTracer's fitting is O(n) against Potrace's O(n²). It has pixel, polygon and spline fitting modes — [VTracer README](https://cdn.jsdelivr.net/npm/svgit4me@1.0.7/vtracer-webapp.2024.5/README.md); [lib.rs](https://lib.rs/crates/vtracer)
- VTracer uses a **stacking strategy** that avoids shapes with holes, so its output is more compact than Illustrator Image Trace — [VTracer README](https://cdn.jsdelivr.net/npm/svgit4me@1.0.7/vtracer-webapp.2024.5/README.md)
- VTracer is on PyPI (`vtracer`) — [PyPI](https://pypi.org/project/vtracer/)
- Recraft MCP `vectorize_image` costs about $0.01/call — [npm](https://classic.yarnpkg.com/en/package/@recraft-ai/mcp-recraft-server)
- StarVector (joanrod/star-vector) has 1B and 8B image-to-SVG checkpoints on Hugging Face, reportedly under Apache 2.0, and is **trained for icons, logos, technical diagrams and charts, not natural images**. It generates SVG code rather than tracing pixels — [README](https://cdn.jsdelivr.net/gh/joanrod/star-vector@main/README.md); [arXiv](https://arxiv.org/abs/2312.11556); [dev.co](https://dev.co/ai/frameworks/star-vector)

### Inferences
- Tracing AI raster art gives flat colour regions stacked in z-order, not named body-part groups. For animation, the agent would still need to segment parts itself, for example by masking before tracing or regrouping paths by colour and position. Recraft native SVG is likely to have fewer paths than a trace, but I found no evidence that it comes grouped by part.
- StarVector is a poor fit for character illustrations.

### Gaps
- No sources found on **Vectorizer.ai** pricing, API terms or quality for flat illustrations.
- No source on **Inkscape Trace Bitmap** quality against VTracer.
- No benchmark of path count or editability for traces of AI art.

## 3D-for-2D (Blender + blender-mcp, Grease Pencil, toon shading)

### Takeaway
blender-mcp (ahujasid) is very popular, at about 22.7k stars by mid-2026. It is the standard way to drive Blender from Claude. I found no evidence of it being used in practice to pose characters and render flat explainer frames. Treat that as experimental.

### Cited Findings
- ahujasid/blender-mcp had about 22.7k stars and 2.2k forks as of 2026-06-14. A second repo from the same author, ahujasid/mcp-for-blender, shows about 29.1k stars as of 2026-09-20. The relationship between the two repos (rename or successor) is unclear — [Star History blender-mcp](https://www.star-history.com/ahujasid/blender-mcp); [Star History mcp-for-blender](https://www.star-history.com/ahujasid/mcp-for-blender); [OSS Insight](https://ossinsight.io/analyze/ahujasid/blender-mcp)

### Inferences
- Memory notes for this project say a Blender/MPFB motion test was already tried outside the repo, and it hit a VRAM gotcha that forced rendering one shot at a time. Blender is usable on this machine, but the cost of building a 3D→flat pipeline (rig, toon shader/Freestyle, then SVG export or a raster trace) is high compared with drawing SVG directly.

### Gaps
- Not researched: Grease Pencil v3 (Blender 4.3+) agent workflows, Freestyle SVG export, or toon-shader-to-flat recipes. I found no practitioner reports of agents producing Kurzgesagt-style output via Blender.
- Whether blender-mcp and mcp-for-blender are the same project (renamed) is unverified.

## Animation formats and tools (Rive, Lottie/dotLottie, Motion Canvas, Remotion)

### Takeaway
Rive has the stronger character rig and state-machine model, but its editor is GUI-first and its files are binary `.riv`, which is hard for an agent to author. Lottie is JSON, so an agent can write and edit it. EffectCraft (installed locally) imports and exports Lottie and has puppet pins. For a headless-Chrome HTML/SVG pipeline, Lottie (lottie-web) or direct SVG/JS animation is easier for an agent than Rive.

### Cited Findings
- Rive's state machine lives inside the `.riv` file. The editor is a desktop/web app, and the runtimes are open source (web, iOS, Android, Flutter, React, React Native) — [Rive blog](https://rive.app/blog/rive-as-a-lottie-alternative); [makerstack review](https://makerstack.co/reviews/rive-review/)
- Standard Lottie plays back linearly, and dotLottie adds state machines via Lottie Creator — [LottieFiles 2026 guide](https://lottiefiles.com/blog/design-guides-and-tips/best-motion-design-tools-ranked-by-use-case)
- A review claims a complex Rive character is about 50 KB, against about 500 KB for an equivalent Lottie. This is a review claim, not a benchmark — [makerstack](https://makerstack.co/reviews/rive-review/)
- Rive pricing conflicts: Free / $9 Cadet / $32 Voyager (LottieFiles guide), against $24–25 per editor per month (other sites) — [LottieFiles](https://lottiefiles.com/blog/design-guides-and-tips/best-motion-design-tools-ranked-by-use-case); [toolradar](https://toolradar.com/compare/rive-vs-lottie); [comparetiers](https://comparetiers.com/compare/lottiefiles-vs-rive)
- EffectCraft has built-in Lottie import and export (`.json` and `.lottie`) and lists anything Lottie can't express. It has puppet pin tools (Position, Advanced, Bend, Starch, Overlap) on a layer-derived mesh with follow-through, but no dedicated character rig — [EffectCraft README](https://raw.githubusercontent.com/storytold/effectcraft/main/README.md)

### Inferences
- Rive's real strength (runtime interactivity) is wasted in pre-rendered video. Its rigging (bones, meshes) is GUI work, so it is unlikely to improve agent output.
- Remotion is already in this repo (`remotion/`). Motion Canvas is a similar code-first TS option. Neither changes illustration quality; they only change how motion is authored.

### Gaps
- Motion Canvas and Remotion were not researched for character animation (for example Remotion's Lottie or Rive integrations).
- No source on AI or agent tools that generate Lottie character rigs.

## Design MCP servers (Figma, Canva, Adobe, Penpot, Inkscape, SVGO)

### Takeaway
Since March 2026, Figma's official MCP can **write** to the canvas (`use_figma`, beta, free for now, usage-based later), but it is built for UI/design-system work. The official Penpot MCP and community Inkscape MCPs (for example `inksmcp`) can create vector shapes. None of these is clearly better than an agent writing SVG directly for illustration.

### Cited Findings
- The official Figma MCP `use_figma` tool writes Figma-native frames, components, variables and auto layout. Clients include Claude Code. It is in **beta, free for now, and will become usage-based paid**. The `/figma-use` skill drives it — [Figma dev docs](https://developers.figma.com/docs/figma-mcp-server/write-to-canvas); [Figma help](https://help.figma.com/hc/en-us/articles/40219873508247-Workflow-lab-Code-to-canvas); [AlternativeTo Mar 2026](https://alternativeto.net/news/2026/3/figma-opens-direct-ai-agent-design-on-canvas-introduces-skills-for-guided-workflows)
- Client support varies. In April 2026, a Windsurf user reported that `use_figma` did not appear in the tool list — [Figma forum](https://forum.figma.com/ask-the-community-7/figma-mcp-for-windsurf-says-read-and-write-access-however-write-to-canvas-is-not-working-52569)
- Penpot's official MCP moved into the main penpot/penpot repo (under `mcp`); the standalone repo was archived on 2026-02-03. It runs hosted (URL from account integrations) or local via npm. A community `ancrz/penpot-mcp-server` (Python, 66 tools, Apache 2.0) also exists — [Penpot help](https://help.penpot.app/mcp/); [Glama penpot-mcp](https://glama.ai/mcp/servers/penpot/penpot-mcp); [Glama ancrz](https://glama.ai/mcp/servers/@ancrz/penpot-mcp-server/blob/8ee7cf15865a8b2db647654adaa999dd407fa7b3/README.md)
- There is no official Inkscape MCP. `inksmcp` (PyPI, MIT) creates, edits and exports vector graphics via Inkscape. Another "Inkscape MCP Server" listed on Glama wraps the Inkscape CLI but is flagged as not installable — [PyPI inksmcp](https://pypi.org/project/inksmcp/); [Glama](https://glama.ai/mcp/servers/k24heo3z44)

### Inferences
- These MCPs give the agent a canvas, not drawing skill. Claude already writes SVG directly into the HTML page, so an intermediary design tool adds export steps without raising the quality ceiling. Penpot/Figma could help as a place for นน to review or tweak layouts.

### Gaps
- Not researched: Canva MCP/Connect API, Adobe Illustrator/Express/Firefly APIs and their terms, and SVGO (an MIT CLI optimiser, from prior knowledge, unverified here).

## Local apps: VectorCraft and EffectCraft (ArtCraft / storytold)

### Takeaway
Both are installed on this machine at version **0.17.0** (`C:\Program Files\VectorCraft`, `C:\Program Files\EffectCraft`, plus an ArtCraft Launcher). Both are MIT/Apache-2.0 Rust apps with a stdio MCP server and a headless CLI. They are explicitly **alpha**: EffectCraft's first commit was 2026-10-01, and the project says it is not yet recommended for production. VectorCraft bundles **Noto Sans Thai**.

### Cited Findings
- VectorCraft is an open-source vector app in pure Rust with an Illustrator-like toolset: Pen, Direct Selection, Pathfinder, Appearance, Layers, live blends, 3D Revolve, gradient mesh, envelope distort and radial repeat. It imports and exports SVG, PDF and PDF-compatible `.ai`, exports PNG, JPEG and WebP, and saves to a native `.vectorcraft` JSON format — [VectorCraft README](https://raw.githubusercontent.com/storytold/vectorcraft/main/README.md)
- `vectorcraft-cli` provides `mcp` (stdio MCP server), `run` (headless batch export) and `bench`. The desktop app takes `--control` (JSON control channel). Agents such as Claude Code can be restricted to specific read and write folders — [VectorCraft README](https://raw.githubusercontent.com/storytold/vectorcraft/main/README.md)
- VectorCraft maturity is self-assessed in its README (dated 2026-10-10): alpha, about 88% of core menu items present, about 65% ready for mainstream illustrators' work. Scripting and gen-AI features are missing, and `.ai` exchange is incomplete. Builds exist for Windows x64, arm64 and x86 — [VectorCraft README](https://raw.githubusercontent.com/storytold/vectorcraft/main/README.md)
- EffectCraft is a clean-room After Effects reimplementation in Rust with 306 effects, keyframes and graph editor, JS expressions, 3D cameras and lights, pure-Rust encoders (H.264, ProRes, AV1 and more, no FFmpeg), and versioned JSON `.ecproj` projects. `effectcraft-cli` provides `set`, `render`, `exec` and `mcp` (tools cover commands, project/property tree, keyframes and rendered frames) and ships a `.mcp.json` — [EffectCraft README](https://raw.githubusercontent.com/storytold/effectcraft/main/README.md)
- EffectCraft maturity: alpha, first commit 2026-10-01, about 91% of tracked parity features and about 45% ready for professional production. It "isn't yet recommended for production client work". macOS is the most tested platform, and **Linux and Windows have basic interaction bugs** — [EffectCraft README](https://raw.githubusercontent.com/storytold/effectcraft/main/README.md)
- ArtCraft trended on GitHub around 2026-10-10 to 10-15. The suite includes PhotoCraft, VectorCraft, FilmCraft, LightCraft, EffectCraft, SoundCraft and others. Release numbers in coverage conflict (v0.9.2 on 10-13 against 0.11.1 on 10-20), and the local install is 0.17.0, so it is moving fast — [aitoolly](https://aitoolly.com/ai-news/article/2026-10-10-artcraft-debuts-on-github-trending-as-a-targeted-creation-engine-for-artists-designers-and-filmmaker); [aiidelist review](https://aiidelist.com/blog/effectcraft-review); [Korben](https://korben.info/de/ich-habe-die-12-kostenlosen-klone-von-adobe-und-microsoft-getestet.html)
- Local check (this machine): `vectorcraft-cli 0.17.0` and `effectcraft-cli 0.17.0`. The VectorCraft folder includes `OFL-noto-sans-thai.txt` (Thai font bundled) — local `--version` and directory listing, 2026-10-26

### Inferences
- These are the only tools found that give Claude **Illustrator-class vector operations** (Pathfinder boolean ops, blends, gradient mesh, envelope distort) over MCP on Windows, under a commercial-safe licence. This could help with shape construction, such as booleans for clean flat silhouettes. They do not supply drawing taste.
- Given the alpha status and Windows interaction bugs, use them as optional helpers (boolean ops, batch export) behind the existing SVG→Chrome pipeline, not as the renderer.

### Gaps
- No independent reviews of VectorCraft quality. Exact MCP tool names were not enumerated (that would need running `vectorcraft-cli mcp` and listing tools).
- No GitHub star or activity counts retrieved for storytold repos.

## Asset libraries an agent could compose from (Open Peeps, Humaaans, Blush, unDraw, OpenMoji, Kenney)

### Takeaway
Open Peeps is CC0 (commercial use, no attribution). Sources conflict on whether Humaaans is formally CC0. Reportedly unDraw's licence bans programmatic embedding and aggregation. Blush, OpenMoji and Kenney terms were not confirmed from sources. Verify each official licence page before use on a monetised channel.

### Cited Findings
- Open Peeps: CC0, usable in personal and commercial projects without attribution — [t3n](https://t3n.de/news/webdesign-character-illustrations-1287803/); [allsvgicons](https://allsvgicons.com/cc0-illustrations/)
- Humaaans: one source says CC0, another says it is free for commercial use but not formally CC0 — [allsvgicons](https://allsvgicons.com/cc0-illustrations/); [rigorousthemes](https://rigorousthemes.com/blog/best-humaaans-alternatives/)
- unDraw: reportedly free for projects, but the licence prohibits compiling assets into packs or aggregators and "embedding them programmatically on another service". This is unverified against the official text — [toolfolio](https://toolfolio.io/productive-value/free-open-source-illustrations-library)
- Blush is a browser-based character, colour and background customiser. No licence terms were found — [hongkiat](https://www.hongkiat.com/blog/download-free-illustration-websites/)

### Inferences
- These kits have a generic "SaaS landing page" look (Open Peeps is hand-drawn line art; Humaaans is corporate-flat), not Kurzgesagt's geometric, glowy, rounded style. They are better used as pose and anatomy references, or as base shapes the agent restyles, than as final art. The channel already has its own mascot (จุก) and look (glow/flat.js), so stock kits would dilute it.

### Gaps
- Not verified from sources: **OpenMoji** (from prior knowledge CC BY-SA 4.0, which requires attribution and share-alike) and **Kenney** (from prior knowledge CC0). Check both on their official pages.
- Not verified: Blush's free-tier licence (from prior knowledge, attribution or a paid plan may be needed for some collections).

## Closing judgement: what would most improve the agent's illustration quality (synthesised from the above)

### Takeaway
Ranked by expected gain for this pipeline:
1. **Recraft via its official MCP**, on a paid plan for commercial rights, using a custom style. It gives native 9:16 and 16:9 SVG that drops straight into the HTML pipeline, plus a style lock.
2. **A raster model for consistent characters (Nano Banana Pro) plus VTracer**, only where pose or anatomy matters. The traced SVG is flat-stacked and needs regrouping before animation.
3. **VectorCraft MCP** (already installed, MIT/Apache) for boolean and shape operations and batch export. It is alpha, so keep it optional.
4. Low value for drawing quality: Figma, Penpot or Inkscape MCPs; Rive; Blender MCP for 3D-for-2D (heavy setup, unproven for this style); and stock kits, which are off-style.

### Cited Findings
- See the sections above. Each ranking input is cited there (Recraft MCP tools and SVG ratios, Nano Banana consistency claims, VTracer stacking, VectorCraft alpha status, Figma write beta).

### Inferences
- The biggest quality limit is probably style direction and composition, not tooling. A generator with a locked custom style (Recraft) addresses that most directly. Every option still needs นน's review, and monetisation risk comes from YouTube's repetitive-content rule more than from AI disclosure.

### Gaps
- No hands-on A/B test was run. Quality rankings are inferred from vendor capabilities and general 2026 guides, not measured on Kurzgesagt-style prompts.
