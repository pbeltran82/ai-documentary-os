from __future__ import annotations

"""Art-direction polish for the general cartoon documentary renderer.

This layer keeps the small reusable core while improving semantic selection,
character anatomy, crowd variety, and final-frame presentation.
"""

import hashlib
import math

from PIL import ImageDraw

from . import cartoon_documentary as cartoon

_ORIGINAL_RENDER_PLANNED_FRAME = cartoon.render_planned_frame

PHRASE_WEIGHTS: dict[str, dict[str, int]] = {
    "route_map": {
        "earth": 5, "mars": 7, "planet": 5, "journey": 5, "route": 7,
        "from earth to mars": 12, "off-planet": 7, "orbit": 6,
    },
    "crowd_focus": {
        "crowd": 8, "families": 7, "people": 4, "survivors": 8,
        "community": 6, "stranded": 7, "human consequence": 8,
    },
    "presenter_desk": {
        "researcher": 8, "scientist": 8, "report": 6, "records": 6,
        "evidence": 7, "observer": 6, "archivist": 8, "interview": 7,
    },
    "transport_scene": {
        "evacuation": 10, "boarding": 9, "transport": 9, "relocation": 8,
        "launch": 7, "spacecraft": 8, "moving people": 8, "exodus": 8,
    },
    "habitat_build": {
        "habitat": 10, "colony": 8, "construction": 8, "build": 6,
        "life support": 10, "drones": 7, "robotic fleets": 8,
        "infrastructure": 8, "greenhouse": 7,
    },
    "council_scene": {
        "governance": 10, "council": 10, "law": 8, "ethics": 8,
        "accountability": 8, "authority": 7, "consent": 8, "choice": 5,
    },
    "process_diagram": {
        "system": 5, "process": 6, "tradeoff": 8, "supply": 6,
        "risk": 5, "flow": 6, "cause": 5, "effect": 5, "comparison": 6,
    },
}


def _context(scene, extra_context: str = "") -> str:
    return " ".join(
        [
            str(getattr(scene, "narration", "")),
            str(getattr(scene, "visual_intent", "")),
            *list(getattr(scene, "search_keywords", []) or []),
            str(extra_context or ""),
        ]
    ).lower()


def _weighted_scores(scene, extra_context: str = "") -> list[tuple[int, str]]:
    whole = _context(scene)
    beat = str(extra_context or "").lower()
    scores: list[tuple[int, str]] = []
    for template in cartoon.TEMPLATES:
        score = 0
        for phrase, weight in PHRASE_WEIGHTS.get(template.template_id, {}).items():
            if phrase in whole:
                score += weight
            if phrase in beat:
                score += weight * 3
        score += 2 * len(cartoon._words(beat) & set(template.keywords))
        score += len(cartoon._words(whole) & set(template.keywords))
        scores.append((score, template.template_id))
    return scores


def suggest_template(scene, extra_context: str = ""):
    scores = _weighted_scores(scene, extra_context)
    best_score = max(score for score, _template_id in scores)
    candidates = sorted(template_id for score, template_id in scores if score == best_score)
    if best_score <= 0:
        digest = hashlib.sha256(
            f"{getattr(scene, 'scene_number', 1)}|{extra_context}|{getattr(scene, 'visual_intent', '')}".encode("utf-8")
        ).digest()
        selected_id = cartoon.TEMPLATES[digest[0] % len(cartoon.TEMPLATES)].template_id
    else:
        digest = hashlib.sha256(str(extra_context or getattr(scene, "visual_intent", "")).encode("utf-8")).digest()
        selected_id = candidates[digest[0] % len(candidates)]
    template = cartoon.TEMPLATE_BY_ID[selected_id]
    confidence = min(0.98, 0.58 + max(0, best_score) * 0.018)
    return template, round(confidence, 2), f"Matched {max(0, best_score)} weighted cartoon documentary signals."


def _limb(draw: ImageDraw.ImageDraw, points: tuple[tuple[int, int], ...], width: int, fill) -> None:
    draw.line(points, fill=cartoon.INK, width=width + 6, joint="curve")
    draw.line(points, fill=fill, width=width, joint="curve")


