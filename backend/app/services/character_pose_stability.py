from __future__ import annotations

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


def _stable_planned_person(*args, pose: str = "idle", mood: str = "neutral", **kwargs):
    """Consume saved direction without sending unsupported poses into the rig."""
    plan = runtime._ACTIVE_PLAN
    if plan:
        progress = character._CURRENT_TIME / max(0.01, character._CURRENT_DURATION)
        poses = [str(value).lower().strip() for value in (plan.get("pose_sequence") or [])]
        expressions = [str(value) for value in (plan.get("expression_sequence") or [])]

        if poses:
            index = min(len(poses) - 1, int(max(0.0, min(0.999999, progress)) * len(poses)))
            planned_pose = poses[index]
            # Script language may contain semantic beats such as "recoil" that
            # are not yet physical rig poses. Keep the template's proven pose
            # instead of dropping into an undefined default body configuration.
            if planned_pose in SUPPORTED_POSES:
                pose = planned_pose

        if expressions:
            index = min(
                len(expressions) - 1,
                int(max(0.0, min(0.999999, progress)) * len(expressions)),
            )
            mood = runtime._mapped_expression(expressions[index])

    return runtime._ORIGINAL_PERSON(*args, pose=pose, mood=mood, **kwargs)


runtime._planned_person = _stable_planned_person
staging.base._person = _stable_planned_person
