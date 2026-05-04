"""
podcast_shorts_scorer.py — Score podcast scenes for YouTube Shorts virality.

Usage:
    from podcast_shorts_scorer import score_scenes
    top = score_scenes(".mp/podcast_slug_20250101", top_n=3)
    # Returns list of dicts: {scene_index, score, reason, narration, image_prompt}
"""

import json
import os

from llm_provider import generate_text_structured
from status import error, info, warning

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_index": {"type": "integer"},
                    "score": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["scene_index", "score", "reason"],
            },
        }
    },
    "required": ["scores"],
}

_SYSTEM_PROMPT = (
    "Score each scene 1-10 for YouTube Shorts virality. "
    "Consider: strong hook, surprising fact, emotional punch, "
    "self-contained (can stand alone without context). Return only JSON."
)


def score_scenes(episode_dir: str, top_n: int = 3) -> list[dict]:
    """
    Score podcast scenes for YouTube Shorts virality using an LLM.

    Args:
        episode_dir: Path to the podcast episode directory (must contain script.json).
        top_n: Number of top-scoring scenes to return.

    Returns:
        List of top_n scene dicts ordered by score descending.
        Each dict has: scene_index, score, reason, narration, image_prompt.
    """
    script_path = os.path.join(episode_dir, "script.json")
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"script.json not found in {episode_dir}")

    with open(script_path, "r", encoding="utf-8") as fh:
        scenes: list[dict] = json.load(fh)

    if not scenes:
        raise ValueError(f"script.json in {episode_dir} is empty")

    # Build prompt: numbered narration list only (strictly narration text)
    lines = [f"[{i}] {s.get('narration', '').strip()}" for i, s in enumerate(scenes)]
    prompt = "\n\n".join(lines)

    info(f"Scoring {len(scenes)} scenes with LLM...")

    raw = generate_text_structured(prompt, _SYSTEM_PROMPT, SCORE_SCHEMA)

    try:
        # generate_text_structured returns a JSON string; guard against dict return in future
        data = raw if isinstance(raw, dict) else json.loads(raw)
    except json.JSONDecodeError as exc:
        error(f"Failed to parse scorer response: {exc}\nRaw: {raw[:300]}")
        raise

    scores: list[dict] = data.get("scores", [])

    if not scores:
        warning("LLM returned no scores — defaulting to first top_n scenes")
        return [
            {
                "scene_index": i,
                "score": 5,
                "reason": "default (no LLM scores returned)",
                "narration": scenes[i].get("narration", ""),
                "image_prompt": scenes[i].get("image_prompt", ""),
            }
            for i in range(min(top_n, len(scenes)))
        ]

    # Sort by score descending and take top_n
    scores.sort(key=lambda x: x.get("score", 0), reverse=True)
    top = scores[:top_n]

    # Enrich with narration + image_prompt from script
    for item in top:
        # LLM may return scene_index as a string — cast defensively
        idx = int(item.get("scene_index", 0))
        item["scene_index"] = idx  # normalise to int in output
        if 0 <= idx < len(scenes):
            item["narration"] = scenes[idx].get("narration", "")
            item["image_prompt"] = scenes[idx].get("image_prompt", "")
        else:
            item["narration"] = ""
            item["image_prompt"] = ""
            warning(f"scene_index {idx} out of range (script has {len(scenes)} scenes)")

    return top
