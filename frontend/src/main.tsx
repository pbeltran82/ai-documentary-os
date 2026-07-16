import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AnimationScriptLauncher } from "./components/AnimationScriptLauncher";
import { FinanceMotionLauncher } from "./components/FinanceMotionLauncher";
import "./styles.css";
import "./asset-planner.css";
import "./provider-hub.css";
import "./visual-director.css";
import "./timeline-builder.css";
import "./narration.css";
import "./finance-motion-composition.css";
import "./character-explainer.css";
import "./release-v140.css";
import "./release-v150.css";
import "./release-v160.css";
import "./release-v170.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
    <AnimationScriptLauncher />
    <FinanceMotionLauncher />
  </StrictMode>,
);
