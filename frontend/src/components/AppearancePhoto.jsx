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

  const commitFile = (jpeg, { force = false } = {}) => {
    if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
    const url = URL.createObjectURL(jpeg);
    setPreview(url);
    onPreview?.(url);
    onFile?.(jpeg, { force });
    setSaved(true);
    setPendingFile(null);
    setSoftWarn(null);
  };

  const applyFile = async (file) => {
    if (!file || busy) return;
    setError(null);
    setSoftWarn(null);
    setPendingFile(null);
    setBusy(true);
    setSaved(false);
    // P1.2: clear parent immediately so Search/Next cannot upload a stale prior file
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
        if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
        setPreview(null);
        return;
      }
      if (data.soft_warn) {
        setPendingFile(jpeg);
        setSoftWarn(data.message || data.issues?.[0] || "Are you sure this is a dog photo?");
        if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
        setPreview(URL.createObjectURL(jpeg));
        return;
      }
      commitFile(jpeg, { force: false });
    } catch (err) {
      setError(formatApiError(err, err.message || "Could not read that photo."));
      if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
      setPreview(null);
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
          <p className="appearance-soft-hint">Look photos are not biometric, but staff see them. Use a body or face shot of the dog when you can.</p>
          <div className="appearance-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => pendingFile && commitFile(pendingFile, { force: true })}
            >
              Use anyway
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => {
                setSoftWarn(null);
                setPendingFile(null);
                if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
                setPreview(null);
                clearParentFile();
              }}
            >
              Choose another
            </button>
          </div>
        </div>
      )}

      {!preview && !busy && !softWarn && (
        <p className="appearance-empty">No full-dog photo yet — optional but helps staff compare coat colour.</p>
      )}

      {error && <p className="appearance-error">{error}</p>}

      {!softWarn && (
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
    </div>
  );
}
