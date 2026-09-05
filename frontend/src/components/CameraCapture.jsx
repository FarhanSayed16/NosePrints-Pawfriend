import { useRef, useState, useCallback, useEffect } from "react";
import Icon from "./Icon";
import "./CameraCapture.css";

function analyzeFrame(video) {
  if (!video.videoWidth) return null;
  const w = 160;
  const h = Math.max(8, Math.round((video.videoHeight / video.videoWidth) * w));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(video, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);
  const gray = new Float32Array(w * h);
  let sum = 0;
  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    const g = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    gray[p] = g;
    sum += g;
  }
  const brightness = sum / gray.length;
  let acc = 0;
  let n = 0;
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const idx = y * w + x;
      const lap = gray[idx - 1] + gray[idx + 1] + gray[idx - w] + gray[idx + w] - 4 * gray[idx];
      acc += lap * lap;
      n++;
    }
  }
  return { sharpness: acc / Math.max(1, n), brightness };
}

/** Client-side blur/brightness only — never used to auto-shutter (no nose ML in-browser). */
const SHARPNESS_OK = 80;
const BRIGHTNESS_MIN = 50;
const BRIGHTNESS_MAX = 210;

function hintFromStats(stats) {
  // Blur/brightness only — never claim a nose was found (server checks after crop).
  if (!stats) return "Fill the circle with the nose leather, then tap shutter";
  if (stats.brightness < BRIGHTNESS_MIN) return "Too dark — add light on the nose";
  if (stats.brightness > BRIGHTNESS_MAX) return "Too bright — reduce glare on the nose";
  if (stats.sharpness < SHARPNESS_OK) return "Hold steady — image is blurry";
  return "Focus OK — fill the circle with the nose (not fur or body), then tap shutter";
}

