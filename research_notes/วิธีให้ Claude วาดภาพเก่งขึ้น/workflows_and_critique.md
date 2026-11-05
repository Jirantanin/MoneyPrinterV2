# Workflows, skills and review loops that improve an agent's visual design output (explainer frames in SVG/JS, Kurzgesagt-style)

Scope note: research done 2026-10-26 with about 15 search/fetch calls. Studio-practice sources are mostly the studios' own pages plus secondary guides. The AI side is mostly arXiv papers (2023–2026) and Anthropic's own blog. Claims marked as inferences come from me, not from a source.

## Studio practice: what Kurzgesagt and other flat motion studios do, and which steps transfer to an agent

### Takeaway
Kurzgesagt's public process runs script → sketch visual metaphors and scene priority → about 200 illustrated panels → narration sets the timing → hand-keyed animation of rigged parts → composed music, with team reviews "every few days". They keep an illustration library but still draw most panels from scratch. In the wider motion-design industry, style frames, boards and colour scripts fix the look before animation starts. The parts that transfer to an agent: deciding metaphors and scene priority before drawing, fixing a style frame before mass production, using the narration to drive timing, and running frequent short reviews.

### Cited Findings
- Kurzgesagt's official page lists five phases: research (books, papers, experts, a "sourcesheet" per video), script ("about a dozen drafts"), illustration ("after sketching visual metaphors for each scene", in vector, pixel and infographic styles, built around "quirky and relatable characters"), voiceover and animation (Steve's narration sets the animators' timing; "classic 2D flat animation with 3D elements"), and music and SFX (a custom score from Epic Mountain). — [Kurzgesagt: Our video process](https://kurzgesagt.org/youtube/)
- From Kurzgesagt's "How to make a Kurzgesagt video in 1,200 hours" (mirrored transcript):
  - Sketching plans the visual metaphors, the transitions between ideas, and which scenes need the most attention.
  - "On average, 200 panels need to be illustrated in Adobe Illustrator." There is an illustration library, but most panels are still drawn from scratch. Two to three illustrators work for 8–12 weeks.
  - Illustrated scenes are split into parts and brought into After Effects, and each character is rigged. "Every single thing that's moving on-screen has been moved manually." Two to three animators work for about 8–10 weeks.
  - The team reviews work "every few days" and tweaks it until it feels right. One video takes "at least 1,200 hours", and 2–4 videos are in progress at once.
  - Source: [LingQ mirror of the Kurzgesagt video transcript](https://www.lingq.com/en/learn-english-online/courses/689474/how-to-make-a-kurzgesagt-video-in-120-4887128/)
- A secondary description says the Kurzgesagt look is "based off of rounded shapes and vibrant colors", made by a "stacked team of art directors, illustrators, and producers". — [Arts at Michigan blog (2019)](https://artsatmichigan.umich.edu/ink/2019/09/27/simple-bright-beautiful-the-work-of-kurzgesagt)
- Style frames are described as "a simple, visual representation of how the final animation will look", used so that everyone can agree on a visual style before production goes further. The animator then uses them as reference. A key style frame plus the storyboard should together show the expected end result. — [Tar Heels Live: What is a Style Frame?](https://tarheels.live/mediadesign/?p=1995); [Milanote style-frames guide](https://www.milanote.com/guide/motion-design-style-frames)
- The author of *Design for Motion* argues that style frames, concept art, character design and design boards largely decide whether a motion project succeeds. — [Motionographer interview](https://motionographer.com/2015/12/16/author-of-design-for-motion-talks-industry-education-and-the-state-of-design/)
- School of Motion's Design Bootcamp teaches typography, hierarchy, contrast, colour, value, form, repetition and references for building boards, then mood boards and visual-language direction. It frames the goal as "design systems, not just attractive frames". — [School of Motion Design Bootcamp](https://www.schoolofmotion.com/products/design-bootcamp/)
- Pixar colour scripts: Ralph Eggleston went through the whole *Toy Story* script making "small pastel drawings of each scene" that "concentrated on the basic color". Lasseter noticed that colour intensity tracked the emotion, and Pixar has made colour scripts for every film since. — [MoMA audio: Pixar 20 Years of Animation](https://www.moma.org/audio/playlist/192/2581). Eggleston worked on long strips of black paper in chalk pastel, mapping colour, value and drama. — [Hyperallergic](https://hyperallergic.com/610771/the-art-of-pixar-chronicle-books/). Cooper Hewitt describes colour scripts as mapping "the emotional arc of the film's story through color and light". — [Cooper Hewitt exhibition text](https://www-3.collection.cooperhewitt.org/exhibitions/102147315/text)

### Inferences
- Pipeline mapping to the agent: (1) list the metaphors in the narration and rank scenes by importance, so that drawing time goes to the hero scenes; (2) make one or two style frames and get approval before drawing every scene; (3) make a colour script, meaning one tiny thumbnail per section with its dominant hue and value, and check that the arc follows the emotion; (4) let the narration audio drive timing, which this repo already does; (5) review in short, frequent loops rather than one big pass at the end.
- Kurzgesagt draws most panels fresh even with a library, so a library should supply consistency (characters, props, palette) more than whole scenes. For an agent, the reuse payoff is highest for characters and rigs and lowest for full compositions.
- The "200 panels for about 10 minutes" figure suggests roughly one new illustration every 3 seconds. That is a useful density benchmark for the shot list.

### Gaps
- I found no primary Kurzgesagt source (blog, Patreon or talk) on style guides, shape-language rules, palette tokens or style frames specifically. The "rounded shapes, vibrant colors" description is secondary.
- I didn't find sources on Ninh Ly, TED-Ed or Vox process within the call budget.
- The Pixar dates disagree: one bookseller says the first colourscript was 1993, while Eggleston joined in 1992 (per Hyperallergic).

## Agent design workflows that work: reference-first, tokens, design system first, skills, Remotion

### Takeaway
Anthropic's own write-up says unguided models drift to the "high-probability center" of their training data ("distributional convergence"). The fix is a short, on-demand skill, about 400 tokens, that commits to one bold direction per dimension (type, colour via variables, motion, backgrounds) at the "right altitude". The evidence is qualitative only. Other teams (Google Stitch DESIGN.md, Remotion Agent Skills) take the same approach: a persistent design-system or conventions file the agent reads every time. Reviewers report that agents don't always honour these files.

### Cited Findings
- Anthropic, "Improving frontend design through Skills":
  - Without guidance, models sample from the "high-probability center", producing Inter fonts, purple gradients on white and minimal animation.
  - Guidance is kept in on-demand skills rather than in every prompt, because extra context on every request can degrade performance.
  - The prompt is about 400 tokens, pitched at the "right altitude" (no hard-coded hex values, but not vague either). It covers typography ("Use extremes: 100/200 weight vs 800/900", size jumps of 3x or more), colour ("Dominant colors with sharp accents outperform timid, evenly-distributed palettes", using CSS variables), motion (one staged page load rather than scattered micro-interactions) and backgrounds (layered depth rather than flat colour). It ends with a warning not to converge on new defaults such as Space Grotesk.
  - The evidence is side-by-side examples only, with no metrics.
  - Source: [Claude blog](https://www.claude.com/blog/improving-frontend-design-through-skills)
- The frontend-design skill is model-invoked and ships in the anthropics/claude-code plugin marketplace. Secondary write-ups say it works best paired with a custom brief stating brand constraints. — [ClaudeLog](https://claudelog.com/faqs/what-is-frontend-design-skill-in-claude-code/); [Medium: anti AI-slop skill](https://medium.com/@porter.nicholas/anthropic-skills-marketplace-the-anti-ai-slop-ui-design-skill-a572d0cfef4f)
- Google Stitch DESIGN.md is a markdown file that describes a design system (colours, typography, spacing, components) to an agent. Stitch builds a styleguide from it as the first generation step, and Claude Code can read it too. One reviewer found that a heading-font change didn't fully carry through. All sources here are secondary. — [MindStudio](https://www.mindstudio.ai/blog/what-is-design-md-google-stitch); [Tutorials Dojo critique](https://tutorialsdojo.com/what-google-stitch-actually-does-and-where-it-falls-short/)
- Remotion Agent Skills are maintained convention files for coding agents, covering animation, timing, audio and captions. Guides advise prompting "one composition, one animation, one caption track at a time" and keeping judgment-heavy timeline work (pacing, music sync, art direction) with a human or an editor. The install command differs between sources. — [Tella guide](https://www.tella.com/blog/how-to-use-remotion-agent-skills-with-claude-code); [mer.vin](https://mer.vin/2026/05/remotion-agent-skills-install-remotion-dev-skills-for-claude-code-and-cursor/)

### Inferences
- A copyable "art direction skill" for this repo would follow the Anthropic pattern: about 400 tokens, loaded only for graphic work, with one committed direction per axis. For example:
  - shape language: rounded rectangles and circles, no hairlines
  - palette: one dominant hue per section, one accent, colour tokens only, no raw hex in scene code
  - value: a three-step value plan of background, midground and subject
  - motion: one staged entrance per shot
  - an explicit list of this channel's own default clichés to avoid
- The concrete numbers in the Anthropic piece (weight extremes, 3x size jumps) suggest the rules should be measurable, so a script can check them.
- The DESIGN.md "not honoured" report suggests tokens should be enforced in code (a palette module the compositor imports, plus a lint check that fails on raw colours), not only described in prose.

### Gaps
- I found no quantitative study showing that reference-first or mood-board-first prompting improves agent illustration quality. The support is practitioner and vendor claims only.
- I couldn't retrieve the exact text of Anthropic's frontend-design or artifact-design SKILL.md from these searches.
- I didn't look at v0, Lovable, Figma AI or Recraft engineering blogs within the budget.

## Critic loops: render → screenshot → VLM critique → revise; separate reviewers; rubrics; VLM blind spots

### Takeaway
A model checking itself with no outside signal does not reliably improve, and it often turns correct answers into wrong ones. LLM judges also prefer their own outputs. Loops do work when they bring in external signal: a rendered image, a separate judge, few-shot expert critiques, or relational feedback. VLMs are weak at small details, exact positions and counting, and cropping the region of interest measurably helps. So a loop should combine rendered full frames, zoomed crops, a separate rubric-driven judge, and pixel-level programmatic checks for whatever a VLM can't measure.

### Cited Findings
- Huang et al. (ICLR 2024): models "cannot inherently correct their own reasoning errors without external feedback, often degrading performance by altering correct answers to incorrect ones". Earlier positive results often relied on oracle labels. External feedback such as code-execution results does help. — [arXiv 2310.01798](https://arxiv.org/abs/2310.01798)
- Panickssery, Bowman and Feng (NeurIPS 2024): LLM evaluators score their own outputs higher than humans do, and the strength of the bias correlates linearly with self-recognition ability. — [arXiv 2404.13076](https://arxiv.org/html/2404.13076v1)
  - An alternative account says judges prefer lower-perplexity (more familiar) text whether or not they wrote it. — [arXiv 2410.21819](https://arxiv.org/pdf/2410.21819)
  - A multimodal study reports that each MLLM judge typically favours its own generations. — [MLLM-as-a-Judge self-preference project page](https://projectpage-1sg1y.kinsta.page/)
- "See it. Say it. Sorted." (arXiv 2508.15222, 2025) is a training-free SVG diagram loop:
  - A Critic VLM proposes a small set of qualitative, relational edits.
  - Several candidate LLMs implement them with different strategies (conservative, aggressive, alternative, focused).
  - A separate Judge VLM picks the best candidate to "ensure stable improvement". The design "prioritizes qualitative reasoning over brittle numerical estimates".
  - Result: more faithful layout than GPT-5 and Gemini-2.5-Pro, but on only 10 sketches.
  - Source: [arXiv 2508.15222](https://arxiv.org/abs/2508.15222v2)
- IntroSVG (CVPR 2026) uses one VLM as both generator and critic. It runs generate → render to PNG → critique → refine, trained with SFT and DPO from a teacher VLM, and reports state-of-the-art SVG results. — [arXiv 2603.09312](https://arxiv.org/html/2603.09312v1); [CVPR poster](https://cvpr.thecvf.com/virtual/2026/poster/38201)
- UICrit (UIST 2024) collected 3,059 expert critiques of 983 mobile UIs from seven designers. Few-shot plus visual prompting gave a 55% gain in LLM-generated UI feedback. — [arXiv 2407.08850](https://arxiv.org/abs/2407.08850)
  - A follow-up adds iterative refinement of both comments and bounding boxes. For Gemini, box IoU rose from 0.120 (zero-shot) to 0.357 (few-shot, visual prompting and iterative refinement). — [arXiv 2412.16829](https://arxiv.org/html/2412.16829v1)
  - PerceptUI (2026) still finds human designer critiques ahead of all LLM methods (0.75 vs 0.48 for UICrit few-shot), and notes that few-shot imitation can produce shallow comments. — [arXiv 2606.05697](https://arxiv.org/pdf/2606.05697)
- VLM blind spots:
  - BlindTest: four state-of-the-art VLMs average 56.20% on simple visual tasks, struggling with precise spatial information and counting from 0 to 10. — [arXiv 2407.06581](https://arxiv.org/abs/2407.06581v3)
  - SPHERE finds "spatial blind spots", especially size constancy, egocentric perspective-taking and physical inference. — [arXiv 2412.12693](https://arxiv.org/pdf/2412.12693)
  - A 2025 counting study finds VLMs sensitive to object number, arrangement and distractors. — [arXiv 2501.15144](https://arxiv.org/pdf/2501.15144v2)
- Zoomed crops: "MLLMs Know Where to Look" (ICLR 2025) shows that MLLM accuracy depends causally on how large the visual subject is. The models do attend to the right region even when they answer wrongly. ViCrop feeds the original image plus an attention-guided crop and gives significant training-free gains across seven benchmarks. — [arXiv 2502.17422](https://arxiv.org/html/2502.17422v1)

### Inferences
- Loop design for this compositor:
  1. Render the frame to PNG at final resolution.
  2. Run programmatic checks first (see the composition section).
  3. Send a separate reviewer agent with fresh context, which has not seen the generation reasoning. Give it the full frame, 2–4 crops (focal subject, text or label areas, character face and hands, frame edges), and the approved style frame side by side.
  4. The reviewer scores a fixed rubric and returns a few relational edits ("move the planet so it overlaps the moon", "the label touches the ring edge") rather than pixel numbers. The relational phrasing follows the "See it. Say it. Sorted." design.
  5. Optionally generate 2–3 variants and have a judge pick one.
  6. Cap the loop at 2–3 rounds and stop when the score doesn't improve. Self-critique without new signal tends to degrade.
- Because of self-preference bias, the judge shouldn't be told which candidate is the current or "own" version. Better still, compare against the approved style frame rather than asking "is this good?".
- Few-shot examples help critics, per UICrit. Keep 5–10 annotated good and bad frames from past episodes, with short critiques, as reviewer exemplars.
- Copyable rubric. Score 0–2 each; any 0 on a starred item fails the frame. Items marked "code" should be checked by script, not by the VLM.
  - *Focal point: exactly one obvious subject, readable in under one second (squint or blur test).
  - *Silhouette: the subject is readable as a solid-black silhouette (code: render a mask and check area and compactness).
  - *Value contrast: subject vs background luminance contrast at or above a threshold (code: mean-luminance difference or WCAG-style ratio on the masks).
  - Hierarchy: one primary, one or two secondary, everything else recessive in size, saturation and contrast.
  - *Tangents: no edges that just touch, whether object–object, object–frame edge or text–shape (code: bounding-box and outline proximity under N px, with no overlap).
  - Overlap and depth: at least three depth layers (background, midground, foreground), with depth shown by overlap, scale and value.
  - Negative space: breathing room around the subject; text never crammed against shapes.
  - *Safe areas: all text and key shapes inside the platform safe zone (code).
  - Consistency: palette tokens only (code), character proportions match the rig, line weight and corner radius match the style frame.
  - Narration fit: the frame shows the thing the narration says at that moment.
  - Clutter: element count under a limit for the shot type (code).

### Gaps
- I found no study that directly compares a fresh-context reviewer agent against self-review specifically for illustration. The support comes from reasoning and text-judge studies plus SVG pipeline papers that use separate judges.
- A gamedev.net item mentions a 2026 paper by "Perlman et al." on constrained iterative refinement of SVG with off-the-shelf VLMs. The page returned 403, so I couldn't verify it.
- I found no benchmark of VLM judging specifically for flat-illustration aesthetics.

## Composition heuristics as checkable rules (9:16 Shorts and 16:9)

### Takeaway
Tangents are a well-documented composition fault: edges that touch without overlapping or separating flatten depth and draw the eye. They are machine-checkable. Vertical-video safe zones are not officially published by YouTube, and third-party numbers vary. A conservative rule is to keep captions and key subjects out of the top and bottom ~15% and the right ~140 px of a 1080×1920 frame, then verify on a device.

### Cited Findings
- Tangents: when adjacent shapes "are not either overlapped or given some space between them" the spatial depth gets confused. The fix is to move, overlap or reframe. A shape that blocks a corner isolates that corner. — [The Informed Illustrator (Don Arday)](https://www.theinformedillustrator.com/2013/10/off-on-tangent.html); [Ctrl+Paint: avoiding visual tangents](https://ctrlpaint.com/videos/avoiding-visual-tangents)
- "There are no real rules against kissing — only conventions. One lone kiss generally sticks out as the blunder of an amateur." If touching edges are used deliberately, they should be repeated. — [Painter's Keys](https://painterskeys.com/?p=6833)
- Shorts frame is 1080×1920. About 15% at the top is covered by search and menu, about 15% at the bottom by title, handle and description (more for long titles), and about 140 px on the right by the action buttons. Captions 100 px from the bottom are hidden in the app. — [Clipspeed](https://www.clipspeed.ai/blog/youtube-shorts-size.html)
- A cross-platform safe area of about 900×1400 px centred works across TikTok, Reels and Shorts. Captions should sit around y=1200–1300 and end no lower than about 370 px from the bottom. Reap says these are not official specs. — [Reap: short-form safe zones](https://reap.video/blog/short-form-video-safe-zones)

### Inferences
Checkable rules, for the compositor to report per frame:

1. Safe zone (9:16, 1080×1920): every text box and focal-subject box lies inside x∈[60, 940] and y∈[290, 1550]. Captions stay in the y band 1150–1450. Fail on any overlap with the UI zones.
2. Safe zone (16:9, 1920×1080): keep text inside the 90% title-safe area, about 96 px margins left and right and 54 px top and bottom. This is the broadcast convention; I found no 2024–26 source for it in this pass.
3. Thirds: the centroid of the focal subject lies within ±8% of a thirds intersection or the centre line. For vertical video, the upper third is often better because captions take the lower third. Allow intentional centring for a single hero object.
4. Focal hierarchy: the focal element has the largest area or the highest contrast, and is at least 1.5× more salient than the next element (by area × contrast).
5. Negative space: at least 25–35% of the frame is low-detail background. Padding around the focal subject is at least 5% of the frame's shorter side.
6. Tangents: for every pair of shape outlines, and every shape against the frame edge, the minimum distance must be either ≤ -k px (clear overlap) or ≥ +k px (clear gap). Fail if it is in (-k, +k) with k≈6–10 px at 1080p. Exempt deliberate repeated alignments.
7. Depth: at least three z-layers, with foreground elements larger or darker or higher in contrast and background lower in contrast. Check the luminance-contrast ordering by layer.
8. Text: no text over busy high-frequency regions (local variance threshold behind text boxes). Text contrast ratio at least 4.5:1.

All numbers in rules 3–8 are my starting thresholds and need tuning on past episodes.

### Gaps
- There is no official YouTube safe-zone spec, and third-party numbers conflict (right edge 48 px vs 140 px; usable area 984×1500 vs 900×1400).
- I found no source that codifies rule-of-thirds, negative-space or hierarchy as numeric thresholds. Those numbers are inferred defaults.

## Reusable, parametric asset libraries (rigs, pose libraries, prop kits)

### Takeaway
In After Effects practice, quality builds up through rigged characters and pose-based controls rather than redrawing. Joysticks 'n Sliders interpolates between keyed extreme poses, and Duik and Rubberhose handle limb rigging. These give reusable actions such as blinks, gaze, mouth shapes, hand poses and head turns. Kurzgesagt rigs every character and keeps a library, but most panels are still new drawings.

### Cited Findings
- Kurzgesagt splits each illustration into parts and rigs each character in After Effects, and keeps an illustration library while drawing most panels from scratch. — [LingQ mirror of the Kurzgesagt transcript](https://www.lingq.com/en/learn-english-online/courses/689474/how-to-make-a-kurzgesagt-video-in-120-4887128/)
- Joysticks 'n Sliders is a pose-based rigging system: you set five keyframes (origin, left, right, top, bottom extremes) and a joystick interpolates between them. Later versions support masks and Bézier shape paths. — [aescripts: Joystick 'n Sliders](https://aescripts.com/joystick-n-sliders)
- Typical reusable uses are "eye blinks, eyebrow movements, eye gaze, mouth poses (lip syncing), hand poses, head turns, reusable actions". — [Udemy course listing](https://www.udemy.com/course/rigging-and-animating-psds-with-duik-joysticks-n-sliders/)
- School of Motion compares Duik's Bassel connectors with Joysticks (Sliders are "more technical, and more powerful"). Rigs often combine a head rig, Joysticks 'n Sliders and Duik. — [School of Motion review](https://schoolofmotion.com/blog/after-effects-tool-review-joysticks-n-sliders-vs-duik-bassel); [aescripts: Rubberhose + JnS rigging](https://aescripts.com/learn/character-rigging-with-rubberhose-and-joysticks-n-sliders)

### Inferences
- Code equivalent for this repo's gfx_kit:
  - Each character is a function `drawCharacter(params)` with named parameters: head turn −1..1, gaze x/y, mouth shape index, brow, arm angles, and an expression preset.
  - A pose library is a JSON map from pose name to parameter values. A joystick is bilinear interpolation between five stored extreme poses, mirroring JnS.
- A prop kit is a set of parametric functions (planet, rocket, cell, building) that take only tokens (palette role, size, detail level), so props match automatically.
- Accumulation loop: whenever the reviewer approves a new drawn element, promote it into the kit with a thumbnail and a short usage note (a LIBRARY.md entry). Contact-sheet renders of the whole kit then act as a living style guide and as few-shot reference for the critic.
- Following Kurzgesagt, reuse characters, props and palette, but still compose each scene fresh. Reusing whole scenes risks visible repetition.

### Gaps
- I found no public material on how Kurzgesagt structures its illustration library or character model sheets.
- I found no 2024–2026 sources on agents building and maintaining parametric SVG asset libraries over time. This section's agent mapping is inference.
