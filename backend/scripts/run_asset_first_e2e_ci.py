from __future__ import annotations

import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (BACKEND_DIR, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

resolved_ffmpeg = shutil.which("ffmpeg")
if not resolved_ffmpeg:
    raise RuntimeError("The CI image reports FFmpeg unavailable inside Python")

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