export default function CameraCapture({
  onCapture,
  mode = "single",
  showFilePicker = true,
  autoStart = false,
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const onCaptureRef = useRef(onCapture);
  const capturingRef = useRef(false);

  const [isActive, setIsActive] = useState(false);
  const [capturedImages, setCapturedImages] = useState([]);
  const [error, setError] = useState(null);
  const [facingMode, setFacingMode] = useState("environment");
  const [hint, setHint] = useState("Fill the circle with the nose, then tap the shutter");
  const [qualityOk, setQualityOk] = useState(false);

  const maxPhotos = mode === "multi" ? 5 : 1;
  const minPhotos = mode === "multi" ? 3 : 1;

  useEffect(() => {
    onCaptureRef.current = onCapture;
  }, [onCapture]);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      capturingRef.current = false;
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera API not available. Use HTTPS and a current browser.");
      }
      const attempts = [
        {
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        },
        { video: { facingMode: { ideal: facingMode } }, audio: false },
        { video: true, audio: false },
      ];
      let stream;
      let lastErr;
      for (const constraints of attempts) {
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          break;
        } catch (err) {
          lastErr = err;
        }
      }
      if (!stream) throw lastErr || new Error("Could not open camera");
      streamRef.current = stream;
      // Video node is only in the DOM after isActive — attach in the effect below.
      setIsActive(true);
    } catch (err) {
      console.error("Camera error:", err);
      setError(
        err.name === "NotAllowedError"
          ? "Camera permission denied. Please allow camera access to scan nose prints."
          : err.message || "Could not access camera. Please check your device settings."
      );
    }
  }, [facingMode]);

  const stopCamera = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsActive(false);
    setQualityOk(false);
  }, []);

  useEffect(() => {
    if (!isActive) return undefined;
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return undefined;
    video.srcObject = stream;
    video.muted = true;
    const play = () => {
      const p = video.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
    };
    if (video.readyState >= 1) play();
    video.addEventListener("loadedmetadata", play);
    return () => video.removeEventListener("loadedmetadata", play);
  }, [isActive]);

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || capturingRef.current) return;
    capturingRef.current = true;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        capturingRef.current = false;
        if (!blob) return;
        const file = new File([blob], `nose-${Date.now()}.jpg`, { type: "image/jpeg" });
        if (mode === "multi") {
          setCapturedImages((prev) => {
            const updated = [...prev, file];
            if (updated.length >= maxPhotos) {
              stopCamera();
            }
            return updated;
          });
        } else {
          setCapturedImages([file]);
          onCaptureRef.current?.(file);
          stopCamera();
        }
      },
      "image/jpeg",
      0.95
    );
  }, [mode, maxPhotos, stopCamera]);

  const toggleCamera = () => {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };

  const submitMultiCapture = () => {
    if (capturedImages.length >= minPhotos) {
      onCaptureRef.current?.(capturedImages);
      stopCamera();
    }
  };

  const resetCapture = () => {
    setCapturedImages([]);
    startCamera();
  };

  const onFilePick = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    const images = files.filter((f) => f.type.startsWith("image/") || !f.type);
    if (!images.length) return;
    const named = images.map(
      (f, i) => (f instanceof File ? f : new File([f], `pick-${i}.jpg`, { type: f.type || "image/jpeg" }))
    );
    if (mode === "multi") {
      setCapturedImages((prev) => [...prev, ...named].slice(0, maxPhotos));
      stopCamera();
    } else {
      onCaptureRef.current?.(named[0]);
      stopCamera();
    }
  };

  // Quality hints only — never auto-capture. A laptop screen or random sharp frame
  // used to trip shutter after ~0.6–2s; user must tap the shutter deliberately.
  useEffect(() => {
    if (!isActive) return undefined;
    const id = setInterval(() => {
      const video = videoRef.current;
      if (!video || video.readyState < 2) return;
      const stats = analyzeFrame(video);
      setHint(hintFromStats(stats));
      setQualityOk(
        Boolean(
          stats &&
            stats.sharpness >= SHARPNESS_OK &&
            stats.brightness >= BRIGHTNESS_MIN &&
            stats.brightness <= BRIGHTNESS_MAX
        )
      );
    }, 250);
    return () => clearInterval(id);
  }, [isActive]);

  useEffect(() => {
    if (isActive) {
      stopCamera();
      startCamera();
    }
    // Restart only when the user flips cameras
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  useEffect(() => () => stopCamera(), [stopCamera]);

  // One entry: Camera tab opens live view (permission still requires user gesture on some browsers)
  useEffect(() => {
    if (autoStart && !isActive && !error && capturedImages.length === 0) {
      startCamera();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  return (
    <div className="camera-capture">
      {error && (
        <div className="camera-error glass-card">
          <div className="error-icon">
            <Icon name="alertCircle" size={24} />
          </div>
          <p>{error}</p>
          <button className="btn btn-primary btn-sm" onClick={startCamera}>
            Try Again
          </button>
        </div>
      )}

      {!isActive && !error && capturedImages.length === 0 && (
        <div className="camera-start glass-card" onClick={startCamera}>
          <div className="camera-start-icon">
            <Icon name="camera" size={32} />
          </div>
          <h3>{autoStart ? "Starting camera…" : "Open camera"}</h3>
          <p>Tap if the live view does not open — you take the photo when ready</p>
        </div>
      )}

      {isActive && (
        <div className="camera-preview">
          <video
            ref={videoRef}
            className="camera-video"
            autoPlay
            muted
            playsInline
            webkit-playsinline="true"
          />
          <div className="camera-overlay">
            <div className="nose-guide">
              <div className={`guide-circle ${qualityOk ? "guide-focus-ok" : ""}`}></div>
              <p className={`guide-text ${qualityOk ? "hint-focus-ok" : ""}`}>{hint}</p>
            </div>
          </div>
          <div className="camera-controls">
            <button className="btn btn-outline btn-sm" type="button" onClick={toggleCamera}>
              <Icon name="refresh" size={14} /> Flip
            </button>
            <button
              className="capture-btn"
              type="button"
              onClick={captureFrame}
              aria-label="Take nose photo"
              title="Take photo"
            >
              <span className="capture-ring"></span>
            </button>
            <button className="btn btn-outline btn-sm" type="button" onClick={stopCamera}>
              <Icon name="x" size={14} /> Close
            </button>
          </div>
          {mode === "multi" && (
            <div className="capture-counter">
              {capturedImages.length} / {maxPhotos} photos
            </div>
          )}
        </div>
      )}

      {mode === "multi" && capturedImages.length > 0 && (
        <div className="captured-preview">
          <div className="captured-grid">
            {capturedImages.map((blob, idx) => (
              <div key={idx} className="captured-thumb">
                <img src={URL.createObjectURL(blob)} alt={`Capture ${idx + 1}`} />
                <span className="thumb-number">{idx + 1}</span>
              </div>
            ))}
          </div>
          <div className="captured-actions">
            <button className="btn btn-outline btn-sm" type="button" onClick={resetCapture}>
              <Icon name="refresh" size={14} /> Retake All
            </button>
            {capturedImages.length >= minPhotos && (
              <button className="btn btn-primary" type="button" onClick={submitMultiCapture}>
                <Icon name="check" size={16} /> Submit {capturedImages.length} Photos
              </button>
            )}
            {capturedImages.length < minPhotos && isActive && (
              <p className="capture-hint">
                Need at least {minPhotos} photos ({minPhotos - capturedImages.length} more)
              </p>
            )}
          </div>
        </div>
      )}

      {showFilePicker && (
      <label className="camera-file-fallback">
        <input
          type="file"
          accept="image/*"
          multiple={mode === "multi"}
          onChange={onFilePick}
        />
        Or pick photos from this phone
      </label>
      )}

      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}
