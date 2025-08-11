from typing import Any, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import ImageGrid
from PIL import Image


def _prepare_cmap_alpha(
    cmap: Optional[Union[str, Sequence[Optional[str]]]],
    alpha: Union[float, Sequence[Optional[float]]],
    count: int,
) -> Tuple[List[Optional[str]], List[Optional[float]]]:
    """Prepare colormap and alpha values for multiple images."""
    if not isinstance(count, int) or count <= 0:
        raise ValueError(f"count must be a positive integer, got {count}")

    # Handle colormap
    if isinstance(cmap, str) or cmap is None:
        cmap_list: List[Optional[str]] = [cmap] * count
    elif isinstance(cmap, (list, tuple)):
        cmap_list = list(cmap)[:count] + [None] * max(0, count - len(cmap))
    else:
        raise TypeError(f"cmap must be str, None, or sequence, got {type(cmap)}")

    # Handle alpha values
    if isinstance(alpha, (int, float)):
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
        alpha_list: List[Optional[float]] = [float(alpha)] * count
    elif isinstance(alpha, (list, tuple)):
        alpha_list = []
        for i, a in enumerate(alpha[:count]):
            if a is not None:
                if not isinstance(a, (int, float)) or not (0.0 <= a <= 1.0):
                    raise ValueError(
                        f"alpha[{i}] must be between 0 and 1 or None, got {a}"
                    )
                alpha_list.append(float(a))
            else:
                alpha_list.append(None)
        alpha_list += [None] * max(0, count - len(alpha_list))
    else:
        raise TypeError(f"alpha must be number or sequence, got {type(alpha)}")

    return cmap_list, alpha_list


def _normalize_image(image: npt.NDArray[Any]) -> npt.NDArray[Any]:
    """Normalize image to [0, 1] range."""
    if not isinstance(image, np.ndarray):
        raise TypeError(f"Expected numpy array, got {type(image)}")

    if image.size == 0:
        raise ValueError("Cannot normalize empty array")

    image = image.astype(np.float32)
    img_min, img_max = image.min(), image.max()

    # Handle constant images (all pixels same value)
    if img_max == img_min:
        # If all values are already in [0,1], keep them; otherwise set to 0.5
        if 0.0 <= img_min <= 1.0:
            return np.full_like(image, img_min)
        else:
            return np.full_like(image, 0.5)

    # Normal case: scale to [0, 1]
    return (image - img_min) / (img_max - img_min)


def _standardize_image_format(
    image: Union[npt.NDArray[Any], Image.Image],
    bgr2rgb: bool = False,
    normalize: bool = True,
) -> npt.NDArray[Any]:
    """
    Convert image to standard format for matplotlib display.

    Supports all formats:
    - (H, W) - grayscale
    - (1, H, W) - grayscale with batch/channel dimension
    - (H, W, 1) - grayscale with channel dimension
    - (3, H, W) - RGB with channel-first
    - (H, W, 3) - RGB with channel-last
    """
    # Convert PIL Image to numpy array
    if isinstance(image, Image.Image):
        np_image = np.array(image)
    elif not isinstance(image, np.ndarray):
        raise TypeError(f"Expected numpy array or PIL Image, got {type(image)}")
    else:
        np_image = image

    if image.size == 0:
        raise ValueError("Cannot process empty image")

    # Handle different image formats
    if len(np_image.shape) == 2:
        # (H, W) - already in correct format for grayscale
        pass
    elif len(np_image.shape) == 3:
        if np_image.shape[0] == 1:
            # (1, H, W) - remove batch/channel dimension
            np_image = np_image[0]
        elif np_image.shape[-1] == 1:
            # (H, W, 1) - remove last dimension
            np_image = np_image[:, :, 0]
        elif np_image.shape[0] == 3:
            # (3, H, W) - move channel to last
            np_image = np.transpose(np_image, (1, 2, 0))
        elif np_image.shape[-1] == 3:
            # (H, W, 3) - already in correct format
            pass
        else:
            raise ValueError(f"Unsupported np_image shape: {np_image.shape}")
    else:
        raise ValueError(f"Unsupported np_image dimensions: {len(np_image.shape)}D")

    # Convert BGR to RGB if requested (only for 3-channel images)
    if bgr2rgb and len(np_image.shape) == 3 and np_image.shape[-1] == 3:
        np_image = np_image[:, :, [2, 1, 0]]  # BGR -> RGB

    # Normalize if requested
    if normalize:
        np_image = _normalize_image(np_image)

    return np_image


