"""
Copyright (c) 2025 Luke Kreczko. All rights reserved.

fasthep-curator: Package for making (ROOT T)Trees into (Pandas) Tables
"""

from __future__ import annotations

from ._curate import curate, curate_all
from ._inspect import inspect, inspect_all
from ._version import version as __version__
from .config import load_config
from .read import check
from .write import write_yaml

__all__ = [
    "__version__",
    "check",
    "curate",
    "curate_all",
    "inspect",
    "inspect_all",
    "load_config",
    "write_yaml",
]
