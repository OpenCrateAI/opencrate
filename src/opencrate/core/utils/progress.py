import os
import re
from datetime import timedelta
from typing import Dict, Iterator, List, Optional

import lovelyplots
import matplotlib.pyplot as plt
import numpy as np
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from .io.gif import dir_to_gif

plt.style.use(["use_mathtext", "colors10-ls"])
# plt.style.use("seaborn-v0_8-darkgrid")
# plt.style.use("dark_background")


class AverageProgressSpeed(ProgressColumn):
    """Renders human-readable processing rate (seconds per iteration)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speeds: List[float] = []

    def render(self, task) -> Text:
        speed = task.finished_speed or task.speed
        if speed is None or speed == 0:
            return Text("... s/it ... it/s")
        self.speeds.append(speed)
        if len(self.speeds) > 20:
            self.speeds.pop(0)
        avg_speed = sum(self.speeds) / len(self.speeds)
        return Text(f"{1/avg_speed:.2f} s/it {avg_speed:.2f} it/s")


class MetricsColumn(ProgressColumn):
    """Renders live metrics like g_loss and d_loss."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics: Dict[str, float] = {}

    def update_metrics(self, **metrics: float):
        """Update the metrics to be displayed."""
        self.metrics.update(metrics)

    def render(self, task) -> Text:
        if not self.metrics:
            return Text("")
        metrics_text = ", ".join(
            [
                f"[bold blue]{key}[/bold blue]: [bold grey]{value:.4f}[/bold grey]"
                for key, value in self.metrics.items()
            ]
        )
        return Text.from_markup(metrics_text)


