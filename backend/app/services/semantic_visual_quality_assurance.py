from __future__ import annotations

"""Semantic release QA for topic/template alignment and beat coverage.

Technical media checks cannot recognize that a healthy MP4 about the Internet is
showing a Mars habitat. This guard evaluates the project topic, generated exact-
visual identities, and the renderer's resolved beat sequence before granting a
PASS verdict.
"""

from typing import Any

from . import media_quality_assurance as base
from . import internet_attention_visuals as internet

_previous_evaluate_quality = base.evaluate_quality

MARS_ONLY_TEMPLATE_IDS = {
    "route_map",
    "crowd_focus",
    "presenter_desk",
    "transport_scene",
    "habitat_build",
    "council_scene",
    "process_diagram",
}
MARS_ONLY_TOKENS = ("mars", "martian", "habitat", "settlement", "colony", "spacecraft")


def _project_domain(project: Any) -> str:
    context = " ".join(
        str(getattr(project, field, ""))
        for field in ("title", "topic", "audience", "tone", "visual_style")
    ).lower()
    if any(
        signal in context
        for signal in (
            "how the internet changed human attention",
            "internet and human attention",
            "attention economy",
            "world wide web",
        )
    ):
        return "internet_attention"
    if "internet" in context and any(
        signal in context for signal in ("attention", "notification", "smartphone", "distraction", "focus")
    ):
        return "internet_attention"
    if any(signal in context for signal in ("mars", "martian", "red planet", "space settlement")):
        return "mars"
    return "unknown"


def _generated_clips(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        clip
        for clip in list(plan.get("clips") or [])
        if str(clip.get("provider") or "").lower() == "generated"
    ]


def semantic_checks(project: Any, plan: dict[str, Any]) -> list[dict[str, Any]]:
    domain = _project_domain(project)
    if domain != "internet_attention":
        return []

    generated = _generated_clips(plan)
    forbidden: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for clip in generated:
        template_id = str(clip.get("exact_visual_template_id") or "")
        source = " ".join(
            str(clip.get(key) or "")
            for key in ("source_url", "provider_asset_id", "visual_intent", "narration")
        ).lower()
        item = {
            "scene_number": int(clip.get("scene_number") or 0),
            "template_id": template_id or None,
        }
        if template_id in MARS_ONLY_TEMPLATE_IDS or any(token in source for token in MARS_ONLY_TOKENS):
            forbidden.append(item)
        elif template_id in internet.INTERNET_TEMPLATE_IDS:
            accepted.append(item)
        elif template_id:
            unknown.append(item)

    if forbidden:
        alignment_status = "fail"
        alignment_details = (
            f"Detected {len(forbidden)} generated scene(s) using Mars-authored templates "
            "inside an Internet and human-attention documentary."
        )
    elif unknown:
        alignment_status = "warn"
        alignment_details = (
            f"Detected {len(unknown)} generated scene(s) outside the dedicated Internet visual family; "
            "review their semantic relevance."
        )
    elif generated and len(accepted) == len(generated):
        alignment_status = "pass"
        alignment_details = "Every generated scene uses the topic-aware Internet and attention visual family."
    else:
        alignment_status = "warn"
        alignment_details = "No generated exact visuals were available for semantic template verification."

    checks = [
        base._check(
            "semantic_visual_alignment",
            "Topic and visual alignment",
            alignment_status,
            alignment_details,
            severity="blocker" if alignment_status == "fail" else "minor",
            metrics={
                "domain": domain,
                "accepted": accepted,
                "unknown": unknown,
                "forbidden": forbidden,
            },
        )
    ]

    scenes = sorted(list(getattr(project, "scenes", None) or []), key=lambda item: int(getattr(item, "scene_number", 0)))
    weak_scenes: list[dict[str, Any]] = []
    covered_scenes: list[dict[str, Any]] = []
    all_templates: list[str] = []
    for scene in scenes:
        duration = float(getattr(scene, "duration_seconds", 0.0) or 0.0)
        beats = list(dict(getattr(scene, "animation_plan", None) or {}).get("visual_beats") or [])
        if duration < 12.0 or len(beats) < 2:
            continue
        sequence = internet.beat_template_sequence(scene)
        unique_count = len(set(sequence))
        all_templates.extend(sequence)
        target = min(4, len(beats))
        item = {
            "scene_number": int(getattr(scene, "scene_number", 0) or 0),
            "duration_seconds": round(duration, 3),
            "visual_beat_count": len(beats),
            "resolved_template_count": unique_count,
            "resolved_templates": sequence,
            "target_unique_templates": target,
        }
        if unique_count < min(3, target):
            weak_scenes.append(item)
        else:
            covered_scenes.append(item)

    if weak_scenes:
        beat_status = "fail"
        beat_details = f"{len(weak_scenes)} long scene(s) do not resolve into enough distinct visual compositions."
    elif covered_scenes:
        beat_status = "pass"
        beat_details = f"All {len(covered_scenes)} long scene(s) use multiple beat-level compositions."
    else:
        beat_status = "warn"
        beat_details = "No long scenes with planned visual beats were available for coverage verification."

    checks.append(
        base._check(
            "semantic_visual_beat_coverage",
            "Beat-level visual coverage",
            beat_status,
            beat_details,
            severity="major" if beat_status == "fail" else "minor",
            metrics={"covered_scenes": covered_scenes, "weak_scenes": weak_scenes},
        )
    )

    unique_templates = set(all_templates)
    if all_templates and len(unique_templates) < 5:
        diversity_status = "fail"
        diversity_details = (
            f"The documentary resolves to only {len(unique_templates)} distinct beat-level visual templates."
        )
    elif all_templates:
        diversity_status = "pass"
        diversity_details = (
            f"The documentary uses {len(unique_templates)} distinct beat-level visual templates across its story."
        )
    else:
        diversity_status = "warn"
        diversity_details = "Template diversity could not be evaluated without resolved visual beats."

    checks.append(
        base._check(
            "semantic_template_diversity",
            "Story-wide template diversity",
            diversity_status,
            diversity_details,
            severity="major" if diversity_status == "fail" else "minor",
            metrics={
                "unique_template_count": len(unique_templates),
                "templates": sorted(unique_templates),
            },
        )
    )
    return checks


def evaluate_quality(
    *,
    project: Any,
    plan: dict[str, Any],
    metadata: dict[str, Any],
    black_segments: list[dict[str, float]],
    freeze_segments: list[dict[str, float]],
    audio_peak_db: float | None,
    repeated_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks = _previous_evaluate_quality(
        project=project,
        plan=plan,
        metadata=metadata,
        black_segments=black_segments,
        freeze_segments=freeze_segments,
        audio_peak_db=audio_peak_db,
        repeated_pairs=repeated_pairs,
    )
    checks.extend(semantic_checks(project, plan))
    return checks


base.evaluate_quality = evaluate_quality
