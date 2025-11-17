import os
from typing import Any, Union

import cv2
import matplotlib.figure
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# Define a type hint for image-like data for better readability and type checking
ImageType = Union[NDArray[Any], "Image.Image", "matplotlib.figure.Figure"]


def load(path: str, lib: str = "pil", **kwargs) -> Union[NDArray[Any], Image.Image]:
    """
    Load an image from a file path using either PIL or OpenCV.

    This function provides a unified interface for loading images using different backends
    (PIL or OpenCV) while handling common image formats.

    Args:
        path (str): Path to the image file to load.
        lib (str, optional): Library to use for loading. Defaults to "pil".
            - "pil": Use PIL/Pillow library
            - "cv2": Use OpenCV library

    Returns:
        Union[np.ndarray, Image.Image]: Loaded image.
            - When using PIL: Returns PIL Image object
            - When using OpenCV: Returns numpy array

    Raises:
        FileNotFoundError: If the specified file path does not exist.
        ValueError: If an unsupported library is specified or image cannot be loaded.
        IOError: If there's an error during the image loading process.

    Examples:
        Load an image using PIL (default):
        >>> img = load("path/to/image.jpg")

        Load an image using OpenCV:
        >>> img = load("path/to/image.jpg", lib="cv2")
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    # try:
    if lib == "pil":
        return Image.open(path, **kwargs)

    elif lib == "cv2":
        img = cv2.imread(path, **kwargs)
        if img is None:
            raise ValueError(f"Could not load image from {path}")
        return img

    else:
        raise ValueError(f"Unsupported library: {lib}. Supported libraries are 'pil' and 'cv2'.")

    # except Exception as e:
    #     raise IOError(f"Failed to load image from {path}: {e}")


def save(data: ImageType, path: str, renormalize: bool = True, **kwargs: Any) -> None:
    # Ensure the output directory exists
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        if isinstance(data, np.ndarray):
            # Handle NumPy array
            image = data.copy()  # Avoid modifying the original array

            # Handle different numpy array formats
            if image.ndim == 2:  # Grayscale (H, W)
                pass  # Keep as is
            elif image.ndim == 3:
                if image.shape[0] == 1:  # (1, H, W) -> (H, W)
                    image = image.squeeze(0)
                elif image.shape[0] == 3:  # (3, H, W) -> (H, W, 3)
                    image = np.transpose(image, (1, 2, 0))
                elif image.shape[2] == 1:  # (H, W, 1) -> (H, W)
                    image = image.squeeze(axis=2)
                elif image.shape[2] == 3:  # (H, W, 3)
                    pass  # Keep as is
                else:
                    raise ValueError(f"Unsupported image shape {image.shape}. Supported formats: (H, W), (H, W, 1), (H, W, 3), (1, H, W), (3, H, W)")
            else:
                raise ValueError(f"Unsupported image dimensions {image.ndim}. Only 2D and 3D arrays are supported.")

            # Normalize to [0, 255] if not already uint8
            if renormalize and image.dtype != np.uint8:
                np_image = image.astype("float32")
                # Avoid division by zero if the image is flat
                ptp = np.ptp(np_image)
                if ptp > 0:
                    np_image = (np_image - np_image.min()) / ptp
                np_image *= 255.0
                image = np_image.astype("uint8")

            # Convert to PIL and save
            pil_image = Image.fromarray(image)
            pil_image.save(path, **kwargs)

        elif isinstance(data, Image.Image):
            data.save(path, **kwargs)

        elif isinstance(data, matplotlib.figure.Figure):
            kwargs.setdefault("bbox_inches", "tight")
            data.savefig(path, **kwargs)

        else:
            supported_types = "np.ndarray, PIL.Image.Image, or matplotlib.figure.Figure"
            raise ValueError(f"Unsupported data type: {type(data)}. Supported types are {supported_types}.")

    except Exception as e:
        raise OSError(f"Failed to save image to {path}: {e}")
