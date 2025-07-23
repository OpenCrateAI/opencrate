from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
from typing import Any, Callable, List, Optional

from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.text import Text


class AverageIterationPerSecond(ProgressColumn):
    """Renders human-readable processing rate."""

    speeds: List[float] = []

    def render(self, task) -> Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            # return Text("[... avg it/s]", style="blue")
            return Text("[... avg it/s]")

        self.speeds.append(speed)
        if len(self.speeds) > 20:
            self.speeds.pop(0)
        avg_speed = sum(self.speeds) / len(self.speeds)
        # return Text(f"[{avg_speed:.0f} avg it/s]", style="blue")
        return Text(f"[{avg_speed:.0f} avg it/s]")


class AverageSecondPerIteration(ProgressColumn):
    """Renders human-readable processing rate."""

    speeds: List[float] = []

    def render(self, task) -> Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            # return Text("[... avg s/it]", style="blue")
            return Text("[... avg s/it]")

        self.speeds.append(speed)
        if len(self.speeds) > 20:
            self.speeds.pop(0)
        avg_speed = sum(self.speeds) / len(self.speeds)
        return Text(f"[{1 / avg_speed:.2f} avg s/it]", style="blue")


def _is_iterable(obj):
    return isinstance(obj, list) or isinstance(obj, tuple)


def _make_args_list_iterable(args_list: List[Any]):
    if not _is_iterable(args_list[0]):
        for i, args in enumerate(args_list):
            if not _is_iterable(args):
                args_list[i] = (args,)
    return args_list


def parallelize_with_threads(
    func: Callable[[Any], Any],
    args_list: List[Any],
    max_workers: Optional[int] = None,
    title: str = "Parallelizing with threads",
) -> List[Any]:
    """
    Executes a function in parallel using multithreading.

    Args:
        func (Callable): The function to execute in parallel.
        args_list (List[Any]): A list of argument tuples to pass to the function.
        max_workers (Optional[int]): Maximum number of threads to use. If None, it defaults to the number of CPUs.
        title (Optional[str]): The title to display in the progress bar.

    Returns:
        List[Any]: A list of results from the function calls.

    Example:
        >>> import requests
        >>> def io_bound_task(url):
        ...     response = requests.get(url)
        ...     return response.status_code
        >>> results = parallelize_with_threads(
        ...     io_bound_task, ["https://www.example.com"] * 20, max_workers=5, title="Downloading Files"
        ... )
        Downloading Files ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 [217 avg it/s] [0.00 avg s/it]
        >>> print(results) # the order of results may vary
        [200, 200, 200, ..., 200]
    """

    results: List[Any] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(func, *args) for args in _make_args_list_iterable(args_list)
        ]
        progress = Progress(
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(complete_style="magenta", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            AverageIterationPerSecond(),
            AverageSecondPerIteration(),
        )
        with progress:
            task = progress.add_task(f"[cyan]{title}", total=len(futures))
            for future in as_completed(futures):
                results.append(future.result())
                progress.update(task, advance=1)
                progress.refresh()
    return results


def parallelize_with_processes(
    func: Callable[[Any], Any],
    args_list: List[Any],
    max_workers: Optional[int] = None,
    title: str = "Parallelizing with processes",
) -> List[Any]:
    """
    Executes a function in parallel using multiprocessing. Best for tasks with varying execution times where order is not important.

    Args:
        func (Callable): The function to execute in parallel.
        args_list (List[Any]): A list of argument tuples to pass to the function.
        max_workers (Optional[int]): Maximum number of processes to use. If None, it defaults to the number of CPUs.
        title (Optional[str]): The title to display in the progress bar.

    Returns:
        List[Any]: A list of results from the function calls.

    Example:
        >>> from math import factorial
        >>> def cpu_bound_task(n):
        ...     return factorial(n)
        >>> numbers = [1000 + i for i in range(20)]
        >>> results = parallelize_with_processes(cpu_bound_task, numbers, title="Computing factorials")
        Computing factorials ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 [681 avg it/s] [0.00 avg s/it]
        >>> print(results) # the order of results may vary
        [factorial(100000), factorial(100001), ..., factorial(100019)]
    """

    results: List[Any] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(func, *args) for args in _make_args_list_iterable(args_list)
        ]
        progress = Progress(
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(complete_style="magenta", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            AverageIterationPerSecond(),
            AverageSecondPerIteration(),
        )
        with progress:
            task = progress.add_task(f"[cyan]{title}", total=len(futures))
            for future in as_completed(futures):
                results.append(future.result())
                progress.update(task, advance=1)
                progress.refresh()
    return results


def parallize_with_batch_processes(
    func: Callable[[Any], Any],
    data: List[Any],
    batch_size: Optional[int] = None,
    title: Optional[str] = None,
) -> List[Any]:
    """
    Processes data in batches using multiprocessing. Best for tasks with uniform execution times where the order of results is important.

    Args:
        func (Callable): The function to execute on each item in the data.
        data (List[Any]): A list of data items to process.
        batch_size (Optional[int]): Number of processes to use. If None, it defaults to the number of CPUs.
        title (Optional[str]): The title to display in the progress bar.

    Returns:
        List[Any]: A list of results from processing the data.

    Example:
        >>> def square(x):
        ...     return x ** 2
        >>> results = parallize_with_batch_processes(square, [1, 2, 3, 4], title="Computing squares")
        Computing squares ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 [684 avg it/s] [0.00 avg s/it]
        >>> print(results) # the order of results is preserved
        [1, 4, 9, 16]
    """

    if batch_size is None:
        batch_size = max(cpu_count() - 4, 2)

    results: List[Any] = []
    with Pool(batch_size) as pool:
        progress = Progress(
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(complete_style="magenta", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            AverageIterationPerSecond(),
            AverageSecondPerIteration(),
        )
        with progress:
            task = progress.add_task(
                f"[cyan]{title if title else 'Batch processing'}", total=len(data)
            )
            for result in pool.imap(func, data):
                results.append(result)
                progress.update(task, advance=1)
                progress.refresh()
    return results
