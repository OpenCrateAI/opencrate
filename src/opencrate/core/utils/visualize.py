from typing import List, Optional, Tuple, Union

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from mpl_toolkits.axes_grid1 import ImageGrid
from PIL import Image


def _get_cmap_alpha(cmap, alpha, cols):
    if not isinstance(cmap, str):
        cmap = cmap or [None] * cols
    else:
        cmap = [cmap] * cols
    if not isinstance(alpha, float):
        alpha = alpha or [None] * cols
    else:
        alpha = [alpha] * cols

    return cmap, alpha


def _normalize(image: Union[np.ndarray, torch.Tensor]):
    if isinstance(image, np.ndarray):
        image = image.astype("float32")
    elif isinstance(image, torch.Tensor):
        image = image.float()

    return (image - image.min()) / (image.max() - image.min())


def _get_plt_image(image, bgr2rgb: bool = False, normalize_image: bool = True):
    if isinstance(image, np.ndarray) and bgr2rgb:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    if normalize_image and not isinstance(image, Image.Image):
        image = _normalize(image)

    if isinstance(image, torch.Tensor):
        image = (
            image.detach().cpu().permute(1, 2, 0).numpy()
            if len(image.shape) == 3
            else image.detach().cpu().numpy()
        )

    if isinstance(image, np.ndarray):
        if image.shape[-1] == 1:
            image = image[:, :, 0]
        elif image.shape[0] == 1:
            image = image[0]

    return image


def image_stack(
    stack_lists: List[Union[Image.Image, np.ndarray, torch.Tensor]],
    titles: Optional[List[str]] = None,
    shape: Tuple[float, float] = (8, 8),
    bgr2rgb: bool = True,
    normalize: bool = True,
    cmap: Optional[str] = None,
    alpha: float = 1.0,
    save: bool = False,
) -> None:
    if titles:
        assert len(stack_lists) == len(titles), (
            f'\n\nTitles must be provided for each image columns, found total "{len(titles)}" titles, while total image columns are "{len(stack_lists)}".\n'
        )

    fig = plt.figure(figsize=shape)
    first_elem = stack_lists[0]
    if isinstance(first_elem, (list, np.ndarray, torch.Tensor)):
        shape = (len(first_elem), len(stack_lists))
    else:
        raise TypeError(f"Unsupported type {type(first_elem)} in stack_lists")
    grid = ImageGrid(fig, 111, nrows_ncols=shape, axes_pad=0.02)
    grid_list = []

    for col in zip(*stack_lists):
        for i in range(len(col)):
            grid_list.append(col[i])

    for ax, image in zip(grid, grid_list):  # type: ignore
        ax.imshow(image, cmap=cmap, alpha=alpha)  # type: ignore
        ax.axis("off")  # type: ignore

    if titles is not None:
        plt.title(" | ".join(titles))
    if save:
        plt.savefig(save)
    plt.show()


def image_grid(
    grid_list: List[Union[Image.Image, np.ndarray, torch.Tensor]],
    shape: Tuple[float, float] = (6, 6),
    size: int = 10,
    bgr2rgb: bool = True,
    normalize: bool = True,
    cmap=None,
    alpha=1.0,
    title: Optional[str] = None,
) -> plt.Figure:
    fig = plt.figure(figsize=(size, size))
    grid = ImageGrid(fig, 111, nrows_ncols=shape, axes_pad=0.02)

    cmap, alpha = _get_cmap_alpha(cmap, alpha, len(grid_list))

    for idx, (ax, image) in enumerate(zip(grid, grid_list)):  # type: ignore
        # for 1 channel or no channel show image in gray
        ax.imshow(
            _get_plt_image(image, bgr2rgb, normalize), cmap=cmap[idx], alpha=alpha[idx]
        )
        ax.axis("off")

    if title is not None:
        fig.suptitle(title)

    plt.subplots_adjust(left=0.08, right=0.92, top=0.92, bottom=0.08)
    return fig


def labeled_images(
    image_batch: torch.Tensor,
    label_batch: torch.Tensor,
    shape: Tuple[int],
    label_names: Optional[List[str]] = None,
    size: int = 10,
    title: Optional[str] = None,
    bgr2rgb: bool = True,
    normalize: bool = True,
    save: Optional[bool] = None,
    cmap=None,
    alpha=1.0,
    show=True,
) -> None:
    fig = plt.figure(figsize=(size, size))
    grid = ImageGrid(fig, 111, nrows_ncols=shape, axes_pad=0.05)

    cmap, alpha = _get_cmap_alpha(cmap, alpha, int(shape[0] * shape[1]))

    for idx, (ax, image, label) in enumerate(zip(grid, image_batch, label_batch)):  # type: ignore
        ax.imshow(
            _get_plt_image(image, bgr2rgb, normalize), cmap=cmap[idx], alpha=alpha[idx]
        )  # type: ignore
        ax.axis("off")
        ax.set_title(f"{label}" if label_names is None else f"{label_names[label]}")

    if title is not None:
        print(title)
    if save:
        plt.savefig(save)
    if show:
        plt.show()
