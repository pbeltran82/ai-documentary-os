from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Scene
from ..schemas import (
    SceneCreate,
    SceneGenerateRequest,
    SceneGenerateResponse,
    SceneRead,
    SceneUpdate,
)

router = APIRouter(tags=["scenes"])

WORDS_PER_SECOND = 2.5
STOP_WORDS = {
    "about", "after", "again", "against", "almost", "also", "among", "because",
    "before", "being", "between", "could", "does", "during", "each", "from",
    "have", "having", "into", "itself", "more", "most", "other", "over", "same",
    "should", "some", "such", "than", "that", "their", "there", "these", "they",
    "this", "those", "through", "under", "very", "what", "when", "where", "which",
    "while", "with", "would", "your", "you", "were", "will", "just", "then", "them",
}
ASSET_TYPE_ALIASES = {
    "stock video": "stock_video",
    "video": "stock_video",
    "stock footage": "stock_video",
    "stock image": "stock_image",
    "image": "stock_image",
    "photo": "stock_image",
    "ai image": "ai_image",
    "generated image": "ai_image",
    "ai video": "ai_video",
    "generated video": "ai_video",
    "chart": "chart",
    "graphic": "chart",
    "chart / graphic": "chart",
    "text animation": "text_animation",
}
ASSET_STATUS_ALIASES = {
    "missing": "missing",
    "needed": "missing",
    "searching": "searching",
    "selected": "selected",
    "ready": "ready",
    "complete": "ready",
    "completed": "ready",
}
FIELD_NAMES = (
    "visual intent|search keywords|search terms|preferred visual|preferred asset|"
    "asset type|asset status|narration|voiceover|keywords|visual|status"
)
SCENE_HEADER_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*)?scene\s+\d+\b[^\n]*$"
)
FIELD_LINE_RE = re.compile(
    rf"^\s*(?:[-*]\s*)?(?:\*\*)?(?P<label>{FIELD_NAMES})"
    rf"(?::\*\*|\*\*:|:)\s*(?P<value>.*)$",
    re.IGNORECASE | re.MULTILINE,
)
TIMECODE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?)\s*[–—-]\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?)"
)


@dataclass
class ImportedScene:
    narration: str
    duration_seconds: float
    visual_intent: str
    search_keywords: list[str]
    preferred_asset_type: str
    asset_status: str
    start_seconds: float | None = None
    end_seconds: float | None = None


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_scene_or_404(scene_id: int, db: Session) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def scene_query(project_id: int):
    return (
        select(Scene)
        .where(Scene.project_id == project_id)
        .order_by(Scene.scene_number.asc())
    )


def recalculate_timing(scenes: Iterable[Scene]) -> None:
    cursor = 0.0
    for number, scene in enumerate(scenes, start=1):
        scene.scene_number = number
        scene.start_seconds = round(cursor, 2)
        cursor += scene.duration_seconds
        scene.end_seconds = round(cursor, 2)


def clean_label(value: str) -> str:
    return " ".join(value.lower().strip().split())


def clean_field_value(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized.strip("*").strip()


def parse_labeled_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_label: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_lines
        if current_label is not None:
            fields[current_label] = clean_field_value(" ".join(current_lines))
        current_label = None
        current_lines = []

    for raw_line in block.splitlines():
        match = FIELD_LINE_RE.match(raw_line)
        if match:
            flush()
            current_label = clean_label(match.group("label"))
            current_lines = [match.group("value")]
        elif current_label is not None:
            current_lines.append(raw_line.strip())

    flush()
    return fields


def timecode_to_seconds(value: str) -> float:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes * 60 + seconds)
    hours, minutes, seconds = parts
    return float(hours * 3600 + minutes * 60 + seconds)


def split_keywords(value: str) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,;|\n]+", value):
        keyword = clean_label(part.strip("* "))
        if keyword and keyword not in seen:
            keywords.append(keyword)
            seen.add(keyword)
    return keywords[:20]


def estimate_duration(narration: str, target_scene_seconds: float) -> float:
    word_count = max(1, len(narration.split()))
    estimated_duration = round(word_count / WORDS_PER_SECOND, 2)
    return round(
        min(target_scene_seconds * 1.5, max(3.0, estimated_duration)),
        2,
    )


