import os
import re
from typing import Any, List, Sequence, Union

import imageio
import numpy as np
import numpy.typing as npt
from PIL import Image, ImageSequence


def _to_gif(
    images: Sequence[Union[npt.NDArray[Any], Image.Image]],
    output_path: str,
    fps: int = 10,
) -> None:
    images_ = []
    for img in images:
        if isinstance(img, Image.Image):
            img = np.array(img)
        elif isinstance(img, np.ndarray) and len(img.shape) == 3 and img.shape[0] == 1:
            # Remove batch dimension if present (shape: [1, H, W] or [1, H, W, C])
            img = img[0]

        # Ensure img is numpy array at this point
        if not isinstance(img, np.ndarray):
            raise TypeError(f"Unsupported image type: {type(img)}. Expected numpy.ndarray or PIL.Image")

        # Normalize to [0, 1] range
        img_min, img_max = img.min(), img.max()
        if img_max > img_min:
            img_ = (img - img_min) / (img_max - img_min)
        else:
            # Handle constant images
            img_ = np.zeros_like(img)

        # Convert to uint8 [0, 255] range
        images_.append((img_ * 255.0).astype(np.uint8))

    imageio.mimsave(output_path, images_, fps=fps)


def dir_to_gif(src_dir: str, output_path: str, fps: int = 10) -> None:
    """
    Converts all images in a directory to a GIF.

    Args:
        src_dir: Directory containing image files
        output_path: Path where the GIF will be saved
        fps: Frames per second for the output GIF
    """
    images = []

    # Sort files to ensure correct sequence
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]

    for filename in sorted(os.listdir(src_dir), key=natural_sort_key):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
            file_path = os.path.join(src_dir, filename)
            img = Image.open(file_path)
            images.append(img)

    if not images:
        raise ValueError(f"\n\nNo valid image files found in '{src_dir}' for creating the gif\n")

    # Use _to_gif helper function
    _to_gif(images, output_path, fps)


def images_to_gif(images: List[Union[npt.NDArray[Any], Image.Image]], output_path: str, fps: int = 10) -> None:
    """
    Converts a list of images to a GIF.

    Args:
        images: List of images (supports numpy arrays and PIL images)
        output_path: Path where the GIF will be saved
        fps: Frames per second for the output GIF
    """

    _to_gif(images, output_path, fps)


def gif_to_images(path: str, transform=None) -> List[Any]:
    images_ = []
    for frame in ImageSequence.Iterator(Image.open(path)):
        if transform:
            frame = transform(frame)
        images_.append(frame)
    return images_