class CustomProgress(Progress):
    _snapshot = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics_column = MetricsColumn()
        self.metrics = {}
        self.metrics_accumulated = {}
        self.monitor_idx = 0
        self.columns = list(self.columns) + [self.metrics_column]

    def monitor(self, **metrics: float):
        """Update the metrics displayed in the progress bar."""
        self.monitor_idx += 1

        self.plot_groups = metrics.get("plot_groups", None)
        self.plot_samples = metrics.get("plot_samples", 10)

        if "plot_groups" in metrics:
            del metrics["plot_groups"]
        if "plot_samples" in metrics:
            del metrics["plot_samples"]

        self.metrics_column.update_metrics(**metrics)

        if self.plot_groups:
            for group in self.plot_groups:
                missing_metrics = [metric for metric in group if metric not in metrics]
                if missing_metrics:
                    raise ValueError(
                        f"\n\nThe following metrics are missing from the provided metrics names: {', '.join(missing_metrics)}. "
                        f"Allowed metrics names are {list(metrics.keys())}.\n"
                    )

        if self.monitor_idx % (self.total_idx // self.plot_samples) == 0:
            for metric_name, metric_value in metrics.items():
                if metric_name not in self.metrics:
                    self.metrics[metric_name] = {"raw": []}
                self.metrics[metric_name]["raw"].append(metric_value)

    def accumulate_metrics(self):
        """Accumulate metrics for the entire training run."""
        if not hasattr(self, "plot_groups") or not self.plot_groups:
            return

        for metric_name in self.metrics:
            if metric_name not in self.metrics_accumulated:
                self.metrics_accumulated[metric_name] = {
                    "raw": [],
                }
            values = self.metrics[metric_name]["raw"][-self.plot_samples :]
            accumulated_metric_value = sum(values) / len(values)

            self.metrics_accumulated[metric_name]["raw"].append(accumulated_metric_value)

    def plot_accumulated_metrics(self, **title_kwargs):
        """Plot the accumulated metrics using seaborn and save the figure."""
        if not hasattr(self, "plot_groups") or not self.plot_groups:
            return

        if len(title_kwargs):
            for x_axis_name in title_kwargs:
                break
            plot_title = f"{x_axis_name.title()}({title_kwargs[x_axis_name]})"
        else:
            x_axis_name = "Accumulated Iteration"
            plot_title = "Accumulated Metrics"

        for metric_group in self.plot_groups:
            fig = plt.figure(figsize=(12, 6))
            title = "x"
            all_values = []

            for metric_name in metric_group:
                if metric_name in self.metrics_accumulated:
                    title += f", {metric_name}"
                    values = self.metrics_accumulated[metric_name]["raw"]

                    all_values.extend(values)
                    plt.plot(range(len(values)), values, label=metric_name)

            if all_values:
                y_min, y_max = min(all_values), max(all_values)
                y_range = y_max - y_min
                padding = y_range * 0.15
                ylim_top = y_max + padding
                ylim_bottom = y_min - padding

                if y_min >= 0 and ylim_bottom < 0 and y_min < y_range * 0.3:
                    ylim_bottom = 0

                if y_max <= 0 and ylim_top > 0 and abs(y_max) < y_range * 0.3:
                    ylim_top = 0

            if title != "x":
                title = title.replace("x, ", "")
                plt.grid(True, linestyle="--", alpha=0.8)
                plt.title(f"{plot_title} - {title}", fontsize=12)
                plt.xlabel(x_axis_name, fontsize=10)
                plt.ylabel("Value", fontsize=10)
                plt.legend(fontsize=10)

                if all_values:
                    # Ensure top and bottom are different to avoid singular transformation
                    if abs(ylim_top - ylim_bottom) < 1e-10:
                        ylim_top += 0.1
                        ylim_bottom -= 0.1
                    plt.ylim(top=ylim_top, bottom=ylim_bottom)

                plt.tick_params(axis="both", which="major", labelsize=10)

                yield title, fig

    def plot_metrics(self):
        """Plot the metrics using seaborn and save the figure."""
        if not hasattr(self, "plot_groups") or not self.plot_groups:
            return

        for group_index, metric_group in enumerate(self.plot_groups):
            fig = plt.figure(figsize=(12, 6))
            title = "x"
            all_values = []  # Collect all values to determine optimal y limits

            # First pass - collect all values and create the plots
            for metric_name in metric_group:
                if metric_name in self.metrics:
                    title += f", {metric_name}"
                    values = self.metrics[metric_name]["raw"]

                    # Clip outliers - only if we have enough data points
                    if len(values) > 5:
                        q1, q3 = np.percentile(values, [5, 95])
                        iqr = q3 - q1
                        upper_bound = q3 + 1.5 * iqr
                        lower_bound = q1 - 1.5 * iqr
                        clipped_values = np.clip(values, lower_bound, upper_bound)
                    else:
                        clipped_values = values

                    all_values.extend(clipped_values)
                    plt.plot(range(len(values)), values, label=metric_name)

            # Set appropriate y-axis limits
            if all_values:
                y_min, y_max = min(all_values), max(all_values)

                # Add padding (10% on top/bottom, but more if needed for readability)
                y_range = y_max - y_min
                if y_range < 1e-6:  # Avoid division by zero or very small ranges
                    y_range = abs(y_min) * 0.1 if y_min != 0 else 0.1

                padding = y_range * 0.15  # 15% padding

                # Ensure we don't create negative padding when values are near zero
                ylim_top = y_max + padding
                ylim_bottom = y_min - padding

                # Special handling for values near zero
                if y_min >= 0 and ylim_bottom < 0 and y_min < y_range * 0.3:
                    ylim_bottom = 0  # Don't go below zero if data is close to zero

                # If values are all negative, make sure top limit doesn't cross zero
                if y_max <= 0 and ylim_top > 0 and abs(y_max) < y_range * 0.3:
                    ylim_top = 0

            if title != "x":
                title = title.replace("x, ", "")
                plt.grid(True, linestyle="--", alpha=0.8)
                plt.title(title, fontsize=12)
                plt.xlabel("Iteration", fontsize=10)
                plt.ylabel("Value", fontsize=10)
                plt.legend(fontsize=10)

                if all_values:
                    plt.ylim(top=ylim_top, bottom=ylim_bottom)

                plt.tick_params(axis="both", which="major", labelsize=10)

                yield title, fig


def progress(
    iterator: Iterator,
    title: str,
    step: str = "Iter",
    step_start: int = 0,
) -> Iterator:
    """
    Create a progress bar that automatically advances and supports updating metrics.

    Args:
        iterator: The iterator to track progress for
        title: The title of the progress bar
        step: The name of the step (default: "Iter")
        step_start: The starting index for the step counter
    """

    from ..opencrate import snapshot

    CustomProgress._snapshot = snapshot

    with CustomProgress(
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        SpinnerColumn(spinner_name="point", style="grey"),
        BarColumn(complete_style="yellow", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        AverageProgressSpeed(),
    ) as progress_bar:
        total = len(iterator)
        task_id = progress_bar.add_task(title, total=total)  # type: ignore - TODO: write logic if iterator has no len method
        progress_bar.total_idx = total
        # Calculate initial completed percentage
        if step_start > 0:
            progress_bar.start_task(task_id)
            progress_bar.advance(task_id, advance=step_start)
            progress_bar.update(
                task_id, description=f"{title} [bold cyan]{step}({step_start}/{total})[/bold cyan]"
            )
        try:
            for iter_idx, item in enumerate(iterator, step_start):
                progress_bar.advance(task_id)
                progress_bar.update(
                    task_id, description=f"{title} [bold cyan]{step}({iter_idx}/{total})[/bold cyan]"
                )
                progress_bar.refresh()
                yield iter_idx, item, progress_bar
        finally:
            progress_bar.accumulate_metrics()
            # Store metrics info before removing the progress bar
            progress_snapshot = progress_bar.tasks[task_id]
            speed = progress_snapshot.speed

            # Hide the progress bar by completing the task (which will make it disappear)
            progress_bar.update(task_id, visible=False)
            progress_bar.refresh()

            # Plot and save the metrics at the end of each iteration
            for fig_title, fig in progress_bar.plot_metrics():
                # Save epoch-specific version if epoch number is available
                fig_title = fig_title.replace(", ", "_")
                fig_path = f"monitored/{fig_title}[iterations].jpg"
                plt.subplots_adjust(left=0.08, right=0.92, top=0.9, bottom=0.1)
                snapshot.figure(fig, fig_path)

                plt.close(fig)
            plt.close("all")

            completed = ((iter_idx) / total) * 100
            # Log the final state of the progress bar and metrics
            elapsed_time = progress_snapshot.elapsed
            elapsed_time = str(timedelta(seconds=max(0, int(elapsed_time))))

            metrics = progress_bar.metrics_column.render(progress_snapshot)
            if len(str(metrics)):
                metrics = f"- {metrics}"

            if speed:
                snapshot.info(
                    f"{title} {step}({iter_idx}/{total}) - {completed:.2f}% - {elapsed_time} - {speed:.2f} it/s {(1/speed):.2f} s/it {metrics}"
                )
            else:
                if len(metrics):
                    snapshot.info(
                        f"{title} {step}({iter_idx}/{total}) - {completed:.2f}% - {elapsed_time} {metrics}"
                    )
                else:
                    snapshot.info(f"{title} {step}({iter_idx}/{total}) - {completed:.2f}% - {elapsed_time}")

            # Stop and remove the progress bar
            progress_bar.stop()
