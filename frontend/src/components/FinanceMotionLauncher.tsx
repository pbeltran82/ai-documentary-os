import { useEffect, useMemo, useState } from "react";
import "../finance-motion.css";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type ProjectSummary = { id: number; title: string };
type SceneSummary = {
  id: number;
  scene_number: number;
  duration_seconds: number;
  narration: string;
  visual_intent: string;
  selected_asset: { provider: string } | null;
};
type ProjectDetail = ProjectSummary & { scenes: SceneSummary[] };
type TemplateOption = { template_id: string; label: string; description: string };
type MotionSuggestion = {
  recommended: TemplateOption & { confidence: number; reason: string };
  templates: TemplateOption[];
};
type GeneratedAsset = {
  preview_url: string;
  download_url: string;
  license_name: string;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = ((await response.json()) as { detail?: string }).detail ?? message;
    } catch {
      // Keep the fallback message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

function durationLabel(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}s`;
}

export function FinanceMotionLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [sceneId, setSceneId] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MotionSuggestion | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [generated, setGenerated] = useState<GeneratedAsset | null>(null);

  const scene = useMemo(
    () => project?.scenes.find((item) => item.id === sceneId) ?? null,
    [project, sceneId],
  );

  useEffect(() => {
    if (!open || projects.length) return;
    setBusy(true);
    void request<ProjectSummary[]>("/projects")
      .then((items) => {
        setProjects(items);
        setProjectId(items[0]?.id ?? null);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load projects"))
      .finally(() => setBusy(false));
  }, [open, projects.length]);

  useEffect(() => {
    if (!open || !projectId) return;
    setBusy(true);
    setGenerated(null);
    void request<ProjectDetail>(`/projects/${projectId}`)
      .then((item) => {
        setProject(item);
        setSceneId(item.scenes[0]?.id ?? null);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load project"))
      .finally(() => setBusy(false));
  }, [open, projectId]);

  useEffect(() => {
    if (!open || !sceneId) return;
    setGenerated(null);
    setSuggestion(null);
    void request<MotionSuggestion>(`/scenes/${sceneId}/finance-motion-suggestion`)
      .then((item) => {
        setSuggestion(item);
        setTemplateId(item.recommended.template_id);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to direct motion"));
  }, [open, sceneId]);

  async function generate() {
    if (!sceneId || !templateId) return;
    setBusy(true);
    setGenerated(null);
    setError("");
    try {
      setGenerated(
        await request<GeneratedAsset>(
          `/scenes/${sceneId}/finance-motion?template_id=${encodeURIComponent(templateId)}`,
          { method: "POST" },
        ),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to generate motion graphic");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button className="finance-motion-launcher" onClick={() => setOpen(true)}>
        <span>✦</span> Generate exact visual
      </button>
      {open && (
        <div className="finance-motion-backdrop">
          <section className="finance-motion-modal" role="dialog" aria-modal="true">
            <header className="finance-motion-header">
              <div>
                <p>LOCAL CONTENT GENERATOR</p>
                <h2>Finance Motion Studio</h2>
                <span>Build an exact, rights-clean 1080p animation when free providers fail.</span>
              </div>
              <button aria-label="Close" onClick={() => setOpen(false)}>×</button>
            </header>
            {error && <div className="finance-motion-error">{error}</div>}
            <div className="finance-motion-controls">
              <label>
                Project
                <select value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>
                  {projects.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}
                </select>
              </label>
              <div className="finance-motion-rule">
                <strong>Editorial rule</strong>
                <span>Strong real footage first. Exact generated motion when stock fails.</span>
              </div>
            </div>
            {busy && !project ? (
              <div className="finance-motion-empty">Loading production workspace…</div>
            ) : project?.scenes.length ? (
              <div className="finance-motion-layout">
                <aside className="finance-motion-scenes">
                  {project.scenes.map((item) => (
                    <button className={item.id === sceneId ? "active" : ""} key={item.id} onClick={() => setSceneId(item.id)}>
                      <strong>Scene {String(item.scene_number).padStart(2, "0")}</strong>
                      <span>{durationLabel(item.duration_seconds)} · {item.selected_asset?.provider ?? "No visual"}</span>
                      <p>{item.narration}</p>
                    </button>
                  ))}
                </aside>
                <main className="finance-motion-workbench">
                  {scene && <article className="finance-motion-scene-brief"><span>SCENE PROMISE</span><strong>{scene.visual_intent || scene.narration}</strong></article>}
                  {suggestion && (
                    <>
                      <article className="finance-motion-recommendation">
                        <div><span>DIRECTOR RECOMMENDATION</span><h3>{suggestion.recommended.label}</h3><p>{suggestion.recommended.description}</p></div>
                        <strong>{Math.round(suggestion.recommended.confidence * 100)}%</strong>
                        <small>{suggestion.recommended.reason}</small>
                      </article>
                      <div className="finance-motion-template-grid">
                        {suggestion.templates.map((item) => (
                          <button key={item.template_id} className={item.template_id === templateId ? "active" : ""} onClick={() => setTemplateId(item.template_id)}>
                            <strong>{item.label}</strong><span>{item.description}</span>
                          </button>
                        ))}
                      </div>
                      <button className="finance-motion-generate" disabled={busy} onClick={() => void generate()}>
                        {busy ? "Rendering exact 1080p visual…" : "Generate and attach to scene"}
                      </button>
                    </>
                  )}
                  {generated && (
                    <article className="finance-motion-success">
                      <video src={generated.download_url} poster={generated.preview_url} controls autoPlay muted loop />
                      <div><span>GENERATED AND ATTACHED</span><h3>Project-owned motion graphic ready</h3><p>{generated.license_name}. The old timeline render was invalidated.</p><button onClick={() => window.location.reload()}>Reload workspace</button></div>
                    </article>
                  )}
                </main>
              </div>
            ) : (
              <div className="finance-motion-empty">Create a project with scenes before generating motion graphics.</div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
