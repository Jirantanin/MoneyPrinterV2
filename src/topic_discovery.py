"""
Topic Discovery for MoneyPrinterV2
===================================
Fetches trending topics from Google Trends, YouTube, and NewsAPI,
then uses LLM (Ollama or Anthropic) to score and pick the best topic
for a YouTube Shorts video purely based on what's trending right now.

Output cached to .mp/discovered_topics.json
"""

import os
import json
from datetime import datetime, timedelta

from config import (
    get_topic_discovery_youtube_api_key,
    get_topic_discovery_news_api_key,
    get_topic_discovery_anthropic_api_key,
    get_topic_discovery_scoring_provider,
    get_topic_discovery_geo,
    get_topic_discovery_max_age_hours,
)
from cache import get_discovered_topics_cache_path
from status import info as _info, warning as _warning, error as _error, success as _success

# Wrap status calls with show_emoji=False to avoid cp874 encoding crashes on Thai Windows
def info(msg): _info(msg, False)
def warning(msg): _warning(msg, False)
def error(msg): _error(msg, False)
def success(msg): _success(msg, False)


# -- 1. Google Trends --------------------------------------------------------

def fetch_google_trends(geo: str = None, top_n: int = 10) -> list[str]:
    """Return top trending search queries via Google Trends RSS feed."""
    if geo is None:
        geo = get_topic_discovery_geo()
    # Try RSS feed first (more reliable than pytrends API)
    try:
        import xml.etree.ElementTree as ET
        import urllib.request
        url = f"https://trends.google.com/trending/rss?geo={geo}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
        items = tree.findall(".//item/title")
        trends = [item.text for item in items if item.text][:top_n]
        if trends:
            info(f" => Google Trends (RSS): {trends}")
            return trends
    except Exception as e:
        warning(f" Google Trends RSS failed: {e}")

    # Fallback to pytrends library
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360)
        df = pt.trending_searches(pn="united_states")
        trends = df[0].tolist()[:top_n]
        info(f" => Google Trends (pytrends): {trends}")
        return trends
    except Exception as e:
        warning(f" Google Trends pytrends also failed: {e}")
        return []


# -- 2. YouTube Trending (News category = 25) --------------------------------

def fetch_youtube_trending(api_key: str = None, max_results: int = 10) -> list[dict]:
    """Return trending YouTube videos in News & Politics category."""
    if api_key is None:
        api_key = get_topic_discovery_youtube_api_key()
    if not api_key:
        warning(" YOUTUBE_API_KEY not set, skipping YouTube trending.")
        return []
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", developerKey=api_key)
        resp = (
            yt.videos()
            .list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode="US",
                videoCategoryId="25",
                maxResults=max_results,
            )
            .execute()
        )
        items = [
            {
                "title": v["snippet"]["title"],
                "views": v["statistics"].get("viewCount", "0"),
                "description": v["snippet"].get("description", "")[:200],
            }
            for v in resp.get("items", [])
        ]
        info(f" => YouTube trending: {[i['title'] for i in items]}")
        return items
    except Exception as e:
        warning(f" YouTube trending failed: {e}")
        return []


# -- 3. NewsAPI top headlines ------------------------------------------------

def fetch_top_news(api_key: str = None, max_articles: int = 10) -> list[dict]:
    """Return top English headlines right now."""
    if api_key is None:
        api_key = get_topic_discovery_news_api_key()
    if not api_key:
        warning(" NEWS_API_KEY not set, skipping NewsAPI.")
        return []
    try:
        from newsapi import NewsApiClient
        client = NewsApiClient(api_key=api_key)
        resp = client.get_top_headlines(language="en", page_size=max_articles)
        articles = [
            {
                "title": a["title"],
                "source": a["source"]["name"],
                "description": (a.get("description") or "")[:200],
            }
            for a in resp.get("articles", [])
            if a.get("title")
        ]
        info(f" => NewsAPI: {[a['title'] for a in articles]}")
        return articles
    except Exception as e:
        warning(f" NewsAPI failed: {e}")
        return []


# -- 4. Scoring prompt -------------------------------------------------------

SCORING_PROMPT = """\
You are a YouTube Shorts content strategist.
Your job is to pick the BEST topic for a 60-second YouTube Shorts video
based purely on what is trending RIGHT NOW.

Criteria:
- High shareability / emotional hook
- Easy to explain in 60 seconds
- Currently trending or breaking
- Broad appeal (not too niche)
- Safe for all audiences (no gore, politics extremes, NSFW)

Language for the topic should be: {language}

Here is today's trending data:

=== GOOGLE TRENDS ===
{google_trends}

=== YOUTUBE TRENDING (News & Politics) ===
{youtube_trending}

=== TOP NEWS HEADLINES ===
{top_news}

Return ONLY a valid JSON object like this (no markdown, no preamble):
{{
  "winner": {{
    "topic": "short topic title",
    "angle": "one-sentence video angle / hook",
    "source": "google_trends | youtube | news",
    "score": 95
  }},
  "runners_up": [
    {{"topic": "...", "angle": "...", "source": "...", "score": 88}},
    {{"topic": "...", "angle": "...", "source": "...", "score": 82}}
  ],
  "reasoning": "2-3 sentences why winner was chosen"
}}
"""


