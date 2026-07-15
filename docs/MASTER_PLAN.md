# AI Documentary OS — Master Plan

## Vision

Build a local-first AI production operating system that transforms a documentary idea into an organized, editable, publishable production package.

## Mission

Reduce the time and friction required to produce documentaries by automating repetitive production work while preserving human creative control.

## North Star

> We do not automate storytelling. We automate everything around storytelling.

## Primary workflow

1. Idea and project brief
2. Research and source verification
3. Story architecture and script
4. Scene breakdown and timing
5. Asset search, selection, and generation
6. Automatic first-pass timeline assembly
7. Human polish and quality control
8. Export and publishing package

## Product principles

- **Local first:** Personal projects and media remain on the creator's machine by default.
- **Human approval:** The creator controls story, tone, sources, visuals, and final edits.
- **Automate repetition:** Search, file organization, timing, status tracking, and assembly are prime automation targets.
- **Structured data:** Projects, scenes, assets, sources, and exports are stored as editable records rather than disposable chat output.
- **Provider independence:** AI, stock-media, voice, and video providers should be replaceable.
- **Working milestones:** Every sprint ends with a runnable, testable improvement.

## Roadmap

### Phase 1 — Foundation

- Local FastAPI backend
- React mission-control dashboard
- SQLite project storage
- Documentary project creation
- Bird's-eye production pipeline

### Phase 2 — Scene Engine

- Import narration or script
- Split narration into timed scenes
- Store keywords, emotion, people, location, and visual intent per scene
- Review and edit scene boundaries

### Phase 3 — Asset Planner

- Generate search queries from each scene
- Search stock-media providers
- Preview and attach candidate assets
- Track license and attribution metadata
- Fall back to AI image or video generation when appropriate

### Phase 4 — Timeline Builder

- Align assets to narration timings
- Trim and sequence assets automatically
- Add simple motion to still images
- Produce a first-pass MP4 and editing manifest

### Phase 5 — Production Intelligence

- Research with citations
- Script and outline assistance
- Voiceover integration
- Music and sound recommendations
- Thumbnail and YouTube packaging

## Current sprint

**Sprint 1: Foundation**

Definition of done:

- The backend starts locally and exposes `/health` and `/api/projects`.
- The frontend starts locally at `http://localhost:5173`.
- A documentary project can be created, saved in SQLite, listed, and deleted.
- The dashboard displays the complete production pipeline and current priorities.

## Next priority

Build the Scene Engine around real narration timing, because scenes become the unit that connects audio, visuals, and timeline assembly.
