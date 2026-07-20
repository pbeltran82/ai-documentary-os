import { useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type ProjectSummary = {
  id: number;
  title: string;
};

type AssetDirective = {
  execution_mode: "asset_first" | "exact_visual";
  preferred_media_type: string;
  fallback_media_type: string | null;
  overlay_mode: string;
  reason: string;
};

type VisualPlan = {
  strategy: {
    family: string;
    realism: string;
    source_mode: string;
    reason: string;
  };
  shot: {
    shot_type: string;
    composition: string;
    camera_move: string;
    focal_subject: string;
  };
  asset: AssetDirective;
};

type ProjectPlan = {
  project_id: number;
  project_title: string;
  scene_count: number;
  asset_first_count: number;
  exact_visual_count: number;
  scenes: Array<{
    scene_id: number;
    scene_number: number;
    plan: VisualPlan;
  }>;
};

type ExecutionEntry = {
  scene_id: number;
  scene_number: number;
  status: "completed" | "skipped" | "failed";
  execution_mode: string;
  visual_family: string;
  provider?: string;
  media_type?: string;
  reason: string;
};

type ExecutionResult = {
  project_id: number;
  project_title: string;
  scene_count: number;
  completed: number;
  skipped: number;
  failed: number;
  entries: ExecutionEntry[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = ((await response.json()) as { detail?: string }).detail ?? message;
    } catch {
      // Preserve the fallback message.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

function readable(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function VisualArchitectureLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [plan, setPlan] = useState<ProjectPlan | null>(null);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId) ?? null,
    [projectId, projects],
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
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load projects");
      })
      .finally(() => setLoading(false));
  }, [open, projects.length]);

  useEffect(() => {
    if (!open || !projectId) return;
    setLoading(true);
    setPlan(null);
    setResult(null);
    setError("");
    void request<ProjectPlan>(`/projects/${projectId}/visual-architecture-plan`)
      .then(setPlan)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to build visual plan");
      })
      .finally(() => setLoading(false));
  }, [open, projectId]);

  async function execute() {
    if (!projectId) return;
    setExecuting(true);
    setResult(null);
    setError("");
    const parameters = new URLSearchParams({
      replace_existing: String(replaceExisting),
      per_page: "6",
    });
    try {
      const nextResult = await request<ExecutionResult>(
        `/projects/${projectId}/visual-architecture-execute?${parameters.toString()}`,
        { method: "POST" },
      );
      setResult(nextResult);
      setPlan(await request<ProjectPlan>(`/projects/${projectId}/visual-architecture-plan`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to execute visual architecture");
    } finally {
      setExecuting(false);
    }
  }

  return (
    <>
      <button className="visual-architecture-launcher" onClick={() => setOpen(true)}>
        Visual Architecture
      </button>

      {open && (
        <div className="visual-architecture-backdrop" role="presentation">
          <section className="visual-architecture-modal" role="dialog" aria-modal="true">
            <header className="visual-architecture-header">
              <div>
                <p className="eyebrow">ASSET-FIRST DOCUMENTARY DIRECTION</p>
                <h2>Visual Architecture</h2>
                <p>
                  Real footage and photography carry documentary scenes. Procedural graphics
                  are reserved for data explanations and the final CTA.
                </p>
              </div>
              <button className="visual-architecture-close" onClick={() => setOpen(false)}>
                Close
              </button>
            </header>

            <div className="visual-architecture-controls">
              <label>
                Project
                <select
                  value={projectId ?? ""}
                  onChange={(event) => setProjectId(Number(event.target.value) || null)}
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="visual-architecture-checkbox">
                <input
                  type="checkbox"
                  checked={replaceExisting}
                  onChange={(event) => setReplaceExisting(event.target.checked)}
                />
                Replace existing visuals
              </label>
              <button
                className="primary-button"
                disabled={!projectId || loading || executing}
                onClick={() => void execute()}
              >
                {executing ? "Directing and attaching visuals…" : "Execute Visual Architecture"}
              </button>
            </div>

            {error && <div className="error-banner">{error}</div>}
            {loading && <div className="visual-architecture-loading">Building source plan…</div>}

            {plan && (
              <>
                <div className="visual-architecture-summary">
                  <article>
                    <strong>{plan.scene_count}</strong>
                    <span>Total scenes</span>
                  </article>
                  <article>
                    <strong>{plan.asset_first_count}</strong>
                    <span>Real asset first</span>
                  </article>
                  <article>
                    <strong>{plan.exact_visual_count}</strong>
                    <span>True explainers / CTA</span>
                  </article>
                </div>

                <div className="visual-architecture-scenes">
                  {plan.scenes.map((item) => (
                    <article key={item.scene_id} className="visual-architecture-scene">
                      <div className="visual-architecture-scene-number">
                        Scene {item.scene_number}
                      </div>
                      <div>
                        <strong>{readable(item.plan.strategy.family)}</strong>
                        <p>{item.plan.asset.reason}</p>
                        <div className="visual-architecture-tags">
                          <span>{readable(item.plan.asset.execution_mode)}</span>
                          <span>{readable(item.plan.strategy.source_mode)}</span>
                          <span>{readable(item.plan.shot.shot_type)}</span>
                          <span>{readable(item.plan.shot.camera_move)}</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            )}

            {result && (
              <section className="visual-architecture-result">
                <h3>{selectedProject?.title ?? result.project_title} execution</h3>
                <p>
                  {result.completed} completed · {result.skipped} preserved · {result.failed} blocked
                </p>
                <div className="visual-architecture-result-list">
                  {result.entries.map((entry) => (
                    <div key={entry.scene_id} className={`visual-result-${entry.status}`}>
                      <strong>Scene {entry.scene_number}</strong>
                      <span>{readable(entry.execution_mode)}</span>
                      <span>{entry.provider ? `${entry.provider} ${entry.media_type ?? ""}` : entry.reason}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </section>
        </div>
      )}
    </>
  );
}
