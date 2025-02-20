import time

import pytest

from opencrate.core.utils.decorate import memoize, rate_limit, retry, timeit


class TestDecorateFunctions:
    def test_timeit(self):
        @timeit
        def slow_function():
            time.sleep(1)
            return "Done"

        result = slow_function()
        assert result == "Done"

    def test_memoize(self):
        call_count = 0

        @memoize
        def compute_fibonacci(n):
            nonlocal call_count
            call_count += 1
            if n < 2:
                return n
            return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)

        assert compute_fibonacci(10) == 55
        assert call_count == 11  # Only 11 unique calls should be made

    def test_retry_success(self):
        call_count = 0

        @retry(max_retries=3, delay=1)
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "Success"

        result = sometimes_fails()
        assert result == "Success"
        assert call_count == 3

    def test_retry_failure(self):
        @retry(max_retries=3, delay=1)
        def always_fails():
            raise ValueError("This will always fail")

        with pytest.raises(
            Exception, match=r"`always_fails\(\)` failed after 3 retries:\nThis will always fail"
        ):
            always_fails()

    def test_rate_limit(self):
        @rate_limit(calls=2, period=5)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        with pytest.raises(Exception, match=r"rate limit exceeded"):
            limited_function()

    def test_rate_limit_wait(self):
        @rate_limit(calls=2, period=2)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        time.sleep(2)
        assert limited_function() == "Success"
