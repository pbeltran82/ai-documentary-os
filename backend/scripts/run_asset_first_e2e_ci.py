from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (BACKEND_DIR, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

configured_ffmpeg = os.getenv("FFMPEG_BIN", "").strip()
configured_path = Path(configured_ffmpeg).expanduser() if configured_ffmpeg else None
resolved_ffmpeg = (
    str(configured_path.resolve())
    if configured_path is not None and configured_path.is_file()
    else shutil.which(configured_ffmpeg or "ffmpeg")
)
if not resolved_ffmpeg:
    raise RuntimeError(
        "FFmpeg could not be resolved inside Python; "
        f"FFMPEG_BIN={configured_ffmpeg!r}, PATH={os.getenv('PATH', '')!r}"
    )

from app.services import finance_motion as finance_engine  # noqa: E402
from app.services import finance_motion_art as finance_art  # noqa: E402
from app.services import timeline_builder as timeline_builder  # noqa: E402
from app.services import timeline_playback_polish as timeline_polish  # noqa: E402

finance_engine.FFMPEG_NAME = resolved_ffmpeg
finance_art.engine.FFMPEG_NAME = resolved_ffmpeg
timeline_builder.FFMPEG_NAME = resolved_ffmpeg
timeline_builder.ffmpeg_executable = lambda: resolved_ffmpeg
timeline_polish.base.FFMPEG_NAME = resolved_ffmpeg
timeline_polish.base.ffmpeg_executable = lambda: resolved_ffmpeg

from run_asset_first_e2e import main  # noqa: E402

print(
    {
        "resolved_ffmpeg": resolved_ffmpeg,
        "timeline_ffmpeg": timeline_builder.ffmpeg_executable(),
        "finance_ffmpeg": finance_engine.FFMPEG_NAME,
    }
)
main()
