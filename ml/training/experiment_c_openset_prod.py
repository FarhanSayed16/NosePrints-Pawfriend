"""
Experiment C — Open-set evaluation on production embedding baseline.

Gallery = train images for KNOWN ids only.
Genuine probes = val images of known ids.
Unknown probes = val images of held-out dog ids (absent from gallery).

Reports verification FAR/FRR and identification FPIR at 0.51 / 0.56 / 0.60.
Uses Torch baseline after ONNX parity (same as Experiment A).
"""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from augmentations import get_val_transforms
from experiment_a_multiprint import (
    l2_normalize,
    parity_check,
    rates_at_threshold,
    score_probes_max_prints,
    torch_embed_loader,
)
from train_embedding import NosePrintDataset, NosePrintEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("expC")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity_root", default="data/identity")
    ap.add_argument("--onnx", default="../backend/models/embedding_model.onnx")
    ap.add_argument("--checkpoint", default="checkpoints/embedding/best_model.baseline.pt")
    ap.add_argument("--out_dir", default="eval_results/experiment_c_openset")
    ap.add_argument("--unknown_frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_dogs", type=int, default=0)
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

    cache = Path("eval_results/experiment_a_multiprint/embeddings_cache.npz")
    if cache.exists():
        logger.info("Reusing Experiment A embedding cache")
        z = np.load(cache, allow_pickle=True)
        g_emb, g_lab = z["g_emb"], z["g_lab"]
        p_emb, p_lab = z["p_emb"], z["p_lab"]
    else:
        train_loader = DataLoader(
            NosePrintDataset(str(root / "train"), transform=get_val_transforms(224)),
            batch_size=64,
            shuffle=False,
            num_workers=0,
        )
        val_loader = DataLoader(
            NosePrintDataset(str(root / "val"), transform=get_val_transforms(224)),
            batch_size=64,
            shuffle=False,
            num_workers=0,
        )
        g_emb, g_lab, _ = torch_embed_loader(model, train_loader, device)
        p_emb, p_lab, _ = torch_embed_loader(model, val_loader, device)

    ids = sorted(set(int(x) for x in p_lab.tolist()) & set(int(x) for x in g_lab.tolist()))
    if args.max_dogs > 0:
        ids = ids[: args.max_dogs]
    rng = random.Random(args.seed)
    shuffled = ids[:]
    rng.shuffle(shuffled)
    n_unk = max(1, int(len(shuffled) * args.unknown_frac))
    unknown_ids = set(shuffled[:n_unk])
    known_ids = set(shuffled[n_unk:])

    g_mask = np.array([int(x) in known_ids for x in g_lab])
    known_probe_mask = np.array([int(x) in known_ids for x in p_lab])
    unk_probe_mask = np.array([int(x) in unknown_ids for x in p_lab])

    g_e, g_y = g_emb[g_mask], g_lab[g_mask]
    k_e, k_y = p_emb[known_probe_mask], p_lab[known_probe_mask]
    u_e = p_emb[unk_probe_mask]

    # Closed-set style metrics on known (production max-print)
    closed = score_probes_max_prints(g_e, g_y, k_e, k_y)

    # Build gallery print matrix for unknown FPIR
    by = {}
    for e, lab in zip(g_e, g_y):
        by.setdefault(int(lab), []).append(e)
    G = np.vstack([np.stack(by[d]) for d in sorted(by)])
    # best sim of each unknown probe to any gallery print
    best_unk = (u_e @ G.T).max(axis=1) if len(u_e) else np.array([])

    report = {
        "parity": parity,
        "protocol": {
            "unknown_frac": args.unknown_frac,
            "seed": args.seed,
            "known_ids": len(known_ids),
            "unknown_ids": len(unknown_ids),
            "gallery_images": int(len(g_e)),
            "known_probes": int(len(k_e)),
            "unknown_probes": int(len(u_e)),
            "matcher": "max_similarity_over_prints (production)",
        },
        "closed_set_known": {
            "auc": closed["auc"],
            "rank1": closed["rank1"],
            "rank5": closed["rank5"],
            "n_probe": closed["n_probe"],
        },
        "thresholds": {},
    }

    for thr in (0.51, 0.56, 0.60):
        ver = rates_at_threshold(closed["genuine"], closed["impostor"], thr)
        # FPIR: fraction of unknown probes whose best gallery score >= thr
        # (would be accepted as some enrolled identity in verification-against-gallery)
        fpir = float((best_unk >= thr).mean()) if len(best_unk) else 0.0
        # Identification-style: also report mean best sim
        report["thresholds"][str(thr)] = {
            **ver,
            "unknown_FPIR_best_gallery_ge_thr": fpir,
            "unknown_mean_best_sim": float(best_unk.mean()) if len(best_unk) else None,
            "known_mean_genuine_sim": float(closed["genuine"].mean()),
            "known_mean_impostor_sim": float(closed["impostor"].mean()),
        }

    # ROC of known genuine vs known impostor
    scores = np.concatenate([closed["genuine"], closed["impostor"]])
    y = np.array([1] * len(closed["genuine"]) + [0] * len(closed["impostor"]))
    fpr, tpr, thr_arr = roc_curve(y, scores)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f"AUC={closed['auc']:.4f}")
    plt.plot([0, 1], [0, 1], "k--")
    for t, c in [(0.56, "g"), (0.60, "r")]:
        plt.axvline(x=float((closed["impostor"] >= t).mean()), color=c, linestyle=":", label=f"FAR@{t}")
    plt.xlabel("FAR")
    plt.ylabel("TAR")
    plt.title("Experiment C — known genuine vs impostor (lab CVPR)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / "roc_known.png", dpi=120)
    plt.close()

    (out / "results.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    logger.info("Wrote %s", out / "results.json")
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
