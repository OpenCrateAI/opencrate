import json
import os
import shutil
from typing import Any, Dict, List, Optional

import requests


def ensure_dir_exists(path: str) -> None:
    """
    Ensures that a directory exists.

    Args:
        path (str): The path to the directory.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        >>> ensure_dir_exists("data")
        FileNotFoundError: Directory not found: data
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"\n\nDirectory not found: {path}\n")


def ensure_file_exists(path: str) -> None:
    """
    Ensures that a file exists.

    Args:
        path (str): The path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> ensure_file_exists("data.txt")
        FileNotFoundError: File not found: data.txt
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"\n\nFile not found: {path}\n")


def handle_replace(path: str, replace: bool) -> None:
    """
    Handles the replacement of a file or directory if it exists.

    Args:
        path (str): The path to the file or directory.
        replace (bool): If True, the file or directory will be deleted if it already exists.

    Raises:
        FileExistsError: If the file or directory already exists and `replace` is False.

    Example:
        >>> handle_replace("data.txt", replace=True)
        >>> handle_replace("data.txt", replace=False)
        FileExistsError: Path already exists: data.txt. Pass `replace` as `True` if you want to replace the existing file or directory.
    """
    if os.path.exists(path):
        if replace:
            if os.path.isdir(path):
                delete_dir(path)
            else:
                delete_file(path)
        else:
            raise FileExistsError(
                f"\n\nPath already exists: {path}. Pass `replace` as `True` if you want to replace the existing file or directory.\n"
            )


def create_dir(path: str, replace: bool = False) -> None:
    """
    Creates a directory at the specified path if it doesn't already exist.

    Args:
        path (str): The path to the directory to be created.
        replace (bool): If True, the directory will be deleted if it already exists.

    Raises:
        FileExistsError: If the directory already exists and `replace` is False.

    Example:
        >>> create_dir("new_folder")
        Directory created: new_folder
        >>> create_dir("existing_folder", replace=True)
        Directory created: existing_folder
    """
    handle_replace(path, replace)
    os.makedirs(path)
    print(f"Directory created: {path}")


def delete_dir(path: str) -> None:
    """
    Deletes a directory and all its contents recursively.

    Args:
        path (str): The path to the directory to be deleted.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        >>> delete_dir("old_folder")
        Directory deleted: old_folder
    """
    ensure_dir_exists(path)
    shutil.rmtree(path)
    print(f"Directory deleted: {path}")


def read_json(file_path: str) -> Dict[str, Any]:
    """
    Reads a JSON file and returns its content as a dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The content of the JSON file as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> data = read_json("data.json")
        >>> print(data)
        {'key': 'value'}
    """
    ensure_file_exists(file_path)
    with open(file_path, "r") as file:
        return json.load(file)


def write_json(file_path: str, data: Dict[str, Any], indent: int = 4, replace: bool = False) -> None:
    """
    Writes a dictionary to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict): The dictionary to be written to the JSON file.
        indent (int): The number of spaces to use for indentation.
        replace (bool): If True, the file will be deleted if it already exists.

    Raises:
        FileExistsError: If the file already exists and `replace` is False.

    Example:
        >>> write_json("data.json", {"key": "value"})
        JSON file written: data.json
    """
    handle_replace(file_path, replace)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=indent)
    print(f"JSON file written: {file_path}")


def list_files_in_dir(dir: str, extension: Optional[str] = None) -> List[str]:
    """
    Recursively reads and lists all files in a directory tree and returns their paths.

    Args:
        dir (str): The path to the directory.
        extension (str, optional): The file extension to filter by. Defaults to None.

    Returns:
        List[str]: A list of file paths.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        >>> files = list_files_in_dir("my_folder", extension="txt")
        >>> print(files)
        ['my_folder/file1.txt', 'my_folder/subfolder/file2.txt']
    """
    ensure_dir_exists(dir)
    file_paths: List[str] = []
    for root, _, files in os.walk(dir):
        for file in files:
            if extension:
                if file.endswith(extension):
                    file_paths.append(os.path.join(root, file))
            else:
                file_paths.append(os.path.join(root, file))
    print(f"Found {len(file_paths)} files in {dir}")
    return file_paths


