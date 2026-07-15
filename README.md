# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.3 Asset Planner MVP

The working application now includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project, scene, and selected-asset storage,
- documentary project creation, listing, and deletion,
- plain-narration breakdown and smart structured scene import,
- editable timing, visual intent, keywords, asset type, and status,
- scene-by-scene Pexels photo and video search,
- visual preview, creator attribution, and selection,
- a direct Pexels-search fallback when no API key is configured,
- automatic visual-coverage tracking across the documentary.

## Architecture

```text
ai-documentary-os/
├── backend/                 FastAPI + SQLAlchemy + SQLite
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

Press `Control+C` in Terminal to stop both services.

## Using the Scene Engine

1. Create or open a documentary project.
2. Paste either plain narration or a structured scene plan.
3. Choose the fallback visual-slot duration.
4. Generate or import the scene plan.
5. Review and edit the resulting scene records.

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

## Connecting Pexels

Pexels requires an API key sent through the `Authorization` header. Keep that key only on your Mac.

1. Create or open `backend/.env`.
2. Add:

```text
PEXELS_API_KEY=your_key_here
```

3. Restart `./scripts/dev.sh`.
4. Open a project, enter the Asset Planner, select a scene, and search.

The app displays a prominent Pexels link and creator attribution. Without a key, it still generates a direct Pexels search link for the scene.

## Local data

The SQLite database is created at:

```text
backend/data/documentary_os.db
```

Secrets, the database, downloaded media, and generated exports are excluded from Git.

## Product direction

Read these before major development work:

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- [`docs/PAIN_LOG.md`](docs/PAIN_LOG.md)

The next major milestone is **asset downloading and local media organization**, followed by the first automatic timeline manifest.
