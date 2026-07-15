# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.6 Timeline Builder

The working application now includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project, scene, and selected-asset storage,
- plain-narration breakdown and smart structured scene import,
- editable timing, visual intent, keywords, asset type, and status,
- provider-independent visual search,
- Pixabay photo and video search,
- Unsplash photography search,
- Wikimedia Commons historical and cultural image search,
- NASA image and video search,
- optional Pexels search when a key becomes available,
- strict visual-relevance filtering for stock results,
- local downloading of every selected visual,
- SHA-256, content type, file size, source, creator, license, and attribution records,
- an automatically refreshed timeline manifest,
- scene-by-scene assembly planning,
- reproducible FFmpeg render scripts,
- a playable local 1080p silent first-cut preview.

## Architecture

```text
ai-documentary-os/
├── backend/                 FastAPI + SQLAlchemy + SQLite
│   ├── app/services/assets  Replaceable media-provider adapters
│   ├── app/services/        Local intake + FFmpeg assembly engine
│   └── data/projects/       Local media, manifests, plans, and renders
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

The Timeline Builder requires FFmpeg:

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
- Downloaded media and renders: `http://localhost:8000/media/`

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

Create or open `backend/.env`. The two currently useful keyed providers are:

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
| Wikimedia Commons | Yes | No | No | History, maps, art, archives |
| NASA Images | Yes | Yes | No | Space, science, aviation, climate |
| Pexels | Yes | Yes | Optional | Additional general stock media |

The planner preserves the provider, creator, source page, original remote media URL, license label, rights URL, and attribution text with every selected visual. Always review the original source page before publishing.

## Local project files

Selecting a visual downloads the media immediately and marks the scene `ready` only after the local copy succeeds.

The project workspace is organized predictably:

```text
backend/data/projects/
└── project-0001/
    ├── assets/
    │   ├── scene-001-pixabay-12345.mp4
    │   └── scene-001-pixabay-12345-poster.jpg
    └── timeline/
        ├── manifest.json
        ├── render-plan.json
        ├── render.sh
        └── first-cut.mp4
```

The timeline manifest includes scene timing, narration, local paths, checksums, source links, and rights metadata. The render plan adds exact clip operations and the complete FFmpeg command.

Timeline API endpoints:

```text
POST /api/projects/{project_id}/timeline-manifest
POST /api/projects/{project_id}/timeline/plan
POST /api/projects/{project_id}/timeline/render
```

## Timeline Builder behavior

For every ready scene, the assembly engine:

1. loads the selected local media file,
2. loops short video when needed,
3. trims the source to the exact scene duration,
4. scales and pads it to 1920×1080,
5. converts it to 30 fps and `yuv420p`, and
6. concatenates every scene in timeline order.

The v0.6 first cut is intentionally silent. Narration, music, transitions, captions, and final export controls are later milestones.

Optional local-media and render settings in `backend/.env`:

```text
PUBLIC_BACKEND_URL=http://localhost:8000
MEDIA_ROOT=./data/projects
MAX_ASSET_DOWNLOAD_BYTES=524288000
TIMELINE_OUTPUT_WIDTH=1920
TIMELINE_OUTPUT_HEIGHT=1080
TIMELINE_OUTPUT_FPS=30
TIMELINE_RENDER_TIMEOUT_SECONDS=3600
FFMPEG_BIN=ffmpeg
```

## Existing local databases

The database lives at:

```text
backend/data/documentary_os.db
```

Startup migrations remain additive. Existing projects, scenes, downloaded assets, and rights records are preserved.

Secrets, the database, downloaded media, and generated exports are excluded from Git.

## Product direction

Read these before major development work:

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- [`docs/PAIN_LOG.md`](docs/PAIN_LOG.md)

The next milestone is **narration audio alignment**, followed by transitions, captions, music, and final export controls.
