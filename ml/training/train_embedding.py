"""
ResNet50 + ArcFace embedding model training pipeline.

Trains a metric learning model that produces 512-d embeddings for
dog nose-print identification. Uses ArcFace loss (additive angular
margin) — the current standard in biometric recognition.

Usage:
    python train_embedding.py --data_dir ./data/noseprints --epochs 50 --batch_size 32
"""

import argparse
import logging
import os
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import models
import numpy as np
from PIL import Image

from augmentations import get_train_transforms, get_val_transforms

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# Model Architecture
# ────────────────────────────────────────────

class NosePrintEmbedder(nn.Module):
    """
    ResNet50 backbone → 512-d embedding.
    Pretrained on ImageNet, fine-tuned for nose-print metric learning.
    """

    def __init__(self, embedding_dim: int = 512, pretrained: bool = True):
        super().__init__()

        # Load ResNet50 backbone
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        backbone = models.resnet50(weights=weights)

        # Remove the classification head
        self.features = nn.Sequential(*list(backbone.children())[:-1])  # Up to avgpool

        # Embedding projection head
        self.embedding = nn.Sequential(
            nn.Flatten(),
            nn.Linear(2048, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(1024, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input images [B, 3, 224, 224]
        Returns:
            L2-normalized embeddings [B, embedding_dim]
        """
        features = self.features(x)
        embedding = self.embedding(features)
        # L2 normalize — critical for cosine similarity matching
        embedding = nn.functional.normalize(embedding, p=2, dim=1)
        return embedding


# ────────────────────────────────────────────
# ArcFace Loss
# ────────────────────────────────────────────

class ArcFaceLoss(nn.Module):
    """
    Additive Angular Margin Loss (ArcFace).
    The current standard for face/biometric recognition.
    Pushes same-class embeddings closer, different-class farther apart
    in angular space.

    Reference: Deng et al., "ArcFace: Additive Angular Margin Loss
    for Deep Face Recognition," CVPR 2019.
    """

    def __init__(
        self,
        embedding_dim: int,
        num_classes: int,
        scale: float = 30.0,
        margin: float = 0.5,
    ):
        super().__init__()
        self.scale = scale
        self.margin = margin
        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)
        self.ce_loss = nn.CrossEntropyLoss()

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embeddings: L2-normalized embeddings [B, embedding_dim]
            labels: Ground truth class IDs [B]
        """
        # Normalize weights
        weight_norm = nn.functional.normalize(self.weight, p=2, dim=1)

        # Cosine similarity between embeddings and class centers
        cosine = torch.mm(embeddings, weight_norm.t())
        cosine = cosine.clamp(-1.0 + 1e-7, 1.0 - 1e-7)

        # Convert to angle
        theta = torch.acos(cosine)

        # Add angular margin to target class
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.unsqueeze(1), 1.0)

        output = torch.cos(theta + one_hot * self.margin)
        output *= self.scale

        return self.ce_loss(output, labels)


# ────────────────────────────────────────────
# Dataset
# ────────────────────────────────────────────

class NosePrintDataset(Dataset):
    """
    Dataset for nose-print images.
    Expected directory structure:
        data_dir/
            dog_001/
                img_001.jpg
                img_002.jpg
            dog_002/
                img_001.jpg
            ...
    Each subdirectory = one dog (one class).
    """

    def __init__(self, data_dir: str, transform=None):
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.samples = []  # (image_path, class_id)
        self.class_names = []

        # Scan directory
        class_dirs = sorted([d for d in self.data_dir.iterdir() if d.is_dir()])
        for class_id, class_dir in enumerate(class_dirs):
            self.class_names.append(class_dir.name)
            for img_path in class_dir.glob("*"):
                if img_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    self.samples.append((str(img_path), class_id))

        logger.info(
            f"Loaded {len(self.samples)} images from {len(self.class_names)} dogs"
        )

    @property
    def num_classes(self) -> int:
        return len(self.class_names)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        img_path, class_id = self.samples[idx]
        image = np.array(Image.open(img_path).convert("RGB"))

        if self.transform:
            augmented = self.transform(image=image)
            image = augmented["image"]

        return image, class_id


# ────────────────────────────────────────────
# Training Loop
# ────────────────────────────────────────────

def train(args):
    """Main training function."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # Dataset
    train_transforms = get_train_transforms(args.img_size)
    val_transforms = get_val_transforms(args.img_size)

    train_dataset = NosePrintDataset(
        os.path.join(args.data_dir, "train"),
        transform=train_transforms,
    )
    val_dataset = NosePrintDataset(
        os.path.join(args.data_dir, "val"),
        transform=val_transforms,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    # Model
    model = NosePrintEmbedder(
        embedding_dim=args.embedding_dim,
        pretrained=True,
    ).to(device)

    # Loss
    criterion = ArcFaceLoss(
        embedding_dim=args.embedding_dim,
        num_classes=train_dataset.num_classes,
        scale=args.arcface_scale,
        margin=args.arcface_margin,
    ).to(device)

    # Optimizer — different LR for backbone (pretrained) vs head (random init)
    backbone_params = list(model.features.parameters())
    head_params = list(model.embedding.parameters()) + list(criterion.parameters())

    optimizer = optim.Adam([
        {"params": backbone_params, "lr": args.lr * 0.1},  # Lower LR for pretrained backbone
        {"params": head_params, "lr": args.lr},
    ], weight_decay=args.weight_decay)

    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Training
    best_val_loss = float("inf")
    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    logger.info(f"AMP: {use_amp}")

    for epoch in range(args.epochs):
        # ── Train ──
        model.train()
        criterion.train()
        train_loss = 0.0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                embeddings = model(images)
                loss = criterion(embeddings, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()

            if (batch_idx + 1) % 100 == 0:
                logger.info(
                    f"Epoch [{epoch+1}/{args.epochs}] "
                    f"Batch [{batch_idx+1}/{len(train_loader)}] "
                    f"Loss: {loss.item():.4f}"
                )

        avg_train_loss = train_loss / len(train_loader)

        # ── Validate ──
        model.eval()
        criterion.eval()
        val_loss = 0.0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                with torch.amp.autocast("cuda", enabled=use_amp):
                    embeddings = model(images)
                    loss = criterion(embeddings, labels)
                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0

        scheduler.step()

        logger.info(
            f"Epoch [{epoch+1}/{args.epochs}] "
            f"Train Loss: {avg_train_loss:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | "
            f"LR: {scheduler.get_last_lr()[0]:.6f}"
        )

        # Save best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            checkpoint_path = checkpoint_dir / "best_model.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": avg_val_loss,
                "embedding_dim": args.embedding_dim,
                "num_classes": train_dataset.num_classes,
            }, checkpoint_path)
            logger.info(f"Saved best model to {checkpoint_path}")

    # Save final model
    final_path = checkpoint_dir / "final_model.pt"
    torch.save({
        "epoch": args.epochs,
        "model_state_dict": model.state_dict(),
        "embedding_dim": args.embedding_dim,
        "num_classes": train_dataset.num_classes,
    }, final_path)
    logger.info(f"Training complete! Final model: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train nose-print embedding model")
    parser.add_argument("--data_dir", type=str, required=True, help="Path to dataset directory")
    parser.add_argument("--checkpoint_dir", type=str, default="./checkpoints", help="Where to save checkpoints")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--img_size", type=int, default=224)
    parser.add_argument("--embedding_dim", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--arcface_scale", type=float, default=30.0)
    parser.add_argument("--arcface_margin", type=float, default=0.5)
    parser.add_argument(
        "--num_workers",
        type=int,
        default=0,
        help="DataLoader workers. 0 is safest on Windows.",
    )

    args = parser.parse_args()
    train(args)
