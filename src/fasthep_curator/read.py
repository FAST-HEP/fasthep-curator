from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace as Dataset
from typing import Any, TypeAlias

Prefix: TypeAlias = str | list[dict[str, Any]] | None


def __load_yaml_config(yaml_config: str) -> dict[str, Any]:
    """
    Load a YAML configuration file and return the datasets.

    Args:
        yaml_config (str): Path to the YAML configuration file.

    Returns:
        str: The loaded YAML configuration.
    Raises:
        RuntimeError: If the YAML configuration file is empty.
    """
    import yaml

    with Path(yaml_config).open("r") as f:
        config = yaml.safe_load(f)
    if not config:
        msg = f"Empty config file: {yaml_config}"
        raise RuntimeError(msg)

    return config  # type: ignore[no-any-return]


def from_string(dataset: str, defaults: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Load a dataset from a string.

    Args:
        dataset (str): The dataset string.
        defaults (dict[str, str] | None): Default values for the dataset.

    Returns:
        Dataset: The loaded dataset.
    """
    datasets = defaults.copy() if defaults else {}
    datasets["name"] = dataset

    return datasets


def from_dict(
    dataset: dict[str, str], defaults: dict[str, Any] | None
) -> dict[str, Any]:
    """
    Load a dataset from a dictionary.

    Args:
        dataset (dict[str, str]): The dataset dictionary.
        defaults (dict[str, str] | None): Default values for the dataset.

    Returns:
        Dataset: The loaded dataset.
    """
    if "name" not in dataset:
        msg = "Dataset must contain a 'name' key"
        raise RuntimeError(msg)

    datasets = defaults.copy() if defaults else {}
    datasets.update(dataset)

    return datasets


def from_yaml(
    yaml_config: str,
    defaults: dict[str, Any] | None = None,
    prefix: Prefix = None,
    expand_prefix: bool = True,
) -> list[Dataset]:
    """
    Load datasets from a YAML configuration file.

    Args:
        yaml_config (str): Path to the YAML configuration file.

    Returns:
        dict[Dataset]: A dictionary containing the datasets.
    """
    config = __load_yaml_config(yaml_config)
    this_dir = Path(yaml_config).parent

    return get_datasets(
        config=config,
        defaults=defaults,
        config_dir=this_dir,
        prefix=prefix,
        expand_prefix=expand_prefix,
    )


def get_datasets(
    config: dict[str, Any],
    defaults: dict[str, Any] | None = None,
    imported_files: set[str] | None = None,
    config_dir: Path | None = None,
    prefix: Prefix = None,
    expand_prefix: bool = True,
) -> list[Dataset]:
    """
    Get datasets from a configuration dictionary.
    Args:
        config (dict[str, Any]): The configuration dictionary.
        defaults (dict[str, Any] | None): Default values for the datasets.
        already_imported (bool): Flag indicating if the datasets have already been imported.
        prefix (Prefix): Prefix to be applied to the dataset names.
        expand_prefix (bool): Flag indicating if the prefix should be expanded.
    Returns:
        list[Dataset]: A list of datasets.
    """
    datasets = []

    if defaults is None:
        defaults = {}
    defaults.update(config.get("defaults", {}))
    if imported_files is None:
        imported_files = set()

    for import_str in config.get("import", []):
        import_file = import_str
        if config_dir:
            import_file = import_file.replace("{this_dir}", str(config_dir))
        if import_file in imported_files:
            continue
        imported_files.add(import_file)
        content = __load_yaml_config(import_file)
        datasets.extend(
            get_datasets(
                content, defaults, imported_files, config_dir, prefix, expand_prefix
            )
        )

    for dataset_cfg in config.get("datasets", []):
        if isinstance(dataset_cfg, str):
            dataset = from_string(dataset_cfg, defaults)
        elif isinstance(dataset_cfg, dict):
            dataset = from_dict(dataset_cfg, defaults)
        else:
            msg = f"Invalid dataset format: {dataset_cfg}"
            raise RuntimeError(msg)

        if prefix and expand_prefix:
            dataset["files"] = apply_prefix(
                prefix, dataset_cfg["files"], str(config_dir)
            )

        datasets.append(Dataset(**dataset))

    return datasets


def apply_prefix(
    prefix: Prefix,
    files: list[str],
    selected_prefix: str | None = None,
    dataset: str | None = None,
) -> list[str]:
    """
    Apply a prefix to a list of files.

    Args:
        prefix (str | None): The prefix to be applied.
        files (list[str]): The list of files.
        config_dir (Path | None): The configuration directory.
        dataset (str | None): The name of the dataset.

    Returns:
        list[str]: The list of files with the prefix applied.
    """
    if not prefix:
        return files

    prefix_str = str(prefix)
    if isinstance(prefix, list):
        if not all(isinstance(p, dict) and len(p) == 1 for p in prefix):  # type: ignore[redundant-expr]
            msg = "'prefix' is a list, but not all elements are single-length dicts"
            raise ValueError(msg)
        prefix_list = [next(iter(p.items())) for p in prefix]

        if selected_prefix:
            matched = [v for p, v in prefix_list if p == selected_prefix]
            if len(matched) > 1:
                msg = f"Prefix '{selected_prefix}' is defined {len(matched)} times, not sure which to use"
                raise ValueError(msg)
            if not matched:
                msg = (
                    f"Prefix '{selected_prefix}' is not defined for dataset '{dataset}'"
                )
                raise ValueError(msg)
            prefix_str = matched[0]
        else:
            prefix_str = prefix_list[0][1]
    elif not isinstance(prefix, str):
        msg = f"'prefix' for dataset '{dataset}' is type {type(prefix)}. Need a string or a list of single-length dicts"  # type: ignore[unreachable]
        raise ValueError(msg)

    return [file.format(prefix=prefix_str) for file in files]
