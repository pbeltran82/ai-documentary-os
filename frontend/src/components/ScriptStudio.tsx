import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type {
  DocumentaryScript,
  NarrationManifest,
  ProjectDetail,
  ScriptSegment,
} from "../types";
import "./ScriptStudio.css";

type Props = {
  project: ProjectDetail;
  onBack: () => void;
  onOpenScenes: () => void;
  onProjectChanged: () => Promise<void>;
};

const voices = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"];

function cloneSegments(segments: ScriptSegment[]): ScriptSegment[] {
  return segments.map((segment) => ({ ...segment, search_keywords: [...segment.search_keywords] }));
}

export function ScriptStudio({ project, onBack, onOpenScenes, onProjectChanged }: Props) {
  const [script, setScript] = useState<DocumentaryScript | null>(null);
  const [segments, setSegments] = useState<ScriptSegment[]>([]);
  const [narration, setNarration] = useState<NarrationManifest | null>(null);
  const [provider, setProvider] = useState<"openai" | "local-outline">("openai");
  const [angle, setAngle] = useState("");
  const [researchNotes, setResearchNotes] = useState("");
  const [voice, setVoice] = useState("alloy");
  const [rate, setRate] = useState(1);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const completeCount = useMemo(
    () => narration?.segments.filter((item) => item.status === "complete").length ?? 0,
    [narration],
  );

  async function loadArtifacts() {
    setError("");
    const [scriptResult, narrationResult] = await Promise.allSettled([
      api.getProductionScript(project.id),
      api.getNarrationPlan(project.id),
    ]);
    if (scriptResult.status === "fulfilled") {
      setScript(scriptResult.value);
      setSegments(cloneSegments(scriptResult.value.segments));
      setAngle(scriptResult.value.angle ?? "");
    }
    if (narrationResult.status === "fulfilled") {
      setNarration(narrationResult.value);
      setVoice(narrationResult.value.voice_id);
      setRate(narrationResult.value.speaking_rate);
    }
  }

  useEffect(() => {
    void loadArtifacts();
  }, [project.id]);

  async function generateScript() {
    setBusy("generate");
    setError("");
    setMessage("");
    try {
      const generated = await api.generateProductionScript(project.id, {
        provider,
        angle,
        research_notes: researchNotes,
        target_scene_seconds: 8,
        replace_scenes: false,
      });
      setScript(generated);
      setSegments(cloneSegments(generated.segments));
      setMessage(`Draft revision ${generated.revision} generated.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate script");
    } finally {
      setBusy("");
    }
  }

  function updateSegment(index: number, patch: Partial<ScriptSegment>) {
    setSegments((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  async function saveDraft() {
    if (!script) return;
    setBusy("save");
    setError("");
    try {
      const saved = await api.updateProductionScript(project.id, {
        title: script.title,
        thesis: script.thesis,
        editor_notes: script.editor_notes ?? "",
        segments: segments.map((segment) => ({
          act: segment.act,
          narration: segment.narration,
          visual_intent: segment.visual_intent,
          search_keywords: segment.search_keywords,
        })),
        apply_to_scenes: false,
      });
      setScript(saved);
      setSegments(cloneSegments(saved.segments));
      setMessage(`Draft revision ${saved.revision} saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save draft");
    } finally {
      setBusy("");
    }
  }

  async function approveAndApply() {
    if (!script) return;
    setBusy("approve");
    setError("");
    try {
      await saveDraft();
      const approved = await api.approveProductionScript(project.id, {
        notes: "Approved in Script Studio",
      });
      setScript(approved);
      setSegments(cloneSegments(approved.segments));
      await api.updateProductionScript(project.id, {
        title: approved.title,
        thesis: approved.thesis,
        editor_notes: approved.editor_notes ?? "",
        segments: approved.segments.map((segment) => ({
          act: segment.act,
          narration: segment.narration,
          visual_intent: segment.visual_intent,
          search_keywords: segment.search_keywords,
        })),
        apply_to_scenes: true,
      });
      await onProjectChanged();
      setMessage("Script approved and applied to project scenes.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to approve script");
    } finally {
      setBusy("");
    }
  }

  async function planNarration() {
    setBusy("plan");
    setError("");
    try {
      const plan = await api.planNarration(project.id, {
        provider: "openai",
        voice_id: voice,
        speaking_rate: rate,
      });
      setNarration(plan);
      setMessage(`${plan.segment_count} narration segments planned.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to plan narration");
    } finally {
      setBusy("");
    }
  }

  async function synthesize(force = false) {
    setBusy("synthesize");
    setError("");
    try {
      const result = await api.synthesizeNarration(project.id, {
        scene_numbers: [],
        force,
        retime_scenes: true,
      });
      setNarration(result);
      await onProjectChanged();
      setMessage(`Narration ${result.status}. ${result.last_run.completed} completed, ${result.last_run.failed} failed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to synthesize narration");
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="workspace script-studio">
      <header className="topbar">
        <div>
          <p className="eyebrow">SCRIPT + NARRATION STUDIO</p>
          <h2>{project.title}</h2>
          <p>Generate, edit, approve, voice, and retime the documentary from one production desk.</p>
        </div>
        <div className="studio-actions">
          <button className="ghost-button" onClick={onBack}>Mission Control</button>
          <button className="ghost-button" onClick={onOpenScenes}>Open scenes</button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {message && <div className="studio-message">{message}</div>}

      <section className="panel studio-grid">
        <div>
          <p className="eyebrow">01 · WRITER</p>
          <h3>Generate the documentary draft</h3>
          <label>Writer provider
            <select value={provider} onChange={(event) => setProvider(event.target.value as typeof provider)}>
              <option value="openai">OpenAI documentary writer</option>
              <option value="local-outline">Local outline fallback</option>
            </select>
          </label>
          <label>Editorial angle
            <textarea rows={3} value={angle} onChange={(event) => setAngle(event.target.value)} />
          </label>
          <label>Verified research notes
            <textarea rows={7} value={researchNotes} onChange={(event) => setResearchNotes(event.target.value)} placeholder="Paste verified facts, source notes, dates, quotations, and constraints." />
          </label>
          <button className="primary-button" disabled={Boolean(busy)} onClick={() => void generateScript()}>
            {busy === "generate" ? "Writing…" : script ? "Regenerate draft" : "Generate draft"}
          </button>
        </div>

        <div className="studio-status-card">
          <p className="eyebrow">PRODUCTION STATUS</p>
          <strong>{script?.status ?? "No script"}</strong>
          <span>Revision {script?.revision ?? 0}</span>
          <span>{script?.word_count ?? 0} words</span>
          <span>{Math.round((script?.estimated_runtime_seconds ?? 0) / 60)} min estimated</span>
          <span>{narration ? `${completeCount}/${narration.segment_count} audio segments` : "Narration not planned"}</span>
        </div>
      </section>

      {script && (
        <>
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">02 · EDITOR</p>
                <h3>Review the story scene by scene</h3>
              </div>
              <div className="studio-actions">
                <button className="ghost-button" disabled={Boolean(busy)} onClick={() => void saveDraft()}>
                  {busy === "save" ? "Saving…" : "Save draft"}
                </button>
                <button className="primary-button" disabled={Boolean(busy)} onClick={() => void approveAndApply()}>
                  {busy === "approve" ? "Approving…" : "Approve + apply scenes"}
                </button>
              </div>
            </div>
            <div className="script-segment-list">
              {segments.map((segment, index) => (
                <article className="script-segment-card" key={segment.segment_id || index}>
                  <div className="segment-heading">
                    <span>Scene {index + 1}</span>
                    <input value={segment.act} onChange={(event) => updateSegment(index, { act: event.target.value })} />
                    <small>{segment.estimated_duration_seconds.toFixed(1)} sec</small>
                  </div>
                  <label>Narration
                    <textarea rows={5} value={segment.narration} onChange={(event) => updateSegment(index, { narration: event.target.value })} />
                  </label>
                  <label>Visual intent
                    <textarea rows={3} value={segment.visual_intent} onChange={(event) => updateSegment(index, { visual_intent: event.target.value })} />
                  </label>
                </article>
              ))}
            </div>
          </section>

          <section className="panel studio-grid">
            <div>
              <p className="eyebrow">03 · NARRATION</p>
              <h3>Choose the voice and synthesize</h3>
              <div className="voice-controls">
                <label>Voice
                  <select value={voice} onChange={(event) => setVoice(event.target.value)}>
                    {voices.map((item) => <option value={item} key={item}>{item}</option>)}
                  </select>
                </label>
                <label>Speaking rate
                  <input type="number" min={0.5} max={2} step={0.05} value={rate} onChange={(event) => setRate(Number(event.target.value))} />
                </label>
              </div>
              <div className="studio-actions">
                <button className="ghost-button" disabled={script.status !== "approved" || Boolean(busy)} onClick={() => void planNarration()}>
                  {busy === "plan" ? "Planning…" : "Plan narration"}
                </button>
                <button className="primary-button" disabled={!narration || Boolean(busy)} onClick={() => void synthesize(false)}>
                  {busy === "synthesize" ? "Synthesizing…" : "Synthesize pending"}
                </button>
                <button className="ghost-button" disabled={!narration || Boolean(busy)} onClick={() => void synthesize(true)}>
                  Regenerate all
                </button>
              </div>
            </div>
            <div className="narration-progress">
              <strong>{narration?.status ?? "Not planned"}</strong>
              {(narration?.segments ?? []).map((item) => (
                <div className={`audio-row ${item.status}`} key={item.segment_id}>
                  <span>Scene {item.scene_number}</span>
                  <span>{item.status}</span>
                  <span>{item.actual_duration_seconds ? `${item.actual_duration_seconds.toFixed(1)}s` : "—"}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
