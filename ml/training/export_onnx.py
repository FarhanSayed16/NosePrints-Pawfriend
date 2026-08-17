"""
Export trained PyTorch models to ONNX format for production inference.

Usage:
    python export_onnx.py --checkpoint ./checkpoints/best_model.pt --output ../backend/models/embedding_model.onnx
"""

import argparse
import logging

import torch
from train_embedding import NosePrintEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_embedding_model(checkpoint_path: str, output_path: str, img_size: int = 224):
    """Export the embedding model to ONNX."""

    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    embedding_dim = checkpoint.get("embedding_dim", 512)

    # Reconstruct model
    model = NosePrintEmbedder(embedding_dim=embedding_dim, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Dummy input
    dummy_input = torch.randn(1, 3, img_size, img_size)

    # Export
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["input"],
        output_names=["embedding"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "embedding": {0: "batch_size"},
        },
        opset_version=17,
        do_constant_folding=True,
    )

    logger.info(f"Exported embedding model to {output_path}")
    logger.info(f"  Input shape:  [batch, 3, {img_size}, {img_size}]")
    logger.info(f"  Output shape: [batch, {embedding_dim}]")

    # Verify
    import onnxruntime as ort
    import numpy as np

    session = ort.InferenceSession(output_path)
    test_input = np.random.randn(1, 3, img_size, img_size).astype(np.float32)
    result = session.run(None, {"input": test_input})
    logger.info(f"  Verification: output shape = {result[0].shape} ✓")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export model to ONNX")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to .pt checkpoint")
    parser.add_argument("--output", type=str, required=True, help="Output .onnx path")
    parser.add_argument("--img_size", type=int, default=224)
    args = parser.parse_args()

    export_embedding_model(args.checkpoint, args.output, args.img_size)
