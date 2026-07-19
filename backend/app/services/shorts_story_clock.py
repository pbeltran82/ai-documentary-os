from __future__ import annotations

"""Independent 40-60 second Shorts narration and timeline contract."""

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from . import master_narration as master
from . import narration_synthesis as synthesis
from . import timeline_builder as timeline
from . import timeline_playback_polish as playback
from .script_audio_pipeline import load_narration_plan
from .video_format import SHORTS_FORMAT, project_video_format

_SHORTS_MAX_RUNTIME_SECONDS = 60.0
_original_synthesis_retime = synthesis._retime_project_scenes
_original_master_retime = master._retime_scenes_from_manifest
_previous_build_timeline_plan = timeline.build_timeline_plan


def _shorts_manifest(project) -> dict[str, Any] | None:
    if project_video_format(project) != SHORTS_FORMAT:
        return None
    manifest = load_narration_plan(project.id)
    if not manifest or manifest.get("story_mode") != "shorts":
        return None
    return manifest


def _selected_numbers(manifest: dict[str, Any]) -> list[int]:
    numbers = [int(value) for value in manifest.get("selected_scene_numbers", []) if int(value) > 0]
    if numbers:
        return numbers[:7]
    return [
        int(item.get("scene_number", 0))
        for item in manifest.get("segments", [])
        if int(item.get("scene_number", 0)) > 0
    ][:7]


def _mark_selection(project, selected: set[int]) -> None:
    for scene in project.scenes:
        plan = dict(scene.animation_plan or {})
        plan["shorts_selected"] = scene.scene_number in selected
        plan["shorts_story_order"] = (
            sorted(selected).index(scene.scene_number) + 1
            if scene.scene_number in selected
            else None
        )
        scene.animation_plan = plan


def _retime_selected_scenes(project, manifest: dict[str, Any], db, *, require_complete: bool) -> bool:
    selected_order = _selected_numbers(manifest)
    selected = set(selected_order)
    _mark_selection(project, selected)
    by_number = {
        int(item.get("scene_number", 0)): item
        for item in manifest.get("segments", [])
        if (not require_complete or item.get("status") == "complete")
        and item.get("actual_duration_seconds")
    }
    cursor = 0.0
    changed = False
    scenes = {scene.scene_number: scene for scene in project.scenes}
    for number in selected_order:
        scene = scenes.get(number)
        segment = by_number.get(number)
        if scene is None:
            continue
        if segment is None:
            if require_complete:
                raise HTTPException(status_code=409, detail=f"Completed Shorts narration is missing for Scene {number}")
            continue
        duration = max(0.25, round(float(segment["actual_duration_seconds"]), 3))
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        if (
            float(scene.start_seconds) != start
            or float(scene.end_seconds) != end
            or float(scene.duration_seconds) != duration
        ):
            scene.start_seconds = start
            scene.end_seconds = end
            scene.duration_seconds = duration
            changed = True
        cursor = end
    if cursor > _SHORTS_MAX_RUNTIME_SECONDS + 0.01:
        raise HTTPException(
            status_code=422,
            detail=f"Shorts narration is {cursor:.1f}s; regenerate the narration plan to stay at or below 60 seconds.",
        )
    db.commit()
    return changed


def _synthesis_retime(project, manifest: dict[str, Any], db) -> None:
    if _shorts_manifest(project) is None or manifest.get("story_mode") != "shorts":
        return _original_synthesis_retime(project, manifest, db)
    _retime_selected_scenes(project, manifest, db, require_complete=False)
    project.status = "narrated"
    db.commit()


def _master_retime(project, manifest: dict[str, Any], db) -> bool:
    if _shorts_manifest(project) is None or manifest.get("story_mode") != "shorts":
        return _original_master_retime(project, manifest, db)
    return _retime_selected_scenes(project, manifest, db, require_complete=True)


def _selected_project_scenes(project, manifest: dict[str, Any]) -> list[Any]:
    order = _selected_numbers(manifest)
    by_number = {scene.scene_number: scene for scene in project.scenes}
    return [by_number[number] for number in order if number in by_number]


def _rebuild_short_plan(project, plan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    selected_scenes = _selected_project_scenes(project, manifest)
    selected_numbers = {scene.scene_number for scene in selected_scenes}
    clips = [dict(clip) for clip in plan.get("clips", []) if int(clip.get("scene_number", 0)) in selected_numbers]
    missing = [item for item in plan.get("missing_scenes", []) if int(item.get("scene_number", 0)) in selected_numbers]

    cursor = 0.0
    scene_by_number = {scene.scene_number: scene for scene in selected_scenes}
    for index, clip in enumerate(clips):
        scene = scene_by_number[int(clip["scene_number"])]
        duration = round(float(scene.duration_seconds), 3)
        clip["input_index"] = index
        clip["start_seconds"] = round(cursor, 3)
        clip["end_seconds"] = round(cursor + duration, 3)
        clip["duration_seconds"] = duration
        clip["source_scene_duration_seconds"] = duration
        clip["duration_extension_seconds"] = 0.0
        clip["processed_duration_seconds"] = duration
        cursor += duration

    timeline.apply_edit_decisions(clips, plan["settings"])
    runtime = round(sum(float(clip["duration_seconds"]) for clip in clips), 3)
    if runtime > _SHORTS_MAX_RUNTIME_SECONDS + 0.01:
        raise HTTPException(status_code=422, detail=f"Shorts timeline is {runtime:.1f}s and exceeds the 60-second contract")

    timeline_dir = timeline.timeline_directory(project.id)
    caption_path = timeline_dir / "captions.srt"
    caption_count = timeline.write_caption_track(selected_scenes, caption_path)
    output_path = timeline_dir / "first-cut.mp4"
    executable = timeline.ffmpeg_executable()
    voiceover = plan.get("voiceover")
    alignment_status, delta, message = timeline.narration_alignment(voiceover, runtime)
    command = (
        timeline.build_ffmpeg_command(
            clips,
            output_path,
            executable,
            voiceover=voiceover,
            runtime_seconds=runtime,
            style=plan["settings"],
        )
        if clips and not missing
        else []
    )

    plan.update(
        {
            "ready": bool(clips) and not missing,
            "runtime_seconds": runtime,
            "clip_count": len(clips),
            "missing_scenes": missing,
            "clips": clips,
            "command": command,
            "alignment_status": alignment_status,
            "duration_delta_seconds": delta,
            "alignment_message": message,
            "shorts_story_clock": {
                "enabled": True,
                "selected_scene_numbers": _selected_numbers(manifest),
                "target_runtime_seconds": manifest.get("target_runtime_seconds"),
                "actual_runtime_seconds": runtime,
                "maximum_runtime_seconds": _SHORTS_MAX_RUNTIME_SECONDS,
            },
            "captions": {
                **dict(plan.get("captions") or {}),
                "cue_count": caption_count,
                "exists": caption_count > 0 and caption_path.is_file(),
            },
        }
    )
    return plan


def build_timeline_plan(project, style=None) -> dict[str, Any]:
    plan = _previous_build_timeline_plan(project, style)
    manifest = _shorts_manifest(project)
    if manifest is None:
        return plan
    return _rebuild_short_plan(project, plan, manifest)


synthesis._retime_project_scenes = _synthesis_retime
master._retime_scenes_from_manifest = _master_retime
timeline.build_timeline_plan = build_timeline_plan
playback.build_timeline_plan = build_timeline_plan
