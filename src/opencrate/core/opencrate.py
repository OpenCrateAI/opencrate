import inspect
import os
import re
import threading
import time
from copy import deepcopy
from datetime import datetime
from glob import glob
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Type, Union

import lovelyplots  # noqa: F401
import matplotlib.pyplot as plt
import numpy as np
import pynvml
from memory_profiler import profile
from pyinstrument import Profiler
from pyinstrument.renderers import SpeedscopeRenderer
from rich.align import Align
from rich.box import HEAVY, ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import _configuration, config, snapshot, snp
from .utils.progress import progress

_has_torch = True

try:
    import torch
except ImportError:
    _has_torch = False


plt.style.use(["use_mathtext", "colors10-ls"])


class CheckpointLoadException(Exception):
    """Base class for custom exceptions in this module."""

    def __init__(self, message="Unable to load checkpoint.") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}"


def meta_kwargs() -> Dict[str, Any]:
    return {
        "start_epoch": 0,
        "current_epoch": 0,
        "start_batch_idx": 0,
        "is_resuming": False,
        "metrics": {},
        "metrics_accumulated": {},
        "batch_progress": None,
        "epoch_title": None,
        "finished": False,
        "profile": None,
    }


def to_mib(byte_val) -> str:
    return f"{byte_val / 1024**2:.2f} MiB"


