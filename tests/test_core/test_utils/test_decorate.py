import time

import pytest

from opencrate import decorate


class TestUtilsDecorate:
    def test_timeit_with_record(self, capsys):
        """Test timeit decorator with recording enabled."""

        @decorate.timeit(record=True)
        def slow_function():
            time.sleep(1)

        slow_function()
        slow_function()
        slow_function.summarize()
        captured = capsys.readouterr()
        assert "slow_function() executed in" in captured.out
        assert "Total executions  : 2" in captured.out
        assert "Mean time taken   :" in captured.out
        assert "Median time taken :" in captured.out

    def test_timeit_without_record(self, capsys):
        """Test timeit decorator without recording."""

        @decorate.timeit(record=False)
        def fast_function():
            time.sleep(0.1)

        fast_function()
        captured = capsys.readouterr()
        assert "fast_function() executed in" in captured.out

    def test_timeit_without_record_summarize(self):
        """Test that summarize raises exception when record=False."""

        @decorate.timeit(record=False)
        def slow_function():
            time.sleep(1)

        slow_function()
        with pytest.raises(Exception, match=r"Summarize is not enabled, set `record` argument to `True` to enable summary."):
            slow_function.summarize()

    def test_memoize(self, capsys):
        """Test memoize decorator caches function results."""
        call_count = 0

        @decorate.memoize
        def compute_fibonacci(n):
            nonlocal call_count
            call_count += 1
            if n < 2:
                return n
            return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)

        assert compute_fibonacci(10) == 55
        assert call_count == 11  # Only 11 unique calls should be made
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_memoize_repeated_calls(self):
        """Test memoize returns cached results on repeated calls."""
        call_count = 0

        @decorate.memoize
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same argument - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Call count should not increase

    def test_retry_success(self, capsys):
        """Test retry decorator succeeds after retries."""
        call_count = 0

        @decorate.retry(max_retries=3, delay=1)
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "Success"

        result = sometimes_fails()
        assert result == "Success"
        assert call_count == 3
        captured = capsys.readouterr()
        assert "Retrying sometimes_fails()... (1/3)" in captured.out
        assert "Retrying sometimes_fails()... (2/3)" in captured.out

    def test_retry_failure(self, capsys):
        """Test retry decorator fails after max retries."""

        @decorate.retry(max_retries=3, delay=1)
        def always_fails():
            raise ValueError("This will always fail")

        with pytest.raises(Exception, match=r"always_fails\(\) failed after 3 retries:\nThis will always fail"):
            always_fails()
        captured = capsys.readouterr()
        assert "Retrying always_fails()... (1/3)" in captured.out
        assert "Retrying always_fails()... (2/3)" in captured.out

    def test_retry_selective_exceptions(self):
        """Test retry decorator only retries specific exceptions."""
        call_count = 0

        @decorate.retry(max_retries=3, delay=0.1, exceptions=ConnectionError)
        def selective_retry():
            nonlocal call_count
            call_count += 1
            # This will not be retried because it's not a ConnectionError
            raise TypeError("This error will not be retried")

        with pytest.raises(TypeError, match="This error will not be retried"):
            selective_retry()
        # Should fail immediately without retries
        assert call_count == 1

    def test_rate_limit(self):
        """Test rate_limit decorator enforces call limits."""

        @decorate.rate_limit(calls=2, period=5)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        with pytest.raises(Exception, match=r"limited_function\(\) rate limit exceeded. Try again in"):
            limited_function()

    def test_rate_limit_wait(self, capsys):
        """Test rate_limit decorator resets after period."""

        @decorate.rate_limit(calls=2, period=2)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        time.sleep(2)
        assert limited_function() == "Success"
        captured = capsys.readouterr()
        assert captured.out == ""
