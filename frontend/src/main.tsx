import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./asset-planner.css";
import "./provider-hub.css";
import "./visual-director.css";
import "./timeline-builder.css";
import "./narration.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
