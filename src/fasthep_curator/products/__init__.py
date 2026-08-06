from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hepflow.build_layout import BuildPaths
from hepflow.runtime.materialize import product_id
from hepflow.utils import write_json


def merge_schema_products(
    values: list[dict[str, Any]],
    *,
    node: Any,
    output_name: str,
    dataset_name: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    del node, output_name, dataset_name
    if len(values) == 1:
        return values[0]
    return list(values)


def materialize_schema_product(
    value: dict[str, Any],
    *,
    node: Any,
    output_name: str,
    outdir: str | Path,
    build_paths: BuildPaths | None = None,
) -> dict[str, Any]:
    del output_name
    return _materialize_json_product(
        value,
        node=node,
        outdir=outdir,
        build_paths=build_paths,
        family="schemas",
        manifest_key="schemas",
    )


def merge_schema_comparison_products(
    values: list[dict[str, Any]],
    *,
    node: Any,
    output_name: str,
    dataset_name: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    del node, output_name, dataset_name
    if len(values) == 1:
        return values[0]
    return list(values)


def materialize_schema_comparison_product(
    value: dict[str, Any],
    *,
    node: Any,
    output_name: str,
    outdir: str | Path,
    build_paths: BuildPaths | None = None,
) -> dict[str, Any]:
    del output_name
    return _materialize_json_product(
        value,
        node=node,
        outdir=outdir,
        build_paths=build_paths,
        family="comparisons",
        manifest_key="comparisons",
    )


def _materialize_json_product(
    value: dict[str, Any],
    *,
    node: Any,
    outdir: str | Path,
    build_paths: BuildPaths | None,
    family: str,
    manifest_key: str,
) -> dict[str, Any]:
    paths = build_paths or BuildPaths(root=Path(outdir))
    product_dir = paths.artifact_dir(family)
    product_dir.mkdir(parents=True, exist_ok=True)
    item_id = product_id(node)
    product_path = paths.artifact(family, f"{item_id}.json")
    write_json(value, product_path)
    item = {
        "id": item_id,
        "path": paths.relative_to_root(product_path).as_posix(),
        "producer": node.id,
    }
    _update_manifest(product_dir, manifest_key, item)
    return {"value": value, "items": [item]}


def _update_manifest(root: Path, key: str, item: dict[str, str]) -> None:
    manifest_path = root / "manifest.json"
    manifest: dict[str, Any] = {key: []}
    if manifest_path.exists():
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            manifest.update(loaded)
    items = [
        entry
        for entry in list(manifest.get(key) or [])
        if entry.get("id") != item["id"]
    ]
    items.append(item)
    manifest[key] = sorted(items, key=lambda entry: str(entry.get("id")))
    write_json(manifest, manifest_path)


__all__ = [
    "materialize_schema_comparison_product",
    "materialize_schema_product",
    "merge_schema_comparison_products",
    "merge_schema_products",
]
