import time

import pytest

from opencrate.core.utils.decorate import memoize, rate_limit, retry, timeit


class TestUtilsDecorate:
    def test_timeit_with_record(self, capsys):
        @timeit(record=True)
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

    def test_timeit_without_record_summarize(self):
        @timeit(record=False)
        def slow_function():
            time.sleep(1)

        slow_function()
        with pytest.raises(Exception, match=r"Summarize is not enabled, set `record` argument to `True` to enable summary."):
            slow_function.summarize()

    def test_memoize(self, capsys):
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
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_retry_success(self, capsys):
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
        captured = capsys.readouterr()
        assert "Retrying sometimes_fails()... (1/3)" in captured.out
        assert "Retrying sometimes_fails()... (2/3)" in captured.out

    def test_retry_failure(self, capsys):
        @retry(max_retries=3, delay=1)
        def always_fails():
            raise ValueError("This will always fail")

        with pytest.raises(Exception, match=r"always_fails\(\) failed after 3 retries:\nThis will always fail"):
            always_fails()
        captured = capsys.readouterr()
        assert "Retrying always_fails()... (1/3)" in captured.out
        assert "Retrying always_fails()... (2/3)" in captured.out

    def test_rate_limit(self):
        @rate_limit(calls=2, period=5)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        with pytest.raises(Exception, match=r"limited_function\(\) rate limit exceeded. Try again in"):
            limited_function()

    def test_rate_limit_wait(self, capsys):
        @rate_limit(calls=2, period=2)
        def limited_function():
            return "Success"

        assert limited_function() == "Success"
        assert limited_function() == "Success"
        time.sleep(2)
        assert limited_function() == "Success"
        captured = capsys.readouterr()
        assert captured.out == ""
