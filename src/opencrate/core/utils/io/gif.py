import os
import re
from typing import List, Union

import imageio
import numpy as np
import torch
from PIL import Image, ImageSequence


def _to_gif(images: List[Union[np.ndarray, torch.Tensor, Image.Image]], output_path: str, fps: int = 10):
    images_ = []
    for img in images:
        if isinstance(img, torch.Tensor):
            if len(img.shape) == 3:
                img = img.permute(1, 2, 0).numpy()
            elif img.shape[0] == 1:
                img = img[0].numpy()
            else:
                img = img.numpy()
        elif isinstance(img, Image.Image):
            img = np.array(img)
        elif isinstance(img, np.ndarray) and img.shape[0] == 1:
            img = img[0]

        img = (img - img.min()) / (img.max() - img.min())
        images_.append((img * 255.0).astype("uint8"))

    imageio.mimsave(output_path, images_, fps=fps)


def dir_to_gif(src_dir: os.PathLike, output_path: str, fps: int = 10):
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


def images_to_gif(images: List[Union[np.ndarray, torch.Tensor, Image.Image]], output_path: str, fps: int = 10):
    """
    Converts a list of images to a GIF.

    Args:
        images: List of images (supports numpy arrays, PyTorch tensors, and PIL images)
        output_path: Path where the GIF will be saved
        fps: Frames per second for the output GIF
    """
    # Directly use _to_gif helper function
    _to_gif(images, output_path, fps)


def gif_to_images(path: os.PathLike, transform=None):
    images_ = []
    for frame in ImageSequence.Iterator(Image.open(path)):
        if transform:
            frame = transform(frame)
        images_.append(frame)
    return images_
