import traceback
from datetime import timedelta
from typing import Dict, Iterator, List, Optional, Tuple

import lovelyplots  # noqa: F401
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

plt.style.use(["use_mathtext", "colors10-ls"])


class OpenCrateProgress:
    _snapshot = None

    def __init__(self, total: int, title: str = "", step_start: int = 0):
        self.total = total
        self.title = title
        self.metrics: Dict[str, List[float]] = {}
        self.metrics_accumulated: Dict[str, List[float]] = {}
        self.metrics_column: Dict[str, float] = {}
        self.plot_groups: Optional[List[List[str]]] = None

        # Initialize tqdm progress bar with starting position
        # Use file=None initially to prevent immediate display when step_start > 0
        self.pbar = tqdm(
            total=total,
            initial=step_start,
            desc=title,
            unit="it",
            leave=False,
            ncols=120,
            bar_format="{desc} {percentage:.2f}% |{bar}| {elapsed}, {remaining}, {rate_fmt}{postfix}",
        )
        # Clear any initial display artifacts
        if step_start > 0:
            self.pbar.clear()

    def step(self):
        """Advance the progress bar by one step."""
        if self.pbar is not None:
            self.pbar.update(1)

    def update_description(self, description: str):
        """Update the progress bar description."""
        if self.pbar is not None and self.pbar.desc != description:
            self.pbar.set_description(description, refresh=True)

    def close(self):
        """Close the progress bar."""
        if self.pbar is not None:
            self.pbar.close()
            self.pbar = None

    def monitor(self, **metrics: float):
        # handle plot controls
        groups = metrics.get("plot_groups")
        samples = metrics.get("plot_samples")
        if groups is not None:
            self.plot_groups = groups
            del metrics["plot_groups"]
        elif self.plot_groups is None:
            self.plot_groups = [[k] for k in metrics.keys()]
        if samples is not None:
            self.plot_samples = samples
            del metrics["plot_samples"]
        else:
            self.plot_samples = self.total

        # update live metrics
        self.metrics_column.update(metrics)

        display = {}
        for metric_name, metric_value in metrics.items():
            metric_value = (
                np.mean(metric_value)
                if isinstance(metric_value, (list, tuple, np.ndarray))
                else metric_value
            )
            self.metrics.setdefault(metric_name, []).append(metric_value)
            if len(self.metrics[metric_name]) % self.plot_samples == 0:
                recent = self.metrics[metric_name][-self.plot_samples :]
                avg = sum(recent) / len(recent)
                self.metrics_accumulated.setdefault(metric_name, []).append(avg)
            if isinstance(metric_value, int):
                display[metric_name] = metric_value
            else:
                display[metric_name] = f"{metric_value:.4f}"

        if self.pbar and display:
            self.pbar.set_postfix(display)

    def accumulate_metrics(self):
        if not self.plot_groups:
            return
        for k in self.metrics:
            vals = self.metrics[k][-self.plot_samples :]
            avg = sum(vals) / len(vals)
            self.metrics_accumulated.setdefault(k, []).append(avg)

    def plot_accumulated_metrics(
        self, **title_kwargs
    ) -> Iterator[Tuple[str, plt.Figure]]:
        if not self.plot_groups:
            return
        if title_kwargs:
            x_name, x_val = next(iter(title_kwargs.items()))
            plot_title = f"{x_name.title()}({x_val})"
        else:
            x_name = "Accumulated Iteration"
            plot_title = "Accumulated Metrics"
        for group in self.plot_groups:
            fig = plt.figure(figsize=(12, 6))
            all_vals = []
            for k in group:
                data = self.metrics_accumulated.get(k, [])
                if data:
                    all_vals += data
                    plt.plot(range(1, len(data) + 1), data, label=k)
            if all_vals:
                mn, mx = min(all_vals), max(all_vals)
                rng = mx - mn or 1
                pad = rng * 0.15
                plt.ylim(mn - pad, mx + pad)
            plt.title(f"{plot_title} - {','.join(group)}")
            plt.xlabel(x_name.title())
            plt.ylabel("Value")
            plt.legend()
            yield ",".join(group), fig

    def plot_metrics(self) -> Iterator[Tuple[str, plt.Figure]]:
        if not self.plot_groups:
            return
        for group in self.plot_groups:
            fig = plt.figure(figsize=(12, 6))
            all_vals = []
            for k in group:
                data = self.metrics.get(k, [])
                if data:
                    vals = (
                        np.clip(
                            data,
                            np.percentile(data, 5)
                            - 1.5 * np.subtract(*np.percentile(data, [95, 5])),
                            np.percentile(data, 95)
                            + 1.5 * np.subtract(*np.percentile(data, [95, 5])),
                        )
                        if len(data) > 5
                        else data
                    )
                    all_vals += list(vals)
                    plt.plot(range(len(data)), data, label=k)
            if all_vals:
                mn, mx = min(all_vals), max(all_vals)
                rng = mx - mn or 1
                pad = rng * 0.15
                plt.ylim(mn - pad, mx + pad)
            plt.title(",".join(group))
            plt.xlabel("Iteration")
            plt.ylabel("Value")
            plt.legend()
            yield ",".join(group), fig