class MemoryProfiler:
    """
    A profiler class that measures both CPU (line-by-line) and GPU (before/after)
    memory usage for a given function call without modifying the original function.

    Usage:
        with MemoryProfiler(my_func, log_file='profile.log') as profiler:
            profiler.run(arg1, kwarg1='value')
    """

    def __init__(self, target_function, output_dir, gpu_id=0) -> None:
        self.target_function = target_function
        self.output_dir = output_dir
        self.gpu_id = gpu_id
        self.gpu_handle = None

    def __enter__(self) -> "MemoryProfiler":
        """Setup context: initialize NVML, get GPU handle, open log file."""
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_id)
            # print(
            #     f"GPU Profiling enabled for: {pynvml.nvmlDeviceGetName(self.gpu_handle)}"
            # )
        except pynvml.NVMLError:
            # print(f"Warning: Could not initialize NVML for GPU profiling. {error}")
            self.gpu_handle = None

        # Open the log file in append mode
        self.log_stream = open(os.path.join(self.output_dir, "profile.log"), "a")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Teardown context: shut down NVML and close the log file."""
        if self.gpu_handle:
            pynvml.nvmlShutdown()
        if self.log_stream:
            self.log_stream.close()

    def run(self, *args, **kwargs) -> Any:
        """Profile the target function and write results to the log."""

        # --- GPU Memory: Before Execution ---
        if self.gpu_handle:
            mem_info_before = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            gpu_mem_before = mem_info_before.used

        # --- Log Header ---
        self.log_stream.write(
            f"[==================== System Memory Profiling for {self.target_function.__name__}() ====================]\n"
        )
        # if self.gpu_handle:
        #     self.log_stream.write(f"GPU Memory (Before): {to_mib(gpu_mem_before)}\n")
        # self.log_stream.write(f"{'-' * 80}\n")
        # self.log_stream.write("CPU Memory Profile (line-by-line):\n\n")

        # Create a profiled version of the function that streams to our log file

        profiled_func = profile(self.target_function, stream=self.log_stream)

        # Execute the function
        time_profiler = Profiler()
        time_profiler.start()
        result = profiled_func(*args, **kwargs)
        time_profiler.stop()
        text_output = time_profiler.output_text(color=False).split("\n")[10:]
        text_output = [
            output[9:]
            .replace("|-", "├─")
            .replace("- ", "─ ")
            .replace("|", "│")
            .replace("`─", "└─")
            for output in text_output
            if output.startswith("      ") and "frames hidden" not in output
        ]
        # text_output[0] = text_output[0].replace("└─", "──")
        time_output = "\n".join(text_output)
        self.log_stream.write(
            f"[==================== Time Profiling for {self.target_function.__name__}() ====================]\n"
        )
        self.log_stream.write("\n" + time_output)
        time_profiler.write_html(os.path.join(self.output_dir, "time_profile.html"))
        speedscope_json_string = time_profiler.output(renderer=SpeedscopeRenderer())
        with open(os.path.join(self.output_dir, "time_profile.json"), "w") as f:
            f.write(speedscope_json_string)

        if self.gpu_handle:
            mem_info_after = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            gpu_mem_after = mem_info_after.used
            gpu_mem_increment = float(gpu_mem_after) - float(gpu_mem_before)

            self.log_stream.write(
                f"\n\n\n[==================== GPU Memory Profiling for {self.target_function.__name__}() ====================]\n"
            )
            self.log_stream.write(f"    Memory Before: {to_mib(gpu_mem_before)}\n")
            self.log_stream.write(f"    Memory After:  {to_mib(gpu_mem_after)}\n")
            self.log_stream.write(f"    Increment:     {to_mib(gpu_mem_increment)}\n")

        return result

    def log_benchmarks(self, profile_data) -> None:
        """
        Log the profiling data to the log file.
        :param profile_data: Dictionary containing profiling data.
        """
        self.log_stream.write(
            f"\n\n[==================== Throughput Profiling for {self.target_function.__name__}() ====================]\n"
        )
        for key, values in profile_data.items():
            if values:
                avg_time = sum(values) / len(values)
                median_time = np.median(values)
                std_time = np.std(values)

                throughput_per_sec = 1 / avg_time
                throughput_per_min = throughput_per_sec * 60
                throughput_per_hour = throughput_per_sec * 3600

                def format_time(seconds):
                    """Format seconds into hh:mm:ss format"""
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = seconds % 60
                    return f"{hours:02d} hrs: {minutes:02d} mins: {secs:06.2f} secs"

                self.log_stream.write(f"    {key}:\n")
                self.log_stream.write(
                    f"        Median Time: {format_time(median_time)}\n"
                )
                self.log_stream.write(f"        Avg Time: {format_time(avg_time)}\n")
                self.log_stream.write(f"        Std Dev: {format_time(std_time)}\n")
                self.log_stream.write(
                    f"        Throughput: {throughput_per_sec:.2f}/sec, {throughput_per_min:.2f}/min, {throughput_per_hour:.2f}/hour\n"
                )


class OpenCrate:
    config_eval_timeout: int = 60
    use_config: str = "default"
    start: Optional[Union[str, int]] = None
    tag: Optional[str] = None
    log_level: str = "info"
    replace: bool = False
    finetune: Optional[str] = None
    finetune_tag: Optional[str] = None
    snapshot: snp.Snapshot = snapshot
    script_name: Optional[str] = None
    _original_snapshot_reset: Optional[Callable[..., Any]] = None
    _original_snapshot_setup: Optional[Callable[..., Any]] = None
    _opencrate_subclass_initialized: bool = False
    jobs_meta_kwargs: Dict[str, Dict[str, Any]] = {}
    jobs_dag: Dict[str, Dict[str, Any]] = {}
    meta_saved = False
    registered_checkpoint_configs_list: List[Dict[str, Any]] = []
    available_jobs: List[str] = []

    @classmethod
    def job(
        cls,
        save_on_exception: bool = False,
        execute_once: bool = False,
        upstream_jobs: Optional[List[str]] = None,
        downstream_jobs: Optional[List[str]] = None,
        concurrent: bool = False,
    ) -> Callable[..., Callable[..., None]]:
        _concurrent = concurrent

        def decorator(job_func):
            job_name = job_func.__name__
            cls.jobs_meta_kwargs[job_name] = meta_kwargs()

            # Store DAG metadata
            doc = inspect.cleandoc(job_func.__doc__ or "")
            description_lines = []
            for line in doc.split("\n"):
                if line.strip().startswith(
                    ("Args:", "Arguments:", "Returns:", "Raises:", "Yields:")
                ):
                    break
                description_lines.append(line)

            cls.jobs_dag[job_name] = {
                "doc": "\n".join(description_lines).strip(),
                "upstream": upstream_jobs,
                "downstream": downstream_jobs,
            }

            if job_name not in cls.available_jobs:
                cls.available_jobs.append(job_name)
            else:
                cls.snapshot.error(
                    f"Job {job_name}() is already registered. Please use a unique name for each job."
                )

            def wrapper(
                self,
                upstream_params: Optional[Dict[str, Any]] = None,
                downstream_params: Optional[Dict[str, Any]] = None,
                schedule: str = "",
                schedule_timeout: Optional[str] = "",
                schedule_runout: Optional[int] = None,
                profile: Optional[bool] = False,
                *args,
                **kwargs,
            ):
                # Determine master concurrency setting
                master_concurrent = kwargs.pop("concurrent", _concurrent)

                # Execution sequence handling dependencies
                def execute_job_sequence():
                    save_function_name = f"save_{job_name}"

                    try:
                        # Upstream jobs - force sequential execution
                        if upstream_jobs:
                            for up_job in upstream_jobs:
                                if up_job not in self.available_jobs:
                                    raise ValueError(
                                        f"Upstream job {up_job}() is not registered."
                                    )

                                params = (
                                    upstream_params.get(up_job, {})
                                    if upstream_params
                                    else {}
                                )
                                getattr(self, up_job)(concurrent=False, **params)

                        # Main job execution
                        if (not execute_once) or (
                            not self.jobs_meta_kwargs[job_name]["finished"]
                        ):
                            if profile:
                                self.jobs_meta_kwargs["train"]["profile"] = {
                                    "epoch": [],
                                    "batch": [],
                                }
                                os.makedirs(
                                    os.path.join(self.snapshot.dir_path, "profile"),
                                    exist_ok=True,
                                )
                                with MemoryProfiler(
                                    job_func,
                                    output_dir=os.path.join(
                                        self.snapshot.dir_path,
                                        "profile",
                                    ),
                                ) as profiler:
                                    # Run the profile for a specific workload
                                    # job_func(self, *args, **kwargs)
                                    profiler.run(self, *args, **kwargs)
                                    profiler.log_benchmarks(
                                        self.jobs_meta_kwargs["train"]["profile"]
                                    )
                            else:
                                job_func(self, *args, **kwargs)

                            self.snapshot.info(f"Job {job_name}() has completed!")

                            if execute_once:
                                self.jobs_meta_kwargs[job_name]["finished"] = True
                            else:
                                self.jobs_meta_kwargs[job_name] = meta_kwargs()
                                if profile:
                                    self.jobs_meta_kwargs[job_name]["profile"] = {
                                        "epoch": [],
                                        "batch": [],
                                    }

                            # Save checkpoint if available
                            if hasattr(self, save_function_name):
                                getattr(self, save_function_name)()

                        # Downstream jobs - force sequential execution
                        if downstream_jobs:
                            for down_job in downstream_jobs:
                                if down_job not in self.available_jobs:
                                    raise ValueError(
                                        f"Downstream job {down_job}() is not registered."
                                    )

                                params = (
                                    downstream_params.get(down_job, {})
                                    if downstream_params
                                    else {}
                                )
                                getattr(self, down_job)(concurrent=False, **params)

                    except KeyboardInterrupt:
                        self.snapshot.info("Keyboard Interrupt occurred.")
                        if hasattr(self, save_function_name) and save_on_exception:
                            getattr(self, save_function_name)()
                            self.snapshot.info("Checkpoint saved successfully!")
                    except Exception as e:
                        self.snapshot.exception(e)
                        if hasattr(self, save_function_name) and save_on_exception:
                            getattr(self, save_function_name)()
                            self.snapshot.info("Checkpoint saved successfully!")

                # Scheduling logic with timeout/runout limits
                def run_scheduled_job():
                    # Validate schedule parameters
                    if schedule_timeout is None and schedule_runout is None:
                        raise ValueError(
                            "Scheduled jobs require either `schedule_timeout` or `schedule_runout` parameter"
                        )

                    # Convert timeout to seconds
                    timeout_seconds = None
                    if schedule_timeout:
                        parts = schedule_timeout.split(":")
                        if len(parts) != 3:
                            raise ValueError(
                                "schedule_timeout must be in 'hh:mm:ss' format"
                            )
                        h, m, s = map(int, parts)
                        timeout_seconds = h * 3600 + m * 60 + s

                    try:
                        h_str, m_str, s_str = schedule.split(":")
                        is_continuous = h_str == "*" and m_str == "*" and s_str == "*"

                        if is_continuous:
                            schedule_desc = "immediately after previous run completes"
                        else:
                            schedule_desc = ""
                            if s_str != "*":
                                schedule_desc = f"{s_str} seconds"
                            if m_str != "*":
                                if schedule_desc != "":
                                    schedule_desc = f"{m_str} minutes, {schedule_desc}"
                                else:
                                    schedule_desc = f"{m_str} minutes"
                            if h_str != "*":
                                if schedule_desc != "":
                                    schedule_desc = f"{h_str} hours, {schedule_desc}"
                                else:
                                    schedule_desc = f"{h_str} hours"
                            schedule_desc = f"every {schedule_desc}"

                        self.snapshot.info(f"{job_name}() will run {schedule_desc}.")

                        # Add timeout/runout info
                        if timeout_seconds:
                            self.snapshot.info(
                                f"{job_name}() will timeout after {schedule_timeout}"
                            )
                        if schedule_runout:
                            self.snapshot.info(
                                f"{job_name}() will run at most {schedule_runout} times"
                            )

                        self.snapshot.info("Waiting for schedule trigger...")
                        last_run_time = None
                        run_count = 0
                        start_time = time.time()

                        while True:
                            now = datetime.now()
                            current_time = time.time()

                            # Check termination conditions
                            if (
                                timeout_seconds
                                and (current_time - start_time) > timeout_seconds
                            ):
                                self.snapshot.info(
                                    f"Schedule timeout reached after {schedule_timeout}"
                                )
                                break

                            if schedule_runout and run_count >= schedule_runout:
                                self.snapshot.info(
                                    f"Schedule runout reached after {run_count} executions"
                                )
                                break

                            # For continuous mode, skip time matching logic
                            if not is_continuous:
                                # Prevent duplicate execution in same second
                                if now.strftime("%H:%M:%S") == last_run_time:
                                    time.sleep(0.5)
                                    continue

                                is_match = (
                                    (h_str == "*" or now.hour == int(h_str))
                                    and (m_str == "*" or now.minute == int(m_str))
                                    and (s_str == "*" or now.second == int(s_str))
                                )
                            else:
                                is_match = True  # Always run in continuous mode

                            if is_match:
                                self.snapshot.info("")
                                self.snapshot.info(
                                    f"Executing scheduled {job_name}() at {now.strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                                self.jobs_meta_kwargs[job_name]["finished"] = False

                                execute_job_sequence()
                                run_count += 1
                                last_run_time = now.strftime("%H:%M:%S")

                                # In continuous mode, skip the sleep and go straight to next execution
                                if is_continuous:
                                    continue

                            time.sleep(0.2)  # Check time frequently

                    except KeyboardInterrupt:
                        self.snapshot.info(f"Scheduler for {job_name}() interrupted.")

                # Execution controller
                def run_job():
                    if schedule:
                        run_scheduled_job()
                    else:
                        execute_job_sequence()

                # Master concurrency decision
                if master_concurrent:
                    self.snapshot.info(
                        f"{job_name}() running concurrently in background..."
                    )
                    thread = threading.Thread(target=run_job)
                    thread.daemon = True
                    thread.start()
                else:
                    run_job()

            return wrapper

        return decorator

    def _snapshot_reset(self, confirm) -> Optional[Any]:
        self.snapshot._name = self.script_name
        if self._original_snapshot_reset is not None:
            return self._original_snapshot_reset(confirm)

    def _snapshot_setup(self, *args, **kwargs) -> Optional[Any]:
        if "name" in kwargs:
            del kwargs["name"]

        if self._original_snapshot_setup is not None:
            return self._original_snapshot_setup(*args, **kwargs, name=self.script_name)

    def save_meta(self, **kwargs) -> None:
        """
        Sets all the __init__ arguments as attribute to the class instance.
        """

        # for key, value in self.meta_kwargs.items():
        #     setattr(self, key, value)

        # for key, value in kwargs.items():
        #     setattr(self, key, value)
        #     self.meta_kwargs[key] = getattr(self, key)

        frame = inspect.currentframe().f_back  # type: ignore
        init_kwargs = inspect.getargvalues(frame).locals  # type: ignore
        for key, value in init_kwargs.items():
            if key != "self" and key != "__class__":
                setattr(self, key, value)

        self.snapshot.debug(f"Initialized meta config: {init_kwargs}")
        self.meta_saved = True
        # self.jobs_meta_kwargs["current_epoch"], self.current_batch_idx,

    def register_checkpoint_config(
        self, module_name, module, get_params, update_params
    ) -> None:
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

    def __call__(self):  # -> Any:
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs) -> None:
        """Finalize configuration"""

        if getattr(cls, "_opencrate_subclass_initialized", False):
            super().__init_subclass__(**kwargs)
            return

        cls._opencrate_subclass_initialized = True

        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # self.script_name = cls.__module__.split(".")[-1]
            self.script_name = cls.__name__
            self.script_name = re.sub(
                r"([A-Z]+)([A-Z][a-z])", r"\1_\2", self.script_name
            )
            self.script_name = re.sub(
                r"([a-z])([A-Z])", r"\1_\2", self.script_name
            ).lower()

            # Setup snapshot
            _configuration.snapshot = self.snapshot
            self._original_snapshot_reset = self.snapshot.reset
            self._original_snapshot_setup = self.snapshot.setup
            self.snapshot.reset = self._snapshot_reset
            self.snapshot.setup = self._snapshot_setup
            self.snapshot.setup(
                start=self.start,
                tag=self.tag,
                replace=self.replace,
                log_level=self.log_level,
            )

            # Check if checkpoint exists
            if self.finetune is not None:
                prefix = "Finetuning"
            else:
                meta_list = glob(
                    os.path.join(self.snapshot.path.checkpoint(), "meta_*.json")
                )
                checkpoint_exists = len(meta_list) > 0
                prefix = "Resuming" if checkpoint_exists else "Creating"
            config_path = f"config/{self.script_name}:{self.use_config}.yml"

            # Determine if we should use existing config or create default
            use_existing_config = False
            configs = glob(os.path.join(self.snapshot.dir_path, "*.yml"))

            if self.use_config == "resume":
                if len(configs) == 0:
                    message = "\n\nCannot use `config='resume'` when creating a new snapshot, as there is no existing snapshot to resume."
                    if os.path.exists("config"):
                        available_configs = [
                            os.path.splitext(name)[0].split(":")[-1]
                            for name in os.listdir("config")
                        ]
                        if available_configs:
                            message += f"\nPlease use `config='default'` or one of the available configs: {', '.join(available_configs)}."
                    else:
                        message += "\nPlease use `config='default'` to create an initial configuration."
                    raise AssertionError(message)

                assert len(configs) == 1, (
                    f"\n\nMultiple config files found in the snapshot {self.snapshot.dir_path}.\
                        nThere must be only one config present in the snapshot to get selected for resuming the pipeline.\n"
                )
                config_name = os.path.splitext(os.path.basename(configs[0]))[0]
            else:
                config_name = f"{self.script_name}:{self.use_config}"
            # if self.use_config not in ("default", "resume") and os.path.isfile(
            if self.use_config != "resume" and os.path.isfile(config_path):
                # Use custom config file if it exists
                _configuration.read(config_name)

                _configuration.write(config_name)
                if prefix != "Finetuning":
                    _configuration.display(
                        f"[bold]{prefix}[/bold] [bold]{self.snapshot.version_name}[/bold] with {self.use_config} config"
                    )
                else:
                    if self.finetune is not None:
                        if self.finetune == "dev":
                            finetune_from_version = f"{self.finetune}"
                        else:
                            finetune_from_version = f"v{self.finetune}"
                        if self.finetune_tag:
                            finetune_from_version = (
                                f"{finetune_from_version}:{self.finetune_tag}"
                            )

                    _configuration.display(
                        f"[bold]{prefix}[/bold] from [bold]{finetune_from_version}[/bold] to [bold]{self.snapshot.version_name}[/bold] with custom config"
                    )
                use_existing_config = True
            elif self.use_config == "resume" and self.start not in ("reset", "new"):
                # Use resume config from checkpoint
                _configuration.read(config_name, load_from_use_version=True)
                # _configuration.write(
                #     f"{self.script_name}:{self.use_config}", replace_config=True
                # )

                _configuration.write(config_name)
                _configuration.display(
                    f"[bold]{prefix} {self.snapshot.version_name}[/bold] with resume config"
                )
                use_existing_config = True
            else:
                if os.path.exists("config") and self.use_config != "default":
                    available_config_names = [
                        os.path.splitext(name)[0].split(":")[-1]
                        for name in os.listdir("config")
                    ]
                    if len(available_config_names) == 1:
                        assert self.use_config in available_config_names, (
                            f"\n\nNo config found with name '{self.use_config}'.\nThe only available config in your `config/` folder is '{available_config_names[0]}'.\n"
                        )
                    else:
                        assert self.use_config in available_config_names, (
                            f"\n\nNo config found with name '{self.use_config}'.\nAvailable config names in your `config/` folder are: {', '.join(available_config_names)}.\n"
                        )
                else:
                    assert self.use_config == "default", (
                        f"\n\nNo config found with name '{self.use_config}' as no 'config' folder exists.\nYou must first create a default config by using `config='default'`.\n"
                    )

            # Initialize with appropriate config
            _configuration.config_eval_timeout = self.config_eval_timeout
            _configuration.config_eval_start = time.perf_counter()

            decorated_init = config()(original_init)
            decorated_init(self, *args, **kwargs)

            _configuration.opencrate_init_done = True

            # If we didn't use an existing config or if starting new with resume config,
            # write the default config
            if not use_existing_config or (
                self.start == "new" and self.use_config == "resume"
            ):
                _configuration.write(
                    f"{self.script_name}:{self.use_config}", replace_config=True
                )
                if self.finetune:
                    if self.finetune is not None:
                        if self.finetune == "dev":
                            finetune_from_version = f"{self.finetune}"
                        else:
                            finetune_from_version = f"v{self.finetune}"
                        if self.finetune_tag:
                            finetune_from_version = (
                                f"{finetune_from_version}:{self.finetune_tag}"
                            )

                    _configuration.display(
                        f"[bold]{prefix}[/bold] from [bold]{finetune_from_version}[/bold] to [bold]{self.snapshot.version_name}[/bold] with default config"
                    )
                else:
                    config_type = "default"
                    if not use_existing_config and self.use_config == "custom":
                        config_type += (
                            f" (as no custom config found at '{config_path}')"
                        )
                    _configuration.display(
                        f"[bold]{prefix}[/bold] [bold]{self.snapshot.version_name}[/bold] with {config_type} config"
                    )

            # get list of all methods that start with "save_" prefix
            save_methods_names = [
                method_name
                for method_name in dir(self)
                if method_name.startswith("save_")
            ]
            load_methods_names = [
                method_name
                for method_name in dir(self)
                if method_name.startswith("load_")
            ]

            for save_method_name in save_methods_names:
                setattr(
                    self,
                    save_method_name,
                    self._save_checkpoint_decorator(getattr(self, save_method_name)),
                )

            for load_method_name in load_methods_names:
                setattr(
                    self,
                    load_method_name,
                    self._load_checkpoint_decorator(getattr(self, load_method_name)),
                )

        setattr(cls, "__init__", new_init)
        super().__init_subclass__(**kwargs)
        cls._validate_dag()

    @classmethod
    def _validate_dag(cls) -> None:
        """
        Validates the job dependency graph for recursive call loops.
        Raises RuntimeError if a loop is detected.
        """
        if not cls.jobs_dag:
            return

        # Build call graph: A -> B if job A triggers job B
        adj: dict[str, set[str]] = {job: set() for job in cls.available_jobs}
        for job, dag in cls.jobs_dag.items():
            # A calls its upstream jobs
            for up in dag.get("upstream") or []:
                if up in adj:
                    adj[job].add(up)
            # A calls its downstream jobs
            for down in dag.get("downstream") or []:
                if down in adj:
                    adj[job].add(down)

        visited = set()
        stack = set()
        path = []

        def find_cycle(v):
            visited.add(v)
            stack.add(v)
            path.append(v)

            for neighbor in adj.get(v, []):
                if neighbor in stack:
                    # Found a cycle
                    cycle_start_idx = path.index(neighbor)
                    cycle_path = path[cycle_start_idx:] + [neighbor]
                    arrow_path = " -> ".join(f"{j}()" for j in cycle_path)

                    raise RuntimeError(
                        f"\nInfinite execution loop detected: {arrow_path}.\n"
                        "Check your @pipeline.job decorators. A job cannot trigger another job "
                        "that eventually triggers it back (via upstream or downstream dependencies).\n"
                        "Example: If 'train' has 'evaluate' as downstream, and 'evaluate' has 'train' as upstream, "
                        "they will call each other forever."
                    )
                if neighbor not in visited:
                    if find_cycle(neighbor):
                        return True

            stack.remove(v)
            path.pop()
            return False

        for job in cls.available_jobs:
            if job not in visited:
                find_cycle(job)

    def _save_checkpoint_decorator(self, func) -> Callable[..., None]:
        def wrapper(*args, **kwargs):
            # self.snapshot.checkpoint(
            #     {key: getattr(self, key) for key in self.meta_kwargs}, "meta.json"
            # )

            job_name = func.__name__.replace("save_", "")
            job_ckpt = self.jobs_meta_kwargs[job_name]
            if "batch_progress" in job_ckpt:
                batch_progress = job_ckpt["batch_progress"]
                del job_ckpt["batch_progress"]
                job_ckpt_copy = deepcopy(job_ckpt)
                self.jobs_meta_kwargs[job_name]["batch_progress"] = batch_progress
                self.snapshot.checkpoint(job_ckpt_copy, f"meta_{job_name}.json")
                del job_ckpt_copy
            else:
                self.snapshot.checkpoint(job_ckpt, f"meta_{job_name}.json")
            func(*args, **kwargs)
            self.snapshot.debug("Saved checkpoint successfully!")

            # job_name = func.__name__.replace("save_", "")
            # job_ckpt = deepcopy(self.jobs_meta_kwargs[job_name])
            # del job_ckpt["batch_progress"]  # remove batch progress from checkpoint
            # # del job_ckpt["batch_progress"]  # remove batch progress from checkpoint
            # self.snapshot.checkpoint(job_ckpt, f"meta_{job_name}.json")
            # del job_ckpt
            # func(*args, **kwargs)
            # self.snapshot.debug("Saved checkpoint successfully!")

        return wrapper

    def _load_checkpoint_decorator(self, func) -> Callable[..., Any]:
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
                        self.snapshot.version_name = (
                            f"{self.snapshot.version_name}:{self.finetune_tag}"
                        )
                        self.snapshot.tag = self.finetune_tag
                    else:
                        self.snapshot.tag = None

                    self.snapshot.version = self.finetune
                    self.snapshot.debug(
                        f"Loading checkpoint for finetuning from '{self.snapshot.version_name}'"
                    )
                else:
                    job_name = func.__name__.replace("load_", "")
                    meta_path = self.snapshot.path.checkpoint(
                        f"meta_{job_name}.json", check_exists=False
                    )
                    # if self.finetune is not None:
                    #     assert os.path.isfile(
                    #         meta_path
                    #     ), f"\n\nUnable to find checkpoint for finetuning at '{meta_path}'\n"
                    if not os.path.isfile(meta_path):
                        self.snapshot.debug(
                            f"Skipping checkpoint loading, '{meta_path}' not found"
                        )
                        return  # handle this return better, right now it just skips the job if the meta file is not found
                    # self.snapshot.debug(f"Loading meta variables from '{meta_path}'")
                    try:
                        assert _has_torch, (
                            "\n\nPyTorch is not installed. Please install PyTorch to load a checkpoint.\n\n"
                        )
                        loaded_job_meta_kwargs = torch.load(
                            meta_path, weights_only=False
                        )
                        # new_meta_kwargs = {}
                        # for key, value in meta.items():
                        #     setattr(self, key, value)
                        #     assert key in self.jobs_meta_kwargs[job_name], (
                        #         f"Failed to load meta variables, `{key}` not found in this checkpoint."
                        #     )
                        #     new_meta_kwargs[key] = value
                        # if not (
                        #     len(self.jobs_meta_kwargs[job_name]) == len(new_meta_kwargs)
                        # ):
                        #     unknown_keys = list(
                        #         set(self.jobs_meta_kwargs[job_name].keys())
                        #         - set(new_meta_kwargs.keys())
                        #     )
                        #     raise AssertionError(
                        #         f"Failed to load meta variables, '{', '.join(unknown_keys)}' not found in this checkpoint."
                        #     )
                        self.jobs_meta_kwargs[job_name] = loaded_job_meta_kwargs
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

                self.snapshot.debug("Loaded checkpoint successfully!")
            except Exception as e:
                msg = str(e).replace("\n", "")
                raise CheckpointLoadException(f"Failed to load checkpoint. {msg}")

        return wrapper

    def epoch_progress(
        self, num_epochs, title: str = "Epoch"
    ) -> Generator[Any, Any, None]:
        job_name = inspect.stack()[1].function

        assert self.meta_saved, (
            "Meta variables not saved. Please call `save_meta()` in `__init__` method."
        )

        self.jobs_meta_kwargs[job_name]["epoch_title"] = title
        self.num_epochs = num_epochs

        do_profile = self.jobs_meta_kwargs[job_name]["profile"] is not None

        for self.jobs_meta_kwargs[job_name]["current_epoch"] in range(
            self.jobs_meta_kwargs[job_name]["start_epoch"], self.num_epochs
        ):
            if do_profile:
                start_time = time.perf_counter()

            yield self.jobs_meta_kwargs[job_name]["current_epoch"]

            if do_profile:
                self.jobs_meta_kwargs[job_name]["profile"]["epoch"].append(
                    time.perf_counter() - start_time
                )

            for fig_title, fig in self.jobs_meta_kwargs[job_name][
                "batch_progress"
            ].plot_accumulated_metrics(
                epoch=f"{self.jobs_meta_kwargs[job_name]['current_epoch'] + 1}"
            ):
                # Save epoch-specific version if epoch number is available
                fig_title = fig_title.replace(", ", "_")
                fig_path = f"monitored/{job_name}({fig_title})[epochs].jpg"
                self.snapshot.figure(fig, fig_path)
                plt.subplots_adjust(left=0.08, right=0.92, top=0.94, bottom=0.06)
                plt.close(fig)
            plt.close("all")
            self.jobs_meta_kwargs[job_name]["start_epoch"] += 1
        # TODO: consider automating and standardizing some of such common variable names in ML projects

    def batch_progress(
        self, dataloader, title="Batch"
    ) -> Generator[Tuple[Any, Any, Any], Any, None]:
        job_name = inspect.stack()[1].function

        assert self.meta_saved, (
            "Meta variables not saved. Please call `save_meta()` in `__init__` method."
        )

        if self.jobs_meta_kwargs[job_name]["is_resuming"]:
            self.jobs_meta_kwargs[job_name]["start_batch_idx"] += 1

        metrics_are_not_resumed = True
        if self.jobs_meta_kwargs[job_name]["epoch_title"] is not None:
            epoch_title = f"{self.jobs_meta_kwargs[job_name]['epoch_title']}({self.jobs_meta_kwargs[job_name]['current_epoch'] + 1}/{self.num_epochs})"
        else:
            epoch_title = ""

        do_profile = self.jobs_meta_kwargs[job_name]["profile"] is not None

        for batch_idx, batch, self.jobs_meta_kwargs[job_name][
            "batch_progress"
        ] in progress(
            dataloader,
            title=epoch_title,
            step=title,
            step_start=self.jobs_meta_kwargs[job_name]["start_batch_idx"],
            job_name=job_name,
        ):
            if metrics_are_not_resumed:
                for metric_name, metric_values in self.jobs_meta_kwargs[job_name][
                    "metrics"
                ].items():
                    self.jobs_meta_kwargs[job_name]["batch_progress"].metrics[
                        metric_name
                    ] = metric_values
                for metric_name, metrics_accumulated_values in self.jobs_meta_kwargs[
                    job_name
                ]["metrics_accumulated"].items():
                    self.jobs_meta_kwargs[job_name][
                        "batch_progress"
                    ].metrics_accumulated[metric_name] = metrics_accumulated_values
                metrics_are_not_resumed = False

            (
                self.jobs_meta_kwargs[job_name]["is_resuming"],
                self.jobs_meta_kwargs[job_name]["start_batch_idx"],
            ) = (
                True,
                batch_idx,
            )
            if do_profile:
                start_time = time.perf_counter()

            yield batch_idx, batch, self.jobs_meta_kwargs[job_name]["batch_progress"]

            if do_profile:
                self.jobs_meta_kwargs[job_name]["profile"]["batch"].append(
                    time.perf_counter() - start_time
                )
            (
                self.jobs_meta_kwargs[job_name]["is_resuming"],
                self.jobs_meta_kwargs[job_name]["start_batch_idx"],
            ) = (
                False,
                self.jobs_meta_kwargs[job_name]["start_batch_idx"] + 1,
            )

        # if hasattr(self, "_custom_batch_progress"):
        if self.jobs_meta_kwargs[job_name]["batch_progress"] is not None:
            for (
                metric_name,
                metric_values,
            ) in self.jobs_meta_kwargs[job_name]["batch_progress"].metrics.items():
                self.jobs_meta_kwargs[job_name]["metrics"][metric_name] = metric_values

            for (
                metric_name,
                metrics_accumulated_values,
            ) in self.jobs_meta_kwargs[job_name][
                "batch_progress"
            ].metrics_accumulated.items():
                self.jobs_meta_kwargs[job_name]["metrics_accumulated"][metric_name] = (
                    metrics_accumulated_values
                )

                self.jobs_meta_kwargs[job_name]["start_batch_idx"] = 0

    @classmethod
    def inspect(cls) -> None:
        console = Console()

        # 1. Listing all the jobs in a rich table
        job_list_table = Table(
            title="[bold]Available Jobs[/bold]", box=HEAVY, expand=False
        )
        job_list_table.add_column("Job Name", style="bold cyan", no_wrap=True)
        job_list_table.add_column("Description", style="dim")

        for job_name in cls.available_jobs:
            doc = cls.jobs_dag.get(job_name, {}).get("doc", "")
            job_list_table.add_row(job_name, doc)

        console.print(job_list_table)
        # console.print("") # Removed to reduce gap

        # 2. Group jobs by their dependency signature
        # We store them as a list of dicts for easier indexing

        groups: List[Dict[str, Any]] = []
        for job_name in cls.available_jobs:
            dag = cls.jobs_dag.get(job_name, {})
            upstream: Set[str] = set(dag.get("upstream") or [])
            downstream: Set[str] = set(dag.get("downstream") or [])

            # Find existing group or create new one
            found = False
            for group in groups:
                # group["jobs"] is always a list by our construction below
                if (
                    isinstance(group.get("upstream"), set)
                    and isinstance(group.get("downstream"), set)
                    and group["upstream"] == upstream
                    and group["downstream"] == downstream
                ):
                    jobs_list: List[str] = group["jobs"]
                    jobs_list.append(job_name)
                    found = True
                    break
            if not found:
                groups.append(
                    {"jobs": [job_name], "upstream": upstream, "downstream": downstream}
                )

        # 3. Build meta-graph between groups and calculate levels
        # A group G1 is a parent of G2 if G2 depends on G1
        adj: Dict[int, Set[int]] = {i: set() for i in range(len(groups))}
        in_degree = dict.fromkeys(range(len(groups)), 0)

        for i, g1 in enumerate(groups):
            for j, g2 in enumerate(groups):
                if i == j:
                    continue

                # G1 -> G2 if G2's upstream has jobs from G1
                is_parent = False
                if any(job in g2["upstream"] for job in g1["jobs"]):
                    is_parent = True
                # G1 -> G2 if G1's downstream has jobs from G2
                elif any(job in g1["downstream"] for job in g2["jobs"]):
                    is_parent = True

                if is_parent:
                    if j not in adj[i]:
                        adj[i].add(j)
                        in_degree[j] += 1

        # Calculate levels using Kahn's style BFS
        levels = {}  # group_idx -> level
        queue = [i for i, d in in_degree.items() if d == 0]
        current_level = 0

        while queue:
            next_queue = []
            for node in queue:
                levels[node] = current_level
                # If this group has NO dependencies at all, we might want to distinguish it?
                # User said Row 1 is for parents.
                # Standalone jobs (no UP/DOWN) already listed in table, usually skipped by previous logic.
                for neighbor in adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue
            current_level += 1

        # 4. Prepare Panel for each group
        prepared_panels = {}  # group_idx -> Panel
        for i, group in enumerate(groups):
            # Skip standalone jobs (no dependencies)
            if not group["upstream"] and not group["downstream"]:
                continue

            parts = []
            # 1. Upstream
            if group["upstream"]:
                up_grid = Table.grid(padding=(0, 0))
                for job in sorted(group["upstream"]):
                    up_grid.add_row(f"[dim]{job}[/dim]")
                parts.append(
                    Align.center(
                        Panel(up_grid, border_style="dim", box=ROUNDED, expand=False)
                    )
                )
                parts.append(Align.center(Text("↓", style="bold")))

            # 2. Jobs
            job_grid = Table.grid(padding=(0, 0))
            for job in sorted(group["jobs"]):
                job_grid.add_row(Text(f"{job}", style="bold"))
            parts.append(Align.center(job_grid))

            # 3. Downstream
            if group["downstream"]:
                parts.append(Align.center(Text("↓", style="bold")))
                down_grid = Table.grid(padding=(0, 0))
                for job in sorted(group["downstream"]):
                    down_grid.add_row(f"[dim]{job}[/dim]")
                parts.append(
                    Align.center(
                        Panel(down_grid, border_style="dim", box=ROUNDED, expand=False)
                    )
                )

            title_name = ", ".join(sorted(group["jobs"]))
            panel = Panel(
                Group(*parts),
                title=f"[bold]{title_name}[/bold]",
                box=ROUNDED,
                expand=False,
            )
            prepared_panels[i] = panel

        # 5. Render rows by level
        max_level = max(levels.values()) if levels else -1
        for level_idx in range(max_level + 1):
            level_group_indices = [
                i
                for i, level_val in levels.items()
                if level_val == level_idx and i in prepared_panels
            ]
            if not level_group_indices:
                continue

            # Sub-divide into rows of 5
            for row_start in range(0, len(level_group_indices), 5):
                row_indices = level_group_indices[row_start : row_start + 5]
                row_panels = [prepared_panels[i] for i in row_indices]

                grid = Table.grid(padding=(1, 2))
                for _ in range(len(row_panels)):
                    grid.add_column()
                grid.add_row(*row_panels)
                console.print(grid)

            # Spacer between different levels if desired?
            # console.print("")

    @classmethod
    def launch(cls, *args, **kwargs) -> Any:
        from ..cli.environment import launch

        workflow: Union[str, Type[OpenCrate]] = cls.__module__.split(".")[-1]
        if isinstance(workflow, str) and (
            workflow == "__main__" or "." not in workflow
        ):
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
        return "{}(\n    {},\n)".format(cls_name, ",\n    ".join(details))

    def __repr__(self) -> str:
        return self.__str__()
