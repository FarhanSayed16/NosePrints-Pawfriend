"""Generate synthetic junk fixtures and hit live gate endpoints."""
from __future__ import annotations

import json
import uuid
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(r"D:\NosePrints-Pawfriend\ml\data\detector\phone-test")
REPORT = Path(r"D:\NosePrints-Pawfriend\docs\OPS_ACCEPTANCE_API.json")
BASE = "http://127.0.0.1:8000"


def post_file(url: str, path: Path, fields: dict | None = None):
    boundary = "----Boundary" + uuid.uuid4().hex
    data = path.read_bytes()
    body = b""
    if fields:
        for k, v in fields.items():
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
            ).encode()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{path.name}\"\r\nContent-Type: image/jpeg\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:500]}
    except Exception as e:
        return 0, {"error": str(e)}


def make_fixtures():
    OUT.mkdir(parents=True, exist_ok=True)
    kb = Image.new("RGB", (640, 480), (40, 40, 45))
    d = ImageDraw.Draw(kb)
    for y in range(40, 440, 40):
        for x in range(20, 620, 55):
            d.rectangle([x, y, x + 45, y + 28], fill=(70, 70, 75), outline=(120, 120, 130))
    kb_path = OUT / "junk_keyboard.jpg"
    kb.save(kb_path, quality=90)

    wall_path = OUT / "junk_wall.jpg"
    Image.new("RGB", (640, 480), (210, 205, 200)).save(wall_path, quality=90)

    fab = Image.new("RGB", (640, 480), (180, 40, 60))
    df = ImageDraw.Draw(fab)
    for i in range(0, 640, 30):
        df.line([(i, 0), (i, 480)], fill=(40, 120, 200), width=8)
    fab_path = OUT / "junk_fabric.jpg"
    fab.save(fab_path, quality=90)

    nose = Image.new("RGB", (640, 480), (30, 30, 35))
    dn = ImageDraw.Draw(nose)
    dn.ellipse([220, 140, 420, 340], fill=(55, 35, 30))
    arr = np.array(nose)
    noise = np.random.randint(-15, 15, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    nose = Image.fromarray(arr)
    dn = ImageDraw.Draw(nose)
    for i in range(12):
        dn.arc([250 + i * 3, 180 + i * 2, 390 - i * 3, 300 - i * 2], 0, 360, fill=(80, 55, 45))
    nose_path = OUT / "synth_closeup_nose.jpg"
    nose.save(nose_path, quality=92)
    return {
        "keyboard": kb_path,
        "wall": wall_path,
        "fabric": fab_path,
        "synth_nose": nose_path,
    }


def main():
    fixtures = make_fixtures()
    try:
        openapi = json.loads(urllib.request.urlopen(f"{BASE}/openapi.json", timeout=10).read())
        paths = sorted(openapi.get("paths", {}).keys())
        print("gate_paths", [p for p in paths if any(x in p for x in ("detect", "look", "quality"))])
    except Exception as e:
        print("openapi_err", e)
        paths = []

    def pick(substr: str) -> str | None:
        for p in paths:
            if substr in p:
                return BASE + p
        return None

    endpoints = {
        "detect-preview": pick("detect-preview") or f"{BASE}/matching/detect-preview",
        "look-check": pick("look-check") or f"{BASE}/dogs/look-check",
        "quality-check": pick("quality-check") or f"{BASE}/noseprints/quality-check",
    }
    print("endpoints", endpoints)

    results = []
    for kind, url in endpoints.items():
        for label, path in fixtures.items():
            fields = {"pre_cropped": "true"} if kind == "quality-check" else None
            code, body = post_file(url, path, fields)
            slim = {}
            if isinstance(body, dict):
                for k in (
                    "detected",
                    "ok",
                    "passed",
                    "soft_warn",
                    "message",
                    "detail",
                    "reason",
                    "issues",
                    "quality_ok",
                    "nose_found",
                    "error",
                    "bbox",
                    "confidence",
                ):
                    if k in body:
                        slim[k] = body[k]
                if not slim:
                    slim = {k: body[k] for k in list(body)[:8]}
            results.append({"endpoint": kind, "case": label, "http": code, "result": slim})
            print(json.dumps(results[-1], default=str))

    REPORT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("wrote", REPORT, "n=", len(results))


if __name__ == "__main__":
    main()