def image_stack(
    stack_lists: List[List[Union[Image.Image, npt.NDArray[Any]]]],
    titles: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (8, 8),
    bgr2rgb: bool = False,
    normalize: bool = True,
    cmap: Optional[Union[str, List[Optional[str]]]] = None,
    alpha: Union[float, List[Optional[float]]] = 1.0,
    save: Optional[str] = None,
) -> None:
    """
    Display images in a stack grid format.

    Args:
        stack_lists: List of image lists, each representing a column
        titles: Optional titles for each column
        figsize: Figure size (width, height)
        bgr2rgb: Whether to convert BGR to RGB
        normalize: Whether to normalize images
        cmap: Colormap(s) to use
        alpha: Alpha value(s) for transparency
        save: Path to save the figure
    """
    # Validate input types
    if not isinstance(stack_lists, list):
        raise TypeError(f"stack_lists must be a list, got {type(stack_lists)}")

    if not stack_lists:
        raise ValueError("stack_lists cannot be empty")

    if not all(isinstance(col, list) for col in stack_lists):
        raise TypeError("stack_lists must be a list of lists")

    if any(not col for col in stack_lists):
        raise ValueError("All columns in stack_lists must be non-empty")

    # Check that all columns have the same length
    column_lengths = [len(col) for col in stack_lists]
    if len(set(column_lengths)) > 1:
        raise ValueError(
            f"All columns must have the same length, got lengths: {column_lengths}"
        )

    if titles is not None:
        if not isinstance(titles, list):
            raise TypeError(f"titles must be a list or None, got {type(titles)}")
        if len(stack_lists) != len(titles):
            raise ValueError(
                f"Number of titles ({len(titles)}) must match number of columns ({len(stack_lists)})"
            )

    num_rows = len(stack_lists[0])
    num_cols = len(stack_lists)

    # Flatten the grid
    images = [img for col in stack_lists for img in col]

    fig = plt.figure(figsize=figsize)
    grid = ImageGrid(fig, 111, nrows_ncols=(num_rows, num_cols), axes_pad=0.02)

    cmap, alpha = _prepare_cmap_alpha(cmap, alpha, len(images))

    for i, (image, cm, a) in enumerate(zip(images, cmap, alpha)):
        if i >= len(grid):
            break
        ax = grid[i]
        processed_image = _standardize_image_format(image, bgr2rgb, normalize)
        ax.imshow(processed_image, cmap=cm, alpha=a)
        ax.axis("off")

    if titles:
        plt.suptitle(" | ".join(titles))

    if save:
        plt.savefig(save, bbox_inches="tight", dpi=150)

    plt.show()


def image_grid(
    grid_list: Union[List[Union[Image.Image, npt.NDArray[Any]]], npt.NDArray[Any]],  # type: ignore
    shape: Tuple[int, int] = (3, 3),
    figsize: int = 10,
    bgr2rgb: bool = False,
    normalize: bool = True,
    cmap: Optional[Union[str, List[Optional[str]]]] = None,
    alpha: Union[float, List[Optional[float]]] = 1.0,
    title: Optional[str] = None,
    save: Optional[str] = None,
) -> Figure:
    """
    Display images in a grid format.

    Args:
        grid_list: List of images or batch of images as numpy array
        shape: Grid shape (rows, cols)
        figsize: Figure size
        bgr2rgb: Whether to convert BGR to RGB
        normalize: Whether to normalize images
        cmap: Colormap(s) to use
        alpha: Alpha value(s) for transparency
        title: Figure title
        save: Path to save the figure
    """
    # Validate inputs
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise TypeError("shape must be a tuple or list of length 2")

    if not all(isinstance(x, int) and x > 0 for x in shape):
        raise ValueError("shape values must be positive integers")

    if not isinstance(figsize, (int, float)) or figsize <= 0:
        raise ValueError("figsize must be a positive number")

    # Handle numpy array input (batch of images)
    if isinstance(grid_list, np.ndarray):
        if len(grid_list.shape) == 4:  # type: ignore # Batch of images
            grid_list = [
                grid_list[i] for i in range(min(len(grid_list), shape[0] * shape[1]))
            ]
        else:
            raise ValueError(
                f"Expected 4D array for batch input, got {len(grid_list.shape)}D"
            )  # type: ignore
    elif not isinstance(grid_list, list):
        raise TypeError(
            f"grid_list must be a list or numpy array, got {type(grid_list)}"
        )

    if not grid_list:
        raise ValueError("grid_list cannot be empty")

    # Limit to grid size
    max_images = shape[0] * shape[1]
    grid_list = grid_list[:max_images]

    fig = plt.figure(figsize=(figsize, figsize))
    grid = ImageGrid(fig, 111, nrows_ncols=shape, axes_pad=0.02)

    cmap, alpha = _prepare_cmap_alpha(cmap, alpha, len(grid_list))

    for i, image in enumerate(grid_list):
        if i >= len(grid):
            break
        ax = grid[i]
        processed_image = _standardize_image_format(image, bgr2rgb, normalize)
        ax.imshow(processed_image, cmap=cmap[i], alpha=alpha[i])
        ax.axis("off")

    # Turn off remaining axes if we have fewer images than grid slots
    for i in range(len(grid_list), len(grid)):
        grid[i].axis("off")

    if title:
        fig.suptitle(title)

    plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.08)

    if save:
        plt.savefig(save, bbox_inches="tight", dpi=150)

    return fig


