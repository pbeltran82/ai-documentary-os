import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AssetPlanner } from "./components/AssetPlanner";
import { ProjectWorkspace } from "./components/ProjectWorkspace";
import { TimelineBuilder } from "./components/TimelineBuilder";
import type { Project, ProjectCreate, ProjectDetail, Scene, SceneUpdate } from "./types";

type WorkspaceMode = "scenes" | "assets" | "timeline";

const emptyProject: ProjectCreate = {
  title: "",
  topic: "",
  target_minutes: 8,
  audience: "General audience",
  tone: "Cinematic and informative",
  visual_style: "Cinematic documentary",
};

const pipeline = [
  { name: "Research", description: "Sources, facts, timeline" },
  { name: "Script", description: "Narration and story arc" },
  { name: "Scenes", description: "Timing and visual intent" },
  { name: "Assets", description: "Search, select, generate" },
  { name: "Timeline", description: "Automatic first assembly" },
  { name: "Export", description: "Polish and publish" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("scenes");
  const [form, setForm] = useState<ProjectCreate>(emptyProject);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [projectLoading, setProjectLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const totalMinutes = useMemo(
    () => projects.reduce((total, project) => total + project.target_minutes, 0),
    [projects],
  );

  async function refreshProjects() {
    try {
      setError("");
      setProjects(await api.listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load projects");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSelectedProject(projectId?: number) {
    const id = projectId ?? selectedProject?.id;
    if (!id) return;
    setProjectLoading(true);
    try {
      setError("");
      setSelectedProject(await api.getProject(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load project");
    } finally {
      setProjectLoading(false);
    }
  }

  useEffect(() => {
    void refreshProjects();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");

    try {
      const project = await api.createProject(form);
      setForm(emptyProject);
      setShowForm(false);
      setWorkspaceMode("scenes");
      await refreshProjects();
      await refreshSelectedProject(project.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create project");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(project: Project) {
    const confirmed = window.confirm(`Delete “${project.title}”?`);
    if (!confirmed) return;

    try {
      await api.deleteProject(project.id);
      if (selectedProject?.id === project.id) setSelectedProject(null);
      await refreshProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete project");
    }
  }

  async function openProject(project: Project) {
    setWorkspaceMode("scenes");
    await refreshSelectedProject(project.id);
  }

  async function generateScenes(narration: string, targetSeconds: number) {
    if (!selectedProject) return;
    try {
      setError("");
      await api.generateScenes(selectedProject.id, {
        narration,
        target_scene_seconds: targetSeconds,
        replace_existing: true,
      });
      await Promise.all([
        refreshSelectedProject(selectedProject.id),
        refreshProjects(),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate scenes");
      throw err;
    }
  }

  async function updateScene(sceneId: number, payload: SceneUpdate) {
    if (!selectedProject) return;
    try {
      setError("");
      await api.updateScene(sceneId, payload);
      await refreshSelectedProject(selectedProject.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update scene");
      throw err;
    }
  }

  async function deleteScene(scene: Scene) {
    if (!selectedProject) return;
    const confirmed = window.confirm(`Delete Scene ${scene.scene_number}?`);
    if (!confirmed) return;

    try {
      setError("");
      await api.deleteScene(scene.id);
      await refreshSelectedProject(selectedProject.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete scene");
    }
  }

  function returnToMissionControl() {
    setSelectedProject(null);
    setWorkspaceMode("scenes");
  }

  const activePipelineStage =
    workspaceMode === "timeline"
      ? "Timeline"
      : workspaceMode === "assets"
        ? "Assets"
        : "Scenes";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand-mark">AD</div>
          <p className="eyebrow">LOCAL-FIRST CREATIVE SYSTEM</p>
          <h1>AI Documentary OS</h1>
          <p className="sidebar-copy">
            We do not automate storytelling. We automate everything around it.
          </p>
        </div>

        <nav className="nav-list" aria-label="Primary navigation">
          <button
            className={`nav-item ${selectedProject ? "" : "active"}`}
            onClick={returnToMissionControl}
          >
            Mission Control
          </button>
          <button
            className={`nav-item ${
              selectedProject && workspaceMode === "scenes" ? "active" : ""
            }`}
            disabled={!selectedProject}
            onClick={() => setWorkspaceMode("scenes")}
          >
            Scene Engine {selectedProject && workspaceMode === "scenes" ? "· Active" : ""}
          </button>
          <button
            className={`nav-item ${
              selectedProject && workspaceMode === "assets" ? "active" : ""
            }`}
            disabled={!selectedProject || selectedProject.scenes.length === 0}
            onClick={() => setWorkspaceMode("assets")}
          >
            Asset Planner {selectedProject && workspaceMode === "assets" ? "· Active" : ""}
          </button>
          <button
            className={`nav-item ${
              selectedProject && workspaceMode === "timeline" ? "active" : ""
            }`}
            disabled={!selectedProject || selectedProject.scenes.length === 0}
            onClick={() => setWorkspaceMode("timeline")}
          >
            Timeline Builder {selectedProject && workspaceMode === "timeline" ? "· Active" : ""}
          </button>
        </nav>

        <div className="sidebar-footer">
          <span>v0.6.0</span>
          <span>Timeline Builder</span>
        </div>
      </aside>

      {selectedProject ? (
        workspaceMode === "assets" ? (
          <AssetPlanner
            project={selectedProject}
            loading={projectLoading}
            error={error}
            onBack={returnToMissionControl}
            onOpenScenes={() => setWorkspaceMode("scenes")}
            onRefreshProject={() => refreshSelectedProject(selectedProject.id)}
          />
        ) : workspaceMode === "timeline" ? (
          <TimelineBuilder
            project={selectedProject}
            loading={projectLoading}
            error={error}
            onBack={returnToMissionControl}
            onOpenAssets={() => setWorkspaceMode("assets")}
          />
        ) : (
          <ProjectWorkspace
            project={selectedProject}
            loading={projectLoading}
            error={error}
            onBack={returnToMissionControl}
            onOpenAssets={() => setWorkspaceMode("assets")}
            onGenerate={generateScenes}
            onUpdateScene={updateScene}
            onDeleteScene={deleteScene}
          />
        )
      ) : (
        <main className="workspace">
          <header className="topbar">
            <div>
              <p className="eyebrow">MISSION CONTROL</p>
              <h2>What documentary are we making today?</h2>
            </div>
            <button className="primary-button" onClick={() => setShowForm(true)}>
              + New documentary
            </button>
          </header>

          {error && <div className="error-banner">{error}</div>}

          <section className="stats-grid" aria-label="Project overview">
            <article className="stat-card">
              <span>Projects</span>
              <strong>{projects.length}</strong>
            </article>
            <article className="stat-card">
              <span>Planned runtime</span>
              <strong>{totalMinutes} min</strong>
            </article>
            <article className="stat-card accent">
              <span>Current focus</span>
              <strong>Timeline Builder</strong>
            </article>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">BIRD’S-EYE VIEW</p>
                <h3>The documentary production pipeline</h3>
              </div>
              <span className="status-pill">Phase 4 active</span>
            </div>

            <div className="pipeline-grid">
              {pipeline.map((stage, index) => (
                <article
                  className={`pipeline-card ${
                    stage.name === activePipelineStage ? "active-stage" : ""
                  }`}
                  key={stage.name}
                >
                  <span className="stage-number">{String(index + 1).padStart(2, "0")}</span>
                  <h4>{stage.name}</h4>
                  <p>{stage.description}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">PROJECTS</p>
                <h3>Recent documentaries</h3>
              </div>
              <span className="subtle-text">
                {loading ? "Loading…" : `${projects.length} total`}
              </span>
            </div>

            {!loading && projects.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🎬</div>
                <h4>Your production slate is empty.</h4>
                <p>Create the first documentary project and begin building the workflow.</p>
                <button className="secondary-button" onClick={() => setShowForm(true)}>
                  Create first project
                </button>
              </div>
            ) : (
              <div className="project-grid">
                {projects.map((project) => (
                  <article className="project-card" key={project.id}>
                    <div className="project-card-top">
                      <span className="status-pill">{project.status}</span>
                      <button
                        className="icon-button"
                        aria-label={`Delete ${project.title}`}
                        onClick={() => void handleDelete(project)}
                      >
                        ×
                      </button>
                    </div>
                    <h4>{project.title}</h4>
                    <p>{project.topic}</p>
                    <div className="project-meta">
                      <span>{project.target_minutes} min</span>
                      <span>{project.tone}</span>
                      <span>{formatDate(project.created_at)}</span>
                    </div>
                    <button className="project-open-button" onClick={() => void openProject(project)}>
                      Open production →
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        </main>
      )}

      {showForm && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="new-project-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">NEW PRODUCTION</p>
                <h3 id="new-project-title">Create a documentary project</h3>
              </div>
              <button className="icon-button" onClick={() => setShowForm(false)} aria-label="Close">
                ×
              </button>
            </div>

            <form className="project-form" onSubmit={handleSubmit}>
              <label>
                Project title
                <input
                  required
                  minLength={2}
                  value={form.title}
                  placeholder="The Rise and Fall of Kodak"
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                />
              </label>

              <label className="wide-field">
                Topic and story angle
                <textarea
                  required
                  minLength={5}
                  rows={5}
                  value={form.topic}
                  placeholder="Investigate how Kodak invented the digital camera but failed to lead the revolution."
                  onChange={(event) => setForm({ ...form, topic: event.target.value })}
                />
              </label>

              <label>
                Target runtime
                <div className="input-with-suffix">
                  <input
                    required
                    type="number"
                    min={1}
                    max={180}
                    value={form.target_minutes}
                    onChange={(event) =>
                      setForm({ ...form, target_minutes: Number(event.target.value) })
                    }
                  />
                  <span>minutes</span>
                </div>
              </label>

              <label>
                Audience
                <input
                  required
                  value={form.audience}
                  onChange={(event) => setForm({ ...form, audience: event.target.value })}
                />
              </label>

              <label>
                Tone
                <input
                  required
                  value={form.tone}
                  onChange={(event) => setForm({ ...form, tone: event.target.value })}
                />
              </label>

              <label>
                Visual style
                <input
                  required
                  value={form.visual_style}
                  onChange={(event) => setForm({ ...form, visual_style: event.target.value })}
                />
              </label>

              <div className="form-actions wide-field">
                <button type="button" className="ghost-button" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="primary-button" disabled={saving}>
                  {saving ? "Creating…" : "Create project"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
