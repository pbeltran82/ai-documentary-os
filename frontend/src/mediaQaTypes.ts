export type MediaQAStatus = "pass" | "warn" | "fail";
export type MediaQAVerdict = "PASS" | "HOLD";

export interface MediaQACheck {
  id: string;
  label: string;
  status: MediaQAStatus;
  severity: "minor" | "major" | "blocker";
  details: string;
  metrics: Record<string, unknown>;
}

export interface MediaQASummary {
  passed: number;
  warnings: number;
  failures: number;
  message: string;
}

export interface MediaQARenderMetadata {
  container_duration_seconds: number;
  video_duration_seconds: number;
  audio_duration_seconds: number | null;
  width: number;
  height: number;
  fps: number;
  frame_count: number;
  video_codec: string;
  pixel_format: string;
  audio_codec: string | null;
  audio_sample_rate: number | null;
  has_video: boolean;
  has_audio: boolean;
  size_bytes: number;
}

export interface MediaQAReport {
  schema_version: string;
  generated_at: string;
  project_id: number;
  project_title: string;
  video_format: "youtube" | "shorts";
  verdict: MediaQAVerdict;
  summary: MediaQASummary;
  render: MediaQARenderMetadata;
  checks: MediaQACheck[];
  black_segments: Array<Record<string, number>>;
  freeze_segments: Array<Record<string, number>>;
  repeated_scene_pairs: Array<Record<string, unknown>>;
  report_relative_path: string;
  report_url: string;
}

export interface TimelineRenderedEventDetail {
  projectId: number;
  qaReport: MediaQAReport | null;
}
