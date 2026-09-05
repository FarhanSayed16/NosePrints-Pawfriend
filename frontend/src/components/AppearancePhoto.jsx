import { useEffect, useState } from "react";
import Icon from "./Icon";
import ProcessingOverlay from "./ProcessingOverlay";
import { checkLookPhoto, formatApiError } from "../services/api";
import { toJpegFile } from "../utils/imageFile";
import "./AppearancePhoto.css";

export default function AppearancePhoto({
  title,
  help,
  onFile,
  onPreview,
  onBusyChange,
  existingUrl,
  softGate = true,
  readyLabel = "Photo ready",
}) {
  const [preview, setPreview] = useState(existingUrl || null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(Boolean(existingUrl));
  const [pendingFile, setPendingFile] = useState(null);
  const [softWarn, setSoftWarn] = useState(null);

  useEffect(() => {
    onBusyChange?.(busy);
  }, [busy, onBusyChange]);

  useEffect(() => {
    return () => {
      if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const clearParentFile = () => {
    onFile?.(null, { force: false });
    onPreview?.(null);
  };

  const setPreviewUrl = (url) => {
    if (preview && preview.startsWith("blob:") && preview !== url) {
      URL.revokeObjectURL(preview);
    }
    setPreview(url);
  };

  const commitFile = (jpeg, { force = false } = {}) => {
    const url = URL.createObjectURL(jpeg);
    setPreviewUrl(url);
    onPreview?.(url);
    onFile?.(jpeg, { force });
    setSaved(true);
    setPendingFile(null);
    setSoftWarn(null);
    setError(null);
  };

  const applyFile = async (file) => {
    if (!file || busy) return;
    setError(null);
    setSoftWarn(null);
    setPendingFile(null);
    setSaved(false);
    setBusy(true);
    clearParentFile();
    try {
      const jpeg = await toJpegFile(file, "dog-look.jpg");
      if (!softGate) {
        commitFile(jpeg, { force: false });
        return;
      }
      const res = await checkLookPhoto(jpeg);
      const data = res.data;
      if (!data.ok) {
        setError(data.message || data.issues?.[0] || "This photo was rejected.");
        setPreviewUrl(null);
        return;
      }
      // Always show preview for soft_warn, but never mark ready / commit until Use anyway
      const url = URL.createObjectURL(jpeg);
      setPreviewUrl(url);
      if (data.soft_warn) {
        setPendingFile(jpeg);
        setSoftWarn(data.message || data.issues?.[0] || "Are you sure this is a dog photo?");
        return;
      }
      onPreview?.(url);
      onFile?.(jpeg, { force: false });
      setSaved(true);
      setPendingFile(null);
      setSoftWarn(null);
    } catch (err) {
      setError(formatApiError(err, err.message || "Could not read that photo."));
      setPreviewUrl(null);
    } finally {
      setBusy(false);
    }
  };

  const onChange = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    applyFile(file);
  };

  const clearAll = () => {
    setSoftWarn(null);
    setPendingFile(null);
    setSaved(false);
    setPreviewUrl(null);
    clearParentFile();
  };

  return (
    <div className="appearance-photo glass-card">
      {busy && (
        <ProcessingOverlay title="Checking photo…" detail="Making sure this looks like a dog" previewUrl={preview} />
      )}

      {title && <h3>{title}</h3>}
      {help && <p className="appearance-help">{help}</p>}

      {preview && (
        <div className="appearance-preview-wrap">
          <img className="appearance-preview" src={preview} alt="Dog appearance" />
          {saved && !softWarn && (
            <span className="appearance-saved">
              <Icon name="check" size={14} /> {readyLabel}
            </span>
          )}
        </div>
      )}

      {softWarn && (
        <div className="appearance-soft-warn">
          <p><Icon name="alertCircle" size={16} /> {softWarn}</p>
          <p className="appearance-soft-hint">
            Look photos are not biometric, but staff see them. Prefer a body or face shot of the dog.
          </p>
          <div className="appearance-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => pendingFile && commitFile(pendingFile, { force: true })}
            >
              Use anyway
            </button>
            <button type="button" className="btn btn-outline" onClick={clearAll}>
              Choose another
            </button>
          </div>
        </div>
      )}

      {!preview && !busy && !softWarn && (
        <p className="appearance-empty">No full-dog photo yet — optional but helps staff compare coat colour.</p>
      )}

      {error && <p className="appearance-error">{error}</p>}

      {!softWarn && !saved && (
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
      )}

      {!softWarn && saved && (
        <div className="appearance-actions">
          <label className={`btn btn-outline ${busy ? "disabled" : ""}`}>
            <input type="file" accept="image/*" onChange={onChange} hidden disabled={busy} />
            <Icon name="clipboard" size={16} /> Change photo
          </label>
        </div>
      )}
    </div>
  );
}
