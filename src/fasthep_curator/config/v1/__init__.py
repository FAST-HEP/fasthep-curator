from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Dataset:
    """
    DatasetConfig class for holding dataset information.
    """

    name: str
    files: list[str] | None = None
    n_events: int = 0
    n_files: int = 0
    event_type: str = "data"
    trees: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass
class CuratorConfig:
    """
    CuratorConfig class for holding curator configuration.
    """

    datasets: list[Dataset] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])
    defaults: dict[str, Any] | None = None
    version: int = 0
