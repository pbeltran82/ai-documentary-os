from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from sqlalchemy.engine import Engine


SAFE_MARKERS = ("test", "tests", "e2e", "fixture", "fixtures")


def sqlite_path_from_url(database_url: str) -> Path | None:
    """Resolve a local SQLite path without importing the services package."""
    if not database_url.startswith("sqlite:///"):
        return None
    raw = unquote(database_url.removeprefix("sqlite:///"))
    if raw == ":memory:":
        return None
    return Path(raw).expanduser().resolve()


def _has_explicit_safety_marker(path: Path) -> bool:
    """Require an intentional test/e2e marker, not a generic OS temp directory."""
    components = [part.lower() for part in path.parts]
    filename = path.name.lower()
    return any(
        marker in filename or any(marker in component for component in components)
        for marker in SAFE_MARKERS
    )


def assert_destructive_database_is_safe(database_url: str, *, purpose: str) -> Path:
    """Only permit destructive resets against explicitly marked test/e2e SQLite files."""
    path = sqlite_path_from_url(database_url)
    if path is None:
        raise RuntimeError(
            f"Refusing destructive database operation for {purpose}: only a dedicated "
            "test/e2e SQLite database is allowed."
        )

    if not _has_explicit_safety_marker(path):
        raise RuntimeError(
            f"Refusing destructive database operation for {purpose}: {path} does not "
            "contain an explicit test/e2e safety marker."
        )
    return path


def backup_sqlite_database(database_url: str, *, label: str = "automatic") -> Path | None:
    """Create a timestamped sidecar backup when the SQLite file already exists."""
    path = sqlite_path_from_url(database_url)
    if path is None or not path.is_file():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{path.stem}-{label}-{timestamp}{path.suffix}.bak"
    shutil.copy2(path, destination)
    return destination


def guarded_drop_all(base, engine: Engine, *, database_url: str, purpose: str) -> Path:
    """Validate, back up, and only then drop metadata."""
    path = assert_destructive_database_is_safe(database_url, purpose=purpose)
    backup_sqlite_database(database_url, label="pre-reset")
    base.metadata.drop_all(bind=engine)
    return path
