export type ProjectStatus =
  | "planning"
  | "research"
  | "script"
  | "storyboard"
  | "assets"
  | "timeline"
  | "complete";

export interface Project {
  id: number;
  title: string;
  topic: string;
  target_minutes: number;
  audience: string;
  tone: string;
  visual_style: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  topic: string;
  target_minutes: number;
  audience: string;
  tone: string;
  visual_style: string;
}
