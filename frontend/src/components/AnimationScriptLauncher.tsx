import { useEffect, useMemo, useState } from "react";
import "../animation-script.css";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type ProjectSummary = { id: number; title: string };
type SceneSummary = { id: number; scene_number: number; narration: string; visual_intent: string };
type ProjectDetail = ProjectSummary & { scenes: SceneSummary[] };
type AnimationPlan = {
  version: string;
  visual_strategy: string;
  character_action: string;
  expression_sequence: string[];
  pose_sequence: string[];
  props: string[];
  camera_direction: string;
  animation_beats: Record<string, number>;
  transition_intention: string;
};

const PERFORMANCE_METHODS = [
  "idle", "walk", "run", "look", "think", "point", "wave", "shrug",
  "confused", "nod", "shake_head", "type", "swipe", "tap", "celebrate",
] as const;

function performanceLabel(value: string): string {
  return value.split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }
  return await response.json() as T;
}

function list(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export function AnimationScriptLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [sceneId, setSceneId] = useState<number | null>(null);
  const [plan, setPlan] = useState<AnimationPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [previewNonce, setPreviewNonce] = useState(0);

  const scene = useMemo(() => project?.scenes.find((item) => item.id === sceneId) ?? null, [project, sceneId]);
  const previewUrl = useMemo(() => sceneId
    ? `${API}/scenes/${sceneId}/finance-motion-preview?family_id=character_explainer&style_id=premium_motion&preview=${previewNonce}`
    : "", [sceneId, previewNonce]);

  useEffect(() => {
    if (!open || projects.length) return;
    void request<ProjectSummary[]>("/projects").then((items) => {
      setProjects(items);
      setProjectId(items[0]?.id ?? null);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load projects"));
  }, [open, projects.length]);

  useEffect(() => {
    if (!open || !projectId) return;
    setBusy(true);
    void request<ProjectDetail>(`/projects/${projectId}`).then((item) => {
      setProject(item);
      setSceneId(item.scenes[0]?.id ?? null);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load project"))
      .finally(() => setBusy(false));
  }, [open, projectId]);

  useEffect(() => {
    if (!open || !sceneId) return;
    setBusy(true);
    setMessage("");
    setPreviewNonce((value) => value + 1);
    void request<AnimationPlan>(`/scenes/${sceneId}/animation-plan`).then(setPlan)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to direct animation"))
      .finally(() => setBusy(false));
  }, [open, sceneId]);

  async function regenerate() {
    if (!sceneId) return;
    setBusy(true);
    setError("");
    try {
      setPlan(await request<AnimationPlan>(`/scenes/${sceneId}/animation-plan/regenerate`, { method: "POST" }));
      setMessage("Animation script regenerated from the current narration and visual intent.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to regenerate plan");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!sceneId || !plan) return false;
    setBusy(true);
    setError("");
    try {
      setPlan(await request<AnimationPlan>(`/scenes/${sceneId}/animation-plan`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan),
      }));
      setMessage("Animation script saved. Exact Visual Studio and Batch Production will use it on the next render.");
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save plan");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function saveAndPreview() {
    if (!await save()) return;
    setPreviewNonce((value) => value + 1);
    setMessage("Animation script saved and the directed Character Studio frame refreshed.");
  }

  function addPerformanceMethod(method: string) {
    if (!plan) return;
    setPlan({ ...plan, pose_sequence: [...plan.pose_sequence, method] });
    setMessage(`${performanceLabel(method)} added to the end of the performance sequence.`);
  }

  function removePerformanceBeat(index: number) {
    if (!plan) return;
    setPlan({ ...plan, pose_sequence: plan.pose_sequence.filter((_, itemIndex) => itemIndex !== index) });
    setMessage("Performance beat removed. Save the animation script to keep this change.");
  }

  return <>
    <button className="animation-script-launcher" onClick={() => setOpen(true)}>✎ Direct animation</button>
    {open && <div className="animation-script-backdrop">
      <section className="animation-script-modal" role="dialog" aria-modal="true">
        <header><div><span>AI ANIMATION SCRIPT</span><h2>Animation Script Director</h2><p>Turn narration into editable performance, expression, prop, camera, and timing direction.</p></div><button onClick={() => setOpen(false)} aria-label="Close">×</button></header>
        {error && <div className="animation-script-error">{error}</div>}
        {message && <div className="animation-script-message">{message}</div>}
        <div className="animation-script-selectors">
          <label>Project<select value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label>Scene<select value={sceneId ?? ""} onChange={(event) => setSceneId(Number(event.target.value))}>{project?.scenes.map((item) => <option key={item.id} value={item.id}>Scene {String(item.scene_number).padStart(2, "0")}</option>)}</select></label>
        </div>
        {scene && <article className="animation-script-narration"><span>NARRATION</span><p>{scene.narration}</p><small>{scene.visual_intent}</small></article>}
        {busy && !plan ? <div className="animation-script-loading">Directing performance…</div> : plan && <div className="animation-script-form">
          <div className="animation-script-version"><span>CHARACTER STUDIO</span><strong>Plan {plan.version}</strong></div>
          <label className="wide">Character action<textarea value={plan.character_action} onChange={(event) => setPlan({ ...plan, character_action: event.target.value })} /></label>
          <label>Expression sequence<input value={plan.expression_sequence.join(", ")} onChange={(event) => setPlan({ ...plan, expression_sequence: list(event.target.value) })} /></label>
          <label>Pose sequence<input value={plan.pose_sequence.join(", ")} onChange={(event) => setPlan({ ...plan, pose_sequence: list(event.target.value) })} /></label>
          <div className="animation-script-performance wide">
            <div><span>PERFORMANCE SEQUENCE</span><small>Click a beat to remove it. Add methods from the library below.</small></div>
            <div className="animation-script-sequence" aria-label="Current performance sequence">
              {plan.pose_sequence.map((pose, index) => <button key={`${pose}-${index}`} type="button" onClick={() => removePerformanceBeat(index)}><b>{index + 1}</b>{performanceLabel(pose)}<i>×</i></button>)}
              {!plan.pose_sequence.length && <em>No performance beats selected</em>}
            </div>
            <div className="animation-script-methods" aria-label="Character animation methods">
              {PERFORMANCE_METHODS.map((method) => <button key={method} type="button" onClick={() => addPerformanceMethod(method)}>+ {performanceLabel(method)}</button>)}
            </div>
          </div>
          <figure className="animation-script-preview wide">
            <div><span>DIRECTED FRAME PREVIEW</span><small>Uses the saved poses, expressions, cinematic style, and scene timing.</small></div>
            <img key={previewUrl} src={previewUrl} alt="Directed Character Studio scene preview" />
          </figure>
          <label>Props<input value={plan.props.join(", ")} onChange={(event) => setPlan({ ...plan, props: list(event.target.value) })} /></label>
          <label className="wide">Camera direction<textarea value={plan.camera_direction} onChange={(event) => setPlan({ ...plan, camera_direction: event.target.value })} /></label>
          <label className="wide">Transition intention<input value={plan.transition_intention} onChange={(event) => setPlan({ ...plan, transition_intention: event.target.value })} /></label>
          <div className="animation-script-beats"><span>PERFORMANCE TIMING</span>{Object.entries(plan.animation_beats).map(([key, value]) => <label key={key}>{key}<input type="number" min="0" max="1" step="0.05" value={value} onChange={(event) => setPlan({ ...plan, animation_beats: { ...plan.animation_beats, [key]: Number(event.target.value) } })} /></label>)}</div>
        </div>}
        <footer><button className="secondary" disabled={busy || !sceneId} onClick={() => void regenerate()}>Regenerate from script</button><button className="secondary" disabled={busy || !plan} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button><button className="primary" disabled={busy || !plan} onClick={() => void saveAndPreview()}>{busy ? "Directing…" : "Save & preview"}</button></footer>
      </section>
    </div>}
  </>;
}
