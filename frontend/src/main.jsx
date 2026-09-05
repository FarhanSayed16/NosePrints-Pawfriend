import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

async function setupServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  // Dev + tunnel preview: an installed SW caches old bundles so phones never see fixes.
  const disableSw =
    import.meta.env.DEV ||
    import.meta.env.VITE_DISABLE_SW === "1" ||
    import.meta.env.MODE === "tunnel";

  if (disableSw) {
    const regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(regs.map((r) => r.unregister()));
    if (window.caches) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
    return;
  }

  const reg = await navigator.serviceWorker.register("/sw.js");
  reg.update().catch(() => {});
}

window.addEventListener("load", () => {
  setupServiceWorker().catch((err) => {
    console.warn("Service worker setup failed:", err);
  });
});

const rootEl = document.getElementById("root");
try {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
} catch (err) {
  console.error(err);
  if (rootEl) {
    rootEl.innerHTML =
      "<p style=\"font-family:sans-serif;padding:2rem;color:#b91c1c\">NosePrints failed to start. Hard-refresh this tab (Ctrl+Shift+R) or open it in Incognito.</p>";
  }
}
