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
        snapshot.checkpoint(checkpoint, "checkpoint.pth")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth"))

    def test_figure_numpy(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        image = np.random.rand(100, 100, 3)
        snapshot.figure(image, "image.png")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png"))

    def test_figure_pil(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        image = Image.new("RGB", (100, 100))
        snapshot.figure(image, "image.png")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png"))

    def test_figure_matplotlib(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        fig = Figure()
        snapshot.figure(fig, "figure.png")
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0", "figures", "figure.png"))

    def test_setup_with_tag(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag")

        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag"))
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "checkpoints"))
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "figures"))
        assert os.path.isfile(os.path.join("snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.log"))

    def test_asset_path_access(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot")

        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        snapshot.bias(np.random.rand(100, 100, 3), "bias.png")
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join("snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth")
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "v0", "randoms", "random.png")
        assert snapshot.path.bias("bias.png") == os.path.join("snapshots", "test_snapshot", "v0", "biases", "bias.png")

    def test_asset_path_access_with_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", tag="test_tag")

        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag", "randoms", "random.png")

    def test_asset_path_access_different_tags(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        snapshot.setup(name="test_snapshot", tag="test_tag1")
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")

        snapshot.setup(name="test_snapshot", tag="test_tag2")
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")

        snapshot.setup(name="test_snapshot", tag="test_tag3")
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag3", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "v0:test_tag3", "randoms", "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth", tag="test_tag1") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag1",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png", tag="test_tag1") == os.path.join("snapshots", "test_snapshot", "v0:test_tag1", "figures", "image.png")
        assert snapshot.path.random("random.png", tag="test_tag1") == os.path.join("snapshots", "test_snapshot", "v0:test_tag1", "randoms", "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth", tag="test_tag2") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v0:test_tag2",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png", tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v0:test_tag2", "figures", "image.png")
        assert snapshot.path.random("random.png", tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v0:test_tag2", "randoms", "random.png")

    def test_asset_path_access_different_tags_with_version(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)

        snapshot.setup(name="test_snapshot", tag="test_tag1")  # version 0, tag test_tag1
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert snapshot.version == 0

        snapshot.version = None
        snapshot.setup(name="test_snapshot", tag="test_tag2")  # version 1, tag test_tag2
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert snapshot.version == 1

        snapshot.version = None
        snapshot.setup(name="test_snapshot", tag="test_tag3")  # version 2, tag test_tag3
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert snapshot.version == 2
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v2:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "randoms", "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth", version=1, tag="test_tag2") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v1:test_tag2",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png", version=1, tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v1:test_tag2", "figures", "image.png")
        assert snapshot.path.random("random.png", version=1, tag="test_tag2") == os.path.join("snapshots", "test_snapshot", "v1:test_tag2", "randoms", "random.png")
        assert snapshot.path.checkpoint("checkpoint.pth", version=2, tag="test_tag3") == os.path.join(
            "snapshots",
            "test_snapshot",
            "v2:test_tag3",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png", version=2, tag="test_tag3") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "figures", "image.png")
        assert snapshot.path.random("random.png", version=2, tag="test_tag3") == os.path.join("snapshots", "test_snapshot", "v2:test_tag3", "randoms", "random.png")

    def test_dev_version(self, tmp_path):
        # Create config.json in tmp_path
        config_file = tmp_path / "config.json"
        config_file.write_text('{"project_name": "test_snapshot"}')

        snapshot = Snapshot()
        snapshot._config_dir = str(tmp_path)
        snapshot.setup(name="test_snapshot", start="dev", tag="test_tag")

        assert snapshot.version == "dev"
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "dev:test_tag"))
        snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        snapshot.random(np.random.rand(100, 100, 3), "random.png")
        snapshot.debug("This is a debug message")
        assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
            "snapshots",
            "test_snapshot",
            "dev:test_tag",
            "checkpoints",
            "checkpoint.pth",
        )
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png")
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
        assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png")
        assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png")
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
        assert snapshot.path.figure("image.png", version="dev", tag="test_tag") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png")
        assert snapshot.path.random("random.png", version="dev", tag="test_tag") == os.path.join("snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png")

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

        snapshot.debug("This is a debug message")
        snapshot_name = snapshot.snapshot_name
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.info("This is an info message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is an info message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.warning("This is a warning message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is a warning message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.error("This is an error message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is an error message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.critical("This is a critical message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is a critical message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.success("This is a success message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is a success message" in log_content

        snapshot.reset(confirm=True)
        snapshot.version = None
        snapshot.snapshot_name = ""
        snapshot._setup_not_done = True
        snapshot.exception("This is a exception message")
        log_file_path = os.path.join("snapshots", snapshot_name, "v0", f"{snapshot_name}.log")
        assert log_file_path == snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path) as log_file:
            log_content = log_file.read()
            assert "This is a exception message" in log_content

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

            snapshot.path.abc("whatever.pth")
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'checkpoint_non_existing.pth' found in 'checkpoint' for version",
        ):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")
            snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
            assert snapshot.path.checkpoint("checkpoint.pth") == os.path.join("snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth")
            snapshot.path.checkpoint("checkpoint_non_existing.pth")
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'figure_non_existing.png' found in 'figure' for version",
        ):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")
            snapshot.figure(np.random.rand(100, 100, 3), "image.png")
            assert snapshot.path.figure("image.png") == os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png")
            snapshot.path.figure("figure_non_existing.png")
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'random_non_existing.png' found in 'random' for version",
        ):
            snapshot.version = None
            snapshot.reset(confirm=True)
            snapshot.setup(name="test_snapshot")
            snapshot.random(np.random.rand(100, 100, 3), "random.png")
            assert snapshot.path.random("random.png") == os.path.join("snapshots", "test_snapshot", "v0", "randoms", "random.png")
            snapshot.path.random("random_non_existing.png")
