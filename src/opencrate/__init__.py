from .core import concurrency, io, snapshot  # type: ignore
 
snapshot = snapshot.Snapshot()

debug = snapshot.debug
info = snapshot.info
warning = snapshot.warning
error = snapshot.error
critical = snapshot.critical
exception = snapshot.exception
success = snapshot.success

__all__ = [
    "concurrency",
    "io",
    "snapshot",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
    "success",
]
