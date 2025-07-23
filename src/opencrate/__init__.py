from typing import Any, Callable

from .core import (  # noqa: F401
    concurrency,  # noqa: F401
    decorate,
    io,
    visualize,  # noqa: F401
)
from .core import configuration as cfg
from .core import snapshot as snp  # noqa: F401

snapshot: snp.Snapshot = snp.Snapshot()
_configuration = cfg.Configuration()
config: callable = _configuration.config

from .core.opencrate import OpenCrate  # noqa: F401

debug: Callable[[Any], Any] = snapshot.debug
info: Callable[[Any], Any] = snapshot.info
warning: Callable[[Any], Any] = snapshot.warning
error: Callable[[Any], Any] = snapshot.error
critical: Callable[[Any], Any] = snapshot.critical
exception: Callable[[Any], Any] = snapshot.exception
success: Callable[[Any], Any] = snapshot.success
