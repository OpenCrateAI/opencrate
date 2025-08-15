import json

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
    def test_ensure_dir_exists(self, tmp_path):
        existing_dir = tmp_path / "existing_dir"
        existing_dir.mkdir()

        ensure_dir_exists(str(existing_dir))
        assert existing_dir.exists()

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            ensure_dir_exists(str(non_existing_dir))

    def test_ensure_dir_exists_not_found(self, tmp_path):
        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            ensure_dir_exists(str(non_existing_dir))

    def test_ensure_file_exists(self, tmp_path):
        test_file = tmp_path / "old_name.txt"
        test_file.write_text("old content")

        ensure_file_exists(str(test_file))
        assert test_file.exists()

        non_existing_file = tmp_path / "non_existing_file.txt"
        with pytest.raises(FileNotFoundError):
            ensure_file_exists(str(non_existing_file))

    def test_handle_replace(self, tmp_path):
        test_file = tmp_path / "old_name.txt"
        test_file.write_text("old content")

        handle_replace(str(test_file), replace=True)
        assert not test_file.exists()

        test_file.write_text("old content")

        with pytest.raises(FileExistsError):
            handle_replace(str(test_file), replace=False)

        non_existing_file = tmp_path / "non_existing_file.txt"
        handle_replace(str(non_existing_file), replace=False)

    def test_handle_replace_directory(self, tmp_path):
        dir_to_replace = tmp_path / "dir_to_replace"
        dir_to_replace.mkdir()
        handle_replace(str(dir_to_replace), replace=True)
        assert not dir_to_replace.exists()

    def test_create_dir(self, tmp_path):
        existing_dir = tmp_path / "existing_dir"
        existing_dir.mkdir()

        create_dir_path = tmp_path / "create_dir"
        create_dir(str(create_dir_path), replace=True)
        assert create_dir_path.exists()

        with pytest.raises(FileExistsError):
            create_dir(str(existing_dir), replace=False)

    def test_delete_dir(self, tmp_path):
        existing_dir = tmp_path / "existing_dir"
        existing_dir.mkdir()

        delete_dir(str(existing_dir))
        assert not existing_dir.exists()

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            delete_dir(str(non_existing_dir))

    def test_read_json(self, tmp_path):
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"key": "value"}))

        data = read_json(str(data_file))
        assert data == {"key": "value"}

        non_existing_file = tmp_path / "non_existing_file.json"
        with pytest.raises(FileNotFoundError):
            read_json(str(non_existing_file))

    def test_write_json(self, tmp_path):
        data_file = tmp_path / "data.json"
        write_json(str(data_file), {"key": "new_value"}, replace=True)

        data = json.loads(data_file.read_text())
        assert data == {"key": "new_value"}

    def test_list_files_in_dir(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        sub_dir = source_dir / "sub_dir"
        sub_dir.mkdir()

        (source_dir / "file.txt").write_text("content")
        (sub_dir / "file.txt").write_text("content")

        files = list_files_in_dir(str(source_dir))
        assert files == [
            str(source_dir / "file.txt"),
            str(sub_dir / "file.txt"),
        ]

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            list_files_in_dir(str(non_existing_dir))

    def test_list_files_in_dir_with_extension(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        files = list_files_in_dir(str(source_dir), extension="txt")
        assert files == [str(source_dir / "file.txt")]

    def test_copy_dir(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        dst_dir = tmp_path / "dst"

        copy_dir(str(src_dir), str(dst_dir), replace=True)
        assert dst_dir.exists()

        non_existing_src = tmp_path / "non_existing_src"
        with pytest.raises(FileNotFoundError):
            copy_dir(str(non_existing_src), str(dst_dir))

    def test_move_dir(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        dst_dir = tmp_path / "dst"

        move_dir(str(src_dir), str(dst_dir), replace=True)
        assert dst_dir.exists()
        assert not src_dir.exists()

        non_existing_src = tmp_path / "non_existing_src"
        with pytest.raises(FileNotFoundError):
            move_dir(str(non_existing_src), str(dst_dir))

    def test_read_file(self, tmp_path):
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        content = read_file(str(test_file))
        assert content == "content"

        non_existing_file = tmp_path / "non_existing_file.txt"
        with pytest.raises(FileNotFoundError):
            read_file(str(non_existing_file))

    def test_write_file(self, tmp_path):
        test_file = tmp_path / "file.txt"
        write_file(str(test_file), "new content", replace=True)

        content = test_file.read_text()
        assert content == "new content"

    def test_file_exists(self, tmp_path):
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        assert file_exists(str(test_file))

        non_existing_file = tmp_path / "non_existing_file.txt"
        assert not file_exists(str(non_existing_file))

    def test_dir_exists(self, tmp_path):
        existing_dir = tmp_path / "existing_dir"
        existing_dir.mkdir()

        assert dir_exists(str(existing_dir))

        non_existing_dir = tmp_path / "non_existing_dir"
        assert not dir_exists(str(non_existing_dir))

    def test_get_file_size(self, tmp_path):
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        size = get_file_size(str(test_file))
        assert size == test_file.stat().st_size

        non_existing_file = tmp_path / "non_existing_file.txt"
        with pytest.raises(FileNotFoundError):
            get_file_size(str(non_existing_file))

    def test_get_dir_size(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        test_file = source_dir / "file.txt"
        test_file.write_text("content")

        size = get_dir_size(str(source_dir))
        assert size == test_file.stat().st_size

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            get_dir_size(str(non_existing_dir))

    def test_list_dir(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()

        items = list_dir(str(source_dir))
        assert items == []

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            list_dir(str(non_existing_dir))

    def test_delete_file(self, tmp_path):
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        delete_file(str(test_file))
        assert not test_file.exists()

        non_existing_file = tmp_path / "non_existing_file.txt"
        with pytest.raises(FileNotFoundError):
            delete_file(str(non_existing_file))

    def test_rename(self, tmp_path):
        old_file = tmp_path / "old_name.txt"
        old_file.write_text("old content")
        new_file = tmp_path / "new_name.txt"

        rename(str(old_file), str(new_file), replace=True)
        assert new_file.exists()
        assert not old_file.exists()

        non_existing_file = tmp_path / "non_existing_file.txt"
        with pytest.raises(FileNotFoundError):
            rename(str(non_existing_file), str(new_file))

    def test_get_file_name(self):
        assert get_file_name("path/to/file.txt") == "file.txt"

    def test_get_file_extension(self):
        assert get_file_extension("file.txt") == "txt"

    def test_get_parent_dir(self):
        assert get_parent_dir("path/to/file.txt") == "path/to"

    def test_download_file(self, tmp_path):
        archive_file = tmp_path / "archive.zip"
        download_file(
            "https://www.learningcontainer.com/download/sample-zip-files/?wpdmdl=1637&refresh=67ac3bd61a3771739340758",
            str(archive_file),
            replace=True,
        )
        assert archive_file.exists()

    def test_create_archive(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        archive_path = tmp_path / "create_archive"

        create_archive(str(archive_path), str(source_dir), format="zip")
        assert (tmp_path / "create_archive.zip").exists()

    def test_create_archive_invalid_format(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        archive_path = tmp_path / "create_archive"

        with pytest.raises(ValueError):
            create_archive(str(archive_path), str(source_dir), format="invalid_format")

    def test_extract_archive(self, tmp_path):
        # This test assumes the archive.zip was created by test_download_file
        archive_file = tmp_path / "archive.zip"
        dest_dir = tmp_path / "dest_dir"

        # Create a simple zip file for testing
        import zipfile

        with zipfile.ZipFile(str(archive_file), "w") as zf:
            zf.writestr("test.txt", "test content")

        extract_archive(str(archive_file), str(dest_dir))
        assert dest_dir.exists()

    def test_extract_archive_invalid_file(self, tmp_path):
        non_existing_archive = tmp_path / "non_existing_archive.zip"
        dest_dir = tmp_path / "dest_dir"

        with pytest.raises(FileNotFoundError):
            extract_archive(str(non_existing_archive), str(dest_dir))
