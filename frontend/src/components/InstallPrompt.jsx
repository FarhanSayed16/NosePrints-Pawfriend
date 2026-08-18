import { useEffect, useState } from "react";
import Icon from "./Icon";
import "./InstallPrompt.css";

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showBanner, setShowBanner] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [showIOSTip, setShowIOSTip] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    // Detect iOS Safari
    const ua = navigator.userAgent;
    const isiOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
    setIsIOS(isiOS);

    // Don't re-show if user dismissed recently
    const dismissed = localStorage.getItem("pwa-dismiss");
    if (dismissed && Date.now() - Number(dismissed) < 7 * 24 * 60 * 60 * 1000) return;

    // Android / Chrome: listen for beforeinstallprompt
    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowBanner(true);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // iOS: show tip after a few seconds if not installed
    let iosTimer;
    if (isiOS) {
      iosTimer = setTimeout(() => setShowIOSTip(true), 5000);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      clearTimeout(iosTimer);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setShowBanner(false);
    }
    setDeferredPrompt(null);
  };

  const dismiss = () => {
    setShowBanner(false);
    setShowIOSTip(false);
    localStorage.setItem("pwa-dismiss", String(Date.now()));
  };

  if (!showBanner && !showIOSTip) return null;

  return (
    <div className="install-banner">
      <div className="install-content">
        <div className="install-icon">
          <Icon name="paw" size={20} />
        </div>
        <div className="install-text">
          {isIOS ? (
            <>
              <strong>Add NosePrints to Home Screen</strong>
              <span>Tap <strong>Share</strong> → <strong>Add to Home Screen</strong></span>
            </>
          ) : (
            <>
              <strong>Install NosePrints</strong>
              <span>Quick access from your home screen</span>
            </>
          )}
        </div>
      </div>
      <div className="install-actions">
        {!isIOS && (
          <button className="btn btn-primary btn-sm" onClick={handleInstall}>
            Install
          </button>
        )}
        <button className="install-dismiss" onClick={dismiss} aria-label="Dismiss">
          <Icon name="x" size={16} />
        </button>
      </div>
    </div>
  );
}
