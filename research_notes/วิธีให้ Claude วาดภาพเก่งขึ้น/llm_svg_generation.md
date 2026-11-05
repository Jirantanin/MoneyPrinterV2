# LLM-driven SVG / vector illustration generation: 2024–2026 state of the art and techniques that measurably help

Scope note: these notes come from about 18 search and fetch calls. Primary sources were read for VectorGym (2026), IntroSVG (2026), RLRF (NeurIPS 2025), SVGenius (ACM MM 2025) and Chat2SVG (CVPR 2025). Several systems named in the brief (StarVector original numbers, LLM4SVG, SVGDreamer++, IconShop, VGBench, SVG-Bench, UniSVG numbers, OmniSVG numbers) were found only as abstracts or mentions. They are listed under Gaps instead of being filled in from memory.

## Q1. What the research systems do, what they show helps, and the reported numbers for general LLMs

### Takeaway
Frontier general LLMs (Claude, GPT and Gemini, from 2025–2026 versions) are now the strongest *text-to-SVG* generators on every public benchmark that includes them. They clearly beat specialised open SVG models such as IconShop and LLM4SVG, especially on hard prompts. The models are bunched closely together: in the newest benchmark (VectorGym, 2026), GPT-5.1, Gemini 3 Pro and Claude Sonnet 4.5 are within about 1.5 points on Text2SVG. The research that improves quality all points the same way: **feed the rendered image back into the model** (RL from rendering feedback, a generator-critic loop, or visual rectification). Constraining the model to simple primitives and then optimising the geometry separately also helps.

### Cited Findings

