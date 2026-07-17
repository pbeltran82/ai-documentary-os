from __future__ import annotations

import math
from typing import Iterable

from PIL import Image, ImageDraw

from . import character_staging_clean as clean
from . import character_staging as staged


_CURRENT_TIME = 0.0
_CURRENT_DURATION = 1.0
_original_render_frame = clean.render_frame


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _smooth(value: float) -> float:
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _ease_out_back(value: float) -> float:
    value = _clamp(value)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (value - 1) ** 3 + c1 * (value - 1) ** 2


def _performance_pulse() -> float:
    progress = (_CURRENT_TIME / max(0.01, _CURRENT_DURATION)) % 1.0
    local = (progress * 3.0) % 1.0
    if local < 0.22:
        return -0.10 * (local / 0.22)
    if local < 0.58:
        return 0.13 * _ease_out_back((local - 0.22) / 0.36)
    return 0.13 * (1 - (local - 0.58) / 0.42)


def _point(origin: tuple[float, float], angle: float, length: float) -> tuple[int, int]:
    radians = math.radians(angle)
    return (
        round(origin[0] + math.cos(radians) * length),
        round(origin[1] + math.sin(radians) * length),
    )


def _limb(
    draw: ImageDraw.ImageDraw,
    points: Iterable[tuple[int, int]],
    color: tuple[int, int, int],
    width: int,
) -> None:
    sequence = list(points)
    if len(sequence) < 2:
        return
    draw.line(sequence, fill=(3, 6, 14), width=width + max(3, width // 3), joint="curve")
    draw.line(sequence, fill=color, width=width, joint="curve")
    radius = max(3, width // 2)
    for x, y in sequence[1:-1]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def _hand(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    color: tuple[int, int, int],
    scale: float,
    *,
    open_hand: bool = False,
    hand_shape: str | None = None,
    facing: int = 1,
) -> None:
    x, y = center
    shape = hand_shape or ("wave" if open_hand else "relaxed")
    radius = max(8, round(13 * scale))
    draw.ellipse((x - radius - 3, y - radius + 4, x + radius + 3, y + radius + 8), fill=(3, 6, 14))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    stroke = max(2, round(3 * scale))
    if shape == "wave":
        finger_width = max(2, round(3 * scale))
        for offset, angle in zip((-6, 0, 6), (-105, -90, -75), strict=True):
            start = (x + round(offset * scale), y - round(5 * scale))
            end = _point(start, angle, round(12 * scale))
            draw.line((start, end), fill=color, width=finger_width)
    elif shape == "point":
        start = (x + facing * round(7 * scale), y - round(3 * scale))
        end = (x + facing * round(27 * scale), y - round(6 * scale))
        draw.line((start, end), fill=color, width=stroke + 1)
    elif shape == "cup":
        draw.arc(
            (x - round(8 * scale), y - round(7 * scale), x + round(10 * scale), y + round(9 * scale)),
            15 if facing > 0 else 165,
            165 if facing > 0 else 345,
            fill=(3, 6, 14),
            width=max(1, stroke - 1),
        )
    elif shape == "fist":
        for offset in (-5, 2):
            draw.line(
                (x - round(7 * scale), y + round(offset * scale), x + round(7 * scale), y + round(offset * scale)),
                fill=(3, 6, 14),
                width=max(1, stroke - 1),
            )


def _hair(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    scale: float,
    *,
    style: str,
    color: tuple[int, int, int],
    facing: int,
) -> None:
    x, y = center
    if style == "curly_crop":
        radius = max(7, round(11 * scale))
        for offset, drop in ((-28, 7), (-14, 1), (0, -2), (14, 1), (28, 7)):
            cx = x + round(offset * scale)
            cy = y - round((38 - drop) * scale)
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
        return

    # A low side part leaves the brows and eyes fully readable.
    points = (
        (x - round(37 * scale), y - round(8 * scale)),
        (x - round(33 * scale), y - round(27 * scale)),
        (x - round(18 * scale), y - round(40 * scale)),
        (x + round(8 * scale), y - round(44 * scale)),
        (x + round(34 * scale), y - round(25 * scale)),
        (x + round(37 * scale), y - round(10 * scale)),
        (x + facing * round(12 * scale), y - round(25 * scale)),
        (x - facing * round(8 * scale), y - round(29 * scale)),
    )
    draw.polygon(points, fill=color)
    draw.line(
        (x + facing * round(9 * scale), y - round(42 * scale), x - facing * round(3 * scale), y - round(28 * scale)),
        fill=(91, 68, 57),
        width=max(1, round(2 * scale)),
    )


def _shoe(
    draw: ImageDraw.ImageDraw,
    ankle: tuple[int, int],
    facing: int,
    color: tuple[int, int, int],
    scale: float,
) -> None:
    x, y = ankle
    length = round(38 * scale)
    height = round(16 * scale)
    left = x - round(9 * scale) if facing > 0 else x - length
    right = x + length if facing > 0 else x + round(9 * scale)
    draw.rounded_rectangle((left + 5, y - height + 6, right + 5, y + 8), radius=max(5, height // 2), fill=(3, 6, 14))
    draw.rounded_rectangle((left, y - height, right, y + 2), radius=max(5, height // 2), fill=color)


def _expression(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    scale: float,
    mood: str,
    facing: int,
) -> None:
    x, y = center
    ink = palette["ink"]
    blink_phase = (_CURRENT_TIME * 2.15) % 3.4
    blinking = blink_phase > 3.22
    gaze = facing * round(3 * scale)
    eye_y = y - round(7 * scale)
    eye_dx = round(14 * scale)
    eye_radius = max(2, round(4 * scale))
    for eye_x in (x - eye_dx, x + eye_dx):
        if blinking:
            draw.line((eye_x - eye_radius, eye_y, eye_x + eye_radius, eye_y), fill=ink, width=max(2, round(3 * scale)))
        else:
            draw.ellipse(
                (
                    eye_x + gaze - eye_radius,
                    eye_y - eye_radius,
                    eye_x + gaze + eye_radius,
                    eye_y + eye_radius,
                ),
                fill=ink,
            )

    brow_y = eye_y - round(13 * scale)
    brow_width = max(2, round(3 * scale))
    if mood in {"sad", "concerned"}:
        draw.line((x - round(23 * scale), brow_y - round(4 * scale), x - round(7 * scale), brow_y + round(2 * scale)), fill=ink, width=brow_width)
        draw.line((x + round(7 * scale), brow_y + round(2 * scale), x + round(23 * scale), brow_y - round(4 * scale)), fill=ink, width=brow_width)
    elif mood == "happy":
        draw.line((x - round(22 * scale), brow_y, x - round(7 * scale), brow_y - round(2 * scale)), fill=ink, width=brow_width)
        draw.line((x + round(7 * scale), brow_y - round(2 * scale), x + round(22 * scale), brow_y), fill=ink, width=brow_width)
    elif mood == "confident":
        draw.line((x - round(22 * scale), brow_y, x - round(7 * scale), brow_y), fill=ink, width=brow_width)
        draw.line((x + round(7 * scale), brow_y, x + round(22 * scale), brow_y), fill=ink, width=brow_width)

    mouth_y = y + round(15 * scale)
    mouth_width = round(18 * scale)
    stroke = max(2, round(3 * scale))
    if mood == "happy":
        draw.arc((x - mouth_width, mouth_y - round(10 * scale), x + mouth_width, mouth_y + round(11 * scale)), 10, 170, fill=ink, width=stroke)
    elif mood == "confident":
        subtle = round(14 * scale)
        draw.arc((x - subtle, mouth_y - round(7 * scale), x + subtle, mouth_y + round(8 * scale)), 15, 165, fill=ink, width=stroke)
    elif mood in {"sad", "concerned"}:
        draw.arc((x - mouth_width, mouth_y - round(2 * scale), x + mouth_width, mouth_y + round(18 * scale)), 190, 350, fill=ink, width=stroke)
    elif mood == "surprised":
        radius = max(4, round(7 * scale))
        draw.ellipse((x - radius, mouth_y - radius, x + radius, mouth_y + radius), outline=ink, width=stroke)
    else:
        draw.line((x - round(12 * scale), mouth_y, x + round(12 * scale), mouth_y), fill=ink, width=stroke)


def _expressive_person(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    *,
    scale: float = 1.0,
    pose: str = "idle",
    mood: str = "neutral",
    facing: int = 1,
    alternate: bool = False,
    hair_style: str | None = None,
    hair_color: tuple[int, int, int] | None = None,
) -> None:
    x, ground_y = center
    body = palette["person_alt"] if alternate else palette["person"]
    skin = palette["skin"]
    outline = (3, 6, 14)
    pulse = _performance_pulse()
    motion_phase = _CURRENT_TIME * 6.2
    gait = math.sin(motion_phase) if pose == "walk" else 0.0
    scene_progress = _CURRENT_TIME / max(0.01, _CURRENT_DURATION)
    step_progress = _clamp((scene_progress - 0.02) / 0.13) if pose == "step_in" else 0.0
    step_eased = _smooth(step_progress)
    step_start_x = x
    step_final_x = x

    # A readable walk needs vertical weight transfer as well as changing leg
    # angles. Keeping both hips and feet on one flat rail produced the previous
    # skating silhouette.
    if pose == "walk":
        x += round(3 * gait * scale)
        ground_y -= round(4 * abs(gait) * scale)
    elif pose == "step_in":
        step_final_x = x
        step_start_x = x - facing * round(36 * scale)
        x = round(step_start_x + (step_final_x - step_start_x) * step_eased)
        ground_y -= round(3 * math.sin(math.pi * step_progress) ** 2 * scale)

    posture = {
        "slump": (18, 11, -7),
        "celebrate": (-3, -2, 4),
        "relaxed": (4, 2, 3),
        "tap": (-2, -3, 5),
        "receive": (-5, -2, 5),
        "point": (-3, -2, 6),
        "step_in": (0, 0, 3),
        "walk": (0, 0, 7),
        "run": (-4, -3, 13),
        "look": (0, 0, 4),
        "think": (5, 3, -4),
        "wave": (-2, -2, 5),
        "shrug": (-7, -2, 0),
        "confused": (5, 4, -5),
        "nod": (0, round(6 * math.sin(motion_phase * 0.55)), 0),
        "shake_head": (0, 0, round(7 * math.sin(motion_phase * 0.7))),
        "type": (-1, -2, 6),
        "swipe": (-2, -2, 7),
    }.get(pose, (0, 0, 0))
    shoulder_drop, head_drop, lean = posture
    lean += pulse * 8 * facing

    hip = (x, ground_y - round(78 * scale))
    shoulder = (x + round(lean * scale), ground_y - round((178 - shoulder_drop) * scale))
    neck = (shoulder[0] + round(2 * facing * scale), shoulder[1] - round(22 * scale))
    head = (neck[0] + round((5 + pulse * 4) * facing * scale), neck[1] - round((54 - head_drop) * scale))
    if pose == "look":
        head = (head[0] + round(8 * math.sin(motion_phase * 0.35) * scale), head[1])
    elif pose == "shake_head":
        head = (head[0] + round(10 * math.sin(motion_phase * 0.7) * scale), head[1])

    torso_width = round(54 * scale)
    shoulder_width = round(47 * scale)
    torso_box = (
        shoulder[0] - shoulder_width,
        shoulder[1] - round(8 * scale),
        hip[0] + torso_width,
        hip[1] + round(18 * scale),
    )
    draw.rounded_rectangle(
        (torso_box[0] + 7, torso_box[1] + 9, torso_box[2] + 7, torso_box[3] + 9),
        radius=round(34 * scale),
        fill=outline,
    )
    draw.rounded_rectangle(torso_box, radius=round(34 * scale), fill=body)

    head_radius_x = round(39 * scale)
    head_radius_y = round(44 * scale)
    draw.ellipse((head[0] - head_radius_x + 7, head[1] - head_radius_y + 9, head[0] + head_radius_x + 7, head[1] + head_radius_y + 9), fill=outline)
    draw.ellipse((head[0] - head_radius_x, head[1] - head_radius_y, head[0] + head_radius_x, head[1] + head_radius_y), fill=skin, outline=body, width=max(3, round(5 * scale)))
    resolved_hair_style = hair_style or ("curly_crop" if alternate else "side_part")
    resolved_hair_color = hair_color or ((46, 32, 25) if alternate else (35, 31, 29))
    _hair(draw, head, scale, style=resolved_hair_style, color=resolved_hair_color, facing=facing)
    _expression(draw, head, palette, scale, mood, facing)

    shoulder_left = (shoulder[0] - round(37 * scale), shoulder[1] + round(8 * scale))
    shoulder_right = (shoulder[0] + round(37 * scale), shoulder[1] + round(8 * scale))
    limb_width = max(7, round(14 * scale))

    front_shape = "relaxed"
    rear_shape = "relaxed"
    if pose == "receive":
        front_hand = (x + facing * round((78 + pulse * 8) * scale), shoulder[1] + round((54 - pulse * 5) * scale))
        rear_hand = (x - facing * round(50 * scale), shoulder[1] + round(104 * scale))
        front_shape = "cup"
    elif pose == "point":
        front_hand = (x + facing * round((102 + pulse * 8) * scale), shoulder[1] + round((31 - pulse * 5) * scale))
        rear_hand = (x - facing * round(46 * scale), shoulder[1] + round(94 * scale))
        front_shape = "point"
    elif pose in {"phone", "tap"}:
        front_hand = (x + facing * round(72 * scale), shoulder[1] + round(52 * scale))
        rear_hand = (x + facing * round(28 * scale), shoulder[1] + round(72 * scale))
    elif pose == "celebrate":
        # One compact accent hand and one grounded hand read as confidence,
        # without the symmetrical open-palm "stick-up" silhouette.
        front_hand = (x + facing * round((84 + pulse * 8) * scale), shoulder[1] - round((10 + pulse * 8) * scale))
        rear_hand = (x - facing * round(38 * scale), shoulder[1] + round(72 * scale))
        front_shape = "fist"
    elif pose == "slump":
        front_hand = (x + round(54 * scale), shoulder[1] + round(124 * scale))
        rear_hand = (x - round(54 * scale), shoulder[1] + round(124 * scale))
    elif pose == "wave":
        wave = math.sin(motion_phase * 1.15)
        front_hand = (x + facing * round((80 + 10 * wave) * scale), shoulder[1] - round(86 * scale))
        rear_hand = (x - facing * round(66 * scale), shoulder[1] + round(102 * scale))
        front_shape = "wave"
    elif pose in {"shrug", "confused"}:
        lift = round((30 + 5 * math.sin(motion_phase * 0.5)) * scale)
        front_hand = (x + facing * round(94 * scale), shoulder[1] + lift)
        rear_hand = (x - facing * round(54 * scale), shoulder[1] + round(102 * scale))
        front_shape = "cup"
    elif pose == "think":
        front_hand = (head[0] + facing * round(35 * scale), head[1] + round(25 * scale))
        rear_hand = (x - facing * round(62 * scale), shoulder[1] + round(105 * scale))
    elif pose in {"type", "swipe"}:
        travel = math.sin(motion_phase) if pose == "type" else math.sin(motion_phase * 0.45)
        front_hand = (x + facing * round((72 + 20 * travel) * scale), shoulder[1] + round(55 * scale))
        rear_hand = (x + facing * round((28 - 12 * travel) * scale), shoulder[1] + round(68 * scale))
    elif pose == "step_in":
        swing = math.sin(math.pi * step_progress)
        front_hand = (x + facing * round((46 - 10 * swing) * scale), shoulder[1] + round((96 + 10 * swing) * scale))
        rear_hand = (x - facing * round((46 + 10 * swing) * scale), shoulder[1] + round((96 - 10 * swing) * scale))
    elif pose == "walk":
        # Arms counter-swing against the stepping leg and remain below the
        # shoulders. This supplies the missing locomotion cue at small scale.
        front_hand = (x + facing * round((48 - 18 * gait) * scale), shoulder[1] + round((96 + 16 * gait) * scale))
        rear_hand = (x - facing * round((48 + 18 * gait) * scale), shoulder[1] + round((96 - 16 * gait) * scale))
    else:
        front_hand = (x + facing * round(74 * scale), shoulder[1] + round(102 * scale))
        rear_hand = (x - facing * round(72 * scale), shoulder[1] + round(102 * scale))

    front_shoulder = shoulder_right if facing > 0 else shoulder_left
    rear_shoulder = shoulder_left if facing > 0 else shoulder_right
    front_elbow = (
        round((front_shoulder[0] + front_hand[0]) / 2 + facing * 20 * scale),
        round((front_shoulder[1] + front_hand[1]) / 2 - 6 * pulse * scale),
    )
    rear_elbow = (
        round((rear_shoulder[0] + rear_hand[0]) / 2 - facing * 15 * scale),
        round((rear_shoulder[1] + rear_hand[1]) / 2 + 8 * scale),
    )
    _limb(draw, (front_shoulder, front_elbow, front_hand), body, limb_width)
    _limb(draw, (rear_shoulder, rear_elbow, rear_hand), body, limb_width)
    _hand(draw, front_hand, body, scale, hand_shape=front_shape, facing=facing)
    _hand(draw, rear_hand, body, scale, hand_shape=rear_shape, facing=-facing)

    knee_y = ground_y - round(38 * scale)
    if pose == "step_in":
        front_phase = _smooth(step_progress / 0.55)
        rear_phase = _smooth((step_progress - 0.55) / 0.45)
        front_start = step_start_x + facing * round(34 * scale)
        front_final = step_final_x + facing * round(52 * scale)
        rear_start = step_start_x - facing * round(48 * scale)
        rear_final = step_final_x - facing * round(48 * scale)
        front_x = round(front_start + (front_final - front_start) * front_phase)
        rear_x = round(rear_start + (rear_final - rear_start) * rear_phase)
        front_lift = math.sin(math.pi * front_phase) if step_progress <= 0.55 else 0.0
        rear_lift = math.sin(math.pi * rear_phase) if step_progress > 0.55 else 0.0
        front_foot = (front_x, ground_y - round(front_lift * 17 * scale))
        rear_foot = (rear_x, ground_y - round(rear_lift * 14 * scale))
        if facing > 0:
            left_foot, right_foot = rear_foot, front_foot
            left_lift, right_lift = rear_lift, front_lift
        else:
            left_foot, right_foot = front_foot, rear_foot
            left_lift, right_lift = front_lift, rear_lift
        left_knee = (x - round(23 * scale), knee_y - round(left_lift * 14 * scale))
        right_knee = (x + round(23 * scale), knee_y - round(right_lift * 14 * scale))
    else:
        locomotion_speed = 1.65 if pose == "run" else 1.0
        step = math.sin(motion_phase * locomotion_speed) if pose in {"walk", "run"} else 0.0
        left_lift = max(0.0, -step) if pose in {"walk", "run"} else 0.0
        right_lift = max(0.0, step) if pose in {"walk", "run"} else 0.0
        lift_height = 18 if pose == "walk" else 25
        left_foot = (x - round((56 + 26 * step) * scale), ground_y - round(left_lift * lift_height * scale))
        right_foot = (x + round((56 - 26 * step) * scale), ground_y - round(right_lift * lift_height * scale))
        if pose == "slump":
            left_foot = (x - round(48 * scale), ground_y)
            right_foot = (x + round(38 * scale), ground_y)
        left_knee = (x - round((23 - 13 * step) * scale), knee_y - round(left_lift * 15 * scale))
        right_knee = (x + round((23 + 13 * step) * scale), knee_y - round(right_lift * 15 * scale))
    hip_left = (hip[0] - round(18 * scale), hip[1])
    hip_right = (hip[0] + round(18 * scale), hip[1])
    _limb(draw, (hip_left, left_knee, left_foot), body, limb_width)
    _limb(draw, (hip_right, right_knee, right_foot), body, limb_width)
    _shoe(draw, left_foot, -1, body, scale)
    _shoe(draw, right_foot, 1, body, scale)

    if pose in {"phone", "tap", "type", "swipe"}:
        phone_x = x + facing * round(76 * scale)
        phone_y = shoulder[1] + round(45 * scale)
        draw.rounded_rectangle((phone_x - round(20 * scale), phone_y - round(34 * scale), phone_x + round(20 * scale), phone_y + round(34 * scale)), radius=max(4, round(7 * scale)), fill=palette["ink"], outline=palette["accent"], width=max(2, round(3 * scale)))


def render_frame(
    template_id: str,
    duration_seconds: float,
    time_seconds: float,
    style_id: str | None = None,
) -> Image.Image:
    global _CURRENT_TIME, _CURRENT_DURATION
    _CURRENT_TIME = max(0.0, float(time_seconds))
    _CURRENT_DURATION = max(1.0, float(duration_seconds))
    return _original_render_frame(template_id, duration_seconds, time_seconds, style_id)


# All existing templates resolve the person primitive dynamically. Replacing the
# primitive upgrades the entire Character Explainer family while retaining the
# proven face-safe staging and scene layouts.
staged.base._person = _expressive_person
staged.base.render_frame = render_frame

CHARACTER_TEMPLATES = clean.CHARACTER_TEMPLATES
CHARACTER_TEMPLATE_BY_ID = clean.CHARACTER_TEMPLATE_BY_ID
DEFAULT_STYLE_ID = clean.DEFAULT_STYLE_ID
STYLES = clean.STYLES
OUTPUT_WIDTH = clean.OUTPUT_WIDTH
OUTPUT_HEIGHT = clean.OUTPUT_HEIGHT
ffmpeg_encoder_command = clean.ffmpeg_encoder_command
render_character_motion = clean.render_character_motion
score_character_templates = clean.score_character_templates
storyboard_beats = clean.storyboard_beats
style_catalog = clean.style_catalog
suggest_template = clean.suggest_template
template_catalog = clean.template_catalog
