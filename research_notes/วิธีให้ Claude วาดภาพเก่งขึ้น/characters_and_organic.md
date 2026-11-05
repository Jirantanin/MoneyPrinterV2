# Characters, poses, hands and organic shapes for a code-drawing agent (SVG/JS)

Scope: practical ways for an AI coding agent that draws in SVG/JS (headless on Windows, output for commercial YouTube) to get readable flat-vector characters and organic shapes. Ranked by how practical each is, with examples, limits and evidence. The researcher ran about 15 searches and fetches; when a source is weak or vendor marketing, that is stated.

**Practicality ranking (researcher's synthesis; reasoning under each question's Inferences):**
1. **Parametric SVG puppet as a data package.** The agent draws each body part once, then poses it by rotating it around explicit pivots. This beats drawing every pose freehand.
2. **Procedural organic primitives.** Use a radial noise-displaced polygon for rocks and asteroids, the superformula for leaves, flowers and starfish, unions of circles for clouds and blobs, and perfect-freehand or rough.js for a hand-drawn edge.
3. **CC0 or commercially licensed parts libraries** (Open Peeps, DiceBear CC0 styles, Notionists, Lorelei). These can be mixed and matched without drawing anatomy at all, but the style may not match the channel's own look.
4. **Pose from 3D or video skeletons driving a 2D rig** (Animated Drawings-style retargeting, MediaPipe landmarks). The anatomy comes out right, but setup is heavy, and Animated Drawings is archived and not tested on Windows.
5. **Generate-then-trace** (image model, then vtracer or Recraft SVG, then rig). This has the highest style-drift and cleanup risk, and the traced output has no usable part separation for rigging.

---

## 1. How flat-style artists build characters that read well (construction rules an agent can follow)

### Takeaway
No primary Kurzgesagt character-construction guide was found. The general flat and cartoon rules are well established, though: build from simple geometric shapes, give stylised figures large heads (2 to 4 heads tall for chibi-like figures, against 7 to 8 for realistic adults), and simplify hands to mittens or to thumb plus finger block. Kurzgesagt's own statements confirm a rounded-shape, vibrant-colour style and characters cut into many separately rigged parts.

