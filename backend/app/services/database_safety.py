from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from sqlalchemy.engine import Engine


SAFE_MARKERS = ("test", "tests", "e2e", "fixture", "tmp", "temporary")


def sqlite_path_from_url(database_url: str) -> Path | None:
    """Resolve a local SQLite path without touching non-SQLite databases."""
    if not database_url.startswith("sqlite:///"):
        return None
    raw = unquote(database_url.removeprefix("sqlite:///"))
    if raw == ":memory:":
        return None
    return Path(raw).expanduser().resolve()


def assert_destructive_database_is_safe(database_url: str, *, purpose: str) -> Path | None:
    """Refuse destructive schema operations against a normal user database."""
    if os.getenv("ALLOW_DESTRUCTIVE_DATABASE_RESET", "").strip() == "1":
        return sqlite_path_from_url(database_url)

    path = sqlite_path_from_url(database_url)
    if path is None:
        raise RuntimeError(
            f"Refusing destructive database operation for {purpose}: only an explicit "
            "test/e2e SQLite database or ALLOW_DESTRUCTIVE_DATABASE_RESET=1 is allowed."
        )

    searchable = " ".join(part.lower() for part in path.parts)
    if not any(marker in searchable for marker in SAFE_MARKERS):
        raise RuntimeError(
            f"Refusing destructive database operation for {purpose}: {path} does not "
            "contain a test/e2e safety marker. Use a dedicated test database."
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


def guarded_drop_all(base, engine: Engine, *, database_url: str, purpose: str) -> Path | None:
    """Back up, validate, and only then drop metadata."""
    path = assert_destructive_database_is_safe(database_url, purpose=purpose)
    backup_sqlite_database(database_url, label="pre-reset")
    base.metadata.drop_all(bind=engine)
    return path
