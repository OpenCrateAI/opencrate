import time
from functools import cache, wraps
from typing import Any, Callable


def timeit(func: Callable) -> Callable:
    """
    Decorator to measure and log the execution time of a function.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function with timing functionality.

    Example:
    >>> @timeit
    ... def slow_function():
    ...     time.sleep(2)
    ...     return "Done"
    >>> slow_function()
    `slow_function()` executed in 00:00:02
    'Done'
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time

        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        took = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        print(f"`{func.__name__}()` executed in {took}")
        return result

    return wrapper


def memoize(func: Callable) -> Callable:
    """
    Decorator to cache the results of a function to avoid redundant computations.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function with memoization functionality.

    Example:
    >>> @memoize
    ... def compute_fibonacci(n):
    ...     if n < 2:
    ...         return n
    ...     return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)
    >>> compute_fibonacci(10)  # Computes and caches the results
    55
    >>> compute_fibonacci(10)  # Returns the cached result
    55
    """

    @wraps(func)
    @cache
    def wrapper(*args, **kwargs) -> Any:
        return func(*args, **kwargs)

    return wrapper


def retry(max_retries: int = 3, delay: float = 2.0) -> Callable:
    """
    Decorator to retry a function call a specified number of times on failure.

    Args:
        max_retries (int): Maximum number of retry attempts. Default is 3.
        delay (float): Delay between retries in seconds. Default is 2.0.

    Returns:
        Callable: The wrapped function with retry functionality.

    Raises:
        Exception: If the function fails after all retry attempts.

    Example:
    >>> @retry(max_retries=5, delay=1)
    ... def api_call():
    ...     response = requests.get("https://www.example.com")
    ...     response.raise_for_status()
    ...     return response.json()
    >>> try:
    ...     print(api_call())
    ... except Exception as e:
    ...     print(e)
    `api_call()` failed after 5 retries
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
                    last_exception = e
                    time.sleep(delay)
            raise Exception(f"`{func.__name__}()` failed after {max_retries} retries:\n{last_exception}")

        return wrapper

    return decorator


def rate_limit(calls: int, period: float) -> Callable:
    """
    Decorator to limit the number of times a function can be called within a time period.

    Args:
        calls (int): Maximum number of allowed calls within the time period.
        period (float): Time period in seconds.

    Returns:
        Callable: The wrapped function with rate-limiting functionality.

    Raises:
        Exception: If the rate limit is exceeded.

    Example:
    >>> @rate_limit(calls=5, period=10)
    ... def api_call():
    ...     response = requests.get("https://www.example.com")
    ...     return response.json()
    >>> for _ in range(5):
    ...     print(api_call())
    >>> print(api_call())
    `api_call()` rate limit exceeded. Try again in 5.00 seconds...
    """

    def decorator(func: Callable) -> Callable:
        call_history = []

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            now = time.time()
            call_history[:] = [t for t in call_history if now - t < period]
            if len(call_history) >= calls:
                wait_time = max(period - (now - call_history[0]), period)
                raise Exception(f"{func.__name__}`() rate limit exceeded. Try again in {wait_time:.2f} seconds")
            call_history.append(now)
            return func(*args, **kwargs)

        return wrapper

    return decorator
