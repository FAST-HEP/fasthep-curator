from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import awkward as ak
from hepflow.model.defaults import DEFAULT_PRIMARY_STREAM_ID
from hepflow.model.io import OutputResult

SCHEMA_SNAPSHOT_OBSERVER_SPEC = {
    "name": "hep.schema_snapshot",
    "kind": "observer",
    "version": "1.0",
    "input": {
        "name": "target",
        "kind": "any",
        "required": True,
    },
    "params": {
        "out": {
            "type": "string",
            "required": False,
            "default": "schema",
        },
        "node_id": {
            "type": "string",
            "required": True,
        },
        "format": {
            "type": "string",
            "required": False,
            "default": "json",
            "allowed": ["json"],
        },
        "mode": {
            "type": "string",
            "required": False,
            "default": "partition",
            "allowed": ["partition", "first_partition"],
        },
    },
    "result": {
        "kind": "report",
        "default_output_family": "reports/schema",
        "description": "Runtime schema snapshot report.",
    },
}


def run_schema_snapshot_observer(
    target: Any,
    *,
    node_id: str,
    out: str = "schema",
    format: str = "json",
    mode: str = "partition",
    path: str | None = None,
    ctx: dict[str, Any] | None = None,
) -> OutputResult:
    if format != "json":
        raise ValueError(f"Unsupported schema snapshot format: {format!r}")
    if mode not in {"partition", "first_partition"}:
        raise ValueError(f"Unsupported schema snapshot mode: {mode!r}")

    ctx = dict(ctx or {})
    if mode == "first_partition" and not _is_first_partition(ctx):
        return OutputResult(
            kind="report",
            path="",
            format="json",
            metadata={
                "node_id": node_id,
                "skipped": True,
                "reason": "not first partition",
            },
        )

    inspected_target, envelope = _unwrap_for_schema(target)
    fields = _extract_fields(inspected_target)
    schema_info = _metadata_schema_info(inspected_target)
    awkward_info = (
        schema_info
        if schema_info is not None
        else _awkward_schema_info(inspected_target)
    )
    partition = dict(ctx.get("partition") or {})

    report = {
        "kind": "schema_snapshot",
        "node_id": node_id,
        "python_type": type(target).__name__,
        "inspected_python_type": type(inspected_target).__name__,
        "entry_count": awkward_info["entry_count"],
        "awkward_type": awkward_info["awkward_type"],
        "fields": fields,
        "envelope": envelope,
        "metadata": {
            "dataset_name": ctx.get("dataset_name"),
            "partition_id": partition.get("id"),
            "source": partition.get("source"),
            "file": partition.get("file"),
            "part": partition.get("part"),
            "start": partition.get("start"),
            "stop": partition.get("stop"),
        },
    }

    output_path = _resolve_output_path(
        path=path,
        out=out,
        node_id=node_id,
        ctx=ctx,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    return OutputResult(
        kind="report",
        path=str(output_path),
        format="json",
        metadata={
            "node_id": node_id,
            "fields": fields,
            "envelope": envelope,
        },
    )


def _unwrap_for_schema(target: Any) -> tuple[Any, dict[str, Any]]:
    if isinstance(target, dict) and len(target) == 1:
        stream_key = next(iter(target))
        if stream_key == DEFAULT_PRIMARY_STREAM_ID:
            return target[stream_key], {
                "unwrapped": True,
                "envelope_kind": "single_stream_mapping",
                "stream_key": DEFAULT_PRIMARY_STREAM_ID,
            }
        return target[stream_key], {
            "unwrapped": True,
            "envelope_kind": "single_mapping",
            "stream_key": str(stream_key),
        }

    return target, {"unwrapped": False}


def _extract_fields(target: Any) -> list[str]:
    if _is_metadata_schema(target):
        return [str(field) for field in target.fields]
    if hasattr(target, "fields"):
        return list(target.fields)
    if isinstance(target, dict):
        return list(target.keys())
    return []


def _metadata_schema_info(target: Any) -> dict[str, Any] | None:
    if not _is_metadata_schema(target):
        return None
    awkward_type = target.awkward_type
    if not isinstance(awkward_type, dict):
        awkward_type = {}
    return {
        "entry_count": getattr(target, "entry_count", None),
        "awkward_type": {str(key): str(value) for key, value in awkward_type.items()},
    }


def _is_metadata_schema(target: Any) -> bool:
    return (
        hasattr(target, "fields")
        and hasattr(target, "awkward_type")
        and not hasattr(target, "__getitem__")
    )


def _awkward_schema_info(target: Any) -> dict[str, Any]:
    entry_count = _safe_len(target)
    return {
        "entry_count": entry_count,
        "awkward_type": _top_level_awkward_type_map(target, entry_count=entry_count),
    }


def _top_level_awkward_type_map(
    target: Any,
    *,
    entry_count: int | None,
) -> dict[str, str] | None:
    fields = _extract_fields(target)
    if not fields:
        return None

    out: dict[str, str] = {}
    for field in fields:
        try:
            field_type = str(ak.type(target[field]))
        except Exception:
            continue
        out[str(field)] = _strip_entry_count_prefix(field_type, entry_count)
    return out or None


def _strip_entry_count_prefix(type_str: str, entry_count: int | None) -> str:
    if entry_count is None:
        return type_str
    prefix = f"{entry_count} * "
    if type_str.startswith(prefix):
        return type_str[len(prefix):]
    return type_str


def _safe_len(target: Any) -> int | None:
    try:
        return len(target)
    except Exception:
        return None


def _is_first_partition(ctx: dict[str, Any]) -> bool:
    partition = dict(ctx.get("partition") or {})
    dataset_names = list(ctx.get("dataset_names") or [])
    dataset_name = ctx.get("dataset_name")
    return (
        partition.get("part") == "0_0"
        and bool(dataset_names)
        and dataset_name == dataset_names[0]
    )


def _resolve_output_path(
    *,
    path: str | None,
    out: str,
    node_id: str,
    ctx: dict[str, Any],
) -> Path:
    if path:
        return Path(path)

    outdir = Path(ctx.get("outdir") or ".")
    safe_node_id = node_id.replace(".", "_").replace("/", "_")
    partition_id = dict(ctx.get("partition") or {}).get("id")
    if partition_id:
        return (
            outdir
            / "reports"
            / "schema"
            / out
            / safe_node_id
            / f"{partition_id}.json"
        )
    return outdir / "reports" / "schema" / out / f"{safe_node_id}.json"
