"""
Data augmentation pipeline for nose-print images.
Heavy augmentation is critical when training with few images per dog.
"""

import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2


def get_train_transforms(img_size: int = 224) -> A.Compose:
    """
    Training augmentations — heavy, to compensate for few images per dog.
    Includes geometric, color, and noise augmentations.
    """
    return A.Compose([
        A.Resize(img_size, img_size),
        # Geometric
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=30, p=0.7, border_mode=cv2.BORDER_REFLECT_101),
        A.Affine(
            scale=(0.85, 1.15),
            translate_percent={"x": (-0.1, 0.1), "y": (-0.1, 0.1)},
            rotate=(-15, 15),
            shear=(-10, 10),
            p=0.5,
        ),
        A.Perspective(scale=(0.02, 0.08), p=0.3),
        # Color / lighting
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
        A.HueSaturationValue(
            hue_shift_limit=10, sat_shift_limit=30, val_shift_limit=30, p=0.5
        ),
        A.CLAHE(clip_limit=4.0, p=0.3),
        A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05, p=0.3),
        # Noise / degradation (simulates real phone camera conditions)
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.4),
        A.GaussianBlur(blur_limit=(3, 5), p=0.2),
        A.MotionBlur(blur_limit=5, p=0.15),
        A.ImageCompression(quality_lower=60, quality_upper=95, p=0.3),
        # Cutout (occlusion robustness)
        A.CoarseDropout(
            max_holes=4, max_height=20, max_width=20,
            min_holes=1, fill_value=0, p=0.3,
        ),
        # Normalize for ResNet50 (ImageNet stats)
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
        ToTensorV2(),
    ])


def get_val_transforms(img_size: int = 224) -> A.Compose:
    """Validation transforms — minimal, just resize and normalize."""
    return A.Compose([
        A.Resize(img_size, img_size),
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
        ToTensorV2(),
    ])