### Cited Findings
- Kurzgesagt describes its style as a mix of vector illustration, pixel-based illustration and infographics. It calls its characters a signature element, and the narrator's voiceover sets the animation timing. — [Kurzgesagt: Our video process](https://kurzgesagt.org/youtube/)
- Kurzgesagt's signature style centres on "rounded shapes and vibrant colors" and is produced by a team of art directors, illustrators and producers. — [U-Michigan Arts: Simple, Bright, Beautiful](https://artsatmichigan.umich.edu/ink/2019/09/27/simple-bright-beautiful-the-work-of-kurzgesagt)
- Kurzgesagt scenes are reportedly broken into hundreds or thousands of separate parts before animation, and each character and object is rigged. This comes from a secondary video summary, so it is moderate reliability. — [gist.ly summary of "How Kurzgesagt creates videos"](https://gist.ly/youtube-summarizer/how-kurzgesagt-creates-videos-1200-hours-of-science-art)
- Shape language: simple geometric forms carry personality and meaning quickly. — [BINUS: Character Design 101](https://binus.ac.id/bandung/dkv/2025/11/04/character-design-101-turning-simple-shapes-into-personality/)
- Cartoon bird construction: an oval body plus a circle head, a triangle beak, and wing, tail and feet shapes, each a simple primitive. A slightly tilted, imperfect head is recommended over a symmetric one to avoid stiffness. — [How to draw a cartoon bird (low-authority tutorial)](https://appmgss.impactfirst.co/post/how-to-draw-a-cartoon-bird)
- Proportions: realistic adults are about 7 to 8 heads tall, and chibi or stylised figures 2 to 4 heads tall, with the head at roughly 50 to 60% of the height in extreme chibi. — [Clip Studio Tips: chibi](https://tips.clip-studio.com/es-es/articles/4879?org=1); [Clip Studio: Easy steps to chibi characters](https://clipstudio.net/how-to-draw/archives/155423)
- Hand simplification: draw mittens or small ovals with fingers omitted, or split the hand into two shapes (the thumb and a block of four fingers). Finger counts of 4, 5 or none are all used, and the sources disagree on a "standard". — [Clip Studio: General tips on chibi art](https://tips.clip-studio.com/ja-jp/articles/4897?org=1); [Clip Studio Tips 4879](https://tips.clip-studio.com/es-es/articles/4879?org=1)
- Limbs on stylised figures are soft tapering cylinders with no muscle definition. One proportion check: the hand barely reaches the ear. — [Clip Studio Tips 4879](https://tips.clip-studio.com/es-es/articles/4879?org=1)

### Inferences
- **Rules an agent could encode** (synthesised from the above, not from a single source):
  - Fix a head unit H. Use about 2.5 to 3.5 H total height for a mascot or simple human, and keep a single style sheet with torso, limb and hand lengths in H.
  - Hands are always a mitten: one rounded rectangle or capsule plus one thumb capsule. Never draw separate fingers unless a gesture needs one (pointing = mitten plus one finger capsule).
  - Limbs are tapered capsules or noodle strokes (`stroke-linecap: round`) between joint points. This hides elbow and knee anatomy errors.
  - Silhouette test: fill the whole character in one colour, render it, and check the pose still reads. An agent can do this headlessly by rendering a black-fill version.
  - Use a small closed pose set (stand, walk-cycle keys, point, shrug, sit, surprise) rather than inventing new poses each shot.
- Kurzgesagt's "thousands of parts, each rigged" suggests the right mental model for an agent: draw parts once, then animate transforms rather than redrawing.
- Line of action: no good source was found in this pass (see Gaps). The common practice is to bend the torso spine along one C or S curve and keep the head on that curve.

### Gaps
- No primary, authoritative Kurzgesagt character-design breakdown, and no head-unit spec for their humans or birds. Their published material is pipeline-level only.
- No sourced rule set for "line of action" in flat characters. Several sources found were low-authority, SEO-generated pages.

---

## 2. Parametric and rigged 2D character systems (cut-out rigs, generators, code rigs)

### Takeaway
For an agent, the most practical route is a **JSON rig plus SVG parts plus a generic frame-driven renderer**: parts with explicit pivots, parents, layers and rotation limits, rendered deterministically per frame in Remotion or a headless browser. Commercial rig tools (Spine, Rive) have headless or Node rendering paths, but each character still has to be authored in their editors. Mix-and-match avatar libraries give licence-clean parts, but mostly as busts or static poses.

### Cited Findings
- **Data-package rig pattern (OpenMontage character-rigging skill):** keep runtime code generic and make each character a data package. The JSON has `character_id`, `rig_type: "svg_rig"`, `parts` (id, kind, layer, optional parent) and `joints` (pivot in artwork coordinates, plus a rotation range such as `[-20, 20]` for the head as a constraint). The skill's rules:
  - Split the character into independently transformable parts.
  - Keep eyes, pupils and mouth separate.
  - Make carried or touched props separate parts.
  - Use explicit SVG-coordinate pivots, because `transform-origin` behaviour is browser-defined.
  - Set layering explicitly; don't rely on SVG source order.
  - Animation must be frame-driven and deterministic (the Remotion model).
  — [skills.cat: openmontage/character-rigging](https://skills.cat/skills/calesthio/openmontage/character-rigging)
- Motion Canvas is an MIT-licensed TypeScript library that programs animations with generators, plus an editor with real-time preview. Custom 2D components are the natural home for a reusable character. No public reusable character-rig repo for Motion Canvas was found. — [Motion Canvas docs](https://motioncanvas.io/docs); [VideoZero motion-canvas skill](https://openskillindex.com/skills/videozero-skills-motion-canvas)
- **Spine:** the spine-canvaskit runtime renders Spine animations in any JS environment with WebAssembly, including Node.js, and explicitly supports headless or server rendering. — [Esoteric Software blog: spine-canvaskit](https://esotericsoftware.com/blog/spine-canvaskit-runtime-released)
- **Rive:** rendering to a bitmap is not supported directly in the React runtime. Rive's docs point to Remotion and Revideo for offline or server video rendering of Rive files. A third-party ComfyUI node drives a weighted, boned .riv character with external motion through Rive's runtime and renders MP4 or GIF. — [Rive docs: rendering to a bitmap](https://rive.app/docs/runtimes/react/rendering-to-a-bitmap.md); [Kimodo Render Rive Skinned Character](https://comfy.icu/node/Kimodo_RenderRiveSkin)
- **Open Peeps** (Pablo Stanley): public domain under CC0, free for commercial and personal use. It is built from "vector arms, legs, and emotions" as nested components, with standing and sitting poses and busts, claims more than 584,688 combinations, and ships ready-made Peeps as PNG and SVG. — [openpeeps.com](https://www.openpeeps.com/)
- **DiceBear** (MIT code, © Florian Körner). The licences of all 61 styles are listed on its licence page, and none are non-commercial:
  - **CC0 1.0 (42 styles):** Lorelei and Lorelei Neutral (remix of Lisa Wischofsky), Notionists and Notionists Neutral (remix of Zoish), Open Peeps, and all DiceBear-made styles, including Blobs, Critters, Planets, Shapes and Thumbs.
  - **CC BY 4.0, attribution required (14 styles):** Adventurer, Big Ears, Big Smile, Croodles, Dylan, Fun Emoji, Glyphs, Micah, Miniavs, Personas, Toon Head.
  - **"Free for personal and commercial use", artist's own terms:** Avataaars and Bottts (Pablo Stanley).
  — [DiceBear licenses](https://www.dicebear.com/licenses/)
- The npm package READMEs agree with this per-style licensing; for example, `@dicebear/open-peeps` is CC0 and `@dicebear/micah` is CC BY 4.0. — [npm @dicebear/open-peeps](https://npmjs.com/package/@dicebear/open-peeps); [npm @dicebear/micah](https://npmjs.com/package/@dicebear/micah)
- StretchyStudio is a free in-browser auto-rigging editor for layered PSD characters. It uses mesh deformation rather than bones, with DWPose pose detection or a heuristic skeleton. img2rig is a header-only C++ runtime for layered 2D characters (also on PyPI). — [GitHub MangoLion/stretchystudio](https://github.com/MangoLion/stretchystudio); [GitHub SSnemo/img2rig](https://github.com/SSnemo/img2rig); [PyPI img2rig](https://pypi.org/project/img2rig/)

### Inferences
- **Most practical for this repo:** a hand-rolled JSON-rig SVG puppet rendered by the existing headless HTML-to-MP4 path (the `doc_renderer/gfx_kit` style). The agent's weakness is drawing, not transforming. Drawing each part once, in a neutral T-pose, and then posing by rotation turns a drawing problem into a numeric one. Joint limits stop impossible poses.
- Spine and Rive are viable only if a human authors the rig in their editor. Spine has the more direct headless Node path. Spine's editor is commercial and its runtime licence terms were not checked here (see Gaps).
- Open Peeps and DiceBear are licence-clean for YouTube when you pick CC0 or "free for commercial" styles; CC BY styles need attribution in the description. These are avatar or bust systems, not animation rigs. Open Peeps' separate arm and leg components are the closest to rig-ready.
- These libraries' styles (hand-drawn line art for Open Peeps, Notion-like) won't match a glow or flat no-outline channel look without restyling.

### Gaps
- Spine runtime licence terms (the Spine Runtimes licence requires a Spine editor licence) and the Rive runtime licence were not checked in this pass. Verify before relying on either.
- No public Motion Canvas, Remotion or manim reusable character-rig library was found. The searches surfaced only general docs and the OpenMontage skill.
- Lottie and Moho rig export paths for headless rendering were not researched.

---

## 3. Pose sources: 3D mannequins, pose estimation, or mocap driving a flat 2D rig

### Takeaway
Meta's Animated Drawings is the clearest working example. It takes a 2D character with a joint hierarchy, retargets 3D BVH motion onto it, deforms it with ARAP and renders to MP4 or GIF, including headless via Mesa, and it accepts hand-supplied masks and joint files. It is MIT-licensed but archived (September 2025) and tested only on macOS and Ubuntu. MediaPipe Pose provides 2D and 3D landmarks in JS that could set limb angles of an SVG rig, but no ready SVG-puppet project was found.

### Cited Findings
- **Animated Drawings pipeline:**
  - Detect the humanoid figure.
  - Estimate its joints (OpenMMLab models).
  - Segment it into `mask.png` and `texture.png`.
  - Save the joints to `char_cfg.yaml`.
  - Deform with As-Rigid-As-Possible (ARAP) shape manipulation.
  - Apply BVH motion through a retarget config.
  - Output to an interactive window, `video.mp4` or a transparent `video.gif`.
  - Headless rendering: set `USE_MESA: True`.
  - Code, weights and the Amateur Drawings dataset are MIT, the ChildlikeSHAPES dataset is CC-BY 4.0, and the repo has been archived and read-only since September 3, 2025.
  - Tested on macOS Ventura and Ubuntu 18.04; other operating systems "may have issues". Docker may need 16 GB of RAM.
  - You can skip detection and supply your own `char_cfg.yaml`, mask and joints: "as long as they are valid, AnimatedDrawings will give you an animation."
  — [GitHub facebookresearch/AnimatedDrawings](https://github.com/facebookresearch/AnimatedDrawings)
- **Animated Drawings retargeting:** BVH joints map onto the 2D rig through a retarget config that chooses projection planes (frontal, sagittal or PCA) and depth order. Custom BVH skeletons need their own motion and retarget configs. BVH can come from RGB video through tools like Rokoko. — [AnimatedDrawings repo docs via Algolia DocSearch](https://docsearch.algolia.com/mcp/docs/repo/facebookresearch/animateddrawings); [HF mirror retargeter.py](https://huggingface.co/spaces/ygauravyy/nanee-animation/blame/main/animated_drawings/model/retargeter.py); [Meta developer blog, April 2023](https://developers.facebook.com/blog/post/2023/04/13/meta-os-animated-drawings/)
- **MediaPipe Pose Landmarker** (`@mediapipe/tasks-vision` on npm) outputs pose landmarks in image coordinates and in 3D world coordinates. — [Google AI Edge: Pose landmarker for Web](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js?authuser=8)
- Raw landmarks jitter. One third-party library smooths them by averaging over 8 frames. — [GitHub yousufkalim/mediapipe-pose-smooth](https://github.com/yousufkalim/mediapipe-pose-smooth)
- StretchyStudio uses DWPose pose detection to auto-rig layered characters. — [GitHub MangoLion/stretchystudio](https://github.com/MangoLion/stretchystudio)
- Kimodo Motion Bridge (a third-party ComfyUI node) bakes external motion onto Rive bones and renders MP4. This is a working example of "external skeleton motion drives a 2D bone rig". — [comfy.icu Kimodo Export Rive](https://comfy.icu/node/Kimodo_ExportRive)

### Inferences
- **The cheapest agent-native version:** keep a library of 2D joint-angle poses, either extracted once from MediaPipe on reference photos or video, or from BVH frames projected to the frontal plane. Store them as JSON (`{shoulder_L: -35, elbow_L: 70, ...}`) and apply them to the JSON rig from section 2. This copies Animated Drawings' retarget idea (project 3D bones onto a plane, take the angles) without its Linux and Mesa stack.
- Animated Drawings itself is better used as a reference design than a dependency: it is archived and not tested on Windows. Running it would probably need WSL or Docker, which the user doesn't use per project memory.
- ARAP mesh deformation, as in Animated Drawings and StretchyStudio, suits a raster or textured character. Cut-out rotation of separate parts is simpler and cleaner for flat vector parts.

### Gaps
- No public example was found of an agent or script mapping MediaPipe or OpenPose landmarks onto an SVG cut-out puppet.
- Mixamo's licence terms for using its animations (as BVH or FBX converted to 2D) in commercial video were not verified in this pass.
- Blender-to-2D-pose export scripts were not researched. The repo memory notes an existing Blender/MPFB motion-lab test outside the repo, which may be relevant.

---

## 4. Organic shapes in code (rocks, asteroids, animals, plants, clouds) and flat texture

### Takeaway
Several robust, well-known techniques exist, but no SVG-specific tutorials were found; the evidence is 3D displacement analogues and general libraries. The best options are:
- **Rocks and asteroids:** a radial noise-displaced polygon.
- **Leaves, flowers, starfish:** the superformula.
- **Organic edges:** perfect-freehand (MIT) and rough.js (MIT).
- **Texture:** grain or noise overlays plus a clipped highlight or shadow shape.

### Cited Findings
- **Rocks and asteroids:** start from a sphere, push each vertex along its normal by a noise value, then optionally add a displacement map. A JS `displaceAlongNormals` example exists. — [Babylon.js forum: procedural rock generator](https://forum.babylonjs.com/t/procedural-rock-generator-any-ideas/9568); [hive.blog creative coding #66](https://hive.blog/hive-196387/@femdev/learn-creative-coding-66-procedural-mesh-generation)
- Variety tip from game development: tuning noise and polycount alone was slow. Deforming several hand-made base shapes with noise displacement gave better variety. — [Unity discussions: procedural asteroid generation](https://discussions.unity.com/t/procedural-asteroid-generation/639383)
- Research-grade asteroid surfaces use spot noise for craters and boulders, plus Gabor noise for fine detail. — [Uni Bremen: Procedural generation of asteroids](https://cgvr.cs.uni-bremen.de/research/procedural_asteroid/)
- **Superformula** (Gielis, 2003, American Journal of Botany) generalises circles and superellipses into polygons, stars and plant-like forms. A generalised version fits some starfish and leaf shapes. Supergraphx used it for compact 2D and 3D graphics files. Hello Games' Sean Murray cited it for geological forms in No Man's Sky. — [SIGGRAPH history: Variational superformula curves](https://history.siggraph.org/?p=99344); [Generalized Gielis equation (Symmetry 2020)](https://figshare.utas.edu.au/articles/journal_contribution/The_generalized_Gielis_geometric_equation_and_its_application/22988051); [80.lv: Secret formula behind No Man's Sky](https://80.lv/articles/secret-formula-behind-no-mans-skys-endless-worlds/)
- Critics say the superformula's significance was overstated in the media. — [National Academies: The Secret Life of Numbers](https://www.nationalacademies.org/read/11543/chapter/39)
- The 80.lv article mentions a patent claim on generating shapes from the parameterised formula. — [80.lv](https://80.lv/articles/secret-formula-behind-no-mans-skys-endless-worlds/)
- **perfect-freehand** (MIT): `getStroke(points)` turns `[x, y, pressure?]` points into an outline polygon.
  - Options: `size`, `thinning`, `smoothing`, `streamline`, `simulatePressure`, `easing`, and start and end `taper`.
  - `getSvgPathFromStroke` converts the result to SVG path data.
  - It suits tapered organic strokes: tails, stems, whiskers, grass, hair.
  — [GitHub steveruizok/perfect-freehand](https://github.com/steveruizok/perfect-freehand)
- **rough.js** (MIT, under 9 kB) draws sketchy, hand-drawn-style shapes to Canvas or SVG. — [JSR @rough/roughjs](https://jsr.io/@rough/roughjs@6.0.5)
- **Flat-art texture:** build grain from two identical shapes, a base colour and a grain colour shown through a mask, and lower the grain's opacity. Grain can also come from gradients plus dissolve or blend-mode effects. Shading on flat vectors is often painted with grain shader brushes for highlight and shadow. — [MediaLoot: noise in vector graphics](https://medialoot.com/blog/how-to-add-noise-to-your-vector-graphics-in-illustrator/); [Tuts+: grain noise textures in Illustrator](https://design.tutsplus.com/tutorials/how-to-make-grain-noise-textures-in-illustrator--cms-40662); [Shutterstock: techniques to transform flat design vectors](https://www.shutterstock.com/blog/techniques-transform-flat-design-vectors); [Spoon Graphics: grainy shading](https://blog.spoongraphics.co.uk/tutorials/videos/how-to-add-grainy-shading-to-your-photoshop-art)

### Inferences (techniques, synthesised; not individually sourced)
- **Asteroid or rock in SVG:**
  - Place 12 to 24 points around a circle and set each radius to `r * (1 + a*noise(cosθ, sinθ, seed))`, sampled on a circle so the outline closes seamlessly.
  - Smooth with a Catmull-Rom spline, or keep it polygonal for "low-poly rock".
  - Add 3 to 6 craters, each an ellipse with a darker crescent offset towards the light.
  - Clip one lighter band on the lit side and one darker band on the far side (offset copies of the same outline intersected with the shape), which gives "gradient bands".
  - This is the 2D form of the sourced sphere-displacement method.
- **Clouds and blobs:** a union of 4 to 8 circles on a baseline, merged by a small blur-and-threshold (an SVG metaball-style filter: `feGaussianBlur` plus a steep `feColorMatrix` alpha). Alternatively, compute the outer outline geometrically for a crisp flat edge.
- **Plants:** the superformula for leaves and petals. Stems and grass as perfect-freehand tapered strokes along a bezier, with a slight per-instance seed jitter so repeats don't look cloned.
- **Animals:** the same construction as section 1. Build from primitives (ellipse body, circle head, triangle ears or beak), join them with a capsule or union, and keep the parts separate for rigging. Use a superformula or noise outline only for fur, mane or shell silhouettes.
- **Kurzgesagt-like finish:** a fine speckle or stipple overlay (an SVG `feTurbulence` grain clipped to the shape at low opacity), a thin lighter rim along the lit edge (a stroke clipped inside the shape, offset towards the light), and 2 to 3 flat tone bands rather than smooth gradients. No primary Kurzgesagt source confirms these details (see Gaps).
- Superformula patent caution: the patent's status and scope weren't checked. Implementing a published equation in your own code for video art is low-risk, but this is not legal advice.

### Gaps
- No SVG- or JS-specific tutorial for asteroid or rock outlines was found. The method is adapted from 3D sources.
- No primary source documents Kurzgesagt's specific texture vocabulary (speckles, rim light, bands). The rim-light search found only a Blender forum post.
- Metaball SVG filter recipes and polygon-offset or union libraries (for example Clipper, paper.js boolean ops) were not researched in this pass.

---

## 5. Generate-then-trace (image model, then vector, then rig) and its pitfalls

### Takeaway
Feasible but the least agent-friendly route.
- **Tracers:** they are deterministic (vtracer) and give compact stacked shapes, but no semantic parts.
- **Native-vector generators:** Recraft's claims of clean layers are mostly vendor or reseller marketing, and it has style locks but no character-identity lock.
- **Layer decomposition:** this needs separate research models (See-through, SIGGRAPH 2026), trained on anime only.
- **Text- or image-to-SVG LLMs:** StarVector and OmniSVG exist, but their own authors note context limits on complex SVGs.

### Cited Findings
- vtracer (Rust, open source):
  - It converts raster images to SVG with colour or black-and-white modes, curve fitting (`pixel`, `polygon`, `spline`) and presets (`bw`, `poster`, `photo`).
  - It produces fewer shapes than Illustrator's Image Trace because it stacks shapes and avoids holes.
  - It is a deterministic tracer, not AI.
  — [docs.rs vtracer 0.6.5](https://docs.rs/crate/vtracer/0.6.5); [lib.rs vtracer](https://lib.rs/crates/vtracer)
- Tracing hygiene: crop, raise contrast, convert to pure black and white, and remove specks before tracing, then simplify nodes and delete stray points afterwards. This advice comes from a lettering guide, so it is general. — [Jeff Bullas forum thread](https://www.jeffbullas.com/thread/can-ai-turn-hand-drawn-lettering-into-clean-vector-paths-for-printing-and-scaling/)
- Hosted vectoriser wrappers advertise a "character" mode for cartoon or mascot art. Their claims to beat Illustrator are unverified marketing. — [Replicate merahburam/vectorizer-v2](https://replicate.com/merahburam/vectorizer-v2)
- Recraft added vector (SVG) output with V2 (March 2024). Its docs say V2 can generate icon sets with consistent line width and corners. The custom style system creates reusable style tokens from reference images. — [Recraft docs: V2](https://www.recraft.ai/docs/recraft-models/recraft-V2)
- Claims that v4 Pro gives "perfectly layered SVG" needing "little to no cleanup" come from a third-party host's marketing. — [RunDiffusion: Recraft v4 Pro](https://learn.rundiffusion.com/recraft-v4-pro-on-rundiffusion)
- A Recraft v4 review says scenes that depend on believable gesture or interaction between figures "don't land well". The review is secondary and low-to-moderate reliability. — [pasqualepillitteri.it review](https://pasqualepillitteri.it/en/news/769/recraft-ai-v4-review-2026-vector-svg-midjourney-dalle)
- **See-through** (arXiv February 2026, SIGGRAPH 2026):
  - It decomposes one anime illustration into inpainted, semantically separated RGBA body-part layers with drawing order and pseudo-depth.
  - It was trained on supervision derived from Live2D models.
  - Its README says a full image-to-Live2D pipeline still needs finer, deformation-aware splits and a rigging step.
  - It is anime- and VTuber-specific.
  — [arXiv 2602.03749](https://arxiv.org/abs/2602.03749v1); [GitHub shitagaki-lab/see-through](https://github.com/shitagaki-lab/see-through)
- **Bunraku** (preprint, July 2026) predicts layer-wise mesh deformation with a Transformer and notes that a poor initial layer decomposition limits the final rig. — [alphaxiv 2607.27348](https://www.alphaxiv.org/abs/2607.27348)
- **StarVector** (CVPR 2025) is a multimodal LLM that generates SVG code and introduced SVG-Bench, with 10 datasets across image-to-SVG, text-to-SVG and diagrams. Its own limitations: a 16k-token context that is "inadequate for complex SVGs", and minimal visual feedback. — [arXiv 2312.11556](https://arxiv.org/abs/2312.11556); [CVPR 2025 open access](https://openaccess.thecvf.com/content/CVPR2025/html/Rodriguez_StarVector_Generating_Scalable_Vector_Graphics_Code_from_Images_and_Text_CVPR_2025_paper.html)
- **OmniSVG** targets icons up to complex anime characters, with the MMSVG-2M dataset and MMSVG-Bench. Its results are self-reported only. — [Liner review of OmniSVG](https://liner.com/review/omnisvg-unified-scalable-vector-graphics-generation-model)

### Inferences
- Pitfalls to expect:
  - Traced output is one flat stack of colour regions. There are no arm or head groups and no hidden geometry behind limbs, so it can't be rotated as a rig without inpainting.
  - Path counts and nodes bloat on gradients or anti-aliasing.
  - The palette drifts away from the channel palette.
  - Each new image of "the same" character drifts in proportions and details unless a strong reference or style lock is used. Even then, style locks target style, not identity.
- Tracing is most useful for single-pose props or backgrounds, or as a reference underlay the agent redraws cleanly from primitives.
- StarVector's "minimal visual feedback" limitation supports a render-and-look loop for any code-drawing agent: render the PNG, inspect it, revise.

### Gaps
- No independent benchmark of LLM or SVG-model quality specifically on characters or hands was found.
- No hard evidence on the identity consistency of character-consistency image models (for example reference-image features in current image models) was found in this pass.
- Recraft's commercial-use terms, and vtracer's licence (believed MIT but not verified here), were not checked.
