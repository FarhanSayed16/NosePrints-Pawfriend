import { useEffect, useRef, useState } from "react";
import { toJpegFile } from "../utils/imageFile";
import "./NoseCropEditor.css";

const MIN_NORM = 0.06;
const MIN_PX = 160;
const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];

function defaultBox() {
  return { x1: 0.32, y1: 0.32, x2: 0.68, y2: 0.68 };
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
  const [box, setBox] = useState(initialBox || defaultBox());
  const [preview, setPreview] = useState(null);
  const [warn, setWarn] = useState("");
  const dragRef = useRef(null);

  useEffect(() => {
    setBox(initialBox || defaultBox());
  }, [initialBox, imageUrl]);

  const clientToNorm = (clientX, clientY) => {
    const img = imgRef.current;
    const rect = img.getBoundingClientRect();
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

  const onPointerDown = (event, handle) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const p = clientToNorm(event.clientX, event.clientY);
    dragRef.current = { handle, start: p, orig: { ...box } };

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
    const cx = (box.x1 + box.x2) / 2;
    const cy = (box.y1 + box.y2) / 2;
    const w = Math.max(MIN_NORM, (box.x2 - box.x1) * factor);
    const h = Math.max(MIN_NORM, (box.y2 - box.y1) * factor);
    setBox(
      clampBox({
        x1: cx - w / 2,
        y1: cy - h / 2,
        x2: cx + w / 2,
        y2: cy + h / 2,
      })
    );
  };

  const cropPixels = () => {
    const img = imgRef.current;
    if (!img?.naturalWidth) return null;
    const sx = Math.round(box.x1 * img.naturalWidth);
    const sy = Math.round(box.y1 * img.naturalHeight);
    const sw = Math.max(8, Math.round((box.x2 - box.x1) * img.naturalWidth));
    const sh = Math.max(8, Math.round((box.y2 - box.y1) * img.naturalHeight));
    return { sx, sy, sw, sh, img };
  };

  useEffect(() => {
    const region = cropPixels();
    if (!region) return undefined;
    const { sx, sy, sw, sh, img } = region;
    const canvas = document.createElement("canvas");
    canvas.width = sw;
    canvas.height = sh;
    canvas.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
    const url = canvas.toDataURL("image/jpeg", 0.85);
    setPreview(url);
    setWarn(
      Math.min(sw, sh) < MIN_PX
        ? `This crop is only ${sw}×${sh} px. Pinch the handles inward onto the nose leather, or take a closer photo.`
        : ""
    );
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [box, imageUrl]);

  const confirm = async () => {
    const region = cropPixels();
    if (!region) return;
    const { sx, sy, sw, sh, img } = region;
    const canvas = document.createElement("canvas");
    canvas.width = sw;
    canvas.height = sh;
    canvas.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95));
    if (!blob) return;
    const file = await toJpegFile(blob, "nose-crop.jpg");
    onConfirm(file);
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
    <div className="crop-editor glass-card">
      <p className="crop-msg">
        {message || "Drag the box onto the black nose leather. Leave a little muzzle, not the eyes."}
      </p>
      <div className="crop-stage">
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Uploaded dog"
          draggable={false}
          onLoad={() => setBox((current) => ({ ...current }))}
        />
        <div className="crop-dim" style={dim.top} />
        <div className="crop-dim" style={dim.bottom} />
        <div className="crop-dim" style={dim.left} />
        <div className="crop-dim" style={dim.right} />
        <div
          className="crop-box"
          style={style}
          onPointerDown={(e) => onPointerDown(e, "move")}
        >
          {HANDLES.map((h) => (
            <span
              key={h}
              className={`crop-handle ${h}`}
              onPointerDown={(e) => onPointerDown(e, h)}
            />
          ))}
        </div>
      </div>

      <div className="crop-nudge">
        <button className="btn btn-outline btn-sm" type="button" onClick={() => scaleBox(0.85)}>
          Smaller box
        </button>
        <button className="btn btn-outline btn-sm" type="button" onClick={() => scaleBox(1.15)}>
          Larger box
        </button>
      </div>

      {preview && (
        <div className="crop-preview-row">
          <img src={preview} alt="Nose crop preview" />
          <p>This is what will be saved. Tighten the box until it is mostly the nose.</p>
        </div>
      )}
      {warn && <p className="crop-warn">{warn}</p>}

      <div className="crop-actions">
        <button className="btn btn-outline" type="button" onClick={onCancel}>
          Choose another
        </button>
        <button className="btn btn-primary" type="button" onClick={confirm} disabled={Boolean(warn)}>
          Use this nose crop
        </button>
      </div>
    </div>
  );
}
