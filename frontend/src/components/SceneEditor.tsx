import { useEffect, useState } from "react";
import type { AssetStatus, AssetType, Scene, SceneUpdate } from "../types";

interface SceneEditorProps {
  scene: Scene;
  saving: boolean;
  onSave: (sceneId: number, payload: SceneUpdate) => Promise<void>;
  onDelete: (scene: Scene) => Promise<void>;
}

const assetTypes: Array<{ value: AssetType; label: string }> = [
  { value: "stock_video", label: "Stock video" },
  { value: "stock_image", label: "Stock image" },
  { value: "ai_image", label: "AI image" },
  { value: "ai_video", label: "AI video" },
  { value: "chart", label: "Chart / graphic" },
  { value: "text_animation", label: "Text animation" },
];

const assetStatuses: Array<{ value: AssetStatus; label: string }> = [
  { value: "missing", label: "Missing" },
  { value: "searching", label: "Searching" },
  { value: "selected", label: "Selected" },
  { value: "ready", label: "Ready" },
];

function formatTimestamp(seconds: number): string {
  const wholeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(wholeSeconds / 60);
  const remaining = wholeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

export function SceneEditor({ scene, saving, onSave, onDelete }: SceneEditorProps) {
  const [draft, setDraft] = useState({
    narration: scene.narration,
    duration_seconds: scene.duration_seconds,
    visual_intent: scene.visual_intent,
    keywords: scene.search_keywords.join(", "),
    preferred_asset_type: scene.preferred_asset_type,
    asset_status: scene.asset_status,
  });

  useEffect(() => {
    setDraft({
      narration: scene.narration,
      duration_seconds: scene.duration_seconds,
      visual_intent: scene.visual_intent,
      keywords: scene.search_keywords.join(", "),
      preferred_asset_type: scene.preferred_asset_type,
      asset_status: scene.asset_status,
    });
  }, [scene]);

  const isDirty =
    draft.narration !== scene.narration ||
    draft.duration_seconds !== scene.duration_seconds ||
    draft.visual_intent !== scene.visual_intent ||
    draft.keywords !== scene.search_keywords.join(", ") ||
    draft.preferred_asset_type !== scene.preferred_asset_type ||
    draft.asset_status !== scene.asset_status;

  async function save() {
    await onSave(scene.id, {
      narration: draft.narration,
      duration_seconds: Number(draft.duration_seconds),
      visual_intent: draft.visual_intent,
      search_keywords: draft.keywords
        .split(",")
        .map((keyword) => keyword.trim())
        .filter(Boolean),
      preferred_asset_type: draft.preferred_asset_type,
      asset_status: draft.asset_status,
    });
  }

  return (
    <article className="scene-card">
      <div className="scene-card-header">
        <div>
          <p className="eyebrow">SCENE {String(scene.scene_number).padStart(2, "0")}</p>
          <strong className="scene-time">
            {formatTimestamp(scene.start_seconds)}–{formatTimestamp(scene.end_seconds)}
          </strong>
        </div>
        <span className={`asset-status ${scene.asset_status}`}>{scene.asset_status}</span>
      </div>

      <label>
        Narration
        <textarea
          rows={3}
          value={draft.narration}
          onChange={(event) => setDraft({ ...draft, narration: event.target.value })}
        />
      </label>

      <div className="scene-fields-grid">
        <label>
          Duration
          <div className="input-with-suffix compact">
            <input
              type="number"
              min={1}
              max={60}
              step={0.1}
              value={draft.duration_seconds}
              onChange={(event) =>
                setDraft({ ...draft, duration_seconds: Number(event.target.value) })
              }
            />
            <span>sec</span>
          </div>
        </label>

        <label>
          Preferred visual
          <select
            value={draft.preferred_asset_type}
            onChange={(event) =>
              setDraft({ ...draft, preferred_asset_type: event.target.value as AssetType })
            }
          >
            {assetTypes.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label>
          Asset status
          <select
            value={draft.asset_status}
            onChange={(event) =>
              setDraft({ ...draft, asset_status: event.target.value as AssetStatus })
            }
          >
            {assetStatuses.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      </div>

      <label>
        Visual intent
        <textarea
          rows={2}
          value={draft.visual_intent}
          onChange={(event) => setDraft({ ...draft, visual_intent: event.target.value })}
        />
      </label>

      <label>
        Search keywords
        <input
          value={draft.keywords}
          placeholder="compound interest, calendar, investing"
          onChange={(event) => setDraft({ ...draft, keywords: event.target.value })}
        />
      </label>

      <div className="scene-actions">
        <button className="danger-button" type="button" onClick={() => void onDelete(scene)}>
          Delete
        </button>
        <button
          className="secondary-button"
          type="button"
          disabled={!isDirty || saving}
          onClick={() => void save()}
        >
          {saving ? "Saving…" : isDirty ? "Save scene" : "Saved"}
        </button>
      </div>
    </article>
  );
}
