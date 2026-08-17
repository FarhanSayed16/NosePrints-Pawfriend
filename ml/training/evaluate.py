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
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=2)

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


def evaluate(args):
    """Run full evaluation: extract embeddings, build pairs, compute ROC."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model
    checkpoint = torch.load(args.checkpoint, map_location=device)
    embedding_dim = checkpoint.get("embedding_dim", 512)

    model = NosePrintEmbedder(embedding_dim=embedding_dim, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)

    logger.info("Extracting embeddings...")
    embeddings, labels = extract_all_embeddings(model, args.data_dir, args.img_size, device)
    logger.info(f"Extracted {len(embeddings)} embeddings across {len(set(labels))} dogs")

    logger.info("Building pairs...")
    similarities, pair_labels = build_pairs(embeddings, labels)
    pos_count = int(pair_labels.sum())
    neg_count = len(pair_labels) - pos_count
    logger.info(f"Built {len(pair_labels)} pairs: {pos_count} positive, {neg_count} negative")

    # ROC Curve
    fpr, tpr, thresholds = roc_curve(pair_labels, similarities)
    auc = roc_auc_score(pair_labels, similarities)

    logger.info(f"\n{'='*50}")
    logger.info(f"  AUC (Area Under ROC Curve): {auc:.4f}")
    logger.info(f"{'='*50}")

    # Find optimal threshold (Youden's J statistic)
    j_scores = tpr - fpr
    optimal_idx = np.argmax(j_scores)
    optimal_threshold = thresholds[optimal_idx]
    optimal_tpr = tpr[optimal_idx]
    optimal_fpr = fpr[optimal_idx]

    logger.info(f"  Optimal threshold: {optimal_threshold:.4f}")
    logger.info(f"  At this threshold:")
    logger.info(f"    True Positive Rate (recall):  {optimal_tpr:.4f}")
    logger.info(f"    False Positive Rate (FAR):    {optimal_fpr:.4f}")
    logger.info(f"    False Reject Rate (FRR):      {1 - optimal_tpr:.4f}")

    # Performance at specific thresholds
    logger.info(f"\n  Performance at key thresholds:")
    for thresh in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        idx = np.argmin(np.abs(thresholds - thresh))
        logger.info(
            f"    threshold={thresh:.2f}: "
            f"TPR={tpr[idx]:.4f}, FPR={fpr[idx]:.4f}, "
            f"FRR={1-tpr[idx]:.4f}"
        )

    # Plot ROC curve
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 8))
    plt.plot(fpr, tpr, "b-", linewidth=2, label=f"ROC Curve (AUC = {auc:.4f})")
    plt.plot([0, 1], [0, 1], "r--", linewidth=1, label="Random")
    plt.scatter(
        [optimal_fpr], [optimal_tpr],
        color="green", s=100, zorder=5,
        label=f"Optimal (threshold={optimal_threshold:.3f})",
    )
    plt.xlabel("False Positive Rate (FAR)", fontsize=14)
    plt.ylabel("True Positive Rate (1 - FRR)", fontsize=14)
    plt.title("NosePrint Matching — ROC Curve", fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "roc_curve.png", dpi=150)
    logger.info(f"ROC curve saved to {output_dir / 'roc_curve.png'}")

    # Similarity distribution plot
    plt.figure(figsize=(10, 6))
    pos_sims = similarities[pair_labels == 1]
    neg_sims = similarities[pair_labels == 0]
    plt.hist(neg_sims, bins=100, alpha=0.6, color="red", label="Different dogs (negative)")
    plt.hist(pos_sims, bins=100, alpha=0.6, color="green", label="Same dog (positive)")
    plt.axvline(x=optimal_threshold, color="blue", linestyle="--", label=f"Threshold = {optimal_threshold:.3f}")
    plt.xlabel("Cosine Similarity Score", fontsize=14)
    plt.ylabel("Count", fontsize=14)
    plt.title("Similarity Score Distribution", fontsize=16)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig(output_dir / "similarity_distribution.png", dpi=150)
    logger.info(f"Similarity distribution saved to {output_dir / 'similarity_distribution.png'}")

    # Save metrics to file
    with open(output_dir / "metrics.txt", "w") as f:
        f.write(f"AUC: {auc:.6f}\n")
        f.write(f"Optimal Threshold: {optimal_threshold:.6f}\n")
        f.write(f"TPR at Optimal: {optimal_tpr:.6f}\n")
        f.write(f"FPR at Optimal: {optimal_fpr:.6f}\n")
        f.write(f"Total Pairs: {len(pair_labels)}\n")
        f.write(f"Positive Pairs: {pos_count}\n")
        f.write(f"Negative Pairs: {neg_count}\n")
        f.write(f"Total Images: {len(embeddings)}\n")
        f.write(f"Total Dogs: {len(set(labels))}\n")

    logger.info("Evaluation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate nose-print model accuracy")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--data_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./eval_results")
    parser.add_argument("--img_size", type=int, default=224)
    args = parser.parse_args()

    evaluate(args)
