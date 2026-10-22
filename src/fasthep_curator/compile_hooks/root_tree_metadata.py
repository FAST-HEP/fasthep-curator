from __future__ import annotations

import warnings
from typing import Any

import uproot

ROOT_TREE_DATASET_METADATA_SPEC = {
    "name": "dataset_metadata.root_tree",
    "kind": "compile_hook",
    "version": "1.0",
    "lifecycle": {"when": "after_datasets"},
    "input": {"artifacts": ["datasets", "sources"]},
    "result": {"artifacts": ["dataset_metadata"]},
}


def inspect_root_tree_datasets(
    ctx: Any,
    *,
    total_entries_source: str | None = "nevents",
    add_per_file: bool = False,
) -> dict[str, Any]:
    """Record entry counts for declared datasets.

    ``total_entries`` of a dataset is taken from the dataset key named by
    ``total_entries_source`` (default ``nevents``) when it holds a valid count:
    an ``int`` (not a ``bool``) or a digit-only string, and not negative. The
    files are opened only for datasets without a valid count, when
    ``total_entries_source`` is ``None``, or when ``add_per_file`` asks for the
    per-file entries. ``total_entries_origin`` records which source was used, and
    ``total_entries_fallback`` why a requested key was not used.

    The hook uses metadata-only ROOT access. It reads ``TTree.num_entries`` and
    must not materialise event arrays. Counts from the dataset key are not
    cross-checked against the file list: a trimmed ``files`` list is
    inconsistent input that the hook cannot detect (unless ``add_per_file``
    reads the files anyway, which then warns on a mismatch).
    """
    _validate_params(total_entries_source, add_per_file)
    datasets = dict(getattr(ctx, "plan_context", {}).get("datasets") or {})
    tree_names = _root_tree_names(getattr(ctx, "normalized", {}) or {})
    if not datasets or not tree_names:
        return {"dataset_metadata": {"datasets": {}}}

    out: dict[str, Any] = {"datasets": {}}
    for dataset_name, dataset_spec in datasets.items():
        dataset = dataset_spec or {}
        declared = None
        fallback = None
        if total_entries_source is not None:
            raw = dataset.get(total_entries_source)
            declared = _valid_entry_count(raw)
            if declared is None:
                fallback = "missing" if raw is None else "invalid"

        files_obj: dict[str, Any] = {}
        read_total = None
        if declared is None or add_per_file:
            files_obj = _inspect_dataset_files(
                str(dataset_name), list(dataset.get("files") or []), tree_names
            )
            read_total = int(sum(item["entries"] for item in files_obj.values()))

        record: dict[str, Any] = {"files": files_obj if add_per_file else {}}
        if declared is not None:
            record["total_entries"] = declared
            record["total_entries_origin"] = total_entries_source
            if read_total is not None and read_total != declared:
                warnings.warn(
                    f"dataset={dataset_name!r}: {total_entries_source!r} is "
                    f"{declared} but the listed files hold {read_total} entries; "
                    "the file list and the count are inconsistent",
                    stacklevel=2,
                )
        else:
            record["total_entries"] = read_total
            record["total_entries_origin"] = "read"
            if fallback is not None:
                record["total_entries_fallback"] = fallback
        out["datasets"][str(dataset_name)] = record

    return {"dataset_metadata": out}


def _validate_params(total_entries_source: Any, add_per_file: Any) -> None:
    if total_entries_source is not None:
        if not isinstance(total_entries_source, str):
            raise TypeError(
                "total_entries_source must be a dataset key (str) or None, "
                f"got {type(total_entries_source).__name__}"
            )
        if not total_entries_source:
            raise ValueError("total_entries_source must not be an empty string")
    if not isinstance(add_per_file, bool):
        raise TypeError(
            f"add_per_file must be a bool, got {type(add_per_file).__name__}"
        )


def _valid_entry_count(value: Any) -> int | None:
    """Return ``value`` as a non-negative int, or ``None`` when it is not one.

    Flow stores ``nevents`` as a string, so digit-only strings are accepted.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return None


def _inspect_dataset_files(
    dataset_name: str,
    files: list[Any],
    tree_names: list[str],
) -> dict[str, Any]:
    files_obj: dict[str, Any] = {}
    for file_path in files:
        file_key = str(file_path)
        try:
            by_tree = _inspect_file_tree_entries(file_key, tree_names)
        except Exception as exc:
            raise RuntimeError(
                "Failed to inspect ROOT dataset metadata for "
                f"dataset={dataset_name!r} file={file_key!r}: {exc}"
            ) from exc
        files_obj[file_key] = {
            "entries": int(by_tree[tree_names[0]]),
            "by_tree": by_tree,
        }
    return files_obj


def _root_tree_names(normalized: dict[str, Any]) -> list[str]:
    sources = dict(normalized.get("sources") or {})
    trees: list[str] = []
    seen: set[str] = set()
    for source in sources.values():
        if not isinstance(source, dict):
            continue
        if source.get("kind") != "root_tree":
            continue
        tree = source.get("tree")
        if not isinstance(tree, str) or not tree:
            continue
        if tree in seen:
            continue
        seen.add(tree)
        trees.append(tree)
    return trees


def _inspect_file_tree_entries(
    file_path: str,
    tree_names: list[str],
) -> dict[str, int]:
    by_tree: dict[str, int] = {}
    with uproot.open(file_path) as root_file:
        for tree_name in tree_names:
            try:
                tree = root_file[tree_name]
            except KeyError as exc:
                raise KeyError(
                    f"Tree {tree_name!r} not found in ROOT file: {file_path}"
                ) from exc
            by_tree[tree_name] = int(tree.num_entries)
    return by_tree
