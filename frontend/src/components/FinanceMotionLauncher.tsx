import { useEffect, useMemo, useState } from "react";
import "../finance-motion.css";
import "../batch-production.css";

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
type TemplateRecommendation = TemplateOption & {
  confidence: number;
  reason: string;
};
type StyleOption = {
  style_id: string;
  label: string;
  description: string;
  swatches: string[];
};
type FamilyOption = {
  family_id: string;
  label: string;
  description: string;
};
type FamilyRecommendation = FamilyOption & {
  confidence: number;
  reason: string;
};
type MotionSuggestion = {
  recommended_family: FamilyRecommendation;
  recommended: TemplateRecommendation;
  recommended_by_family: Record<string, TemplateRecommendation>;
  families: FamilyOption[];
  templates: TemplateOption[];
  templates_by_family: Record<string, TemplateOption[]>;
  styles: StyleOption[];
  default_style_id: string;
};
type StoryBeat = {
  label: string;
  description: string;
  time_seconds: number;
};
type Storyboard = {
  family_id: string;
  template_id: string;
  duration_seconds: number;
  beats: StoryBeat[];
};
type GeneratedAsset = {
  preview_url: string;
  download_url: string;
  license_name: string;
};
type BatchEntryStatus = "completed" | "skipped" | "failed";
type BatchEntry = {
  sceneId: number;
  sceneNumber: number;
  status: BatchEntryStatus;
  family: string;
  template: string;
  message: string;
};
type BatchProgress = {
  active: boolean;
  finished: boolean;
  total: number;
  processed: number;
  currentSceneNumber: number | null;
  currentFamily: string;
  currentTemplate: string;
  completed: number;
  skipped: number;
  failed: number;
  entries: BatchEntry[];
  finalizeError: string;
};

