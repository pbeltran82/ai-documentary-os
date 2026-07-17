import { useEffect, useState } from "react";
import "../production-pipeline.css";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type Project = { id: number; title: string };
type PipelineStage = {
  stage_id: string;
  label: string;
  status: "blocked" | "ready" | "in_progress" | "complete";
  complete: number;
  total: number;
  percent: number;
  description: string;
};
type PipelineStatus = {
  version: string;
  project_title: string;
  status: string;
  scene_count: number;
  visual_coverage_percent: number;
  stages: PipelineStage[];
  next_action: string;
  prepared_scene_ids?: number[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }
  return await response.json() as T;
}

export function ProductionPipelineLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || projects.length) return;
    void request<Project[]>("/projects").then((items) => {
      setProjects(items);
      setProjectId(items[0]?.id ?? null);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load projects"));
  }, [open, projects.length]);

  useEffect(() => {
    if (!open || !projectId) return;
    setBusy(true);
    setError("");
    void request<PipelineStatus>(`/projects/${projectId}/production-pipeline`).then(setPipeline)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to inspect production pipeline"))
      .finally(() => setBusy(false));
  }, [open, projectId]);

  async function prepare() {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      setPipeline(await request<PipelineStatus>(`/projects/${projectId}/production-pipeline/prepare`, { method: "POST" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to prepare production pipeline");
    } finally {
      setBusy(false);
    }
  }

  return <>
    <button className="production-pipeline-launcher" onClick={() => setOpen(true)}><span>▶</span> Production pipeline</button>
    {open && <div className="production-pipeline-backdrop">
      <section className="production-pipeline-modal" role="dialog" aria-modal="true">
        <header><div><span>AI DOCUMENTARY OS v2.0</span><h2>Production Pipeline</h2><p>One control plane from directed scenes to the final narrated first cut.</p></div><button onClick={() => setOpen(false)} aria-label="Close">×</button></header>
        {error && <div className="production-pipeline-error">{error}</div>}
        <label className="production-pipeline-project">Project<select value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
        {busy && !pipeline ? <div className="production-pipeline-loading">Evaluating the production…</div> : pipeline && <>
          <div className="production-pipeline-summary"><div><span>SCENES</span><strong>{pipeline.scene_count}</strong></div><div><span>VISUAL COVERAGE</span><strong>{pipeline.visual_coverage_percent}%</strong></div><div><span>CONTROL PLANE</span><strong>{pipeline.version}</strong></div></div>
          <div className="production-pipeline-stages">{pipeline.stages.map((stage, index) => <article className={stage.status} key={stage.stage_id}><b>{index + 1}</b><div><span>{stage.status.replace("_", " ")}</span><h3>{stage.label}</h3><p>{stage.description}</p><small>{stage.complete}/{stage.total} complete</small></div><strong>{stage.percent}%</strong></article>)}</div>
          <aside><span>NEXT BEST ACTION</span><strong>{pipeline.next_action}</strong>{pipeline.prepared_scene_ids?.length ? <small>Prepared scenes: {pipeline.prepared_scene_ids.join(", ")}</small> : null}</aside>
        </>}
        <footer><button className="secondary" onClick={() => setOpen(false)}>Close</button><button className="primary" disabled={busy || !projectId} onClick={() => void prepare()}>{busy ? "Preparing…" : "Prepare missing direction"}</button></footer>
      </section>
    </div>}
  </>;
}
