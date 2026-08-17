import { useRef, useState, useCallback, useEffect } from "react";
import "./CameraCapture.css";

/**
 * CameraCapture — Uses getUserMedia to capture nose-print photos.
 * Provides a live video preview with a guide overlay and auto-capture hints.
 *
 * @param {function} onCapture - Called with the captured image Blob
 * @param {string} mode - "single" for one photo, "multi" for 3-5 photos
 */
export default function CameraCapture({ onCapture, mode = "single" }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [isActive, setIsActive] = useState(false);
  const [capturedImages, setCapturedImages] = useState([]);
  const [error, setError] = useState(null);
  const [facingMode, setFacingMode] = useState("environment"); // rear camera

  const maxPhotos = mode === "multi" ? 5 : 1;
  const minPhotos = mode === "multi" ? 3 : 1;

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: facingMode,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsActive(true);
    } catch (err) {
      console.error("Camera error:", err);
      setError(
        err.name === "NotAllowedError"
          ? "Camera permission denied. Please allow camera access to scan nose prints."
          : "Could not access camera. Please check your device settings."
      );
    }
  }, [facingMode]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsActive(false);
  }, []);

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;

        if (mode === "multi") {
          setCapturedImages((prev) => {
            const updated = [...prev, blob];
            if (updated.length >= maxPhotos) {
              stopCamera();
            }
            return updated;
          });
        } else {
          setCapturedImages([blob]);
          onCapture?.(blob);
          stopCamera();
        }
      },
      "image/jpeg",
      0.92
    );
  }, [mode, maxPhotos, onCapture, stopCamera]);

  const toggleCamera = () => {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };

  const submitMultiCapture = () => {
    if (capturedImages.length >= minPhotos) {
      onCapture?.(capturedImages);
      stopCamera();
    }
  };

  const resetCapture = () => {
    setCapturedImages([]);
    startCamera();
  };

  // Restart camera when facing mode changes
  useEffect(() => {
    if (isActive) {
      stopCamera();
      startCamera();
    }
  }, [facingMode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  return (
    <div className="camera-capture">
      {error && (
        <div className="camera-error glass-card">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button className="btn btn-primary btn-sm" onClick={startCamera}>
            Try Again
          </button>
        </div>
      )}

      {!isActive && !error && capturedImages.length === 0 && (
        <div className="camera-start glass-card" onClick={startCamera}>
          <div className="camera-start-icon">📸</div>
          <h3>Open Camera</h3>
          <p>Tap to start scanning the dog's nose</p>
        </div>
      )}

      {isActive && (
        <div className="camera-preview">
          <video ref={videoRef} playsInline muted className="camera-video" />

          {/* Guide overlay */}
          <div className="camera-overlay">
            <div className="nose-guide">
              <div className="guide-circle"></div>
              <p className="guide-text">Align the nose inside the circle</p>
            </div>
            <div className="scan-line"></div>
          </div>

          {/* Controls */}
          <div className="camera-controls">
            <button className="btn btn-outline btn-sm" onClick={toggleCamera}>
              🔄 Flip
            </button>
            <button className="capture-btn" onClick={captureFrame}>
              <span className="capture-ring"></span>
            </button>
            <button className="btn btn-outline btn-sm" onClick={stopCamera}>
              ✕ Close
            </button>
          </div>

          {/* Multi-capture counter */}
          {mode === "multi" && (
            <div className="capture-counter">
              {capturedImages.length} / {maxPhotos} photos
            </div>
          )}
        </div>
      )}

      {/* Captured images preview (multi mode) */}
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
            <button className="btn btn-outline btn-sm" onClick={resetCapture}>
              ↻ Retake All
            </button>
            {capturedImages.length >= minPhotos && (
              <button
                className="btn btn-primary"
                onClick={submitMultiCapture}
              >
                ✓ Submit {capturedImages.length} Photos
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

      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}
