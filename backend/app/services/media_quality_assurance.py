from __future__ import annotations

"""Automated release QA for rendered documentary timelines.

The service inspects the actual ``first-cut.mp4`` with FFprobe/FFmpeg, compares it
with the saved render plan, and writes a durable ``qa-report.json`` next to the
render. It intentionally separates blocking release defects from editorial
warnings so creators receive a clear PASS/HOLD decision without hiding useful
quality observations.
"""

import json
import math
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException

from .media_library import MEDIA_ROOT, public_media_url
from .timeline_builder import OUTPUT_FPS, timeline_directory
from .video_format import SHORTS_FORMAT, video_format_profile

FFMPEG_NAME = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE_NAME = os.getenv("FFPROBE_BIN", "ffprobe")
QA_TIMEOUT_SECONDS = int(os.getenv("MEDIA_QA_TIMEOUT_SECONDS", "360"))
BLACK_MIN_SECONDS = float(os.getenv("MEDIA_QA_BLACK_MIN_SECONDS", "0.02"))
FREEZE_MIN_SECONDS = float(os.getenv("MEDIA_QA_FREEZE_MIN_SECONDS", "3.0"))
INTERNAL_EDGE_TOLERANCE_SECONDS = float(
    os.getenv("MEDIA_QA_EDGE_TOLERANCE_SECONDS", "0.12")
)
REPEATED_SCENE_WARNING_SIMILARITY = float(
    os.getenv("MEDIA_QA_REPEAT_WARNING_SIMILARITY", "0.985")
)
REPEATED_SCENE_FAILURE_SIMILARITY = float(
    os.getenv("MEDIA_QA_REPEAT_FAILURE_SIMILARITY", "0.995")
)

_BLACK_RE = re.compile(
    r"black_start:(?P<start>-?\d+(?:\.\d+)?)\s+"
    r"black_end:(?P<end>-?\d+(?:\.\d+)?)\s+"
    r"black_duration:(?P<duration>\d+(?:\.\d+)?)"
)
_FREEZE_START_RE = re.compile(r"freeze_start:\s*(?P<value>-?\d+(?:\.\d+)?)")
_FREEZE_DURATION_RE = re.compile(r"freeze_duration:\s*(?P<value>\d+(?:\.\d+)?)")
_FREEZE_END_RE = re.compile(r"freeze_end:\s*(?P<value>-?\d+(?:\.\d+)?)")
_MAX_VOLUME_RE = re.compile(r"max_volume:\s*(?P<value>-?inf|-?\d+(?:\.\d+)?)\s*dB")

DOCUMENTARY_TEMPLATE_IDS = {
    "transport_scene",
    "habitat_build",
    "presenter_desk",
    "council_scene",
    "crowd_focus",
    "process_diagram",
    "route_map",
}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _executable(name: str) -> str | None:
    configured = Path(name).expanduser()
    if configured.is_absolute():
        return str(configured) if configured.is_file() else None
    return shutil.which(name)


def ffmpeg_executable() -> str | None:
    return _executable(FFMPEG_NAME)


def ffprobe_executable() -> str | None:
    return _executable(FFPROBE_NAME)


def qa_report_path(project_id: int) -> Path:
    return timeline_directory(project_id) / "qa-report.json"


def _relative_media_path(path: Path) -> str:
    return path.resolve().relative_to(MEDIA_ROOT.resolve()).as_posix()


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary:
        json.dump(payload, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _run(command: list[str], *, timeout: int = QA_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Media QA exceeded the configured time limit") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not start media QA tool: {exc}") from exc
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "Media inspection failed")[-1800:]
        raise HTTPException(status_code=422, detail=f"Rendered media could not be inspected: {error}")
    return completed


