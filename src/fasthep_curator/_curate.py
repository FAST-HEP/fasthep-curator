from __future__ import annotations

from typing import Any

from fasthep_curator._inspect import get_trees

from .write import prepare_file_list


def _parse_tree_from_obj_name(obj_name: str) -> str:
    if "." in obj_name:
        return obj_name.split(".")[0]
    return obj_name


def curate(dataset: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Curate the datasets and write them to a YAML file.

    Args:
        dataset (str): The name of the dataset.
        files (list[str]): List of file paths to curate.
    """
    files = data.get("files", [])
    if not files:
        msg = f"No files found for dataset: {dataset}"
        raise ValueError(msg)
    tree_names = list(get_trees(files[0]))
    return prepare_file_list(
        files=files,
        dataset=dataset,
        eventtype=data.get("event_type", "data"),
        tree_name=tree_names[0],
    )


def curate_all(datasets: dict[str, Any]) -> dict[str, Any]:
    """
    Curate all datasets and write them to a YAML file.

    Args:
        datasets (list[dict[str, Any]]): List of datasets to curate.
    """
    results = {}
    for name, dataset in datasets.items():
        results[name] = curate(name, dataset)
    return results
