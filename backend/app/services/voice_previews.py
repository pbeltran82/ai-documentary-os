from __future__ import annotations

import hashlib
from typing import Any

from .media_library import MEDIA_ROOT, public_media_url, safe_component
from .narration_synthesis import _openai_tts, _wav_duration

DEFAULT_SAMPLE = (
    "Every documentary begins with a question. The voice should carry clarity, "
    "tension, and enough restraint to let the story speak for itself."
)


def generate_voice_preview(
    project_id: int,
    *,
    voice_id: str,
    speaking_rate: float,
    text: str = "",
) -> dict[str, Any]:
    sample = " ".join((text or DEFAULT_SAMPLE).split())[:600]
    fingerprint = hashlib.sha256(f"{voice_id}:{speaking_rate:.2f}:{sample}".encode("utf-8")).hexdigest()[:12]
    relative = (
        f"project-{project_id:04d}/production/narration/previews/"
        f"{safe_component(voice_id, 'voice')}-{fingerprint}.wav"
    )
    path = MEDIA_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    cached = path.is_file()
    if not cached:
        _openai_tts(path, sample, voice_id, speaking_rate)
    return {
        "voice_id": voice_id,
        "speaking_rate": speaking_rate,
        "text": sample,
        "relative_path": relative,
        "public_url": public_media_url(relative),
        "duration_seconds": _wav_duration(path),
        "cached": cached,
    }