def labeled_images(
    image_batch: Union[List[Union[Image.Image, npt.NDArray[Any]]], npt.NDArray[Any]],  # type: ignore
    label_batch: Union[List, npt.NDArray[Any]],  # type: ignore
    shape: Tuple[int, int],
    label_names: Optional[List[str]] = None,
    figsize: int = 10,
    title: Optional[str] = None,
    bgr2rgb: bool = False,
    normalize: bool = True,
    save: Optional[str] = None,
    cmap: Optional[Union[str, List[Optional[str]]]] = None,
    alpha: Union[float, List[Optional[float]]] = 1.0,
    show: bool = True,
) -> Figure:
    """
    Display labeled images in a grid format.

    Args:
        image_batch: Batch of images
        label_batch: Corresponding labels
        shape: Grid shape (rows, cols)
        label_names: Optional mapping from label indices to names
        figsize: Figure size
        title: Figure title
        bgr2rgb: Whether to convert BGR to RGB
        normalize: Whether to normalize images
        save: Path to save the figure
        cmap: Colormap(s) to use
        alpha: Alpha value(s) for transparency
        show: Whether to display the figure
    """
    # Validate inputs
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise TypeError("shape must be a tuple or list of length 2")

    if not all(isinstance(x, int) and x > 0 for x in shape):
        raise ValueError("shape values must be positive integers")

    if not isinstance(figsize, (int, float)) or figsize <= 0:
        raise ValueError("figsize must be a positive number")

    # Convert numpy arrays to lists for easier handling
    if isinstance(image_batch, np.ndarray):
        if len(image_batch) == 0:
            raise ValueError("image_batch cannot be empty")
        image_batch = [image_batch[i] for i in range(len(image_batch))]
    elif isinstance(image_batch, list):
        if not image_batch:
            raise ValueError("image_batch cannot be empty")
    else:
        raise TypeError(
            f"image_batch must be a list or numpy array, got {type(image_batch)}"
        )

    if isinstance(label_batch, np.ndarray):
        label_batch = label_batch.tolist()
    elif not isinstance(label_batch, list):
        raise TypeError(
            f"label_batch must be a list or numpy array, got {type(label_batch)}"
        )

    # Check lengths before limiting
    if len(image_batch) != len(label_batch):
        raise ValueError(
            f"Number of images ({len(image_batch)}) must match number of labels ({len(label_batch)})"
        )

    # Limit to grid size
    max_images = shape[0] * shape[1]
    image_batch = image_batch[:max_images]
    label_batch = label_batch[:max_images]

    if label_names is not None:
        if not isinstance(label_names, list):
            raise TypeError(
                f"label_names must be a list or None, got {type(label_names)}"
            )

    fig = plt.figure(figsize=(figsize, figsize))
    grid = ImageGrid(fig, 111, nrows_ncols=shape, axes_pad=0.05)

    cmap, alpha = _prepare_cmap_alpha(cmap, alpha, len(image_batch))

    for i, (image, label) in enumerate(zip(image_batch, label_batch)):
        if i >= len(grid):
            break
        ax = grid[i]
        processed_image = _standardize_image_format(image, bgr2rgb, normalize)
        ax.imshow(processed_image, cmap=cmap[i], alpha=alpha[i])
        ax.axis("off")

        # Set label as title
        try:
            if label_names is None:
                label_text = str(label)
            else:
                label_idx = int(label)
                if label_idx < 0 or label_idx >= len(label_names):
                    raise IndexError(
                        f"Label index {label_idx} out of range for label_names of length {len(label_names)}"
                    )
                label_text = str(label_names[label_idx])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid label at index {i}: {label}") from e

        ax.set_title(label_text, fontsize=8)

    # Turn off remaining axes
    for i in range(len(image_batch), len(grid)):
        grid[i].axis("off")

    if title:
        fig.suptitle(title)

    if save:
        plt.savefig(save, bbox_inches="tight", dpi=150)

    if show:
        plt.show()

    return fig
