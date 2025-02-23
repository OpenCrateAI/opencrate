from typing import Any, Callable

from .core import concurrency, decorate, io  # noqa: F401
from .core import snapshot as snp

snapshot: snp.Snapshot = snp.Snapshot()

debug: Callable[[Any], Any] = snapshot.debug
info: Callable[[Any], Any] = snapshot.info
warning: Callable[[Any], Any] = snapshot.warning
error: Callable[[Any], Any] = snapshot.error
critical: Callable[[Any], Any] = snapshot.critical
exception: Callable[[Any], Any] = snapshot.exception
success: Callable[[Any], Any] = snapshot.success

__all__ = [
    "concurrency",
    "decorate",
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
