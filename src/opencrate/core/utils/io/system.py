import datetime
import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

import requests
from rich.console import Console
from rich.tree import Tree

PathLike = Union[str, Path]


def ensure_dir_exists(path: PathLike) -> Path:
    """Ensures that a directory exists.

    Args:
        path (PathLike): The path to the directory.

    Raises:
        FileNotFoundError: If the path does not exist or is not a directory.

    Returns:
        Path: The Path object of the directory.

    Example:
        Check if a directory exists:
        ```python
        # Assuming 'my_folder' exists
        oc.io.ensure_dir_exists("my_folder")
        ```
        ---
        Raise an error if the directory does not exist:
        ```python
        oc.io.ensure_dir_exists("non_existent_folder")
        ```
        Output:
        ```
        FileNotFoundError:

        Directory not found: non_existent_folder

        ```
    """
    p = Path(path)
    if not p.is_dir():
        raise FileNotFoundError(f"\n\nDirectory not found: {path}\n")
    return p


def ensure_file_exists(path: PathLike) -> Path:
    """Ensures that a file exists.

    Args:
        path (PathLike): The path to the file.

    Raises:
        FileNotFoundError: If the path does not exist or is not a file.

    Returns:
        Path: The Path object of the file.

    Example:
        Check if a file exists:
        ```python
        # Assuming 'my_file.txt' exists
        oc.io.ensure_file_exists("my_file.txt")
        ```
        ---
        Raise an error if the file does not exist:
        ```python
        oc.io.ensure_file_exists("non_existent_file.txt")
        ```
        Output:
        ```
        FileNotFoundError:

        File not found: non_existent_file.txt

        ```
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"\n\nFile not found: {path}\n")
    return p


def handle_replace(path: PathLike, replace: bool) -> None:
    """Handles the replacement of a file or directory if it exists.

    Args:
        path (PathLike): The path to the file or directory.
        replace (bool): If True, the file or directory will be deleted if it
            already exists.

    Raises:
        FileExistsError: If the file or directory already exists and `replace`
            is False.

    Example:
        Replace an existing file:
        ```python
        # Assuming 'data.txt' is a file that exists
        oc.io.handle_replace("data.txt", replace=True)
        ```
        Output:
        ```
        Replacing file data.txt
        File deleted: data.txt
        ```
        ---
        Replace an existing directory:
        ```python
        # Assuming 'my_folder' is a directory that exists
        oc.io.handle_replace("my_folder", replace=True)
        ```
        Output:
        ```
        Replacing directory my_folder
        Directory deleted: my_folder
        ```
        ---
        Raise an error if the path already exists and replace is False:
        ```python
        oc.io.handle_replace("data.txt", replace=False)
        ```
        Output:
        ```
        FileExistsError:
        Path already exists: data.txt.
        Pass `replace=True` if you want to replace the existing file or directory.
        ```
    """
    p = Path(path)
    if p.exists():
        if replace:
            if p.is_dir():
                print(f"Replacing directory {p}")
                delete_dir(p)
            else:
                print(f"Replacing file {p}")
                delete_file(p)
        else:
            raise FileExistsError(f"\nPath already exists: {p}.\nPass `replace=True` if you want to replace the existing file or directory.\n")


def create_dir(path: PathLike, replace: bool = False) -> None:
    """Creates a directory at the specified path.

    Args:
        path (PathLike): The path to the directory to be created.
        replace (bool): If True, the directory will be deleted if it already
            exists. Defaults to False.

    Raises:
        FileExistsError: If the directory already exists and `replace` is False.

    Example:
        Create a new directory:
        ```python
        oc.io.create_dir("new_folder")
        ```
        Output:
        ```
        Directory created: new_folder
        ```
        ---
        Replace an existing directory:
        ```python
        # Assuming 'existing_folder' already exists
        oc.io.create_dir("existing_folder", replace=True)
        ```
        Output:
        ```
        Replacing directory existing_folder
        Directory deleted: existing_folder
        Directory created: existing_folder
        ```
    """
    p = Path(path)
    handle_replace(p, replace)
    p.mkdir(parents=True, exist_ok=True)
    print(f"Directory created: {p}")


def delete_dir(path: PathLike) -> None:
    """Deletes a directory and all its contents recursively.

    Args:
        path (PathLike): The path to the directory to be deleted.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        Delete a directory:
        ```python
        # Assuming 'old_folder' exists
        oc.io.delete_dir("old_folder")
        ```
        Output:
        ```
        Directory deleted: old_folder
        ```
        ---
        Raise an error if the directory does not exist:
        ```python
        oc.io.delete_dir("non_existent_folder")
        ```
        Output:
        ```
        FileNotFoundError:

        Directory not found: non_existent_folder

        ```
    """
    p = ensure_dir_exists(path)
    shutil.rmtree(p)
    print(f"Directory deleted: {p}")


def list_dir(dir: str, extension: Optional[Union[List[str], str]] = None, recursive: bool = True) -> List[str]:
    """Recursively lists all files in a directory tree.

    Args:
        dir (str): The path to the directory.
        extension (Optional[List[str] | str]): The file extension(s) to filter by.
            Can be a single extension as a string or a list of extensions.
            Defaults to None.

    Returns:
        List[str]: A list of file paths.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        List all files:
        ```python
        files = oc.io.list_dir("my_folder")
        print(files)
        ```
        Output:
        ```
        ['my_folder/file1.txt', 'my_folder/subfolder/file2.log']
        ```
        ---
        List only files with a specific extension:
        ```python
        files = oc.io.list_dir("my_folder", extension="txt")
        print(files)
        ```
        Output:
        ```
        ['my_folder/file1.txt']
        ```
        ---
        List files with multiple extensions:
        ```python
        files = oc.io.list_dir("my_folder", extension=["txt", "log"])
        print(files)
        ```
        Output:
        ```
        ['my_folder/file1.txt', 'my_folder/subfolder/file2.log']
        ```
    """
    ensure_dir_exists(dir)

    if not recursive:
        return os.listdir(dir)

    file_paths: List[str] = []

    # Convert single extension to list for uniform handling
    if isinstance(extension, str):
        extensions = [extension]
    elif extension is None:
        extensions = None
    else:
        extensions = extension

    for root, _, files in os.walk(dir):
        for file in files:
            if extensions:
                if any(file.endswith(ext) for ext in extensions):
                    file_paths.append(os.path.join(root, file))
            else:
                file_paths.append(os.path.join(root, file))
    print(f"Found {len(file_paths)} files in {dir}")
    return file_paths


def show_files_in_dir(
    directory: PathLike,
    extensions: Optional[Union[str, List[str]]] = None,
    depth: Optional[int] = 2,
    verbose: bool = False,
) -> None:
    """Displays all files in a directory tree using Rich Tree structure.

    Args:
        directory (PathLike): The path to the directory.
        extensions (Optional[Union[str, List[str]]]): File extensions to filter by.
        depth (Optional[int]): Maximum depth to display. Defaults to 2.
        verbose (bool): If True, displays file modification time and size. Defaults to False.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        Show all files with default depth:
        ```python
        oc.io.show_files_in_dir("my_folder")
        ```
        ---
        Show only Python files with custom depth:
        ```python
        oc.io.show_files_in_dir("my_folder", extensions=".py", depth=3)
        ```
        ---
        Show files with multiple extensions and unlimited depth:
        ```python
        oc.io.show_files_in_dir("my_folder", extensions=[".py", ".txt"], depth=None)
        ```
        ---
        Show files with verbose information:
        ```python
        oc.io.show_files_in_dir("my_folder", verbose=True)
        ```
    """
    console = Console()
    dir_path = ensure_dir_exists(directory)

    tree = Tree(f"{dir_path.name}")

    extensions_list = extensions if isinstance(extensions, (list, tuple)) else [extensions] if extensions else None
    if extensions_list:
        extensions_list = [f".{ext.lstrip('.')}" for ext in extensions_list]

    def add_files_to_tree(current_path: Path, current_tree: Tree, current_level: int = 0):
        if depth is not None and current_level >= depth:
            return

        try:
            items = sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))

            for item in items:
                if item.is_dir():
                    dir_name = f"{item.name}/"
                    if verbose:
                        try:
                            stat = item.stat()
                            modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            size_str = get_size(item)
                            dir_name += f" [dim]({modified_time}, {size_str})[/dim]"
                        except (OSError, PermissionError):
                            dir_name += " [dim](Permission denied)[/dim]"
                    branch = current_tree.add(dir_name)
                    add_files_to_tree(item, branch, current_level + 1)
                elif extensions_list is None or item.suffix.lower() in extensions_list:
                    file_name = f"{item.name}"
                    if verbose:
                        try:
                            stat = item.stat()
                            modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            size_str = get_size(item)
                            file_name += f" [dim]({modified_time}, {size_str})[/dim]"
                        except (OSError, PermissionError):
                            file_name += " [dim](Permission denied)[/dim]"
                    current_tree.add(file_name)
        except PermissionError:
            current_tree.add("Permission denied")

    add_files_to_tree(dir_path, tree)
    console.print(tree)


def copy_dir(src: PathLike, dst: PathLike, replace: bool = False) -> None:
    """Copies a directory tree from the source to the destination.

    Args:
        src (PathLike): The source directory path.
        dst (PathLike): The destination directory path.
        replace (bool): If True, the destination directory will be deleted if
            it already exists. Defaults to False.

    Raises:
        FileNotFoundError: If the source directory does not exist.
        FileExistsError: If the destination directory already exists and
            `replace` is False.

    Example:
        Copy a directory to a new destination:
        ```python
        # Assuming 'source_folder' exists
        oc.io.copy_dir("source_folder", "destination_folder")
        ```
        ---
        Replace an existing destination directory:
        ```python
        # Assuming 'source_folder' and 'destination_folder' exist
        oc.io.copy_dir("source_folder", "destination_folder", replace=True)
        ```
        Output:
        ```
        Replacing directory destination_folder
        Directory deleted: destination_folder
        ```
    """
    src_path = ensure_dir_exists(src)
    handle_replace(dst, replace)
    shutil.copytree(src_path, dst)


def move_dir(src: PathLike, dst: PathLike, replace: bool = False) -> None:
    """Moves a directory from the source to the destination.

    Args:
        src (PathLike): The source directory path.
        dst (PathLike): The destination directory path.
        replace (bool): If True, the destination directory will be deleted if
            it already exists. Defaults to False.

    Raises:
        FileNotFoundError: If the source directory does not exist.
        FileExistsError: If the destination directory already exists and
            `replace` is False.

    Example:
        Move a directory:
        ```python
        # Assuming 'old_folder' exists
        oc.io.move_dir("old_folder", "new_folder")
        ```
        Output:
        ```
        Directory moved from old_folder to new_folder
        ```
        ---
        Replace an existing destination:
        ```python
        # Assuming 'old_folder' and 'new_folder' exist
        oc.io.move_dir("old_folder", "new_folder", replace=True)
        ```
        Output:
        ```
        Replacing directory new_folder
        Directory deleted: new_folder
        Directory moved from old_folder to new_folder
        ```
    """
    src_path = ensure_dir_exists(src)
    handle_replace(dst, replace)
    shutil.move(str(src_path), str(dst))
    print(f"Directory moved from {src_path} to {dst}")


def path_exists(path: PathLike) -> bool:
    """Checks if a path exists (file or directory).

    Args:
        path (PathLike): The path to check.

    Returns:
        bool: True if the path exists, False otherwise.

    Example:
        Check if a file exists:
        ```python
        exists = oc.io.path_exists("example.txt")
        print(exists)
        ```
        Output:
        ```
        True
        ```
        ---
        Check if a directory exists:
        ```python
        exists = oc.io.path_exists("my_folder")
        print(exists)
        ```
        Output:
        ```
        True
        ```
    """
    return Path(path).exists()


def get_size(path: PathLike, unit: Optional[str] = None) -> str:
    """Returns the size of a file or directory in human-readable format.

    This function calculates the total size of a file or directory (including all
    subdirectories and files recursively) and returns it in a human-readable format
    with appropriate units (Bytes, KB, MB, GB, TB). By default, it automatically
    selects the most suitable unit, but you can specify a particular unit if needed.

    Args:
        path (PathLike): The path to the file or directory.
        unit (Optional[str]): The unit to use for the size. Valid values are
            'Bytes', 'KB', 'MB', 'GB', 'TB'. If None, automatically selects
            the most suitable unit. Defaults to None.

    Returns:
        str: The size in the specified or auto-selected unit, formatted with
            up to 2 decimal places (e.g., '323 Bytes', '12.52 GB', '53.45 MB').

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If an invalid unit is specified.

    Example:
        Get the size with automatic unit selection:
        ```python
        size = oc.io.get_size("example.txt")
        print(size)
        ```
        Output:
        ```
        '1.23 KB'
        ```
        ---
        Get the size of a directory:
        ```python
        size = oc.io.get_size("my_folder")
        print(size)
        ```
        Output:
        ```
        '45.67 MB'
        ```
        ---
        Get the size in a specific unit:
        ```python
        size = oc.io.get_size("large_file.zip", unit="GB")
        print(size)
        ```
        Output:
        ```
        '2.34 GB'
        ```
        ---
        Get the size in bytes:
        ```python
        size = oc.io.get_size("small.txt", unit="Bytes")
        print(size)
        ```
        Output:
        ```
        '323 Bytes'
        ```
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")

    # Valid units and their conversion factors
    valid_units = ["Bytes", "KB", "MB", "GB", "TB"]
    if unit is not None and unit not in valid_units:
        raise ValueError(f"Invalid unit: {unit}. Valid units are: {', '.join(valid_units)}")

    # Calculate total size in bytes
    if p.is_file():
        size_bytes = p.stat().st_size
    else:
        size_bytes = 0
        try:
            for item in p.rglob("*"):
                if item.is_file():
                    try:
                        size_bytes += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass

    # Convert to specified unit or auto-select
    if unit is None:
        # Auto-select the most suitable unit
        if size_bytes == 0:
            return "0 Bytes"

        size_value = float(size_bytes)
        unit_index = 0
        while size_value >= 1024 and unit_index < len(valid_units) - 1:
            size_value /= 1024.0
            unit_index += 1

        selected_unit = valid_units[unit_index]
        # Format: no decimals for Bytes, up to 2 decimals for others
        if selected_unit == "Bytes":
            return f"{int(size_value)} {selected_unit}"
        else:
            return f"{size_value:.2f} {selected_unit}"
    else:
        # Convert to specified unit
        unit_index = valid_units.index(unit)
        size_value = float(size_bytes)

        # Convert bytes to the specified unit
        for _ in range(unit_index):
            size_value /= 1024.0

        # Format: no decimals for Bytes, up to 2 decimals for others
        if unit == "Bytes":
            return f"{int(size_value)} {unit}"
        else:
            return f"{size_value:.2f} {unit}"


