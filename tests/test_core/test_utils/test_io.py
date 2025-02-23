import json
import os
import shutil

import pytest

from opencrate.core.utils import (
    copy_dir,
    create_archive,
    create_dir,
    delete_dir,
    delete_file,
    dir_exists,
    download_file,
    ensure_dir_exists,
    ensure_file_exists,
    extract_archive,
    file_exists,
    get_dir_size,
    get_file_extension,
    get_file_name,
    get_file_size,
    get_parent_dir,
    handle_replace,
    list_dir,
    list_files_in_dir,
    move_dir,
    read_file,
    read_json,
    rename,
    write_file,
    write_json,
)


class TestUtilsIO:
    test_root_dir: str = "tests/assets"

    def setup_ensure_dir_exists(self):
        os.makedirs(f"{self.test_root_dir}/existing_dir", exist_ok=True)

    def teardown_ensure_dir_exists(self):
        shutil.rmtree(f"{self.test_root_dir}/existing_dir", ignore_errors=True)

    def test_ensure_dir_exists(self):
        self.setup_ensure_dir_exists()
        ensure_dir_exists(f"{self.test_root_dir}/existing_dir")
        assert os.path.exists(f"{self.test_root_dir}/existing_dir")

        with pytest.raises(FileNotFoundError):
            ensure_dir_exists(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_ensure_dir_exists()

    def test_ensure_dir_exists_not_found(self):
        with pytest.raises(FileNotFoundError):
            ensure_dir_exists(f"{self.test_root_dir}/non_existing_dir")

    def setup_ensure_file_exists(self):
        with open(f"{self.test_root_dir}/old_name.txt", "w") as f:
            f.write("old content")

    def teardown_ensure_file_exists(self):
        if os.path.exists(f"{self.test_root_dir}/old_name.txt"):
            os.remove(f"{self.test_root_dir}/old_name.txt")

    def test_ensure_file_exists(self):
        self.setup_ensure_file_exists()
        ensure_file_exists(f"{self.test_root_dir}/old_name.txt")
        assert os.path.exists(f"{self.test_root_dir}/old_name.txt")

        with pytest.raises(FileNotFoundError):
            ensure_file_exists(f"{self.test_root_dir}/non_existing_file.txt")
        self.teardown_ensure_file_exists()

    def setup_handle_replace(self):
        with open(f"{self.test_root_dir}/old_name.txt", "w") as f:
            f.write("old content")

    def teardown_handle_replace(self):
        if os.path.exists(f"{self.test_root_dir}/old_name.txt"):
            os.remove(f"{self.test_root_dir}/old_name.txt")

    def test_handle_replace(self):
        self.setup_handle_replace()
        handle_replace(f"{self.test_root_dir}/old_name.txt", replace=True)
        assert not os.path.exists(f"{self.test_root_dir}/old_name.txt")

        with open(f"{self.test_root_dir}/old_name.txt", "w") as f:
            f.write("old content")

        with pytest.raises(FileExistsError):
            handle_replace(f"{self.test_root_dir}/old_name.txt", replace=False)

        handle_replace(f"{self.test_root_dir}/non_existing_file.txt", replace=False)
        self.teardown_handle_replace()

    def test_handle_replace_directory(self):
        os.makedirs(f"{self.test_root_dir}/dir_to_replace", exist_ok=True)
        handle_replace(f"{self.test_root_dir}/dir_to_replace", replace=True)
        assert not os.path.exists(f"{self.test_root_dir}/dir_to_replace")

    def setup_create_dir(self):
        os.makedirs(f"{self.test_root_dir}/existing_dir", exist_ok=True)

    def teardown_create_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/existing_dir", ignore_errors=True)
        shutil.rmtree(f"{self.test_root_dir}/create_dir", ignore_errors=True)

    def test_create_dir(self):
        self.setup_create_dir()
        create_dir(f"{self.test_root_dir}/create_dir", replace=True)
        assert os.path.exists(f"{self.test_root_dir}/create_dir")

        with pytest.raises(FileExistsError):
            create_dir(f"{self.test_root_dir}/existing_dir", replace=False)
        self.teardown_create_dir()

    def setup_delete_dir(self):
        os.makedirs(f"{self.test_root_dir}/existing_dir", exist_ok=True)

    def teardown_delete_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/existing_dir", ignore_errors=True)

    def test_delete_dir(self):
        self.setup_delete_dir()
        delete_dir(f"{self.test_root_dir}/existing_dir")
        assert not os.path.exists(f"{self.test_root_dir}/existing_dir")

        with pytest.raises(FileNotFoundError):
            delete_dir(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_delete_dir()

    def setup_read_json(self):
        with open(f"{self.test_root_dir}/data.json", "w") as f:
            json.dump({"key": "value"}, f)

    def teardown_read_json(self):
        if os.path.exists(f"{self.test_root_dir}/data.json"):
            os.remove(f"{self.test_root_dir}/data.json")

    def test_read_json(self):
        self.setup_read_json()
        data = read_json(f"{self.test_root_dir}/data.json")
        assert data == {"key": "value"}

        with pytest.raises(FileNotFoundError):
            read_json(f"{self.test_root_dir}/non_existing_file.json")
        self.teardown_read_json()

    def setup_write_json(self):
        pass

    def teardown_write_json(self):
        if os.path.exists(f"{self.test_root_dir}/data.json"):
            os.remove(f"{self.test_root_dir}/data.json")

    def test_write_json(self):
        self.setup_write_json()
        write_json(f"{self.test_root_dir}/data.json", {"key": "new_value"}, replace=True)
        with open(f"{self.test_root_dir}/data.json", "r") as f:
            data = json.load(f)
        assert data == {"key": "new_value"}
        self.teardown_write_json()

    def setup_list_files_in_dir(self):
        os.makedirs(f"{self.test_root_dir}/source_dir", exist_ok=True)
        os.makedirs(f"{self.test_root_dir}/source_dir/sub_dir", exist_ok=True)
        with open(f"{self.test_root_dir}/source_dir/file.txt", "w") as f:
            f.write("content")
        with open(f"{self.test_root_dir}/source_dir/sub_dir/file.txt", "w") as f:
            f.write("content")

    def teardown_list_files_in_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/source_dir", ignore_errors=True)

    def test_list_files_in_dir(self):
        self.setup_list_files_in_dir()
        files = list_files_in_dir(f"{self.test_root_dir}/source_dir")
        assert files == [
            f"{self.test_root_dir}/source_dir/file.txt",
            f"{self.test_root_dir}/source_dir/sub_dir/file.txt",
        ]

        with pytest.raises(FileNotFoundError):
            list_files_in_dir(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_list_files_in_dir()

    def setup_list_files_in_dir_with_extension(self):
        os.makedirs(f"{self.test_root_dir}/source_dir", exist_ok=True)
        with open(f"{self.test_root_dir}/source_dir/file.txt", "w") as f:
            f.write("content")

    def teardown_list_files_in_dir_with_extension(self):
        shutil.rmtree(f"{self.test_root_dir}/source_dir", ignore_errors=True)

    def test_list_files_in_dir_with_extension(self):
        self.setup_list_files_in_dir_with_extension()
        files = list_files_in_dir(f"{self.test_root_dir}/source_dir", extension="txt")
        assert files == [f"{self.test_root_dir}/source_dir/file.txt"]
        self.teardown_list_files_in_dir_with_extension()

    def setup_copy_dir(self):
        os.makedirs(f"{self.test_root_dir}/src", exist_ok=True)

    def teardown_copy_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/src", ignore_errors=True)
        shutil.rmtree(f"{self.test_root_dir}/dst", ignore_errors=True)

    def test_copy_dir(self):
        self.setup_copy_dir()
        copy_dir(f"{self.test_root_dir}/src", f"{self.test_root_dir}/dst", replace=True)
        assert os.path.exists(f"{self.test_root_dir}/dst")

        with pytest.raises(FileNotFoundError):
            copy_dir(f"{self.test_root_dir}/non_existing_src", f"{self.test_root_dir}/dst")
        self.teardown_copy_dir()

    def setup_move_dir(self):
        os.makedirs(f"{self.test_root_dir}/src", exist_ok=True)

    def teardown_move_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/src", ignore_errors=True)
        shutil.rmtree(f"{self.test_root_dir}/dst", ignore_errors=True)

    def test_move_dir(self):
        self.setup_move_dir()
        move_dir(f"{self.test_root_dir}/src", f"{self.test_root_dir}/dst", replace=True)
        assert os.path.exists(f"{self.test_root_dir}/dst")
        assert not os.path.exists(f"{self.test_root_dir}/src")

        with pytest.raises(FileNotFoundError):
            move_dir(f"{self.test_root_dir}/non_existing_src", f"{self.test_root_dir}/dst")
        self.teardown_move_dir()

    def setup_read_file(self):
        with open(f"{self.test_root_dir}/file.txt", "w") as f:
            f.write("content")

    def teardown_read_file(self):
        if os.path.exists(f"{self.test_root_dir}/file.txt"):
            os.remove(f"{self.test_root_dir}/file.txt")

    def test_read_file(self):
        self.setup_read_file()
        content = read_file(f"{self.test_root_dir}/file.txt")
        assert content == "content"

        with pytest.raises(FileNotFoundError):
            read_file(f"{self.test_root_dir}/non_existing_file.txt")
        self.teardown_read_file()

    def setup_write_file(self):
        pass

    def teardown_write_file(self):
        if os.path.exists(f"{self.test_root_dir}/file.txt"):
            os.remove(f"{self.test_root_dir}/file.txt")

    def test_write_file(self):
        self.setup_write_file()
        write_file(f"{self.test_root_dir}/file.txt", "new content", replace=True)
        with open(f"{self.test_root_dir}/file.txt", "r") as f:
            content = f.read()
        assert content == "new content"
        self.teardown_write_file()

    def setup_file_exists(self):
        with open(f"{self.test_root_dir}/file.txt", "w") as f:
            f.write("content")

    def teardown_file_exists(self):
        if os.path.exists(f"{self.test_root_dir}/file.txt"):
            os.remove(f"{self.test_root_dir}/file.txt")

    def test_file_exists(self):
        self.setup_file_exists()
        assert file_exists(f"{self.test_root_dir}/file.txt")
        assert not file_exists(f"{self.test_root_dir}/non_existing_file.txt")
        self.teardown_file_exists()

    def setup_dir_exists(self):
        os.makedirs(f"{self.test_root_dir}/existing_dir", exist_ok=True)

    def teardown_dir_exists(self):
        shutil.rmtree(f"{self.test_root_dir}/existing_dir", ignore_errors=True)

    def test_dir_exists(self):
        self.setup_dir_exists()
        assert dir_exists(f"{self.test_root_dir}/existing_dir")
        assert not dir_exists(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_dir_exists()

    def setup_get_file_size(self):
        with open(f"{self.test_root_dir}/file.txt", "w") as f:
            f.write("content")

    def teardown_get_file_size(self):
        if os.path.exists(f"{self.test_root_dir}/file.txt"):
            os.remove(f"{self.test_root_dir}/file.txt")

    def test_get_file_size(self):
        self.setup_get_file_size()
        size = get_file_size(f"{self.test_root_dir}/file.txt")
        assert size == os.path.getsize(f"{self.test_root_dir}/file.txt")

        with pytest.raises(FileNotFoundError):
            get_file_size(f"{self.test_root_dir}/non_existing_file.txt")
        self.teardown_get_file_size()

    def setup_get_dir_size(self):
        os.makedirs(f"{self.test_root_dir}/source_dir", exist_ok=True)
        with open(f"{self.test_root_dir}/source_dir/file.txt", "w") as f:
            f.write("content")

    def teardown_get_dir_size(self):
        shutil.rmtree(f"{self.test_root_dir}/source_dir", ignore_errors=True)

    def test_get_dir_size(self):
        self.setup_get_dir_size()
        size = get_dir_size(f"{self.test_root_dir}/source_dir")
        assert size == os.path.getsize(f"{self.test_root_dir}/source_dir/file.txt")

        with pytest.raises(FileNotFoundError):
            get_dir_size(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_get_dir_size()

    def setup_list_dir(self):
        os.makedirs(f"{self.test_root_dir}/source_dir", exist_ok=True)

    def teardown_list_dir(self):
        shutil.rmtree(f"{self.test_root_dir}/source_dir", ignore_errors=True)

    def test_list_dir(self):
        self.setup_list_dir()
        items = list_dir(f"{self.test_root_dir}/source_dir")
        assert items == []

        with pytest.raises(FileNotFoundError):
            list_dir(f"{self.test_root_dir}/non_existing_dir")
        self.teardown_list_dir()

    def setup_delete_file(self):
        with open(f"{self.test_root_dir}/file.txt", "w") as f:
            f.write("content")

    def test_delete_file(self):
        self.setup_delete_file()
        delete_file(f"{self.test_root_dir}/file.txt")
        assert not os.path.exists(f"{self.test_root_dir}/file.txt")

        with pytest.raises(FileNotFoundError):
            delete_file(f"{self.test_root_dir}/non_existing_file.txt")

    def setup_rename(self):
        with open(f"{self.test_root_dir}/old_name.txt", "w") as f:
            f.write("old content")

    def teardown_rename(self):
        if os.path.exists(f"{self.test_root_dir}/new_name.txt"):
            os.remove(f"{self.test_root_dir}/new_name.txt")

    def test_rename(self):
        self.setup_rename()
        rename(f"{self.test_root_dir}/old_name.txt", f"{self.test_root_dir}/new_name.txt", replace=True)
        assert os.path.exists(f"{self.test_root_dir}/new_name.txt")
        assert not os.path.exists(f"{self.test_root_dir}/old_name.txt")

        with pytest.raises(FileNotFoundError):
            rename(f"{self.test_root_dir}/non_existing_file.txt", f"{self.test_root_dir}/new_name.txt")
        self.teardown_rename()

    def test_get_file_name(self):
        assert get_file_name("path/to/file.txt") == "file.txt"

    def test_get_file_extension(self):
        assert get_file_extension("file.txt") == "txt"

    def test_get_parent_dir(self):
        assert get_parent_dir("path/to/file.txt") == "path/to"

    def test_download_file(self):
        download_file(
            "https://www.learningcontainer.com/download/sample-zip-files/?wpdmdl=1637&refresh=67ac3bd61a3771739340758",
            f"{self.test_root_dir}/archive.zip",
            replace=True,
        )
        assert os.path.exists(f"{self.test_root_dir}/archive.zip")

    def setup_create_archive(self):
        os.makedirs(f"{self.test_root_dir}/source_dir", exist_ok=True)

    def teardown_create_archive(self):
        shutil.rmtree(f"{self.test_root_dir}/source_dir", ignore_errors=True)
        if os.path.exists(f"{self.test_root_dir}/create_archive.zip"):
            os.remove(f"{self.test_root_dir}/create_archive.zip")

    def test_create_archive(self):
        self.setup_create_archive()
        create_archive(f"{self.test_root_dir}/create_archive", f"{self.test_root_dir}/source_dir", format="zip")
        assert os.path.exists(f"{self.test_root_dir}/create_archive.zip")
        self.teardown_create_archive()

    def test_create_archive_invalid_format(self):
        with pytest.raises(ValueError):
            create_archive(
                f"{self.test_root_dir}/create_archive",
                f"{self.test_root_dir}/source_dir",
                format="invalid_format",
            )

    def teardown_extract_archive(self):
        shutil.rmtree(f"{self.test_root_dir}/dest_dir", ignore_errors=True)
        if os.path.exists(f"{self.test_root_dir}/archive.zip"):
            os.remove(f"{self.test_root_dir}/archive.zip")

    def test_extract_archive(self):
        extract_archive(f"{self.test_root_dir}/archive.zip", f"{self.test_root_dir}/dest_dir")
        assert os.path.exists(f"{self.test_root_dir}/dest_dir")
        self.teardown_extract_archive()

    def test_extract_archive_invalid_file(self):
        with pytest.raises(FileNotFoundError):
            extract_archive(f"{self.test_root_dir}/non_existing_archive.zip", f"{self.test_root_dir}/dest_dir")
