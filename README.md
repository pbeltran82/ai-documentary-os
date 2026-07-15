# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.5 Local Asset Intake

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
- local video-poster storage,
- SHA-256, content type, and file-size records,
- source, creator, license, rights, and attribution preservation,
- an automatically refreshed timeline manifest for first assembly.

## Architecture

```text
ai-documentary-os/
├── backend/                 FastAPI + SQLAlchemy + SQLite
│   ├── app/services/assets  Replaceable media-provider adapters
│   └── data/projects/       Local project media + timeline manifests
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

## Start the application

```bash
./scripts/dev.sh
```

Open:

- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Downloaded media: `http://localhost:8000/media/`

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

Files are organized predictably:

```text
backend/data/projects/
└── project-0001/
    ├── assets/
    │   ├── scene-001-pixabay-12345.mp4
    │   └── scene-001-pixabay-12345-poster.jpg
    └── timeline/
        └── manifest.json
```

The manifest includes scene timing, narration, local paths, checksums, source links, and rights metadata. It is refreshed whenever a selected asset is added or removed. It can also be regenerated through:

```text
POST /api/projects/{project_id}/timeline-manifest
```

Optional local-media settings in `backend/.env`:

```text
PUBLIC_BACKEND_URL=http://localhost:8000
MEDIA_ROOT=./data/projects
MAX_ASSET_DOWNLOAD_BYTES=524288000
```

## Existing local databases

The database lives at:

```text
backend/data/documentary_os.db
```

On startup, v0.5 safely adds the local-file metadata columns to an existing SQLite database. Existing projects, scenes, and rights records are preserved.

Secrets, the database, downloaded media, and generated exports are excluded from Git.

## Product direction

Read these before major development work:

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- [`docs/PAIN_LOG.md`](docs/PAIN_LOG.md)

The next major milestone is the **Timeline Builder**, which will consume the local manifest and create an automatic first assembly plan.
