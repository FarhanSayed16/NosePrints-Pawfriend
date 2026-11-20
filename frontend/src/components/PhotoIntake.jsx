import { useEffect, useRef, useState } from "react";
import CameraCapture from "./CameraCapture";
import NoseCropEditor from "./NoseCropEditor";
import ProcessingOverlay from "./ProcessingOverlay";
import Icon from "./Icon";
import { checkImageQuality, detectNosePreview, formatApiError } from "../services/api";
import { blobCacheKey, formatCaptureError, toJpegFile } from "../utils/imageFile";
import "./PhotoIntake.css";

const PHASE = {
  IDLE: "idle",
  PREPARING: "preparing",
  DETECTING: "detecting",
  VALIDATING: "validating",
  CROPPING: "cropping",
};

const qualityCache = new Map();

export default function PhotoIntake({ onCapture, mode = "single", onCroppingChange }) {
  const [tab, setTab] = useState("camera");
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [error, setError] = useState(null);
  const [rejectFlash, setRejectFlash] = useState(null);
  const [cropSrc, setCropSrc] = useState(null);
  const [cropBox, setCropBox] = useState(null);
  const [cropMsg, setCropMsg] = useState("");
  const [pending, setPending] = useState([]); // { blob, url }
  const [pickPreview, setPickPreview] = useState(null);
  const [inlineStatus, setInlineStatus] = useState("");
  const pendingUrlsRef = useRef([]);
  const lastDetectRef = useRef(null); // { key, bbox, message }
  const rejectTimerRef = useRef(null);

  const clearIntakeError = () => {
    setError(null);
    setRejectFlash(null);
    if (rejectTimerRef.current) {
      clearTimeout(rejectTimerRef.current);
      rejectTimerRef.current = null;
    }
  };

  const showRejectOnce = (message) => {
    // Never leave a sticky red banner on the idle camera (confused field screenshots).
    // Soft hint only — clears when user Flip/shutter/tab or starts a new crop.
    if (rejectTimerRef.current) clearTimeout(rejectTimerRef.current);
    setError(null);
    setRejectFlash(message);
    rejectTimerRef.current = setTimeout(() => {
      setRejectFlash(null);
      rejectTimerRef.current = null;
    }, 20000);
  };

  useEffect(() => {
    return () => {
      if (rejectTimerRef.current) clearTimeout(rejectTimerRef.current);
    };
  }, []);

  const maxPhotos = mode === "multi" ? 5 : 1;
  const minPhotos = mode === "multi" ? 3 : 1;
  const heavyBusy = phase === PHASE.PREPARING || phase === PHASE.DETECTING;
  const validating = phase === PHASE.VALIDATING;

  useEffect(() => {
    onCroppingChange?.(phase === PHASE.CROPPING);
  }, [phase, onCroppingChange]);

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
    setInlineStatus("");
    setPickPreview(null);
  };

  const removePending = (idx) => {
    setPending((prev) => {
      const next = [...prev];
      const [removed] = next.splice(idx, 1);
      if (removed?.url) {
        URL.revokeObjectURL(removed.url);
        pendingUrlsRef.current = pendingUrlsRef.current.filter((u) => u !== removed.url);
      }
      return next;
    });
  };

  const submitPending = () => {
    if (pending.length < minPhotos) return;
    emit(
      pending.map((p) => p.blob),
      true,
    );
  };

  /** Server nose gate before treating a crop as queued (stops “saved” junk UI). */
  const validateAndQueue = async (blob) => {
    setError(null);
    setPhase(PHASE.VALIDATING);
    setInlineStatus("Checking crop…");
    const key = blobCacheKey(blob);
    try {
      if (qualityCache.has(key)) {
        const cached = qualityCache.get(key);
        if (!cached.passed) {
          showRejectOnce(cached.message);
          setPhase(PHASE.IDLE);
          setInlineStatus("");
          return;
        }
        addBlob(blob);
        return;
      }
      const res = await checkImageQuality(blob, { preCropped: true });
      if (!res.data?.passed) {
        const issues = Array.isArray(res.data?.issues)
          ? res.data.issues.filter((x) => typeof x === "string" && x.trim())
          : [];
        const message =
          issues[0] ||
          "That crop did not look like nose leather. Pinch until ONLY the wet black/pink leather fills the circle, then try again.";
        qualityCache.set(key, { passed: false, message });
        showRejectOnce(message);
        setPhase(PHASE.IDLE);
        setInlineStatus("");
        return;
      }
      qualityCache.set(key, { passed: true, message: "" });
      addBlob(blob);
    } catch (err) {
      showRejectOnce(formatCaptureError(err, formatApiError(err, "Could not verify this nose crop.")));
      setPhase(PHASE.IDLE);
      setInlineStatus("");
    }
  };

  const openCrop = async (file) => {
    clearIntakeError();
    setRejectFlash(null);
    setInlineStatus("");
    setPhase(PHASE.PREPARING);
    const thumb = URL.createObjectURL(file);
    setPickPreview(thumb);

    const fileKey = blobCacheKey(file);
    const cachedDetect = lastDetectRef.current?.key === fileKey ? lastDetectRef.current : null;

    // Parallel: JPEG for crop stage + detect-preview (lighter JPEG for detect when no cache)
    let jpeg;
    let detectRes = null;
    try {
      const jpegPromise = toJpegFile(file, "upload.jpg", { quality: 0.85 });
      const detectPromise = cachedDetect
        ? Promise.resolve(null)
        : toJpegFile(file, "detect.jpg", { maxEdge: 1280, quality: 0.72 }).then((previewJpeg) =>
            detectNosePreview(previewJpeg),
          );

      setPhase(PHASE.DETECTING);
      const [jpegOut, detectOut] = await Promise.all([jpegPromise, detectPromise]);
      jpeg = jpegOut;
      detectRes = detectOut;
    } catch (err) {
      URL.revokeObjectURL(thumb);
      setPickPreview(null);
      setPhase(PHASE.IDLE);
      setError(err.message || formatCaptureError(err, "Could not read that photo."));
      return;
    }

    URL.revokeObjectURL(thumb);
    const url = URL.createObjectURL(jpeg);
    setPickPreview(url);

    let bbox = cachedDetect?.bbox ?? null;
    let message =
      cachedDetect?.message ||
      "Pinch until ONLY the wet black/pink nose leather fills the circle — not eyes or the whole head.";

    if (detectRes) {
      try {
        // Keep suggested bbox even when detected=false (user still needs a starting box).
        bbox = detectRes.data.bbox || null;
        if (detectRes.data.detected) {
          message =
            detectRes.data.message ||
            "Nose found — pinch until ONLY leather fills the circle, then confirm.";
        } else {
          message =
            detectRes.data.message ||
            "No clear nose — pinch a tight box until ONLY the wet leather fills the circle.";
        }
        lastDetectRef.current = { key: fileKey, bbox, message };
      } catch {
        message =
          "Auto-detect did not respond — pinch until ONLY the nose leather fills the circle.";
      }
    } else if (!cachedDetect) {
      message =
        "Auto-detect did not respond — pinch until ONLY the nose leather fills the circle.";
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
    if (!files[0] || heavyBusy || validating) return;
    openCrop(files[0]);
  };

  const confirmCrop = (blob) => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    setCropBox(null);
    setTab("camera");
    validateAndQueue(blob);
  };

  const cancelCrop = () => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    setCropBox(null);
    clearIntakeError();
    setRejectFlash(null);
    setPhase(PHASE.IDLE);
  };

  const overlayTitle = phase === PHASE.PREPARING ? "Reading photo…" : "Finding the nose…";
  const overlayDetail =
    phase === PHASE.PREPARING ? "Preparing for crop" : "You can adjust the box next";

  return (
    <div className="photo-intake">
      {heavyBusy && (
        <ProcessingOverlay title={overlayTitle} detail={overlayDetail} previewUrl={pickPreview} />
      )}

      {phase !== PHASE.CROPPING && (
        <div className="intake-tabs">
          <button
            type="button"
            className={tab === "camera" ? "active" : ""}
            disabled={heavyBusy || validating}
            onClick={() => {
              clearIntakeError();
              setTab("camera");
            }}
          >
            <Icon name="camera" size={16} /> Camera
          </button>
          <button
            type="button"
            className={tab === "gallery" ? "active" : ""}
            disabled={heavyBusy || validating}
            onClick={() => {
              clearIntakeError();
              setTab("gallery");
            }}
          >
            <Icon name="clipboard" size={16} /> Gallery
          </button>
        </div>
      )}

      {error && (
        <div className="intake-error-banner" role="alert">
          <Icon name="alertCircle" size={18} />
          <span>{error}</span>
        </div>
      )}

      {!error && rejectFlash && phase === PHASE.IDLE && (
        <p className="intake-reject-hint" role="status">
          {rejectFlash}
        </p>
      )}

      {validating && inlineStatus && (
        <p className="intake-inline-status" role="status">
          {inlineStatus}
        </p>
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
            const file = Array.isArray(blobs) ? blobs[0] : blobs;
            if (file) openCrop(file);
          }}
          onUserEngage={clearIntakeError}
          mode="single"
          showFilePicker={false}
          autoStart
        />
      )}

      {phase === PHASE.IDLE && tab === "gallery" && (
        <div className="upload-pane glass-card">
          <p>
            Pick a nose photo. Pinch until <strong>ONLY the wet black/pink leather</strong> fills
            the circle — not eyes, muzzle, or whole head.
          </p>
          <div className="upload-actions">
            <label className={`btn btn-primary ${heavyBusy || validating ? "disabled" : ""}`}>
              <input
                type="file"
                accept="image/*"
                onChange={onUpload}
                hidden
                disabled={heavyBusy || validating}
              />
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
              {pending.length} crop{pending.length !== 1 ? "s" : ""} passed the nose check
            </strong>
          </div>
          <p className="capture-hint pending-hint">
            These passed a quick server check. Final save happens when you upload.
          </p>
          <div className="captured-grid">
            {pending.map((item, idx) => (
              <div key={idx} className="captured-thumb saved">
                <img src={item.url} alt={`Nose ${idx + 1}`} />
                <span className="thumb-number">{idx + 1}</span>
                <button
                  type="button"
                  className="thumb-remove"
                  aria-label={`Remove crop ${idx + 1}`}
                  onClick={() => removePending(idx)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <p className="capture-hint">
            {pending.length < minPhotos
              ? `Need ${minPhotos - pending.length} more good crop${minPhotos - pending.length !== 1 ? "s" : ""} (${pending.length}/${minPhotos})`
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
              onClick={() => setTab("camera")}
            >
              <Icon name="camera" size={14} /> Add another crop
            </button>
          )}
        </div>
      )}
    </div>
  );
}
