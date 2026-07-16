from __future__ import annotations

from PIL import Image, ImageDraw

from . import animation_script_runtime as runtime
from . import character_expressive as character
from . import character_staging as staging

SUPPORTED_POSES = {
    "idle",
    "receive",
    "point",
    "phone",
    "tap",
    "celebrate",
    "relaxed",
    "slump",
    "walk",
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _sequence_state(
    values: list[str],
    progress: float,
    fallback: str,
    *,
    mapper=lambda value: value,
) -> tuple[str, str, float]:
    if not values:
        return fallback, fallback, 0.0
    position = _clamp(progress) * len(values)
    index = min(len(values) - 1, int(min(position, len(values) - 0.000001)))
    local = position - index
    current = mapper(values[index])
    following = mapper(values[min(len(values) - 1, index + 1)])
    blend = _smooth((local - 0.80) / 0.20) if current != following else 0.0
    return current, following, blend


def _supported_pose(value: str, fallback: str) -> str:
    normalized = value.lower().strip()
    return normalized if normalized in SUPPORTED_POSES else fallback


def _render_person_layer(
    size: tuple[int, int],
    args: tuple,
    kwargs: dict,
    *,
    pose: str,
    mood: str,
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    runtime._ORIGINAL_PERSON(
        ImageDraw.Draw(layer),
        *args,
        pose=pose,
        mood=mood,
        **kwargs,
    )
    return layer


def _stable_planned_person(*args, pose: str = "idle", mood: str = "neutral", **kwargs):
    """Consume saved direction with supported poses and short eased transitions."""
    plan = runtime._ACTIVE_PLAN
    if not plan:
        return runtime._ORIGINAL_PERSON(*args, pose=pose, mood=mood, **kwargs)

    progress = character._CURRENT_TIME / max(0.01, character._CURRENT_DURATION)
    poses = [str(value) for value in (plan.get("pose_sequence") or [])]
    expressions = [str(value) for value in (plan.get("expression_sequence") or [])]

    current_pose, next_pose, pose_blend = _sequence_state(
        poses,
        progress,
        pose,
        mapper=lambda value: _supported_pose(value, pose),
    )
    current_mood, next_mood, mood_blend = _sequence_state(
        expressions,
        progress,
        mood,
        mapper=runtime._mapped_expression,
    )
    blend = max(pose_blend, mood_blend)

    # Ordinary unit tests and non-Pillow callers do not expose a backing image.
    # They still receive the stabilized current state without crossfade work.
    draw = args[0] if args else None
    base_image = getattr(draw, "_image", None)
    if not isinstance(base_image, Image.Image) or blend <= 0.0:
        return runtime._ORIGINAL_PERSON(
            *args,
            pose=current_pose,
            mood=current_mood,
            **kwargs,
        )

    layer_args = args[1:]
    current_layer = _render_person_layer(
        base_image.size,
        layer_args,
        kwargs,
        pose=current_pose,
        mood=current_mood,
    )
    next_layer = _render_person_layer(
        base_image.size,
        layer_args,
        kwargs,
        pose=next_pose,
        mood=next_mood,
    )
    character_layer = Image.blend(current_layer, next_layer, blend)
    composite = Image.alpha_composite(base_image.convert("RGBA"), character_layer)
    base_image.paste(composite.convert(base_image.mode))
    return None


runtime._planned_person = _stable_planned_person
staging.base._person = _stable_planned_person
