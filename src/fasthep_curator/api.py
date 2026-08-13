from __future__ import annotations

from pathlib import Path
from typing import Any

import uproot

from fasthep_curator.schema_format import (
    filter_schema_fields,
    format_schema_alignment,
    format_schema_table,
    format_schema_yaml_list,
)


def inspect_root_tree_schema(
    file: str | Path,
    *,
    tree: str = "Events",
    dataset: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    file_path = str(file)
    tree_name = _required_string(tree, "tree")
    path = Path(file_path)
    if not _is_remote_path(file_path) and not path.exists():
        raise FileNotFoundError(f"ROOT input file does not exist: {file_path}")

    try:
        root_file_ctx = uproot.open(file_path if _is_remote_path(file_path) else path)
    except Exception as exc:
        raise ValueError(f"Could not open ROOT file {file_path!r}: {exc}") from exc

    with root_file_ctx as root_file:
        try:
            root_tree = root_file[tree_name]
        except KeyError as exc:
            raise KeyError(
                f"Tree {tree_name!r} not found in ROOT file: {file_path}"
            ) from exc

        fields = [str(field) for field in list(root_tree.keys())]
        typenames = dict(root_tree.typenames())
        interpretations_attr = getattr(root_tree, "interpretations", None)
        interpretations = (
            dict(interpretations_attr())
            if callable(interpretations_attr)
            else dict(interpretations_attr or {})
        )
        physical_counters = _physical_counter_map(root_tree)
        field_details = {
            field: _field_detail(
                field,
                typenames=typenames,
                interpretations=interpretations,
                counter_for=physical_counters.get(field, []),
                counter_branch=_counter_branch_for(root_tree, field),
            )
            for field in fields
        }
        return {
            "version": "1.0",
            "kind": "schema_snapshot",
            "dataset": dataset or path.stem,
            "tree": tree_name,
            "source_file": file_path,
            "entry_count": int(root_tree.num_entries),
            "fields": fields,
            "field_details": field_details,
            "physical_counters": physical_counters,
            "metadata": dict(metadata or {}),
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
    primitive_type = _primitive_type(typename)
    detail: dict[str, Any] = {
        "name": field,
        "type": typename,
        "primitive_type": primitive_type,
        "logical_type": _logical_type(primitive_type),
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


def _logical_type(primitive_type: str) -> str:
    return {
        "bool": "bool",
        "Bool_t": "bool",
        "char": "int8",
        "Char_t": "int8",
        "signed char": "int8",
        "unsigned char": "uint8",
        "UChar_t": "uint8",
        "short": "int16",
        "Short_t": "int16",
        "unsigned short": "uint16",
        "UShort_t": "uint16",
        "int": "int32",
        "Int_t": "int32",
        "int32_t": "int32",
        "unsigned int": "uint32",
        "UInt_t": "uint32",
        "uint32_t": "uint32",
        "long": "int64",
        "Long64_t": "int64",
        "int64_t": "int64",
        "unsigned long": "uint64",
        "ULong64_t": "uint64",
        "uint64_t": "uint64",
        "float": "float32",
        "Float_t": "float32",
        "double": "float64",
        "Double_t": "float64",
    }.get(primitive_type, primitive_type)


def _shape(type_name: str, interpretation: str) -> str:
    if str(type_name).strip().endswith("[]"):
        return "jagged"
    if "AsJagged" in str(interpretation):
        return "jagged"
    return "scalar"


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _is_remote_path(path: str) -> bool:
    return "://" in str(path)


__all__ = [
    "filter_schema_fields",
    "format_schema_alignment",
    "format_schema_table",
    "format_schema_yaml_list",
    "inspect_root_tree_schema",
]
