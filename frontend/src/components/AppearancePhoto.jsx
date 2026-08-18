import { useEffect, useState } from "react";
import Icon from "./Icon";
import ProcessingOverlay from "./ProcessingOverlay";
import { toJpegFile } from "../utils/imageFile";
import "./AppearancePhoto.css";

export default function AppearancePhoto({
  title,
  help,
  onFile,
  onPreview,
  onBusyChange,
  existingUrl,
}) {
  const [preview, setPreview] = useState(existingUrl || null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(Boolean(existingUrl));

  useEffect(() => {
    onBusyChange?.(busy);
  }, [busy, onBusyChange]);

  useEffect(() => {
    return () => {
      if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const applyFile = async (file) => {
    if (!file || busy) return;
    setError(null);
    setBusy(true);
    setSaved(false);
    try {
      const jpeg = await toJpegFile(file, "dog-look.jpg");
      if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
      const url = URL.createObjectURL(jpeg);
      setPreview(url);
      onPreview?.(url);
      onFile(jpeg);
      setSaved(true);
    } catch (err) {
      setError(err.message || "Could not read that photo.");
    } finally {
      setBusy(false);
    }
  };

  const onChange = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    applyFile(file);
  };

  return (
    <div className="appearance-photo glass-card">
      {busy && (
        <ProcessingOverlay title="Reading photo…" detail="Preparing your dog photo" previewUrl={preview} />
      )}

      {title && <h3>{title}</h3>}
      {help && <p className="appearance-help">{help}</p>}

      {preview && (
        <div className="appearance-preview-wrap">
          <img className="appearance-preview" src={preview} alt="Dog appearance" />
          {saved && (
            <span className="appearance-saved">
              <Icon name="check" size={14} /> Photo ready — will be sent with your search
            </span>
          )}
        </div>
      )}

      {!preview && !busy && (
        <p className="appearance-empty">No full-dog photo yet — optional but helps staff compare coat colour.</p>
      )}

      {error && <p className="appearance-error">{error}</p>}

      <div className="appearance-actions">
        <label className={`btn btn-primary ${busy ? "disabled" : ""}`}>
          <input type="file" accept="image/*" capture="environment" onChange={onChange} hidden disabled={busy} />
          <Icon name="camera" size={16} /> Take photo
        </label>
        <label className={`btn btn-outline ${busy ? "disabled" : ""}`}>
          <input type="file" accept="image/*" onChange={onChange} hidden disabled={busy} />
          <Icon name="clipboard" size={16} /> Choose from gallery
        </label>
      </div>
    </div>
  );
}