def delete_file(file_path: PathLike) -> None:
    """Deletes a file at the specified path.

    Args:
        file_path (PathLike): The path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        Delete a file:
        ```python
        # Assuming 'example.txt' exists
        oc.io.delete_file("example.txt")
        ```
        Output:
        ```
        File deleted: example.txt
        ```
        ---
        Raise an error if the file does not exist:
        ```python
        oc.io.delete_file("non_existent_file.txt")
        ```
        Output:
        ```
        FileNotFoundError:

        File not found: non_existent_file.txt

        ```
    """
    p = ensure_file_exists(file_path)
    p.unlink()
    print(f"File deleted: {p}")


def rename(src: PathLike, dst: PathLike, replace: bool = False) -> None:
    """Renames a file or directory.

    Args:
        src (PathLike): The current path to the file or directory.
        dst (PathLike): The new path for the file or directory.
        replace (bool): If True, the destination will be overwritten if it
            already exists. Defaults to False.

    Raises:
        FileNotFoundError: If the source file or directory does not exist.
        FileExistsError: If the destination already exists and `replace` is False.

    Example:
        Rename a file:
        ```python
        # Assuming 'old_name.txt' exists
        oc.io.rename("old_name.txt", "new_name.txt")
        ```
        Output:
        ```
        Renamed old_name.txt to new_name.txt
        ```
        ---
        Replace an existing file with rename:
        ```python
        # Assuming 'old_name.txt' and 'new_name.txt' exist
        oc.io.rename("old_name.txt", "new_name.txt", replace=True)
        ```
        Output:
        ```
        Replacing file new_name.txt
        File deleted: new_name.txt
        Renamed old_name.txt to new_name.txt
        ```
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source path not found: {src_path}")

    dst_path = Path(dst)
    handle_replace(dst_path, replace)
    src_path.rename(dst_path)
    print(f"Renamed {src_path} to {dst_path}")


def get_file_name(file_path: PathLike) -> str:
    """Returns the name of a file from its path.

    Args:
        file_path (PathLike): The path to the file.

    Returns:
        str: The name of the file.

    Example:
        Get the name of a file:
        ```python
        name = oc.io.get_file_name("path/to/example.txt")
        print(name)
        ```
        Output:
        ```
        'example.txt'
        ```
    """
    return os.path.basename(file_path)


def get_file_extension(file_path: PathLike) -> str:
    """Returns the extension of a file from its path.

    Args:
        file_path (PathLike): The path to the file.

    Returns:
        str: The extension of the file (without the dot).

    Example:
        Get the extension of a file:
        ```python
        ext = oc.io.get_file_extension("example.txt")
        print(ext)
        ```
        Output:
        ```
        'txt'
        ```
    """
    # return Path(file_path).suffix.lstrip(".")
    return os.path.splitext(file_path)[1][1:]


def get_parent_dir(path: PathLike) -> Path:
    """Returns the parent directory of a file or directory.

    Args:
        path (PathLike): The path to the file or directory.

    Returns:
        Path: The path to the parent directory.

    Example:
        Get the parent directory:
        ```python
        parent = oc.io.get_parent_dir("path/to/example.txt")
        print(parent)
        ```
        Output:
        ```
        path/to
        ```
    """
    # return Path(path).parent
    return Path(os.path.dirname(path))


def download_file(url: str, file_path: PathLike, replace: bool = False) -> None:
    """Downloads a file from a URL and saves it to the specified path.

    Args:
        url (str): The URL of the file to download.
        file_path (PathLike): The path to save the downloaded file.
        replace (bool): If True, the file will be deleted if it already exists.
            Defaults to False.

    Raises:
        FileExistsError: If the file already exists and `replace` is False.

    Example:
        Download a file:
        ```python
        oc.io.download_file("https://example.com/file.txt", "downloaded_file.txt")
        ```
        Output:
        ```
        File downloaded: downloaded_file.txt
        ```
        ---
        Download and replace an existing file:
        ```python
        oc.io.download_file("https://example.com/file.txt", "downloaded_file.txt", replace=True)
        ```
        Output:
        ```
        Replacing file downloaded_file.txt
        File deleted: downloaded_file.txt
        File downloaded: downloaded_file.txt
        ```
    """
    p = Path(file_path)
    handle_replace(p, replace)
    response = requests.get(url)
    response.raise_for_status()
    p.write_bytes(response.content)
    print(f"File downloaded: {p}")


def create_archive(output_filename: str, source_dir: PathLike, format: str = "zip") -> None:
    """Creates an archive from a directory.

    Args:
        output_filename (str): The name of the archive file (without extension).
        source_dir (PathLike): The path to the source directory.
        format (str): The archive format. Valid formats are: 'zip', 'tar',
            'gztar', 'bztar', and 'xztar'. Defaults to 'zip'.

    Example:
        Create a zip archive:
        ```python
        # Assuming 'my_folder' exists
        oc.io.create_archive("archive", "my_folder", format="zip")
        ```
        Output:
        ```
        Archive created: archive.zip
        ```
        ---
        Create a gzipped tar archive for better compression:
        ```python
        oc.io.create_archive("archive", "my_folder", format="gztar")
        ```
        Output:
        ```
        Archive created: archive.tar.gz
        ```
    """
    valid_formats = [name for name, _ in shutil.get_archive_formats()]
    if format not in valid_formats:
        raise ValueError(f"Invalid archive format: {format}. Valid formats are: {', '.join(valid_formats)}")

    source_path = ensure_dir_exists(source_dir)
    archive_path = shutil.make_archive(output_filename, format, source_path)
    print(f"Archive created: {archive_path}")


def extract_archive(archive_file: PathLike, dest_dir: PathLike, replace: bool = True) -> None:
    """Extracts an archive to a directory.

    Supports formats: zip, tar, gztar, bztar, and xztar.

    Args:
        archive_file (PathLike): The path to the archive.
        dest_dir (PathLike): The destination directory to extract the archive to.
        replace (bool): If True, the destination directory will be deleted if
            it already exists. Defaults to True.

    Example:
        Extract an archive to a new directory:
        ```python
        # Assuming 'archive.zip' exists
        oc.io.extract_archive("archive.zip", "extracted_folder")
        ```
        Output:
        ```
        Archive extracted: archive.zip
        ```
        ---
        Extract and replace an existing directory:
        ```python
        # Assuming 'archive.zip' and 'extracted_folder' exist
        oc.io.extract_archive("archive.zip", "extracted_folder", replace=True)
        ```
        Output:
        ```
        Replacing directory extracted_folder
        Directory deleted: extracted_folder
        Archive extracted: archive.zip
        ```
    """
    archive_path = ensure_file_exists(archive_file)
    dest_path = Path(dest_dir)
    handle_replace(dest_path, replace)
    shutil.unpack_archive(archive_path, dest_path)
    print(f"Archive extracted: {archive_path}")
