/** Max long edge for uploads — keeps tunnel + ONNX fast enough. */
export const MAX_UPLOAD_EDGE = 1600;

/**
 * Decode, resize if needed, and return a named JPEG File for API upload.
 */
export async function toJpegFile(input, filename = "photo.jpg", { maxEdge = MAX_UPLOAD_EDGE } = {}) {
  if (!input) return null;

  const bitmap = await decodeBitmap(input);
  let { width, height } = bitmap;

  if (Math.max(width, height) > maxEdge) {
    const scale = maxEdge / Math.max(width, height);
    width = Math.round(width * scale);
    height = Math.round(height * scale);
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bitmap, 0, 0, width, height);
  if (typeof bitmap.close === "function") bitmap.close();

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (out) => (out ? resolve(out) : reject(new Error("Could not encode JPEG"))),
      "image/jpeg",
      0.88
    );
  });
  return new File([blob], filename, { type: "image/jpeg" });
}

async function decodeBitmap(blob) {
  if (typeof createImageBitmap === "function") {
    try {
      return await createImageBitmap(blob);
    } catch {
      /* HEIC / odd types: fall through to <img> */
    }
  }
  const url = URL.createObjectURL(blob);
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () =>
        reject(new Error("This phone could not read that image. Try a JPEG from the gallery."));
      el.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    canvas.getContext("2d").drawImage(img, 0, 0);
    return canvas;
  } finally {
    URL.revokeObjectURL(url);
  }
}

function isHtmlPayload(value) {
  return typeof value === "string" && /<html|<!doctype/i.test(value);
}

export function formatCaptureError(err, fallback = "Could not use that photo") {
  const status = err?.response?.status;
  const raw = err?.response?.data;

  if (status === 502 || status === 504) {
    return "The server took too long. Keep this PC awake, then try again with a closer nose photo.";
  }
  if (status === 429) {
    return "Too many tries — wait a minute and try again.";
  }
  if (err?.code === "ECONNABORTED") {
    return "Upload timed out. Try a closer photo or check that the PC running the app is still on.";
  }
  if (!err?.response && err?.message?.includes("Network Error")) {
    return "Could not reach the server. Check your internet and that the app PC is still running.";
  }

  let detail = raw;
  if (typeof raw === "string" && isHtmlPayload(raw)) {
    if (/cloudflare/i.test(raw)) {
      return "Connection through Cloudflare failed. Retry in a few seconds — the photo may have been too large.";
    }
    return fallback;
  }

  if (detail == null) return err?.message || fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join("; ");
  }
  if (typeof detail === "object") {
    const parts = [detail.message || fallback];
    if (Array.isArray(detail.issues) && detail.issues.length) {
      parts.push(detail.issues.join(" "));
    }
    if (Array.isArray(detail.suggestions) && detail.suggestions.length) {
      parts.push(detail.suggestions.join(" "));
    }
    return parts.join(" — ");
  }
  return fallback;
}