def split_narration(narration: str, target_scene_seconds: float) -> list[str]:
    normalized = re.sub(r"\s+", " ", narration).strip()
    if not normalized:
        return []

    target_words = max(5, round(target_scene_seconds * WORDS_PER_SECOND))
    raw_sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\s*\n+\s*", normalized)
        if sentence.strip()
    ]

    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(" ".join(current).strip())
            current = []

    for sentence in raw_sentences:
        words = sentence.split()
        while words:
            available = target_words - len(current)
            if current and len(words) > available:
                current.extend(words[:available])
                words = words[available:]
                flush()
                continue

            if not current and len(words) > round(target_words * 1.4):
                chunks.append(" ".join(words[:target_words]))
                words = words[target_words:]
                continue

            current.extend(words)
            words = []
            if len(current) >= round(target_words * 0.8):
                flush()

    flush()
    return chunks


def extract_keywords(narration: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", narration.lower())
    keywords: list[str] = []
    seen: set[str] = set()
    for word in words:
        cleaned = word.strip("'-")
        if len(cleaned) < 4 or cleaned in STOP_WORDS or cleaned in seen:
            continue
        keywords.append(cleaned)
        seen.add(cleaned)
        if len(keywords) == 6:
            break
    return keywords


def build_visual_intent(narration: str) -> str:
    phrase = re.sub(r"\s+", " ", narration).strip().rstrip(".!?")
    words = phrase.split()
    short_phrase = " ".join(words[:16])
    return f"Show a clear cinematic visual representing: {short_phrase}"


def parse_structured_scene_plan(
    text: str, target_scene_seconds: float
) -> list[ImportedScene]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    headers = list(SCENE_HEADER_RE.finditer(normalized))
    if not headers:
        return []

    imported: list[ImportedScene] = []
    for index, header in enumerate(headers):
        block_end = headers[index + 1].start() if index + 1 < len(headers) else len(normalized)
        block = normalized[header.start():block_end].strip()
        fields = parse_labeled_fields(block)

        narration = fields.get("narration") or fields.get("voiceover") or ""
        if not narration:
            continue

        time_match = TIMECODE_RE.search(block)
        start_seconds: float | None = None
        end_seconds: float | None = None
        if time_match:
            start_seconds = timecode_to_seconds(time_match.group("start"))
            end_seconds = timecode_to_seconds(time_match.group("end"))

        if (
            start_seconds is not None
            and end_seconds is not None
            and end_seconds > start_seconds
        ):
            duration_seconds = round(end_seconds - start_seconds, 2)
        else:
            duration_seconds = estimate_duration(narration, target_scene_seconds)

        visual_intent = (
            fields.get("visual intent")
            or fields.get("visual")
            or build_visual_intent(narration)
        )
        keyword_text = (
            fields.get("search terms")
            or fields.get("search keywords")
            or fields.get("keywords")
            or ""
        )
        search_keywords = (
            split_keywords(keyword_text) if keyword_text else extract_keywords(narration)
        )
        asset_type_text = (
            fields.get("preferred visual")
            or fields.get("preferred asset")
            or fields.get("asset type")
            or ""
        )
        status_text = fields.get("asset status") or fields.get("status") or ""

        imported.append(
            ImportedScene(
                narration=narration,
                duration_seconds=duration_seconds,
                visual_intent=visual_intent,
                search_keywords=search_keywords,
                preferred_asset_type=ASSET_TYPE_ALIASES.get(
                    clean_label(asset_type_text), "stock_video"
                ),
                asset_status=ASSET_STATUS_ALIASES.get(
                    clean_label(status_text), "missing"
                ),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
        )

    return imported


@router.get("/projects/{project_id}/scenes", response_model=list[SceneRead])
def list_scenes(project_id: int, db: Session = Depends(get_db)) -> list[Scene]:
    get_project_or_404(project_id, db)
    return list(db.scalars(scene_query(project_id)).all())


@router.post(
    "/projects/{project_id}/scenes",
    response_model=SceneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_scene(
    project_id: int, payload: SceneCreate, db: Session = Depends(get_db)
) -> Scene:
    project = get_project_or_404(project_id, db)
    scenes = list(db.scalars(scene_query(project_id)).all())
    start_seconds = scenes[-1].end_seconds if scenes else 0.0
    scene = Scene(
        project_id=project_id,
        scene_number=len(scenes) + 1,
        start_seconds=start_seconds,
        end_seconds=start_seconds + payload.duration_seconds,
        **payload.model_dump(),
    )
    project.status = "storyboard"
    db.add(scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.post(
    "/projects/{project_id}/scenes/generate",
    response_model=SceneGenerateResponse,
)
def generate_scenes(
    project_id: int,
    payload: SceneGenerateRequest,
    db: Session = Depends(get_db),
) -> SceneGenerateResponse:
    project = get_project_or_404(project_id, db)
    structured_input = bool(
        SCENE_HEADER_RE.search(payload.narration)
        and FIELD_LINE_RE.search(payload.narration)
    )
    imported_scenes = parse_structured_scene_plan(
        payload.narration, payload.target_scene_seconds
    )

    if structured_input and not imported_scenes:
        raise HTTPException(
            status_code=422,
            detail=(
                "Structured scene plan detected, but no Narration: or Voiceover: "
                "fields could be imported."
            ),
        )

    if payload.replace_existing:
        db.execute(delete(Scene).where(Scene.project_id == project_id))
        existing_scenes: list[Scene] = []
    else:
        existing_scenes = list(db.scalars(scene_query(project_id)).all())

    cursor = existing_scenes[-1].end_seconds if existing_scenes else 0.0
    next_number = len(existing_scenes) + 1

    if imported_scenes:
        preserve_timecodes = payload.replace_existing and not existing_scenes
        for offset, imported in enumerate(imported_scenes):
            if (
                preserve_timecodes
                and imported.start_seconds is not None
                and imported.end_seconds is not None
            ):
                start_seconds = imported.start_seconds
                end_seconds = imported.end_seconds
            else:
                start_seconds = round(cursor, 2)
                end_seconds = round(cursor + imported.duration_seconds, 2)

            scene = Scene(
                project_id=project_id,
                scene_number=next_number + offset,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_seconds=imported.duration_seconds,
                narration=imported.narration,
                visual_intent=imported.visual_intent,
                search_keywords=imported.search_keywords,
                preferred_asset_type=imported.preferred_asset_type,
                asset_status=imported.asset_status,
            )
            db.add(scene)
            cursor = end_seconds
    else:
        chunks = split_narration(payload.narration, payload.target_scene_seconds)
        if not chunks:
            raise HTTPException(
                status_code=422, detail="Narration did not contain usable text"
            )

        for offset, chunk in enumerate(chunks):
            duration = estimate_duration(chunk, payload.target_scene_seconds)
            scene = Scene(
                project_id=project_id,
                scene_number=next_number + offset,
                start_seconds=round(cursor, 2),
                end_seconds=round(cursor + duration, 2),
                duration_seconds=duration,
                narration=chunk,
                visual_intent=build_visual_intent(chunk),
                search_keywords=extract_keywords(chunk),
                preferred_asset_type="stock_video",
                asset_status="missing",
            )
            db.add(scene)
            cursor += duration

    project.status = "storyboard"
    db.commit()

    scenes = list(db.scalars(scene_query(project_id)).all())
    return SceneGenerateResponse(
        project_id=project_id,
        scene_count=len(scenes),
        total_duration_seconds=round(sum(scene.duration_seconds for scene in scenes), 2),
        scenes=scenes,
    )


@router.patch("/scenes/{scene_id}", response_model=SceneRead)
def update_scene(
    scene_id: int, payload: SceneUpdate, db: Session = Depends(get_db)
) -> Scene:
    scene = get_scene_or_404(scene_id, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(scene, field, value)

    scenes = list(db.scalars(scene_query(scene.project_id)).all())
    recalculate_timing(scenes)
    db.commit()
    db.refresh(scene)
    return scene


@router.delete("/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(scene_id: int, db: Session = Depends(get_db)) -> Response:
    scene = get_scene_or_404(scene_id, db)
    project_id = scene.project_id
    db.delete(scene)
    db.flush()
    scenes = list(db.scalars(scene_query(project_id)).all())
    recalculate_timing(scenes)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
