from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models import Project
from .script_audio_pipeline import (
    ACT_BLUEPRINTS,
    WORDS_PER_SECOND,
    _production_directory,
    _stable_id,
    _write_json,
    utc_iso,
)


class ScriptGenerationError(RuntimeError):
    pass


SCRIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "thesis", "segments"],
    "properties": {
        "title": {"type": "string"},
        "thesis": {"type": "string"},
        "segments": {
            "type": "array",
            "minItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["act", "narration", "visual_intent", "search_keywords"],
                "properties": {
                    "act": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual_intent": {"type": "string"},
                    "search_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 8,
                    },
                },
            },
        },
    },
}


def _response_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    raise ScriptGenerationError("The script provider returned no structured text output")


def _normalize_keywords(values: Any, topic: str, act: str) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    raw_values = values if isinstance(values, list) else []
    for value in [*raw_values, topic, act]:
        keyword = " ".join(str(value).lower().split()).strip()
        if keyword and keyword not in seen:
            cleaned.append(keyword)
            seen.add(keyword)
        if len(cleaned) >= 8:
            break
    return cleaned


def normalize_generated_script(
    project: Project,
    generated: dict[str, Any],
    *,
    provider: str,
    model: str,
    angle: str,
    research_notes: str,
    target_scene_seconds: float,
    previous_revision: int = 0,
) -> dict[str, Any]:
    raw_segments = generated.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ScriptGenerationError("The script provider returned no documentary segments")

    segments: list[dict[str, Any]] = []
    cursor = 0.0
    for index, raw in enumerate(raw_segments, start=1):
        if not isinstance(raw, dict):
            continue
        narration = " ".join(str(raw.get("narration") or "").split()).strip()
        if not narration:
            continue
        act = " ".join(str(raw.get("act") or "Story").split()).strip() or "Story"
        visual_intent = " ".join(str(raw.get("visual_intent") or "").split()).strip()
        if not visual_intent:
            visual_intent = f"Create a clear {project.visual_style.lower()} visual that advances the {act.lower()} beat."
        duration = round(max(3.0, len(narration.split()) / WORDS_PER_SECOND), 2)
        # Keep provider output honest while preventing a single paragraph from
        # swallowing a large part of the timeline.
        duration = min(duration, max(45.0, target_scene_seconds * 3.0))
        segment_id = _stable_id(f"{project.id}:{index}:{narration}")
        segments.append(
            {
                "segment_id": segment_id,
                "scene_number": index,
                "act": act,
                "narration": narration,
                "visual_intent": visual_intent,
                "search_keywords": _normalize_keywords(
                    raw.get("search_keywords"), project.topic, act
                ),
                "estimated_duration_seconds": duration,
                "start_seconds": round(cursor, 2),
                "end_seconds": round(cursor + duration, 2),
                "status": "draft",
            }
        )
        cursor += duration

    if len(segments) < 3:
        raise ScriptGenerationError("The script provider returned too few usable segments")

    payload: dict[str, Any] = {
        "schema_version": "1.1",
        "project_id": project.id,
        "project_title": project.title,
        "title": str(generated.get("title") or project.title).strip(),
        "topic": project.topic,
        "thesis": str(generated.get("thesis") or angle or project.topic).strip(),
        "target_minutes": project.target_minutes,
        "audience": project.audience,
        "tone": project.tone,
        "visual_style": project.visual_style,
        "provider": provider,
        "model": model,
        "status": "draft",
        "angle": angle.strip(),
        "research_notes": research_notes.strip(),
        "generated_at": utc_iso(),
        "updated_at": utc_iso(),
        "revision": max(1, previous_revision + 1),
        "estimated_runtime_seconds": round(cursor, 2),
        "word_count": sum(len(item["narration"].split()) for item in segments),
        "segments": segments,
    }
    _write_json(_production_directory(project.id) / "script.json", payload)
    return payload


