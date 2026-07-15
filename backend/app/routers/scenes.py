from __future__ import annotations

import re
from collections.abc import Iterable

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
    chunks = split_narration(payload.narration, payload.target_scene_seconds)
    if not chunks:
        raise HTTPException(status_code=422, detail="Narration did not contain usable text")

    if payload.replace_existing:
        db.execute(delete(Scene).where(Scene.project_id == project_id))
        existing_scenes: list[Scene] = []
    else:
        existing_scenes = list(db.scalars(scene_query(project_id)).all())

    cursor = existing_scenes[-1].end_seconds if existing_scenes else 0.0
    next_number = len(existing_scenes) + 1

    for offset, chunk in enumerate(chunks):
        word_count = max(1, len(chunk.split()))
        estimated_duration = round(word_count / WORDS_PER_SECOND, 2)
        duration = min(
            payload.target_scene_seconds * 1.5,
            max(3.0, estimated_duration),
        )
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
