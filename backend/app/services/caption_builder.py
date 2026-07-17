from __future__ import annotations

import math
import re
import textwrap
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from ..models import Scene


MAX_CUE_CHARACTERS = 78
MAX_LINE_CHARACTERS = 42
MIN_CUE_SECONDS = 1.2


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _initial_chunks(text: str) -> list[str]:
    words = _clean(text).split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > MAX_CUE_CHARACTERS:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks


def caption_chunks(text: str, duration_seconds: float) -> list[str]:
    chunks = _initial_chunks(text)
    if not chunks:
        return []
    maximum_cues = max(1, math.floor(max(0.1, duration_seconds) / MIN_CUE_SECONDS))
    while len(chunks) > maximum_cues:
        eligible_pairs = [
            index
            for index in range(len(chunks) - 1)
            if len(chunks[index]) + 1 + len(chunks[index + 1])
            <= MAX_CUE_CHARACTERS
        ]
        if not eligible_pairs:
            break
        smallest_pair = min(
            eligible_pairs,
            key=lambda index: len(chunks[index]) + len(chunks[index + 1]),
        )
        chunks[smallest_pair:smallest_pair + 2] = [
            f"{chunks[smallest_pair]} {chunks[smallest_pair + 1]}"
        ]
    return chunks


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def _wrapped(value: str) -> str:
    return "\n".join(
        textwrap.wrap(
            value,
            width=MAX_LINE_CHARACTERS,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def build_srt(scenes: Iterable[Scene]) -> tuple[str, int]:
    cues: list[str] = []
    cue_number = 1
    for scene in sorted(scenes, key=lambda item: item.scene_number):
        start = max(0.0, float(scene.start_seconds))
        end = max(start + 0.1, float(scene.end_seconds))
        chunks = caption_chunks(scene.narration, end - start)
        if not chunks:
            continue
        weights = [max(1, len(chunk)) for chunk in chunks]
        total_weight = sum(weights)
        elapsed_weight = 0
        for index, (chunk, weight) in enumerate(zip(chunks, weights, strict=True)):
            cue_start = start + (end - start) * elapsed_weight / total_weight
            elapsed_weight += weight
            cue_end = (
                end
                if index == len(chunks) - 1
                else start + (end - start) * elapsed_weight / total_weight
            )
            cues.append(
                f"{cue_number}\n{_timestamp(cue_start)} --> {_timestamp(cue_end)}\n{_wrapped(chunk)}"
            )
            cue_number += 1
    content = "\n\n".join(cues)
    return (content + "\n" if content else ""), cue_number - 1


def write_caption_track(scenes: Iterable[Scene], path: Path) -> int:
    content, cue_count = build_srt(scenes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)
    return cue_count
