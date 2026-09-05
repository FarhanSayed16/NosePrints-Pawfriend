"""
Evaluation script — measures model accuracy using ROC curves and AUC.
Builds positive/negative pairs, computes similarity scores, and plots
the trade-off between FAR (False Accept Rate) and FRR (False Reject Rate).

Usage:
    python evaluate.py --checkpoint ./checkpoints/best_model.pt --data_dir ./data/noseprints/val
"""

import argparse
import logging
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from augmentations import get_val_transforms
from train_embedding import NosePrintDataset, NosePrintEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_all_embeddings(
    model: NosePrintEmbedder,
    data_dir: str,
    img_size: int = 224,
    device: str = "cpu",
) -> tuple[np.ndarray, np.ndarray]:
    """Extract embeddings for all images in the dataset."""
    transform = get_val_transforms(img_size)
    dataset = NosePrintDataset(data_dir, transform=transform)
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=0)

    all_embeddings = []
    all_labels = []

    model.eval()
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            embeddings = model(images)
            all_embeddings.append(embeddings.cpu().numpy())
            all_labels.append(labels.numpy())

    return np.vstack(all_embeddings), np.concatenate(all_labels)


def build_pairs(
    embeddings: np.ndarray,
    labels: np.ndarray,
    max_pairs: int = 50000,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build positive and negative pairs for ROC analysis.

    Returns:
        similarity_scores: cosine similarity for each pair
        pair_labels: 1 for positive (same dog), 0 for negative (different dogs)
    """
    n = len(embeddings)
    similarities = []
    pair_labels = []

    # Generate pairs
    indices = list(range(n))
    all_pairs = list(combinations(indices, 2))

    # Subsample if too many pairs
    if len(all_pairs) > max_pairs:
        rng = np.random.RandomState(42)
        selected = rng.choice(len(all_pairs), size=max_pairs, replace=False)
        all_pairs = [all_pairs[i] for i in selected]

    for i, j in all_pairs:
        # Cosine similarity (embeddings are already L2-normalized)
        sim = float(np.dot(embeddings[i], embeddings[j]))
        similarities.append(sim)
        pair_labels.append(1 if labels[i] == labels[j] else 0)

    return np.array(similarities), np.array(pair_labels)


def evaluate_gallery_probe(
    gallery_emb: np.ndarray,
    gallery_labels: np.ndarray,
    probe_emb: np.ndarray,
    probe_labels: np.ndarray,
) -> dict:
    """
    Open-set style scores: each val photo vs registered (train) photos.
    Genuine = best cosine to the same dog. Impostor = best cosine to any other dog.
    """
    gallery_by_dog: dict[int, list[np.ndarray]] = {}
    for emb, lab in zip(gallery_emb, gallery_labels):
        gallery_by_dog.setdefault(int(lab), []).append(emb)

    dog_ids = sorted(gallery_by_dog)
    centroids = np.stack(
        [np.mean(np.stack(gallery_by_dog[d]), axis=0) for d in dog_ids]
    )
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-8
    dog_index = {d: i for i, d in enumerate(dog_ids)}

    genuine = []
    impostor = []
    rank1 = 0
    used = 0
    for emb, lab in zip(probe_emb, probe_labels):
        lab = int(lab)
        if lab not in dog_index:
            continue
        used += 1
        sims = centroids @ emb
        pred = dog_ids[int(np.argmax(sims))]
        if pred == lab:
            rank1 += 1
        genuine.append(float(sims[dog_index[lab]]))
        others = np.delete(sims, dog_index[lab])
        impostor.append(float(others.max()) if others.size else 0.0)

    scores = np.array(genuine + impostor, dtype=np.float32)
    y = np.array([1] * len(genuine) + [0] * len(impostor), dtype=np.int32)
    return {
        "scores": scores,
        "labels": y,
        "rank1": rank1 / max(1, used),
        "n_probe": used,
        "genuine": np.array(genuine),
        "impostor": np.array(impostor),
    }


def _write_roc_outputs(
    similarities: np.ndarray,
    pair_labels: np.ndarray,
    output_dir: Path,
    extra_lines: list[str] | None = None,
) -> None:
    fpr, tpr, thresholds = roc_curve(pair_labels, similarities)
    auc = roc_auc_score(pair_labels, similarities)

    j_scores = tpr - fpr
    optimal_idx = np.argmax(j_scores)
    optimal_threshold = float(thresholds[optimal_idx])
    optimal_tpr = float(tpr[optimal_idx])
    optimal_fpr = float(fpr[optimal_idx])

    def thresh_at_fpr(target: float) -> tuple[float, float, float]:
        idx = int(np.argmin(np.abs(fpr - target)))
        return float(thresholds[idx]), float(tpr[idx]), float(fpr[idx])

    t_high, tpr_high, fpr_high = thresh_at_fpr(0.05)
    t_low, tpr_low, fpr_low = thresh_at_fpr(0.20)

    logger.info(f"AUC: {auc:.4f}")
    logger.info(f"Youden threshold: {optimal_threshold:.4f}  TPR={optimal_tpr:.4f} FAR={optimal_fpr:.4f}")
    logger.info(f"T_high (~5% FAR): {t_high:.4f}  TPR={tpr_high:.4f} FAR={fpr_high:.4f}")
    logger.info(f"T_low  (~20% FAR): {t_low:.4f}  TPR={tpr_low:.4f} FAR={fpr_low:.4f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 8))
    plt.plot(fpr, tpr, "b-", linewidth=2, label=f"ROC (AUC = {auc:.4f})")
    plt.plot([0, 1], [0, 1], "r--", linewidth=1, label="Random")
    plt.scatter([optimal_fpr], [optimal_tpr], color="green", s=80, zorder=5, label="Youden")
    plt.xlabel("False Positive Rate (FAR)")
    plt.ylabel("True Positive Rate")
    plt.title("NosePrint matching ROC")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "roc_curve.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 6))
    pos_sims = similarities[pair_labels == 1]
    neg_sims = similarities[pair_labels == 0]
    plt.hist(neg_sims, bins=80, alpha=0.6, color="red", label="Different dogs")
    plt.hist(pos_sims, bins=80, alpha=0.6, color="green", label="Same dog")
    plt.axvline(x=t_high, color="blue", linestyle="--", label=f"T_high={t_high:.3f}")
    plt.axvline(x=t_low, color="purple", linestyle=":", label=f"T_low={t_low:.3f}")
    plt.xlabel("Cosine similarity")
    plt.ylabel("Count")
    plt.title("Similarity score distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "similarity_distribution.png", dpi=150)
    plt.close()

    with open(output_dir / "metrics.txt", "w", encoding="utf-8") as f:
        f.write(f"AUC: {auc:.6f}\n")
        f.write(f"Youden Threshold: {optimal_threshold:.6f}\n")
        f.write(f"TPR at Youden: {optimal_tpr:.6f}\n")
        f.write(f"FPR at Youden: {optimal_fpr:.6f}\n")
        f.write(f"T_high (FAR~5%): {t_high:.6f}\n")
        f.write(f"TPR at T_high: {tpr_high:.6f}\n")
        f.write(f"FPR at T_high: {fpr_high:.6f}\n")
        f.write(f"T_low (FAR~20%): {t_low:.6f}\n")
        f.write(f"TPR at T_low: {tpr_low:.6f}\n")
        f.write(f"FPR at T_low: {fpr_low:.6f}\n")
        f.write(f"Positive Pairs: {int(pair_labels.sum())}\n")
        f.write(f"Negative Pairs: {int((pair_labels == 0).sum())}\n")
        if extra_lines:
            for line in extra_lines:
                f.write(line.rstrip() + "\n")
    logger.info(f"Wrote {output_dir / 'metrics.txt'}")


def evaluate(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    embedding_dim = checkpoint.get("embedding_dim", 512)

    model = NosePrintEmbedder(embedding_dim=embedding_dim, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)

    gallery_dir = getattr(args, "gallery_dir", None)
    probe_dir = getattr(args, "probe_dir", None)
    output_dir = Path(args.output_dir)

    if gallery_dir and probe_dir:
        logger.info("Gallery-probe protocol (train=gallery, val=probe)")
        gallery_emb, gallery_lab = extract_all_embeddings(model, gallery_dir, args.img_size, str(device))
        probe_emb, probe_lab = extract_all_embeddings(model, probe_dir, args.img_size, str(device))
        result = evaluate_gallery_probe(gallery_emb, gallery_lab, probe_emb, probe_lab)
        logger.info(f"Probes used: {result['n_probe']}  Rank-1: {result['rank1']:.4f}")
        _write_roc_outputs(
            result["scores"],
            result["labels"],
            output_dir,
            extra_lines=[
                f"Protocol: gallery-probe",
                f"Rank-1: {result['rank1']:.6f}",
                f"Probes: {result['n_probe']}",
                f"Gallery images: {len(gallery_emb)}",
                f"Probe images: {len(probe_emb)}",
            ],
        )
        logger.info("Evaluation complete!")
        return

    logger.info("Extracting embeddings...")
    embeddings, labels = extract_all_embeddings(model, args.data_dir, args.img_size, str(device))
    logger.info(f"Extracted {len(embeddings)} embeddings across {len(set(labels))} dogs")
    similarities, pair_labels = build_pairs(embeddings, labels)
    _write_roc_outputs(
        similarities,
        pair_labels,
        output_dir,
        extra_lines=[
            f"Protocol: pairwise",
            f"Total Images: {len(embeddings)}",
            f"Total Dogs: {len(set(labels.tolist()))}",
        ],
    )
    logger.info("Evaluation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate nose-print model accuracy")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--data_dir", type=str, default="", help="Single folder for pairwise ROC")
    parser.add_argument("--gallery_dir", type=str, default=None)
    parser.add_argument("--probe_dir", type=str, default=None)
    parser.add_argument("--output_dir", type=str, default="./eval_results")
    parser.add_argument("--img_size", type=int, default=224)
    args = parser.parse_args()
    if not args.gallery_dir and not args.data_dir:
        raise SystemExit("Pass --data_dir or both --gallery_dir and --probe_dir")
    evaluate(args)
