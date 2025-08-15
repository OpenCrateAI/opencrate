from opencrate.core.utils.concurrency import parallelize_with_processes, parallelize_with_threads, parallize_with_batch_processes


def _cube(value):
    return value**3


def x():
    return list(range(100))


def y():
    return [i**3 for i in list(range(100))]


class TestUtilsConcurrency:
    def test_parallelize_with_threads(self):
        results = parallelize_with_threads(_cube, x(), title="Computing cubes")
        assert all(result in y() for result in results)

    def test_parallelize_with_processes(self):
        results = parallelize_with_processes(_cube, x(), title="Computing cubes")
        assert all(result in y() for result in results)

    def test_parallize_with_batch_processes(self):
        results = parallize_with_batch_processes(_cube, x(), title="Computing cubes")
        assert results == y()
