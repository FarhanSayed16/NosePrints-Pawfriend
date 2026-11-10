"""
Experiment A — Multi-print aggregation (offline, non-destructive).

Compares gallery templates built ONLY from enrollment (train) images:
  A) best-quality single print (Laplacian sharpness)
  B) max similarity over prints (production matcher.py strategy)
  C) mean L2-normalized embedding template (re-normalized)
  D) quality-weighted mean template (sharpness weights)

Uses production-equivalent embeddings: Torch baseline checkpoint after ONNX parity check,
OR ONNX if --force-onnx (slower on CPU).
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader
from tqdm import tqdm

from augmentations import get_val_transforms
from train_embedding import NosePrintDataset, NosePrintEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("expA")


def sharpness_laplacian(path: Path) -> float:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def l2_normalize(x: np.ndarray, axis: int = -1) -> np.ndarray:
    n = np.linalg.norm(x, axis=axis, keepdims=True) + 1e-8
    return x / n


def onnx_embed_batch(session, input_name, imgs_chw: np.ndarray) -> np.ndarray:
    # imgs_chw: N,3,224,224 float32 imagenet-norm
    outs = []
    for i in range(len(imgs_chw)):
        out = session.run(None, {input_name: imgs_chw[i : i + 1]})[0].reshape(-1)
        outs.append(out)
    e = np.stack(outs).astype(np.float32)
    return l2_normalize(e, axis=1)


def torch_embed_loader(model, loader, device) -> tuple[np.ndarray, np.ndarray, list[str]]:
    embs, labs, paths = [], [], []
    model.eval()
    ds: NosePrintDataset = loader.dataset
    flat_paths = [p for p, _ in ds.samples]
    idx = 0
    with torch.no_grad():
        for images, labels in tqdm(loader, desc=f"embed:{Path(ds.data_dir).name}"):
            images = images.to(device, non_blocking=True)
            e = model(images).cpu().numpy()
            embs.append(e)
            labs.append(labels.numpy())
            b = len(labels)
            paths.extend(flat_paths[idx : idx + b])
            idx += b
    return np.vstack(embs).astype(np.float32), np.concatenate(labs), paths


def parity_check(onnx_path: Path, ckpt_path: Path, sample_dir: Path, n: int = 32) -> dict:
    import onnxruntime as ort

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = NosePrintEmbedder(embedding_dim=ckpt.get("embedding_dim", 512), pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    iname = sess.get_inputs()[0].name
    tfm = get_val_transforms(224)

    paths = []
    for class_dir in sorted([d for d in sample_dir.iterdir() if d.is_dir()])[:50]:
        for p in sorted(class_dir.iterdir()):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                paths.append(p)
            if len(paths) >= n:
                break
        if len(paths) >= n:
            break

    diffs = []
    cos = []
    with torch.no_grad():
        for p in paths:
            im = Image.open(p).convert("RGB")
            arr = np.array(im)
            t = tfm(image=arr)["image"].unsqueeze(0).to(device)
            te = model(t).cpu().numpy().reshape(-1)
            te = te / (np.linalg.norm(te) + 1e-8)
            # match production ONNX preprocess (cv2 path)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            resized = cv2.resize(bgr, (224, 224))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], np.float32)
            std = np.array([0.229, 0.224, 0.225], np.float32)
            x = ((rgb - mean) / std).transpose(2, 0, 1)[None]
            oe = sess.run(None, {iname: x})[0].reshape(-1)
            oe = oe / (np.linalg.norm(oe) + 1e-8)
            diffs.append(float(np.max(np.abs(te - oe))))
            cos.append(float(np.dot(te, oe)))
    return {
        "n": len(paths),
        "max_abs_diff_mean": float(np.mean(diffs)),
        "max_abs_diff_max": float(np.max(diffs)),
        "cosine_mean": float(np.mean(cos)),
        "cosine_min": float(np.min(cos)),
        "pass": float(np.mean(cos)) > 0.999,
    }


def build_templates(
    emb: np.ndarray,
    labels: np.ndarray,
    paths: list[str],
    method: str,
) -> tuple[dict[int, np.ndarray], dict]:
    """Return dog_id -> template embedding (L2-normalized)."""
    by: dict[int, list[tuple[np.ndarray, float, str]]] = defaultdict(list)
    for e, lab, p in zip(emb, labels, paths):
        q = sharpness_laplacian(Path(p))
        by[int(lab)].append((e, q, p))

    templates: dict[int, np.ndarray] = {}
    meta = {"method": method, "dogs": len(by), "quality_notes": []}
    zero_q = 0
    for dog, items in by.items():
        vecs = np.stack([x[0] for x in items])
        qs = np.array([x[1] for x in items], dtype=np.float64)
        if method == "A_best_quality":
            i = int(np.argmax(qs))
            t = vecs[i]
            if qs[i] <= 0:
                zero_q += 1
        elif method == "C_mean":
            t = vecs.mean(axis=0)
        elif method == "D_quality_weighted":
            w = np.maximum(qs, 1e-6)
            if not np.any(qs > 0):
                zero_q += 1
                t = vecs.mean(axis=0)
            else:
                t = (vecs * w[:, None]).sum(axis=0) / w.sum()
        else:
            raise ValueError(method)
        templates[dog] = l2_normalize(t.astype(np.float32))
    if zero_q:
        meta["quality_notes"].append(f"{zero_q} dogs had non-positive sharpness; fell back/mean used where needed")
    meta["zero_quality_dogs"] = zero_q
    return templates, meta


def score_probes_templates(
    templates: dict[int, np.ndarray],
    probe_emb: np.ndarray,
    probe_labels: np.ndarray,
) -> dict:
    dog_ids = sorted(templates)
    mat = np.stack([templates[d] for d in dog_ids])  # D,512
    dog_index = {d: i for i, d in enumerate(dog_ids)}

    genuine, impostor = [], []
    rank1 = rank5 = used = 0
    t0 = time.perf_counter()
    for e, lab in zip(probe_emb, probe_labels):
        lab = int(lab)
        if lab not in dog_index:
            continue
        used += 1
        sims = mat @ e
        order = np.argsort(-sims)
        pred = dog_ids[int(order[0])]
        if pred == lab:
            rank1 += 1
        top5 = {dog_ids[int(i)] for i in order[:5]}
        if lab in top5:
            rank5 += 1
        genuine.append(float(sims[dog_index[lab]]))
        others = np.delete(sims, dog_index[lab])
        impostor.append(float(others.max()) if others.size else 0.0)
    latency_ms = (time.perf_counter() - t0) * 1000 / max(1, used)

    scores = np.array(genuine + impostor, np.float32)
    y = np.array([1] * len(genuine) + [0] * len(impostor), np.int32)
    auc = float(roc_auc_score(y, scores)) if len(set(y.tolist())) > 1 else float("nan")
    return {
        "n_probe": used,
        "auc": auc,
        "rank1": rank1 / max(1, used),
        "rank5": rank5 / max(1, used),
        "genuine": np.array(genuine),
        "impostor": np.array(impostor),
        "latency_ms_per_probe": latency_ms,
        "gallery_vectors": len(dog_ids),
    }


def score_probes_max_prints(
    gal_emb: np.ndarray,
    gal_labels: np.ndarray,
    probe_emb: np.ndarray,
    probe_labels: np.ndarray,
) -> dict:
    """Production strategy: max cosine over all prints of each dog."""
    by: dict[int, np.ndarray] = {}
    for e, lab in zip(gal_emb, gal_labels):
        lab = int(lab)
        by.setdefault(lab, [])
        by[lab].append(e)
    mats = {d: np.stack(v) for d, v in by.items()}  # each Ni,512
    dog_ids = sorted(mats)
    dog_index = {d: i for i, d in enumerate(dog_ids)}

    genuine, impostor = [], []
    rank1 = rank5 = used = 0
    t0 = time.perf_counter()
    # Precompute for speed: stacked all prints + dog id per row
    all_prints = []
    print_dog = []
    for d in dog_ids:
        all_prints.append(mats[d])
        print_dog.extend([d] * len(mats[d]))
    G = np.vstack(all_prints)
    print_dog = np.array(print_dog)

    for e, lab in zip(probe_emb, probe_labels):
        lab = int(lab)
        if lab not in dog_index:
            continue
        used += 1
        sims_prints = G @ e
        # max per dog
        best = np.full(len(dog_ids), -1.0, np.float32)
        for i, d in enumerate(dog_ids):
            mask = print_dog == d
            best[i] = float(sims_prints[mask].max())
        order = np.argsort(-best)
        pred = dog_ids[int(order[0])]
        if pred == lab:
            rank1 += 1
        if lab in {dog_ids[int(i)] for i in order[:5]}:
            rank5 += 1
        genuine.append(float(best[dog_index[lab]]))
        others = np.delete(best, dog_index[lab])
        impostor.append(float(others.max()) if others.size else 0.0)
    latency_ms = (time.perf_counter() - t0) * 1000 / max(1, used)
    scores = np.array(genuine + impostor, np.float32)
    y = np.array([1] * len(genuine) + [0] * len(impostor), np.int32)
    auc = float(roc_auc_score(y, scores))
    return {
        "n_probe": used,
        "auc": auc,
        "rank1": rank1 / max(1, used),
        "rank5": rank5 / max(1, used),
        "genuine": np.array(genuine),
        "impostor": np.array(impostor),
        "latency_ms_per_probe": latency_ms,
        "gallery_vectors": int(len(G)),
    }


def rates_at_threshold(genuine: np.ndarray, impostor: np.ndarray, thr: float) -> dict:
    # Verification-style: accept if score >= thr
    tar = float((genuine >= thr).mean()) if len(genuine) else 0.0  # genuine accept
    frr = 1.0 - tar
    far = float((impostor >= thr).mean()) if len(impostor) else 0.0
    return {"threshold": thr, "TAR": tar, "FRR": frr, "FAR": far}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity_root", default="data/identity")
    ap.add_argument("--onnx", default="../backend/models/embedding_model.onnx")
    ap.add_argument("--checkpoint", default="checkpoints/embedding/best_model.baseline.pt")
    ap.add_argument("--out_dir", default="eval_results/experiment_a_multiprint")
    ap.add_argument("--max_dogs", type=int, default=0, help="0=all; use e.g. 500 for smoke")
    ap.add_argument("--force_onnx", action="store_true")
    args = ap.parse_args()

    root = Path(args.identity_root)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    parity = parity_check(Path(args.onnx), Path(args.checkpoint), root / "val", n=32)
    (out / "onnx_torch_parity.json").write_text(json.dumps(parity, indent=2), encoding="utf-8")
    logger.info("parity=%s", parity)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model = NosePrintEmbedder(embedding_dim=ckpt.get("embedding_dim", 512), pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)

    if args.force_onnx and not parity["pass"]:
        logger.warning("Parity weak; still using Torch unless --force_onnx only path")

    # Optionally subset dogs by rewriting temp dirs is heavy; instead filter after load
    train_ds = NosePrintDataset(str(root / "train"), transform=get_val_transforms(224))
    val_ds = NosePrintDataset(str(root / "val"), transform=get_val_transforms(224))
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=False, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, num_workers=0)

    cache = out / "embeddings_cache.npz"
    if cache.exists() and not args.force_onnx:
        logger.info("Loading embedding cache %s", cache)
        z = np.load(cache, allow_pickle=True)
        g_emb, g_lab = z["g_emb"], z["g_lab"]
        p_emb, p_lab = z["p_emb"], z["p_lab"]
        g_paths = z["g_paths"].tolist()
        p_paths = z["p_paths"].tolist()
    else:
        g_emb, g_lab, g_paths = torch_embed_loader(model, train_loader, device)
        p_emb, p_lab, p_paths = torch_embed_loader(model, val_loader, device)
        np.savez_compressed(
            cache,
            g_emb=g_emb,
            g_lab=g_lab,
            p_emb=p_emb,
            p_lab=p_lab,
            g_paths=np.array(g_paths, dtype=object),
            p_paths=np.array(p_paths, dtype=object),
        )
        logger.info("Saved embedding cache %s", cache)

    if args.max_dogs > 0:
        keep = set(sorted(set(int(x) for x in g_lab.tolist()))[: args.max_dogs])
        g_mask = np.array([int(x) in keep for x in g_lab])
        p_mask = np.array([int(x) in keep for x in p_lab])
        g_emb, g_lab, g_paths = g_emb[g_mask], g_lab[g_mask], [p for p, m in zip(g_paths, g_mask) if m]
        p_emb, p_lab, p_paths = p_emb[p_mask], p_lab[p_mask], [p for p, m in zip(p_paths, p_mask) if m]

    results = {"parity": parity, "methods": {}}

    # B first — production
    logger.info("Method B max-prints")
    t0 = time.perf_counter()
    b = score_probes_max_prints(g_emb, g_lab, p_emb, p_lab)
    b["build_s"] = 0.0
    b["search_wall_s"] = time.perf_counter() - t0
    for thr in (0.51, 0.56, 0.60):
        b[f"@ {thr}"] = rates_at_threshold(b["genuine"], b["impostor"], thr)
    results["methods"]["B_max_similarity"] = {k: v for k, v in b.items() if k not in ("genuine", "impostor")}
    results["methods"]["B_max_similarity"]["thresholds"] = {str(t): b[f"@ {t}"] for t in (0.51, 0.56, 0.60)}

    for method in ("A_best_quality", "C_mean", "D_quality_weighted"):
        logger.info("Method %s", method)
        t0 = time.perf_counter()
        templates, meta = build_templates(g_emb, g_lab, g_paths, method)
        build_s = time.perf_counter() - t0
        r = score_probes_templates(templates, p_emb, p_lab)
        r["build_s"] = build_s
        r["meta"] = meta
        for thr in (0.51, 0.56, 0.60):
            r[f"@ {thr}"] = rates_at_threshold(r["genuine"], r["impostor"], thr)
        results["methods"][method] = {
            k: v for k, v in r.items() if k not in ("genuine", "impostor")
        }
        results["methods"][method]["thresholds"] = {str(t): r[f"@ {t}"] for t in (0.51, 0.56, 0.60)}

    # storage implication
    n_prints = len(g_emb)
    n_dogs = len(set(int(x) for x in g_lab.tolist()))
    results["storage"] = {
        "prints_in_gallery": n_prints,
        "dogs": n_dogs,
        "bytes_max_strategy_approx": n_prints * 512 * 4,
        "bytes_template_strategy_approx": n_dogs * 512 * 4,
    }

    (out / "results.json").write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")
    logger.info("Wrote %s", out / "results.json")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "meta"} if isinstance(v, dict) else v for k, v in results["methods"].items()}, indent=2, default=float))


if __name__ == "__main__":
    main()
