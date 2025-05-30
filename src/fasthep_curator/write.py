from __future__ import annotations

import importlib
import itertools
import logging
import operator
import os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from . import read
from .catalogues import get_file_list_expander, known_expanders

logger = logging.getLogger(__name__)


__all__ = [
    "add_meta",
    "known_expanders",
    "prepare_file_list",
    "process_user_function",
    "write_yaml",
]


def prepare_file_list(
    files: list[str],
    dataset: str,
    eventtype: str,
    tree_name: str | list[str],
    expander_name: str = "xrootd",
    prefix: str | None = None,
    no_empty_files: bool = True,
    confirm_tree: bool = True,
    ignore_inaccessible: bool = False,
    include_branches: bool = False,
) -> dict[str, Any]:
    """
    Expands all globs in the file lists and creates a dataframe similar to those from a DAS query
    """
    expander = get_file_list_expander(expander_name)

    full_list = expander.expand_file_list(files, prefix=prefix)
    full_list = [os.path.realpath(f) if ":" not in f else f for f in full_list]
    full_list, numentries, branches = expander.check_files(
        full_list,
        tree_name,
        disallow_empty=no_empty_files,
        list_branches=include_branches,
        confirm_tree=confirm_tree,
        ignore_inaccessible=ignore_inaccessible,
    )
    # full_list = [str(f) for f in full_list]

    data: dict[str, Any] = {}
    if prefix:
        full_list = [
            "{prefix}" + path[len(prefix) :] if path.startswith(prefix) else path
            for path in full_list
        ]
        data["prefix"] = [{"default": prefix}]
    data["eventtype"] = eventtype
    data["name"] = dataset
    data["nevents"] = numentries
    data["nfiles"] = len(full_list)
    data["files"] = full_list
    data["tree"] = tree_name[0] if len(tree_name) == 1 else tree_name
    if branches:
        data["branches"] = branches

    return data


def select_default(values: list[Any]) -> Any | None:
    groups_by_value = itertools.groupby(sorted(values))
    groups = [(group, len(list(items))) for group, items in groups_by_value]
    groups_with_multiple_items = [group for group in groups if group[1] > 1]
    if not groups_with_multiple_items:
        return None
    most_common, item_count = max(
        groups_with_multiple_items, key=operator.itemgetter(1)
    )
    count = 0
    for group in groups_with_multiple_items:
        if group[1] == item_count:
            count += 1
            if count > 1:
                is_unique = False
                break
    else:
        is_unique = count == 1
    if not is_unique:
        return None
    return most_common


def prepare_contents(
    datasets: list[dict[str, Any]] | list[SimpleNamespace],
    no_defaults_in_output: bool = False,
) -> dict[str, Any]:
    datasets = [
        vars(data) if isinstance(data, read.Dataset) else data for data in datasets
    ]
    for d in datasets:
        if "associates" in d:
            del d["associates"]

    if no_defaults_in_output:
        # do not group common settings together in default block
        return {"datasets": datasets}

    # build the default properties
    values = defaultdict(list)
    for data in datasets:
        for k, v in data.items():
            values[k].append(v)

    defaults = {}
    for key, vals in values.items():
        if key == "name":
            continue
        is_in_all_datasets = len(vals) == len(datasets)
        if not is_in_all_datasets:
            continue
        new_default = select_default(vals)
        if new_default:
            defaults[key] = new_default

    cleaned_datasets = []
    for data in datasets:
        new_data = {}
        for key, val in data.items():
            if key in defaults and val == defaults[key]:
                continue
            new_data[key] = val
        cleaned_datasets.append(new_data)

    contents = {"datasets": cleaned_datasets}
    if defaults:
        contents["defaults"] = defaults  # type: ignore[assignment]
    return contents


def write_yaml(
    datasets: dict[str, Any],
    output_file: str,
    append: bool = False,
    no_defaults_in_output: bool = False,
) -> str:
    if Path(output_file).exists() and append:
        existing_datasets = read.from_yaml(output_file, expand_prefix=False)
        existing_datasets.append(SimpleNamespace(**datasets))
        contents = prepare_contents(
            existing_datasets, no_defaults_in_output=no_defaults_in_output
        )
    else:
        contents = {}
        if "defaults" in datasets:
            defaults = datasets.pop("defaults")
            contents["defaults"] = defaults
        contents["datasets"] = list(datasets.values())

    # https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
    class MyDumper(yaml.Dumper):
        """Custom YAML dumper to avoid using block style for lists."""

        # def increase_indent(self, flow=False, indentless=False):
        #     return super().increase_indent(flow, indentless)

        # disable aliases and anchors, see https://github.com/yaml/pyyaml/issues/103
        def ignore_aliases(self, _: Any) -> bool:
            return True

    yaml_contents = yaml.dump(contents, Dumper=MyDumper, indent=2)
    with Path(output_file).open("w", encoding="utf-8") as out:
        out.write(yaml_contents)

    return str(Path(output_file).absolute())


def add_meta(dataset: dict[str, Any], meta: list[tuple[Any, Any]]) -> None:
    for key, value in meta:
        if key in dataset:
            msg = f"Meta data '{key}' will override an existing value"
            raise RuntimeError(msg)
        dataset[key] = value


def process_user_function(dataset: dict[str, Any], user_func: str) -> None:
    path = user_func.split(".")
    mod_name = ".".join(path[:-1])
    module = importlib.import_module(mod_name)

    func_name = path[-1]
    function = getattr(module, func_name)

    function(dataset)
