from __future__ import annotations

from typing import Any

from PIL import Image

from . import animation_script_runtime as runtime
from . import character_explainer as character

_ORIGINAL_CAMERA_MOVE = character._camera_move


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _directed_crop(
    image: Image.Image,
    *,
    zoom: float,
    focus_x: float,
    focus_y: float,
) -> Image.Image:
    width, height = image.size
    zoom = max(1.0, zoom)
    scaled_width = max(width, round(width * zoom))
    scaled_height = max(height, round(height * zoom))
    scaled = image.resize((scaled_width, scaled_height), Image.Resampling.BICUBIC)
    left = round((scaled_width - width) * _clamp(focus_x))
    top = round((scaled_height - height) * _clamp(focus_y))
    return scaled.crop((left, top, left + width, top + height))


def apply_camera_direction(
    image: Image.Image,
    motion: dict[str, Any],
    progress: float,
) -> Image.Image:
    mode = str(motion.get("mode") or "hold")
    intensity = _clamp(float(motion.get("intensity") or 0.0)) * 0.10
    focus = motion.get("focus") or [0.5, 0.5]
    focus_x = float(focus[0]) if len(focus) > 0 else 0.5
    focus_y = float(focus[1]) if len(focus) > 1 else 0.5
    eased = _smooth(progress)

    if mode == "push_in":
        zoom = 1 + intensity * eased
    elif mode == "pull_back":
        zoom = 1 + intensity * (1 - eased)
    elif mode == "track":
        zoom = 1 + intensity * 0.55
        focus_x = _clamp(focus_x - 0.22 + 0.44 * eased)
    elif mode == "drift":
        zoom = 1 + intensity * 0.45
        focus_x = _clamp(focus_x + (eased - 0.5) * 0.24)
    elif mode == "settle":
        zoom = 1 + intensity * _smooth(min(1.0, progress / 0.68))
    else:
        return image

    return _directed_crop(
        image,
        zoom=zoom,
        focus_x=focus_x,
        focus_y=focus_y,
    )


def _planned_camera_move(image: Image.Image, template_id: str, progress: float) -> Image.Image:
    framed = _ORIGINAL_CAMERA_MOVE(image, template_id, progress)
    plan = runtime._ACTIVE_PLAN or {}
    motion = plan.get("camera_motion")
    if not isinstance(motion, dict):
        return framed
    return apply_camera_direction(framed, motion, progress)


character._camera_move = _planned_camera_move
