from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Scene
from . import timeline_builder as base


@dataclass(frozen=True)
class StillDirection:
    motion: str
    reason: str
    focal_x: float
    focal_y: float
    composition_profile: str
    blur_sigma: int
    background_brightness: float
    background_saturation: float


READABILITY_WORDS = set(base.READABILITY_WORDS)
EMPHASIS_WORDS = set(base.EMPHASIS_WORDS)
REVEAL_WORDS = set(base.REVEAL_WORDS)
HUMAN_WORDS = {
    "person",
    "people",
    "worker",
    "employee",
    "woman",
    "man",
    "family",
    "couple",
    "child",
    "face",
    "portrait",
    "customer",
    "investor",
    "consumer",
    "shopper",
    "founder",
    "owner",
}
ARCHIVAL_WORDS = {
    "archive",
    "archival",
    "historic",
    "historical",
    "factory",
    "city",
    "street",
    "building",
    "landscape",
    "panorama",
}


def _words(scene: Scene) -> set[str]:
    context = " ".join(
        [scene.narration, scene.visual_intent, *scene.search_keywords]
    ).lower()
    return {
        "".join(character for character in token if character.isalnum())
        for token in context.replace("&", " ").split()
    } - {""}


def direct_still(scene: Scene, clip_index: int) -> StillDirection:
    asset = scene.selected_asset
    duration = float(scene.duration_seconds)
    words = _words(scene)
    width = int(asset.width if asset is not None else 0)
    height = int(asset.height if asset is not None else 0)
    ratio = width / height if width > 0 and height > 0 else 0.0

    if duration < 1.75:
        return StillDirection(
            "static",
            "Very short still held steady with a centered safe focal point",
            0.50,
            0.50,
            "readability_hold",
            28,
            -0.18,
            0.78,
        )

    if words & READABILITY_WORDS:
        return StillDirection(
            "static",
            "Text, chart, map, or interface content stays centered and steady for readability",
            0.50,
            0.50,
            "readability_hold",
            28,
            -0.16,
            0.82,
        )

    if words & HUMAN_WORDS:
        focal_x = 0.42 if scene.scene_number % 2 else 0.58
        focal_y = 0.34 if ratio and ratio < 1.15 else 0.40
        return StillDirection(
            "zoom_in",
            "Likely human subject receives an upper-third focal point and restrained push-in",
            focal_x,
            focal_y,
            "human_upper_third",
            34,
            -0.22,
            0.80,
        )

    if ratio and ratio < 1.10:
        focal_x = 0.44 if scene.scene_number % 2 else 0.56
        return StillDirection(
            "zoom_in",
            "Portrait-oriented source keeps upper-frame headroom over a soft cinematic background",
            focal_x,
            0.38,
            "portrait_safe",
            38,
            -0.24,
            0.76,
        )

    if ratio >= 1.85 and duration >= 4:
        motion = "pan_left" if scene.scene_number % 2 else "pan_right"
        return StillDirection(
            motion,
            "Wide archival or environmental composition receives a slow edge-safe documentary pan",
            0.50,
            0.50,
            "wide_documentary_pan",
            26,
            -0.18,
            0.80,
        )

    if words & EMPHASIS_WORDS:
        return StillDirection(
            "zoom_in",
            "Narrative emphasis receives a centered focal lock and restrained push-in",
            0.50,
            0.48,
            "emphasis_lock",
            30,
            -0.20,
            0.80,
        )

    if words & REVEAL_WORDS:
        return StillDirection(
            "zoom_out",
            "Growth or reveal language receives a centered pull-out that exposes more context",
            0.50,
            0.50,
            "context_reveal",
            28,
            -0.18,
            0.82,
        )

    if words & ARCHIVAL_WORDS and duration >= 4:
        motion = "pan_left" if clip_index % 2 == 0 else "pan_right"
        return StillDirection(
            motion,
            "Archival context receives a restrained documentary pan with protected frame edges",
            0.50,
            0.50,
            "archival_context",
            30,
            -0.20,
            0.76,
        )

    motion = "zoom_in" if clip_index % 2 == 0 else "zoom_out"
    focal_x = 0.46 if clip_index % 2 == 0 else 0.54
    return StillDirection(
        motion,
        "Balanced focal bias and restrained motion prevent a generic centered slideshow feel",
        focal_x,
        0.48,
        "balanced_editorial",
        30,
        -0.19,
        0.80,
    )


_original_scene_clip = base.scene_clip
_original_apply_edit_decisions = base.apply_edit_decisions
_original_build_timeline_plan = base.build_timeline_plan


