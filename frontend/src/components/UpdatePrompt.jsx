import { useEffect, useState } from "react";
import Icon from "./Icon";
import "./InstallPrompt.css";

/**
 * Shown when a new service-worker version is installed (production PWA only).
 * Dev / Cloudflare tunnel unregisters the worker so this does not run there.
 */
export default function UpdatePrompt() {
  const [waiting, setWaiting] = useState(false);

  useEffect(() => {
    if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return undefined;

    let regRef = null;
    const onControllerChange = () => window.location.reload();

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    navigator.serviceWorker.getRegistration().then((reg) => {
      if (!reg) return;
      regRef = reg;
      if (reg.waiting) setWaiting(true);
      reg.addEventListener("updatefound", () => {
        const worker = reg.installing;
        if (!worker) return;
        worker.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) {
            setWaiting(true);
          }
        });
      });
    });

    const id = setInterval(() => {
      regRef?.update().catch(() => {});
    }, 60_000);

    return () => {
      clearInterval(id);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  const apply = () => {
    navigator.serviceWorker.getRegistration().then((reg) => {
      reg?.waiting?.postMessage({ type: "SKIP_WAITING" });
      window.location.reload();
    });
  };

  if (!waiting) return null;

  return (
    <div className="install-banner">
      <div className="install-content">
        <div className="install-icon">
          <Icon name="refresh" size={20} />
        </div>
        <div className="install-text">
          <strong>App update available</strong>
          <span>New camera and upload tools are ready</span>
        </div>
      </div>
      <div className="install-actions">
        <button className="btn btn-primary btn-sm" type="button" onClick={apply}>
          Update
        </button>
      </div>
    </div>
  );
}
