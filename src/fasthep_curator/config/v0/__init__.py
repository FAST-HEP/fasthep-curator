from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omegaconf import DictConfig, OmegaConf, SCMode


@dataclass
class Dataset:
    """
    DatasetConfig class for holding dataset information.
    """

    name: str
    files: list[str] | None = None
    nevents: int | None = None
    nfiles: int | None = None
    eventtype: str = "data"
    tree: str = "Events"
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

    @staticmethod
    def from_dictconfig(config: DictConfig) -> CuratorConfig:
        schema = OmegaConf.structured(CuratorConfig)
        processed_config = config.copy()
        if "defaults" in config:
            processed_config["datasets"] = []
            for dataset in config["datasets"]:
                processed_dataset = config["defaults"].copy()

                processed_dataset.update(dataset)

                processed_config["datasets"].append(processed_dataset)

        merged_conf = OmegaConf.merge(schema, processed_config)
        return OmegaConf.to_container(
            merged_conf,
            resolve=True,
            structured_config_mode=SCMode.INSTANTIATE,
        )  # type: ignore[return-value]
