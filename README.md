# AI Documentary OS

A local-first documentary production operating system focused on the two most expensive creator bottlenecks:

1. finding strong images and video for each narration segment, and
2. assembling those assets into correctly timed timeline slots.

> We do not automate storytelling. We automate everything around storytelling.

## Current milestone: v0.2 Scene Engine

The working application now includes:

- a React + TypeScript mission-control dashboard,
- a FastAPI backend,
- local SQLite project and scene storage,
- documentary project creation, listing, and deletion,
- a dedicated Scene Engine workspace,
- narration-to-scene breakdown with estimated timing,
- editable visual intent, search keywords, preferred asset type, and asset status,
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
3. Paste the narration or finished voiceover script.
4. Choose the desired visual-slot duration—five seconds is a practical starting point.
5. Generate the scene plan.
6. Review and edit timing, visual intent, search keywords, asset type, and asset status.

The current splitter is deterministic and local. It estimates narration timing at roughly 150 words per minute and creates structured scene records without using a paid AI API.

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
