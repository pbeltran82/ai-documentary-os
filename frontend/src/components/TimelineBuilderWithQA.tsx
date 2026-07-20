import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { MediaQACheck, MediaQAReport, TimelineRenderedEventDetail } from "../mediaQaTypes";
import type { ProjectDetail } from "../types";
import { TimelineBuilder } from "./TimelineBuilder";
import "../media-qa.css";

interface TimelineBuilderWithQAProps {
  project: ProjectDetail;
  loading: boolean;
  error: string;
  onBack: () => void;
  onOpenAssets: () => void;
  onOpenScenes: () => void;
  onProjectChanged: () => Promise<void> | void;
}

const statusOrder: Record<MediaQACheck["status"], number> = {
  fail: 0,
  warn: 1,
  pass: 2,
};

function formatGeneratedAt(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatRuntime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds - minutes * 60;
  return `${minutes}:${remaining.toFixed(2).padStart(5, "0")}`;
}

function formatFps(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function statusLabel(status: MediaQACheck["status"]): string {
  if (status === "fail") return "FAIL";
  if (status === "warn") return "REVIEW";
  return "PASS";
}

export function TimelineBuilderWithQA(props: TimelineBuilderWithQAProps) {
  const { project } = props;
  const [report, setReport] = useState<MediaQAReport | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState("");

  const orderedChecks = useMemo(
    () => report?.checks.slice().sort((left, right) => statusOrder[left.status] - statusOrder[right.status]) ?? [],
    [report],
  );

  async function loadLatestReport() {
    setQaError("");
    try {
      setReport(await api.getTimelineQA(project.id));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load release QA";
      if (message.includes("No media QA report exists")) {
        setReport(null);
        return;
      }
      setQaError(message);
    }
  }

  async function runQA() {
    setQaLoading(true);
    setQaError("");
    try {
      setReport(await api.runTimelineQA(project.id));
    } catch (err) {
      setQaError(err instanceof Error ? err.message : "Unable to run release QA");
    } finally {
      setQaLoading(false);
    }
  }

  useEffect(() => {
    setReport(null);
    void loadLatestReport();
  }, [project.id, project.updated_at]);

  useEffect(() => {
    const rendered = (event: Event) => {
      const detail = (event as CustomEvent<TimelineRenderedEventDetail>).detail;
      if (detail?.projectId !== project.id) return;
      if (detail.qaReport) {
        setReport(detail.qaReport);
        setQaError("");
      } else {
        void runQA();
      }
    };
    const invalidated = (event: Event) => {
      const projectId = Number((event as CustomEvent<{ projectId?: number }>).detail?.projectId);
      if (projectId !== project.id) return;
      setReport(null);
      setQaError("");
    };
    window.addEventListener("atlas:timeline-rendered", rendered);
    window.addEventListener("atlas:timeline-qa-invalidated", invalidated);
    return () => {
      window.removeEventListener("atlas:timeline-rendered", rendered);
      window.removeEventListener("atlas:timeline-qa-invalidated", invalidated);
    };
  }, [project.id]);

  return (
    <div className="timeline-qa-shell">
      <TimelineBuilder {...props} />
      <div className="media-qa-dock">
        <section className={`panel media-qa-panel ${report ? report.verdict.toLowerCase() : "pending"}`}>
          <div className="section-heading media-qa-heading">
            <div>
              <p className="eyebrow">AUTOMATIC RELEASE QA</p>
              <h3>Software checks for the rendered first cut</h3>
              <p className="media-qa-intro">
                Every render is inspected for delivery format, runtime, black frames, frozen holds,
                repeated adjacent scenes, audio safety, and audio/video synchronization.
              </p>
            </div>
            <div className="media-qa-actions">
              {report && <span className={`media-qa-verdict ${report.verdict.toLowerCase()}`}>{report.verdict}</span>}
              <button className="secondary-button" disabled={qaLoading} onClick={() => void runQA()}>
                {qaLoading ? "Running release QA…" : report ? "Run QA again" : "Run release QA"}
              </button>
            </div>
          </div>

          {qaError && <div className="error-banner">{qaError}</div>}

          {!report ? (
            <div className="media-qa-empty">
              <strong>No release report yet</strong>
              <p>Render the timeline and QA will run automatically. The manual action can inspect any existing first cut.</p>
            </div>
          ) : (
            <>
              <div className="media-qa-summary-grid" aria-label="Release QA summary">
                <article><span>Verdict</span><strong>{report.verdict}</strong></article>
                <article><span>Checks passed</span><strong>{report.summary.passed}</strong></article>
                <article><span>Needs review</span><strong>{report.summary.warnings}</strong></article>
                <article><span>Failures</span><strong>{report.summary.failures}</strong></article>
                <article><span>Runtime</span><strong>{formatRuntime(report.render.container_duration_seconds)}</strong></article>
                <article><span>Delivery</span><strong>{report.render.width}×{report.render.height} · {formatFps(report.render.fps)} fps</strong></article>
              </div>

              <div className={`media-qa-summary-message ${report.verdict.toLowerCase()}`}>
                <strong>{report.summary.message}</strong>
                <span>Generated {formatGeneratedAt(report.generated_at)}</span>
              </div>

              <div className="media-qa-checks">
                {orderedChecks.map((check) => (
                  <article className={`media-qa-check ${check.status}`} key={check.id}>
                    <div>
                      <span className="media-qa-check-label">{check.label}</span>
                      <strong>{check.details}</strong>
                    </div>
                    <span className={`media-qa-check-status ${check.status}`}>{statusLabel(check.status)}</span>
                  </article>
                ))}
              </div>

              <div className="media-qa-footer">
                <p>Automated QA protects technical release quality. Final story, pacing, and taste still receive human review.</p>
                <a href={report.report_url} target="_blank" rel="noreferrer">Open QA evidence JSON</a>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