def _person(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float = 1.0,
    *,
    accent=None,
    pose: str = "stand",
) -> None:
    line = max(4, round(8 * scale))
    fill = accent or cartoon.MUTED
    clothing = fill if accent else cartoon.DARK_MUTED
    head_r = round(36 * scale)
    neck = round(10 * scale)
    torso_w = round(68 * scale)
    torso_h = round(84 * scale)

    # Head, hair silhouette, eyes, and expression.
    draw.ellipse((x-head_r, y-head_r, x+head_r, y+head_r), fill=fill, outline=cartoon.INK, width=line)
    if accent:
        draw.arc((x-head_r+3, y-head_r+2, x+head_r-3, y+head_r-8), 190, 350, fill=cartoon.INK, width=max(5, line))
    eye_y = y - round(4 * scale)
    eye_dx = round(12 * scale)
    eye_r = max(2, round(4 * scale))
    draw.ellipse((x-eye_dx-eye_r, eye_y-eye_r, x-eye_dx+eye_r, eye_y+eye_r), fill=cartoon.INK)
    draw.ellipse((x+eye_dx-eye_r, eye_y-eye_r, x+eye_dx+eye_r, eye_y+eye_r), fill=cartoon.INK)
    if pose == "carry":
        draw.arc((x-round(14*scale), y+round(3*scale), x+round(14*scale), y+round(18*scale)), 190, 350, fill=cartoon.INK, width=max(2, round(3*scale)))
    else:
        draw.arc((x-round(14*scale), y+round(2*scale), x+round(14*scale), y+round(22*scale)), 8, 172, fill=cartoon.INK, width=max(2, round(3*scale)))

    top = y + head_r + neck
    # Rounded tapered torso.
    draw.rounded_rectangle(
        (x-torso_w//2, top, x+torso_w//2, top+torso_h),
        radius=round(22 * scale),
        fill=clothing,
        outline=cartoon.INK,
        width=line,
    )
    shoulder_y = top + round(22 * scale)
    elbow_y = shoulder_y + round(32 * scale)
    hip_y = top + torso_h

    if pose == "point":
        _limb(draw, ((x-torso_w//2, shoulder_y), (x-round(65*scale), elbow_y-round(18*scale)), (x-round(103*scale), y-round(8*scale))), max(5, round(11*scale)), fill)
        _limb(draw, ((x+torso_w//2, shoulder_y), (x+round(55*scale), elbow_y), (x+round(44*scale), top+round(70*scale))), max(5, round(11*scale)), fill)
    elif pose == "carry":
        _limb(draw, ((x-torso_w//2, shoulder_y), (x-round(55*scale), elbow_y), (x-round(18*scale), top+round(72*scale))), max(5, round(11*scale)), fill)
        _limb(draw, ((x+torso_w//2, shoulder_y), (x+round(55*scale), elbow_y), (x+round(18*scale), top+round(72*scale))), max(5, round(11*scale)), fill)
        draw.rounded_rectangle((x-round(42*scale), top+round(62*scale), x+round(42*scale), top+round(112*scale)), radius=round(8*scale), fill=cartoon.AMBER, outline=cartoon.INK, width=line)
    else:
        sway = round(8 * scale * math.sin((x + y) * 0.03))
        _limb(draw, ((x-torso_w//2, shoulder_y), (x-round(53*scale), elbow_y), (x-round(48*scale)+sway, top+round(78*scale))), max(5, round(11*scale)), fill)
        _limb(draw, ((x+torso_w//2, shoulder_y), (x+round(53*scale), elbow_y), (x+round(48*scale)+sway, top+round(78*scale))), max(5, round(11*scale)), fill)

    # Bent legs and shoes create a less rigid silhouette.
    knee_y = hip_y + round(35 * scale)
    foot_y = hip_y + round(72 * scale)
    _limb(draw, ((x-round(20*scale), hip_y), (x-round(28*scale), knee_y), (x-round(34*scale), foot_y)), max(6, round(13*scale)), clothing)
    _limb(draw, ((x+round(20*scale), hip_y), (x+round(28*scale), knee_y), (x+round(36*scale), foot_y)), max(6, round(13*scale)), clothing)
    shoe_w = round(28 * scale)
    shoe_h = round(12 * scale)
    draw.rounded_rectangle((x-round(48*scale), foot_y-shoe_h, x-round(48*scale)+shoe_w, foot_y+shoe_h), radius=shoe_h, fill=cartoon.INK)
    draw.rounded_rectangle((x+round(20*scale), foot_y-shoe_h, x+round(20*scale)+shoe_w, foot_y+shoe_h), radius=shoe_h, fill=cartoon.INK)


def _crowd(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float, focal: bool = True) -> None:
    rows = 4
    poses = ("stand", "carry", "stand", "point")
    accents = (cartoon.PURPLE, cartoon.BLUE, cartoon.AMBER)
    for row in range(rows):
        count = 7 + row * 2
        base_y = round(height * (0.43 + row * 0.135))
        for index in range(count):
            spacing = width / count
            jitter = ((index * 37 + row * 53) % 31) - 15
            x = round((index + 0.5) * spacing + jitter)
            scale = 0.68 + row * 0.105 + ((index + row) % 3) * 0.025
            is_focal = focal and row == 1 and index == count // 2
            accent = accents[(index + row) % len(accents)] if is_focal else None
            y = base_y - (round(38 * cartoon._ease(progress)) if is_focal else 0)
            pose = poses[(index + row * 2) % len(poses)] if is_focal else "stand"
            _person(draw, x, y, scale, accent=accent, pose=pose)


def render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id=None):
    image = _ORIGINAL_RENDER_PLANNED_FRAME(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )
    # The core renderer historically added the raw visual-intent sentence as a
    # storyboard note. Finished documentary frames should communicate through the
    # drawing, so cover that annotation with a clean editorial header field.
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, cartoon.OUTPUT_WIDTH, 205), fill=cartoon.PAPER)
    draw.line((72, 184, cartoon.OUTPUT_WIDTH - 72, 184), fill=(222, 222, 216), width=3)
    return image


cartoon.suggest_template = suggest_template
cartoon._person = _person
cartoon._crowd = _crowd
cartoon.render_planned_frame = render_planned_frame
