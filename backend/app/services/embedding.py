"""
Embedding extraction service — the core "fingerprint" generator.
Uses a ResNet50-based metric learning model exported to ONNX.
Converts a cropped nose image into a 512-d embedding vector.
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """
    ResNet50 ONNX embedding model.
    Produces a 512-dimensional float vector ("nose fingerprint")
    such that same-dog photos cluster together in vector space.
    """

    def __init__(self):
        self.session = None
        self.input_name = None
        self.input_shape = None
        self._loaded = False

    def load(self):
        """Load the ONNX model. Called once at startup."""
        model_path = Path(settings.EMBEDDING_MODEL_PATH)
        if not model_path.exists():
            logger.warning(
                f"Embedding model not found at {model_path}. "
                "A placeholder random embedding will be generated. "
                "Train and export the ResNet50 model to enable real nose-print matching."
            )
            self._loaded = False
            return

        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape  # e.g., [1, 3, 224, 224]
        self._loaded = True
        logger.info(f"Embedding model loaded from {model_path}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def extract(self, nose_image: np.ndarray) -> np.ndarray:
        """
        Extract a 512-d embedding vector from a cropped nose image.

        Args:
            nose_image: BGR numpy array of the cropped nose region

        Returns:
            1-D numpy array of shape (512,), L2-normalized
        """
        if not self._loaded:
            # Phase 1 fallback: generate a deterministic placeholder embedding
            # based on image content (not random — so same image gives same vector)
            logger.debug("Embedding model not loaded, generating placeholder embedding")
            return self._placeholder_embedding(nose_image)

        # Preprocess: resize, normalize, convert to tensor format
        input_h = self.input_shape[2] if len(self.input_shape) == 4 else 224
        input_w = self.input_shape[3] if len(self.input_shape) == 4 else 224

        resized = cv2.resize(nose_image, (input_w, input_h))
        # ImageNet normalization (standard for ResNet50)
        img = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        img = img.transpose(2, 0, 1)  # HWC → CHW
        img = np.expand_dims(img, axis=0)  # Add batch dim

        # Run inference
        outputs = self.session.run(None, {self.input_name: img})
        embedding = outputs[0].flatten()

        # L2 normalize — critical for cosine similarity to work correctly
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _placeholder_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Generate a deterministic placeholder embedding from image content.
        NOT a real biometric — just ensures the pipeline works end-to-end
        before the real model is trained.
        """
        # Resize to a fixed size and flatten a portion as a seed
        small = cv2.resize(image, (32, 32))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        # Use pixel values as seed for reproducibility
        seed = int(np.sum(gray)) % (2**31)
        rng = np.random.RandomState(seed)
        embedding = rng.randn(settings.EMBEDDING_DIMENSION).astype(np.float32)
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding


# Singleton instance
embedding_extractor = EmbeddingExtractor()
