import json
import os
import sys
import time
from functools import partial
from glob import glob
from shutil import copyfile, rmtree
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from .utils import io

_has_torch = True


class Snapshot:
    def __init__(self):
        self.version: Union[str, int, None] = None
        self.start: Union[str, int, None] = None
        self.tag: Optional[str] = None
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
        assert os.path.isdir(self._config_dir), "\n\nNot an OpenCrate project directory.\n"

        if not isinstance(log_level, str):
            raise ValueError(f"\n\n`log_level` must be a string, but received {type(log_level)}")
        log_level = log_level.upper()
        if log_level not in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "SUCCESS",
        ]:
            raise ValueError("\n\n`log_level` must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS']")
        if not isinstance(log_time, bool):
            raise ValueError(f"\n\n`log_time` must be a boolean, but received {type(log_time)}")
        if tag is not None and not isinstance(tag, str):
            raise ValueError(f"\n\n`tag` must be a string or None, but received {type(tag)}")
        try:
            start = int(start)
        except:  # noqa: E722
            pass
        if not isinstance(start, (int, str)) or (isinstance(start, str) and start not in ["new", "last", "dev"]):
            raise ValueError(f"\n\n`start` must be an int, 'new', 'last' or 'dev', but received {type(start)}")

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
            self.history_log_path = self.log_path.replace(f"{self.snapshot_name}.log", f"{self.snapshot_name}.history.log")

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

        self.debug(f"Snapshot setup done for script '{self.snapshot_name}' with version '{self.version_name}'")

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
        if not isinstance(return_tags, bool):
            raise ValueError(f"\n\n`return_tags` must be a boolean, but received `{return_tags}` of type `{type(return_tags).__name__}`")

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

    def reset(self, confirm: bool = False) -> None:
        assert os.path.isdir(self._config_dir), "\n\nNot an OpenCrate project directory.\n"

        if not self.snapshot_name:
            self.snapshot_name = self._snapshot_name()

        if not confirm:
            raise ValueError(f"\n\nPlease confirm to reset the versioning, add `confirm=True` to the reset method. Doing this will delete all `{self.snapshot_name}` snapshots.\n")

        path = os.path.join("snapshots", self.snapshot_name)
        if os.path.isdir(path):
            rmtree(path)

        config = self._read_config()

        if "snapshot_version" in config:
            del config["snapshot_version"]

        self._write_config(config)

    def _check_setup(self):
        if self._setup_not_done:
            raise RuntimeError("\n\nSnapshot setup is not done yet, please perform the setup with `oc.snapshot.setup()` before accessing the snapshot.\n")

    @property
    def path(self):
        self._check_setup()

        return _PATH(self.version, self.tag, self.snapshot_name)  # type: ignore

    def debug(self, *messages: str):
        self._check_setup()

        self.logger.debug(" ".join([str(item) for item in messages]))

    def info(self, *messages: str):
        self._check_setup()

        self.logger.info(" ".join([str(item) for item in messages]))

    def warning(self, *messages: str):
        self._check_setup()

        self.logger.warning(" ".join([str(item) for item in messages]))

    def error(self, *messages: str):
        self._check_setup()

        self.logger.error(" ".join([str(item) for item in messages]))

    def critical(self, *messages: str):
        self._check_setup()

        self.logger.critical(" ".join([str(item) for item in messages]))

    def success(self, *messages: str):
        self._check_setup()

        self.logger.success(" ".join([str(item) for item in messages]))

    def exception(self, *messages: str):
        self._check_setup()

        self.logger.exception(" ".join([str(item) for item in messages]))

    # def __getattribute__(self, name: str) -> Any:
    #     try:
    #         return super().__getattribute__(name)
    #     except AttributeError:
    #         if name.endswith("s"):
    #             return partial(self._log_asset, snapshot_type=name + "es")
    #         else:
    #             return partial(self._log_asset, snapshot_type=name + "s")

    # def _log_asset(self, item: Any, name: str, snapshot_type: str) -> None:
    #     self._get_version()
    #     path = self._get_version_path(snapshot_type)
    #     os.makedirs(path, exist_ok=True)

    #     with open(f"{path}/{name}", "wb") as file:
    #         file.write(pickle.dumps(item))

    # oc.snapshot.json("data.json").save(data)
    # oc.snapshot.json("data.json").load()

    def __getattribute__(self, attr_name: str) -> Any:
        try:
            return super().__getattribute__(attr_name)
        except AttributeError:
            return partial(self._log_asset, snapshot_type=attr_name)

    def _log_asset(self, name: str, snapshot_type: str, handler=None, verbose=False) -> Any:
        handlers = {
            "json": io.json,
            "csv": io.csv,
            "image": io.image,
            "video": io.video,
            "audio": io.audio,
            "text": io.text,
            "yaml": io.yaml,
            "checkpoint": io.checkpoint,
        }

        if snapshot_type in handlers.keys():
            if snapshot_type.endswith("s"):
                snapshot_dir_name = snapshot_type + "es"
            else:
                snapshot_dir_name = snapshot_type + "s"
        else:
            snapshot_dir_name = snapshot_type

        _path = os.path.join(self._get_version_path(snapshot_dir_name), name)
        if os.path.splitext(_path)[1] == "":
            os.makedirs(_path, exist_ok=True)

        self._get_version()

        class _Artifact:
            def __init__(
                self,
                outer_instance,
                snapshot_type,
                name,
                handler,
                verbose,
            ):
                self.outer_instance = outer_instance
                self.path = _path
                self.verbose = verbose
                self.name = name
                self.snapshot_type = snapshot_type

                self.actor = handlers.get(snapshot_type)
                if self.actor is None:
                    if handler is not None:
                        if not (hasattr(handler, "save") and hasattr(handler, "load")):
                            raise ValueError("\n\n`handler` must be a class with `save` and `load` methods.\n")
                        # Instantiate the custom handler, passing it the artifact instance
                        custom_handler = handler()
                        custom_handler.path = self.path
                        custom_handler.verbose = self.verbose
                        custom_handler.name = self.name
                        custom_handler.snapshot_type = self.snapshot_type
                        self.actor = custom_handler

                    else:
                        raise ValueError(f"\n\nNo built-in artifact handler for type '{snapshot_type}', please provide a `handler`.\n")

            def __getattr__(self, name):
                if name not in [
                    "save",
                    "load",
                    "delete",
                    "backup",
                    "list_backups",
                    "exists",
                    "__str__",
                    "__repr__",
                ]:
                    return getattr(self.actor, name)
                return getattr(self, name)

            @property
            def exists(self):
                return os.path.exists(self.path)

            def save(self, artifact, *args, **kwargs):
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                if self.actor is not None:
                    self.actor.save(artifact, self.path, *args, **kwargs)
                if self.verbose:
                    self.outer_instance.info(f"✓ '{self.name}' of '{self.snapshot_type}' saved successfully at '{self.path}'.")

            def load(self, *args, **kwargs):
                if self.actor is not None:
                    loaded_artifact = self.actor.load(self.path, *args, **kwargs)
                else:
                    loaded_artifact = None
                if self.verbose:
                    self.outer_instance.info(f"✓ '{self.name}' of '{self.snapshot_type}' loaded successfully from '{self.path}'.")
                return loaded_artifact

            def delete(self, confirm: bool = False) -> None:
                """Delete the artifact file from the snapshot.

                Args:
                    confirm (bool): Must be True to actually delete the file

                Raises:
                    ValueError: If confirm is not True
                """
                if not os.path.exists(self.path):
                    if self.verbose:
                        self.outer_instance.info(f"✗ '{self.name}' of '{self.snapshot_type}' does not exist at '{self.path}'.")
                    return

                if not confirm:
                    raise ValueError(f"\n\nPlease confirm deletion by setting confirm=True. This will permanently delete '{self.name}'.\n")

                os.remove(self.path)
                if self.verbose:
                    self.outer_instance.info(f"✓ '{self.name}' of '{self.snapshot_type}' deleted successfully.")

            def backup(self, tag: Optional[str] = None) -> Optional[str]:
                """
                Create a backup of the artifact file by appending a timestamp to its name.
                """
                if not os.path.exists(self.path):
                    if self.verbose:
                        self.outer_instance.info(f"✗ '{self.name}' of '{self.snapshot_type}' does not exist at '{self.path}', cannot create backup.")
                    return None

                path_name, ext = os.path.splitext(self.path)

                if tag is None:
                    timestamp = time.strftime("%H:%M:%S_%d-%b-%Y")
                    backup_path = f"{path_name}.backup_{timestamp}{ext}"
                else:
                    backup_path = f"{path_name}.backup_{tag}{ext}"

                copyfile(self.path, backup_path)
                if self.verbose:
                    self.outer_instance.info(f"✓ Backup of '{self.name}' of '{self.snapshot_type}' created at '{backup_path}'.")
                return backup_path
                if self.verbose:
                    self.outer_instance.info(f"✓ Backup of '{self.name}' of '{self.snapshot_type}' created at '{backup_path}'.")
                return backup_path

            def list_backups(self) -> List[str]:
                backup_paths = glob(f"{os.path.splitext(self.path)[0]}.backup_*")
                return [os.path.basename(path) for path in backup_paths]

            def __str__(self):
                if os.path.exists(self.path):
                    stat = os.stat(self.path)
                    size_bytes = stat.st_size

                    # Format size nicely
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    elif size_bytes < 1024 * 1024 * 1024:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

                    last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

                    return f"Artifact: {self.name}\nType: {self.snapshot_type}\nPath: {os.path.abspath(self.path)}\nSize: {size_str}\nLast modified: {last_modified}"
                else:
                    return f"Artifact {self.name} is not created yet at path: {os.path.abspath(self.path)}"

            def __repr__(self):
                return self.__str__()

        return _Artifact(self, snapshot_type, name, handler, verbose)

    def _snapshot_name(self) -> str:
        if self._name:
            return self._name

        snapshot_name = os.path.basename(sys.argv[0]).split(".")[0]
        if snapshot_name == "ipykernel_launcher":
            raise ValueError("\n\nSnapshot name cannot be determined for jupyter notebook, argument `name` must be passed in the `snapshot.setup` method.\n")
        return snapshot_name

    def _read_config(self):
        if os.path.isdir(self._config_dir):
            config_path = os.path.join(self._config_dir, "config.json")

        with open(config_path) as f:
            return json.load(f)

    def _write_config(self, config: Dict[Any, Any]):
        if os.path.isdir(self._config_dir):
            config_path = os.path.join(self._config_dir, "config.json")

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def _get_version(self) -> None:
        if self.version is not None:
            if self.version == "dev":
                return

            config = self._read_config()

            if "snapshot_version" not in config or self.snapshot_name not in config["snapshot_version"]:
                if self.start is not None and self.start != "new":
                    raise ValueError(f"\n\nNo snapshots are created for `{self.snapshot_name}`, cannot set `start` to {self.start}.\n")
                # config["snapshot_version"] = {self.snapshot_name: 0} # check if this line is even being used
            else:
                available_version = config["snapshot_version"][self.snapshot_name]

                if self.version > available_version:
                    raise ValueError(
                        f"\n\nSnapshot of version 'v{self.version}' does not exist, cannot set `start` to {self.version}. Available versions are upto 'v{available_version}'.\n"
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
        self._check_setup()
        return os.path.join("snapshots", self.snapshot_name, self.version_name, snapshot_type)


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
            check_exists: bool = False,
            ensure_dir: bool = False,
        ) -> str:
            if version is None:
                version = self.version
            if version != "dev":
                version = f"v{version}"
            if tag is not None:
                version = f"{version}:{tag}"
            elif self.tag:
                version = f"{version}:{self.tag}"

            # Match the logic from _log_asset
            handlers = {"json", "csv", "image", "video", "audio", "text", "yaml", "checkpoint"}

            if snapshot_type in handlers:
                if snapshot_type.endswith("s"):
                    snapshot_dir_name = snapshot_type + "es"
                else:
                    snapshot_dir_name = snapshot_type + "s"
            else:
                snapshot_dir_name = snapshot_type

            asset_dir = os.path.join("snapshots", self.snapshot_name, str(version), snapshot_dir_name)

            if name is None:
                return asset_dir

            if check_exists:
                assert os.path.isdir(asset_dir), f"\n\nNo '{snapshot_type}' snapshot type found for version '{version}'.\n"

            asset_path = os.path.join(asset_dir, name)
            if check_exists:
                assert os.path.exists(asset_path), f"\n\nNo snapshot '{name}' found in '{snapshot_type}' for version '{version}'.\n"

            if ensure_dir:
                os.makedirs(asset_dir, exist_ok=True)

            return asset_path

        return path_func