def _parse_rate(value: Any) -> float:
    text = str(value or "0").strip()
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        try:
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else 0.0
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def probe_render(path: Path, executable: str | None = None) -> dict[str, Any]:
    probe = executable or ffprobe_executable()
    if probe is None:
        raise HTTPException(
            status_code=503,
            detail="FFprobe was not found. Install it with: brew install ffmpeg",
        )
    completed = _run(
        [
            probe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="FFprobe returned invalid media metadata") from exc

    streams = list(payload.get("streams") or [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_data = dict(payload.get("format") or {})
    container_duration = _safe_float(format_data.get("duration")) or 0.0
    video_duration = _safe_float((video or {}).get("duration")) or container_duration
    audio_duration = _safe_float((audio or {}).get("duration")) if audio else None
    fps = _parse_rate((video or {}).get("avg_frame_rate") or (video or {}).get("r_frame_rate"))
    frame_count = _safe_float((video or {}).get("nb_frames"))
    if frame_count is None and video_duration > 0 and fps > 0:
        frame_count = round(video_duration * fps)

    return {
        "container_duration_seconds": round(container_duration, 3),
        "video_duration_seconds": round(video_duration, 3),
        "audio_duration_seconds": round(audio_duration, 3) if audio_duration is not None else None,
        "width": int((video or {}).get("width") or 0),
        "height": int((video or {}).get("height") or 0),
        "fps": round(fps, 3),
        "frame_count": int(frame_count or 0),
        "video_codec": str((video or {}).get("codec_name") or ""),
        "pixel_format": str((video or {}).get("pix_fmt") or ""),
        "audio_codec": str((audio or {}).get("codec_name") or "") if audio else None,
        "audio_sample_rate": int((audio or {}).get("sample_rate") or 0) if audio else None,
        "has_video": video is not None,
        "has_audio": audio is not None,
        "size_bytes": path.stat().st_size,
    }


def parse_black_segments(log: str) -> list[dict[str, float]]:
    return [
        {
            "start_seconds": round(float(match.group("start")), 3),
            "end_seconds": round(float(match.group("end")), 3),
            "duration_seconds": round(float(match.group("duration")), 3),
        }
        for match in _BLACK_RE.finditer(log)
    ]


def parse_freeze_segments(log: str, media_duration: float) -> list[dict[str, float]]:
    segments: list[dict[str, float]] = []
    current_start: float | None = None
    current_duration: float | None = None
    for line in log.splitlines():
        start_match = _FREEZE_START_RE.search(line)
        if start_match:
            current_start = float(start_match.group("value"))
            current_duration = None
            continue
        duration_match = _FREEZE_DURATION_RE.search(line)
        if duration_match and current_start is not None:
            current_duration = float(duration_match.group("value"))
            continue
        end_match = _FREEZE_END_RE.search(line)
        if end_match and current_start is not None:
            end = float(end_match.group("value"))
            duration = current_duration if current_duration is not None else max(0.0, end - current_start)
            segments.append(
                {
                    "start_seconds": round(current_start, 3),
                    "end_seconds": round(end, 3),
                    "duration_seconds": round(duration, 3),
                }
            )
            current_start = None
            current_duration = None
    if current_start is not None:
        end = max(current_start, media_duration)
        duration = current_duration if current_duration is not None else max(0.0, end - current_start)
        segments.append(
            {
                "start_seconds": round(current_start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(duration, 3),
            }
        )
    return segments


def scan_video_events(path: Path, duration: float, executable: str | None = None) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    ffmpeg = executable or ffmpeg_executable()
    if ffmpeg is None:
        raise HTTPException(
            status_code=503,
            detail="FFmpeg was not found. Install it with: brew install ffmpeg",
        )
    completed = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vf",
            f"blackdetect=d={BLACK_MIN_SECONDS:g}:pix_th=0.98,freezedetect=n=-50dB:d={FREEZE_MIN_SECONDS:g}",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    return parse_black_segments(completed.stderr), parse_freeze_segments(completed.stderr, duration)


def measure_audio_peak(path: Path, executable: str | None = None) -> float | None:
    ffmpeg = executable or ffmpeg_executable()
    if ffmpeg is None:
        raise HTTPException(
            status_code=503,
            detail="FFmpeg was not found. Install it with: brew install ffmpeg",
        )
    completed = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ]
    )
    match = _MAX_VOLUME_RE.search(completed.stderr)
    if not match or match.group("value") == "-inf":
        return None
    return round(float(match.group("value")), 2)


def _frame_signature(path: Path, at_seconds: float, executable: str) -> bytes | None:
    try:
        completed = subprocess.run(
            [
                executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{max(0.0, at_seconds):.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=64:36,format=gray",
                "-pix_fmt",
                "gray",
                "-f",
                "rawvideo",
                "-",
            ],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    expected = 64 * 36
    return completed.stdout[:expected] if completed.returncode == 0 and len(completed.stdout) >= expected else None


def frame_similarity(first: bytes, second: bytes) -> float:
    if not first or len(first) != len(second):
        return 0.0
    difference = sum(abs(left - right) for left, right in zip(first, second, strict=True))
    return round(max(0.0, 1.0 - difference / (len(first) * 255)), 5)


def sample_adjacent_scenes(path: Path, clips: list[dict[str, Any]], executable: str | None = None) -> list[dict[str, Any]]:
    ffmpeg = executable or ffmpeg_executable()
    if ffmpeg is None or len(clips) < 2:
        return []
    samples: list[tuple[dict[str, Any], bytes | None]] = []
    cursor = 0.0
    for clip in clips:
        duration = max(0.05, float(clip.get("duration_seconds") or 0.05))
        midpoint = cursor + duration * 0.5
        samples.append((clip, _frame_signature(path, midpoint, ffmpeg)))
        cursor += duration

    pairs: list[dict[str, Any]] = []
    for (left_clip, left), (right_clip, right) in zip(samples, samples[1:], strict=False):
        if left is None or right is None:
            continue
        similarity = frame_similarity(left, right)
        if similarity < REPEATED_SCENE_WARNING_SIMILARITY:
            continue
        left_template = str(left_clip.get("exact_visual_template_id") or "")
        right_template = str(right_clip.get("exact_visual_template_id") or "")
        pairs.append(
            {
                "first_scene_number": int(left_clip.get("scene_number") or 0),
                "second_scene_number": int(right_clip.get("scene_number") or 0),
                "first_template_id": left_template or None,
                "second_template_id": right_template or None,
                "similarity": similarity,
                "same_documentary_template": bool(
                    left_template
                    and left_template == right_template
                    and left_template in DOCUMENTARY_TEMPLATE_IDS
                ),
            }
        )
    return pairs


def _check(
    check_id: str,
    label: str,
    status: str,
    details: str,
    *,
    severity: str = "minor",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "severity": severity,
        "details": details,
        "metrics": metrics or {},
    }


def _internal_black_segments(segments: list[dict[str, float]], duration: float) -> list[dict[str, float]]:
    return [
        segment
        for segment in segments
        if segment["start_seconds"] > INTERNAL_EDGE_TOLERANCE_SECONDS
        and segment["end_seconds"] < duration - INTERNAL_EDGE_TOLERANCE_SECONDS
    ]


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
    profile = video_format_profile(project)
    duration = float(metadata["container_duration_seconds"])
    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "media_integrity",
            "Readable video stream",
            "pass" if metadata["has_video"] and duration > 0 else "fail",
            "The rendered MP4 contains a readable video stream." if metadata["has_video"] and duration > 0 else "The render has no usable video stream.",
            severity="blocker",
        )
    )

    correct_dimensions = metadata["width"] == profile.width and metadata["height"] == profile.height
    checks.append(
        _check(
            "delivery_dimensions",
            "Delivery dimensions",
            "pass" if correct_dimensions else "fail",
            f"Rendered at {metadata['width']}×{metadata['height']}; expected {profile.width}×{profile.height} ({profile.aspect_ratio}).",
            severity="major",
            metrics={"actual_width": metadata["width"], "actual_height": metadata["height"], "expected_width": profile.width, "expected_height": profile.height},
        )
    )

    fps_delta = abs(float(metadata["fps"]) - OUTPUT_FPS)
    checks.append(
        _check(
            "frame_rate",
            "Frame-rate consistency",
            "pass" if fps_delta <= 0.05 else "fail",
            f"Rendered at {metadata['fps']:g} fps; expected {OUTPUT_FPS} fps.",
            severity="major",
            metrics={"actual_fps": metadata["fps"], "expected_fps": OUTPUT_FPS},
        )
    )

    expected_runtime = float(plan.get("runtime_seconds") or 0.0)
    runtime_delta = abs(duration - expected_runtime)
    runtime_status = "pass" if runtime_delta <= 0.10 else "warn" if runtime_delta <= 0.25 else "fail"
    checks.append(
        _check(
            "planned_runtime",
            "Planned runtime alignment",
            runtime_status,
            f"Render is {duration:.3f}s versus the {expected_runtime:.3f}s timeline plan ({runtime_delta:.3f}s difference).",
            severity="major" if runtime_status == "fail" else "minor",
            metrics={"render_seconds": duration, "planned_seconds": expected_runtime, "delta_seconds": round(runtime_delta, 3)},
        )
    )

    audio_duration = metadata.get("audio_duration_seconds")
    if plan.get("voiceover") and not metadata["has_audio"]:
        checks.append(_check("audio_stream", "Narration audio stream", "fail", "The render plan includes narration, but the exported MP4 has no audio stream.", severity="blocker"))
    elif metadata["has_audio"] and audio_duration is not None:
        av_delta = abs(float(metadata["video_duration_seconds"]) - float(audio_duration))
        av_status = "pass" if av_delta <= 0.08 else "warn" if av_delta <= 0.25 else "fail"
        checks.append(
            _check(
                "audio_video_alignment",
                "Audio/video duration alignment",
                av_status,
                f"Audio and video differ by {av_delta:.3f}s.",
                severity="major" if av_status == "fail" else "minor",
                metrics={"video_seconds": metadata["video_duration_seconds"], "audio_seconds": audio_duration, "delta_seconds": round(av_delta, 3)},
            )
        )
    else:
        checks.append(_check("audio_stream", "Narration audio stream", "pass", "This project intentionally rendered without narration audio."))

    if metadata["has_audio"]:
        if audio_peak_db is None:
            checks.append(_check("audio_peak", "Audio peak safety", "warn", "Audio exists, but its maximum peak could not be measured."))
        else:
            peak_status = "fail" if audio_peak_db >= -0.1 else "warn" if audio_peak_db > -1.0 else "pass"
            checks.append(
                _check(
                    "audio_peak",
                    "Audio peak safety",
                    peak_status,
                    f"Maximum measured audio peak is {audio_peak_db:g} dBFS.",
                    severity="major" if peak_status == "fail" else "minor",
                    metrics={"max_peak_dbfs": audio_peak_db},
                )
            )

    internal_black = _internal_black_segments(black_segments, duration)
    checks.append(
        _check(
            "internal_black_frames",
            "Internal black-frame flashes",
            "fail" if internal_black else "pass",
            f"Detected {len(internal_black)} internal black segment(s)." if internal_black else "No internal black-frame flashes were detected.",
            severity="major",
            metrics={"count": len(internal_black), "segments": internal_black},
        )
    )

    opening_black = next((segment for segment in black_segments if segment["start_seconds"] <= 0.02), None)
    if str(profile.format_id) == SHORTS_FORMAT:
        opening_status = "warn" if opening_black and opening_black["duration_seconds"] > 0.04 else "pass"
        checks.append(
            _check(
                "shorts_immediate_hook",
                "Immediate Shorts opening",
                opening_status,
                f"The Short begins with {opening_black['duration_seconds']:.3f}s of black." if opening_status == "warn" else "The designed hook is visible immediately.",
                metrics={"opening_black_seconds": opening_black["duration_seconds"] if opening_black else 0.0},
            )
        )

    long_freezes = [segment for segment in freeze_segments if segment["duration_seconds"] >= FREEZE_MIN_SECONDS]
    checks.append(
        _check(
            "extended_freezes",
            "Extended frozen holds",
            "warn" if long_freezes else "pass",
            f"Detected {len(long_freezes)} hold(s) lasting at least {FREEZE_MIN_SECONDS:g}s; review whether they are intentional." if long_freezes else "No unusually long frozen holds were detected.",
            metrics={"count": len(long_freezes), "segments": long_freezes},
        )
    )

    severe_repeats = [
        pair
        for pair in repeated_pairs
        if pair["similarity"] >= REPEATED_SCENE_FAILURE_SIMILARITY and pair["same_documentary_template"]
    ]
    repeated_status = "fail" if severe_repeats else "warn" if repeated_pairs else "pass"
    checks.append(
        _check(
            "adjacent_scene_similarity",
            "Adjacent scene uniqueness",
            repeated_status,
            f"Detected {len(repeated_pairs)} highly similar adjacent scene pair(s)." if repeated_pairs else "Adjacent scene samples are visually distinct.",
            severity="major" if severe_repeats else "minor",
            metrics={"pairs": repeated_pairs},
        )
    )

    if str(profile.format_id) == SHORTS_FORMAT:
        checks.append(
            _check(
                "shorts_runtime",
                "Shorts runtime limit",
                "pass" if duration <= 60.05 else "fail",
                f"Short runtime is {duration:.3f}s; the release limit is 60 seconds.",
                severity="blocker",
                metrics={"runtime_seconds": duration, "limit_seconds": 60.0},
            )
        )

    return checks


def load_render_plan(project_id: int) -> dict[str, Any]:
    path = timeline_directory(project_id) / "render-plan.json"
    if not path.is_file():
        raise HTTPException(status_code=409, detail="Build and render the timeline before running release QA")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="The saved timeline plan is unreadable") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="The saved timeline plan is invalid")
    return payload