def score_topics(
    google_trends: list,
    youtube_trending: list,
    top_news: list,
    language: str = "English",
) -> dict:
    """Send all raw data to LLM and get scored/ranked topics back."""
    prompt = SCORING_PROMPT.format(
        language=language,
        google_trends=json.dumps(google_trends, indent=2),
        youtube_trending=json.dumps(youtube_trending, indent=2),
        top_news=json.dumps(top_news, indent=2),
    )

    provider = get_topic_discovery_scoring_provider()

    if provider == "anthropic":
        return _score_with_anthropic(prompt)
    else:
        return _score_with_ollama(prompt)


def _extract_winner_from_partial(raw: str) -> dict:
    """Try to extract at least the winner from truncated JSON."""
    import re
    topic_m = re.search(r'"topic"\s*:\s*"([^"]+)"', raw)
    angle_m = re.search(r'"angle"\s*:\s*"([^"]+)"', raw)
    source_m = re.search(r'"source"\s*:\s*"([^"]+)"', raw)
    score_m = re.search(r'"score"\s*:\s*(\d+)', raw)
    if topic_m and angle_m:
        return {
            "winner": {
                "topic": topic_m.group(1),
                "angle": angle_m.group(1),
                "source": source_m.group(1) if source_m else "unknown",
                "score": int(score_m.group(1)) if score_m else 0,
            },
            "runners_up": [],
            "reasoning": "Extracted from partial LLM response",
        }
    return {}


def _score_with_ollama(prompt: str) -> dict:
    """Score topics using the local Ollama model."""
    from llm_provider import generate_text
    for attempt in range(2):
        try:
            raw = generate_text(prompt)
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            info(f" => Ollama winner: {result['winner']['topic']} (score {result['winner']['score']})")
            return result
        except json.JSONDecodeError:
            # Try to salvage winner from partial JSON
            result = _extract_winner_from_partial(raw)
            if result:
                info(f" => Ollama winner (partial): {result['winner']['topic']}")
                return result
            if attempt == 0:
                warning(f" Ollama returned incomplete JSON, retrying...")
                continue
            error(f" Ollama returned invalid JSON. Raw: {raw[:300]}")
            return {}
        except Exception as e:
            error(f" Ollama scoring failed: {e}")
            return {}


def _score_with_anthropic(prompt: str) -> dict:
    """Score topics using the Anthropic API."""
    api_key = get_topic_discovery_anthropic_api_key()
    if not api_key:
        error(" anthropic_api_key not set in topic_discovery config.")
        return {}
    try:
        import anthropic
    except ImportError:
        error(" 'anthropic' package not installed. Run: pip install anthropic")
        return {}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        info(f" => Claude winner: {result['winner']['topic']} (score {result['winner']['score']})")
        return result
    except Exception as e:
        error(f" Anthropic scoring failed: {e}")
        return {}


# -- 5. Cache management -----------------------------------------------------

def save_topics(result: dict) -> None:
    """Write discovered topics to cache."""
    cache_path = get_discovered_topics_cache_path()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    info(f" => Saved topics to {cache_path}")


def load_topics() -> dict | None:
    """Load cached topics if fresh."""
    cache_path = get_discovered_topics_cache_path()
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            result = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    # Check freshness
    generated_at = result.get("generated_at")
    if not generated_at:
        return None
    try:
        gen_time = datetime.fromisoformat(generated_at)
        max_age = timedelta(hours=get_topic_discovery_max_age_hours())
        if datetime.now() - gen_time > max_age:
            return None
    except (ValueError, TypeError):
        return None

    return result


def get_best_topic() -> str | None:
    """Return the best discovered topic string, or None if stale/missing."""
    result = load_topics()
    if not result or "winner" not in result:
        return None
    winner = result["winner"]
    return f"{winner['topic']}: {winner['angle']}"


# -- 6. Main orchestration ---------------------------------------------------

def run_discovery(language: str = "English") -> dict | None:
    """Full discovery pipeline: fetch -> score -> save -> return."""
    info("=" * 50)
    info(f" Topic Discovery — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    info("=" * 50)

    google_trends = fetch_google_trends()
    youtube_trending = fetch_youtube_trending()
    top_news = fetch_top_news()

    if not any([google_trends, youtube_trending, top_news]):
        error(" All sources failed. Aborting topic discovery.")
        return None

    result = score_topics(google_trends, youtube_trending, top_news, language)

    if not result:
        error(" Scoring returned empty. Aborting.")
        return None

    # Attach metadata
    result["generated_at"] = datetime.now().isoformat()
    result["sources_used"] = {
        "google_trends_count": len(google_trends),
        "youtube_trending_count": len(youtube_trending),
        "news_count": len(top_news),
    }

    save_topics(result)

    success(f" TODAY'S TOPIC: {result['winner']['topic']}")
    info(f" ANGLE: {result['winner']['angle']}")
    info(f" REASONING: {result.get('reasoning', '')}")

    return result
