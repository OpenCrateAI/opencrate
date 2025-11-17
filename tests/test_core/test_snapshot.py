import os
import shutil

import numpy as np
import pytest
from matplotlib.figure import Figure
from PIL import Image

from opencrate.core.snapshot import Snapshot


class TestCoreSnapshot:
    def setup_method(self):
        output_dir = os.getenv("TEST_OUTPUT_DIR", ".")
        self.snapshots_dir = os.path.join(output_dir, "snapshots")
        if os.path.isdir(self.snapshots_dir):
            shutil.rmtree(self.snapshots_dir, ignore_errors=True)

    def teardown_method(self):
        if os.path.isdir(os.path.join("snapshots")):
            shutil.rmtree(os.path.join("snapshots"))

    def test_setup(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        with pytest.raises(AssertionError, match=r"\n\nNot an OpenCrate project directory.\n"):
            snapshot.setup(name="test_snapshot")

    def test_list_no_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        tags = snapshot.list_tags(return_tags=True)
        assert tags == []
        tags = snapshot.list_tags()
        assert tags is None

    def test_list_with_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag1")
        snapshot.setup(name="test_snapshot", tag="test_tag2")
        snapshot.setup(name="test_snapshot", tag="test_tag3")

        with pytest.raises(ValueError, match=r"`return_tags` must be a boolean, but received"):
            tags = snapshot.list_tags(return_tags="wrong_argument")  # pyright: ignore
        tags = snapshot.list_tags(return_tags=True)
        assert tags == ["test_tag1", "test_tag2", "test_tag3"]

    def test_checkpoint(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        checkpoint = {"model_state": "dummy_state"}
        snapshot.checkpoint("checkpoint.pth").save(checkpoint)
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth"))

    def test_figure_numpy(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        image = np.random.rand(100, 100, 3)
        snapshot.image("image.png").save(image)
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "images", "image.png"))

    def test_figure_pil(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        image = Image.new("RGB", (100, 100))
        snapshot.image("image.png").save(image)
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "images", "image.png"))

    def test_figure_matplotlib(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        fig = Figure()
        snapshot.image("figure.png").save(fig)
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "images", "figure.png"))

    def test_setup_with_tag(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag")

        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag"))
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "checkpoints"))
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "images"))
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.log"))

    def test_asset_path_access(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        snapshot.image("image2.png").save(np.random.rand(100, 100, 3))
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join("snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth")
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "v0", "images", "image.png")
        assert snapshot.path.image("image2.png") == os.path.join("snapshots", "test_snapshot", "v0", "images", "image2.png")

    def test_asset_path_access_with_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag")

        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        snapshot.image("image2.png").save(np.random.rand(100, 100, 3))
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag", "images", "image.png")
        assert snapshot.path.image("image2.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag", "images", "image2.png")

    def test_asset_path_access_different_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        snapshot.setup(name="test_snapshot", tag="test_tag1")
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))

        snapshot.setup(name="test_snapshot", tag="test_tag2")
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))

        snapshot.setup(name="test_snapshot", tag="test_tag3")
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag3", "images", "image.png")
        assert snapshot.path.checkpoint("checkpoint.pth", tag="test_tag1") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag1",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png", tag="test_tag1") == os.path.join("snapshots", "test_snapshot", "v0:test_tag1", "images", "image.png")
        assert snapshot.path.checkpoint("checkpoint.pth", tag="test_tag2") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag2",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png", tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v0:test_tag2", "images", "image.png")

    def test_asset_path_access_different_tags_with_version(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        snapshot.setup(name="test_snapshot", tag="test_tag1")  # version 0, tag test_tag1
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        assert snapshot.version == 0

        snapshot.version = None
        snapshot.setup(name="test_snapshot", tag="test_tag2")  # version 1, tag test_tag2
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        assert snapshot.version == 1

        snapshot.version = None
        snapshot.setup(name="test_snapshot", tag="test_tag3")  # version 2, tag test_tag3
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        assert snapshot.version == 2
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v2:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "images", "image.png")
        assert snapshot.path.checkpoint("checkpoint.pth", version=1, tag="test_tag2") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v1:test_tag2",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png", version=1, tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v1:test_tag2", "images", "image.png")
        assert snapshot.path.checkpoint("checkpoint.pth", version=2, tag="test_tag3") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v2:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png", version=2, tag="test_tag3") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "images", "image.png")

    def test_dev_version(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", start="dev", tag="test_tag")

        assert snapshot.version == "dev"
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "dev:test_tag"))
        snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
        snapshot.image("image.png").save(np.random.rand(100, 100, 3))
        snapshot.debug("This is a debug message")
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "dev:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "images", "image.png")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "dev:test_tag", "test_snapshot.log"))

        snapshot.version = None
        snapshot.setup(name="test_snapshot", start="dev", tag="test_tag")
        snapshot.debug("This is a debug message")
        assert snapshot.version == "dev"
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "dev:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "images", "image.png")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "dev:test_tag", "test_snapshot.log"))
        assert os.path.isfile(
            os.path.join(
                "snapshots",
                "test_snapshot",
                "dev:test_tag",
                "test_snapshot.history.log",
            )
        )

        snapshot.version = None
        snapshot.setup(name="test_snapshot")
        snapshot.version = None
        snapshot.setup(name="test_snapshot")
        assert snapshot.version == 1
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0"))
        assert snapshot.path.checkpoint("checkpoint.pth", version="dev", tag="test_tag") == os.path.join(
            "snapshots",
            "test_snapshot",
            "dev:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.image("image.png", version="dev", tag="test_tag") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "images", "image.png")

    def test_reset(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        snapshot.reset(confirm=True)
        assert not os.path.isdir(os.path.join("snapshots", "test_snapshot"))

    def test_logging(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", log_level="DEBUG")

        snapshot.debug("This is a debug message")
        snapshot.info("This is an info message")
        snapshot.warning("This is a warning message")
        snapshot.error("This is an error message")
        snapshot.critical("This is a critical message")
        snapshot.success("This is a success message")
        snapshot.exception("This is an exception message")
        log_path = os.path.join("snapshots", "test_snapshot", "v0", "test_snapshot.log")
        assert os.path.isfile(log_path)
        with open(log_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def test_logging_without_setup(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.debug("This is a debug message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.info("This is an info message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.warning("This is a warning message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.error("This is an error message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.critical("This is a critical message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.success("This is a success message")
        with pytest.raises(RuntimeError, match=r"Snapshot setup is not done yet"):
            snapshot.exception("This is an exception message")

    def test_history_logging(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", log_level="DEBUG")

        snapshot.debug("This is a debug message")
        snapshot.info("This is an info message")
        snapshot.warning("This is a warning message")
        snapshot.error("This is an error message")
        snapshot.critical("This is a critical message")
        snapshot.success("This is a success message")
        snapshot.exception("This is an exception message")
        log_path = os.path.join("snapshots", "test_snapshot", "v0", "test_snapshot.log")
        assert os.path.isfile(log_path)
        with open(log_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

        snapshot.setup(name="test_snapshot", log_level="DEBUG", start="last")
        snapshot.debug("This is a debug message")
        snapshot.info("This is an info message")
        snapshot.warning("This is a warning message")
        snapshot.error("This is an error message")
        snapshot.critical("This is a critical message")
        snapshot.success("This is a success message")
        snapshot.exception("This is an exception message")
        log_history_path = os.path.join("snapshots", "test_snapshot", "v0", "test_snapshot.history.log")
        assert os.path.isfile(log_history_path)
        with open(log_history_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def test_history_logging_with_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag", log_level="DEBUG")

        snapshot.debug("This is a debug message")
        snapshot.info("This is an info message")
        snapshot.warning("This is a warning message")
        snapshot.error("This is an error message")
        snapshot.critical("This is a critical message")
        snapshot.success("This is a success message")
        snapshot.exception("This is an exception message")
        log_path = os.path.join("snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.log")
        assert os.path.isfile(log_path)
        with open(log_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

        snapshot.setup(name="test_snapshot", tag="test_tag", log_level="DEBUG", start="last")
        snapshot.debug("This is a debug message")
        snapshot.info("This is an info message")
        snapshot.warning("This is a warning message")
        snapshot.error("This is an error message")
        snapshot.critical("This is a critical message")
        snapshot.success("This is a success message")
        snapshot.exception("This is an exception message")
        log_history_path = os.path.join("snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.history.log")
        assert os.path.isfile(log_history_path)
        with open(log_history_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def test_errors(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        with pytest.raises(ValueError, match=r"`log_level` must be a string, but received"):
            snapshot.setup(name="test_snapshot", log_level=123)  # pyright: ignore
        with pytest.raises(ValueError, match=r"`log_level` must be one of"):
            snapshot.setup(name="test_snapshot", log_level="INVALID")
        with pytest.raises(ValueError, match=r"`log_time` must be a boolean, but received"):
            snapshot.setup(name="test_snapshot", log_time=5)  # pyright: ignore
        with pytest.raises(ValueError, match=r"`tag` must be a string or None, but received"):
            snapshot.setup(name="test_snapshot", tag=5)  # pyright: ignore
        with pytest.raises(
            ValueError,
            match=r"must be an int, 'new', 'last' or 'dev', but received",
        ):
            snapshot.setup(name="test_snapshot", start="hello")
        with pytest.raises(ValueError, match=r"Please confirm to reset the versioning"):
            snapshot.reset()
        with pytest.raises(ValueError, match=r"No snapshots are created for "):
            snapshot.setup(name="test_snapshot", start=45)
        with pytest.raises(ValueError, match=r"does not exist, cannot set `start` to"):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")

            snapshot.version = None
            snapshot.setup(name="test_snapshot", start=44)
        with pytest.raises(AssertionError, match=r"No 'abc' snapshot type found for version"):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")

            snapshot.path.abc("whatever.pth", check_exists=True)
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'checkpoint_non_existing.pth' found in 'checkpoint' for version",
        ):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")
            snapshot.checkpoint("checkpoint.pth").save({"model_state": "dummy_state"})
            snapshot.path.checkpoint("checkpoint_non_existing.pth", check_exists=True)
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'image_non_existing.png' found in 'image' for version",
        ):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")
            snapshot.image("image.png").save(np.random.rand(100, 100, 3))
            snapshot.path.image("image_non_existing.png", check_exists=True)
