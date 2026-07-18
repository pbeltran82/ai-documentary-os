from __future__ import annotations

"""Final direction polish for the general cartoon documentary renderer.

The core renderer deliberately stays small and reusable.  This layer improves
beat-level semantic selection, deterministic composition variety, and readable
landscape copy without changing the exact-visual API contract.
"""

import hashlib
from types import SimpleNamespace

from PIL import ImageDraw

from . import cartoon_documentary as cartoon

_ORIGINAL_SUGGEST_TEMPLATE = cartoon.suggest_template
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


def _wrap_text(value: str, max_width: int, *, size: int = 31, max_lines: int = 2) -> list[str]:
    font = cartoon._font(size, True)
    words = " ".join(str(value or "").split()).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or font.getlength(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and current:
        lines.append(current)
    consumed = " ".join(lines)
    original = " ".join(words)
    if lines and consumed != original:
        while lines[-1] and font.getlength(lines[-1] + "…") > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines[:max_lines]


def render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id=None):
    image = _ORIGINAL_RENDER_PLANNED_FRAME(
        scene,
        template_id,
        duration_seconds,
        time_seconds,
        style_id,
    )
    beat = cartoon._beat_for_time(scene, time_seconds)
    label = str((beat or {}).get("visual_intent") or getattr(scene, "visual_intent", "") or "Documentary visual")
    draw = ImageDraw.Draw(image)
    panel = (55, 42, 1290, 178)
    draw.rounded_rectangle(panel, radius=24, fill=cartoon.WHITE, outline=cartoon.INK, width=8)
    lines = _wrap_text(label, 1160, size=30, max_lines=2)
    y = 63 if len(lines) > 1 else 82
    for line in lines:
        draw.text((88, y), line, font=cartoon._font(30, True), fill=cartoon.INK)
        y += 42
    return image


cartoon.suggest_template = suggest_template
cartoon.render_planned_frame = render_planned_frame
