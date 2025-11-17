import time
from functools import lru_cache, wraps
from typing import Any, Callable, List, Optional, Tuple, Type, Union

import numpy as np


def _took(elapsed_time: float) -> str:
    if elapsed_time < 1:
        took = f"{elapsed_time:.4f} secs"
    elif elapsed_time < 60:
        took = f"{elapsed_time:.3f} secs"
    elif elapsed_time < 3600:
        minutes, seconds = divmod(elapsed_time, 60)
        took = f"{int(minutes)} mins {seconds:.3f} secs"
    else:
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        took = f"{int(hours)} hrs {int(minutes)} mins {seconds:.3f} secs"

    return took


def timeit(record: bool = False) -> Callable[[Any], Any]:
    """Measures and logs the execution time of a function.

    This decorator prints the execution time of the decorated function each time it is
    called. If `record` is set to `True`, it also records each execution time and
    provides a `summarize()` method to display summary statistics.

    Args:
        record (bool): If `True`, records execution times for later summary.
            Defaults to `False`.

    Returns:
        Callable[[Any], Any]: The wrapped function with timing capabilities.

    Example:
        Basic usage to time a function call:
        ```python
        @timeit()
        def slow_function():
            time.sleep(1)
            return "Done"

        slow_function()
        ```
        Output:
        ```
        slow_function() executed in 1.002 secs
        ```
        ---
        Record and summarize execution times:
        ```python
        @timeit(record=True)
        def fast_function():
            time.sleep(0.1)

        for _ in range(5):
            fast_function()

        fast_function.summarize()
        ```
        Output:
        ```
        fast_function() executed in 100.23 ms
        fast_function() executed in 100.11 ms
        fast_function() executed in 100.35 ms
        fast_function() executed in 100.18 ms
        fast_function() executed in 100.09 ms
        Total executions  : 5
        Mean time taken   : 100.19 ms
        Median time taken : 100.18 ms
        Min time taken    : 100.09 ms
        Max time taken    : 100.35 ms
        Std deviation     : 0.09 ms
        Total time taken  : 500.96 ms
        ```
        ---
        Attempting to summarize without recording:
        ```python
        @timeit(record=False)
        def another_function():
            pass

        another_function()
        try:
            another_function.summarize()
        except Exception as e:
            print(e)
        ```
        Output:
        ```
        another_function() executed in 0.0001 secs
        Summarize is not enabled, set `record` argument to `True` to enable summary.
        ```
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        times = []

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time

            print(f"{func.__name__}() executed in {_took(elapsed_time)}")

            if record:
                times.append(elapsed_time)

            return result

        def summarize():
            if not record:
                raise Exception("Summarize is not enabled, set `record` argument to `True` to enable summary.")
            acc = np.array(times)
            mean_time = acc.mean()
            median_time = float(np.median(acc))

            print(f"Total executions  : {len(acc)}")
            print(f"Mean time taken   : {_took(mean_time)}")
            print(f"Median time taken : {_took(median_time)}")
            print(f"Min time taken    : {_took(acc.min())}")
            print(f"Max time taken    : {_took(acc.max())}")
            print(f"Std deviation     : {_took(acc.std())}")
            print(f"Total time taken  : {_took(acc.sum())}")

        setattr(wrapper, "summarize", summarize)

        return wrapper

    return decorator


def memoize(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Caches the results of a function to avoid redundant computations.

    This decorator uses a Least Recently Used (LRU) cache to store the results
    of function calls with specific arguments. If the same arguments are provided
    again, the cached result is returned immediately without re-executing the
    function.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable[[Any], Any]: The wrapped function with memoization.

    Example:
        Cache a computationally expensive function:
        ```python
        @memoize
        def fibonacci(n):
            if n < 2:
                return n
            return fibonacci(n - 1) + fibonacci(n - 2)

        # First call computes and caches the result
        start_time = time.time()
        result1 = fibonacci(30)
        duration1 = time.time() - start_time
        print(f"Result: {result1}, Time: {duration1:.4f}s")

        # Second call returns the cached result instantly
        start_time = time.time()
        result2 = fibonacci(30)
        duration2 = time.time() - start_time
        print(f"Result: {result2}, Time: {duration2:.4f}s")
        ```
        Output:
        ```
        Result: 832040, Time: 0.1523s
        Result: 832040, Time: 0.0000s
        ```
    """

    @wraps(func)
    @lru_cache(maxsize=None)
    def wrapper(*args, **kwargs) -> Any:
        return func(*args, **kwargs)

    return wrapper


