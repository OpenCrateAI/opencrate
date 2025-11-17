import pytest

from opencrate.core.utils.io.system import (
    copy_dir,
    create_archive,
    create_dir,
    delete_dir,
    delete_file,
    download_file,
    ensure_dir_exists,
    ensure_file_exists,
    extract_archive,
    get_file_extension,
    get_file_name,
    get_parent_dir,
    get_size,
    handle_replace,
    list_dir,
    move_dir,
    rename,
)


class TestUtilsIO:
    def test_get_size_file_auto_unit(self, tmp_path):
        """Test get_size with a file using automatic unit selection."""
        test_file = tmp_path / "file.txt"
        # Create a file with exactly 1024 bytes
        test_file.write_text("a" * 1024)

        size = get_size(str(test_file))
        assert size == "1.00 KB"

    def test_get_size_file_bytes(self, tmp_path):
        """Test get_size with a file in bytes."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello")  # 5 bytes

        size = get_size(str(test_file), unit="Bytes")
        assert size == "5 Bytes"

    def test_get_size_file_kb(self, tmp_path):
        """Test get_size with a file in KB."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("a" * 2048)  # 2048 bytes = 2 KB

        size = get_size(str(test_file), unit="KB")
        assert size == "2.00 KB"

    def test_get_size_file_mb(self, tmp_path):
        """Test get_size with a file in MB."""
        test_file = tmp_path / "file.txt"
        # 1 MB = 1024 * 1024 bytes
        test_file.write_bytes(b"a" * (1024 * 1024))

        size = get_size(str(test_file), unit="MB")
        assert size == "1.00 MB"

    def test_get_size_directory_auto_unit(self, tmp_path):
        """Test get_size with a directory using automatic unit selection."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("a" * 512)
        (test_dir / "file2.txt").write_text("b" * 512)

        size = get_size(str(test_dir))
        assert size == "1.00 KB"

    def test_get_size_directory_recursive(self, tmp_path):
        """Test get_size with nested directories."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        sub_dir = test_dir / "sub_dir"
        sub_dir.mkdir()

        (test_dir / "file1.txt").write_text("a" * 1024)
        (sub_dir / "file2.txt").write_text("b" * 1024)

        size = get_size(str(test_dir))
        assert size == "2.00 KB"

    def test_get_size_empty_directory(self, tmp_path):
        """Test get_size with an empty directory."""
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()

        size = get_size(str(test_dir))
        assert size == "0 Bytes"

    def test_get_size_zero_byte_file(self, tmp_path):
        """Test get_size with a zero-byte file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        size = get_size(str(test_file))
        assert size == "0 Bytes"

    def test_get_size_large_file_gb(self, tmp_path):
        """Test get_size with GB unit."""
        test_file = tmp_path / "large.bin"
        # For testing, create a 10 MB file and check GB conversion
        test_file.write_bytes(b"a" * (1024 * 1024 * 10))  # 10 MB

        size = get_size(str(test_file), unit="GB")
        assert "0.01 GB" in size

    def test_get_size_invalid_unit(self, tmp_path):
        """Test get_size with an invalid unit."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="Invalid unit"):
            get_size(str(test_file), unit="InvalidUnit")

    def test_get_size_nonexistent_path(self, tmp_path):
        """Test get_size with a nonexistent path."""
        with pytest.raises(FileNotFoundError):
            get_size(str(tmp_path / "nonexistent.txt"))

    def test_get_size_decimal_precision(self, tmp_path):
        """Test that get_size returns values with up to 2 decimal places."""
        test_file = tmp_path / "file.txt"
        # Create a file with 1536 bytes (1.5 KB)
        test_file.write_text("a" * 1536)

        size = get_size(str(test_file))
        assert size == "1.50 KB"

    def test_get_size_bytes_no_decimal(self, tmp_path):
        """Test that Bytes unit doesn't show decimal places."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("Hello World")  # 11 bytes

        size = get_size(str(test_file), unit="Bytes")
        assert size == "11 Bytes"
        assert "." not in size

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

    def test_list_dir(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        # Test default recursive behavior
        sub_dir = source_dir / "sub_dir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("content3")

        files = list_dir(str(source_dir))
        assert len(files) == 3
        assert str(source_dir / "file1.txt") in files
        assert str(source_dir / "file2.txt") in files
        assert str(sub_dir / "file3.txt") in files

        non_existing_dir = tmp_path / "non_existing_dir"
        with pytest.raises(FileNotFoundError):
            list_dir(str(non_existing_dir))

    def test_list_dir_with_extension(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")
        (source_dir / "file.md").write_text("content")

        txt_files = list_dir(str(source_dir), extension="txt")
        assert len(txt_files) == 1
        assert str(source_dir / "file.txt") in txt_files

    def test_copy_dir(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("content")
        dst_dir = tmp_path / "dst"

        copy_dir(str(src_dir), str(dst_dir), replace=True)
        assert dst_dir.exists()
        assert (dst_dir / "file.txt").exists()

        non_existing_src = tmp_path / "non_existing_src"
        with pytest.raises(FileNotFoundError):
            copy_dir(str(non_existing_src), str(dst_dir))

    def test_move_dir(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("content")
        dst_dir = tmp_path / "dst"

        move_dir(str(src_dir), str(dst_dir), replace=True)
        assert dst_dir.exists()
        assert not src_dir.exists()
        assert (dst_dir / "file.txt").exists()

        non_existing_src = tmp_path / "non_existing_src"
        with pytest.raises(FileNotFoundError):
            move_dir(str(non_existing_src), str(dst_dir))

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
        assert get_file_name("/absolute/path/to/file.txt") == "file.txt"
        assert get_file_name("file.txt") == "file.txt"

    def test_get_file_extension(self):
        assert get_file_extension("file.txt") == "txt"
        assert get_file_extension("file.tar.gz") == "gz"
        assert get_file_extension("no_extension") == ""

    def test_get_parent_dir(self):
        result = get_parent_dir("path/to/file.txt")
        assert str(result) == "path/to"

    def test_download_file(self, tmp_path):
        archive_file = tmp_path / "archive.zip"
        download_file(
            "https://httpbin.org/bytes/100",
            str(archive_file),
            replace=True,
        )
        assert archive_file.exists()
        assert archive_file.stat().st_size == 100

    def test_create_archive(self, tmp_path):
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")
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
        archive_file = tmp_path / "archive.zip"
        dest_dir = tmp_path / "dest_dir"

        # Create a simple zip file for testing
        import zipfile

        with zipfile.ZipFile(str(archive_file), "w") as zf:
            zf.writestr("test.txt", "test content")

        extract_archive(str(archive_file), str(dest_dir))
        assert dest_dir.exists()
        assert (dest_dir / "test.txt").exists()

    def test_extract_archive_invalid_file(self, tmp_path):
        non_existing_archive = tmp_path / "non_existing_archive.zip"
        dest_dir = tmp_path / "dest_dir"

        with pytest.raises(FileNotFoundError):
            extract_archive(str(non_existing_archive), str(dest_dir))