def copy_dir(src: str, dst: str, replace: bool = False) -> None:
    """
    Copies a directory tree from the source to the destination.

    Args:
        src (str): The source directory path.
        dst (str): The destination directory path.

    Raises:
        FileNotFoundError: If the source directory does not exist.

    Example:
        >>> copy_dir("source_folder", "destination_folder")
    """
    ensure_dir_exists(src)
    handle_replace(dst, replace)
    shutil.copytree(src, dst)


def move_dir(src: str, dst: str, replace: bool = False) -> None:
    """
    Moves a directory from the source to the destination.

    Args:
        src (str): The source directory path.
        dst (str): The destination directory path.
        replace (bool): If True, the destination directory will be deleted if it already exists.

    Raises:
        FileNotFoundError: If the source directory does not exist.
        FileExistsError: If the destination directory already exists and `replace` is False.

    Example:
        >>> move_dir("old_folder", "new_folder")
        Directory moved from old_folder to new_folder
    """
    ensure_dir_exists(src)
    handle_replace(dst, replace)
    shutil.move(src, dst)
    print(f"Directory moved from {src} to {dst}")


def read_file(file_path: str) -> str:
    """
    Reads a file and returns its content as a string.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> content = read_file("example.txt")
        >>> print(content)
        'Hello, world!'
    """
    ensure_file_exists(file_path)
    with open(file_path, "r") as file:
        return file.read()


def write_file(file_path: str, content: str, replace: bool = False) -> None:
    """
    Writes text content to a file.

    Args:
        file_path (str): The path to the file.
        content (str): The content to be written to the file.
        replace (bool): If True, the file will be deleted if it already exists.

    Raises:
        FileExistsError: If the file already exists and `replace` is False.

    Example:
        >>> write_file("example.txt", "Hello, world!")
        File written: example.txt
    """
    handle_replace(file_path, replace)
    with open(file_path, "w") as file:
        file.write(content)
    print(f"File written: {file_path}")


def file_exists(file_path: str) -> bool:
    """
    Checks if a file exists at the specified path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file exists, False otherwise.

    Example:
        >>> file_exists("example.txt")
        True
    """
    return os.path.exists(file_path)


def dir_exists(dir: str) -> bool:
    """
    Checks if a directory exists at the specified path.

    Args:
        dir (str): The path to the directory.

    Returns:
        bool: True if the directory exists, False otherwise.

    Example:
        >>> dir_exists("my_folder")
        True
    """
    return os.path.exists(dir)


def get_file_size(file_path: str) -> int:
    """
    Returns the size of a file in bytes.

    Args:
        file_path (str): The path to the file.

    Returns:
        int: The size of the file in bytes.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> size = get_file_size("example.txt")
        >>> print(size)
        13
    """
    ensure_file_exists(file_path)
    return os.path.getsize(file_path)


