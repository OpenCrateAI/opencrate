from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
from typing import Any, Callable, List, Optional

from .progress import progress


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
    order_results: bool = False,
) -> List[Any]:
    """Executes a function in parallel using a thread pool.

    This function is ideal for I/O-bound tasks, such as making network requests
    or reading from a disk, where threads can perform work while waiting for
    external resources.

    Args:
        func (Callable[[Any], Any]): The function to execute in parallel.
        args_list (List[Any]): A list of arguments to be passed to the function.
            Each element can be a single value or a tuple of arguments.
        max_workers (Optional[int]): The maximum number of threads to use.
            If `None`, it defaults to the number of CPUs. Defaults to `None`.
        title (str): A title for the progress bar.
            Defaults to "Parallelizing with threads".
        order_results (bool): If `True`, results are returned in the same
            order as the input arguments. This may be slower if tasks have
            varying completion times. Defaults to `False`.

    Returns:
        List[Any]: A list of results from the function calls.

    Example:
        Perform multiple network requests in parallel:
        ```python
        import requests

        def download_url(url):
            try:
                return requests.get(url).status_code
            except requests.RequestException:
                return None

        urls = ["https://www.google.com", "https://www.github.com"] * 5
        results = parallelize_with_threads(download_url, urls, max_workers=5)
        print(f"Received {len(results)} results: {results}")
        ```
        Output:
        ```
        Parallelizing with threads ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01 [5 avg it/s] [0.18 avg s/it]
        Received 10 results: [200, 200, 200, 200, 200, 200, 200, 200, 200, 200]
        ```
        ---
        Process tasks with ordered results:
        ```python
        def process_data(item, duration):
            time.sleep(duration)
            return item * 2

        args = [(1, 0.3), (2, 0.1), (3, 0.2)]
        ordered_results = parallelize_with_threads(
            process_data, args, order_results=True
        )
        print(f"Ordered results: {ordered_results}")
        ```
        Output:
        ```
        Ordered results: [2, 4, 6]
        ```
    """

    results: List[Any] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in _make_args_list_iterable(args_list)]

        num_tasks = len(futures)

        if order_results:
            for idx, future in enumerate(futures):
                results.append(future.result())
        else:
            for idx, future, prog_bar in progress(as_completed(futures), title, "Task", total_count=num_tasks):
                results.append(future.result())

    return results


def parallelize_with_processes(
    func: Callable[[Any], Any],
    args_list: List[Any],
    max_workers: Optional[int] = None,
    title: str = "Parallelizing with processes",
    order_results: bool = False,
) -> List[Any]:
    """Executes a function in parallel using a process pool.

    This function is best for CPU-bound tasks that can be executed independently,
    as it leverages multiple CPU cores to perform computations simultaneously.

    Args:
        func (Callable[[Any], Any]): The function to execute in parallel.
        args_list (List[Any]): A list of arguments for the function. Each
            element can be a single value or a tuple of arguments.
        max_workers (Optional[int]): The maximum number of processes to use.
            If `None`, it defaults to the number of CPUs. Defaults to `None`.
        title (str): A title for the progress bar.
            Defaults to "Parallelizing with processes".
        order_results (bool): If `True`, results are returned in the same
            order as the input arguments. Defaults to `False`.

    Returns:
        List[Any]: A list of results from the function calls.

    Example:
        Perform CPU-intensive calculations in parallel:
        ```python
        def compute_square(n):
            return n * n

        numbers = list(range(10))
        results = parallelize_with_processes(compute_square, numbers)
        print(f"Results (order may vary): {results}")
        ```
        Output:
        ```
        Parallelizing with processes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 [15 avg it/s] [0.07 avg s/it]
        Results (order may vary): [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
        ```
        ---
        Process tasks with multiple arguments and ordered results:
        ```python
        def add(x, y):
            return x + y

        args = [(1, 2), (3, 4), (5, 6)]
        ordered_results = parallelize_with_processes(add, args, order_results=True)
        print(f"Ordered results: {ordered_results}")
        ```
        Output:
        ```
        Ordered results: [3, 7, 11]
        ```
    """

    results: List[Any] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in _make_args_list_iterable(args_list)]

        num_tasks = len(futures)

        if order_results:
            for future in futures:
                results.append(future.result())
        else:
            for idx, future, prog_bar in progress(as_completed(futures), title, "Task", total_count=num_tasks):
                results.append(future.result())

    return results


def parallize_with_batch_processes(
    func: Callable[[Any], Any],
    data: List[Any],
    batch_size: Optional[int] = None,
    title: Optional[str] = None,
) -> List[Any]:
    """Processes data in batches using a pool of worker processes.

    This function is efficient for applying a function to a large dataset, as it
    distributes the data in batches to worker processes. It preserves the order
    of the results.

    Args:
        func (Callable[[Any], Any]): The function to apply to each data item.
        data (List[Any]): The list of data items to process.
        batch_size (Optional[int]): The number of processes to use. If `None`,
            it defaults to a value based on the number of CPUs. Defaults to `None`.
        title (Optional[str]): A title for the progress bar.
            Defaults to "Batch processing".

    Returns:
        List[Any]: A list of results in the same order as the input data.

    Example:
        Process a list of numbers in batches:
        ```python
        def process_item(x):
            return x * 10

        dataset = list(range(20))
        results = parallize_with_batch_processes(
            process_item, dataset, batch_size=4
        )
        print(f"Processed results: {results}")
        ```
        Output:
        ```
        Batch processing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 [180 avg it/s] [0.01 avg s/it]
        Processed results: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
        ```
    """

    if batch_size is None:
        batch_size = max(cpu_count() - 4, 2)

    results: List[Any] = []
    with Pool(batch_size) as pool:
        # Use the progress function to track processed items
        progress_title = title if title else "Batch processing"
        for idx, result, prog_bar in progress(pool.imap(func, data), progress_title, "Item", total_count=len(data)):
            results.append(result)

    return results
