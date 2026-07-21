from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.models import Project, Scene  # noqa: E402
from app.services import hyperframes_renderer  # noqa: E402


def main() -> None:
    if not hyperframes_renderer.enabled():
        raise RuntimeError(
            "HYPERFRAMES_ENABLED is not active. Confirm backend/.env contains "
            "HYPERFRAMES_ENABLED=1 and run this command from backend/."
        )

    ready, reason = hyperframes_renderer.available()
    if not ready:
        raise RuntimeError(reason)

    with SessionLocal() as session:
        project = session.scalar(
            select(Project)
            .options(selectinload(Project.scenes))
            .order_by(Project.id.desc())
        )
        if project is None:
            raise RuntimeError("No project exists in documentary_os.db")

        routes = (
            ("tech_behavior_motion", "machine_choice_cta"),
            ("tech_behavior_motion", "behavior_prediction_engine"),
            ("tech_behavior_motion", "algorithm_chose_you"),
        )
        chosen: tuple[Scene, str, str] | None = None
        for scene in sorted(project.scenes, key=lambda item: item.scene_number):
            for family_id, template_id in routes:
                expected_numbers = {
                    "machine_choice_cta": {4},
                    "behavior_prediction_engine": {8},
                    "algorithm_chose_you": {12},
                }
                if scene.scene_number in expected_numbers[template_id]:
                    chosen = (scene, family_id, template_id)
                    break
            if chosen:
                break

        if chosen is None:
            scene = sorted(project.scenes, key=lambda item: item.scene_number)[0]
            chosen = (scene, "tech_behavior_motion", "behavior_prediction_engine")

        scene, family_id, template_id = chosen
        rendered = hyperframes_renderer.render_scene(scene, family_id, template_id)
        print(
            json.dumps(
                {
                    "status": "passed",
                    "project_id": project.id,
                    "scene_id": scene.id,
                    "scene_number": scene.scene_number,
                    "family_id": family_id,
                    "template_id": template_id,
                    "output": rendered.media_relative_path,
                    "composition_dir": rendered.composition_dir,
                    "size_bytes": rendered.size_bytes,
                    "command": list(rendered.command),
                    "stdout": rendered.stdout[-1200:],
                    "stderr": rendered.stderr[-1200:],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
