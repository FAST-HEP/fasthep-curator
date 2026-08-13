from __future__ import annotations

from fasthep_curator import api as api

try:
    from ._version import version as __version__
except ModuleNotFoundError:
    __version__ = "0+unknown"

__all__ = ["__version__", "api"]
