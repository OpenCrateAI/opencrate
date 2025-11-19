import os
from pathlib import Path
from typing import Any, Optional, Union


def save(
    data: Any,
    path: Union[str, Path],
    encoding: str = "utf-8",
) -> None:
    """Save data content to a file.

    Args:
        data: The data content to save
        path: Path to the output file
        encoding: File encoding (default: utf-8)

    Examples:
        >>> save("Hello world", "output.txt")
        >>> save("Content", Path("data/file.txt"))
        >>> save("UTF-8 data", "file.txt", encoding="utf-8")
    """

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding=encoding) as file:
        file.write(str(data))


def load(path: Union[str, Path], encoding: str = "utf-8", default: Optional[Any] = None) -> str:
    """Load text content from a file.

    Args:
        path: Path to the input file
        encoding: File encoding (default: utf-8)
        default: Default value if file doesn't exist or can't be read

    Returns:
        The text content from the file, or default value if specified

    Raises:
        FileNotFoundError: If file doesn't exist and no default provided

    Examples:
        >>> content = load("input.txt")
        >>> content = load(Path("data/file.txt"))
        >>> content = load("missing.txt", default="")
        >>> content = load("file.txt", encoding="latin-1")
    """
    try:
        with open(path, encoding=encoding) as file:
            return file.read()
    except FileNotFoundError:
        if default is not None:
            return default
        raise
