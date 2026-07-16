import { useEffect, useState } from "react";

function completionButton(): HTMLButtonElement | null {
  return document.querySelector<HTMLButtonElement>(
    ".batch-production-overlay .batch-production-done",
  );
}

export function BatchExitGuard() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const sync = () => setVisible(Boolean(completionButton()));
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    sync();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && completionButton()) {
        event.preventDefault();
        completionButton()?.click();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      className="batch-exit-guard"
      onClick={() => completionButton()?.click()}
    >
      <span aria-hidden="true">×</span>
      Return to Exact Visual Studio
    </button>
  );
}