def retry(max_retries: int = 3, delay: float = 2.0, exceptions: Optional[Union[Type[BaseException], Tuple[Type[BaseException], ...]]] = None) -> Callable[[Any], Any]:
    """Retries a function call a specified number of times on failure.

    This decorator automatically re-executes a function if it raises an exception.
    It can be configured to retry a specific number of times, with a delay between
    attempts, and for specific exception types.

    Args:
        max_retries (int): Maximum number of retry attempts. Defaults to 3.
        delay (float): Delay between retries in seconds. Defaults to 2.0.
        exceptions (Exception or tuple of Exception, optional): An exception or tuple of exceptions to catch. If `None`, it catches all exceptions. Defaults to `None`.

    Returns:
        Callable[[Any], Any]: The wrapped function with retry functionality.

    Raises:
        Exception: If the function fails after all retry attempts.

    Example:
        Successful execution after a few retries:
        ```python
        import random

        @retry(max_retries=5, delay=1)
        def flaky_api_call():
            print("Attempting to call API...")
            if random.random() > 0.7:
                return "Success!"
            raise ConnectionError("Failed to connect")

        flaky_api_call()
        ```
        Output (will vary):
        ```
        Attempting to call API...
        Retrying flaky_api_call()... (1/5)
        Attempting to call API...
        Retrying flaky_api_call()... (2/5)
        Attempting to call API...
        Success!
        ```
        ---
        Failure after all retries:
        ```python
        @retry(max_retries=3, delay=0.5)
        def always_fail():
            print("Executing and failing...")
            raise ValueError("Permanent error")

        try:
            always_fail()
        except Exception as e:
            print(e)
        ```
        Output:
        ```
        Executing and failing...
        Retrying always_fail()... (1/3)
        Executing and failing...
        Retrying always_fail()... (2/3)
        Executing and failing...
        always_fail() failed after 3 retries:
        Permanent error
        ```
        ---
        Retry only for specific exceptions:
        ```python
        @retry(max_retries=3, delay=1, exceptions=ConnectionError)
        def selective_retry():
            # This will not be retried because it's not a ConnectionError
            raise TypeError("This error will not be retried")

        try:
            selective_retry()
        except TypeError as e:
            print(f"Caught expected error: {e}")
        ```
        Output:
        ```
        Caught expected error: This error will not be retried
        ```
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for try_idx in range(max_retries):
                try:
                    if try_idx > 0:
                        print(f"Retrying {func.__name__}()... ({try_idx}/{max_retries})")
                    return func(*args, **kwargs)
                except Exception as e:
                    if exceptions is not None and not isinstance(
                        e,
                        exceptions if isinstance(exceptions, tuple) else (exceptions,),
                    ):
                        raise
                    last_exception = e
                    time.sleep(delay)
            raise Exception(f"{func.__name__}() failed after {max_retries} retries:\n{last_exception}")

        return wrapper

    return decorator


def rate_limit(calls: int, period: float) -> Callable[[Any], Any]:
    """Limits the number of times a function can be called within a time period.

    This decorator restricts the execution frequency of a function. If the number
    of calls exceeds the specified limit within the given period, it raises an
    exception.

    Args:
        calls (int): Maximum number of allowed calls within the time period.
        period (float): The time period in seconds.

    Returns:
        Callable[[Any], Any]: The wrapped function with rate-limiting.

    Raises:
        Exception: If the rate limit is exceeded.

    Example:
        Limit a function to 2 calls every 5 seconds:
        ```python
        @rate_limit(calls=2, period=5)
        def limited_function():
            print("Function called.")

        # First two calls succeed
        limited_function()
        limited_function()

        # Third call fails
        try:
            limited_function()
        except Exception as e:
            print(e)

        # Wait for the period to reset
        time.sleep(5)
        print("Waited 5 seconds...")

        # Call succeeds again
        limited_function()
        ```
        Output:
        ```
        Function called.
        Function called.
        limited_function() rate limit exceeded. Try again in 5.00 seconds
        Waited 5 seconds...
        Function called.
        ```
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        call_history: List[float] = []

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            now = time.time()
            call_history[:] = [t for t in call_history if now - t < period]
            if len(call_history) >= calls:
                wait_time = max(period - (now - call_history[0]), period)
                raise Exception(f"{func.__name__}() rate limit exceeded. Try again in {wait_time:.2f} seconds")
            call_history.append(now)
            return func(*args, **kwargs)

        return wrapper

    return decorator
