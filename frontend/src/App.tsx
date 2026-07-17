import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AssetPlanner } from "./components/AssetPlanner";
import { ProjectWorkspace } from "./components/ProjectWorkspace";
import { ScriptStudio } from "./components/ScriptStudio";
import { TimelineBuilder } from "./components/TimelineBuilder";
import type { Project, ProjectCreate, ProjectDetail, Scene, SceneUpdate } from "./types";

type WorkspaceMode = "script" | "scenes" | "assets" | "timeline";

const emptyProject: ProjectCreate = {
  title: "",
  topic: "",
  target_minutes: 8,
  audience: "General audience",
  tone: "Cinematic and informative",
  visual_style: "Cinematic documentary",
  video_format: "youtube",
};

const pipeline = [
  { name: "Research", description: "Sources, facts, timeline" },
  { name: "Script", description: "Narration and story arc" },
  { name: "Scenes", description: "Timing and visual intent" },
  { name: "Assets", description: "Direct, rank, approve" },
  { name: "Timeline", description: "Motion, transitions, narration" },
  { name: "Export", description: "Polish and publish" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("script");
  const [form, setForm] = useState<ProjectCreate>(emptyProject);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [projectLoading, setProjectLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const totalMinutes = useMemo(() => projects.reduce((total, project) => total + project.target_minutes, 0), [projects]);

  async function refreshProjects() {
    try { setProjects(await api.listProjects()); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load projects"); }
    finally { setLoading(false); }
  }

  async function refreshSelectedProject(projectId?: number) {
    const id = projectId ?? selectedProject?.id;
    if (!id) return;
    setProjectLoading(true);
    try { setSelectedProject(await api.getProject(id)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load project"); }
    finally { setProjectLoading(false); }
  }

  useEffect(() => { void refreshProjects(); }, []);

  useEffect(() => {
    const openTimeline = (event: Event) => {
      const projectId = Number((event as CustomEvent<{ projectId?: number }>).detail?.projectId);
      if (!projectId) return;
      setProjectLoading(true);
      void api.getProject(projectId).then((project) => {
        setSelectedProject(project);
        setWorkspaceMode("timeline");
      }).catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to open Timeline Builder"))
        .finally(() => setProjectLoading(false));
    };
    window.addEventListener("atlas:open-timeline", openTimeline);
    return () => window.removeEventListener("atlas:open-timeline", openTimeline);
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const project = await api.createProject(form);
      setForm(emptyProject);
      setShowForm(false);
      setWorkspaceMode("script");
      await refreshProjects();
      await refreshSelectedProject(project.id);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create project"); }
    finally { setSaving(false); }
  }

  async function handleDelete(project: Project) {
    if (!window.confirm(`Delete “${project.title}”?`)) return;
    try {
      await api.deleteProject(project.id);
      if (selectedProject?.id === project.id) setSelectedProject(null);
      await refreshProjects();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to delete project"); }
  }

  async function openProject(project: Project) {
    setWorkspaceMode("script");
    await refreshSelectedProject(project.id);
  }

  async function generateScenes(narration: string, targetSeconds: number) {
    if (!selectedProject) return;
    await api.generateScenes(selectedProject.id, { narration, target_scene_seconds: targetSeconds, replace_existing: true });
    await Promise.all([refreshSelectedProject(selectedProject.id), refreshProjects()]);
  }

  async function updateScene(sceneId: number, payload: SceneUpdate) {
    if (!selectedProject) return;
    await api.updateScene(sceneId, payload);
    await refreshSelectedProject(selectedProject.id);
  }

  async function deleteScene(scene: Scene) {
    if (!selectedProject || !window.confirm(`Delete Scene ${scene.scene_number}?`)) return;
    await api.deleteScene(scene.id);
    await refreshSelectedProject(selectedProject.id);
  }

  function returnToMissionControl() {
    setSelectedProject(null);
    setWorkspaceMode("script");
  }

  const activePipelineStage = workspaceMode === "script" ? "Script" : workspaceMode === "timeline" ? "Timeline" : workspaceMode === "assets" ? "Assets" : "Scenes";

  function navButton(mode: WorkspaceMode, label: string, disabled = false) {
    return <button className={`nav-item ${selectedProject && workspaceMode === mode ? "active" : ""}`} disabled={!selectedProject || disabled} onClick={() => setWorkspaceMode(mode)}>{label} {selectedProject && workspaceMode === mode ? "· Active" : ""}</button>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div><div className="brand-mark">AD</div><p className="eyebrow">LOCAL-FIRST CREATIVE SYSTEM</p><h1>AI Documentary OS</h1><p className="sidebar-copy">We do not automate storytelling. We automate everything around it.</p></div>
        <nav className="nav-list" aria-label="Primary navigation">
          <button className={`nav-item ${selectedProject ? "" : "active"}`} onClick={returnToMissionControl}>Mission Control</button>
          {navButton("script", "Script Studio")}
          {navButton("scenes", "Scene Engine")}
          {navButton("assets", "Asset Planner", selectedProject?.scenes.length === 0)}
          {navButton("timeline", "Timeline Builder", selectedProject?.scenes.length === 0)}
        </nav>
        <div className="sidebar-footer"><span>v2.0 alpha</span><span>End-to-end production</span></div>
      </aside>

      {selectedProject ? (
        workspaceMode === "script" ? (
          <ScriptStudio project={selectedProject} onBack={returnToMissionControl} onOpenScenes={() => setWorkspaceMode("scenes")} onProjectChanged={() => Promise.all([refreshSelectedProject(selectedProject.id), refreshProjects()]).then(() => undefined)} />
        ) : workspaceMode === "assets" ? (
          <AssetPlanner project={selectedProject} loading={projectLoading} error={error} onBack={returnToMissionControl} onOpenScenes={() => setWorkspaceMode("scenes")} onRefreshProject={() => refreshSelectedProject(selectedProject.id)} />
        ) : workspaceMode === "timeline" ? (
          <TimelineBuilder project={selectedProject} loading={projectLoading} error={error} onBack={returnToMissionControl} onOpenAssets={() => setWorkspaceMode("assets")} onOpenScenes={() => setWorkspaceMode("scenes")} onProjectChanged={() => Promise.all([refreshSelectedProject(selectedProject.id), refreshProjects()]).then(() => undefined)} />
        ) : (
          <ProjectWorkspace project={selectedProject} loading={projectLoading} error={error} onBack={returnToMissionControl} onOpenAssets={() => setWorkspaceMode("assets")} onGenerate={generateScenes} onUpdateScene={updateScene} onDeleteScene={deleteScene} />
        )
      ) : (
        <main className="workspace">
          <header className="topbar"><div><p className="eyebrow">MISSION CONTROL</p><h2>Documentary production, without the busywork.</h2></div><button className="primary-button" onClick={() => setShowForm(true)}>New project</button></header>
          {error && <div className="error-banner">{error}</div>}
          <section className="stats-grid"><article className="stat-card"><span>Projects</span><strong>{projects.length}</strong></article><article className="stat-card"><span>Planned runtime</span><strong>{totalMinutes} min</strong></article><article className="stat-card accent"><span>Active milestone</span><strong>{activePipelineStage}</strong></article></section>
          <section className="panel"><div className="section-heading"><div><p className="eyebrow">PRODUCTION PIPELINE</p><h3>Research → Script → Scenes → Assets → Timeline → Export</h3></div></div><div className="pipeline-grid">{pipeline.map((stage, index) => <article key={stage.name} className={`pipeline-card ${stage.name === activePipelineStage ? "active-stage" : ""}`}><span className="stage-number">0{index + 1}</span><h4>{stage.name}</h4><p>{stage.description}</p></article>)}</div></section>
          <section className="panel"><div className="section-heading"><div><p className="eyebrow">PROJECTS</p><h3>Current documentaries</h3></div></div>{loading ? <div className="empty-state"><p>Loading projects…</p></div> : projects.length === 0 ? <div className="empty-state"><div className="empty-icon">🎬</div><h4>No projects yet</h4><p>Create the first documentary workspace.</p></div> : <div className="project-grid">{projects.map((project) => <article className="project-card" key={project.id}><div className="project-card-top"><span className="status-pill">{project.status}</span><button className="icon-button" aria-label={`Delete ${project.title}`} onClick={() => void handleDelete(project)}>×</button></div><h4>{project.title}</h4><p>{project.topic}</p><div className="project-meta"><span>{project.target_minutes} min target</span><span>{project.video_format === "shorts" ? "Shorts · 9:16" : "YouTube · 16:9"}</span><span>{project.visual_style}</span><span>{formatDate(project.updated_at)}</span></div><button className="project-open-button" onClick={() => void openProject(project)}>Open workspace</button></article>)}</div>}</section>

          {showForm && <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="new-project-title"><div className="section-heading"><div><p className="eyebrow">NEW DOCUMENTARY</p><h3 id="new-project-title">Create a project workspace</h3></div><button className="icon-button" onClick={() => setShowForm(false)}>×</button></div><form className="project-form" onSubmit={handleSubmit}><label>Project title<input required minLength={2} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label>Target runtime<div className="input-with-suffix"><input type="number" min={1} max={180} value={form.target_minutes} onChange={(event) => setForm({ ...form, target_minutes: Number(event.target.value) })} /><span>minutes</span></div></label><label className="wide-field">Topic or documentary promise<textarea required minLength={5} rows={4} value={form.topic} onChange={(event) => setForm({ ...form, topic: event.target.value })} /></label><label>Audience<input value={form.audience} onChange={(event) => setForm({ ...form, audience: event.target.value })} /></label><label>Tone<input value={form.tone} onChange={(event) => setForm({ ...form, tone: event.target.value })} /></label><label className="wide-field">Visual style<input value={form.visual_style} onChange={(event) => setForm({ ...form, visual_style: event.target.value })} /></label><div className="wide-field new-project-format"><span>Delivery format</span><div className="format-switch" role="group" aria-label="New project video format"><button type="button" className={form.video_format === "youtube" ? "active" : ""} onClick={() => setForm({ ...form, video_format: "youtube" })}><span className="format-glyph landscape" aria-hidden="true" /><strong>YouTube</strong><small>16:9 · 1920×1080</small></button><button type="button" className={form.video_format === "shorts" ? "active" : ""} onClick={() => setForm({ ...form, video_format: "shorts" })}><span className="format-glyph portrait" aria-hidden="true" /><strong>Shorts</strong><small>9:16 · 1080×1920</small></button></div></div><div className="form-actions wide-field"><button type="button" className="ghost-button" onClick={() => setShowForm(false)}>Cancel</button><button type="submit" className="primary-button" disabled={saving}>{saving ? "Creating…" : "Create project"}</button></div></form></section></div>}
        </main>
      )}
    </div>
  );
}

export default App;
