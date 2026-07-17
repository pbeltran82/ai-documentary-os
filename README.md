# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.9.2 Universal Visual Feed + Editorial Still Motion

The working application now includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project, scene, and selected-asset storage,
- plain-narration breakdown and smart structured scene import,
- editable timing, visual intent, keywords, asset type, and status,
- provider-independent visual search,
- Pixabay photo and video search,
- Unsplash photography search,
- one quality-filtered Open Archives feed spanning Wikimedia Commons, Openverse, Library of Congress, and The Met,
- NASA image and video search,
- optional Pexels search when a key becomes available,
- strict visual-relevance filtering for stock results,
- local downloading of every selected visual,
- source, creator, license, attribution, checksum, content type, and file-size records,
- an automatically refreshed timeline manifest,
- one globally ranked visual feed across every configured provider,
- scene-by-scene FFmpeg assembly planning,
- scene-aware still-image pushes, pulls, pans, steady holds, and soft 16:9 backgrounds,
- selectable 16:9 YouTube and native 9:16 Shorts delivery, with semantic
  full-size mobile beats for every generated exact-visual family,
- playable local 1080p first-cut previews,
- local narration upload and FFprobe duration analysis,
- explicit narration-versus-timeline mismatch warnings,
- narrated first-cut rendering with AAC audio,
- visual-coverage percentage and uncovered narration reporting, and
- scene-count guidance with a direct recovery path to the Scene Engine.

## Architecture

```text
ai-documentary-os/
├── backend/                 FastAPI + SQLAlchemy + SQLite
│   ├── app/services/assets  Replaceable media-provider adapters
│   ├── app/services/        Local intake, narration, and FFmpeg assembly
│   └── data/projects/       Local media, audio, manifests, plans, and renders
├── frontend/                React + TypeScript + Vite
├── docs/                    Master plan and creator pain log
├── episode-001/             Existing production workspace
├── prompts/                 Existing reusable AI prompts
├── templates/               Existing production templates
├── workflows/               Existing documentary workflows
└── scripts/                 Local setup and development commands
```

## First-time setup on macOS

From the repository root:

```bash
chmod +x scripts/setup.sh scripts/dev.sh
./scripts/setup.sh
```

The Timeline Builder and narration analyzer require FFmpeg and FFprobe. Homebrew installs both together:

```bash
brew install ffmpeg
```

## Start the application

```bash
./scripts/dev.sh
```

Open:

- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Downloaded media, audio, and renders: `http://localhost:8000/media/`

Press `Control+C` in Terminal to stop both services.

## Using the Scene Engine

1. Create or open a documentary project.
2. Paste plain narration or a structured scene plan.
3. Choose the fallback visual-slot duration.
4. Generate or import the scene plan.
5. Review and edit the scene records.

Supported structured format:

```text
Scene 01
00:00–00:05
Narration: Most people underestimate the power of time.
Visual intent: Calendar pages and long-term market growth
Search terms: calendar time lapse, investment growth, stock chart
Preferred visual: Stock video
Asset status: Missing
```

## Connecting visual providers

Create or open `backend/.env`:

```text
PIXABAY_API_KEY=your_pixabay_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
PEXELS_API_KEY=
```

Restart the app after changing the file:

```bash
./scripts/dev.sh
```

Provider roles:

| Provider | Photos | Video | Key required | Primary role |
|---|---:|---:|---:|---|
| Pixabay | Yes | Yes | Yes | General stock media |
| Unsplash | Yes | No | Yes | Cinematic photography |
| Open Archives | Yes | No | No | Wikimedia, Openverse, Library of Congress, and The Met |
| NASA Images | Yes | Yes | No | Space, science, aviation, climate |
| Pexels | Yes | Yes | Optional | Additional general stock media |

The planner preserves the provider, creator, source page, original remote media URL, license label, rights URL, and attribution text with every selected visual. Always review the original source page before publishing.

## Local project files

Selecting a visual downloads the media immediately and marks the scene `ready` only after the local copy succeeds. Uploading narration stores the audio locally and records its duration, checksum, content type, file size, and original filename.

```text
backend/data/projects/
└── project-0001/
    ├── assets/
    │   ├── scene-001-pixabay-12345.mp4
    │   └── scene-001-pixabay-12345-poster.jpg
    ├── audio/
    │   ├── narration.mp3
    │   └── narration.json
    └── timeline/
        ├── manifest.json
        ├── render-plan.json
        ├── render.sh
        └── first-cut.mp4
```

Timeline API endpoints:

```text
POST   /api/projects/{project_id}/timeline-manifest
POST   /api/projects/{project_id}/timeline/plan
PUT    /api/projects/{project_id}/timeline/narration?filename=voiceover.mp3
DELETE /api/projects/{project_id}/timeline/narration
POST   /api/projects/{project_id}/timeline/render
```

## Timeline and narration behavior

For every ready scene, the assembly engine:

1. loads the selected local media file,
2. loops short video when needed,
3. trims the source to the exact scene duration,
4. scales and pads it to 1920×1080,
5. converts it to 30 fps and `yuv420p`, and
6. concatenates every scene in timeline order.

When narration is attached, the engine:

1. inspects its exact duration with FFprobe,
2. compares it with the visual timeline,
3. reports whether it is aligned, shorter, or longer,
4. pads short narration with silence or trims long narration to the timeline runtime, and
5. muxes the voiceover into the first cut as AAC audio.

When narration is longer than the visual timeline, v0.7.1 treats the result explicitly as an **excerpt**. The interface shows:

- the percentage of narration with visual coverage,
- the uncovered duration,
- an estimated total scene count based on the current visual pace,
- the approximate number of additional visual decisions required, and
- an **Expand scene plan** action that returns directly to Smart Import.

The system preserves the original uploaded narration file. Automatic time-stretching is intentionally not applied because it can damage voice quality and storytelling cadence.

Optional local-media, narration, and render settings in `backend/.env`:

```text
PUBLIC_BACKEND_URL=http://localhost:8000
MEDIA_ROOT=./data/projects
MAX_ASSET_DOWNLOAD_BYTES=524288000
MAX_NARRATION_UPLOAD_BYTES=262144000
TIMELINE_OUTPUT_WIDTH=1920
TIMELINE_OUTPUT_HEIGHT=1080
TIMELINE_OUTPUT_FPS=30
TIMELINE_RENDER_TIMEOUT_SECONDS=3600
TIMELINE_AUDIO_SAMPLE_RATE=48000
TIMELINE_AUDIO_BITRATE=192k
NARRATION_ALIGNMENT_TOLERANCE_SECONDS=0.25
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

## Existing local databases

The database lives at:

```text
backend/data/documentary_os.db
```

Startup migrations remain additive. Existing projects, scenes, downloaded assets, and rights records are preserved. Narration metadata is stored inside the local project folder, so no destructive database migration is required for v0.7.1.

Secrets, the database, downloaded media, narration, and generated exports are excluded from Git.

## Product direction

Read these before major development work:

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- [`docs/PAIN_LOG.md`](docs/PAIN_LOG.md)

Timeline planning now emits an upload-ready timed SubRip caption track from the approved narration scenes. The next milestone is **final export controls**, followed by music and publishing assistance.