const EMPTY_BATCH: BatchProgress = {
  active: false,
  finished: false,
  total: 0,
  processed: 0,
  currentSceneNumber: null,
  currentFamily: "",
  currentTemplate: "",
  completed: 0,
  skipped: 0,
  failed: 0,
  entries: [],
  finalizeError: "",
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

function familyGlyph(familyId: string): string {
  if (familyId === "character_explainer") return "◯╱╲";
  if (familyId === "tech_behavior_motion") return "◎→◇";
  return "↗ 10%";
}

export function FinanceMotionLauncher() {
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [sceneId, setSceneId] = useState<number | null>(null);
  const [suggestion, setSuggestion] = useState<MotionSuggestion | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [familyId, setFamilyId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [styleId, setStyleId] = useState("");
  const [batchStyleId, setBatchStyleId] = useState("");
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [batch, setBatch] = useState<BatchProgress>(EMPTY_BATCH);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [generated, setGenerated] = useState<GeneratedAsset | null>(null);

  const scene = useMemo(
    () => project?.scenes.find((item) => item.id === sceneId) ?? null,
    [project, sceneId],
  );
  const selectedFamily = useMemo(
    () => suggestion?.families.find((item) => item.family_id === familyId) ?? null,
    [familyId, suggestion],
  );
  const selectedStyle = useMemo(
    () => suggestion?.styles.find((item) => item.style_id === styleId) ?? null,
    [suggestion, styleId],
  );
  const selectedTemplate = useMemo(
    () => suggestion?.templates_by_family[familyId]?.find((item) => item.template_id === templateId) ?? null,
    [familyId, suggestion, templateId],
  );
  const selectedRecommendation = useMemo(
    () => suggestion?.recommended_by_family[familyId] ?? null,
    [familyId, suggestion],
  );
  const visibleTemplates = useMemo(
    () => suggestion?.templates_by_family[familyId] ?? [],
    [familyId, suggestion],
  );
  const missingVisualCount = useMemo(
    () => project?.scenes.filter((item) => !item.selected_asset).length ?? 0,
    [project],
  );
  const batchStyle = useMemo(
    () => suggestion?.styles.find((item) => item.style_id === batchStyleId) ?? null,
    [batchStyleId, suggestion],
  );
  const batchPercent = batch.total ? Math.round((batch.processed / batch.total) * 100) : 0;
  const failedSceneIds = useMemo(
    () => batch.entries.filter((item) => item.status === "failed").map((item) => item.sceneId),
    [batch.entries],
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
    setBatch(EMPTY_BATCH);
    setBatchStyleId("");
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
    setStoryboard(null);
    setFamilyId("");
    setTemplateId("");
    void request<MotionSuggestion>(`/scenes/${sceneId}/finance-motion-suggestion`)
      .then((item) => {
        const recommendedFamily = item.recommended_family.family_id;
        setSuggestion(item);
        setFamilyId(recommendedFamily);
        setTemplateId(item.recommended_by_family[recommendedFamily]?.template_id ?? item.recommended.template_id);
        setStyleId((current) => current || item.default_style_id);
        setBatchStyleId((current) => current || item.default_style_id);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to direct exact visual"));
  }, [open, sceneId]);

  useEffect(() => {
    if (!open || !sceneId || !familyId || !templateId) return;
    setStoryboard(null);
    const parameters = new URLSearchParams({
      family_id: familyId,
      template_id: templateId,
    });
    void request<Storyboard>(`/scenes/${sceneId}/finance-motion-storyboard?${parameters.toString()}`)
      .then((item) => setStoryboard(item))
      .catch(() => setStoryboard(null));
  }, [familyId, open, sceneId, templateId]);

  function chooseFamily(nextFamilyId: string) {
    if (!suggestion) return;
    setFamilyId(nextFamilyId);
    setTemplateId(
      suggestion.recommended_by_family[nextFamilyId]?.template_id
        ?? suggestion.templates_by_family[nextFamilyId]?.[0]?.template_id
        ?? "",
    );
    setGenerated(null);
  }

  function storyboardFrameUrl(timeSeconds: number): string {
    if (!sceneId || !familyId || !templateId || !styleId) return "";
    const parameters = new URLSearchParams({
      family_id: familyId,
      template_id: templateId,
      style_id: styleId,
      time_seconds: String(timeSeconds),
    });
    return `${API}/scenes/${sceneId}/finance-motion-preview?${parameters.toString()}`;
  }

  async function generate() {
    if (!sceneId || !familyId || !templateId || !styleId) return;
    setBusy(true);
    setGenerated(null);
    setError("");
    try {
      const parameters = new URLSearchParams({
        family_id: familyId,
        template_id: templateId,
        style_id: styleId,
      });
      setGenerated(
        await request<GeneratedAsset>(
          `/scenes/${sceneId}/finance-motion?${parameters.toString()}`,
          { method: "POST" },
        ),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to generate exact visual");
    } finally {
      setBusy(false);
    }
  }

  async function runBatch(sceneIds?: number[], forceReplace = false) {
    if (!project || !projectId || !batchStyleId) return;
    const requestedIds = sceneIds ? new Set(sceneIds) : null;
    const scenes = project.scenes.filter((item) => !requestedIds || requestedIds.has(item.id));
    const shouldReplace = forceReplace || replaceExisting;
    let completed = 0;
    let skipped = 0;
    let failed = 0;
    const entries: BatchEntry[] = [];

    setError("");
    setGenerated(null);
    setBatch({
      ...EMPTY_BATCH,
      active: true,
      total: scenes.length,
    });

    for (let index = 0; index < scenes.length; index += 1) {
      const item = scenes[index];
      if (item.selected_asset && !shouldReplace) {
        skipped += 1;
        entries.push({
          sceneId: item.id,
          sceneNumber: item.scene_number,
          status: "skipped",
          family: "Existing visual",
          template: item.selected_asset.provider,
          message: "Skipped because a visual is already attached.",
        });
        setBatch((current) => ({
          ...current,
          processed: index + 1,
          skipped,
          entries: [...entries],
        }));
        continue;
      }

      setBatch((current) => ({
        ...current,
        currentSceneNumber: item.scene_number,
        currentFamily: "Directing scene…",
        currentTemplate: "Analyzing narration and visual intent",
      }));

      try {
        const directed = await request<MotionSuggestion>(`/scenes/${item.id}/finance-motion-suggestion`);
        const recommendedFamily = directed.recommended_family.family_id;
        const recommendedTemplate = directed.recommended_by_family[recommendedFamily] ?? directed.recommended;
        setBatch((current) => ({
          ...current,
          currentFamily: directed.recommended_family.label,
          currentTemplate: recommendedTemplate.label,
        }));

        const parameters = new URLSearchParams({
          family_id: recommendedFamily,
          template_id: recommendedTemplate.template_id,
          style_id: batchStyleId,
          defer_manifest: "true",
        });
        await request<GeneratedAsset>(
          `/scenes/${item.id}/finance-motion?${parameters.toString()}`,
          { method: "POST" },
        );
        completed += 1;
        entries.push({
          sceneId: item.id,
          sceneNumber: item.scene_number,
          status: "completed",
          family: directed.recommended_family.label,
          template: recommendedTemplate.label,
          message: `${batchStyle?.label ?? "Selected style"} visual generated and attached.`,
        });
      } catch (reason) {
        failed += 1;
        entries.push({
          sceneId: item.id,
          sceneNumber: item.scene_number,
          status: "failed",
          family: "Generation failed",
          template: "Needs review",
          message: reason instanceof Error ? reason.message : "Unable to generate this scene.",
        });
      }

      setBatch((current) => ({
        ...current,
        processed: index + 1,
        completed,
        skipped,
        failed,
        entries: [...entries],
      }));
    }

    let finalizeError = "";
    try {
      if (completed > 0) {
        await request(`/projects/${projectId}/exact-visual-batch/finalize`, { method: "POST" });
      }
      const refreshed = await request<ProjectDetail>(`/projects/${projectId}`);
      setProject(refreshed);
    } catch (reason) {
      finalizeError = reason instanceof Error ? reason.message : "Unable to finalize the project manifest.";
    }

    setBatch((current) => ({
      ...current,
      active: false,
      finished: true,
      currentSceneNumber: null,
      currentFamily: "",
      currentTemplate: "",
      completed,
      skipped,
      failed,
      entries: [...entries],
      finalizeError,
    }));
  }

  function dismissBatch() {
    setBatch(EMPTY_BATCH);
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
                <h2>Exact Visual Studio</h2>
                <span>Direct one scene or manufacture an entire rights-clean visual plan locally.</span>
              </div>
              <button aria-label="Close" disabled={batch.active} onClick={() => setOpen(false)}>×</button>
            </header>
            {error && <div className="finance-motion-error">{error}</div>}
            <div className="finance-motion-controls">
              <label>
                Project
                <select value={projectId ?? ""} disabled={batch.active} onChange={(event) => setProjectId(Number(event.target.value))}>
                  {projects.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}
                </select>
              </label>
              <div className="finance-motion-rule">
                <strong>Director rule</strong>
                <span>Human action gets a character. Money systems get finance motion. Algorithms get technology motion. Strong real footage remains valid.</span>
              </div>
            </div>
            {project?.scenes.length ? (
              <section className="batch-production-toolbar">
                <div>
                  <span>BATCH PRODUCTION CONSOLE</span>
                  <h3>Generate the project’s visual plan</h3>
                  <p>{missingVisualCount} of {project.scenes.length} scenes currently need visuals. Existing assets are protected by default.</p>
                </div>
                <label>
                  Project style
                  <select value={batchStyleId} disabled={batch.active} onChange={(event) => setBatchStyleId(event.target.value)}>
                    {suggestion?.styles.map((item) => <option value={item.style_id} key={item.style_id}>{item.label}</option>)}
                  </select>
                </label>
                <label className="batch-production-replace">
                  <input
                    type="checkbox"
                    checked={replaceExisting}
                    disabled={batch.active}
                    onChange={(event) => setReplaceExisting(event.target.checked)}
                  />
                  <span><strong>Replace existing visuals</strong><small>Regenerate every scene instead of filling only gaps.</small></span>
                </label>
                <button
                  className="batch-production-start"
                  disabled={busy || batch.active || !batchStyleId}
                  onClick={() => void runBatch()}
                >
                  <span>✦</span>
                  {replaceExisting ? "Regenerate all visuals" : "Generate all missing visuals"}
                </button>
              </section>
            ) : null}
            {busy && !project ? (
              <div className="finance-motion-empty">Loading production workspace…</div>
            ) : project?.scenes.length ? (
              <div className="finance-motion-layout">
                <aside className="finance-motion-scenes">
                  {project.scenes.map((item) => (
                    <button className={item.id === sceneId ? "active" : ""} key={item.id} disabled={batch.active} onClick={() => setSceneId(item.id)}>
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
                      <article className="exact-visual-family-recommendation">
                        <div>
                          <span>DIRECTOR FAMILY RECOMMENDATION</span>
                          <h3>{suggestion.recommended_family.label}</h3>
                          <p>{suggestion.recommended_family.description}</p>
                          <small>{suggestion.recommended_family.reason}</small>
                        </div>
                        <strong>{Math.round(suggestion.recommended_family.confidence * 100)}%</strong>
                      </article>

                      <div className="finance-motion-section-heading">
                        <div><span>VISUAL FAMILY</span><h3>Choose how the scene communicates</h3></div>
                        <p>The director preselects the strongest route, but every modular family remains available per scene.</p>
                      </div>
                      <div className="exact-visual-family-grid">
                        {suggestion.families.map((item) => (
                          <button
                            key={item.family_id}
                            className={item.family_id === familyId ? "active" : ""}
                            onClick={() => chooseFamily(item.family_id)}
                            aria-pressed={item.family_id === familyId}
                          >
                            <div>
                              <span>{familyGlyph(item.family_id)}</span>
                              {item.family_id === suggestion.recommended_family.family_id && <em>RECOMMENDED</em>}
                            </div>
                            <strong>{item.label}</strong>
                            <p>{item.description}</p>
                          </button>
                        ))}
                      </div>

                      {selectedRecommendation && (
                        <article className="finance-motion-recommendation">
                          <div><span>DIRECTOR COMPOSITION</span><h3>{selectedRecommendation.label}</h3><p>{selectedRecommendation.description}</p></div>
                          <strong>{Math.round(selectedRecommendation.confidence * 100)}%</strong>
                          <small>{selectedRecommendation.reason}</small>
                        </article>
                      )}

                      <div className="finance-motion-section-heading">
                        <div><span>HOUSE STYLE</span><h3>Choose the visual language</h3></div>
                        <p>All exact visual families support Clean, Premium, and Editorial art direction.</p>
                      </div>
                      <div className="finance-motion-style-grid">
                        {suggestion.styles.map((item) => (
                          <button
                            key={item.style_id}
                            className={item.style_id === styleId ? "active" : ""}
                            onClick={() => setStyleId(item.style_id)}
                            aria-pressed={item.style_id === styleId}
                          >
                            <div className="finance-motion-swatches" aria-hidden="true">
                              {item.swatches.map((swatch) => <i key={swatch} style={{ backgroundColor: swatch }} />)}
                            </div>
                            <strong>{item.label}</strong>
                            <span>{item.description}</span>
                          </button>
                        ))}
                      </div>

                      <div className="finance-motion-section-heading template-heading">
                        <div><span>COMPOSITION</span><h3>Choose the exact {selectedFamily?.label ?? "visual"} scene</h3></div>
                      </div>
                      <div className="finance-motion-template-grid">
                        {visibleTemplates.map((item) => (
                          <button key={item.template_id} className={item.template_id === templateId ? "active" : ""} onClick={() => setTemplateId(item.template_id)}>
                            <strong>{item.label}</strong><span>{item.description}</span>
                          </button>
                        ))}
                      </div>

                      {storyboard?.beats.length ? (
                        <article className="finance-motion-live-preview">
                          <div className="finance-motion-preview-copy">
                            <span>THREE-BEAT STORYBOARD</span>
                            <h3>{selectedTemplate?.label ?? "Exact visual"} · {selectedStyle?.label ?? "Art direction"}</h3>
                            <p>Review how the scene establishes the situation, animates the behavior or system, and lands on the result before rendering.</p>
                          </div>
                          <div className="finance-motion-storyboard">
                            {storyboard.beats.map((beat, index) => (
                              <figure key={`${beat.label}-${beat.time_seconds}`}>
                                <div><span>{String(index + 1).padStart(2, "0")}</span><strong>{beat.label}</strong></div>
                                <img src={storyboardFrameUrl(beat.time_seconds)} alt={`${beat.label} exact visual frame`} />
                                <figcaption>{beat.description}</figcaption>
                              </figure>
                            ))}
                          </div>
                        </article>
                      ) : null}

                      <button className="finance-motion-generate" disabled={busy || batch.active} onClick={() => void generate()}>
                        {busy ? `Rendering ${selectedFamily?.label ?? "exact"} 1080p visual…` : `Generate ${selectedStyle?.label ?? "art-directed"} ${selectedFamily?.label ?? "visual"}`}
                      </button>
                    </>
                  )}
                  {generated && (
                    <article className="finance-motion-success">
                      <video src={generated.download_url} poster={generated.preview_url} controls autoPlay muted loop />
                      <div><span>GENERATED AND ATTACHED</span><h3>{selectedFamily?.label ?? "Exact visual"} ready</h3><p>{generated.license_name}. The old timeline render was invalidated.</p><button onClick={() => window.location.reload()}>Reload workspace</button></div>
                    </article>
                  )}
                </main>
              </div>
            ) : (
              <div className="finance-motion-empty">Create a project with scenes before generating exact visuals.</div>
            )}
          </section>
        </div>
      )}

      {(batch.active || batch.finished) && (
        <div className="batch-production-overlay" role="dialog" aria-modal="true" aria-live="polite">
          <section className="batch-production-progress-card">
            <header>
              <div>
                <span>{batch.active ? "BATCH RENDER IN PROGRESS" : "BATCH PRODUCTION COMPLETE"}</span>
                <h2>{project?.title ?? "Exact visual project"}</h2>
                <p>{batch.active ? "Keep this tab open while local 1080p scenes are rendered and attached." : "Review the results before returning to the timeline."}</p>
              </div>
              <strong>{batchPercent}%</strong>
            </header>

            <div className="batch-production-progress-track" aria-label={`${batchPercent}% complete`}>
              <i style={{ width: `${batchPercent}%` }} />
            </div>

            <div className="batch-production-counts">
              <div><span>Completed</span><strong>{batch.completed}</strong></div>
              <div><span>Skipped</span><strong>{batch.skipped}</strong></div>
              <div><span>Failed</span><strong>{batch.failed}</strong></div>
              <div><span>Processed</span><strong>{batch.processed}/{batch.total}</strong></div>
            </div>

            {batch.active && batch.currentSceneNumber !== null ? (
              <article className="batch-production-current">
                <span>NOW RENDERING</span>
                <h3>Scene {String(batch.currentSceneNumber).padStart(2, "0")}</h3>
                <p>{batch.currentFamily}</p>
                <strong>{batch.currentTemplate}</strong>
                <small>{batchStyle?.label ?? "Project style"} · Local project-owned 1080p motion</small>
              </article>
            ) : null}

            <div className="batch-production-log">
              {batch.entries.length ? batch.entries.map((entry) => (
                <article className={entry.status} key={`${entry.sceneId}-${entry.status}`}>
                  <span>Scene {String(entry.sceneNumber).padStart(2, "0")}</span>
                  <div><strong>{entry.family}</strong><small>{entry.template}</small></div>
                  <p>{entry.message}</p>
                  <em>{entry.status}</em>
                </article>
              )) : <p className="batch-production-waiting">Directing the first scene…</p>}
            </div>

            {batch.finalizeError ? <div className="batch-production-finalize-error">Project finalization warning: {batch.finalizeError}</div> : null}

            <footer>
              {batch.active ? (
                <p>Scenes render sequentially to protect memory, files, and project state.</p>
              ) : (
                <>
                  {failedSceneIds.length ? (
                    <button className="batch-production-retry" onClick={() => void runBatch(failedSceneIds, true)}>Retry failed scenes</button>
                  ) : null}
                  <button className="batch-production-done" onClick={dismissBatch}>Review Exact Visual Studio</button>
                </>
              )}
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
