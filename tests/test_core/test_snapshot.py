import json
import os
import shutil

import numpy as np
import pytest
from matplotlib.figure import Figure
from PIL import Image

from opencrate.core.snapshot import Snapshot

try:
    import torch  # noqa: F811

    _has_torch = True
except:
    _has_torch = False


class TestCoreSnapshot:
    test_root_dir: str = "tests/assets"

    def setup_method(self):
        if os.path.isdir(os.path.join("snapshots")):
            shutil.rmtree(os.path.join("snapshots"), ignore_errors=True)

        with open(os.path.join(self.test_root_dir, "config.json"), "w") as f:
            json.dump({"project_name": "test_snapshot"}, f, indent=4)

    def teardown_method(self):
        if os.path.isdir(os.path.join("snapshots")):
            shutil.rmtree(os.path.join("snapshots"))

    def setup_test_setup(self):
        self.snapshot = Snapshot()

    def test_setup(self):
        self.setup_test_setup()
        with pytest.raises(
            AssertionError, match=r"\n\nNot an OpenCrate project directory.\n"
        ):
            self.snapshot.setup(name="test_snapshot")

    def setup_test_list_no_tags(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_list_no_tags(self):
        self.setup_test_list_no_tags()
        tags = self.snapshot.list_tags(return_tags=True)
        assert tags == []
        tags = self.snapshot.list_tags()
        assert tags is None

    def setup_test_list_with_tags(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", tag="test_tag1")
        self.snapshot.setup(name="test_snapshot", tag="test_tag2")
        self.snapshot.setup(name="test_snapshot", tag="test_tag3")

    def test_list_with_tags(self):
        self.setup_test_list_with_tags()
        with pytest.raises(
            ValueError, match=r"`return_tags` must be a boolean, but received"
        ):
            tags = self.snapshot.list_tags(return_tags="wrong_argument")  # type: ignore
        tags = self.snapshot.list_tags(return_tags=True)
        assert tags == ["test_tag1", "test_tag2", "test_tag3"]

    def setup_test_checkpoint(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_checkpoint(self):
        if _has_torch:
            self.setup_test_checkpoint()
            checkpoint = {"model_state": "dummy_state"}
            self.snapshot.checkpoint(checkpoint, "checkpoint.pth")
            assert os.path.isfile(
                os.path.join(
                    "snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth"
                )
            )

    def setup_test_figure_numpy(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_figure_numpy(self):
        self.setup_test_figure_numpy()
        image = np.random.rand(100, 100, 3)
        self.snapshot.figure(image, "image.png")
        assert os.path.isfile(
            os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png")
        )

    def setup_test_figure_pil(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_figure_pil(self):
        self.setup_test_figure_pil()
        image = Image.new("RGB", (100, 100))
        self.snapshot.figure(image, "image.png")
        assert os.path.isfile(
            os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png")
        )

    def setup_test_figure_matplotlib(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_figure_matplotlib(self):
        self.setup_test_figure_matplotlib()
        fig = Figure()
        self.snapshot.figure(fig, "figure.png")
        assert os.path.isfile(
            os.path.join("snapshots", "test_snapshot", "v0", "figures", "figure.png")
        )

    def setup_test_figure_torch(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_figure_torch(self):
        self.setup_test_figure_torch()
        if _has_torch:
            image = torch.rand(3, 100, 100)
            self.snapshot.figure(image, "image.png")
            assert os.path.isfile(
                os.path.join("snapshots", "test_snapshot", "v0", "figures", "image.png")
            )

    def setup_test_setup_with_tag(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", tag="test_tag")

    def test_setup_with_tag(self):
        self.setup_test_setup_with_tag()
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0:test_tag"))
        if _has_torch:
            assert os.path.isdir(
                os.path.join("snapshots", "test_snapshot", "v0:test_tag", "checkpoints")
            )
        assert os.path.isdir(
            os.path.join("snapshots", "test_snapshot", "v0:test_tag", "figures")
        )
        assert os.path.isfile(
            os.path.join(
                "snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.log"
            )
        )

    def setup_test_asset_path_access(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_asset_path_access(self):
        self.setup_test_asset_path_access()
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        self.snapshot.bias(np.random.rand(100, 100, 3), "bias.png")
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth"
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "v0", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "v0", "randoms", "random.png"
        )
        assert self.snapshot.path.bias("bias.png") == os.path.join(
            "snapshots", "test_snapshot", "v0", "biases", "bias.png"
        )

    def setup_test_asset_path_access_with_tags(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", tag="test_tag")

    def test_asset_path_access_with_tags(self):
        self.setup_test_asset_path_access_with_tags()
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots",
                "test_snapshot",
                "v0:test_tag",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag", "randoms", "random.png"
        )

    def setup_test_asset_path_access_different_tags(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir

    def test_asset_path_access_different_tags(self):
        self.setup_test_asset_path_access_different_tags()

        self.snapshot.setup(name="test_snapshot", tag="test_tag1")
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")

        self.snapshot.setup(name="test_snapshot", tag="test_tag2")
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")

        self.snapshot.setup(name="test_snapshot", tag="test_tag3")
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots",
                "test_snapshot",
                "v0:test_tag3",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag3", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag3", "randoms", "random.png"
        )
        if _has_torch:
            assert self.snapshot.path.checkpoint(
                "checkpoint.pth", tag="test_tag1"
            ) == os.path.join(
                "snapshots",
                "test_snapshot",
                "v0:test_tag1",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png", tag="test_tag1") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag1", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png", tag="test_tag1") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag1", "randoms", "random.png"
        )
        if _has_torch:
            assert self.snapshot.path.checkpoint(
                "checkpoint.pth", tag="test_tag2"
            ) == os.path.join(
                "snapshots",
                "test_snapshot",
                "v0:test_tag2",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png", tag="test_tag2") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag2", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png", tag="test_tag2") == os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag2", "randoms", "random.png"
        )

    def setup_test_asset_path_access_different_tags_with_version(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir

    def test_asset_path_access_different_tags_with_version(self):
        self.setup_test_asset_path_access_different_tags_with_version()

        self.snapshot.setup(
            name="test_snapshot", tag="test_tag1"
        )  # version 0, tag test_tag1
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert self.snapshot.version == 0

        self.snapshot.version = None
        self.snapshot.setup(
            name="test_snapshot", tag="test_tag2"
        )  # version 1, tag test_tag2
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert self.snapshot.version == 1

        self.snapshot.version = None
        self.snapshot.setup(
            name="test_snapshot", tag="test_tag3"
        )  # version 2, tag test_tag3
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        assert self.snapshot.version == 2
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots",
                "test_snapshot",
                "v2:test_tag3",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "v2:test_tag3", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "v2:test_tag3", "randoms", "random.png"
        )
        if _has_torch:
            assert self.snapshot.path.checkpoint(
                "checkpoint.pth", version=1, tag="test_tag2"
            ) == os.path.join(
                "snapshots",
                "test_snapshot",
                "v1:test_tag2",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure(
            "image.png", version=1, tag="test_tag2"
        ) == os.path.join(
            "snapshots", "test_snapshot", "v1:test_tag2", "figures", "image.png"
        )
        assert self.snapshot.path.random(
            "random.png", version=1, tag="test_tag2"
        ) == os.path.join(
            "snapshots", "test_snapshot", "v1:test_tag2", "randoms", "random.png"
        )
        if _has_torch:
            assert self.snapshot.path.checkpoint(
                "checkpoint.pth", version=2, tag="test_tag3"
            ) == os.path.join(
                "snapshots",
                "test_snapshot",
                "v2:test_tag3",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure(
            "image.png", version=2, tag="test_tag3"
        ) == os.path.join(
            "snapshots", "test_snapshot", "v2:test_tag3", "figures", "image.png"
        )
        assert self.snapshot.path.random(
            "random.png", version=2, tag="test_tag3"
        ) == os.path.join(
            "snapshots", "test_snapshot", "v2:test_tag3", "randoms", "random.png"
        )

    def setup_test_dev_version(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", start="dev", tag="test_tag")

    def test_dev_version(self):
        self.setup_test_dev_version()
        assert self.snapshot.version == "dev"
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "dev:test_tag"))
        if _has_torch:
            self.snapshot.checkpoint({"model_state": "dummy_state"}, "checkpoint.pth")
        self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
        self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
        self.snapshot.debug("This is a debug message")
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots",
                "test_snapshot",
                "dev:test_tag",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png"
        )
        assert os.path.isfile(
            os.path.join(
                "snapshots", "test_snapshot", "dev:test_tag", "test_snapshot.log"
            )
        )

        self.snapshot.version = None
        self.setup_test_dev_version()
        self.snapshot.debug("This is a debug message")
        assert self.snapshot.version == "dev"
        if _has_torch:
            assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                "snapshots",
                "test_snapshot",
                "dev:test_tag",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure("image.png") == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png"
        )
        assert self.snapshot.path.random("random.png") == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png"
        )
        assert os.path.isfile(
            os.path.join(
                "snapshots", "test_snapshot", "dev:test_tag", "test_snapshot.log"
            )
        )
        assert os.path.isfile(
            os.path.join(
                "snapshots",
                "test_snapshot",
                "dev:test_tag",
                "test_snapshot.history.log",
            )
        )

        self.snapshot.version = None
        self.snapshot.setup(name="test_snapshot")
        self.snapshot.version = None
        self.snapshot.setup(name="test_snapshot")
        assert self.snapshot.version == 1
        assert os.path.isdir(os.path.join("snapshots", "test_snapshot", "v0"))
        if _has_torch:
            assert self.snapshot.path.checkpoint(
                "checkpoint.pth", version="dev", tag="test_tag"
            ) == os.path.join(
                "snapshots",
                "test_snapshot",
                "dev:test_tag",
                "checkpoints",
                "checkpoint.pth",
            )
        assert self.snapshot.path.figure(
            "image.png", version="dev", tag="test_tag"
        ) == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "figures", "image.png"
        )
        assert self.snapshot.path.random(
            "random.png", version="dev", tag="test_tag"
        ) == os.path.join(
            "snapshots", "test_snapshot", "dev:test_tag", "randoms", "random.png"
        )

    def setup_test_reset(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot")

    def test_reset(self):
        self.setup_test_reset()
        self.snapshot.reset(confirm=True)
        assert not os.path.isdir(os.path.join("snapshots", "test_snapshot"))

    def setup_test_logging(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", log_level="DEBUG")

    def test_logging(self):
        self.setup_test_logging()
        self.snapshot.debug("This is a debug message")
        self.snapshot.info("This is an info message")
        self.snapshot.warning("This is a warning message")
        self.snapshot.error("This is an error message")
        self.snapshot.critical("This is a critical message")
        self.snapshot.success("This is a success message")
        self.snapshot.exception("This is an exception message")
        log_path = os.path.join("snapshots", "test_snapshot", "v0", "test_snapshot.log")
        assert os.path.isfile(log_path)
        with open(log_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def setup_test_logging_without_setup(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir

    def test_logging_without_setup(self):
        self.setup_test_logging_without_setup()
        self.snapshot.debug("This is a debug message")
        snapshot_name = self.snapshot.snapshot_name
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.info("This is an info message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is an info message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.warning("This is a warning message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a warning message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.error("This is an error message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is an error message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.critical("This is a critical message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a critical message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.success("This is a success message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a success message" in log_content

        self.snapshot.reset(confirm=True)
        self.snapshot.version = None
        self.snapshot.snapshot_name = ""
        self.snapshot._setup_not_done = True
        self.snapshot.exception("This is a exception message")
        log_file_path = os.path.join(
            "snapshots", snapshot_name, "v0", f"{snapshot_name}.log"
        )
        assert log_file_path == self.snapshot.log_path
        assert os.path.isfile(log_file_path)
        with open(log_file_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a exception message" in log_content

    def setup_test_history_logging(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", log_level="DEBUG")

    def test_history_logging(self):
        self.setup_test_history_logging()

        self.snapshot.debug("This is a debug message")
        self.snapshot.info("This is an info message")
        self.snapshot.warning("This is a warning message")
        self.snapshot.error("This is an error message")
        self.snapshot.critical("This is a critical message")
        self.snapshot.success("This is a success message")
        self.snapshot.exception("This is an exception message")
        log_path = os.path.join("snapshots", "test_snapshot", "v0", "test_snapshot.log")
        assert os.path.isfile(log_path)
        with open(log_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

        self.snapshot.setup(name="test_snapshot", log_level="DEBUG", start="last")
        self.snapshot.debug("This is a debug message")
        self.snapshot.info("This is an info message")
        self.snapshot.warning("This is a warning message")
        self.snapshot.error("This is an error message")
        self.snapshot.critical("This is a critical message")
        self.snapshot.success("This is a success message")
        self.snapshot.exception("This is an exception message")
        log_history_path = os.path.join(
            "snapshots", "test_snapshot", "v0", "test_snapshot.history.log"
        )
        assert os.path.isfile(log_history_path)
        with open(log_history_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def setup_test_history_logging_with_tags(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir
        self.snapshot.setup(name="test_snapshot", tag="test_tag", log_level="DEBUG")

    def test_history_logging_with_tags(self):
        self.setup_test_history_logging_with_tags()

        self.snapshot.debug("This is a debug message")
        self.snapshot.info("This is an info message")
        self.snapshot.warning("This is a warning message")
        self.snapshot.error("This is an error message")
        self.snapshot.critical("This is a critical message")
        self.snapshot.success("This is a success message")
        self.snapshot.exception("This is an exception message")
        log_path = os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.log"
        )
        assert os.path.isfile(log_path)
        with open(log_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

        self.snapshot.setup(
            name="test_snapshot", tag="test_tag", log_level="DEBUG", start="last"
        )
        self.snapshot.debug("This is a debug message")
        self.snapshot.info("This is an info message")
        self.snapshot.warning("This is a warning message")
        self.snapshot.error("This is an error message")
        self.snapshot.critical("This is a critical message")
        self.snapshot.success("This is a success message")
        self.snapshot.exception("This is an exception message")
        log_history_path = os.path.join(
            "snapshots", "test_snapshot", "v0:test_tag", "test_snapshot.history.log"
        )
        assert os.path.isfile(log_history_path)
        with open(log_history_path, "r") as log_file:
            log_content = log_file.read()
            assert "This is a debug message" in log_content
            assert "This is an info message" in log_content
            assert "This is a warning message" in log_content
            assert "This is an error message" in log_content
            assert "This is a critical message" in log_content
            assert "This is a success message" in log_content
            assert "This is an exception message" in log_content

    def setup_test_errors(self):
        self.snapshot = Snapshot()
        self.snapshot._config_dir = self.test_root_dir

    def test_errors(self):
        self.setup_test_errors()

        with pytest.raises(
            ValueError, match=r"`log_level` must be a string, but received"
        ):
            self.snapshot.setup(name="test_snapshot", log_level=123)  # type: ignore
        with pytest.raises(ValueError, match=r"`log_level` must be one of"):
            self.snapshot.setup(name="test_snapshot", log_level="INVALID")
        with pytest.raises(
            ValueError, match=r"`log_time` must be a boolean, but received"
        ):
            self.snapshot.setup(name="test_snapshot", log_time=5)  # type: ignore
        with pytest.raises(
            ValueError, match=r"`tag` must be a string or None, but received"
        ):
            self.snapshot.setup(name="test_snapshot", tag=5)  # type: ignore
        with pytest.raises(
            ValueError,
            match=r"must be an int, 'new', 'last' or 'dev', but received",
        ):
            self.snapshot.setup(name="test_snapshot", start="hello")
        with pytest.raises(ValueError, match=r"Please confirm to reset the versioning"):
            self.snapshot.reset()
        with pytest.raises(ValueError, match=r"No snapshots are created for "):
            self.snapshot.setup(name="test_snapshot", start=45)
        with pytest.raises(ValueError, match=r"does not exist, cannot set `start` to"):
            self.snapshot.version = None
            self.snapshot.reset(confirm=True)
            self.snapshot.setup(name="test_snapshot")

            self.snapshot.version = None
            self.snapshot.setup(name="test_snapshot", start=44)
        with pytest.raises(
            AssertionError, match=r"No 'abc' snapshot type found for version"
        ):
            self.snapshot.version = None
            self.snapshot.reset(confirm=True)
            self.snapshot.setup(name="test_snapshot")

            self.snapshot.path.abc("whatever.pth")
        if _has_torch:
            with pytest.raises(
                AssertionError,
                match=r"No snapshot 'checkpoint_non_existing.pth' found in 'checkpoint' for version",
            ):
                self.snapshot.version = None
                self.snapshot.reset(confirm=True)
                self.snapshot.setup(name="test_snapshot")
                self.snapshot.checkpoint(
                    {"model_state": "dummy_state"}, "checkpoint.pth"
                )
                assert self.snapshot.path.checkpoint("checkpoint.pth") == os.path.join(
                    "snapshots", "test_snapshot", "v0", "checkpoints", "checkpoint.pth"
                )
                self.snapshot.path.checkpoint("checkpoint_non_existing.pth")
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'figure_non_existing.png' found in 'figure' for version",
        ):
            self.snapshot.version = None
            self.snapshot.reset(confirm=True)
            self.snapshot.setup(name="test_snapshot")
            self.snapshot.figure(np.random.rand(100, 100, 3), "image.png")
            assert self.snapshot.path.figure("image.png") == os.path.join(
                "snapshots", "test_snapshot", "v0", "figures", "image.png"
            )
            self.snapshot.path.figure("figure_non_existing.png")
        with pytest.raises(
            AssertionError,
            match=r"No snapshot 'random_non_existing.png' found in 'random' for version",
        ):
            self.snapshot.version = None
            self.snapshot.reset(confirm=True)
            self.snapshot.setup(name="test_snapshot")
            self.snapshot.random(np.random.rand(100, 100, 3), "random.png")
            assert self.snapshot.path.random("random.png") == os.path.join(
                "snapshots", "test_snapshot", "v0", "randoms", "random.png"
            )
            self.snapshot.path.random("random_non_existing.png")
