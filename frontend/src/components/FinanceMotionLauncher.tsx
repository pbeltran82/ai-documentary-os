import { useEffect, useMemo, useState } from "react";
import "../finance-motion.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

interface ProjectSummary {
  id: number;
  title: string;
}

interface SceneSummary {
  id: number;
  scene_number: number;
  duration_seconds: number;
  narration: string;
  visual_intent: string;
  selected_asset: { provider: string } | null;
}

interface ProjectDetail extends ProjectSummary {
  scenes: SceneSummary[];
}

interface TemplateOption {
  template_id: string;
  label: string;
  description: string;
}

interface MotionSuggestion {
  recommended: TemplateOption & {
    confidence: number;
    reason: string;
  };
  templates: TemplateOption[];
}

interface GeneratedAsset {
  provider: string;
  preview_url: string;
  download_url: string;
  duration_seconds: number;
  license_name: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Preserve the fallback message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function FinanceMotionLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [sceneId, setSceneId] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MotionSuggestion | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [generated, setGenerated] = useState<GeneratedAsset | null>(null);

  const selectedScene = useMemo(
    () => project?.scenes.find((scene) => scene.id === sceneId) ?? null,
    [project, sceneId],
  );

  useEffect(() => {
    if (!open || projects.length > 0) return;
    setLoading(true);
    setError("");
    void request<ProjectSummary[]>("/projects")
      .then((items) => {
        setProjects(items);
        setProjectId(items[0]?.id ?? null);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Unable to load projects"),
      )
      .finally(() => setLoading(false));
  }, [open, projects.length]);

  useEffect(() => {
    if (!open || !projectId) return;
    setLoading(true);
    setError("");
    setGenerated(null);
    void request<ProjectDetail>(`/projects/${projectId}`)
      .then((nextProject) => {
        setProject(nextProject);
        setSceneId(nextProject.scenes[0]?.id ?? null);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Unable to load project"),
      )
      .finally(() => setLoading(false));
  }, [open, projectId]);

  useEffect(() => {
    if (!open || !sceneId) return;
    setSuggestion(null);
    setGenerated(null);
    setError("");
    void request<MotionSuggestion>(`/scenes/${sceneId}/finance-motion-suggestion`)
      .then((nextSuggestion) => {
        setSuggestion(nextSuggestion);
        setTemplateId(nextSuggestion.recommended.template_id);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Unable to direct finance motion"),
      );
  }, [open, sceneId]);

  async function generate() {
    if (!sceneId || !templateId) return;
    setGenerating(true);
    setGenerated(null);
    setError("");
    try {
      const asset = await request<GeneratedAsset>(
        `/scenes/${sceneId}/finance-motion?template_id=${encodeURIComponent(templateId)}`,
        { method: "POST" },
      );
      setGenerated(asset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate motion graphic");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      <button className="finance-motion-launcher" onClick={() => setOpen(true)}>
        <span>✦</span>
        Generate exact visual
      </button>

      {open && (
        <div className="finance-motion-backdrop" role="presentation">
          <section
            className="finance-motion-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="finance-motion-title"
          >
            <header className="finance-motion-header">
              <div>
                <p>LOCAL CONTENT GENERATOR</p>
                <h2 id="finance-motion-title">Finance Motion Studio</h2>
                <span>
                  Build an exact, rights-clean 1080p animation when free providers fail.
                </span>
              </div>
              <button aria-label="Close Finance Motion Studio" onClick={() => setOpen(false)}>
                ×
              </button>
            </header>

            {error && <div className="finance-motion-error">{error}</div>}

            <div className="finance-motion-controls">
              <label>
                Project
                <select
                  value={projectId ?? ""}
                  onChange={(event) => setProjectId(Number(event.target.value))}
                >
                  {projects.map((item) => (
                    <option value={item.id} key={item.id}>{item.title}</option>
                  ))}
                </select>
              </label>
              <div className="finance-motion-rule">
                <strong>Editorial rule</strong>
                <span>Strong real footage first. Exact generated motion when stock fails.</span>
              </div>
            </div>

            {loading ? (
              <div className="finance-motion-empty">Loading production workspace…</div>
            ) : project && project.scenes.length > 0 ? (
              <div className="finance-motion-layout">
                <aside className="finance-motion-scenes">
                  {project.scenes.map((scene) => (
                    <button
                      className={scene.id === sceneId ? "active" : ""}
                      key={scene.id}
                      onClick={() => setSceneId(scene.id)}
                    >
                      <strong>Scene {String(scene.scene_number).padStart(2, "0")}</strong>
                      <span>{scene.duration_seconds:g}s · {scene.selected_asset?.provider ?? "No visual"}</span>
                      <p>{scene.narration}</p>
                    </button>
                  ))}
                </aside>

                <main className="finance-motion-workbench">
                  {selectedScene && (
                    <article className="finance-motion-scene-brief">
                      <span>SCENE PROMISE</span>
                      <strong>{selectedScene.visual_intent || selectedScene.narration}</strong>
                    </article>
                  )}

                  {suggestion && (
                    <>
                      <article className="finance-motion-recommendation">
                        <div>
                          <span>DIRECTOR RECOMMENDATION</span>
                          <h3>{suggestion.recommended.label}</h3>
                          <p>{suggestion.recommended.description}</p>
                        </div>
                        <strong>{Math.round(suggestion.recommended.confidence * 100)}%</strong>
                        <small>{suggestion.recommended.reason}</small>
                      </article>

                      <div className="finance-motion-template-grid">
                        {suggestion.templates.map((template) => (
                          <button
                            key={template.template_id}
                            className={template.template_id === templateId ? "active" : ""}
                            onClick={() => setTemplateId(template.template_id)}
                          >
                            <strong>{template.label}</strong>
                            <span>{template.description}</span>
                          </button>
                        ))}
                      </div>

                      <button
                        className="finance-motion-generate"
                        disabled={generating}
                        onClick={() => void generate()}
                      >
                        {generating ? "Rendering exact 1080p visual…" : "Generate and attach to scene"}
                      </button>
                    </>
                  )}

                  {generated && (
                    <article className="finance-motion-success">
                      <video src={generated.download_url} poster={generated.preview_url} controls autoPlay muted loop />
                      <div>
                        <span>GENERATED AND ATTACHED</span>
                        <h3>Project-owned motion graphic ready</h3>
                        <p>{generated.license_name}. The previous visual was replaced and the stale timeline render was invalidated.</p>
                        <button onClick={() => window.location.reload()}>Reload workspace</button>
                      </div>
                    </article>
                  )}
                </main>
              </div>
            ) : (
              <div className="finance-motion-empty">
                Create a project with scenes before generating motion graphics.
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
