from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import uproot

ROOT_TREE_SCHEMA_SPEC = {
    "name": "curator.root_tree_schema",
    "kind": "transform",
    "version": "1.0",
    "input": None,
    "params": {
        "dataset": {"type": "string", "required": True},
        "tree": {"type": "string", "required": False, "default": "Events"},
        "file": {"type": "string", "required": False},
        "full_schema": {"type": "boolean", "required": False, "default": True},
    },
    "result": {
        "schema": {
            "kind": "schema_snapshot",
            "description": "Full ROOT tree schema snapshot.",
        }
    },
}


COMPARE_SCHEMAS_SPEC = {
    "name": "curator.compare_schemas",
    "kind": "transform",
    "version": "1.0",
    "input": None,
    "params": {
        "reference_label": {"type": "string", "required": False},
        "target_label": {"type": "string", "required": False},
    },
    "result": {
        "comparison": {
            "kind": "schema_comparison",
            "description": "Diagnostic comparison of two schema snapshots.",
        }
    },
}


def run_root_tree_schema(
    *,
    dataset: str,
    tree: str = "Events",
    file: str | None = None,
    full_schema: bool = True,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not full_schema:
        raise ValueError(
            "curator.root_tree_schema requires full_schema=true for this operation"
        )
    ctx = dict(ctx or {})
    dataset_name = _required_string(dataset, "dataset")
    tree_name = _required_string(tree, "tree")
    dataset_record = _dataset_record(ctx, dataset_name)
    file_path = str(file or _first_dataset_file(dataset_record, dataset_name))

    schema = _inspect_root_tree_schema(
        file_path=file_path,
        tree_name=tree_name,
        dataset_name=dataset_name,
        dataset_record=dataset_record,
    )
    if hasattr(ctx.get("provenance"), "record_operation"):
        ctx["provenance"].record_operation(
            inputs={
                "files": [file_path],
                "datasets": [dataset_name],
            },
            outputs={"products": [f"schema:{dataset_name}"]},
        )
    return schema


def run_compare_schemas(
    *,
    reference: dict[str, Any],
    target: dict[str, Any],
    reference_label: str | None = None,
    target_label: str | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference_schema = _normalise_schema(reference, "reference")
    target_schema = _normalise_schema(target, "target")
    reference_name = reference_label or _schema_dataset_name(reference_schema)
    target_name = target_label or _schema_dataset_name(target_schema)

    reference_fields = _field_map(reference_schema, counterpart_schema=target_schema)
    target_fields = _field_map(target_schema, counterpart_schema=reference_schema)
    reference_names = set(reference_fields)
    target_names = set(target_fields)
    common_names = sorted(reference_names & target_names)
    only_reference = sorted(reference_names - target_names)
    only_target = sorted(target_names - reference_names)

    type_mismatches: list[dict[str, Any]] = []
    shape_mismatches: list[dict[str, Any]] = []
    compatible_fields: list[str] = []

    for field in common_names:
        reference_detail = reference_fields[field]
        target_detail = target_fields[field]
        type_match = reference_detail.get("primitive_type") == target_detail.get(
            "primitive_type"
        )
        shape_match = reference_detail.get("shape") == target_detail.get("shape")
        if type_match and shape_match:
            compatible_fields.append(field)
            continue
        if not type_match:
            type_mismatches.append(
                {
                    "field": field,
                    "reference": reference_detail.get("primitive_type"),
                    "target": target_detail.get("primitive_type"),
                }
            )
        if not shape_match:
            shape_mismatches.append(
                {
                    "field": field,
                    "reference": reference_detail.get("shape"),
                    "target": target_detail.get("shape"),
                }
            )

    comparison = {
        "version": "1.0",
        "kind": "schema_comparison",
        "reference": reference_name,
        "target": target_name,
        "reference_dataset": _schema_dataset_name(reference_schema),
        "target_dataset": _schema_dataset_name(target_schema),
        "common_fields": common_names,
        "only_in_reference": only_reference,
        "only_in_target": only_target,
        "type_mismatches": type_mismatches,
        "shape_mismatches": shape_mismatches,
        "compatible_fields": compatible_fields,
        "summary": {
            "reference_fields": len(reference_names),
            "target_fields": len(target_names),
            "common_fields": len(common_names),
            "only_in_reference": len(only_reference),
            "only_in_target": len(only_target),
            "type_mismatches": len(type_mismatches),
            "shape_mismatches": len(shape_mismatches),
            "compatible_fields": len(compatible_fields),
        },
    }
    if ctx is not None and hasattr(ctx.get("provenance"), "record_operation"):
        ctx["provenance"].record_operation(
            inputs={
                "products": [
                    f"schema:{comparison['reference_dataset']}",
                    f"schema:{comparison['target_dataset']}",
                ]
            },
            outputs={
                "products": [
                    f"schema_comparison:{comparison['reference']}:{comparison['target']}"
                ]
            },
        )
    return comparison


def _inspect_root_tree_schema(
    *,
    file_path: str,
    tree_name: str,
    dataset_name: str,
    dataset_record: dict[str, Any],
) -> dict[str, Any]:
    path = Path(file_path)
    if not _is_remote_path(file_path) and not path.exists():
        raise FileNotFoundError(f"ROOT input file does not exist: {file_path}")

    with uproot.open(file_path if _is_remote_path(file_path) else path) as root_file:
        try:
            tree = root_file[tree_name]
        except KeyError as exc:
            raise KeyError(
                f"Tree {tree_name!r} not found in ROOT file: {file_path}"
            ) from exc
        fields = [str(field) for field in list(tree.keys())]
        typenames = dict(tree.typenames())
        interpretations_attr = getattr(tree, "interpretations", None)
        interpretations = (
            dict(interpretations_attr())
            if callable(interpretations_attr)
            else dict(interpretations_attr or {})
        )
        physical_counters = _physical_counter_map(tree)
        field_details = {
            field: _field_detail(
                field,
                typenames=typenames,
                interpretations=interpretations,
                counter_for=physical_counters.get(field, []),
                counter_branch=_counter_branch_for(tree, field),
            )
            for field in fields
        }
        return {
            "version": "1.0",
            "kind": "schema_snapshot",
            "dataset": dataset_name,
            "tree": tree_name,
            "source_file": file_path,
            "entry_count": int(tree.num_entries),
            "fields": fields,
            "field_details": field_details,
            "physical_counters": physical_counters,
            "metadata": {
                **dict(dataset_record.get("meta") or {}),
                "eventtype": dataset_record.get("eventtype"),
                "group": dataset_record.get("group"),
            },
        }


def _field_detail(
    field: str,
    *,
    typenames: dict[str, Any],
    interpretations: dict[str, Any],
    counter_for: list[str],
    counter_branch: str | None,
) -> dict[str, Any]:
    typename = str(typenames.get(field, "unknown"))
    interpretation = str(interpretations.get(field, "unknown"))
    detail: dict[str, Any] = {
        "name": field,
        "type": typename,
        "primitive_type": _primitive_type(typename),
        "shape": _shape(typename, interpretation),
        "nullable": "unknown",
        "interpretation": interpretation,
    }
    if counter_for:
        detail["physical_role"] = "ttree_counter"
        detail["counter_for"] = list(counter_for)
    if counter_branch is not None:
        detail["counter_branch"] = counter_branch
    return detail


def _physical_counter_map(tree: Any) -> dict[str, list[str]]:
    counters: dict[str, list[str]] = {}
    for field in list(tree.keys()):
        counter = _counter_branch_for(tree, str(field))
        if counter is None:
            continue
        counters.setdefault(counter, []).append(str(field))
    return {name: sorted(fields) for name, fields in counters.items()}


def _counter_branch_for(tree: Any, field: str) -> str | None:
    try:
        branch = tree[field]
        leaves = branch.member("fLeaves")
    except Exception:
        return None
    for leaf in leaves:
        try:
            leaf_count = leaf.member("fLeafCount")
        except Exception:
            continue
        if leaf_count is None:
            continue
        try:
            name = leaf_count.member("fName")
        except Exception:
            continue
        if isinstance(name, str) and name:
            return name
    return None


def _primitive_type(type_name: str) -> str:
    cleaned = str(type_name).strip()
    if cleaned.endswith("[]"):
        cleaned = cleaned[:-2]
    return cleaned or "unknown"


def _shape(type_name: str, interpretation: str) -> str:
    if str(type_name).strip().endswith("[]"):
        return "jagged"
    if "AsJagged" in str(interpretation):
        return "jagged"
    return "scalar"


def _normalise_schema(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("kind") == "schema_snapshot":
        return value
    if isinstance(value, str | Path):
        with Path(value).open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict) and loaded.get("kind") == "schema_snapshot":
            return loaded
    raise ValueError(f"Malformed {label} schema input")


def _field_map(
    schema: dict[str, Any],
    *,
    counterpart_schema: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    details = schema.get("field_details")
    if isinstance(details, dict):
        return {
            str(name): dict(detail)
            for name, detail in details.items()
            if isinstance(detail, dict)
            and not _exclude_physical_counter(
                str(name),
                detail,
                counterpart_schema=counterpart_schema,
            )
        }
    awkward_type = schema.get("awkward_type")
    if isinstance(awkward_type, dict):
        return {
            str(name): {
                "name": str(name),
                "type": str(type_name),
                "primitive_type": _primitive_type(str(type_name)),
                "shape": _shape(str(type_name), ""),
            }
            for name, type_name in awkward_type.items()
        }
    raise ValueError("Malformed schema input: missing field_details or awkward_type")


def _exclude_physical_counter(
    name: str,
    detail: dict[str, Any],
    *,
    counterpart_schema: dict[str, Any] | None,
) -> bool:
    if detail.get("physical_role") != "ttree_counter":
        return False
    if counterpart_schema is None:
        return True
    counterpart_details = counterpart_schema.get("field_details")
    if not isinstance(counterpart_details, dict):
        return True
    counterpart = counterpart_details.get(name)
    if not isinstance(counterpart, dict):
        return True
    return counterpart.get("physical_role") == "ttree_counter"


def _schema_dataset_name(schema: dict[str, Any]) -> str:
    dataset = schema.get("dataset")
    if isinstance(dataset, str) and dataset:
        return dataset
    metadata = schema.get("metadata")
    if isinstance(metadata, dict):
        dataset_name = metadata.get("dataset_name")
        if isinstance(dataset_name, str) and dataset_name:
            return dataset_name
    return "unknown"


def _dataset_record(ctx: dict[str, Any], dataset_name: str) -> dict[str, Any]:
    datasets = dict(ctx.get("datasets") or {})
    try:
        record = datasets[dataset_name]
    except KeyError as exc:
        raise KeyError(f"Unknown dataset {dataset_name!r}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"Dataset {dataset_name!r} is malformed")
    return dict(record)


def _first_dataset_file(dataset: dict[str, Any], dataset_name: str) -> str:
    files = list(dataset.get("files") or [])
    if not files:
        raise ValueError(f"Dataset {dataset_name!r} has no files")
    return str(files[0])


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _is_remote_path(path: str) -> bool:
    return "://" in str(path)


__all__ = [
    "COMPARE_SCHEMAS_SPEC",
    "ROOT_TREE_SCHEMA_SPEC",
    "run_compare_schemas",
    "run_root_tree_schema",
]
