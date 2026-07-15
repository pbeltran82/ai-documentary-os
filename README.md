# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.1 Foundation

The first working application includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project storage,
- documentary project creation, listing, and deletion,
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

The next major milestone is the **Scene Engine**, which will split narration into timed scene records and create the foundation for stock-media search and automatic timeline assembly.
