from __future__ import annotations

import glob as local_glob
import operator
import os
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from functools import partial, reduce
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import uproot
from loguru import logger

from fasthep_curator.read import Prefix

try:
    from XRootD.client.glob_funcs import glob as xrd_glob
except ImportError:
    xrd_glob = None
    logger.warning(
        "XRootD client library not found. XRootD file list expansion will not be available."
    )


class Expander(ABC):
    """
    Base class for file list expanders
    """

    @staticmethod
    @abstractmethod
    def check_setup() -> bool: ...

    @staticmethod
    @abstractmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]: ...

    @staticmethod
    @abstractmethod
    def check_files(
        *args: Any, **kwargs: Any
    ) -> tuple[list[str], dict[str, int] | int, dict[str, Any]]: ...


class XrootdExpander(Expander):
    """
    Expand wild-carded file paths, including with xrootd-served files
    """

    @staticmethod
    def check_setup() -> bool:
        return True

    @staticmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]:
        if xrd_glob is None:
            logger.warning(
                "XRootD client library not found. Falling back to local file list expansion."
            )
            glob_func = LocalGlobExpander.glob
        else:
            glob_func = partial(xrd_glob, raise_error=True)
        return expand_file_list_generic(files, prefix, glob=glob_func)

    @staticmethod
    def check_files(
        *args: list[Any], **kwargs: dict[str, Any]
    ) -> tuple[list[str], dict[str, int] | int, dict[str, Any]]:
        return check_entries_uproot(*args, **kwargs)  # type: ignore[arg-type]


class LocalGlobExpander(Expander):
    """
    Expand wild-carded file paths on the local file system
    """

    glob = local_glob.glob

    @staticmethod
    def check_setup() -> bool:
        return True

    @staticmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]:
        return expand_file_list_generic(files, prefix, glob=LocalGlobExpander.glob)

    @staticmethod
    def check_files(
        *args: list[Any], **kwargs: dict[str, Any]
    ) -> tuple[list[str], dict[str, int] | int, dict[str, Any]]:
        return check_entries_uproot(*args, **kwargs)  # type: ignore[arg-type]


def expand_file_list_generic(
    files: list[str], prefix: Prefix, glob: Callable[..., list[str]]
) -> list[str]:
    full_list: list[str] = []
    for name in files:
        path = str(name)
        scheme = urlparse(path).scheme
        if not scheme and not Path(path).is_absolute():
            path = str(Path(str(prefix)) / path) if prefix else os.path.relpath(path)
        expanded = glob(path)
        full_list += map(str, expanded)
    return full_list


def _tree_exists(file: str, tree_name: str) -> bool:
    with uproot.open(file) as f:
        if tree_name in f:
            return True
    return False


def uproot_num_entries(files: list[str], tree_name: str) -> dict[str, Any]:
    func = uproot.numentries if hasattr(uproot, "numentries") else uproot.num_entries
    good_files = [f for f in files if _tree_exists(f, tree_name)]
    missing_trees = [f for f in files if f not in good_files]
    input_files = [f"{file}:{tree_name}" for file in good_files]
    numentries = dict.fromkeys(missing_trees, 0)
    if not input_files:
        return numentries
    for file, _, entries in func(input_files):
        numentries[file] = entries
    return numentries


def check_entries_uproot(
    files: list[str],
    tree_names: str | list[str],
    disallow_empty: bool,
    confirm_tree: bool = True,
    list_branches: bool = False,
    ignore_inaccessible: bool = False,
) -> tuple[list[str], dict[str, Any] | int, dict[str, Any]]:
    disallow_empty = disallow_empty or confirm_tree
    if not isinstance(tree_names, (tuple, list)):
        tree_names = [tree_names]

    if ignore_inaccessible:
        files = [f for f in files if os.access(f, os.R_OK)]

    if not disallow_empty:
        n_entries = {tree: uproot_num_entries(files, tree) for tree in tree_names}
    else:
        n_entries = dict.fromkeys(tree_names, 0)  # type: ignore[arg-type]
        missing_trees = defaultdict(list)
        for tree in tree_names:
            totals = uproot_num_entries(files, tree)

            for name, entries in totals.items():
                n_entries[tree] += entries
                if entries <= 0:
                    files.remove(name)
                if (confirm_tree and entries == 0) and tree not in uproot.open(name):
                    missing_trees[tree].append(name)
        if missing_trees:
            missing_files: set[str] = set(
                reduce(operator.iadd, (list(v) for v in missing_trees.values()), [])
            )
            msg = "Missing at least one tree (%s) for %d file(s): %s"
            msg = msg % (
                ", ".join(missing_trees),
                len(missing_trees),
                ", ".join(missing_files),
            )
            raise RuntimeError(msg)

    branches: dict[str, Any] = {}
    if list_branches:
        for tree in tree_names:
            open_files = (uproot.open(f) for f in files)
            all_branches = (
                f[tree].keys(recursive=True) for f in open_files if tree in f
            )
            branches[tree] = dict(Counter(reduce(operator.iadd, all_branches, [])))

    if len(n_entries) == 1:
        n_entries = next(iter(n_entries.values()))
    return files, n_entries, branches
