import { useEffect, useRef, useState } from "react";
import { toJpegFile } from "../utils/imageFile";
import "./NoseCropEditor.css";

const MIN_NORM = 0.05;
const MIN_PX_SOFT = 96;
const CORNER_HANDLES = ["nw", "ne", "se", "sw"];
const EDGE_HANDLES = ["n", "e", "s", "w"];
const NUDGE = 0.018;

function defaultBox() {
  return { x1: 0.38, y1: 0.32, x2: 0.62, y2: 0.56 };
}

function clampBox(next) {
  const x1 = Math.min(Math.max(0, next.x1), 1 - MIN_NORM);
  const y1 = Math.min(Math.max(0, next.y1), 1 - MIN_NORM);
  const x2 = Math.max(Math.min(1, next.x2), x1 + MIN_NORM);
  const y2 = Math.max(Math.min(1, next.y2), y1 + MIN_NORM);
  return { x1, y1, x2, y2 };
}

export default function NoseCropEditor({ imageUrl, initialBox, message, onConfirm, onCancel }) {
  const imgRef = useRef(null);
  const frameRef = useRef(null);
  const [box, setBox] = useState(initialBox || defaultBox());
  const [preview, setPreview] = useState(null);
  const [warn, setWarn] = useState("");
  const [confirming, setConfirming] = useState(false);
  const dragRef = useRef(null);
  const pinchRef = useRef(null);
  const previewTimer = useRef(null);
  const boxRef = useRef(box);
  boxRef.current = box;

  const found = Boolean(message && /nose found/i.test(message));

  useEffect(() => {
    setBox(initialBox || defaultBox());
  }, [initialBox, imageUrl]);

  const clientToNorm = (clientX, clientY) => {
    const frame = frameRef.current;
    const rect = frame.getBoundingClientRect();
    return {
      x: (clientX - rect.left) / Math.max(rect.width, 1),
      y: (clientY - rect.top) / Math.max(rect.height, 1),
    };
  };

  const applyHandle = (orig, handle, dx, dy) => {
    const next = { ...orig };
    if (handle === "move") {
      const w = orig.x2 - orig.x1;
      const h = orig.y2 - orig.y1;
      let x1 = orig.x1 + dx;
      let y1 = orig.y1 + dy;
      x1 = Math.min(Math.max(0, x1), 1 - w);
      y1 = Math.min(Math.max(0, y1), 1 - h);
      return { x1, y1, x2: x1 + w, y2: y1 + h };
    }
    if (handle.includes("w")) next.x1 = orig.x1 + dx;
    if (handle.includes("e")) next.x2 = orig.x2 + dx;
    if (handle.includes("n")) next.y1 = orig.y1 + dy;
    if (handle.includes("s")) next.y2 = orig.y2 + dy;
    return clampBox(next);
  };

  const beginDrag = (event, handle) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const p = clientToNorm(event.clientX, event.clientY);
    dragRef.current = { handle, start: p, orig: { ...boxRef.current } };

    const onMove = (ev) => {
      if (!dragRef.current) return;
      const cur = clientToNorm(ev.clientX, ev.clientY);
      const { handle: h, start, orig } = dragRef.current;
      setBox(applyHandle(orig, h, cur.x - start.x, cur.y - start.y));
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };

  const scaleBox = (factor) => {
    setBox((current) => {
      const cx = (current.x1 + current.x2) / 2;
      const cy = (current.y1 + current.y2) / 2;
      const w = Math.max(MIN_NORM, (current.x2 - current.x1) * factor);
      const h = Math.max(MIN_NORM, (current.y2 - current.y1) * factor);
      return clampBox({
        x1: cx - w / 2,
        y1: cy - h / 2,
        x2: cx + w / 2,
        y2: cy + h / 2,
      });
    });
  };

  const nudge = (dx, dy) => {
    setBox((current) => applyHandle(current, "move", dx, dy));
  };

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;

    const distance = (t1, t2) => Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);

    const onTouchStart = (ev) => {
      if (ev.touches.length === 2) {
        pinchRef.current = {
          startDist: distance(ev.touches[0], ev.touches[1]),
          orig: { ...boxRef.current },
        };
      }
    };
    const onTouchMove = (ev) => {
      if (ev.touches.length !== 2 || !pinchRef.current) return;
      ev.preventDefault();
      const dist = distance(ev.touches[0], ev.touches[1]);
      const factor = dist / Math.max(pinchRef.current.startDist, 1);
      const orig = pinchRef.current.orig;
      const cx = (orig.x1 + orig.x2) / 2;
      const cy = (orig.y1 + orig.y2) / 2;
      const w = Math.max(MIN_NORM, (orig.x2 - orig.x1) * factor);
      const h = Math.max(MIN_NORM, (orig.y2 - orig.y1) * factor);
      setBox(
        clampBox({
          x1: cx - w / 2,
          y1: cy - h / 2,
          x2: cx + w / 2,
          y2: cy + h / 2,
        }),
      );
    };
    const onTouchEnd = () => {
      pinchRef.current = null;
    };

    frame.addEventListener("touchstart", onTouchStart, { passive: true });
    frame.addEventListener("touchmove", onTouchMove, { passive: false });
    frame.addEventListener("touchend", onTouchEnd);
    frame.addEventListener("touchcancel", onTouchEnd);
    return () => {
      frame.removeEventListener("touchstart", onTouchStart);
      frame.removeEventListener("touchmove", onTouchMove);
      frame.removeEventListener("touchend", onTouchEnd);
      frame.removeEventListener("touchcancel", onTouchEnd);
    };
  }, []);

  useEffect(() => {
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(() => {
      const img = imgRef.current;
      if (!img || !img.naturalWidth) return;
      const canvas = document.createElement("canvas");
      const sx = box.x1 * img.naturalWidth;
      const sy = box.y1 * img.naturalHeight;
      const sw = (box.x2 - box.x1) * img.naturalWidth;
      const sh = (box.y2 - box.y1) * img.naturalHeight;
      canvas.width = 120;
      canvas.height = 120;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, 120, 120);
      setPreview(canvas.toDataURL("image/jpeg", 0.72));
      const fracW = sw / img.naturalWidth;
      const fracH = sh / img.naturalHeight;
      if (Math.min(sw, sh) < MIN_PX_SOFT) {
        setWarn("Box is small — enlarge so the nose leather fills most of it.");
      } else if (fracW > 0.42 || fracH > 0.42) {
        setWarn("Still too wide — tighten onto the black/pink nose only (not eyes or muzzle).");
      } else {
        setWarn("");
      }
    }, 80);
    return () => clearTimeout(previewTimer.current);
  }, [box, imageUrl]);

  const confirm = async () => {
    if (confirming) return;
    setConfirming(true);
    try {
      const img = imgRef.current;
      const canvas = document.createElement("canvas");
      const sx = box.x1 * img.naturalWidth;
      const sy = box.y1 * img.naturalHeight;
      const sw = (box.x2 - box.x1) * img.naturalWidth;
      const sh = (box.y2 - box.y1) * img.naturalHeight;
      canvas.width = Math.max(1, Math.round(sw));
      canvas.height = Math.max(1, Math.round(sh));
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
      const file = await toJpegFile(blob, "nose-crop.jpg", { quality: 0.92 });
      onConfirm(file);
    } catch {
      setWarn("Could not create crop — try again.");
      setConfirming(false);
    }
  };

  const style = {
    left: `${box.x1 * 100}%`,
    top: `${box.y1 * 100}%`,
    width: `${(box.x2 - box.x1) * 100}%`,
    height: `${(box.y2 - box.y1) * 100}%`,
  };

  const dim = {
    top: { left: 0, top: 0, right: 0, height: `${box.y1 * 100}%` },
    bottom: { left: 0, top: `${box.y2 * 100}%`, right: 0, bottom: 0 },
    left: { left: 0, top: `${box.y1 * 100}%`, width: `${box.x1 * 100}%`, height: `${(box.y2 - box.y1) * 100}%` },
    right: { left: `${box.x2 * 100}%`, top: `${box.y1 * 100}%`, right: 0, height: `${(box.y2 - box.y1) * 100}%` },
  };

  return (
    <div className="crop-editor">
      <div className={`crop-banner ${found ? "ok" : "assist"}`}>
        <strong>{found ? "Nose found — fine-tune if needed" : "Frame the nose leather"}</strong>
        <span>{message || "Drag the box onto the black/pink nose only — not eyes or the whole head."}</span>
      </div>

      <div className="crop-stage">
        <div className="crop-frame" ref={frameRef}>
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Uploaded dog"
            draggable={false}
            onLoad={() => setBox((current) => ({ ...current }))}
          />
          <div className="crop-dim" style={dim.top} onPointerDown={(e) => beginDrag(e, "move")} />
          <div className="crop-dim" style={dim.bottom} onPointerDown={(e) => beginDrag(e, "move")} />
          <div className="crop-dim" style={dim.left} onPointerDown={(e) => beginDrag(e, "move")} />
          <div className="crop-dim" style={dim.right} onPointerDown={(e) => beginDrag(e, "move")} />
          <div className="crop-box" style={style} onPointerDown={(e) => beginDrag(e, "move")}>
            <span className="crop-crosshair" aria-hidden />
            {CORNER_HANDLES.map((h) => (
              <span key={h} className={`crop-handle ${h}`} onPointerDown={(e) => beginDrag(e, h)} />
            ))}
            {EDGE_HANDLES.map((h) => (
              <span key={h} className={`crop-handle edge ${h}`} onPointerDown={(e) => beginDrag(e, h)} />
            ))}
          </div>
        </div>
      </div>

      <div className="crop-controls">
        <div className="crop-preview-card">
          {preview ? <img src={preview} alt="" /> : <span className="crop-preview-empty">…</span>}
          <small>Crop</small>
        </div>

        <div className="crop-tools">
          <div className="crop-tool-row" role="group" aria-label="Resize">
            <button className="crop-tool" type="button" onClick={() => scaleBox(0.8)} title="Smaller">
              −
            </button>
            <button className="crop-tool" type="button" onClick={() => scaleBox(1.2)} title="Larger">
              +
            </button>
            <button className="crop-tool accent" type="button" onClick={() => scaleBox(0.68)}>
              Tighten
            </button>
            <button
              className="crop-tool"
              type="button"
              onClick={() => setBox(initialBox || defaultBox())}
            >
              Reset
            </button>
          </div>

          <div className="crop-move-block">
            <span className="crop-move-label">Nudge box</span>
            <div className="crop-dpad" role="group" aria-label="Move crop box">
              <button className="crop-dpad-btn up" type="button" onClick={() => nudge(0, -NUDGE)} aria-label="Move up">
                ↑
              </button>
              <button className="crop-dpad-btn left" type="button" onClick={() => nudge(-NUDGE, 0)} aria-label="Move left">
                ←
              </button>
              <button className="crop-dpad-btn center" type="button" disabled aria-hidden>
                ·
              </button>
              <button className="crop-dpad-btn right" type="button" onClick={() => nudge(NUDGE, 0)} aria-label="Move right">
                →
              </button>
              <button className="crop-dpad-btn down" type="button" onClick={() => nudge(0, NUDGE)} aria-label="Move down">
                ↓
              </button>
            </div>
          </div>
        </div>
      </div>

      {warn && <p className="crop-warn">{warn}</p>}
      <p className="crop-hint">Drag the box or pinch with two fingers. Fill it with nose leather only.</p>

      <div className="crop-actions">
        <button className="btn btn-outline" type="button" onClick={onCancel} disabled={confirming}>
          Cancel
        </button>
        <button className="btn btn-primary" type="button" onClick={confirm} disabled={confirming}>
          {confirming ? "Working…" : "Use this crop"}
        </button>
      </div>
    </div>
  );
}
