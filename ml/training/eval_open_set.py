"""
Open-set style check: hold out a fraction of val dog IDs as unknown.
Report false-accept rate when best gallery match is forced among *known* IDs
vs score of unknown probes against the known gallery at T_high.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch

from evaluate import extract_all_embeddings
from train_embedding import NosePrintEmbedder


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--gallery_dir", required=True, help="identity/train")
    p.add_argument("--probe_dir", required=True, help="identity/val")
    p.add_argument("--t_high", type=float, default=0.56)
    p.add_argument("--unknown_frac", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--img_size", type=int, default=224)
    p.add_argument("--output", type=str, default="")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model = NosePrintEmbedder(embedding_dim=ckpt.get("embedding_dim", 512), pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)

    gal_e, gal_y = extract_all_embeddings(model, args.gallery_dir, args.img_size, str(device))
    pr_e, pr_y = extract_all_embeddings(model, args.probe_dir, args.img_size, str(device))

    ids = sorted(set(int(x) for x in pr_y.tolist()))
    rng = random.Random(args.seed)
    rng.shuffle(ids)
    n_unk = max(1, int(len(ids) * args.unknown_frac))
    unknown_ids = set(ids[:n_unk])
    known_ids = set(ids[n_unk:])

    # Gallery restricted to dogs that appear in known probe set AND have gallery images
    gal_mask = np.array([int(y) in known_ids for y in gal_y], dtype=bool)
    if gal_mask.sum() < 10:
        # fallback: use all gallery labels that intersect known
        gal_mask = np.ones(len(gal_y), dtype=bool)
    g_e, g_y = gal_e[gal_mask], gal_y[gal_mask]

    unk_mask = np.array([int(y) in unknown_ids for y in pr_y], dtype=bool)
    known_mask = np.array([int(y) in known_ids for y in pr_y], dtype=bool)
    unk_e = pr_e[unk_mask]
    known_e, known_y = pr_e[known_mask], pr_y[known_mask]

    # Cosine: embeddings already L2-normalized
    sims_unk = unk_e @ g_e.T  # [Nu, Ng]
    best_unk = sims_unk.max(axis=1) if len(unk_e) else np.array([])
    fa = float((best_unk >= args.t_high).mean()) if len(best_unk) else 0.0

    sims_k = known_e @ g_e.T
    best_k = sims_k.max(axis=1)
    # genuine: best among same-id gallery
    # approximate with overall best for TAR@T_high among known probes
    tar = float((best_k >= args.t_high).mean()) if len(best_k) else 0.0

    lines = [
        f"Open-set holdout frac: {args.unknown_frac}",
        f"Unknown dog IDs: {len(unknown_ids)}",
        f"Known dog IDs (probe): {len(known_ids)}",
        f"Unknown probes: {len(best_unk)}",
        f"Known probes: {len(best_k)}",
        f"T_high: {args.t_high:.6f}",
        f"False-accept rate (unknown probes >= T_high): {fa:.6f}",
        f"Accept rate (known probes >= T_high, any gallery): {tar:.6f}",
        f"Mean best sim unknown: {float(best_unk.mean()) if len(best_unk) else 0:.6f}",
        f"Mean best sim known: {float(best_k.mean()) if len(best_k) else 0:.6f}",
    ]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
