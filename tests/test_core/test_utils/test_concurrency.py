from opencrate import concurrency


def _cube(value):
    return value**3


def _add(x, y):
    return x + y


def x():
    return list(range(100))


def y():
    return [i**3 for i in list(range(100))]


class TestUtilsConcurrency:
    def test_parallelize_with_threads(self):
        """Test basic thread parallelization with single argument."""
        results = concurrency.parallelize_with_threads(_cube, x(), title="Computing cubes")
        assert all(result in y() for result in results)

    def test_parallelize_with_threads_ordered(self):
        """Test thread parallelization with ordered results."""
        results = concurrency.parallelize_with_threads(_cube, list(range(10)), title="Computing cubes", order_results=True)
        expected = [i**3 for i in range(10)]
        assert results == expected

    def test_parallelize_with_threads_multiple_args(self):
        """Test thread parallelization with multiple arguments."""
        args_list = [(1, 2), (3, 4), (5, 6)]
        results = concurrency.parallelize_with_threads(_add, args_list, order_results=True)
        assert results == [3, 7, 11]

    def test_parallelize_with_processes(self):
        """Test basic process parallelization with single argument."""
        results = concurrency.parallelize_with_processes(_cube, x(), title="Computing cubes")
        assert all(result in y() for result in results)

    def test_parallelize_with_processes_ordered(self):
        """Test process parallelization with ordered results."""
        results = concurrency.parallelize_with_processes(_cube, list(range(10)), title="Computing cubes", order_results=True)
        expected = [i**3 for i in range(10)]
        assert results == expected

    def test_parallelize_with_processes_multiple_args(self):
        """Test process parallelization with multiple arguments."""
        args_list = [(1, 2), (3, 4), (5, 6)]
        results = concurrency.parallelize_with_processes(_add, args_list, order_results=True)
        assert results == [3, 7, 11]

    def test_parallize_with_batch_processes(self):
        """Test batch process parallelization preserves order."""
        results = concurrency.parallize_with_batch_processes(_cube, x(), title="Computing cubes")
        assert results == y()

    def test_parallize_with_batch_processes_custom_batch_size(self):
        """Test batch process parallelization with custom batch size."""
        results = concurrency.parallize_with_batch_processes(_cube, list(range(20)), batch_size=4, title="Computing cubes")
        expected = [i**3 for i in range(20)]
        assert results == expected
