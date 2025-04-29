from __future__ import annotations

import operator
import os
from collections import Counter, defaultdict
from functools import partial, reduce
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import uproot

from fasthep_curator.read import Prefix


class Expander:
    """
    Base class for file list expanders
    """

    @staticmethod
    def check_setup() -> bool:
        msg = "check_setup not implemented"
        raise NotImplementedError(msg)

    @staticmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]:
        msg = "expand_file_list not implemented"
        raise NotImplementedError(msg)

    @staticmethod
    def check_files(
        *args: list[Any], **kwargs: dict[str, Any]
    ) -> tuple[list[str], dict[str, int] | int, dict[str, Any]]:
        msg = "check_files not implemented"
        raise NotImplementedError(msg)


class XrootdExpander(Expander):
    """
    Expand wild-carded file paths, including with xrootd-served files
    """

    @staticmethod
    def check_setup() -> bool:
        return True

    @staticmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]:
        from XRootD.client.glob_funcs import glob

        return expand_file_list_generic(
            files, prefix, glob=partial(glob, raise_error=True)
        )

    @staticmethod
    def check_files(
        *args: list[Any], **kwargs: dict[str, Any]
    ) -> tuple[list[str], dict[str, int] | int, dict[str, Any]]:
        return check_entries_uproot(*args, **kwargs)  # type: ignore[arg-type]


class LocalGlobExpander(Expander):
    """
    Expand wild-carded file paths on the local file system
    """

    import glob

    @staticmethod
    def check_setup() -> bool:
        return True

    @staticmethod
    def expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]:
        glob = LocalGlobExpander.glob.glob
        return expand_file_list_generic(files, prefix, glob=glob)

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
        scheme = urlparse(name).scheme
        if not scheme and not Path(name).is_absolute():
            path = str(Path(str(prefix)) / name) if prefix else os.path.relpath(name)
        expanded = glob(path)
        full_list += map(str, expanded)
    return full_list


def uproot_num_entries(files: list[str], tree_name: str) -> dict[str, Any]:
    func = uproot.numentries if hasattr(uproot, "numentries") else uproot.num_entries
    input_files = [f"{file}:{tree_name}" for file in files]
    numentries = {}
    for file, _, entries in func(input_files):
        numentries[file] = entries
    return numentries


def check_entries_uproot(
    files: list[str],
    tree_names: str | list[str],
    no_empty: bool,
    confirm_tree: bool = True,
    list_branches: bool = False,
    ignore_inaccessible: bool = False,
) -> tuple[list[str], dict[str, Any] | int, dict[str, Any]]:
    no_empty = no_empty or confirm_tree
    if not isinstance(tree_names, (tuple, list)):
        tree_names = [tree_names]

    if ignore_inaccessible:
        files = [f for f in files if os.access(f, os.R_OK)]

    if not no_empty:
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