def _is_jupyter():
    """
    Checks if the code is running in a Jupyter Notebook.

    Returns:
        bool: True if running in a Jupyter Notebook, False otherwise.
    """
    try:
        # Attempt to get the IPython shell instance.
        shell = get_ipython().__class__.__name__
        # Check if the shell is the specific one used by Jupyter.
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter Notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type of shell
    except NameError:
        return False  # Probably standard Python interpreter


_IS_JUPYTER = _is_jupyter()


def progress(
    iterator: Iterator,
    title: str,
    step: str = "Iter",
    step_start: int = 0,
    total_count: Optional[int] = None,
    job_name: str = "",
) -> Iterator:
    """
    Create a progress bar that automatically advances and supports updating metrics.

    Args:
        iterator: The iterator to track progress for
        title: The title of the progress bar
        step: The name of the step (default: "Iter")
        step_start: The starting index for the step counter
        total_count: Total count if iterator doesn't support len()
    """

    from ... import snapshot

    OpenCrateProgress._snapshot = snapshot

    # Determine total count
    if total_count is not None:
        total = total_count
    else:
        try:
            total = len(iterator)
        except TypeError:
            raise ValueError(
                "Iterator does not support len(). Please provide total_count parameter."
            )

    # Initialize progress bar with proper title and starting position
    desc = f"{title} " if title else ""
    initial_desc = f"{desc}{step}({step_start}/{total})"
    progress_bar = OpenCrateProgress(
        total=total, title=initial_desc, step_start=step_start
    )
    current_idx = step_start

    try:
        for item in iterator:
            yield current_idx, item, progress_bar
            current_idx += 1
            # Only update description after we've moved to the next step
            next_desc = f"{desc}{step}({current_idx}/{total})"
            progress_bar.update_description(next_desc)
            progress_bar.step()
    except Exception as e:
        tb_str = traceback.format_exc()
        snapshot.exception(f"\n{str(e)}\n{tb_str}")
    finally:
        if not _IS_JUPYTER:
            print("\n", end="")  # Ensure a new line after progress bar
        # Save plots if any metrics were tracked
        for title_key, fig in progress_bar.plot_metrics():
            path = f"monitored/{job_name}({title_key})[iterations].jpg"
            plt.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.1)
            snapshot.figure(fig, path)
            plt.close(fig)
        plt.close("all")

        # Log final summary
        elapsed_str = str(
            timedelta(seconds=int(progress_bar.pbar.format_dict["elapsed"]))
        )
        metrics_text = ", ".join(
            f"{k}: {v:.4f}" for k, v in progress_bar.metrics_column.items()
        )

        # Calculate actual percentage based on current progress
        percentage = (current_idx / total) * 100 if total > 0 else 0
        summary = (
            f"{desc}{step}({current_idx}/{total}): {percentage:.2f}%, {elapsed_str}"
        )
        if metrics_text:
            summary += f", {metrics_text}"

        if not snapshot._setup_not_done:
            snapshot.info(summary)
        else:
            print(summary)

        progress_bar.close()
