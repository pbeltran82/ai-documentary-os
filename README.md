# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.2.1 Smart Scene Import

The working application now includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project and scene storage,
- documentary project creation, listing, and deletion,
- a dedicated Scene Engine workspace,
- plain-narration breakdown with estimated timing,
- structured scene-plan import with labeled field detection,
- supplied timecode, narration, visual-intent, keyword, asset-type, and status mapping,
- editable scene production metadata,
- automatic timestamp recalculation after edits and deletions,
- the complete production pipeline at a bird's-eye view,
- a living master plan and creator pain log.

The repository's existing prompts, templates, workflows, and Episode 1 workspace remain part of the project and will be integrated into the application over time.

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

This creates `backend/.venv`, installs Python dependencies, and runs `npm install` in the frontend.

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
2. Select **Open Scene Engine**.
3. Paste either plain narration or a structured scene plan.
4. Choose the desired fallback visual-slot duration—five seconds is a practical starting point.
5. Generate or import the scene plan.
6. Review and edit timing, visual intent, search keywords, asset type, and asset status.

Plain narration is split deterministically and locally at roughly 150 spoken words per minute. Structured plans are detected and mapped into the correct fields instead of treating production labels as voiceover text.

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

The importer also accepts `Voiceover`, `Search keywords`, `Asset type`, and simple Markdown headings or labels.

## Manual startup

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm run dev
```

## Local data

The SQLite database is created at:

```text
backend/data/documentary_os.db
```

It is intentionally excluded from Git.

## Product direction

Read these before major development work:

- [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
- [`docs/PAIN_LOG.md`](docs/PAIN_LOG.md)

The next major milestone is the **Asset Planner**, which will use each scene's narration, visual intent, and keywords to find suitable stock-media candidates and prepare automatic timeline assembly.
