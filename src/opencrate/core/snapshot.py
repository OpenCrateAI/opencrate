import json
import os
import pickle
import sys
from ast import Dict
from functools import partial
from shutil import copyfile, rmtree
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.figure import Figure

_has_torch = True
_has_pillow = True


try:
    import torch  # type: ignore
except ImportError:
    _has_torch = False

try:
    from PIL import Image
except ImportError:
    _has_pillow = False


class Snapshot:
    def __init__(self):
        self.version: Union[str, int, None] = None
        self.start: Union[str, int, None] = None
        self.tag: str = ""
        self.logger = logger
        self.snapshot_name: str = ""
        self._setup_not_done = True
        self._config_dir: str = ".opencrate"

    def setup(
        self,
        start: Union[int, str] = "new",
        tag: Optional[str] = None,
        replace: bool = False,
        name: Optional[str] = None,
        log_level: str = "INFO",
        log_time: bool = False,
    ) -> None:
        """
        Setup the logger for snapshot logging.

        Args:
            log_level (str, optional): Logging log_level. Defaults to "INFO".
            log_time (bool, optional): Whether to log the time. Defaults to False.
            start (Union[int, str], optional): Version to use. Defaults to "new".
            tag (Optional[str], optional): Tag for the snapshot. Defaults to None.

        Raises:
            ValueError: If `log_level` is not an str or valid logging log_level.
            ValueError: If `log_time` is not a boolean.
            ValueError: If `tag` is not a string or None.
            ValueError: If `start` is not an int, 'new', 'last' or 'dev'.

        Returns:
            None
        """
        assert os.path.isdir(self._config_dir), (
            "\n\nNot an OpenCrate project directory.\n"
        )

        if not isinstance(log_level, str):  # type: ignore
            raise ValueError(
                f"\n\n`log_level` must be a string, but received {type(log_level)}"
            )
        log_level = log_level.upper()
        if log_level not in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "SUCCESS",
        ]:
            raise ValueError(
                "\n\n`log_level` must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS']"
            )
        if not isinstance(log_time, bool):  # type: ignore
            raise ValueError(
                f"\n\n`log_time` must be a boolean, but received {type(log_time)}"
            )
        if tag is not None and not isinstance(tag, str):  # type: ignore
            raise ValueError(
                f"\n\n`tag` must be a string or None, but received {type(tag)}"
            )
        try:
            start = int(start)
        except:
            pass
        if not isinstance(start, (int, str)) or (  # type: ignore
            isinstance(start, str) and start not in ["new", "last", "dev"]
        ):
            raise ValueError(
                f"\n\n`start` must be an int, 'new', 'last' or 'dev', but received {type(start)}"
            )

        self.start = start
        self.tag = tag if tag else ""

        if isinstance(start, int) or start == "dev":
            self.version = start

        self._name = name
        self.snapshot_name = self._snapshot_name()
        self._get_version()  # this must be done before setting up the self.dir_path
        if self.version == "dev":
            self.version_name = f"{self.version}"
        else:
            self.version_name = f"v{self.version}"
        if self.tag:
            self.version_name = f"{self.version_name}:{self.tag}"

        self.dir_path = os.path.join("snapshots", self.snapshot_name, self.version_name)

        if replace and os.path.isdir(self.dir_path):
            rmtree(self.dir_path)

        self.logger.remove()
        self.logger.add(
            lambda msg: print(msg, end=""),  # Use print instead of sys.stderr.write
            format="<level>{level: <8} </level> {message}",
            level=log_level,
            colorize=True,
            # enqueue=True,  # Use a queue for thread-safe logging
            backtrace=False,  # Show full stack traces for exceptions
            diagnose=True,  # Show detailed information about variables in stack traces
        )
        # self.logger.level("INFO", color="<blue>")
        self.logger.level("INFO")

        self.log_path = os.path.join(self.dir_path, f"{self.snapshot_name}.log")

        if start != "new":
            self.history_log_path = self.log_path.replace(
                f"{self.snapshot_name}.log", f"{self.snapshot_name}.history.log"
            )

            if os.path.isfile(self.log_path):
                if not os.path.isfile(self.history_log_path):
                    copyfile(self.log_path, self.history_log_path)

                self.logger.add(
                    self.history_log_path,
                    format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} {message}",
                    level=log_level.upper(),
                    rotation="30 MB",
                    retention="30 days",
                    compression="zip",
                    # enqueue=True,  # Use a queue for thread-safe logging
                    backtrace=False,  # Show full stack traces for exceptions
                    diagnose=True,  # Show detailed information about variables in stack trace
                )

        self.logger.add(
            self.log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} {message}",
            level=log_level.upper(),
            # enqueue=True,  # Use a queue for thread-safe logging
            backtrace=False,  # Show full stack traces for exceptions
            diagnose=True,  # Show detailed information about variables in stack traces
            mode="w",  # Overwrite the log file if it exists
        )

        self._setup_not_done = False

        self.debug(
            f"Snapshot setup done for script '{self.snapshot_name}' with version '{self.version_name}'"
        )

    def list_tags(self, return_tags: Optional[bool] = False) -> Optional[List[str]]:
        """
        List all tags available in the snapshots.

        Args:
            return_tags (Optional[bool], optional): Whether to return the tags. Defaults to False.

        Raises:
            ValueError: If `return_tags` is not a boolean.

        Returns:
            Optional[List[str]]: List of tags available in the snapshots.
        """
        if not isinstance(return_tags, bool):  # type: ignore
            raise ValueError(
                f"\n\n`return_tags` must be a boolean, but received `{return_tags}` of type `{type(return_tags).__name__}`"
            )

        path = os.path.join("snapshots", self.snapshot_name)
        if not os.path.isdir(path):
            print("No snapshots found.")
            return None

        tags: List[str] = []
        for version_name in os.listdir(path):
            if ":" in version_name:
                tags.append(version_name.split(":")[-1])

        unique_tags = list(set(tags))
        unique_tags = sorted(unique_tags)
        print("Tags available in snapshots:")
        for tag in unique_tags:
            print(f"  - {tag}")

        if return_tags:
            return unique_tags

        return None

    @property
    def exists(self):
        path = os.path.join("snapshots", self.snapshot_name, f"v{self.version}")
        return os.path.isdir(path)

    def checkpoint(self, checkpoint: Any, name: str) -> None:
        """
        Saves the given checkpoint object to a file with the specified name
        within the "checkpoints" directory. If the directory or any necessary subdirectories
        do not exist, they will be created. The method requires PyTorch to be installed.

        Args:
            checkpoint (Any): The checkpoint object to be saved. This is typically a model state dictionary or any other serializable object.
            name (str): The name of the file to save the checkpoint to. If the name contains directory separators, the necessary subdirectories will be created.
        Raises:
            AssertionError: If PyTorch is not installed.

        Example:
            ```python
            model_state = {
                'epoch': 10,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict()
            }
            oc.snapshot.checkpoint(model_state, 'training/epoch_10.pth')
            ```
        """

        assert _has_torch, (
            "\n\nPyTorch is not installed. Please install PyTorch to use this method.\n\n"
        )
        self._get_version()
        path = self._get_version_path("checkpoints")
        os.makedirs(path, exist_ok=True)

        if os.path.sep in name:
            os.makedirs(os.path.join(path, os.path.dirname(name)), exist_ok=True)

        torch.save(checkpoint, os.path.join(path, name))  # type: ignore

    def json(self, data: Union[Dict, List[Any]], name: str) -> None:
        """
        Save a dictionary or list to a JSON file.

        Args:
            data (Dict): The dictionary or list to be saved.
            name (str): The name of the file to save the data to. If the name contains directory separators,
                the necessary directories will be created.
        Raises:
            AssertionError: If the data is not a dictionary or list.
            ValueError: If the data type is not supported.
        """

        self._get_version()
        path = self._get_version_path("jsons")
        os.makedirs(path, exist_ok=True)

        if os.path.sep in name:
            os.makedirs(os.path.join(path, os.path.dirname(name)), exist_ok=True)

        if isinstance(data, dict):
            with open(os.path.join(path, name), "w") as f:
                json.dump(data, f, indent=4)
        elif isinstance(data, list):
            with open(os.path.join(path, name), "w") as f:
                json.dump(data, f, indent=4)
        else:
            raise ValueError(
                f"\n\nUnsupported data type {type(data)}. Only dictionaries and lists are supported.\n"
            )

    def csv(self, df: pd.DataFrame, name: str) -> None:
        """
        Save a pandas DataFrame to a CSV file.
        """
        self._get_version()
        path = self._get_version_path("csvs")
        os.makedirs(path, exist_ok=True)

        if os.path.sep in name:
            os.makedirs(os.path.join(path, os.path.dirname(name)), exist_ok=True)

        df.to_csv(os.path.join(path, name), index=False)

    def figure(self, image: Any, name: str) -> None:
        """
        Save an image to the specified path with the given name.
        This method supports saving images of various types including numpy arrays, PIL images,
        matplotlib figures, and torch tensors. The image is saved in the directory corresponding
        to the current version under a subdirectory named "figures".

        Args:
            image (Any): The image to be saved. Supported types are:
                - numpy.ndarray: The image will be normalized to the range [0, 255] and saved as a PNG file.
                - PIL.Image.Image: The image will be saved directly.
                - matplotlib.figure.Figure: The figure will be saved using the `savefig` method.
                - torch.Tensor: The tensor will be converted to a numpy array, normalized, and saved as a PNG file.
            name (str): The name of the file to save the image as. If the name contains directory separators,
                the necessary directories will be created.
        Raises:
            AssertionError: If Pillow is not installed.
            ValueError: If the image type is not supported.
        """

        self._get_version()
        path = self._get_version_path("figures")
        os.makedirs(path, exist_ok=True)

        if os.path.sep in name:
            os.makedirs(os.path.join(path, os.path.dirname(name)), exist_ok=True)

        if isinstance(image, np.ndarray):
            assert _has_pillow, (
                "\n\nPillow is not installed. Please install Pillow to save a numpy image.\n\n"
            )
            image = image.astype("float32")
            image = (image - image.min()) / np.ptp(image)
            image *= 255.0
            image = image.astype("uint8")
            image = Image.fromarray(image)
            image.save(os.path.join(path, name))
        elif isinstance(image, Image.Image):
            image.save(os.path.join(path, name))
        elif isinstance(image, Figure):
            image.savefig(os.path.join(path, name), dpi=100)  # type: ignore
        else:  # for torch images
            assert isinstance(
                image,
                torch.Tensor,  # type: ignore
            ), (
                f"\n\nUnsupported image type {type(image)}. Only numpy, PIL, matplotlib, and torch tensors are supported.\n"
            )
            image = image.cpu().numpy()
            if image.ndim == 3 and image.shape[0] in [
                1,
                3,
                4,
            ]:  # (3, H, W), (1, H, W) or (4, H, W)
                image = np.transpose(
                    image, (1, 2, 0)
                )  # Convert to (H, W, 3), (H, W, 1) or (H, W, 4)
            image = image.astype("float32")
            image = (image - image.min()) / np.ptp(image)
            image *= 255.0
            image = image.astype("uint8")
            image = Image.fromarray(image)
            image.save(os.path.join(path, name))

    def reset(self, confirm: bool = False) -> None:
        assert os.path.isdir(self._config_dir), (
            "\n\nNot an OpenCrate project directory.\n"
        )

        if not self.snapshot_name:
            self.snapshot_name = self._snapshot_name()

        if not confirm:
            raise ValueError(
                f"\n\nPlease confirm to reset the versioning, add `confirm=True` to the reset method. "
                f"Doing this will delete all `{self.snapshot_name}` snapshots.\n"
            )

        path = os.path.join("snapshots", self.snapshot_name)
        if os.path.isdir(path):
            rmtree(path)

        config = self._read_config()

        if "snapshot_version" in config:
            del config["snapshot_version"]

        self._write_config(config)

    @property
    def path(self):
        if self._setup_not_done:
            self.setup()

        return _PATH(self.version, self.tag, self.snapshot_name)  # type: ignore

    def debug(self, *messages: str):
        if self._setup_not_done:
            self.setup(log_level="DEBUG")

        self.logger.debug(" ".join([str(item) for item in messages]))

    def info(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.info(" ".join([str(item) for item in messages]))

    def warning(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.warning(" ".join([str(item) for item in messages]))

    def error(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.error(" ".join([str(item) for item in messages]))

    def critical(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.critical(" ".join([str(item) for item in messages]))

    def success(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.success(" ".join([str(item) for item in messages]))

    def exception(self, *messages: str):
        if self._setup_not_done:
            self.setup()

        self.logger.exception(" ".join([str(item) for item in messages]))

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            if name.endswith("s"):
                return partial(self._log_asset, snapshot_type=name + "es")
            else:
                return partial(self._log_asset, snapshot_type=name + "s")

    def _snapshot_name(self) -> str:
        if self._name:
            return self._name

        snapshot_name = os.path.basename(sys.argv[0]).split(".")[0]
        if snapshot_name == "ipykernel_launcher":
            raise ValueError(
                "\n\nSnapshot name cannot be determined for jupyter notebook, argument `name` must be passed in the `snapshot.setup` method.\n"
            )
        return snapshot_name

    def _read_config(self):
        if os.path.isdir(self._config_dir):
            config_path = os.path.join(self._config_dir, "config.json")

        with open(config_path, "r") as f:
            return json.load(f)

    def _write_config(self, config: Dict):
        if os.path.isdir(self._config_dir):
            config_path = os.path.join(self._config_dir, "config.json")

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def _get_version(self) -> None:
        if self.version is not None:
            if self.version == "dev":
                return

            config = self._read_config()

            if (
                "snapshot_version" not in config
                or self.snapshot_name not in config["snapshot_version"]
            ):
                if self.start is not None and self.start != "new":
                    raise ValueError(
                        f"\n\nNo snapshots are created for `{self.snapshot_name}`, cannot set `start` to {self.start}.\n"
                    )
                # config["snapshot_version"] = {self.snapshot_name: 0} # check if this line is even being used
            else:
                available_version = config["snapshot_version"][self.snapshot_name]

                if self.version > available_version:
                    raise ValueError(
                        f"\n\nSnapshot of version 'v{self.version}' does not exist, cannot set `start` to {self.version}. "
                        f"Available versions are upto 'v{available_version}'.\n"
                    )

                return

        config = self._read_config()

        if "snapshot_version" not in config:
            config["snapshot_version"] = {self.snapshot_name: 0}
        else:
            if self.snapshot_name not in config["snapshot_version"]:
                config["snapshot_version"][self.snapshot_name] = 0
            else:
                if self.start != "last":
                    config["snapshot_version"][self.snapshot_name] += 1

        self._write_config(config)

        self.version = config["snapshot_version"][self.snapshot_name]

    def _get_version_path(self, snapshot_type: str) -> str:
        # version_name = f"v{self.version}" if self.version != "dev" else self.version

        # if self.tag:
        #     version_name = f"{version_name}:{self.tag}"

        # return os.path.join("snapshots", self.snapshot_name, str(version_name), snapshot_type)

        return os.path.join(
            "snapshots", self.snapshot_name, self.version_name, snapshot_type
        )

    def _log_asset(self, item: Any, name: str, snapshot_type: str) -> None:
        self._get_version()
        path = self._get_version_path(snapshot_type)
        os.makedirs(path, exist_ok=True)

        with open(f"{path}/{name}", "wb") as file:
            file.write(pickle.dumps(item))


class _PATH:
    def __init__(self, version: Union[str, int], tag: str, snapshot_name: str):
        self.version = version
        self.tag = tag
        self.snapshot_name = snapshot_name

    def __getattr__(self, snapshot_type: str):
        def path_func(
            name: Optional[str] = None,
            version: Optional[Union[str, int]] = None,
            tag: Optional[str] = None,
            check_exists: bool = True,
        ) -> str:
            if version is None:
                version = self.version
            if version != "dev":
                version = f"v{version}"
            if tag is not None:
                version = f"{version}:{tag}"
            elif self.tag:
                version = f"{version}:{self.tag}"

            if snapshot_type.endswith("s"):
                asset_type_plural = snapshot_type + "es"
            else:
                asset_type_plural = snapshot_type + "s"

            asset_dir = os.path.join(
                "snapshots", self.snapshot_name, str(version), asset_type_plural
            )

            if name is None:
                return asset_dir

            if check_exists:
                assert os.path.isdir(asset_dir), (
                    f"\n\nNo '{snapshot_type}' snapshot type found for version '{version}'.\n"
                )

            asset_path = os.path.join(asset_dir, name)
            if check_exists:
                assert os.path.exists(asset_path), (
                    f"\n\nNo snapshot '{name}' found in '{snapshot_type}' for version '{version}'.\n"
                )

            return asset_path

        return path_func
