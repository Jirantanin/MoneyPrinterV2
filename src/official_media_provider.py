"""Official media search helpers for PodcastV2 Producer Mode.

The provider is metadata-first: it finds official source pages and usable media
URLs, then returns normalized candidates for checkpoint review. A later
production stage can download the selected assets into ``asset_manifest.json``.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests


NASA_IMAGES_SEARCH_URL = "https://images-api.nasa.gov/search"
NASA_SVS_SEARCH_URL = "https://svs.gsfc.nasa.gov/api/search/"
NASA_SVS_DETAIL_URL = "https://svs.gsfc.nasa.gov/api/{svs_id}/"
NASA_IMAGES_DETAILS_URL = "https://images.nasa.gov/details/{nasa_id}"
NASA_MEDIA_USAGE_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"
NASA_MEDIA_LICENSE_NOTE = (
    "NASA media usage is generally available for informational or educational "
    "use, but verify source-specific third-party rights, people, logos, and "
    "endorsement restrictions before final use."
)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = (8, 25)

HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    return HTTP_SESSION.get(url, **kwargs)

TOKEN_STOPWORDS = {
    "about",
    "after",
    "analysis",
    "and",
    "documentary",
    "evidence",
    "explained",
    "facts",
    "for",
    "from",
    "official",
    "research",
    "source",
    "sources",
    "that",
    "the",
    "this",
    "with",
    "youtube",
}

JPL_TARGET_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("mars", "martian", "perseverance", "curiosity", "rover"), "Mars"),
    (("moon", "lunar", "apollo"), "Moon"),
    (("jupiter", "europa", "ganymede", "callisto", "io", "juno"), "Jupiter"),
    (("saturn", "titan", "cassini", "enceladus"), "Saturn"),
    (("earth", "terra", "climate"), "Earth"),
    (("sun", "solar", "heliophysics"), "Sun"),
    (("mercury",), "Mercury"),
    (("venus",), "Venus"),
    (("uranus",), "Uranus"),
    (("neptune",), "Neptune"),
    (("pluto", "charon", "new horizons"), "Pluto"),
    (("asteroid", "asteroids", "ceres", "vesta"), "Asteroids"),
    (("comet", "comets"), "Comets"),
)


class _LinkAndMetaParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}
        self._href_stack: list[str] = []
        self._text_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a":
            href = attrs_dict.get("href", "")
            self._href_stack.append(href)
            self._text_stack.append([])
        elif tag.lower() == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content", "")
            if key and content:
                self.meta[key.lower()] = content
        elif tag.lower() == "title":
            self._href_stack.append("__title__")
            self._text_stack.append([])

    def handle_data(self, data: str) -> None:
        if self._text_stack:
            self._text_stack[-1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() not in {"a", "title"} or not self._href_stack:
            return
        href = self._href_stack.pop()
        text = _clean_text(" ".join(self._text_stack.pop() if self._text_stack else []))
        if href == "__title__":
            if text and "title" not in self.meta:
                self.meta["title"] = text
            return
        if href:
            self.links.append({"url": urljoin(self.base_url, href), "text": text})


def _utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(value or ""))).strip()
    return text or fallback


def _compact(value: Any, limit: int = 600) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _tokens(value: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", str(value or "").lower())
    return [word for word in words if word not in TOKEN_STOPWORDS]


def _score_text(query: str, text: str) -> int:
    tokens = _tokens(query)
    if not tokens:
        return 1
    haystack = str(text or "").lower()
    score = sum(1 for token in tokens if token in haystack)
    normalized_query = re.sub(r"\s+", " ", str(query or "").lower()).strip()
    if normalized_query and normalized_query in haystack:
        score += 3
    return score


def _fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = _http_get(url, params=params, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _fetch_text(url: str) -> tuple[str, str]:
    response = _http_get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text, response.url


def _provider_result(
    *,
    provider: str,
    item_id: str,
    title: str,
    media_type: str,
    source_url: str,
    download_url: str = "",
    preview_url: str = "",
    credit: str = "NASA",
    description: str = "",
    date: str = "",
    keywords: list[str] | None = None,
    width: int | None = None,
    height: int | None = None,
    relevance_score: int = 0,
    selected_reason: str = "",
    risks: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "id": item_id,
        "title": _compact(title, 220),
        "media_type": media_type,
        "source_url": source_url,
        "download_url": download_url,
        "preview_url": preview_url or download_url,
        "credit": credit,
        "license_note": NASA_MEDIA_LICENSE_NOTE,
        "license_url": NASA_MEDIA_USAGE_URL,
        "description": _compact(description, 900),
        "date": date,
        "keywords": keywords or [],
        "width": width,
        "height": height,
        "relevance_score": relevance_score,
        "selected_reason": selected_reason,
        "risks": risks
        or ["Verify the source page and rights notes again before final asset use."],
        "accessed_date": _utc_date(),
    }


def _asset_extension(url: str) -> str:
    path = urlparse(str(url or "")).path.lower()
    match = re.search(r"\.([a-z0-9]+)$", path)
    return match.group(1) if match else ""


def _media_type_from_url(url: str) -> str:
    ext = _asset_extension(url)
    if ext in {"mp4", "webm", "mov", "m4v"}:
        return "video"
    if ext in {"jpg", "jpeg", "png", "webp", "tif", "tiff"}:
        return "image"
    return "page"


def _nasa_collection_asset_score(url: str, media_type: str) -> int:
    lower = str(url or "").lower()
    ext = _asset_extension(lower)
    if ext in {"json", "srt", "vtt", "txt", "xml"}:
        return -10_000

    score = 0
    if media_type == "video":
        if ext == "mp4":
            score += 120
        elif ext == "webm":
            score += 105
        elif ext in {"mov", "m4v"}:
            score += 60
        elif ext in {"jpg", "jpeg", "png", "webp"}:
            score += 15
        else:
            return -10_000
    else:
        if ext in {"jpg", "jpeg"}:
            score += 120
        elif ext in {"png", "webp"}:
            score += 105
        elif ext in {"tif", "tiff"}:
            score += 65
        else:
            return -10_000

    if "~orig" in lower or "_orig" in lower or "orig." in lower:
        score += 35
    if "large" in lower:
        score += 25
    if "medium" in lower:
        score += 12
    if any(marker in lower for marker in ("thumb", "thumbnail", "preview", "small")):
        score -= 35
    if "prores" in lower:
        score -= 80
    return score


def _best_nasa_collection_asset(collection_url: str, media_type: str) -> str:
    if not collection_url:
        return ""
    try:
        payload = _fetch_json(collection_url)
    except (requests.RequestException, ValueError):
        return ""

    urls: list[str] = []
    if isinstance(payload, list):
        urls = [str(item) for item in payload if isinstance(item, str)]
    elif isinstance(payload, dict):
        items = payload.get("items") or payload.get("collection", {}).get("items") or []
        for item in items:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                href = item.get("href") or item.get("url")
                if href:
                    urls.append(str(href))

    candidates = [(url, _nasa_collection_asset_score(url, media_type)) for url in urls]
    candidates = [item for item in candidates if item[1] > 0]
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def search_nasa_images(
    query: str,
    *,
    limit: int = 6,
    media_types: tuple[str, ...] = ("image", "video"),
    resolve_downloads: bool = True,
) -> list[dict[str, Any]]:
    """Search NASA Image and Video Library and return normalized candidates."""

    params = {
        "q": query,
        "media_type": ",".join(media_types),
        "page_size": max(1, min(50, max(limit * 4, limit))),
    }
    payload = _fetch_json(NASA_IMAGES_SEARCH_URL, params=params)
    items = payload.get("collection", {}).get("items", []) if isinstance(payload, dict) else []
    results: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        data_items = item.get("data") or []
        data = data_items[0] if data_items and isinstance(data_items[0], dict) else {}
        item_media_type = str(data.get("media_type") or "").lower()
        if item_media_type not in {"image", "video"}:
            continue
        if item_media_type not in set(media_types):
            continue

        title = _clean_text(data.get("title"))
        description = _clean_text(data.get("description"))
        keywords = [str(value) for value in (data.get("keywords") or []) if str(value).strip()]
        nasa_id = str(data.get("nasa_id") or title)
        links = item.get("links") or []
        preview_url = ""
        if links and isinstance(links[0], dict):
            preview_url = str(links[0].get("href") or "")
        collection_url = str(item.get("href") or "")
        source_url = NASA_IMAGES_DETAILS_URL.format(nasa_id=quote(nasa_id, safe=""))
        score = _score_text(query, " ".join([title, description, " ".join(keywords), nasa_id]))
        if _tokens(query) and score <= 0:
            continue

        download_url = _best_nasa_collection_asset(collection_url, item_media_type) if resolve_downloads else ""
        results.append(
            _provider_result(
                provider="nasa_images",
                item_id=nasa_id,
                title=title or nasa_id,
                media_type=item_media_type,
                source_url=source_url,
                download_url=download_url,
                preview_url=preview_url,
                credit="NASA",
                description=description,
                date=str(data.get("date_created") or ""),
                keywords=keywords,
                relevance_score=score,
                selected_reason="Direct NASA Image and Video Library result for the topic.",
            )
        )
        results[-1]["collection_url"] = collection_url
        if len(results) >= limit:
            break

    return results


def _iter_svs_instances(detail: dict[str, Any]) -> list[dict[str, Any]]:
    instances: list[dict[str, Any]] = []
    for key in ("main_video", "main_image"):
        value = detail.get(key)
        if isinstance(value, dict):
            instances.append(value)
    for group in detail.get("media_groups") or []:
        if not isinstance(group, dict):
            continue
        for wrapper in group.get("items") or []:
            if not isinstance(wrapper, dict):
                continue
            instance = wrapper.get("instance")
            if isinstance(instance, dict):
                instances.append(instance)
    return instances


def _svs_asset_score(instance: dict[str, Any]) -> int:
    url = str(instance.get("url") or "")
    if not url:
        return -10_000
    lower = url.lower()
    ext = _asset_extension(url)
    media_type = str(instance.get("media_type") or "").lower()
    score = 0
    if media_type == "movie" or ext in {"mp4", "webm", "mov", "m4v"}:
        if ext == "mp4":
            score += 130
        elif ext == "webm":
            score += 110
        elif ext in {"mov", "m4v"}:
            score += 45
        else:
            score += 65
    elif media_type == "image" or ext in {"jpg", "jpeg", "png", "webp", "tif", "tiff"}:
        if ext in {"jpg", "jpeg"}:
            score += 95
        elif ext in {"png", "webp"}:
            score += 85
        else:
            score += 55
    else:
        return -10_000

    width = int(instance.get("width") or 0)
    height = int(instance.get("height") or 0)
    if width > 0 and height > 0:
        if width >= height:
            score += 20
        score += min(width * height // 250_000, 30)
        if width > 2600:
            score -= 20
    if any(marker in lower for marker in ("caption", ".srt", ".vtt", ".json")):
        score -= 200
    if "prores" in lower:
        score -= 100
    if "thumbnail" in lower or "thumb" in lower:
        score -= 10
    return score


def _best_svs_asset(detail: dict[str, Any]) -> dict[str, Any]:
    candidates = [(instance, _svs_asset_score(instance)) for instance in _iter_svs_instances(detail)]
    candidates = [item for item in candidates if item[1] > 0]
    if not candidates:
        return {}
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def _svs_keywords(detail: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for item in detail.get("keywords") or []:
        if isinstance(item, dict):
            value = item.get("name") or item.get("title")
        else:
            value = item
        if value and str(value).strip():
            keywords.append(str(value).strip())
    return keywords[:20]


def search_svs(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search NASA Scientific Visualization Studio and return normalized candidates."""

    payload = _fetch_json(
        NASA_SVS_SEARCH_URL,
        params={"search": query, "limit": max(1, min(8, limit * 2))},
    )
    search_items = payload.get("results", []) if isinstance(payload, dict) else []
    results: list[dict[str, Any]] = []

    for inspected, item in enumerate(search_items, start=1):
        if inspected > max(4, limit * 2):
            break
        if not isinstance(item, dict):
            continue
        svs_id = item.get("id")
        if not svs_id:
            continue
        try:
            detail = _fetch_json(NASA_SVS_DETAIL_URL.format(svs_id=quote(str(svs_id), safe="")))
        except (requests.RequestException, ValueError):
            continue
        if not isinstance(detail, dict):
            continue
        title = _clean_text(detail.get("title") or item.get("title"))
        description = _compact(detail.get("description") or item.get("description"), 900)
        keywords = _svs_keywords(detail)
        score = _score_text(query, " ".join([title, description, " ".join(keywords)]))
        if _tokens(query) and score <= 0:
            continue
        asset = _best_svs_asset(detail)
        if not asset:
            continue
        download_url = str(asset.get("url") or "")
        media_type = _media_type_from_url(download_url)
        preview_url = ""
        main_image = detail.get("main_image")
        if isinstance(main_image, dict):
            preview_url = str(main_image.get("url") or "")
        if not preview_url and media_type == "image":
            preview_url = download_url
        results.append(
            _provider_result(
                provider="nasa_svs",
                item_id=str(svs_id),
                title=title or str(svs_id),
                media_type=media_type,
                source_url=str(detail.get("url") or item.get("url") or ""),
                download_url=download_url,
                preview_url=preview_url,
                credit="NASA SVS",
                description=description,
                date=str(detail.get("release_date") or item.get("release_date") or ""),
                keywords=keywords,
                width=int(asset.get("width") or 0) or None,
                height=int(asset.get("height") or 0) or None,
                relevance_score=score,
                selected_reason="NASA SVS visualization candidate for factual or explanatory visual beats.",
            )
        )
        if len(results) >= limit:
            break
    return results


