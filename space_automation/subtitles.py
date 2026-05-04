from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path


@dataclass(slots=True)
class SubtitleSegment:
    index: int
    start_seconds: float
    end_seconds: float
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    parts = re.split(r"(?<=[.!?])\s+", normalized)
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned or [normalized]


def _format_srt_timestamp(total_seconds: float) -> str:
    if total_seconds < 0:
        total_seconds = 0.0

    duration = timedelta(seconds=total_seconds)
    total_ms = int(duration.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def build_subtitle_segments(script: str, duration_seconds: float) -> list[SubtitleSegment]:
    sentences = _split_sentences(script)
    if not sentences:
        raise ValueError("Cannot build subtitles from an empty script.")
    if duration_seconds <= 0:
        raise ValueError("Subtitle duration must be greater than zero.")

    total_units = sum(max(len(sentence), 12) for sentence in sentences)
    current_time = 0.0
    segments: list[SubtitleSegment] = []

    for index, sentence in enumerate(sentences, start=1):
        weight = max(len(sentence), 12)
        if index == len(sentences):
            end_time = duration_seconds
        else:
            segment_duration = duration_seconds * (weight / total_units)
            end_time = min(duration_seconds, current_time + segment_duration)

        segments.append(
            SubtitleSegment(
                index=index,
                start_seconds=current_time,
                end_seconds=end_time,
                text=sentence,
            )
        )
        current_time = end_time

    return segments


def write_srt(script: str, duration_seconds: float, output_path: Path) -> list[SubtitleSegment]:
    segments = build_subtitle_segments(script, duration_seconds)
    lines: list[str] = []
    for segment in segments:
        lines.extend(
            [
                str(segment.index),
                (
                    f"{_format_srt_timestamp(segment.start_seconds)} --> "
                    f"{_format_srt_timestamp(segment.end_seconds)}"
                ),
                segment.text,
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return segments