def generate_openai_script(
    project: Project,
    *,
    angle: str = "",
    research_notes: str = "",
    target_scene_seconds: float = 8.0,
    previous_revision: int = 0,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ScriptGenerationError("OPENAI_API_KEY is not configured")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_SCRIPT_MODEL", "gpt-5-mini")
    target_words = max(180, round(project.target_minutes * 145))
    act_names = ", ".join(name for name, _ in ACT_BLUEPRINTS)
    instructions = (
        "You are the documentary writer for AI Documentary OS. Write factual, cinematic, "
        "plain-language narration with a strong causal arc. Do not invent citations, quotes, "
        "statistics, named studies, or precise claims that are not supplied in the research notes. "
        "Use uncertainty language where evidence is incomplete. Each segment must advance the story "
        "and include a distinct, filmable visual intent. Avoid repeated conclusions and generic filler."
    )
    prompt = f"""Create a complete documentary script plan.

Project title: {project.title}
Topic: {project.topic}
Audience: {project.audience}
Tone: {project.tone}
Visual style: {project.visual_style}
Target length: approximately {target_words} narration words
Preferred scene length: about {target_scene_seconds:.1f} seconds
Editorial angle: {angle.strip() or 'Find the clearest defensible causal angle.'}
Suggested act vocabulary: {act_names}

Research notes supplied by the producer:
{research_notes.strip() or 'No verified research package has been supplied. Stay conceptual and avoid unsupported specifics.'}

Return a coherent hook, context, mechanism, evidence, complication, consequence, and conclusion. The final segment should resolve the thesis before a restrained CTA. Output only the requested structured data."""

    request_payload = {
        "model": model,
        "store": False,
        "instructions": instructions,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "documentary_script",
                "description": "A scene-level documentary script and visual plan.",
                "strict": True,
                "schema": SCRIPT_SCHEMA,
            }
        },
    }
    request = Request(
        f"{base_url}/responses",
        data=json.dumps(request_payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Documentary-OS/2.0",
        },
    )
    try:
        with urlopen(request, timeout=300) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ScriptGenerationError(
            f"OpenAI script generation returned HTTP {exc.code}: {detail}"
        ) from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ScriptGenerationError(f"OpenAI script generation failed: {exc}") from exc

    try:
        generated = json.loads(_response_output_text(response_payload))
    except json.JSONDecodeError as exc:
        raise ScriptGenerationError("The script provider returned invalid structured JSON") from exc
    return normalize_generated_script(
        project,
        generated,
        provider="openai",
        model=model,
        angle=angle,
        research_notes=research_notes,
        target_scene_seconds=target_scene_seconds,
        previous_revision=previous_revision,
    )


def update_script_draft(
    project: Project,
    current: dict[str, Any],
    *,
    title: str | None = None,
    thesis: str | None = None,
    segments: list[dict[str, Any]] | None = None,
    editor_notes: str = "",
) -> dict[str, Any]:
    draft = deepcopy(current)
    if title is not None:
        draft["title"] = title.strip() or project.title
    if thesis is not None:
        draft["thesis"] = thesis.strip()
    raw_segments = segments if segments is not None else list(draft.get("segments", []))
    generated = {
        "title": draft.get("title") or project.title,
        "thesis": draft.get("thesis") or project.topic,
        "segments": raw_segments,
    }
    updated = normalize_generated_script(
        project,
        generated,
        provider=str(draft.get("provider") or "manual-edit"),
        model=str(draft.get("model") or "manual"),
        angle=str(draft.get("angle") or ""),
        research_notes=str(draft.get("research_notes") or ""),
        target_scene_seconds=8.0,
        previous_revision=int(draft.get("revision", 1)),
    )
    updated["editor_notes"] = editor_notes.strip()
    updated["edited_at"] = utc_iso()
    _write_json(_production_directory(project.id) / "script.json", updated)
    return updated
