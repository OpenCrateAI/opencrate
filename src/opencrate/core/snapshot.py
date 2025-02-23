import json
import os
import pickle
import sys
from ast import Dict
from functools import partial
from shutil import copyfile, rmtree
from typing import Any, List, Optional, Union

import numpy as np
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
        self.use_version: Union[str, int, None] = None
        self.tag: str = ""
        self.logger = logger
        self.snapshot_name: str = ""
        self._setup_not_done = True
        self._has_reset = False
        self._dev_replaced = True
        self._config_dir: str = ".opencrate"

    def setup(
        self,
        level: str = "INFO",
        log_time: bool = False,
        use_version: Union[int, str] = "new",
        tag: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """
        Setup the logger for snapshot logging.

        Args:
            level (str, optional): Logging level. Defaults to "INFO".
            log_time (bool, optional): Whether to log the time. Defaults to False.
            use_version (Union[int, str], optional): Version to use. Defaults to "new".
            tag (Optional[str], optional): Tag for the snapshot. Defaults to None.

        Raises:
            ValueError: If `level` is not an str or valid logging level.
            ValueError: If `log_time` is not a boolean.
            ValueError: If `tag` is not a string or None.
            ValueError: If `use_version` is not an int, 'new', 'last' or 'dev'.

        Returns:
            None
        """
        assert os.path.isdir(self._config_dir), "\n\nNot an OpenCrate project directory.\n"

        if not isinstance(level, str):  # type: ignore
            raise ValueError(f"\n\n`level` must be a string, but received {type(level)}")
        level = level.upper()
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "SUCCESS"]:
            raise ValueError(
                f"\n\n`level` must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS']"
            )
        if not isinstance(log_time, bool):  # type: ignore
            raise ValueError(f"\n\n`log_time` must be a boolean, but received {type(log_time)}")
        if tag is not None and not isinstance(tag, str):  # type: ignore
            raise ValueError(f"\n\n`tag` must be a string or None, but received {type(tag)}")
        try:
            use_version = int(use_version)
        except:
            pass
        if not isinstance(use_version, (int, str)) or (  # type: ignore
            isinstance(use_version, str) and use_version not in ["new", "last", "dev"]
        ):
            raise ValueError(
                f"\n\n`use_version` must be an int, 'new', or 'last', but received {type(use_version)}"
            )

        self.use_version = use_version
        self.tag = tag if tag else ""

        if isinstance(use_version, int) or use_version == "dev":
            self.version = use_version

        self.snapshot_name = self._snapshot_name(name)
        self._get_version()  # this must be done before setting up the script_dir
        if self.version == "dev":
            version_name = f"{self.version}"
        else:
            version_name = f"v{self.version}"
        if self.tag:
            version_name = f"{version_name}:{self.tag}"
        script_dir = os.path.join("snapshots", self.snapshot_name, version_name)

        self.logger.remove()
        self.logger.add(
            lambda msg: print(msg, end=""),  # Use print instead of sys.stderr.write
            format="<level>{level: <8} </level> {message}",
            level=level,
            colorize=True,
            # enqueue=True,  # Use a queue for thread-safe logging
            backtrace=False,  # Show full stack traces for exceptions
            diagnose=True,  # Show detailed information about variables in stack traces
        )
        self.logger.level("INFO", color="<blue>")

        log_path = os.path.join(script_dir, f"{self.snapshot_name}.log")

        if use_version != "new":
            history_log_path = log_path.replace(
                f"{self.snapshot_name}.log", f"{self.snapshot_name}.history.log"
            )

            if os.path.isfile(log_path):
                if not os.path.isfile(history_log_path):
                    copyfile(log_path, history_log_path)

                self.logger.add(
                    history_log_path,
                    format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} {message}",
                    level=level.upper(),
                    rotation="30 MB",
                    retention="30 days",
                    compression="zip",
                    # enqueue=True,  # Use a queue for thread-safe logging
                    backtrace=False,  # Show full stack traces for exceptions
                    diagnose=True,  # Show detailed information about variables in stack trace
                )

        self.logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} - {level: <8} {message}",
            level=level.upper(),
            # enqueue=True,  # Use a queue for thread-safe logging
            backtrace=False,  # Show full stack traces for exceptions
            diagnose=True,  # Show detailed information about variables in stack traces
            mode="w",  # Overwrite the log file if it exists
        )

        self._setup_not_done = False

        if self._has_reset and use_version == "last":
            self.warning(
                "Latest snapshot is requested to be used, but all snapshots have been reset, so no last version is left to be used. Creating new snapshot as version 'v0'"
            )

        self.debug(f"Snapshot setup done for script '{self.snapshot_name}' with version 'v{self.version}'")

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
            raise ValueError(f"\n\n`return_tags` must be a boolean, but received {type(return_tags)}")

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

    def checkpoint(self, checkpoint: Any, name: str) -> None:
        assert _has_torch, "\n\nPyTorch is not installed. Please install PyTorch to use this method.\n\n"
        self._get_version()
        path = self._get_version_path("checkpoints")
        os.makedirs(path, exist_ok=True)
        torch.save(checkpoint, os.path.join(path, name))  # type: ignore

    def figure(self, image: Any, name: str) -> None:
        self._get_version()
        path = self._get_version_path("figures")
        os.makedirs(path, exist_ok=True)

        if isinstance(image, np.ndarray):
            assert _has_pillow, f"\n\nPillow is not installed. Please install Pillow to save a numpy image.\n\n"
            image = image.astype("float32")
            image = (image - image.min()) / np.ptp(image)
            image *= 255.0
            image = image.astype("uint8")
            image = Image.fromarray(image)
            image.save(os.path.join(path, name))
        elif isinstance(image, Image.Image):
            image.save(os.path.join(path, name))
        elif isinstance(image, Figure):
            image.savefig(os.path.join(path, name))  # type: ignore
        else:  # for torch images
            assert isinstance(
                image, torch.Tensor  # type: ignore
            ), f"\n\nUnsupported image type {type(image)}. Only numpy, PIL, matplotlib, and torch tensors are supported.\n"
            image = image.cpu().numpy()
            if image.ndim == 3 and image.shape[0] in [1, 3, 4]:  # (3, H, W), (1, H, W) or (4, H, W)
                image = np.transpose(image, (1, 2, 0))  # Convert to (H, W, 3), (H, W, 1) or (H, W, 4)
            image = image.astype("float32")
            image = (image - image.min()) / np.ptp(image)
            image *= 255.0
            image = image.astype("uint8")
            image = Image.fromarray(image)
            image.save(os.path.join(path, name))

    def reset(self, confirm: bool = False) -> None:
        assert os.path.isdir(self._config_dir), "\n\nNot an OpenCrate project directory.\n"

        if not self.snapshot_name:
            self.snapshot_name = self._snapshot_name()

        if not confirm:
            raise ValueError(
                f"\n\nPlease confirm to reset the versioning, add `confirm=True` to the reset method. "
                f"Doing this will delete all `{self.snapshot_name}` snapshots.\n"
            )

        path = os.path.join("snapshots", self.snapshot_name)
        if os.path.isdir(path):
            self._has_reset = True
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
            self.setup()

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

    def _snapshot_name(self, argument_snapshot_name: Optional[str] = None) -> str:
        if argument_snapshot_name:
            return argument_snapshot_name

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
            if self.version == "dev":  # finalize this feature for _dev_replaced (how does user handle this)
                #     path = self._get_version_path("dev")[:-4]  # check if this hard coded 5 is correct or not
                #     if os.path.isdir(path):
                #         rmtree(path)
                #     self._dev_replaced = True
                #     return
                # if self._dev_replaced:
                return

            config = self._read_config()

            if "snapshot_version" not in config or self.snapshot_name not in config["snapshot_version"]:
                config["snapshot_version"] = {self.snapshot_name: 0}
                if self.use_version is not None:
                    raise ValueError(
                        f"\n\nNo snapshots are created for `{self.snapshot_name}`, cannot set `use_version` to {self.use_version}.\n"
                    )
            else:
                available_version = config["snapshot_version"][self.snapshot_name]

                if self.version > available_version:
                    raise ValueError(
                        f"\n\nSnapshot of version 'v{self.version}' does not exist, cannot set `use_version` to {self.version}. "
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
                if self.use_version != "last":
                    config["snapshot_version"][self.snapshot_name] += 1

        self._write_config(config)

        self.version = config["snapshot_version"][self.snapshot_name]

    def _get_version_path(self, snapshot_type: str) -> str:
        version_name = f"v{self.version}" if self.version != "dev" else self.version

        if self.tag:
            version_name = f"{version_name}:{self.tag}"

        return os.path.join("snapshots", self.snapshot_name, str(version_name), snapshot_type)

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
        def path_func(name: str, version: Optional[Union[str, int]] = None, tag: Optional[str] = None) -> str:
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

            asset_dir = os.path.join("snapshots", self.snapshot_name, str(version), asset_type_plural)
            assert os.path.isdir(
                asset_dir
            ), f"\n\nNo '{snapshot_type}' snapshot type found for version '{version}'.\n"

            asset_path = os.path.join(asset_dir, name)
            assert os.path.exists(
                asset_path
            ), f"\n\nNo snapshot '{name}' found in '{snapshot_type}' for version '{version}'.\n"

            return asset_path

        return path_func