def analyze_timeline_render(project: Any) -> dict[str, Any]:
    timeline_dir = timeline_directory(project.id)
    render_path = timeline_dir / "first-cut.mp4"
    if not render_path.is_file():
        raise HTTPException(status_code=409, detail="Render the timeline before running release QA")

    plan = load_render_plan(project.id)
    metadata = probe_render(render_path)
    black_segments, freeze_segments = scan_video_events(
        render_path,
        float(metadata["container_duration_seconds"]),
    )
    audio_peak = measure_audio_peak(render_path) if metadata["has_audio"] else None
    repeated_pairs = sample_adjacent_scenes(render_path, list(plan.get("clips") or []))
    checks = evaluate_quality(
        project=project,
        plan=plan,
        metadata=metadata,
        black_segments=black_segments,
        freeze_segments=freeze_segments,
        audio_peak_db=audio_peak,
        repeated_pairs=repeated_pairs,
    )

    failures = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]
    passes = [check for check in checks if check["status"] == "pass"]
    report_path = qa_report_path(project.id)
    relative_path = _relative_media_path(report_path)
    report = {
        "schema_version": "1.0",
        "generated_at": utc_iso(),
        "project_id": project.id,
        "project_title": project.title,
        "video_format": video_format_profile(project).format_id,
        "verdict": "HOLD" if failures else "PASS",
        "summary": {
            "passed": len(passes),
            "warnings": len(warnings),
            "failures": len(failures),
            "message": (
                f"HOLD: {len(failures)} release-blocking check(s) failed."
                if failures
                else f"PASS with {len(warnings)} warning(s)." if warnings else "PASS: all automated release checks succeeded."
            ),
        },
        "render": metadata,
        "checks": checks,
        "black_segments": black_segments,
        "freeze_segments": freeze_segments,
        "repeated_scene_pairs": repeated_pairs,
        "report_relative_path": relative_path,
        "report_url": public_media_url(relative_path),
    }
    _atomic_json_write(report_path, report)
    return report


def load_qa_report(project_id: int) -> dict[str, Any]:
    path = qa_report_path(project_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No media QA report exists for this project")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="The saved media QA report is unreadable") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="The saved media QA report is invalid")
    return payload