def scene_clip(
    scene: Scene,
    input_index: int,
    style: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    clip, error = _original_scene_clip(scene, input_index, style)
    if clip is None or clip["media_type"] != "photo":
        return clip, error

    if str(style["photo_motion"]) == "editorial":
        direction = direct_still(scene, input_index)
        clip["motion_effect"] = direction.motion
        clip["motion_reason"] = direction.reason
    else:
        direction = StillDirection(
            str(clip["motion_effect"]),
            str(clip["motion_reason"]),
            0.50,
            0.50,
            "manual_motion",
            28,
            -0.18,
            0.78,
        )

    clip["focal_point"] = {
        "x": round(direction.focal_x, 3),
        "y": round(direction.focal_y, 3),
    }
    clip["composition_profile"] = direction.composition_profile
    clip["background_treatment"] = {
        "blur_sigma": direction.blur_sigma,
        "brightness": direction.background_brightness,
        "saturation": direction.background_saturation,
    }
    clip["source_width"] = int(scene.selected_asset.width if scene.selected_asset else 0)
    clip["source_height"] = int(scene.selected_asset.height if scene.selected_asset else 0)
    return clip, error


def _zoom_parameters(
    clip: dict[str, Any],
    frames: int,
    duration: float,
) -> tuple[str, str, str]:
    motion = str(clip["motion_effect"])
    focal = clip.get("focal_point") or {"x": 0.5, "y": 0.5}
    focal_x = max(0.12, min(0.88, float(focal.get("x", 0.5))))
    focal_y = max(0.12, min(0.88, float(focal.get("y", 0.5))))
    progress = f"on/{max(1, frames - 1)}"
    delta = 0.045 if duration <= 3 else 0.065 if duration <= 7 else 0.085

    if motion == "zoom_out":
        zoom = f"{1 + delta:.3f}-{delta:.3f}*{progress}"
        return (
            zoom,
            f"(iw-iw/zoom)*{focal_x:.3f}",
            f"(ih-ih/zoom)*{focal_y:.3f}",
        )
    if motion in {"pan_left", "pan_right"}:
        zoom = "1.060"
        left = max(0.05, focal_x - 0.34)
        right = min(0.95, focal_x + 0.34)
        start, end = (right, left) if motion == "pan_left" else (left, right)
        x_position = f"(iw-iw/zoom)*({start:.3f}+({end - start:.3f})*{progress})"
        return zoom, x_position, f"(ih-ih/zoom)*{focal_y:.3f}"

    zoom = f"1.000+{delta:.3f}*{progress}"
    return (
        zoom,
        f"(iw-iw/zoom)*{focal_x:.3f}",
        f"(ih-ih/zoom)*{focal_y:.3f}",
    )


def normalized_photo_filter(
    clip: dict[str, Any],
    processed_duration: float,
) -> str:
    index = clip["input_index"]
    width, height = base.output_dimensions(clip)
    motion = str(clip["motion_effect"])
    frames = max(2, int(round(processed_duration * base.OUTPUT_FPS)))
    background_label = f"photo_bg_{index}"
    foreground_label = f"photo_fg_{index}"
    blurred_label = f"photo_blur_{index}"
    framed_label = f"photo_frame_{index}"
    treatment = clip.get("background_treatment") or {}
    sigma = int(treatment.get("blur_sigma", 28))
    brightness = float(treatment.get("brightness", -0.18))
    saturation = float(treatment.get("saturation", 0.78))

    graph = (
        f"[{index}:v]"
        f"trim=duration={processed_duration:.3f},"
        "setpts=PTS-STARTPTS,"
        f"split=2[{background_label}][{foreground_label}];"
        f"[{background_label}]"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"gblur=sigma={sigma},"
        f"eq=brightness={brightness:.3f}:saturation={saturation:.3f},"
        f"setsar=1[{blurred_label}];"
        f"[{foreground_label}]"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        "eq=contrast=1.035:saturation=1.035,"
        f"setsar=1[{framed_label}];"
        f"[{blurred_label}][{framed_label}]"
        "overlay=(W-w)/2:(H-h)/2:shortest=1,"
    )
    if motion == "static":
        return graph + f"fps={base.OUTPUT_FPS},format=yuv420p"

    zoom, x_position, y_position = _zoom_parameters(
        clip,
        frames,
        processed_duration,
    )
    return (
        graph
        + f"zoompan=z='{zoom}':"
        f"x='{x_position}':"
        f"y='{y_position}':"
        f"d=1:s={width}x{height}:fps={base.OUTPUT_FPS},"
        "format=yuv420p"
    )


def apply_edit_decisions(
    clips: list[dict[str, Any]],
    style: dict[str, Any],
) -> None:
    _original_apply_edit_decisions(clips, style)
    for clip in clips:
        if clip["media_type"] != "photo":
            continue
        profile = str(clip.get("composition_profile", "balanced_editorial")).replace("_", " ")
        clip["assembly_action"] += f"; focal profile: {profile}"


def build_timeline_plan(project, style=None) -> dict[str, Any]:
    plan = _original_build_timeline_plan(project, style)
    plan["schema_version"] = "0.5"
    plan["settings"]["still_direction"] = "subject_aware"
    return plan


base.scene_clip = scene_clip
base.normalized_photo_filter = normalized_photo_filter
base.apply_edit_decisions = apply_edit_decisions
base.build_timeline_plan = build_timeline_plan

render_first_cut = base.render_first_cut
write_timeline_plan = base.write_timeline_plan
