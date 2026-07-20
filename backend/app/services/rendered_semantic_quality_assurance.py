from __future__ import annotations

"""Output-based semantic QA for delivered documentary frames.

Plan metadata can claim that a scene contains several visual beats while the MP4
still holds one composition.  This release guard samples the actual first-cut
frames, clusters their visual signatures, checks the final scene changes into its
conclusion, and explicitly inspects scene-boundary frames for one-frame black
flashes that broad blackdetect settings can miss.
"""

from pathlib import Path
from typing import Any

from . import internet_attention_delivery_v2 as delivery
from . import internet_attention_visuals as internet
from . import media_quality_assurance as qa
from . import semantic_visual_quality_assurance as semantic  # noqa: F401
from .timeline_builder import OUTPUT_FPS, timeline_directory

_previous_evaluate_quality = qa.evaluate_quality
SIGNATURE_SIMILARITY = 0.975
BLACK_PIXEL_VALUE = 10
BLACK_PICTURE_RATIO = 0.98


def is_black_signature(signature: bytes | None) -> bool:
    if not signature:
        return False
    dark = sum(value <= BLACK_PIXEL_VALUE for value in signature)
    return dark / len(signature) >= BLACK_PICTURE_RATIO


def signature_cluster_count(
    signatures: list[bytes],
    *,
    threshold: float = SIGNATURE_SIMILARITY,
) -> int:
    """Greedily count materially different rendered compositions."""
    representatives: list[bytes] = []
    for signature in signatures:
        if not representatives or all(
            qa.frame_similarity(signature, existing) < threshold
            for existing in representatives
        ):
            representatives.append(signature)
    return len(representatives)


def _is_internet_project(project: Any) -> bool:
    return semantic._project_domain(project) == "internet_attention"


def _clip_windows(clips: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float, float]]:
    cursor = 0.0
    windows: list[tuple[dict[str, Any], float, float]] = []
    for clip in clips:
        duration = max(0.0, float(clip.get("duration_seconds") or 0.0))
        windows.append((clip, cursor, cursor + duration))
        cursor += duration
    return windows


def sample_rendered_scene_compositions(
    path: Path,
    clips: list[dict[str, Any]],
    *,
    executable: str | None = None,
) -> list[dict[str, Any]]:
    ffmpeg = executable or qa.ffmpeg_executable()
    if ffmpeg is None:
        return []
    results: list[dict[str, Any]] = []
    for clip, start, end in _clip_windows(clips):
        duration = end - start
        if duration < 20.0 or str(clip.get("provider") or "").lower() != "generated":
            continue
        sample_count = max(4, min(6, round(duration / 7.0)))
        fractions = [(index + 0.5) / sample_count for index in range(sample_count)]
        signatures = [
            qa._frame_signature(path, start + duration * fraction, ffmpeg)
            for fraction in fractions
        ]
        resolved = [signature for signature in signatures if signature is not None]
        results.append(
            {
                "scene_number": int(clip.get("scene_number") or 0),
                "duration_seconds": round(duration, 3),
                "sample_count": len(resolved),
                "unique_rendered_compositions": signature_cluster_count(resolved),
                "sample_seconds": [round(start + duration * fraction, 3) for fraction in fractions],
            }
        )
    return results


def sample_boundary_black_frames(
    path: Path,
    clips: list[dict[str, Any]],
    *,
    executable: str | None = None,
) -> list[dict[str, Any]]:
    ffmpeg = executable or qa.ffmpeg_executable()
    if ffmpeg is None or len(clips) < 2:
        return []
    frame = 1.0 / max(1, OUTPUT_FPS)
    failures: list[dict[str, Any]] = []
    cursor = 0.0
    for index, clip in enumerate(clips[:-1]):
        cursor += max(0.0, float(clip.get("duration_seconds") or 0.0))
        samples = (cursor - frame, cursor, cursor + frame)
        dark_samples: list[float] = []
        for at_seconds in samples:
            signature = qa._frame_signature(path, max(0.0, at_seconds), ffmpeg)
            if is_black_signature(signature):
                dark_samples.append(round(max(0.0, at_seconds), 3))
        if dark_samples:
            failures.append(
                {
                    "after_scene_number": int(clip.get("scene_number") or index + 1),
                    "boundary_seconds": round(cursor, 3),
                    "black_sample_seconds": dark_samples,
                }
            )
    return failures


def _rendered_checks(project: Any, plan: dict[str, Any]) -> list[dict[str, Any]]:
    if not _is_internet_project(project):
        return []
    path = timeline_directory(project.id) / "first-cut.mp4"
    if not path.is_file():
        return []
    clips = list(plan.get("clips") or [])

    scene_results = sample_rendered_scene_compositions(path, clips)
    weak = [
        item
        for item in scene_results
        if item["sample_count"] >= 4 and item["unique_rendered_compositions"] < 3
    ]
    if weak:
        coverage_status = "fail"
        coverage_details = (
            f"{len(weak)} long generated scene(s) still hold fewer than three "
            "materially different compositions in the rendered MP4."
        )
    elif scene_results:
        coverage_status = "pass"
        coverage_details = (
            f"All {len(scene_results)} long generated scene(s) show multiple "
            "composition changes in delivered frames."
        )
    else:
        coverage_status = "warn"
        coverage_details = "No long generated scenes were available for rendered-frame sampling."

    checks = [
        qa._check(
            "rendered_visual_beat_coverage",
            "Rendered beat-level composition changes",
            coverage_status,
            coverage_details,
            severity="major" if coverage_status == "fail" else "minor",
            metrics={"scenes": scene_results, "weak_scenes": weak},
        )
    ]

    boundary_failures = sample_boundary_black_frames(path, clips)
    checks.append(
        qa._check(
            "rendered_boundary_frames",
            "Rendered scene-boundary frames",
            "fail" if boundary_failures else "pass",
            (
                f"Detected black output at {len(boundary_failures)} scene boundary/boundaries."
                if boundary_failures
                else "Every sampled scene boundary contains authored imagery with no one-frame black flash."
            ),
            severity="major",
            metrics={"boundaries_with_black": boundary_failures},
        )
    )

    scenes = sorted(
        list(getattr(project, "scenes", None) or []),
        key=lambda scene: int(getattr(scene, "scene_number", 0) or 0),
    )
    final_scene = scenes[-1] if scenes else None
    final_sequence = delivery.beat_template_sequence(final_scene) if final_scene is not None else []
    final_clip_result = next(
        (
            item
            for item in reversed(scene_results)
            if item["scene_number"] == int(getattr(final_scene, "scene_number", 0) or 0)
        ),
        None,
    )
    final_changes = bool(
        final_clip_result
        and final_clip_result["unique_rendered_compositions"] >= 2
    )
    final_planned = bool(final_sequence and final_sequence[-1] == "internet_attention_choice")
    conclusion_status = "pass" if final_changes and final_planned else "fail"
    checks.append(
        qa._check(
            "rendered_conclusion_resolution",
            "Rendered conclusion resolution",
            conclusion_status,
            (
                "The final scene changes composition and resolves on the dedicated attention-choice conclusion."
                if conclusion_status == "pass"
                else "The delivered ending does not prove a visual change into the attention-choice conclusion."
            ),
            severity="major",
            metrics={
                "planned_sequence": final_sequence,
                "final_scene_rendered_samples": final_clip_result,
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
    checks.extend(_rendered_checks(project, plan))
    return checks


qa.evaluate_quality = evaluate_quality
