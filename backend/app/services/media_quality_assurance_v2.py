from __future__ import annotations

"""Release QA v2: accurate black detection and a universal frame-one check.

The first QA foundation used ``pix_th=0.98`` as though it were the percentage of
black pixels required. In FFmpeg that option is the luminance threshold, which
can incorrectly classify dark documentary artwork as black. This release guard
uses a conventional dark-pixel threshold and a separate 98% picture threshold.
It also evaluates the opening of both YouTube and Shorts exports.
"""

from typing import Any

from . import media_quality_assurance as base

_original_evaluate_quality = base.evaluate_quality


def scan_video_events(
    path,
    duration: float,
    executable: str | None = None,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    ffmpeg = executable or base.ffmpeg_executable()
    if ffmpeg is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="FFmpeg was not found. Install it with: brew install ffmpeg",
        )
    completed = base._run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vf",
            (
                f"blackdetect=d={base.BLACK_MIN_SECONDS:g}:"
                "pix_th=0.10:pic_th=0.98,"
                f"freezedetect=n=-50dB:d={base.FREEZE_MIN_SECONDS:g}"
            ),
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    return (
        base.parse_black_segments(completed.stderr),
        base.parse_freeze_segments(completed.stderr, duration),
    )


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
    checks = _original_evaluate_quality(
        project=project,
        plan=plan,
        metadata=metadata,
        black_segments=black_segments,
        freeze_segments=freeze_segments,
        audio_peak_db=audio_peak_db,
        repeated_pairs=repeated_pairs,
    )
    # Replace the first version's Shorts-only opening check with one release
    # contract for every delivery format.
    checks = [check for check in checks if check["id"] != "shorts_immediate_hook"]
    opening_black = next(
        (segment for segment in black_segments if segment["start_seconds"] <= 0.02),
        None,
    )
    opening_seconds = float(opening_black["duration_seconds"]) if opening_black else 0.0
    status = "fail" if opening_seconds > 0.25 else "warn" if opening_seconds > 0.04 else "pass"
    format_id = str(base.video_format_profile(project).format_id)
    designed_frame = "hook" if format_id == base.SHORTS_FORMAT else "opening artwork"
    details = (
        f"The export begins with {opening_seconds:.3f}s of black before the {designed_frame}."
        if status != "pass"
        else f"The designed {designed_frame} is visible immediately."
    )
    opening_check = base._check(
        "immediate_opening",
        "Immediate opening frame",
        status,
        details,
        severity="major" if status == "fail" else "minor",
        metrics={"opening_black_seconds": round(opening_seconds, 3)},
    )

    insert_at = next(
        (
            index + 1
            for index, check in enumerate(checks)
            if check["id"] == "internal_black_frames"
        ),
        len(checks),
    )
    checks.insert(insert_at, opening_check)
    return checks


# Install the corrected primitives inside the original analyzer so every caller,
# including the Timeline API, receives v2 behavior without duplicating report IO.
base.scan_video_events = scan_video_events
base.evaluate_quality = evaluate_quality

analyze_timeline_render = base.analyze_timeline_render
load_qa_report = base.load_qa_report
qa_report_path = base.qa_report_path
