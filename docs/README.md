# IO Utility Library

This library provides a set of utility functions for file and directory operations, including creating, deleting, reading, writing, and moving files and directories. It also includes functions for handling JSON files and downloading files from URLs.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
    - [Directory Operations](#directory-operations)
        - [Create Directory](#create-directory)
        - [Delete Directory](#delete-directory)
        - [List Files in Directory](#list-files-in-directory)
        - [Copy Directory](#copy-directory)
        - [Move Directory](#move-directory)
    - [File Operations](#file-operations)
        - [Read File](#read-file)
        - [Write File](#write-file)
        - [Delete File](#delete-file)
        - [Rename File](#rename-file)
        - [Check File Existence](#check-file-existence)
        - [Get File Size](#get-file-size)
        - [Get File Name](#get-file-name)
        - [Get File Extension](#get-file-extension)
    - [JSON Operations](#json-operations)
        - [Read JSON](#read-json)
        - [Write JSON](#write-json)
    - [Download File](#download-file)
- [License](#license)

## Installation

To use this library, simply clone the repository and import the required functions in your project.

```bash
git clone https://github.com/yourusername/ioutility.git
```

## Usage

### Directory Operations

#### Create Directory

Creates a directory at the specified path if it doesn't already exist.

```python
from io import create_dir

create_dir("/path/to/directory", replace=True)
```

**Arguments:**
- `path` (str): The path to the directory to be created.
- `replace` (bool): If True, the directory will be deleted if it already exists.

**Raises:**
- `FileExistsError`: If the directory already exists and `replace` is False.

#### Delete Directory

Deletes a directory and all its contents recursively.

```python
from io import delete_dir

delete_dir("/path/to/directory")
```

**Arguments:**
- `path` (str): The path to the directory to be deleted.

**Raises:**
- `FileNotFoundError`: If the directory does not exist.

#### List Files in Directory

Recursively reads and lists all files in a directory tree and returns their paths.

```python
from io import list_files_in_dir

files = list_files_in_dir("/path/to/directory", extension="txt")
print(files)
```

**Arguments:**
- `dir` (str): The path to the directory.
- `extension` (str, optional): The file extension to filter by. Defaults to None.

**Returns:**
- `List[str]`: A list of file paths.

**Raises:**
- `FileNotFoundError`: If the directory does not exist.

#### Copy Directory

Copies a directory tree from the source to the destination.

```python
from io import copy_dir

copy_dir("/path/to/source", "/path/to/destination", replace=True)
```

**Arguments:**
- `src` (str): The source directory path.
- `dst` (str): The destination directory path.
- `replace` (bool): If True, the destination directory will be deleted if it already exists.

**Raises:**
- `FileNotFoundError`: If the source directory does not exist.
- `FileExistsError`: If the destination directory already exists and `replace` is False.

#### Move Directory

Moves a directory from the source to the destination.

```python
from io import move_dir

move_dir("/path/to/source", "/path/to/destination", replace=True)
```

**Arguments:**
- `src` (str): The source directory path.
- `dst` (str): The destination directory path.
- `replace` (bool): If True, the destination directory will be deleted if it already exists.

**Raises:**
- `FileNotFoundError`: If the source directory does not exist.
- `FileExistsError`: If the destination directory already exists and `replace` is False.

### File Operations

#### Read File

Reads a file and returns its content as a string.

```python
from io import read_file

content = read_file("/path/to/file.txt")
print(content)
```

**Arguments:**
- `file_path` (str): The path to the file.

**Returns:**
- `str`: The content of the file.

**Raises:**
- `FileNotFoundError`: If the file does not exist.

#### Write File

Writes text content to a file.

```python
from io import write_file

write_file("/path/to/file.txt", "Hello, World!", replace=True)
```

**Arguments:**
- `file_path` (str): The path to the file.
- `content` (str): The content to be written to the file.
- `replace` (bool): If True, the file will be deleted if it already exists.

**Raises:**
- `FileExistsError`: If the file already exists and `replace` is False.

#### Delete File

Deletes a file at the specified path.

```python
from io import delete_file

delete_file("/path/to/file.txt")
```

**Arguments:**
- `file_path` (str): The path to the file.

**Raises:**
- `FileNotFoundError`: If the file does not exist.

#### Rename File

Renames a file or directory from `src` to `dst`.

```python
from io import rename

rename("/path/to/file.txt", "/path/to/new_file.txt", replace=True)
```

**Arguments:**
- `src` (str): The current path to the file or directory.
- `dst` (str): The new path to the file or directory.
- `replace` (bool): If True, the destination file or directory will be deleted if it already exists.

**Raises:**
- `FileNotFoundError`: If the source file or directory does not exist.
- `FileExistsError`: If the destination file or directory already exists and `replace` is False.

#### Check File Existence

Checks if a file exists at the specified path.

```python
from io import file_exists

exists = file_exists("/path/to/file.txt")
print(exists)
```

**Arguments:**
- `file_path` (str): The path to the file.

**Returns:**
- `bool`: True if the file exists, False otherwise.

#### Get File Size

Returns the size of a file in bytes.

```python
from io import get_file_size

size = get_file_size("/path/to/file.txt")
print(size)
```

**Arguments:**
- `file_path` (str): The path to the file.

**Returns:**
- `int`: The size of the file in bytes.

**Raises:**
- `FileNotFoundError`: If the file does not exist.

#### Get File Name

Returns the name of a file from its path.

```python
from io import get_file_name

name = get_file_name("/path/to/file.txt")
print(name)
```

**Arguments:**
- `file_path` (str): The path to the file.

**Returns:**
- `str`: The name of the file.

#### Get File Extension

Returns the extension of a file from its path.

```python
from io import get_file_extension

extension = get_file_extension("/path/to/file.txt")
print(extension)
```

**Arguments:**
- `file_path` (str): The path to the file.

**Returns:**
- `str`: The extension of the file.

### JSON Operations

#### Read JSON

Reads a JSON file and returns its content as a dictionary.

```python
from io import read_json

data = read_json("/path/to/file.json")
print(data)
```

**Arguments:**
- `file_path` (str): The path to the JSON file.

**Returns:**
- `dict`: The content of the JSON file as a dictionary.

**Raises:**
- `FileNotFoundError`: If the file does not exist.

#### Write JSON

Writes a dictionary to a JSON file.

```python
from io import write_json

data = {"key": "value"}
write_json("/path/to/file.json", data, indent=4, replace=True)
```

**Arguments:**
- `file_path` (str): The path to the JSON file.
- `data` (dict): The dictionary to be written to the JSON file.
- `indent` (int): The number of spaces to use for indentation.
- `replace` (bool): If True, the file will be deleted if it already exists.

**Raises:**
- `FileExistsError`: If the file already exists and `replace` is False.

### Download File

Downloads a file from a URL and saves it to the specified path.

```python
from io import download_file

download_file("https://example.com/file.txt", "/path/to/file.txt", replace=True)
```

**Arguments:**
- `url` (str): The URL of the file to download.
- `file_path` (str): The path to save the downloaded file.
- `replace` (bool): If True, the file will be deleted if it already exists.

**Raises:**
- `FileExistsError`: If the file already exists and `replace` is False.

## License

This project is licensed under the MIT License.