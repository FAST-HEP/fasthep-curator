from __future__ import annotations

from typing import Any

import uproot

ROOT_TREE_DATASET_METADATA_SPEC = {
    "name": "dataset_metadata.root_tree",
    "kind": "compile_hook",
    "version": "1.0",
    "lifecycle": {"when": "after_datasets"},
    "inputs": ["datasets", "sources"],
    "outputs": ["dataset_metadata"],
}


def inspect_root_tree_datasets(ctx: Any, **params: Any) -> dict[str, Any]:
    """Inspect ROOT tree entry counts for declared datasets.

    This compile hook intentionally uses metadata-only ROOT access. It reads
    ``TTree.num_entries`` and must not materialise event arrays.
    """
    del params
    datasets = dict(getattr(ctx, "plan_context", {}).get("datasets") or {})
    tree_names = _root_tree_names(getattr(ctx, "normalized", {}) or {})
    if not datasets or not tree_names:
        return {"dataset_metadata": {"datasets": {}}}

    out: dict[str, Any] = {"datasets": {}}
    for dataset_name, dataset in datasets.items():
        files = list((dataset or {}).get("files") or [])
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

            entries = int(by_tree[tree_names[0]])
            files_obj[file_key] = {
                "entries": entries,
                "by_tree": by_tree,
            }

        out["datasets"][str(dataset_name)] = {
            "files": files_obj,
            "total_entries": int(sum(item["entries"] for item in files_obj.values())),
        }

    return {"dataset_metadata": out}


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
