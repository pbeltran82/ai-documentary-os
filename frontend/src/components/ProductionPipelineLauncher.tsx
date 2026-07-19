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
  const [message, setMessage] = useState("");

  const stage = (stageId: string) => pipeline?.stages.find((item) => item.stage_id === stageId);
  const directionStage = stage("direction");
  const visualStage = stage("visuals");
  const narrationStage = stage("narration");
  const assemblyStage = stage("assembly");
  const renderStage = stage("render");
  const actionLabel = directionStage?.status !== "complete"
    ? "Prepare missing direction"
    : visualStage?.status !== "complete"
      ? "Open Exact Visual Studio"
      : narrationStage?.status !== "complete"
        ? "Attach narration"
        : assemblyStage?.status !== "complete"
          ? "Build timeline plan"
          : renderStage?.status !== "complete"
            ? "Render first cut"
            : "Refresh production status";

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

  async function refreshPipeline() {
    if (!projectId) return;
    setPipeline(await request<PipelineStatus>(`/projects/${projectId}/production-pipeline`));
  }

  async function runNextAction() {
    if (!projectId) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (directionStage?.status !== "complete") {
        const result = await request<PipelineStatus>(`/projects/${projectId}/production-pipeline/prepare`, { method: "POST" });
        setPipeline(result);
        setMessage(`Prepared ${result.prepared_scene_ids?.length ?? 0} missing scene direction plan(s).`);
      } else if (visualStage?.status !== "complete") {
        setOpen(false);
        document.querySelector<HTMLButtonElement>(".finance-motion-launcher")?.click();
      } else if (narrationStage?.status !== "complete") {
        setOpen(false);
        window.dispatchEvent(new CustomEvent("atlas:open-timeline", { detail: { projectId } }));
      } else if (assemblyStage?.status !== "complete") {
        await request(`/projects/${projectId}/timeline-manifest`, { method: "POST" });
        await request(`/projects/${projectId}/timeline/plan`, { method: "POST" });
        await refreshPipeline();
        setMessage("Timeline manifest and machine-readable render plan are ready.");
      } else if (renderStage?.status !== "complete") {
        await request(`/projects/${projectId}/timeline/render`, { method: "POST" });
        await refreshPipeline();
        setMessage("Narrated first cut rendered successfully.");
      } else {
        await refreshPipeline();
        setMessage("Production status refreshed.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to run the next production action");
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
        {message && <div className="production-pipeline-message" role="status" style={{ marginTop: "1rem", padding: ".8rem", borderRadius: ".7rem", background: "rgba(15, 76, 67, .52)", color: "#b8f3e5" }}>{message}</div>}
        <label className="production-pipeline-project">Project<select value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
        {busy && !pipeline ? <div className="production-pipeline-loading">Evaluating the production…</div> : pipeline && <>
          <div className="production-pipeline-summary"><div><span>SCENES</span><strong>{pipeline.scene_count}</strong></div><div><span>VISUAL COVERAGE</span><strong>{pipeline.visual_coverage_percent}%</strong></div><div><span>CONTROL PLANE</span><strong>{pipeline.version}</strong></div></div>
          <div className="production-pipeline-stages">{pipeline.stages.map((stage, index) => <article className={stage.status} key={stage.stage_id}><b>{index + 1}</b><div><span>{stage.status.replace("_", " ")}</span><h3>{stage.label}</h3><p>{stage.description}</p><small>{stage.complete}/{stage.total} complete</small></div><strong>{stage.percent}%</strong></article>)}</div>
          <aside><span>NEXT BEST ACTION</span><strong>{pipeline.next_action}</strong>{pipeline.prepared_scene_ids?.length ? <small>Prepared scenes: {pipeline.prepared_scene_ids.join(", ")}</small> : null}</aside>
        </>}
        <footer><button className="secondary" onClick={() => setOpen(false)}>Close</button><button className="primary" disabled={busy || !projectId || !pipeline} onClick={() => void runNextAction()}>{busy ? "Working…" : actionLabel}</button></footer>
      </section>
    </div>}
  </>;
}
