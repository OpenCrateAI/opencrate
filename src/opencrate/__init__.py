from .core import concurrency
from .core import configuration as cfg
from .core import decorate, io
from .core import snapshot as snp
from .core import visualize

snapshot: snp.Snapshot = snp.Snapshot()
_configuration = cfg.Configuration()
config = _configuration.config

from .core.opencrate import OpenCrate  # noqa: E402

debug = snapshot.debug
info = snapshot.info
warning = snapshot.warning
error = snapshot.error
critical = snapshot.critical
exception = snapshot.exception
success = snapshot.success

__all__ = [
    "OpenCrate",
    "concurrency",
    "cfg",
    "decorate",
    "io",
    "snapshot",
    "visualize",
    "OpenCrate",
    "config",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
    "success",
]
