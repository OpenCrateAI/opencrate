from opencrate.core.utils.concurrency import (
    parallelize_with_processes,
    parallelize_with_threads,
    parallize_with_batch_processes,
)


def _cube(x):
    return x**3


class TestConcurrencyFunctions:
    def test_parallelize_with_threads(self):
        results = parallelize_with_threads(_cube, [1, 2, 3], title="Computing cubes")
        assert all(result in [1, 8, 27] for result in results)

    def test_parallelize_with_processes(self):
        results = parallelize_with_processes(_cube, [1, 2, 3], title="Computing cubes")
        assert all(result in [1, 8, 27] for result in results)

    def test_parallize_with_batch_processes(self):
        results = parallize_with_batch_processes(_cube, [1, 2, 3, 4], title="Computing cubes")
        assert results == [1, 8, 27, 64]
