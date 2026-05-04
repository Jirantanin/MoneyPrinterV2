"""
Podcast.py — Video Podcast pipeline class.

Standalone class (does not extend YouTube.py). Each public step method
corresponds to one downstream phase:
  generate_script()  → Phase 5
  generate_assets()  → Phase 6
  render()           → Phase 7
  upload()           → Phase 8

run() calls all four steps in order.
"""

import json
import math
import os
import re
import subprocess
import time
from datetime import datetime

from config import (
    ROOT_DIR,
    get_podcast_audio_retry_count,
    get_podcast_image_retry_count,
    get_podcast_narrator,
    get_podcast_script_model,
    get_podcast_metadata_system_prompt,
    get_podcast_script_system_prompt,
    get_podcast_style_prompt,
    get_podcast_thumbnail_system_prompt,
    get_script_sentence_length,
    get_tts_edge_rate,
    get_tts_edge_voice,
    get_tts_edge_thai_rate,
    get_tts_edge_thai_voice,
    get_kling_access_key,
    get_kling_secret_key,
)
from image_provider import generate_image
from kling_provider import generate_video_from_image
from llm_provider import generate_text, generate_text_structured
from classes.Tts import TTS
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def _slugify_topic(topic: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (topic or "").lower()).strip("-")
    if normalized:
        return normalized
    compact = re.sub(r"\s+", "-", (topic or "").strip())
    if compact:
        return f"topic-{abs(hash(compact)) % 1000000:06d}"
    return "untitled"


def _safe_format(template: str, **kwargs) -> str:
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return str(template).format_map(_SafeDict(**kwargs))


def _build_direction_block(creative_direction: str) -> str:
    cleaned = (creative_direction or "").strip()
    if not cleaned:
        return ""

    return (
        "Creative direction:\n"
        f"{cleaned}\n\n"
        "Use this only as a style, mood, and imagery guide. "
        "Do NOT change the core topic or invent a different central subject.\n"
    )


def _build_topic_guardrail_block(topic: str, creative_direction: str, language: str) -> str:
    topic_clean = (topic or "").strip()
    direction_clean = (creative_direction or "").strip()
    key_concepts = []

    if topic_clean:
        key_concepts.append(topic_clean)
    if direction_clean:
        key_concepts.append(direction_clean)

    concepts_text = "\n".join(f"- {item}" for item in key_concepts if item)
    if not concepts_text:
        concepts_text = "- Stay tightly anchored to the exact topic provided by the user."

    return (
        "Hard topic guardrails:\n"
        f"- The exact central topic is: {topic_clean}\n"
        "- Every scene must directly explain, question, or deepen that exact topic.\n"
        "- Reuse the concrete concepts named by the user naturally across the episode.\n"
        "- For abstract topics, stay analytical and reflective. Do NOT invent external lore or plot devices.\n"
        "- Do NOT invent archaeologists, secret organizations, ancient ruins, hidden symbols, forbidden documents, "
        "aliens, mythologies, or supernatural systems unless the user explicitly asked for them.\n"
        f"- Write ALL narration in {language}. Do not switch languages.\n"
        "Key concepts from the user that should remain visible in the writing:\n"
        f"{concepts_text}\n"
    )


def _build_topic_interpretation_block(topic: str, creative_direction: str) -> str:
    topic_clean = (topic or "").strip().lower()
    direction_clean = (creative_direction or "").strip().lower()
    combined = f"{topic_clean}\n{direction_clean}"

    if "ความทรงจำ" in combined or "memory" in combined:
        lines = [
            "Topic interpretation you must follow:",
            "- This episode is about memory, not dreams, not sleep, not ancient mysteries, and not unrelated psychology topics.",
            "- Explain that memory is reconstructed rather than replayed exactly like a recording.",
            "- Include the idea of false memory, distortion, suggestion, or emotional influence on recall.",
            "- Explore what unreliable memory means for identity, truth, and personal certainty.",
        ]
        if "ลูกปัด" in combined or "bead" in combined:
            lines.append(
                "- Reuse the user's bead metaphor across multiple scenes: the mind strings fragments together like beads until they feel like a memory."
            )
        return "\n".join(lines) + "\n"

    return ""


def _generate_image_prompt(narration: str, model_name: str | None = None) -> str:
    """Generate a visual image prompt for a single narration scene."""
    try:
        raw = generate_text(
            "You generate concise visual image prompts for podcast scenes.\n"
            "IMPORTANT: The image prompt MUST be written in English only. Never use Thai or other non-Latin scripts in the image prompt.\n"
            "If there is any text shown in the image, it must be in English.\n\n"
            f"Write a vivid visual image prompt for this narration:\n{narration}\n\n"
            "Return only the image prompt, no explanation, no label, no preamble.",
            model_name=model_name,
        )
        result = raw.strip()
        if result:
            return result
    except Exception:
        pass
    # Fallback: use narration text itself as the image prompt
    return narration[:300]

def _generate_scene_title(narration: str, model_name: str | None = None) -> str:
    """Generate a short 1-4 word summarizing title for a narration scene."""
    try:
        prompt = (
            "Summarize the following narration in a short, punchy title (exactly 1-4 words). "
            "Use the SAME language as the narration (e.g., if the narration is in Thai, the title MUST be in Thai). "
            "Do NOT use markdown, do NOT use quotes, just return the plain title text.\n\n"
            f"NARRATION:\n{narration}"
        )
        title = generate_text(prompt, model_name=model_name).strip()
        # Basic cleanup: remove quotes, trailing periods, or markdown fences
        title = title.replace('"', '').replace("'", '').strip('.')
        if "```" in title:
            title = title.split("```")[-1].strip()
        return title[:100]
    except Exception:
        return ""


SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_title": {"type": "string"},
                    "narration": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["scene_title", "narration", "image_prompt"],
            },
        }
    },
    "required": ["scenes"],
}


TOPIC_BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "topic_anchor": {"type": "string"},
        "core_thesis": {"type": "string"},
        "required_concepts": {"type": "array", "items": {"type": "string"}},
        "forbidden_drifts": {"type": "array", "items": {"type": "string"}},
        "recurring_motifs": {"type": "array", "items": {"type": "string"}},
        "act_1_focus": {"type": "string"},
        "act_2_focus": {"type": "string"},
        "act_3_focus": {"type": "string"},
        "outro_focus": {"type": "string"},
        "visual_world": {"type": "string"},
    },
    "required": [
        "topic_anchor",
        "core_thesis",
        "required_concepts",
        "forbidden_drifts",
        "recurring_motifs",
        "act_1_focus",
        "act_2_focus",
        "act_3_focus",
        "outro_focus",
        "visual_world",
    ],
}


class Podcast:
    """Automates the full Video Podcast pipeline: script → assets → render → upload."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    TOKEN_PATH = os.path.join(ROOT_DIR, "token.json")

    def __init__(
        self,
        topic: str = "",
        language: str = "English",
        tts_source: str = "edge",
        creative_direction: str = "",
        visual_style: str = "",
        script_mode: bool = False,
        raw_script: str = "",
    ) -> None:
        self.topic = topic
        self.language = language
        self.tts_source = (tts_source or "edge").lower()
        self.creative_direction = (creative_direction or "").strip()
        self.visual_style = (visual_style or "").strip()
        self.script_mode = script_mode
        self.raw_script = (raw_script or "").strip()
        self.narrator = get_podcast_narrator()
        self.style_prompt = self.visual_style if self.visual_style else get_podcast_style_prompt()
        self.episode_dir: str = ""
        self.metadata: dict = {}

    def _compile_topic_brief(self, topic: str, script_model: str) -> dict:
        prompt = (
            f"Create a writing brief for a podcast episode about: {topic}\n\n"
            f"{_build_direction_block(self.creative_direction)}"
            "Interpret the user's actual topic as literally and faithfully as possible.\n"
            "This brief will control a later script generator, so it must prevent topic drift.\n"
            "Do NOT turn the topic into a different theme just because it sounds poetic, mysterious, or philosophical.\n"
            "For abstract topics, explain the real idea directly.\n"
            "Required output rules:\n"
            "- topic_anchor must restate the exact topic in one line.\n"
            "- core_thesis must explain the actual idea the episode should explore.\n"
            "- required_concepts must be concrete concepts, phrases, or angles that should appear across the episode.\n"
            "- forbidden_drifts must list topic substitutions or wrong directions the writer must avoid.\n"
            "- recurring_motifs should include any user-provided metaphor or recurring image.\n"
            "- act_1_focus, act_2_focus, act_3_focus, and outro_focus must describe what each section should do.\n"
            "- visual_world should describe the visual feeling while staying consistent with the real topic.\n"
        )
        raw = generate_text_structured(
            prompt=prompt,
            system_prompt=(
                f"Create a tight topic brief in {self.language}. "
                "Be literal, precise, and faithful to the user's topic. "
                "Do not invent a different subject."
            ),
            schema=TOPIC_BRIEF_SCHEMA,
            model_name=script_model,
        )
        brief = json.loads(raw)
        brief["topic_anchor"] = topic
        if self.creative_direction:
            direction = self.creative_direction.strip()
            if direction not in brief["required_concepts"]:
                brief["required_concepts"].insert(0, direction)
        if topic not in brief["required_concepts"]:
            brief["required_concepts"].insert(0, topic)
        brief["required_concepts"] = [str(x).strip() for x in brief["required_concepts"] if str(x).strip()][:8]
        brief["forbidden_drifts"] = [str(x).strip() for x in brief["forbidden_drifts"] if str(x).strip()][:8]
        brief["recurring_motifs"] = [str(x).strip() for x in brief["recurring_motifs"] if str(x).strip()][:6]
        return brief

    def _load_script_scenes(self) -> list:
        if not self.episode_dir:
            raise ValueError(
                "episode_dir is not set. Call generate_script() before generate_assets()."
            )

        script_path = os.path.join(self.episode_dir, "script.json")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"script.json not found at {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            scenes = json.load(f)

        if not scenes:
            raise ValueError("script.json is empty")
        return scenes

    def _scene_paths(self, scene_index: int) -> tuple[str, str]:
        scene_num = str(scene_index).zfill(2)
        image_path = os.path.join(self.episode_dir, f"scene_{scene_num}.png")
        audio_path = os.path.join(self.episode_dir, f"scene_{scene_num}.wav")
        return image_path, audio_path

    def _generate_scene_image_with_retry(self, image_prompt: str, image_path: str, scene_number: int) -> None:
        last_error = None
        max_attempts = max(1, get_podcast_image_retry_count())
        for attempt in range(1, max_attempts + 1):
            try:
                result = generate_image(image_prompt, image_path)
                if result is None or not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                    raise RuntimeError("image provider did not return a valid image")
                return
            except Exception as exc:
                last_error = exc
                if os.path.exists(image_path):
                    os.remove(image_path)
                print(
                    f"  Warning: image generation failed for scene {scene_number} "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                if attempt < max_attempts:
                    time.sleep(2)
        raise RuntimeError(
            f"Scene {scene_number}: image generation failed after {max_attempts} attempts: {last_error}"
        ) from last_error

    def _generate_scene_audio_with_retry(self, narration: str, audio_path: str, scene_number: int) -> None:
        last_error = None
        mp3_path = audio_path.replace(".wav", ".mp3")
        max_attempts = max(1, get_podcast_audio_retry_count())
        for attempt in range(1, max_attempts + 1):
            try:
                if self.language == "Thai" and self.tts_source == "elevenlabs":
                    TTS().synthesize_elevenlabs(narration, output_file=audio_path)
                elif self.language == "Thai" and self.tts_source == "gemini":
                    TTS().synthesize_gemini(narration, output_file=audio_path)
                elif self.language == "Thai":
                    TTS().synthesize(
                        narration,
                        output_file=audio_path,
                        voice=get_tts_edge_thai_voice(),
                        rate=get_tts_edge_thai_rate(),
                    )
                else:
                    TTS().synthesize(
                        narration,
                        output_file=audio_path,
                        voice=get_tts_edge_voice(),
                        rate=get_tts_edge_rate(),
                    )

                if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                    raise RuntimeError("tts provider did not return a valid wav file")
                return
            except Exception as exc:
                last_error = exc
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                print(
                    f"  Warning: audio generation failed for scene {scene_number} "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                if attempt < max_attempts:
                    time.sleep(2)
        raise RuntimeError(
            f"Scene {scene_number}: audio generation failed after {max_attempts} attempts: {last_error}"
        ) from last_error

    def _generate_scene0_video(self, image_path: str, scene: dict, video_path: str) -> None:
        """Generate an animated video clip for scene 0 using Kling image-to-video."""
        access_key = get_kling_access_key()
        secret_key = get_kling_secret_key()
        if not access_key or not secret_key:
            print("  Skipping scene 0 video: Kling keys not configured.")
            return

        image_prompt_excerpt = scene.get("image_prompt", "")[:200]
        prompt = f"Gentle ambient camera motion, slow zoom in. {image_prompt_excerpt}"
        print("  Generating scene 0 video via Kling (this takes ~1-2 min)...")
        try:
            generate_video_from_image(
                image_path=image_path,
                prompt=prompt,
                access_key=access_key,
                secret_key=secret_key,
                output_path=video_path,
                duration=5,
            )
            print(f"  Scene 0 video ready: {video_path}")
        except Exception as exc:
            print(f"  Warning: Kling video generation failed: {exc}")
            if os.path.exists(video_path):
                os.remove(video_path)

    def generate_scene_assets(self, scene_index: int, force_image: bool = False, force_audio: bool = False) -> None:
        scenes = self._load_script_scenes()
        if scene_index < 0 or scene_index >= len(scenes):
            raise ValueError(f"scene_index must be between 0 and {len(scenes) - 1}")

        scene = scenes[scene_index]
        image_path, audio_path = self._scene_paths(scene_index)
        scene_number = scene_index + 1

        if force_image and os.path.exists(image_path):
            os.remove(image_path)
        if force_audio and os.path.exists(audio_path):
            os.remove(audio_path)
        mp3_path = audio_path.replace(".wav", ".mp3")
        if force_audio and os.path.exists(mp3_path):
            os.remove(mp3_path)

        if not os.path.exists(image_path):
            self._generate_scene_image_with_retry(scene["image_prompt"], image_path, scene_number)

        if not os.path.exists(audio_path):
            self._generate_scene_audio_with_retry(scene["narration"], audio_path, scene_number)

    def generate_script(self, topic: str) -> list:
        """Generate a 20-scene podcast script using a 3-call LLM loop.

        Structure: intro(1) + act1(6) + act2(6) + act3(6) + outro(1) = 20 scenes.
        Running summaries are injected as context between LLM calls to prevent
        Ollama context overflow on longer topics.

        Each scene dict contains:
            - narration (str): Spoken narration text for TTS.
            - image_prompt (str): Visual description for image generation.

        The style_prompt prefix is prepended to every image_prompt before
        persisting to ensure visual consistency across scenes.

        Script is written to .mp/podcast_{slug}_{YYYYMMDD}/script.json.

        Args:
            topic: The podcast topic string.

        Returns:
            List of 14 scene dicts.
        """
        narrator = get_podcast_narrator()
        script_model = get_podcast_script_model()
        sentence_length = max(1, get_script_sentence_length())
        system_prompt = _safe_format(
            get_podcast_script_system_prompt(),
            narrator_name=narrator["name"],
            narrator_persona=narrator["persona"],
            language=self.language,
            topic=topic,
            creative_direction=self.creative_direction,
        )
        direction_block = _build_direction_block(self.creative_direction)
        topic_guardrail_block = _build_topic_guardrail_block(
            topic=topic,
            creative_direction=self.creative_direction,
            language=self.language,
        )
        topic_interpretation_block = _build_topic_interpretation_block(
            topic=topic,
            creative_direction=self.creative_direction,
        )
        topic_brief = self._compile_topic_brief(topic, script_model)
        topic_brief_json = json.dumps(topic_brief, ensure_ascii=False, indent=2)

        # --- Call 1: intro(1) + act1(6) = 7 scenes ---
        prompt_1 = (
            f"Create a podcast script about: {topic}\n\n"
            f"{direction_block}"
            f"{topic_guardrail_block}\n"
            f"{topic_interpretation_block}\n"
            f"Locked topic brief:\n{topic_brief_json}\n\n"
            "Generate EXACTLY 7 scenes:\n"
            "  Scene 1: START IN MEDIA RES — begin with a specific real event, a real person's name, a real date, or a real moment of danger or wonder. The very FIRST sentence must be a scene-setter that makes the listener freeze. NO 'today we explore', NO 'have you ever wondered', NO warm-up. Hook first, context second.\n"
            "  Scenes 2-7: Act 1 -- establish the background, context, and key facts.\n\n"
            f"Act 1 focus to follow: {topic_brief['act_1_focus']}\n"
            f"Each scene needs a 'scene_title' (a short 1-4 word summarizing title in the same language as the podcast), "
            f"a 'narration' (about {sentence_length} sentences of engaging spoken text), "
            "and an 'image_prompt' (vivid visual description for an illustration, MUST be in English only — never use Thai or non-Latin text in image prompts; any text shown in the image must also be in English).\n"
            f"The image_prompt will be prefixed with this style: '{self.style_prompt[:80]}'. "
            "Do NOT add keywords that contradict this style. "
            "For example, if the prefix is flat design/Kurzgesagt — do NOT add 'cinematic', 'photorealistic', '8K', 'dark mood'. "
            "If the prefix is cinematic realism — do NOT add 'flat design', 'cartoon', 'vector art'.\n"
            "The narration should sound natural for voice-over and stay directly tied to the topic.\n"
            "IMPORTANT: Do NOT include section headers, act labels, or structural markers like 'Section 1:', 'Act 1:', 'Part 1:' inside the narration text. Narration must flow as natural spoken audio only.\n"
            "The image_prompt should visualize the same idea as the narration, not a different concept.\n"
            "Do NOT invent superhero-like characters, comic-book heroes, or recurring protagonists unless the user "
            "explicitly asked for a character-driven story.\n"
            "If people appear in the image, keep them anonymous, ordinary, and directly relevant to the idea being explained.\n"
            "If the user provided a metaphor, motif, or recurring image in the creative direction, keep it visible "
            "across multiple scenes.\n"
            "Use the required_concepts from the locked topic brief. Avoid everything in forbidden_drifts.\n"
            "Return EXACTLY 7 scenes, no more, no fewer."
        )
        raw_1 = generate_text_structured(
            prompt=prompt_1,
            system_prompt=system_prompt,
            schema=SCENE_SCHEMA,
            model_name=script_model,
        )
        try:
            scenes_1 = json.loads(raw_1)["scenes"]
            if len(scenes_1) != 7:
                raise ValueError(f"Expected 7 scenes, got {len(scenes_1)}")
        except (json.JSONDecodeError, KeyError, ValueError):
            # Retry once with emphatic count instruction
            raw_1 = generate_text_structured(
                prompt=f"You MUST return EXACTLY 7 scenes. No more, no fewer.\n\n{prompt_1}",
                system_prompt=system_prompt,
                schema=SCENE_SCHEMA,
                model_name=script_model,
            )
            try:
                scenes_1 = json.loads(raw_1)["scenes"]
                if len(scenes_1) != 7:
                    raise ValueError(f"Call 1 retry returned {len(scenes_1)} scenes, expected 7")
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"LLM call 1 returned invalid JSON after retry: {exc}") from exc

        # --- Summary 1: summarise Call 1 narrations ---
        narrations_1 = "\n\n".join(s["narration"] for s in scenes_1)
        summary_1 = generate_text(
            f"Summarize the following podcast narration in 3-5 sentences.\n"
            f"Keep the summary anchored to this exact topic: {topic}\n"
            "Preserve the core thesis, key claims, and user-provided concepts.\n"
            "Do NOT rename the topic or replace it with a different mystery, plot, or external story.\n\n"
            f"{topic_interpretation_block}\n"
            f"Locked topic brief:\n{topic_brief_json}\n\n"
            + narrations_1,
            model_name=script_model,
        )

        # --- Visual Summary 1: visual elements from Call 1 image prompts ---
        visual_summary_1 = generate_text(
            "Summarize the key visual elements from these image descriptions "
            "(main characters and their appearance, locations, color palette, lighting mood) "
            "in 2-3 sentences. Preserve recurring motifs explicitly mentioned by the user. "
            "Do NOT introduce new symbols or story worlds that are not already present.\n\n"
            + "\n---\n".join(s["image_prompt"] for s in scenes_1),
            model_name=script_model,
        )

        # --- Call 2: act2(6) = 6 scenes ---
        prompt_2 = (
            f"Story so far:\n{summary_1}\n\n"
            f"Visual style established in earlier scenes:\n{visual_summary_1}\n"
            "Maintain these visual elements consistently in all new image_prompts.\n\n"
            f"Continue the podcast about: {topic}\n\n"
            f"{direction_block}"
            f"{topic_guardrail_block}\n"
            f"{topic_interpretation_block}\n"
            f"Locked topic brief:\n{topic_brief_json}\n\n"
            "Generate EXACTLY 6 scenes for Act 2 -- deepen the story, introduce "
            "complications or surprising revelations, and build tension.\n\n"
            f"Act 2 focus to follow: {topic_brief['act_2_focus']}\n"
            f"Each scene needs a 'scene_title' (a short 1-4 word summarizing title in the same language as the podcast), "
            f"a 'narration' (about {sentence_length} sentences of engaging spoken text), "
            "and an 'image_prompt' (vivid visual description for an illustration, MUST be in English only — never use Thai or non-Latin text in image prompts; any text shown in the image must also be in English).\n"
            f"The image_prompt will be prefixed with this style: '{self.style_prompt[:80]}'. "
            "Do NOT add keywords that contradict this style. "
            "For example, if the prefix is flat design/Kurzgesagt — do NOT add 'cinematic', 'photorealistic', '8K', 'dark mood'. "
            "If the prefix is cinematic realism — do NOT add 'flat design', 'cartoon', 'vector art'.\n"
            "Keep the narration continuous with earlier scenes and tied to the same central idea.\n"
            "Keep the image_prompt visually consistent with earlier scenes and narratively relevant.\n"
            "Do NOT invent superhero-like characters, comic-book heroes, or recurring protagonists unless the user "
            "explicitly asked for a character-driven story.\n"
            "If people appear in the image, keep them anonymous, ordinary, and directly relevant to the idea being explained.\n"
            "Deepen the user's actual topic rather than expanding into a different fictional frame.\n"
            "Use the required_concepts from the locked topic brief. Avoid everything in forbidden_drifts.\n"
            "Return EXACTLY 6 scenes, no more, no fewer."
        )
        raw_2 = generate_text_structured(
            prompt=prompt_2,
            system_prompt=system_prompt,
            schema=SCENE_SCHEMA,
            model_name=script_model,
        )
        try:
            scenes_2 = json.loads(raw_2)["scenes"]
            if len(scenes_2) != 6:
                raise ValueError(f"Expected 6 scenes, got {len(scenes_2)}")
        except (json.JSONDecodeError, KeyError, ValueError):
            # Retry once with emphatic count instruction
            raw_2 = generate_text_structured(
                prompt=f"You MUST return EXACTLY 6 scenes. No more, no fewer.\n\n{prompt_2}",
                system_prompt=system_prompt,
                schema=SCENE_SCHEMA,
                model_name=script_model,
            )
            try:
                scenes_2 = json.loads(raw_2)["scenes"]
                if len(scenes_2) != 6:
                    raise ValueError(f"Call 2 retry returned {len(scenes_2)} scenes, expected 6")
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"LLM call 2 returned invalid JSON after retry: {exc}") from exc

        # --- Summary 2: summarise all scenes so far (Call 1 + Call 2) ---
        narrations_12 = "\n\n".join(
            s["narration"] for s in (scenes_1 + scenes_2)
        )
        summary_2 = generate_text(
            f"Summarize the following podcast narration in 3-5 sentences.\n"
            f"Keep the summary anchored to this exact topic: {topic}\n"
            "Preserve the same thesis, key claims, and user-provided concepts from earlier scenes.\n"
            "Do NOT convert it into a different mystery, mythology, or external plot.\n\n"
            f"{topic_interpretation_block}\n"
            f"Locked topic brief:\n{topic_brief_json}\n\n"
            + narrations_12,
            model_name=script_model,
        )

        # --- Visual Summary 2: visual elements from all scenes so far ---
        visual_summary_2 = generate_text(
            "Summarize the key visual elements from these image descriptions "
            "(main characters and their appearance, locations, color palette, lighting mood) "
            "in 2-3 sentences. Preserve recurring motifs explicitly mentioned by the user. "
            "Do NOT introduce new symbolic systems, hidden artifacts, or unrelated story imagery.\n\n"
            + "\n---\n".join(s["image_prompt"] for s in (scenes_1 + scenes_2)),
            model_name=script_model,
        )

        # --- Call 3: act3(6) + outro(1) = 7 scenes ---
        prompt_3 = (
            f"Story so far:\n{summary_2}\n\n"
            f"Visual style established in earlier scenes:\n{visual_summary_2}\n"
            "Maintain these visual elements consistently in all new image_prompts.\n\n"
            f"Conclude the podcast about: {topic}\n\n"
            f"{direction_block}"
            f"{topic_guardrail_block}\n"
            f"{topic_interpretation_block}\n"
            f"Locked topic brief:\n{topic_brief_json}\n\n"
            "Generate EXACTLY 7 scenes:\n"
            "  Scenes 1-6: Act 3 -- resolve the story arc, deliver the payoff.\n"
            "  Scene 7: A compelling outro that leaves the audience in quiet wonder — end with a philosophical reflection or a haunting final image. Do NOT include 'subscribe', 'like', 'comment', 'กดติดตาม', 'กดกระดิ่ง', or any YouTube CTA language. The outro must feel like the end of a great documentary, not an ad.\n\n"
            f"Act 3 focus to follow: {topic_brief['act_3_focus']}\n"
            f"Outro focus to follow: {topic_brief['outro_focus']}\n"
            f"Each scene needs a 'scene_title' (a short 1-4 word summarizing title in the same language as the podcast), "
            f"a 'narration' (about {sentence_length} sentences of engaging spoken text), "
            "and an 'image_prompt' (vivid visual description for an illustration, MUST be in English only — never use Thai or non-Latin text in image prompts; any text shown in the image must also be in English).\n"
            f"The image_prompt will be prefixed with this style: '{self.style_prompt[:80]}'. "
            "Do NOT add keywords that contradict this style. "
            "For example, if the prefix is flat design/Kurzgesagt — do NOT add 'cinematic', 'photorealistic', '8K', 'dark mood'. "
            "If the prefix is cinematic realism — do NOT add 'flat design', 'cartoon', 'vector art'.\n"
            "The ending should conclude the same topic thoughtfully instead of summarizing a different idea.\n"
            "The image_prompt should feel like a continuation of the same visual world.\n"
            "Do NOT invent superhero-like characters, comic-book heroes, or recurring protagonists unless the user "
            "explicitly asked for a character-driven story.\n"
            "If people appear in the image, keep them anonymous, ordinary, and directly relevant to the idea being explained.\n"
            "Land the user's actual thesis clearly in the ending.\n"
            "Use the required_concepts from the locked topic brief. Avoid everything in forbidden_drifts.\n"
            "Return EXACTLY 7 scenes, no more, no fewer."
        )
        raw_3 = generate_text_structured(
            prompt=prompt_3,
            system_prompt=system_prompt,
            schema=SCENE_SCHEMA,
            model_name=script_model,
        )
        try:
            scenes_3 = json.loads(raw_3)["scenes"]
            if len(scenes_3) != 7:
                raise ValueError(f"Expected 7 scenes, got {len(scenes_3)}")
        except (json.JSONDecodeError, KeyError, ValueError):
            # Retry once with emphatic count instruction
            raw_3 = generate_text_structured(
                prompt=f"You MUST return EXACTLY 7 scenes. No more, no fewer.\n\n{prompt_3}",
                system_prompt=system_prompt,
                schema=SCENE_SCHEMA,
                model_name=script_model,
            )
            try:
                scenes_3 = json.loads(raw_3)["scenes"]
                if len(scenes_3) != 7:
                    raise ValueError(f"Call 3 retry returned {len(scenes_3)} scenes, expected 7")
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"LLM call 3 returned invalid JSON after retry: {exc}") from exc

        # --- Combine all 20 scenes ---
        all_scenes = scenes_1 + scenes_2 + scenes_3
        assert len(all_scenes) == 20, (
            f"Expected 20 scenes total, got {len(all_scenes)}"
        )

        # --- Finalize scenes: prepend style prompt and ensure titles exist ---
        style_prompt = self.style_prompt
        for scene in all_scenes:
            if not scene.get("scene_title"):
                scene["scene_title"] = _generate_scene_title(scene["narration"], model_name=script_model)
            scene["image_prompt"] = f"{style_prompt} {scene['image_prompt']}"

        # --- Create episode directory and persist script.json ---
        slug = _slugify_topic(topic)
        date_str = datetime.now().strftime("%Y%m%d")
        episode_id = f"podcast_{slug}_{date_str}"
        episode_dir = os.path.join(ROOT_DIR, ".mp", episode_id)
        os.makedirs(episode_dir, exist_ok=True)
        script_path = os.path.join(episode_dir, "script.json")

        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(all_scenes, f, ensure_ascii=False, indent=2)

        self.episode_dir = episode_dir

        return all_scenes

    def generate_script_from_text(self, text: str) -> list:
        """Split a user-provided narration text into scenes and generate image prompts.

        Uses an LLM to divide the text into exactly 20 scenes without altering
        the narration content, then calls the LLM once per scene to generate
        an image_prompt.

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

        schema = {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["segments"],
        }
        system_prompt = (
            "You are a script editor. Split the provided narration text into segments for a video podcast. "
            "Rules:\n"
            "- Divide the text into EXACTLY 20 segments. No more, no fewer.\n"
            "- CRITICAL: DO NOT automatically translate the text to English. You MUST keep the exact original language (e.g., Thai).\n"
            "- Do NOT change, rephrase, or omit any content — copy the exact words verbatim.\n"
            "- Each segment should be a natural, coherent chunk (paragraph or thematic break).\n"
            "- Return ONLY valid JSON matching the schema. No markdown, no commentary."
        )
        split_prompt = (
            f"Split this narration into EXACTLY 20 segments. "
            f"Do not translate. Do not change any wording. Keep the exact original language.\n\nNARRATION:\n{text.strip()}"
        )

        script_model = get_podcast_script_model()
        result_json = generate_text_structured(split_prompt, system_prompt, schema, model_name=script_model)
        try:
            segments = json.loads(result_json).get("segments", [])
            segments = [s.strip() for s in segments if s.strip()]
        except (json.JSONDecodeError, AttributeError):
            segments = []

        if len(segments) != 20:
            print(f"Warning: LLM returned {len(segments)} segments instead of 20, attempting basic fallback splits.")
            words = [w.strip() for w in text.split() if w.strip()]
            chunk_size = math.ceil(max(1, len(words) / 20))
            segments = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)][:20]
            while len(segments) < 20:
                segments.append("...")

        scenes = []
        for narration in segments:
            image_prompt = _generate_image_prompt(narration, model_name=script_model)
            if self.style_prompt:
                image_prompt = f"{self.style_prompt} {image_prompt}"
            scene_title = _generate_scene_title(narration, model_name=script_model)
            scenes.append({"scene_title": scene_title, "narration": narration, "image_prompt": image_prompt})

        script_path = os.path.join(self.episode_dir, "script.json")
        os.makedirs(self.episode_dir, exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)

        return scenes

    def generate_assets(self) -> None:
        """Generate per-scene images (Gemini) and TTS audio (edge-tts).

        Reads script.json from the episode directory (set by generate_script()).
        Produces one PNG and one WAV per scene, named scene_00.png / scene_00.wav
        through scene_13.png / scene_13.wav.

        Resumable: scenes that already have both files are skipped.
        """
        scenes = self._load_script_scenes()
        total = len(scenes)

        for i, scene in enumerate(scenes):
            image_path, audio_path = self._scene_paths(i)

            # Resumability check: skip if both files already exist
            if os.path.exists(image_path) and os.path.exists(audio_path):
                print(f"Skipping scene {i + 1}/{total} (already generated).")
            else:
                print(f"Generating assets for scene {i + 1}/{total}...")
                self.generate_scene_assets(i)

            # Scene 0 only: generate video clip via Kling (resumable)
            if i == 0:
                video_path = os.path.join(self.episode_dir, "scene_00.mp4")
                if not os.path.exists(video_path) or os.path.getsize(video_path) < 10_000:
                    self._generate_scene0_video(image_path, scene, video_path)

    def render(self) -> None:
        """Render podcast video via Remotion with Ken Burns + slide transitions.

        1. Collect per-scene durations via ffprobe.
        2. Merge all scene WAV files into a single audio track.
        3. Build props JSON and invoke Remotion renderer.
        4. Output: final.mp4 (1920x1080, 25fps).

        Raises:
            ValueError: If episode_dir is not set.
            FileNotFoundError: If scene_NN.png or scene_NN.wav is missing.
            subprocess.CalledProcessError: If ffprobe, ffmpeg, or Remotion exits non-zero.
        """
        if not self.episode_dir:
            raise ValueError(
                "episode_dir is not set. Call generate_script() before render()."
            )

        scenes = self._load_script_scenes()
        total = len(scenes)
        final_path = os.path.join(self.episode_dir, "final.mp4")

        # Resumability: skip if final.mp4 already exists
        if os.path.exists(final_path) and os.path.getsize(final_path) > 1_000_000:
            print(f"Skipping render (final.mp4 already exists at {final_path}).")
            return

        image_paths = []
        wav_paths = []
        scene_durations = []

        # --- Collect scene assets and durations ---
        for i in range(total):
            scene_num = str(i).zfill(2)
            png_path = os.path.join(self.episode_dir, f"scene_{scene_num}.png")
            wav_path = os.path.join(self.episode_dir, f"scene_{scene_num}.wav")

            if not os.path.exists(png_path):
                raise FileNotFoundError(
                    f"scene_{scene_num}.png not found at {png_path}. "
                    "Run generate_assets() first."
                )
            if not os.path.exists(wav_path):
                raise FileNotFoundError(
                    f"scene_{scene_num}.wav not found at {wav_path}. "
                    "Run generate_assets() first."
                )

            # Get audio duration via ffprobe
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

            image_paths.append(os.path.abspath(png_path))
            wav_paths.append(wav_path)
            scene_durations.append(duration)

        total_duration = sum(scene_durations)

        # --- Merge all scene WAV files into single audio track ---
        merged_audio = os.path.join(self.episode_dir, "merged_audio.wav")
        if not os.path.exists(merged_audio):
            concat_audio_path = os.path.join(self.episode_dir, "audio_concat.txt")
            with open(concat_audio_path, "w", encoding="utf-8") as f:
                for wav in wav_paths:
                    # Use absolute path to avoid Windows relative-path issues
                    abs_wav = os.path.abspath(wav).replace("\\", "/")
                    f.write(f"file '{abs_wav}'\n")

            print("Merging scene audio files...")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_audio_path,
                    "-c", "copy",
                    merged_audio,
                ],
                capture_output=True, text=True, check=True,
            )

        # --- Build Remotion render props ---
        from pathlib import Path

        remotion_dir = Path(ROOT_DIR) / "remotion"
        scene_titles = [s.get("scene_title", "") for s in scenes][:total]

        props = {
            "composition": "VideoPodcast",
            "imagePaths": image_paths,
            "audioPath": os.path.abspath(merged_audio),
            "sceneDurations": scene_durations,
            "sceneTitles": scene_titles,
            "durationInSeconds": total_duration,
            "outputPath": os.path.abspath(final_path),
        }

        video_path_0 = os.path.join(self.episode_dir, "scene_00.mp4")
        if os.path.exists(video_path_0):
            props["scene0VideoPath"] = os.path.abspath(video_path_0)

        props_file = remotion_dir / ".render-props-podcast.json"
        import json as _json
        props_file.write_text(
            _json.dumps(props, ensure_ascii=False),
            encoding="utf-8",
        )
        props_file_path = str(props_file.resolve())

        # --- Invoke Remotion renderer ---
        print(f"Rendering {total} scenes via Remotion ({total_duration:.1f}s total)...")
        subprocess.run(
            ["node", "scripts/render.mjs", props_file_path],
            cwd=str(remotion_dir),
            check=True,
            shell=True,
            timeout=1800,
        )

        # Post-render sanity check
        assert os.path.exists(final_path), f"final.mp4 not found at {final_path}"
        assert os.path.getsize(final_path) > 1_000_000, (
            f"final.mp4 is suspiciously small ({os.path.getsize(final_path)} bytes) — "
            "check Remotion output."
        )

        print(f"Final video: {final_path}")

    def generate_metadata(self) -> dict:
        """Generate YouTube metadata (title, description, tags) via LLM.

        Reads script.json from episode_dir to extract an opening narration
        excerpt, then calls the LLM to produce upload-ready metadata. Falls
        back to minimal metadata if LLM output cannot be parsed.

        Returns:
            dict with keys: title (str), description (str), tags (list[str]).

        Raises:
            ValueError: If episode_dir is not set.
            FileNotFoundError: If script.json is missing from episode_dir.
        """
        if not self.episode_dir:
            raise ValueError(
                "episode_dir is not set. Call generate_script() before generate_metadata()."
            )

        script_path = os.path.join(self.episode_dir, "script.json")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"script.json not found at {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            scenes = json.load(f)

        # Use narrations from scenes 0 and 1 (intro + first act1 scene) as context
        context_scenes = scenes[:2] if len(scenes) >= 2 else scenes
        context_excerpt = " ".join(s["narration"] for s in context_scenes)

        prompt = _safe_format(
            get_podcast_metadata_system_prompt(),
            topic=self.topic,
            language=self.language,
            opening_narration=context_excerpt,
            creative_direction=self.creative_direction,
            creative_direction_block=(
                f"Creative direction:\n{self.creative_direction}\n\n"
                if self.creative_direction
                else ""
            ),
        )

        raw = generate_text(prompt, model_name=get_podcast_script_model())

        # Attempt JSON parse; strip markdown fences if needed
        metadata = None
        try:
            metadata = json.loads(raw)
        except json.JSONDecodeError:
            stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            try:
                metadata = json.loads(stripped)
            except json.JSONDecodeError:
                pass

        if metadata is None:
            print("Warning: LLM metadata parse failed, using fallback metadata.")
            default_title_prefix = "พอดแคสต์" if self.language == "Thai" else "Podcast"
            default_description = (
                f"ตอนพอดแคสต์ที่จะพาไปสำรวจเรื่อง {self.topic} แบบลึกขึ้น"
                if self.language == "Thai"
                else f"A deep dive podcast episode about {self.topic}."
            )
            metadata = {
                "title": f"{default_title_prefix}: {self.topic[:80]}",
                "description": default_description,
                "tags": [self.topic.lower(), "podcast", "deep dive", "storytelling"],
            }

        # Enforce length constraints
        metadata["title"] = str(metadata.get("title", f"Podcast: {self.topic[:80]}"))[:100]
        metadata["description"] = str(metadata.get("description", ""))[:5000]
        if not isinstance(metadata.get("tags"), list):
            metadata["tags"] = [self.topic.lower(), "podcast"]

        self.metadata = metadata

        # Persist to metadata.json
        metadata_path = os.path.join(self.episode_dir, "metadata.json")
        # Merge with any existing metadata to preserve keys like language, uploaded_at, video_id
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                # New metadata takes precedence; existing keys fill in the rest
                merged = {**existing, **metadata}
            except (json.JSONDecodeError, IOError):
                merged = metadata
        else:
            merged = metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        print(f"Metadata title: {metadata['title']}")
        return metadata

    def generate_thumbnail(self) -> str | None:
        """Build the thumbnail image-generation prompt and save it to thumbnail_prompt.txt.

        Image generation is intentionally skipped — the prompt is returned so the caller
        can display it for manual use (e.g. paste into Midjourney / Ideogram).

        Returns:
            The prompt string on success, or None if episode_dir is not set.

        Raises:
            ValueError: If episode_dir is not set.
        """
        if not self.episode_dir:
            raise ValueError(
                "episode_dir is not set. Call generate_script() before generate_thumbnail()."
            )

        prompt_path = os.path.join(self.episode_dir, "thumbnail_prompt.txt")

        if os.path.exists(prompt_path):
            print("Skipping thumbnail prompt build (thumbnail_prompt.txt already exists).")
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()

        prompt = _safe_format(
            get_podcast_thumbnail_system_prompt(),
            topic=self.topic,
            creative_direction_block=(
                f"Use this visual style and creative direction:\n{self.creative_direction}\n{self.style_prompt}\n\n"
                if (self.creative_direction or self.style_prompt)
                else ""
            ),
        )

        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        print(f"Thumbnail prompt saved: {prompt_path}")
        return prompt

    def _build_youtube_client(self):
        """Builds an authenticated YouTube API client using token.json."""
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(self.TOKEN_PATH, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            else:
                raise RuntimeError(
                    "token.json not found or invalid. Run: python src/youtube_auth.py"
                )
        return build("youtube", "v3", credentials=creds)

    def upload(self, privacy_status: str = "public", publish_at: str | None = None) -> str | None:
        """Upload final.mp4 and thumbnail to YouTube via API v3.

        Uses self.metadata (populated by generate_metadata()) for title,
        description, and tags. Sets categoryId to "27" (Education).

        Args:
            privacy_status: "public", "unlisted", or "private".
            publish_at: ISO 8601 UTC datetime string for scheduled publish
                (e.g. "2025-06-01T12:00:00.000Z"). When set, privacyStatus
                is forced to "private" and publishAt is added to the status
                body — YouTube will make the video public at that time.

        Returns:
            Video URL string on success, None on failure.

        Raises:
            ValueError: If episode_dir is not set.
            FileNotFoundError: If final.mp4 or metadata.json is missing.
            RuntimeError: If token.json is missing or invalid.
        """
        if not self.episode_dir:
            raise ValueError(
                "episode_dir is not set. Call generate_script() before upload()."
            )

        final_path = os.path.join(self.episode_dir, "final.mp4")
        if not os.path.exists(final_path):
            raise FileNotFoundError(
                f"final.mp4 not found at {final_path}. Run render() first."
            )

        # Load metadata from file if self.metadata is empty (resumability)
        if not self.metadata:
            meta_path = os.path.join(self.episode_dir, "metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            else:
                raise FileNotFoundError(
                    f"metadata.json not found at {meta_path}. Run generate_metadata() first."
                )

        # Build YouTube API client
        yt = self._build_youtube_client()

        # Prepare upload body
        # When publish_at is set, YouTube requires privacyStatus="private"
        # and publishAt in the status block — it auto-publishes at that time.
        effective_privacy = "private" if publish_at else privacy_status
        status_block: dict = {
            "privacyStatus": effective_privacy,
            "selfDeclaredMadeForKids": False,
        }
        if publish_at:
            status_block["publishAt"] = publish_at

        body = {
            "snippet": {
                "title": self.metadata["title"],
                "description": self.metadata["description"],
                "tags": self.metadata.get("tags", []),
                "categoryId": "27",
            },
            "status": status_block,
        }

        print(f"Uploading to YouTube: {self.metadata['title']}")

        import socket as _socket
        _socket.setdefaulttimeout(300)

        media = MediaFileUpload(
            final_path, mimetype="video/mp4",
            resumable=True, chunksize=1024 * 1024,
        )
        request = yt.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Upload complete: {video_url}")

        # Set thumbnail if it exists
        thumbnail_path = os.path.join(self.episode_dir, "thumbnail.png")
        if os.path.exists(thumbnail_path):
            try:
                thumb_media = MediaFileUpload(
                    thumbnail_path, mimetype="image/png",
                )
                yt.thumbnails().set(
                    videoId=video_id, media_body=thumb_media
                ).execute()
                print(f"Thumbnail set for video {video_id}")
            except Exception as e:
                print(f"Warning: Thumbnail upload failed: {e}")
                print("You can set the thumbnail manually in YouTube Studio.")

        # Save upload result to metadata.json
        self.metadata["video_id"] = video_id
        self.metadata["video_url"] = video_url
        self.metadata["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_path = os.path.join(self.episode_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        return video_url

    def run(self) -> None:
        """Run the full podcast pipeline: script → assets → render → upload."""
        self.generate_script(self.topic)
        self.generate_assets()
        self.generate_metadata()
        self.generate_thumbnail()
        self.render()
        self.upload()