**Most recent benchmarks (2026)**
- VectorGym (arXiv 2603.29852, 2026) has four tasks with human-authored annotations: Sketch2SVG, SVG editing, Text2SVG and SVG captioning. Its data comes from SVG-Stack, with 300 test samples. Metrics are MSE, LPIPS, DINO, CLIP and a 0–5 VLM judge. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- VectorGym Text2SVG scores: GPT-5.1 **70.68**, Gemini 3 Pro **69.92**, Claude Sonnet 4.5 **69.19**, GPT-4o 63.09, Qwen3-VL-8B-Gym (RL-trained) 63.60, Qwen3-VL-235B 59.68. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- VectorGym Sketch2SVG / Edit / Overall scores: Gemini 3 Pro 78.56 / 88.71 / **73.17**, GPT-5.1 75.69 / 87.71 / 71.36, Claude Sonnet 4.5 73.85 / 88.07 / 70.31, GPT-4o 69.55 / 82.35 / 64.93. Claude Sonnet 4.5 had the best editing DINO (95.61) and the lowest editing MSE (6.29). — [VectorGym](https://arxiv.org/html/2603.29852v1)
- VectorGym found that an RL-trained 8B model with a task-specific curriculum overtook much larger models: overall rose from 58.74 to 66.05, and the Sketch VLM-judge score rose from 33.00 to 46.00. The paper does not separate the effect of RL from the effect of the curriculum. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- VectorGym prompts ask for `<think>` reasoning before the SVG, but the paper reports no ablation of the reasoning step. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- IntroSVG (arXiv 2603.09312, 2026) reports single-shot zero-shot text-to-SVG results. All models had a 100% render success rate. Scores are FID↓ / CLIP-T2I↑ / Aesthetic↑ / HPS↑:
  - GPT-4o: 37.00 / 0.2748 / 4.4103 / 0.1941
  - **Claude 4.5 Sonnet: 39.67 / 0.2853 / 4.5724 / 0.1998** (best CLIP and best HPS among the baselines)
  - Gemini 2.5 Pro: 30.52 / 0.2754 / 4.5854 / 0.1981
  - GPT-5: 34.07 / 0.2779 / 4.5232 / 0.1962
  - Grok-4: 33.07 / 0.2717 / 4.4546 / 0.1944

  — [IntroSVG](https://arxiv.org/html/2603.09312v1)

**SVGenius (ACM MM 2025, arXiv 2506.03139)**
- SVGenius has 2,377 queries across understanding, editing and generation, stratified by complexity, from 24 domains. It evaluates 22 models. — [SVGenius GitHub](https://github.com/ZJU-REAL/SVGenius)
- Text-to-SVG rCLIP scores (Easy / Medium / Hard):
  - Claude-3.7-Sonnet: **92.90 / 87.62 / 87.97**
  - GPT-4o: 90.95 / 84.72 / 82.81
  - DeepSeek-R1: 91.39 / 82.99 / 83.06
  - Gemini-2.0-Flash: 90.96 / 80.36 / 78.61
  - IconShop: 86.22 / 77.35 / 72.55
  - LLM4SVG: 75.78 / 68.84 / 62.98

  Claude HPS was 21.35 on Easy and 18.74 on Hard. The paper's Medium HPS value for Claude, 85.71, looks like a typo. — [SVGenius](https://arxiv.org/html/2506.03139)
- Image-to-SVG SSIM (Easy / Medium / Hard): Claude-3.7 54.02 / 51.36 / 51.15, GPT-4o 52.41 / 49.41 / 50.66, Gemini-2.0-Flash 50.07 / 46.98 / 48.29, StarVector-8B 37.60 / 52.95 / 56.53. — [SVGenius](https://arxiv.org/html/2506.03139)
- SVGenius findings:
  - All models degrade as complexity rises. Understanding drops most: Claude's Perceptual QA falls from 80.25% to 33.33%. Generation is the most stable.
  - "Reasoning-enhanced training proves more effective than pure scaling." Example: DeepSeek-R1 matches proprietary models on Easy QA. This is one paper's finding, not a controlled comparison.
  - Style transfer is the hardest task. Proprietary models score about 2.5–3.3 out of 5 on it.
  - Specialised models (IconShop, LLM4SVG) are competitive on Easy prompts but collapse on Hard ones.

  — [SVGenius](https://arxiv.org/html/2506.03139)
- SVG editing (Claude-3.7-Sonnet): bug fixing 76 / 75 / 69, style editing 79.75 / 59.74 / 52.56 (Easy / Medium / Hard). — [SVGenius](https://arxiv.org/html/2506.03139)

**RLRF: Rendering-Aware RL (NeurIPS 2025, ServiceNow/Mila, arXiv 2505.20793)**
- Method: rollouts are rendered with CairoSVG and rewarded on four things: pixel L2 plus Canny-edge L2, DreamSim semantic similarity (CLIP plus a VLM judge for text-to-SVG), and a length penalty for code efficiency. Training uses GRPO with 64 rollouts per image and no KL term. — [RLRF](https://arxiv.org/html/2505.20793v2)
- Im2SVG results on SVG-Stack-Hard, as MSE↓ / SSIM↑ / DINO↑ / LPIPS↓:
  - Claude 3.7 Sonnet: 17.73 / 69.33 / 79.80 / 28.42
  - GPT-4o: 16.92 / 66.91 / 89.00 / 27.55
  - Gemini-Flash-2.0: 19.31 / 60.21 / 86.53 / 32.10
  - StarVector-1B: 4.60 / 87.00 / 96.00 / 9.22; with RLRF, 3.46 / 88 / 98 / 7.51
  - Qwen2.5-VL-7B: 23.10 / 61.40 / 78.00 / 33.80; with SFT, 8.60 / 79.40 / 93.00 / 16.58; with SFT then RLRF, **1.03 / 95.10 / 98.70 / 3.08**
  - The paper is internally inconsistent: its Table 2 gives 4.42 MSE / 89.09 SSIM for the same 7B configuration.

  — [RLRF](https://arxiv.org/html/2505.20793v2)
- The paper explains the failure of SFT-only models: they "fail to incorporate visual feedback from rendered outputs." They hallucinate or loop on complex images that need long SVGs. RLRF applied directly to an instruct model without SFT performs poorly (MSE 14.23). More rollouts per input (8 → 64) consistently improves results. — [RLRF](https://arxiv.org/html/2505.20793v2)
- RLRF: in image-to-SVG, frontier general LLMs are far behind trained models on pixel fidelity. Their MSE is about 17–19, compared with 1–5 for trained models. Tracers such as LIVE and VTracer score well on pixel metrics but produce enormous SVGs, from more than 7k up to 100k tokens. — [RLRF](https://arxiv.org/html/2505.20793v2)

**Chat2SVG (CVPR 2025, arXiv 2411.16602)**
- Chat2SVG uses **claude-3-5-sonnet** as its backbone. Stage 1: the LLM writes an SVG template from primitives only (rect, ellipse, line, polyline, polygon, short paths) on a 512×512 canvas, giving each element a unique ID and a semantic comment. Stage 2 is "visual rectification": the render is fed back to the LLM to fix misalignment, hidden elements, unrecognisable objects, disproportion and path order, and about 2 rounds are usually enough. Stage 3 is diffusion-guided optimisation, run first in a latent space (SVG VAE) and then on control points, with 500 iterations each. — [Chat2SVG](https://arxiv.org/html/2411.16602v1); [CVPR supplementary](https://openaccess.thecvf.com/content/CVPR2025/supplemental/Wu_Chat2SVG_Vector_Graphics_CVPR_2025_supplemental.pdf)
- Results as Image FID↓ / Path FID↓ / text alignment↑: Chat2SVG 33.31 / 39.07 / 0.3090, SVGDreamer 35.48 / 47.95 / 0.2919, VectorFusion 39.52 / 56.79 / 0.2982, DiffSketcher 44.89 / 66.48 / 0.2623, CLIPDraw 46.77 / 70.13 / 0.3048. The paper does not compare against plain Claude or GPT output. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- Stated reason for the primitives-only constraint: the LLM "has limitations in synthesizing geometrically complex paths," and "LLMs may produce imprecise visual layouts." — [Chat2SVG](https://arxiv.org/html/2411.16602v1)

**Reasoning-trained SVG models (2025)**
- Reason-SVG (arXiv 2505.24499) introduces "Drawing-with-Thought": the model writes a design rationale before the code. It is trained with SFT followed by GRPO, using a hybrid reward that covers reasoning, structural validity, semantic alignment and visual quality. The SVGX-DwT-10k dataset was released with it. — [Reason-SVG](https://arxiv.org/html/2505.24499v1)
- SVGThinker (arXiv 2509.24299, ACM MM '25) renders primitives step by step, has an MLLM annotate each step, and trains on that chain-of-thought with SFT. Reported FID is 34.06 and CLIP 0.2765. — [SVGThinker](https://arxiv.org/html/2509.24299v1)
- A 2026 follow-up (arXiv 2603.16189) argues that SVGen and SVGThinker do not fully use `<g>` grouping, which limits editability. — [Reliable Reasoning in SVG-LLMs](https://www.alphaxiv.org/abs/2603.16189)

**OmniSVG (NeurIPS 2025, arXiv 2504.06263)**
- OmniSVG builds on a pre-trained VLM and tokenises SVG commands and coordinates as discrete tokens, separating structure from geometry. It accepts text, image and character-reference inputs and is trained on MMSVG-2M (2M SVGs). Weights are public. No numbers were retrieved. — [OmniSVG arXiv](https://arxiv.org/abs/2504.06263); [NYU Shanghai RITS note](https://rits.shanghai.nyu.edu/ai/omnisvg-weights-released/)

**Background (2023–2024, optimisation-based, not LLM code)**
- VectorFusion uses Score Distillation Sampling from a diffusion model to optimise paths, with optional image initialisation. — [pytorch-svgrender docs](https://pytorch-svgrender.readthedocs.io/en/latest/_sources/vectorfusion.rst.txt)
- SVGDreamer (CVPR 2024) targets editability (separating background and foreground layers), visual quality and diversity in text-to-SVG. — [SVGDreamer supplementary](https://openaccess.thecvf.com/content/CVPR2024/supplemental/Xing_SVGDreamer_Text_Guided_CVPR_2024_supplemental.pdf)
- SGP-Bench ("Can LLMs Understand Symbolic Graphics Programs?", ICLR 2025 Spotlight) asks multiple-choice semantic questions about an image from its SVG or CAD program alone, then checks consistency after random translation and rotation. LLMs struggle, sometimes near chance, and symbolic MNIST challenges GPT-4o. Symbolic Instruction Tuning helps. — [SGP-Bench arXiv](https://arxiv.org/html/2408.08313v1); [Liner review](https://liner.com/review/can-large-language-models-understand-symbolic-graphics-programs)

### Inferences
- For a Claude Code agent, switching models buys little: GPT, Gemini and Claude trade places by benchmark and metric. Process changes are where the measured gains are, in particular a render-feedback loop, primitive constraints and post-hoc geometry optimisation.
- "Writing code blind" is the root failure named across RLRF, Chat2SVG and IntroSVG. An agent that never looks at its render is in the same position as the SFT-only models those papers improve on.
- In text-to-SVG, "quality" metrics (CLIP and HPS) reward semantic recognisability more than artistic polish. A benchmark lead does not mean Kurzgesagt-level art.

### Gaps
- No primary numbers were retrieved for StarVector's original paper (CVPR 2025), LLM4SVG, IconShop, SVGDreamer++, VGBench, SVG-Bench or UniSVG. UniSVG is described secondhand as a dataset of about 525k SVGs. — [search summary](https://arxiv.org/pdf/2510.11341)
- No benchmark tested Claude Opus 4.x or Claude 4.5+ Opus-class models, or Gemini 3 on SVGenius-style hard tiers.

## Q2. Which prompting and agent techniques have evidence behind them

### Takeaway
The best-supported technique is **render → look → revise**. It has quantitative support (IntroSVG zero-shot loops on GPT-4o and GPT-5, and RLRF in training), but the gains for zero-shot frontier models are modest and not monotonic. **Primitives-only templates plus semantic IDs and comments** (Chat2SVG) and **scene → object → layout plan before code** are supported qualitatively and by a system-level win. Reasoning-before-code has training-time evidence (Reason-SVG, SVGThinker, and SVGenius's reasoning-model observation) but no clean prompting-only ablation. Best-of-N with a judge has indirect evidence only: in RLRF more rollouts helps, but that is during training.

### Cited Findings
- **Render → critique → refine loop (quantitative).** IntroSVG ran the same loop zero-shot on general models, from iteration 0 to iteration 3:
  - GPT-4o: FID 37.80 → 36.34
  - GPT-5: FID 35.87 → 32.68. Its CLIP-T2I peaked at iterations 1–2 (0.2858) and then dipped to 0.2779.
  - Grok-4: FID 41.39 → 32.85, with HPS flat.

  IntroSVG's own trained model improved FID 29.76 → 26.18 over 3 iterations. Stopping rule: a maximum of 3 rounds, or a critic score ≥ 9.5. — [IntroSVG](https://arxiv.org/html/2603.09312v1)
- **Visual rectification with Claude 3.5 Sonnet (qualitative).** Chat2SVG feeds the render back for about 2 rounds to catch misalignment, hidden or occluded elements, unrecognisable objects, disproportion and path-order errors. The only evidence is a qualitative figure (misaligned ears, an unrecognisable police car); there is no isolated ablation. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- **Decomposition and layout plan first (system-level quantitative, component qualitative).** Chat2SVG's three-layer expansion has three levels. At scene level, it lists the essential objects and adds complementary ones. At object level, it breaks each object into components "so none are missed." At layout level, it plans position, size, colour and spatial relations. The full pipeline beats SVGDreamer and VectorFusion on FID and CLIP. Its "No SVG Template" ablation removes the whole template stage, not the plan alone. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- **Primitives-only constraint (qualitative, author rationale).** Chat2SVG limits the LLM to rect, ellipse, line, polyline, polygon and short paths because of LLM weakness at complex paths, and moves organic detail to an optimiser. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- **Optimising after generation (quantitative).** Chat2SVG refines the LLM template by latent inversion, then latent optimisation, then point optimisation, each guided by a diffusion model. This is what lifts it above pure diffusion-SVG methods (Path FID 39.07 vs 47.95 for SVGDreamer). — [Chat2SVG](https://arxiv.org/html/2411.16602v1); [supplementary](https://openaccess.thecvf.com/content/CVPR2025/supplemental/Wu_Chat2SVG_Vector_Graphics_CVPR_2025_supplemental.pdf)
- **Reasoning/plan before code (training-time quantitative, no prompt-only ablation).** The evidence is Reason-SVG's "Drawing-with-Thought" rationale-then-code with an RL reward on the reasoning, SVGThinker's step-by-step primitive CoT (FID 34.06), and SVGenius's observation that reasoning models (DeepSeek-R1, QwQ-32B) often beat larger conventional ones. — [Reason-SVG](https://arxiv.org/html/2505.24499v1); [SVGThinker](https://arxiv.org/html/2509.24299v1); [SVGenius](https://arxiv.org/html/2506.03139)
- **Best-of-N / more samples (indirect).** In RLRF, raising rollouts per input from 8 to 64 consistently improved MSE, reward and SVG length. This happens during training; the paper reports no inference-time best-of-N with a VLM judge. — [RLRF](https://arxiv.org/html/2505.20793v2)
- **Short, efficient code is rewarded.** RLRF penalises output longer than half the ground-truth token length (quadratic penalty), and its RL-trained models produced shorter SVGs than SFT ones. — [RLRF](https://arxiv.org/html/2505.20793v2)

### Copyable prompt patterns (reconstructed from the sources' descriptions, not verbatim prompt text)
- Chat2SVG-style template prompt, paraphrasing the structure from the paper's description: "Step 1 Expand: list the essential objects for the scene, add complementary objects, then break each object into named parts; give each part's position, size, colour and what it overlaps. Step 2 Write SVG on a 512×512 canvas using only rect, ellipse, line, polyline, polygon and short paths; give every element a unique id and an XML comment naming the part. Step 3 Improve: review the code for missing parts and layering order." — [Chat2SVG](https://arxiv.org/html/2411.16602v1). The verbatim prompts are in its Appendix D, which was not retrieved.
- Rectification checklist to run on the rendered PNG, using the categories from Chat2SVG: misaligned parts, hidden or occluded elements, unrecognisable object, disproportionate scale, wrong path or stacking order. Stop after about 2 rounds. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- IntroSVG-style stopping rule: score the render 0–10 against the prompt, and stop at ≥ 9.5 or after 3 rounds. — [IntroSVG](https://arxiv.org/html/2603.09312v1)
- Reason-first format, as in VectorGym: emit `<think>…</think>` reasoning, then the SVG. — [VectorGym](https://arxiv.org/html/2603.29852v1)

### Inferences
- Stop the loop early: IntroSVG's GPT-5 CLIP peaked at iterations 1–2. Two or three rounds is where the published loops stop, and more rounds can drift.
- For organic shapes (asteroids, animals), the Chat2SVG lesson carries over to a code-only agent. Build a primitive skeleton with the LLM, then get the organic detail procedurally: noise-displaced polygon vertices, smoothed Catmull-Rom/Bezier through jittered points, or boolean unions of ellipses. Don't ask the LLM to hand-type long cubic-path coordinates. This is inference, not a measured result.
- A "coordinate grid / layout plan first" was not tested in isolation by any source found. Chat2SVG's layout-level expansion is the closest evidence.

### Gaps
- No source isolated the effect of a coordinate grid, a template library or a primitive library in a prompt-only setting with frontier models.
- No retrieved study measured inference-time best-of-N with a VLM judge for frontier models.

## Q3. How well frontier VLMs judge their own rendered output (blind spots)

### Takeaway
VLM judges are measurably unreliable on exactly the things that matter for illustration QA: overlap, closely spaced shapes, counting and small details. They are also more lenient than humans and drift toward mid-range scores when uncertain. Use them for gross semantic checks ("is this recognisably a whale"). For geometry questions (overlap, counts, alignment), use programmatic checks or crop/zoom-and-simplify prompts.

### Cited Findings
- "Vision language models are blind" (ACCV 2024): across 7 trivial tasks (line intersections, overlapping circles, counting and so on), four SOTA VLMs averaged about 58%. The best was Claude 3.5 Sonnet at about 74–78%; humans score 100%. — [VLMs are blind (arXiv)](https://arxiv.org/html/2407.06581v4); [ACCV paper](https://openaccess.thecvf.com/content/ACCV2024/papers/Rahmanzadehgervi_Vision_language_models_are_blind_ACCV_2024_paper.pdf)
- Models fail most when shapes overlap or sit close together and approach 100% when shapes are widely spaced. Simplifying images raised one model's (Sonnet-3) overlapping-shape counting accuracy by 63 points. Linear probes on the vision encoders reach ≥ 99.47% on the same tasks, so the information is present but lost when decoded into language. — [VLMs are blind](https://arxiv.org/html/2407.06581v4)
- VectorGym: VLM judges are "more permissive than humans" and cluster around mid-range scores when uncertain. Judge-human correlation was weak for Text2SVG and editing even on ground-truth examples. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- IntroSVG used GPT-4o as its teacher critic but did not measure critic accuracy. Its zero-shot loops showed non-monotonic or flat metrics (GPT-5 CLIP dips after iteration 2, Grok-4 HPS stays flat), so critique does not reliably move every quality dimension. — [IntroSVG](https://arxiv.org/html/2603.09312v1)
- SVGenius: reading SVG *code* to answer perceptual questions also degrades steeply with complexity (Claude-3.7 Perceptual QA falls from 80.25% to 33.33%), so "judge from the code" is no substitute for looking at the render. — [SVGenius](https://arxiv.org/html/2506.03139)
- SGP-Bench: LLMs answering semantic questions from SVG programs alone are sometimes near chance, and they are inconsistent under simple translations or rotations of the program. — [Liner review of SGP-Bench](https://liner.com/review/can-large-language-models-understand-symbolic-graphics-programs)

### Inferences
- Self-critique prompt design: ask targeted yes/no questions per region. For example, "Crop: the hand region. How many fingers are visible?" works better than "rate this image 1–10". Render at high resolution and zoom into small parts, because overlap and closely spaced elements are the documented weak spot.
- Cheap programmatic checks should cover what VLMs miss: bounding-box overlap of named `<g>` ids, elements outside the viewBox, z-order, and counts of repeated parts.

### Gaps
- No 2025–2026 numbers were found on Claude 4.x or Gemini 3 accuracy as a critic of its own SVG renders specifically.

## Q4. Does a reference raster image to imitate or trace beat text-only generation?

### Takeaway
The evidence is mixed and indirect. When the goal is *pixel fidelity to an image*, image-conditioned trained models and tracers win by a wide margin, while frontier LLMs reproducing an image are mediocre (SSIM about 50–70). No source directly compared text-only against text-plus-reference-image generation by the same frontier LLM on illustration quality.

### Cited Findings
- RLRF Im2SVG: given the target image, Claude 3.7 / GPT-4o / Gemini-Flash-2.0 reached SSIM 69.33 / 66.91 / 60.21. A 7B model trained with RLRF reached SSIM 95.10, and tracers (LIVE, VTracer) reached about 88, but with 7k–100k-token SVGs. — [RLRF](https://arxiv.org/html/2505.20793v2)
- SVGenius Image-to-SVG SSIM is about 48–54 for Claude-3.7, GPT-4o and Gemini-2.0-Flash. — [SVGenius](https://arxiv.org/html/2506.03139)
- VectorGym: frontier models score higher on Sketch2SVG than on Text2SVG (for example, Gemini 3 Pro 78.56 vs 69.92, and Claude Sonnet 4.5 73.85 vs 69.19). The tasks and metrics differ, though, so this is not a controlled comparison. When the input sketch lacks colour, models "tend not to introduce new colors." — [VectorGym](https://arxiv.org/html/2603.29852v1)
- VectorFusion offers optional image-based initialisation for speed and fidelity. — [pytorch-svgrender docs](https://pytorch-svgrender.readthedocs.io/en/latest/_sources/vectorfusion.rst.txt)
- Chat2SVG's pipeline effectively uses a diffusion-generated raster as the target for path optimisation. That is the strongest evidence that a raster reference plus geometric optimisation beats an LLM-only template on detail. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)

### Inferences
- For a hand-coding agent, a reference raster is most useful for **pose, proportion and composition** (hand poses, animal silhouettes). Read the reference into a written spec of proportions and key points rather than asking the model to trace pixels, because LLM image-to-SVG pixel fidelity is weak. Automatic tracing gives fidelity, but the output is not flat or editable in style.

### Gaps
- No source ran a same-model, same-prompt ablation of text-only against text plus reference image on aesthetic or illustration quality.

## Q5. Practical limits: path complexity, token cost, and which shapes LLMs do badly

### Takeaway
LLMs are good at layouts of simple primitives. They get worse as SVG length and complexity grow, and they are consistently weak at geometrically complex organic paths and precise layouts. Training sets and benchmarks cap SVGs at a few thousand tokens.

### Cited Findings
- Chat2SVG says LLMs have "limitations in synthesizing geometrically complex paths" and "may produce imprecise visual layouts" (for example, a misplaced burger). Even the fixed-length SVG VAE struggled with intricate shapes such as a lion's mane. — [Chat2SVG](https://arxiv.org/html/2411.16602v1)
- RLRF: SFT models hallucinate or loop on complex images that need long SVGs, and their consistency degrades over long sequences. — [RLRF](https://arxiv.org/html/2505.20793v2)
- RLRF: frontier LLMs' Im2SVG outputs differed from ground-truth length by about +1.1k to +1.4k tokens. — [RLRF](https://arxiv.org/html/2505.20793v2)
- VectorGym filtered its training samples to 2k–8k tokens. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- SVGenius: every model degrades with complexity. Style transfer (cartoon, line, 3D) is the hardest task, with proprietary models at about 2.5–3.3 out of 5. Large models "falter at style abstraction." — [SVGenius](https://arxiv.org/html/2506.03139)
- VectorGym: models struggle to follow multi-step edits. — [VectorGym](https://arxiv.org/html/2603.29852v1)
- Practitioner, anecdotal: Simon Willison's "Generate an SVG of a pelican riding a bicycle" test (started October 2024 with 16 models) is still in use in 2026. A GLM-5.1 SVG was "excellent," but asking for animation broke the pelican's placement. — [Willison 2024](https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/); [Willison GLM-5.1, Apr 2026](https://simonwillison.net/2026/Apr/7/glm-51/)
- Willison now says "the correlation between pelican performance and actual model quality has been mostly severed," likely because such SVGs are now in the training data. — [OpenEnv docs quoting Willison](https://huggingface.co/docs/openenv/environments/pelican_svg); [HN discussion](https://hn.svelte.dev/item/49010129)

### Inferences
- Keep each LLM-written unit small (one part or one `<g>` at a time) and assemble the parts, rather than emitting one long SVG. The degradation over long sequences and multi-step edits points that way.
- The documented weak spots map onto the agent's struggles. Organic paths cover asteroids and animals. Layout precision covers composition. Small, overlapping details (hands) are also where VLM critics are weakest.

### Gaps
- No source gave quantitative per-category failure rates (hands, animals, perspective).
- No study gave a token-cost comparison of loop vs single-pass generation for frontier models.
