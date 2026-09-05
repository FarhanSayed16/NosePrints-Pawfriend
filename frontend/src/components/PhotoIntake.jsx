import { useEffect, useRef, useState } from "react";
import CameraCapture from "./CameraCapture";
import NoseCropEditor from "./NoseCropEditor";
import ProcessingOverlay from "./ProcessingOverlay";
import Icon from "./Icon";
import { detectNosePreview } from "../services/api";
import { formatCaptureError, toJpegFile } from "../utils/imageFile";
import "./PhotoIntake.css";

const PHASE = {
  IDLE: "idle",
  PREPARING: "preparing",
  DETECTING: "detecting",
  CROPPING: "cropping",
};

export default function PhotoIntake({ onCapture, mode = "single" }) {
  const [tab, setTab] = useState("camera");
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [error, setError] = useState(null);
  const [cropSrc, setCropSrc] = useState(null);
  const [cropBox, setCropBox] = useState(null);
  const [cropMsg, setCropMsg] = useState("");
  const [pending, setPending] = useState([]); // { blob, url }
  const [pickPreview, setPickPreview] = useState(null);
  const pendingUrlsRef = useRef([]);

  const maxPhotos = mode === "multi" ? 5 : 1;
  const minPhotos = mode === "multi" ? 3 : 1;
  const busy = phase !== PHASE.IDLE && phase !== PHASE.CROPPING;

  useEffect(() => {
    return () => {
      pendingUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      pendingUrlsRef.current = [];
    };
  }, []);

  const emit = (blobs, preCropped) => {
    onCapture(blobs, { preCropped });
  };

  const addBlob = (blob) => {
    if (mode === "single") {
      emit(blob, true);
      return;
    }
    const url = URL.createObjectURL(blob);
    pendingUrlsRef.current.push(url);
    setPending((prev) => [...prev, { blob, url }].slice(0, maxPhotos));
    setPhase(PHASE.IDLE);
    setPickPreview(null);
  };

  const submitPending = () => {
    if (pending.length < minPhotos) return;
    emit(
      pending.map((p) => p.blob),
      true,
    );
  };

  const openCrop = async (file) => {
    setError(null);
    setPhase(PHASE.PREPARING);
    const thumb = URL.createObjectURL(file);
    setPickPreview(thumb);

    let jpeg;
    try {
      jpeg = await toJpegFile(file, "upload.jpg");
    } catch (err) {
      URL.revokeObjectURL(thumb);
      setPickPreview(null);
      setPhase(PHASE.IDLE);
      setError(err.message || "Could not read that photo.");
      return;
    }

    URL.revokeObjectURL(thumb);
    const url = URL.createObjectURL(jpeg);
    setPickPreview(url);
    setPhase(PHASE.DETECTING);

    let bbox = null;
    let message = "Drag the box onto the nose leather — not the eyes or whole head.";
    try {
      const res = await detectNosePreview(jpeg);
      bbox = res.data.bbox || null;
      if (res.data.message) message = res.data.message;
    } catch (err) {
      message =
        "Auto-detect did not respond — drag the box onto the nose yourself. " +
        formatCaptureError(err, "");
    }

    setCropSrc(url);
    setCropBox(bbox);
    setCropMsg(message);
    setPickPreview(null);
    setPhase(PHASE.CROPPING);
  };

  const onUpload = (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files[0] || busy) return;
    openCrop(files[0]);
  };

  const confirmCrop = (blob) => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    setCropBox(null);
    setTab("upload");
    addBlob(blob);
  };

  const cancelCrop = () => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    setCropBox(null);
    setPhase(PHASE.IDLE);
  };

  const overlayTitle =
    phase === PHASE.PREPARING ? "Reading your photo…" : "Finding the nose…";
  const overlayDetail =
    phase === PHASE.PREPARING
      ? "Resizing for upload"
      : "This may take a few seconds on mobile";

  return (
    <div className="photo-intake">
      {busy && (
        <ProcessingOverlay title={overlayTitle} detail={overlayDetail} previewUrl={pickPreview} />
      )}

      <div className="intake-tabs">
        <button
          type="button"
          className={tab === "camera" ? "active" : ""}
          disabled={busy || phase === PHASE.CROPPING}
          onClick={() => setTab("camera")}
        >
          <Icon name="camera" size={16} /> Camera
        </button>
        <button
          type="button"
          className={tab === "upload" ? "active" : ""}
          disabled={busy || phase === PHASE.CROPPING}
          onClick={() => setTab("upload")}
        >
          <Icon name="clipboard" size={16} /> Gallery
        </button>
      </div>

      {error && (
        <div className="intake-error-banner" role="alert">
          <Icon name="alertCircle" size={18} />
          <span>{error}</span>
        </div>
      )}

      {phase === PHASE.CROPPING && cropSrc && (
        <NoseCropEditor
          imageUrl={cropSrc}
          initialBox={cropBox}
          message={cropMsg}
          onConfirm={confirmCrop}
          onCancel={cancelCrop}
        />
      )}

      {phase === PHASE.IDLE && tab === "camera" && (
        <CameraCapture
          onCapture={(blobs) => {
            // Always open the crop editor (same as gallery). Never accept a raw
            // camera frame as the final nose print — auto-shutter used to skip this.
            const file = Array.isArray(blobs) ? blobs[0] : blobs;
            if (file) openCrop(file);
          }}
          mode="single"
          showFilePicker={false}
        />
      )}

      {phase === PHASE.IDLE && tab === "upload" && (
        <div className="upload-pane glass-card">
          <p>
            Pick a close-up of the nose, or a face photo. Drag the box onto the{" "}
            <strong>nose leather</strong> — not the eyes or the whole head.
          </p>
          <div className="upload-actions">
            <label className="btn btn-primary">
              <input type="file" accept="image/*" capture="environment" onChange={onUpload} hidden />
              <Icon name="camera" size={16} /> Take photo
            </label>
            <label className="btn btn-outline">
              <input type="file" accept="image/*" onChange={onUpload} hidden />
              <Icon name="clipboard" size={16} /> Choose from gallery
            </label>
          </div>
        </div>
      )}

      {mode === "multi" && pending.length > 0 && phase !== PHASE.CROPPING && (
        <div className="pending-prints glass-card">
          <div className="pending-header">
            <Icon name="checkBadge" size={18} />
            <strong>
              {pending.length} nose crop{pending.length !== 1 ? "s" : ""} saved
            </strong>
          </div>
          <div className="captured-grid">
            {pending.map((item, idx) => (
              <div key={idx} className="captured-thumb saved">
                <img src={item.url} alt={`Nose ${idx + 1}`} />
                <span className="thumb-number">{idx + 1}</span>
              </div>
            ))}
          </div>
          <p className="capture-hint">
            {pending.length < minPhotos
              ? `Add ${minPhotos - pending.length} more (${pending.length}/${minPhotos} minimum)`
              : `${pending.length} ready to upload`}
          </p>
          {pending.length >= minPhotos && (
            <button className="btn btn-primary" type="button" onClick={submitPending}>
              Upload {pending.length} nose photos
            </button>
          )}
          {pending.length < maxPhotos && (
            <button
              className="btn btn-outline btn-sm add-more-btn"
              type="button"
              onClick={() => setTab("upload")}
            >
              <Icon name="camera" size={14} /> Add another crop
            </button>
          )}
        </div>
      )}
    </div>
  );
}
