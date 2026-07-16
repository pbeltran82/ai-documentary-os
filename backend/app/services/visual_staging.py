from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    def padded(self, value: int) -> "Rect":
        return Rect(
            self.left - value,
            self.top - value,
            self.right + value,
            self.bottom + value,
        )

    def overlaps(self, other: "Rect") -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )


@dataclass(frozen=True)
class CharacterPlacement:
    center_x: int
    ground_y: int
    scale: float
    facing: int = 1

    @property
    def face_box(self) -> Rect:
        head_radius = round(38 * self.scale)
        head_y = self.ground_y - round(245 * self.scale)
        return Rect(
            self.center_x - head_radius,
            head_y - head_radius,
            self.center_x + head_radius,
            head_y + head_radius,
        )

    @property
    def gesture_box(self) -> Rect:
        shoulder_y = self.ground_y - round(175 * self.scale)
        reach = round(100 * self.scale)
        return Rect(
            self.center_x - reach,
            shoulder_y - round(90 * self.scale),
            self.center_x + reach,
            shoulder_y + round(130 * self.scale),
        )


@dataclass(frozen=True)
class StagingPlan:
    character: CharacterPlacement
    protected_boxes: tuple[Rect, ...]

    def is_face_safe(self, padding: int = 14) -> bool:
        face = self.character.face_box.padded(padding)
        return all(not face.overlaps(box) for box in self.protected_boxes)


PLANS: dict[str, StagingPlan] = {
    "paycheck_arrival": StagingPlan(
        CharacterPlacement(340, 840, 1.10),
        (
            Rect(500, 450, 760, 610),
            Rect(930, 350, 1810, 585),
            Rect(930, 650, 1810, 900),
        ),
    ),
    "spend_first": StagingPlan(
        CharacterPlacement(255, 840, 1.06),
        (
            Rect(400, 610, 665, 760),
            Rect(850, 355, 1170, 605),
            Rect(1250, 355, 1570, 605),
            Rect(1050, 650, 1370, 900),
        ),
    ),
    "empty_balance_reaction": StagingPlan(
        CharacterPlacement(350, 840, 1.10),
        (
            Rect(850, 350, 1810, 900),
        ),
    ),
    "pay_self_character_comparison": StagingPlan(
        CharacterPlacement(345, 825, 0.98),
        (
            Rect(570, 500, 840, 790),
            Rect(1010, 350, 1835, 905),
        ),
    ),
    "automatic_investing_habit": StagingPlan(
        CharacterPlacement(245, 840, 1.06),
        (
            Rect(365, 425, 690, 500),
            Rect(430, 535, 675, 610),
            Rect(820, 350, 1815, 900),
        ),
    ),
}


def staging_plan(template_id: str) -> StagingPlan:
    return PLANS[template_id]


def face_safe_zone(template_id: str) -> tuple[int, int, int, int]:
    rect = staging_plan(template_id).character.face_box
    return rect.left, rect.top, rect.right, rect.bottom
