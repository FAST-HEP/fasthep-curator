"""
Copyright (c) 2025 Luke Kreczko. All rights reserved.

fasthep-curator: Package for making (ROOT T)Trees into (Pandas) Tables
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._curate import curate, curate_all
from ._inspect import inspect, inspect_all
from ._version import version as __version__
from .config import CuratorConfig, Dataset, compact, load_config, write_config
from .read import check
from .write import write_yaml


def add_dataset(
    dataset_name: str,
    files: list[str],
    output_file: str,
    event_type: str | None = None,
    metadata: dict[str, str] | None = None,
) -> CuratorConfig:
    """Add a dataset to a curator configuration."""
    config = load_config(output_file) if Path(output_file).exists() else CuratorConfig()

    curated_data = curate(
        dataset_name,
        {"files": files, "event_type": event_type, "metadata": metadata or {}},
    )

    config.datasets.append(Dataset(**curated_data))
    config = compact(config)
    write_config(config, output_file)
    return config


def add_datasets(
    datasets: dict[str, Any],
    output_file: str,
    overwrite: bool = False,
) -> None:
    """Add multiple datasets to a curator configuration."""

    if Path(output_file).exists() and not overwrite:
        msg = f"Output file {output_file} already exists. Use overwrite=True to replace it."
        raise FileExistsError(msg)
    config = CuratorConfig()

    curated_data = curate_all(datasets)
    config.datasets = [
        Dataset(name=name, **data) for name, data in curated_data.items()
    ]

    config = compact(config)
    write_config(config, output_file)


__all__ = [
    "__version__",
    "add_dataset",
    "check",
    "curate",
    "curate_all",
    "inspect",
    "inspect_all",
    "load_config",
    "write_yaml",
]
