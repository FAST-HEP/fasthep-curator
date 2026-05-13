from __future__ import annotations

import contextlib
import json
import traceback
from pathlib import Path
from typing import Any

from hepflow.model.hooks import ExecutionHook


def abbreviate_list(items: list[Any], *, max_items: int = 20) -> list[Any]:
    if len(items) <= max_items:
        return items
    return [*items[:max_items], f"... +{len(items) - max_items} more"]


def describe_runtime_value(value: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "python_type": type(value).__name__,
    }

    if isinstance(value, dict):
        summary["keys"] = [str(key) for key in value]

    fields = getattr(value, "fields", None)
    if fields is not None:
        try:
            summary["fields"] = [str(field) for field in fields]
        except Exception:
            summary["fields"] = "<unavailable>"

    with contextlib.suppress(Exception):
        summary["length"] = len(value)

    return summary


def build_node_error_context(
    *,
    node,
    inputs: dict[str, Any],
    ctx: dict[str, Any],
    exc: BaseException,
) -> dict[str, Any]:
    partition = ctx.get("partition") or {}
    if not isinstance(partition, dict):
        partition = {}

    return {
        "node_id": node.id,
        "role": node.role,
        "impl": node.impl,
        "exception": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
        "traceback": traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
        ),
        "partition": {
            key: partition.get(key)
            for key in ("id", "dataset", "file", "part", "start", "stop", "source")
            if key in partition
        },
        "inputs": {
            input_name: describe_runtime_value(value)
            for input_name, value in inputs.items()
        },
    }


def write_node_error_report(
    *,
    error_context: dict[str, Any],
    ctx: dict[str, Any],
    out: str = "errors",
) -> str:
    outdir = Path(ctx.get("outdir") or ".")
    node_id = str(error_context.get("node_id") or "unknown_node")
    safe_node_id = node_id.replace(".", "_").replace("/", "_")
    partition = error_context.get("partition") or {}
    partition_id = partition.get("id") if isinstance(partition, dict) else None

    if partition_id:
        path = (
            outdir
            / "reports"
            / out
            / safe_node_id
            / f"{partition_id}.json"
        )
    else:
        path = outdir / "reports" / out / f"{safe_node_id}.json"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(error_context, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return str(path)


def format_node_error_context(
    error_ctx: dict[str, Any],
    *,
    error_path: str | None = None,
    max_console_fields: int = 20,
) -> str:
    lines = [f"Runtime error in node {error_ctx.get('node_id')}"]
    lines.append(f"  role: {error_ctx.get('role')}")
    lines.append(f"  impl: {error_ctx.get('impl')}")

    exception = dict(error_ctx.get("exception") or {})
    lines.append(
        "  exception: "
        f"{exception.get('type')}: {exception.get('message')}"
    )

    partition = dict(error_ctx.get("partition") or {})
    if partition:
        lines.append("  partition:")
        for key in ("id", "dataset", "file", "part", "start", "stop", "source"):
            if key in partition:
                lines.append(f"    {key}: {partition[key]}")

    inputs = dict(error_ctx.get("inputs") or {})
    if inputs:
        lines.append("  inputs:")
        for input_name, summary in inputs.items():
            lines.append(f"    {input_name}:")
            if not isinstance(summary, dict):
                lines.append(f"      summary: {summary}")
                continue
            lines.append(f"      python_type: {summary.get('python_type')}")
            if "length" in summary:
                lines.append(f"      length: {summary['length']}")
            if "fields" in summary:
                fields = summary["fields"]
                if isinstance(fields, list):
                    fields = abbreviate_list(fields, max_items=max_console_fields)
                lines.append(f"      fields: {fields}")
            if "keys" in summary:
                keys = summary["keys"]
                if isinstance(keys, list):
                    keys = abbreviate_list(keys, max_items=max_console_fields)
                lines.append(f"      keys: {keys}")

    if error_path:
        lines.append("")
        lines.append("Full error context written to:")
        lines.append(f"  {error_path}")

    return "\n".join(lines)


class ErrorReportHook(ExecutionHook):
    name = "hep.error_report"

    def __init__(
        self,
        *,
        max_console_fields: int = 20,
        out: str = "errors",
    ) -> None:
        self.max_console_fields = int(max_console_fields)
        self.out = str(out)

    def on_node_error(
        self,
        *,
        node,
        inputs: dict[str, Any],
        ctx: dict[str, Any],
        exc: BaseException,
    ) -> None:
        error_ctx = build_node_error_context(
            node=node,
            inputs=inputs,
            ctx=ctx,
            exc=exc,
        )
        ctx.setdefault("errors", []).append(error_ctx)
        error_path: str | None = None
        try:
            error_path = write_node_error_report(
                error_context=error_ctx,
                ctx=ctx,
                out=self.out,
            )
        except Exception as report_exc:
            print(f"Failed to write error report: {report_exc}")
        print(
            format_node_error_context(
                error_ctx,
                error_path=error_path,
                max_console_fields=self.max_console_fields,
            )
        )
