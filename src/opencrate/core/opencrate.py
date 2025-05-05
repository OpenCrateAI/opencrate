import inspect
import os
import re
import time
from typing import Any, Generator, Optional, Union

import lovelyplots
import matplotlib.pyplot as plt
import torch

from .. import _configuration, config, snapshot, snp
from .utils.progress import CustomProgress, progress

plt.style.use(["use_mathtext", "colors10-ls"])


class CheckpointLoadException(Exception):
    """Base class for custom exceptions in this module."""

    def __init__(self, message="Unable to load checkpoint."):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"\n\nCheckpointException: {self.message}"


class OpenCrate:
    config_eval_timeout: int = 60
    use_config: str = "default"
    start: Optional[Union[str, int]] = None
    tag: Optional[str] = None
    replace: bool = False
    finetune: Optional[str] = None
    finetune_tag: Optional[str] = None
    snapshot: snp.Snapshot = snapshot
    meta_kwargs = {
        "start_epoch": 1,
        "start_batch_idx": 1,
        "is_resuming": False,
        "metrics": {},
        "metrics_accumulated": {},
    }
    meta_saved = False
    registered_checkpoint_configs_list = []

    def _snapshot_reset(self, confirm):
        self.snapshot._name = self.script_name
        return self._original_snapshot_reset(confirm)

    def _snapshot_setup(self, *args, **kwargs):
        if "name" in kwargs:
            del kwargs["name"]

        return self._original_snapshot_setup(*args, **kwargs, name=self.script_name)

    def save_meta(self, **kwargs):
        """
        Sets all the __init__ arguments as attribute to the class instance.
        """

        for key, value in self.meta_kwargs.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)
            self.meta_kwargs[key] = getattr(self, key)

        frame = inspect.currentframe().f_back
        init_kwargs = inspect.getargvalues(frame).locals
        for key, value in init_kwargs.items():
            if key != "self" and key != "__class__":
                setattr(self, key, value)

        if len(kwargs) + len(init_kwargs):
            self.snapshot.debug(f"Initialized meta config for {self.meta_kwargs}")
        else:
            self.snapshot.debug("No meta config initialized.")

        self.meta_saved = True
        # self.current_epoch, self.current_batch_idx,

    def register_checkpoint_config(self, module_name, module, get_params, update_params):
        setattr(self, module_name, module)
        if self.use_config == "custom":
            self.registered_checkpoint_configs_list.append(
                {
                    "module_name": module_name,
                    "custom_config": get_params(module),
                    "update_config_fn": update_params,
                }
            )
            self.snapshot.debug(f"Registered checkpoint config for '{module_name}'")

    def __call__(self):
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        """Finalize configuration"""
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # self.script_name = cls.__module__.split(".")[-1]
            self.script_name = cls.__name__
            self.script_name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", self.script_name)
            self.script_name = re.sub(r"([a-z])([A-Z])", r"\1_\2", self.script_name).lower()

            # Setup snapshot
            _configuration.snapshot = self.snapshot
            self._original_snapshot_reset = self.snapshot.reset
            self._original_snapshot_setup = self.snapshot.setup
            self.snapshot.reset = self._snapshot_reset
            self.snapshot.setup = self._snapshot_setup
            self.snapshot.setup(start=self.start, tag=self.tag, replace=self.replace, log_level=self.log_level)

            # Check if checkpoint exists
            if self.finetune is not None:
                prefix = "Finetuning"
                checkpoint_exists = False
            else:
                checkpoint_exists = os.path.isfile(
                    self.snapshot.path.checkpoint("meta.pth", check_exists=False)
                )
                prefix = "Resuming" if checkpoint_exists else "Creating"
            config_path = f"config/{self.script_name}.yml"

            # Determine if we should use existing config or create default
            use_existing_config = False

            if self.use_config == "custom" and os.path.isfile(config_path):
                # Use custom config file if it exists
                _configuration.read(self.script_name)
                _configuration.write(self.script_name)
                if prefix != "Finetuning":
                    _configuration.display(
                        f"[bold]{prefix}[/bold] [bold]{self.snapshot.version_name}[/bold] with custom config"
                    )
                else:
                    if self.finetune is not None:
                        if self.finetune == "dev":
                            finetune_from_version = f"{self.finetune}"
                        else:
                            finetune_from_version = f"v{self.finetune}"
                        if self.finetune_tag:
                            finetune_from_version = f"{finetune_from_version}:{self.finetune_tag}"

                    _configuration.display(
                        f"[bold]{prefix}[/bold] from [bold]{finetune_from_version}[/bold] to [bold]{self.snapshot.version_name}[/bold] with custom config"
                    )
                use_existing_config = True
            elif self.use_config == "latest" and checkpoint_exists and self.start not in ("reset", "new"):
                # Use latest config from checkpoint
                _configuration.read(self.script_name, load_from_use_version=True)
                _configuration.write(self.script_name, replace_config=True)
                _configuration.display(f"[bold]{prefix} {self.snapshot.version_name}[/bold] with latest config")
                use_existing_config = True

            # Initialize with appropriate config
            _configuration.config_eval_timeout = self.config_eval_timeout
            _configuration.config_eval_start = time.perf_counter()

            decorated_init = config()(original_init)
            decorated_init(self, *args, **kwargs)

            _configuration.opencrate_init_done = True

            # If we didn't use an existing config or if starting new with latest config,
            # write the default config
            if not use_existing_config or (self.start == "new" and self.use_config == "latest"):
                _configuration.write(self.script_name, replace_config=True)
                if self.finetune:
                    if self.finetune is not None:
                        if self.finetune == "dev":
                            finetune_from_version = f"{self.finetune}"
                        else:
                            finetune_from_version = f"v{self.finetune}"
                        if self.finetune_tag:
                            finetune_from_version = f"{finetune_from_version}:{self.finetune_tag}"

                    _configuration.display(
                        f"[bold]{prefix}[/bold] from [bold]{finetune_from_version}[/bold] to [bold]{self.snapshot.version_name}[/bold] with default config"
                    )
                else:
                    config_type = "default"
                    if not use_existing_config and self.use_config == "custom":
                        config_type += f" (as no custom config found at '{config_path}')"
                    _configuration.display(
                        f"[bold]{prefix}[/bold] [bold]{self.snapshot.version_name}[/bold] with {config_type} config"
                    )

            has_save_checkpoint = hasattr(self, "save_checkpoint")
            has_load_checkpoint = hasattr(self, "load_checkpoint")
            if has_save_checkpoint:
                self.save_checkpoint = self._save_checkpoint_decorator(self.save_checkpoint)
            if has_load_checkpoint:
                self.load_checkpoint = self._load_checkpoint_decorator(self.load_checkpoint)

            if not (has_save_checkpoint and has_load_checkpoint):
                self.snapshot.debug(
                    "No `save_checkpoint` and `load_checkpoint` methods found. We highly recommend implementing these methods in your OpenCrate class to enable proper checkpoint management, allowing you to save progress and resume your pipeline from any state."
                )
            elif not has_save_checkpoint:
                self.snapshot.debug(
                    "No `save_checkpoint` method found. We highly recommend implementing this method in your OpenCrate class to enable proper checkpoint management, allowing you to save progress and resume your pipeline from any state."
                )
            elif not has_load_checkpoint:
                self.snapshot.debug(
                    "No `load_checkpoint` method found. We highly recommend implementing this method in your OpenCrate class to enable proper checkpoint management, allowing you to save progress and resume your pipeline from any state."
                )

        cls.__init__ = new_init
        super().__init_subclass__(**kwargs)
        # self.save_meta() # have this here run by default, make it optional from the user side, user will only need to call this if they need to add new meta variables

    def _save_checkpoint_decorator(self, func):
        def wrapper(*args, **kwargs):
            self.snapshot.checkpoint({key: getattr(self, key) for key in self.meta_kwargs}, "meta.pth")

            func(*args, **kwargs)
            self.snapshot.debug(f"Saved all checkpoints successfully")

        return wrapper

    def _load_checkpoint_decorator(self, func):
        def wrapper(*args, **kwargs):
            try:
                if self.finetune is not None:
                    new_version_name = self.snapshot.version_name
                    new_version = self.snapshot.version
                    new_tag = self.snapshot.tag
                    if self.finetune == "dev":
                        self.snapshot.version_name = f"{self.finetune}"
                    else:
                        self.snapshot.version_name = f"v{self.finetune}"
                    if self.finetune_tag:
                        self.snapshot.version_name = f"{self.snapshot.version_name}:{self.finetune_tag}"
                        self.snapshot.tag = self.finetune_tag
                    else:
                        self.snapshot.tag = None

                    self.snapshot.version = self.finetune
                    self.snapshot.debug(
                        f"Loading checkpoint for finetuning from '{self.snapshot.version_name}'"
                    )
                else:
                    meta_path = self.snapshot.path.checkpoint("meta.pth", check_exists=False)
                    # if self.finetune is not None:
                    #     assert os.path.isfile(
                    #         meta_path
                    #     ), f"\n\nUnable to find checkpoint for finetuning at '{meta_path}'\n"
                    if not os.path.isfile(meta_path):
                        self.snapshot.debug(f"Skipping checkpoint loading, '{meta_path}' not found")
                        return
                    # self.snapshot.debug(f"Loading meta variables from '{meta_path}'")
                    try:
                        meta = torch.load(meta_path)
                        new_meta_kwargs = {}
                        for key, value in meta.items():
                            setattr(self, key, value)
                            assert (
                                key in self.meta_kwargs
                            ), f"Failed to load meta variables, `{key}` not found in this checkpoint."
                            new_meta_kwargs[key] = value
                        if not (len(self.meta_kwargs) == len(new_meta_kwargs)):
                            uknown_keys = list(set(self.meta_kwargs.keys()) - set(new_meta_kwargs.keys()))
                            raise AssertionError(
                                f"Failed to load meta variables, '{', '.join(uknown_keys)}' not found in this checkpoint."
                            )
                        self.meta_kwargs = new_meta_kwargs
                        self.snapshot.debug(f"Loaded meta variables from '{meta_path}'")
                    except Exception as e:
                        self.snapshot.exception(f"Failed to load meta variables > {e}")

                func(*args, **kwargs)

                if self.finetune is not None:
                    self.snapshot.version_name = new_version_name
                    self.snapshot.version = new_version
                    self.snapshot.tag = new_tag

                if self.use_config == "custom":
                    for module in self.registered_checkpoint_configs_list:
                        module["update_config_fn"](
                            getattr(self, module["module_name"]),
                            module["custom_config"],
                        )
                        self.snapshot.debug(
                            f"Updated checkpoint config for '{module['module_name']}' to '{module['custom_config']}'"
                        )

                self.snapshot.debug(f"Loaded all checkpoints successfully")
            except Exception as e:
                e = str(e).replace("\n", "")
                raise CheckpointLoadException(f"Failed to load checkpoint. {e}")

        return wrapper

    def epoch_progress(self, title: str = "Epoch"):
        assert hasattr(
            self, "num_epochs"
        ), "`num_epochs` is not defined. Please add it in your OpenCrate class's `__init__` method."
        self.epoch_title = title
        for self.current_epoch in range(self.start_epoch, self.num_epochs):
            yield self.current_epoch

            for fig_title, fig in self._custom_batch_progress.plot_accumulated_metrics(
                **{title: self.current_epoch}
            ):
                # Save epoch-specific version if epoch number is available
                fig_title = fig_title.replace(", ", "_")
                fig_path = f"monitored/{fig_title}[epochs].jpg"
                self.snapshot.figure(fig, fig_path)
                plt.subplots_adjust(left=0.08, right=0.92, top=0.94, bottom=0.06)
                plt.close(fig)
            plt.close("all")

            self.start_epoch += 1  # TODO: consider automating and standardizing some of such common variable names in ML projects

    def batch_progress(self, dataloader, title="Batch"):
        assert self.meta_saved, "Meta variables not saved. Please call `save_meta()` before using this method."

        if self.is_resuming:
            self.start_batch_idx += 1

        metrics_are_not_resumed = True
        has_epoch = hasattr(self, "epoch_title")
        if has_epoch:
            epoch_title = f"{self.epoch_title}({self.current_epoch}/{self.num_epochs})"
        else:
            epoch_title = ""

        for batch_idx, batch, self._custom_batch_progress in progress(
            dataloader,
            title=epoch_title,
            step=title,
            step_start=self.start_batch_idx,
        ):
            if metrics_are_not_resumed:
                for metric_name, metric_values in self.meta_kwargs["metrics"].items():
                    self._custom_batch_progress.metrics[metric_name] = metric_values
                for metric_name, metrics_accumulated_values in self.meta_kwargs["metrics_accumulated"].items():
                    self._custom_batch_progress.metrics_accumulated[metric_name] = metrics_accumulated_values
                metrics_are_not_resumed = False

            # if has_epoch:
            #     self._custom_batch_progress.current_epoch = self.current_epoch
            #     this is not required but check again just to be sure
            self.is_resuming, self.start_batch_idx = True, batch_idx
            yield batch_idx, batch, self._custom_batch_progress
            self.is_resuming, self.start_batch_idx = False, self.start_batch_idx + 1

        if hasattr(self, "_custom_batch_progress"):
            for metric_name, metric_values in self._custom_batch_progress.metrics.items():
                self.meta_kwargs["metrics"][metric_name] = metric_values

            for (
                metric_name,
                metrics_accumulated_values,
            ) in self._custom_batch_progress.metrics_accumulated.items():
                self.meta_kwargs["metrics_accumulated"][metric_name] = metrics_accumulated_values

            self.start_batch_idx = 1

    @classmethod
    def launch(cls, *args, **kwargs):
        from ..cli.environment import launch

        workflow = cls.__module__.split(".")[-1]
        if workflow == "__main__" or "." not in workflow:
            workflow = cls
        if "workflow" in kwargs:
            del kwargs["workflow"]
        return launch(*args, **kwargs, workflow=workflow)

    def __str__(self) -> str:
        cls_name = type(self).__name__

        details = [
            f"version={self.snapshot.version_name}",
            f"tag={self.tag}",
            f"replace={self.replace}",
            f"config={self.use_config}",
            f"finetune={self.finetune}",
            f"finetune_tag={self.finetune_tag}",
        ]

        return f"{cls_name}({', '.join(details)})"

    def __repr__(self) -> str:
        return self.__str__()