def _infer_jpl_target(query: str) -> str:
    lower = str(query or "").lower()
    for needles, target in JPL_TARGET_HINTS:
        if any(needle in lower for needle in needles):
            return target
    return ""


def _jpl_target_url(target: str) -> str:
    return f"https://photojournal.jpl.nasa.gov/target/{quote(target, safe='')}"


def _jpl_candidate_id(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.rsplit("/", 1)[-1] or url


def _is_jpl_photojournal_item(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if "photojournal" not in path:
        return False
    blocked = (
        "/galleries/",
        "/search",
        "/latest",
        "/about",
        "/feedback",
        "/rss",
        "/wp-json/",
    )
    if any(marker in path for marker in blocked):
        return False
    return not path.rstrip("/").endswith("/photojournal")


def _fetch_jpl_detail(url: str) -> dict[str, str]:
    try:
        text, final_url = _fetch_text(url)
    except requests.RequestException:
        return {"source_url": url}
    parser = _LinkAndMetaParser(final_url)
    parser.feed(text)
    meta = parser.meta
    return {
        "source_url": final_url,
        "title": _clean_text(meta.get("og:title") or meta.get("title")),
        "description": _clean_text(meta.get("og:description") or meta.get("description")),
        "image": meta.get("og:image") or meta.get("twitter:image") or "",
    }


def search_jpl_photojournal(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Best-effort search over the NASA/JPL Photojournal target galleries."""

    target = _infer_jpl_target(query)
    if not target:
        return []
    try:
        text, final_url = _fetch_text(_jpl_target_url(target))
    except requests.RequestException:
        return []

    parser = _LinkAndMetaParser(final_url)
    parser.feed(text)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for link in parser.links:
        url = link.get("url", "")
        if not _is_jpl_photojournal_item(url):
            continue
        clean_url = url.split("#", 1)[0].rstrip("/")
        if clean_url.lower() in seen:
            continue
        seen.add(clean_url.lower())
        title = _clean_text(link.get("text"), _jpl_candidate_id(clean_url))
        score = _score_text(query, f"{title} {clean_url} {target}")
        if _tokens(query) and score <= 0:
            continue
        candidates.append({"url": clean_url, "title": title, "score": score})
        if len(candidates) >= limit * 3:
            break

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        detail = _fetch_jpl_detail(candidate["url"])
        title = detail.get("title") or candidate["title"]
        description = detail.get("description", "")
        image = detail.get("image", "")
        score = candidate["score"] + _score_text(query, f"{title} {description}")
        results.append(
            _provider_result(
                provider="jpl_photojournal",
                item_id=_jpl_candidate_id(detail.get("source_url") or candidate["url"]),
                title=title,
                media_type="image" if image else "page",
                source_url=detail.get("source_url") or candidate["url"],
                download_url=image,
                preview_url=image,
                credit="NASA/JPL-Caltech",
                description=description,
                keywords=[target],
                relevance_score=score,
                selected_reason=f"NASA/JPL Photojournal candidate from the {target} gallery.",
            )
        )
        if len(results) >= limit:
            break
    return results


def _provider_priority(provider: str) -> int:
    return {
        "nasa_images": 40,
        "nasa_svs": 35,
        "jpl_photojournal": 30,
    }.get(provider, 0)


def search_official_media(
    query: str,
    *,
    limit: int = 8,
    media_types: tuple[str, ...] = ("image", "video"),
    include_nasa_images: bool = True,
    include_svs: bool = True,
    include_jpl: bool = True,
    resolve_downloads: bool = True,
) -> list[dict[str, Any]]:
    """Search official media providers and return normalized, deduped results."""

    results: list[dict[str, Any]] = []
    per_provider_limit = max(2, min(4, limit))
    if include_nasa_images:
        try:
            results.extend(
                search_nasa_images(
                    query,
                    limit=per_provider_limit,
                    media_types=media_types,
                    resolve_downloads=resolve_downloads,
                )
            )
        except (requests.RequestException, ValueError):
            pass
    if include_svs:
        try:
            results.extend(search_svs(query, limit=per_provider_limit))
        except (requests.RequestException, ValueError):
            pass
    if include_jpl:
        try:
            results.extend(search_jpl_photojournal(query, limit=per_provider_limit))
        except (requests.RequestException, ValueError):
            pass

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        key = (
            str(result.get("download_url") or result.get("source_url") or result.get("id") or "")
            .strip()
            .lower()
        )
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(result)

    deduped.sort(
        key=lambda item: (
            int(item.get("relevance_score") or 0),
            _provider_priority(str(item.get("provider") or "")),
            1 if item.get("download_url") else 0,
        ),
        reverse=True,
    )
    return deduped[:limit]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search official media providers for Producer Mode")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=8, help="Maximum normalized results to print")
    parser.add_argument(
        "--provider",
        choices=["all", "nasa-images", "svs", "jpl"],
        default="all",
        help="Provider subset",
    )
    parser.add_argument(
        "--media-types",
        default="image,video",
        help="Comma-separated media types for NASA Images search",
    )
    parser.add_argument(
        "--no-resolve-downloads",
        action="store_true",
        help="Skip NASA Images collection lookups for original download URLs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    media_types = tuple(
        item.strip().lower()
        for item in args.media_types.split(",")
        if item.strip().lower() in {"image", "video"}
    ) or ("image", "video")
    results = search_official_media(
        args.query,
        limit=args.limit,
        media_types=media_types,
        include_nasa_images=args.provider in {"all", "nasa-images"},
        include_svs=args.provider in {"all", "svs"},
        include_jpl=args.provider in {"all", "jpl"},
        resolve_downloads=not args.no_resolve_downloads,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
