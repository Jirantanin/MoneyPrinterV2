from __future__ import annotations

import json
import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from space_automation.config import SpaceAutomationConfig
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from config import SpaceAutomationConfig


@dataclass(slots=True)
class ApodPayload:
    date: str
    title: str
    explanation: str
    media_type: str
    url: str
    hdurl: str | None = None
    copyright: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _apod_html_url(target_date: str | None = None) -> str:
    if not target_date:
        return "https://apod.nasa.gov/apod/astropix.html"

    compact = target_date.replace("-", "")
    if len(compact) != 8 or not compact.isdigit():
        return "https://apod.nasa.gov/apod/astropix.html"

    yy = compact[2:4]
    mm = compact[4:6]
    dd = compact[6:8]
    return f"https://apod.nasa.gov/apod/ap{yy}{mm}{dd}.html"


def _strip_html(fragment: str) -> str:
    text = re.sub(r"<\s*br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fetch_apod_from_web(config: SpaceAutomationConfig, target_date: str | None = None) -> ApodPayload:
    page_url = _apod_html_url(target_date)
    request = urllib.request.Request(
        page_url,
        headers={"User-Agent": "MoneyPrinterV2-SpaceAutomation/1.0"},
    )
    with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
        html = response.read().decode("utf-8", errors="replace")

    date_match = re.search(r"<p>\s*([0-9]{4}\s+[A-Za-z]+\s+[0-9]{1,2})\s*<br>", html, flags=re.IGNORECASE)
    title_match = re.search(r"<center>\s*<b>\s*(.*?)\s*</b>\s*<br>", html, flags=re.IGNORECASE | re.DOTALL)
    image_match = re.search(r'<a\s+href="([^"]+\.(?:jpg|jpeg|png|webp))"\s*>\s*<img', html, flags=re.IGNORECASE)
    explanation_match = re.search(
        r"<b>\s*Explanation:\s*</b>\s*(.*?)(?:<p>\s*<center>|<center>\s*<b>\s*Tomorrow's picture:|<p>\s*<a href=)",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    copyright_match = re.search(
        r"<b>\s*Image Credit(?: &amp;| &)\s*Copyright:\s*</b>\s*(.*?)</center>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not title_match or not image_match or not explanation_match:
        raise RuntimeError("Could not parse APOD web page structure.")

    image_url = urllib.parse.urljoin(page_url, unescape(image_match.group(1).strip()))
    explanation = _strip_html(explanation_match.group(1))
    title = _strip_html(title_match.group(1))
    copyright_text = _strip_html(copyright_match.group(1)) if copyright_match else None
    apod_date = date_match.group(1).strip() if date_match else (target_date or "")

    return ApodPayload(
        date=apod_date,
        title=title,
        explanation=explanation,
        media_type="image",
        url=image_url,
        hdurl=image_url,
        copyright=copyright_text or None,
    )


def fetch_apod(config: SpaceAutomationConfig, target_date: str | None = None) -> ApodPayload:
    query = {
        "api_key": config.nasa_api_key,
    }
    if target_date:
        query["date"] = target_date

    url = f"{config.nasa_apod_url}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MoneyPrinterV2-SpaceAutomation/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if 500 <= exc.code <= 599:
            return _fetch_apod_from_web(config, target_date=target_date)
        raise
    except urllib.error.URLError:
        return _fetch_apod_from_web(config, target_date=target_date)

    return ApodPayload(
        date=str(payload.get("date", "")),
        title=str(payload.get("title", "")).strip(),
        explanation=str(payload.get("explanation", "")).strip(),
        media_type=str(payload.get("media_type", "")).strip(),
        url=str(payload.get("url", "")).strip(),
        hdurl=str(payload.get("hdurl", "")).strip() or None,
        copyright=str(payload.get("copyright", "")).strip() or None,
    )


def download_apod_image(apod: ApodPayload, config: SpaceAutomationConfig, job_dir: Path) -> Path:
    image_url = apod.hdurl or apod.url
    if not image_url:
        raise ValueError("APOD response did not include an image URL.")

    parsed = urllib.parse.urlparse(image_url)
    suffix = Path(parsed.path).suffix
    if not suffix:
        guessed_type, _ = mimetypes.guess_type(image_url)
        suffix = mimetypes.guess_extension(guessed_type or "") or ".jpg"

    image_path = job_dir / f"apod_image{suffix}"
    request = urllib.request.Request(
        image_url,
        headers={"User-Agent": "MoneyPrinterV2-SpaceAutomation/1.0"},
    )
    with urllib.request.urlopen(request, timeout=config.request_timeout_seconds) as response:
        image_path.write_bytes(response.read())

    return image_path