def get_dir_size(dir: str) -> int:
    """
    Returns the total size of a directory in bytes.

    Args:
        dir (str): The path to the directory.

    Returns:
        int: The total size of the directory in bytes.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        >>> size = get_dir_size("my_folder")
        >>> print(size)
        1024
    """
    ensure_dir_exists(dir)
    total_size = 0
    for dirpath, _, filenames in os.walk(dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def list_dir(dir: str) -> List[str]:
    """
    Lists all files and directories in the specified directory.

    Args:
        dir (str): The path to the directory.

    Returns:
        List[str]: A list of file and directory names in the specified directory.

    Raises:
        FileNotFoundError: If the directory does not exist.

    Example:
        >>> items = list_dir("my_folder")
        >>> print(items)
        ['file1.txt', 'subfolder']
    """
    ensure_dir_exists(dir)
    return os.listdir(dir)


def delete_file(file_path: str) -> None:
    """
    Deletes a file at the specified path.

    Args:
        file_path (str): The path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> delete_file("example.txt")
        File deleted: example.txt
    """
    ensure_file_exists(file_path)
    os.remove(file_path)
    print(f"File deleted: {file_path}")


def rename(src: str, dst: str, replace: bool = False) -> None:
    """
    Renames a file or directory from `src` to `dst`.

    Args:
        src (str): The current path to the file or directory.
        dst (str): The new path to the file or directory.
        replace (bool): If True, the destination file or directory will be deleted if it already exists.

    Raises:
        FileNotFoundError: If the source file or directory does not exist.
        FileExistsError: If the destination file or directory already exists and `replace` is False.

    Example:
        >>> rename("old_name.txt", "new_name.txt")
        Renamed old_name.txt to new_name.txt
    """
    ensure_file_exists(src)
    handle_replace(dst, replace)
    os.rename(src, dst)
    print(f"Renamed {src} to {dst}")


def get_file_name(file_path: str) -> str:
    """
    Returns the name of a file from its path.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The name of the file.

    Example:
        >>> name = get_file_name("path/to/example.txt")
        >>> print(name)
        'example.txt'
    """
    return os.path.basename(file_path)


def get_file_extension(file_path: str) -> str:
    """
    Returns the extension of a file from its path.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The extension of the file.

    Example:
        >>> ext = get_file_extension("example.txt")
        >>> print(ext)
        'txt'
    """
    return os.path.splitext(file_path)[1][1:]


def get_parent_dir(path: str) -> str:
    """
    Returns the parent directory of a file or directory.

    Args:
        path (str): The path to the file or directory.

    Returns:
        str: The path to the parent directory.

    Example:
        >>> parent = get_parent_dir("path/to/example.txt")
        >>> print(parent)
        'path/to'
    """
    return os.path.dirname(path)


def download_file(url: str, file_path: str, replace: bool = False) -> None:
    """
    Downloads a file from a URL and saves it to the specified path.

    Args:
        url (str): The URL of the file to download.
        file_path (str): The path to save the downloaded file.
        replace (bool): If True, the file will be deleted if it already exists.

    Raises:
        FileExistsError: If the file already exists and `replace` is False.

    Example:
        >>> download_file("https://example.com/file.txt", "downloaded_file.txt")
        File downloaded: downloaded_file.txt
    """
    handle_replace(file_path, replace)
    response = requests.get(url)
    with open(file_path, "wb") as file:
        file.write(response.content)
    print(f"File downloaded: {file_path}")


def create_archive(output_filename: str, source_dir: str, format: str = "zip") -> None:
    """
    Creates an archive from a directory.

    Args:
        output_filename (str): The name of the archive.
        source_dir (str): The path to the source directory.
        format (str): The archive format. Defaults to 'zip'. Valid formats are: 'zip', 'tar', 'gztar', 'bztar', and 'xztar'. You can use 'gztar' or 'zip' for fast compression/decompression and 'xztar' for maximum compression.

    Example:
        >>> create_archive("archive", "my_folder", format="zip")
        Archive created: archive.zip
    """

    # check if format is valid
    valid_formats = ["zip", "tar", "gztar", "bztar", "xztar"]
    if format not in valid_formats:
        raise ValueError(
            f"\n\nInvalid archive format: {format}. Valid formats are: 'zip', 'tar', 'gztar', 'bztar', and 'xztar'.\n"
        )
    ensure_dir_exists(source_dir)
    handle_replace(output_filename, replace=True)
    shutil.make_archive(output_filename, format, source_dir)
    print(f"Archive created: {output_filename}.{format}")


def extract_archive(archive_file: str, dest_dir: str, replace: bool = True) -> None:
    """
    Extracts an archive to a directory. Supports formats are zip, tar, gztar, bztar, and xztar.

    Args:
        archive_file (str): The path to the archive.
        dest_dir (str): The destination directory to extract the archive to.

    Example:
        >>> extract_archive("archive.zip", "extracted_folder")
        Archive extracted: archive.zip
    """

    ensure_file_exists(archive_file)
    handle_replace(dest_dir, replace)
    shutil.unpack_archive(archive_file, dest_dir)
    print(f"Archive extracted: {archive_file}")
