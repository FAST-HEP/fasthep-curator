from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import awkward as ak
from hepflow.model.io import OutputResult


def run_branches_observer(
    target: Any,
    *,
    path: str | None = None,
    out: str | None = None,
    format: str = "json",
    ctx: dict[str, Any] | None = None,
) -> OutputResult:
    if format != "json":
        raise ValueError(f"Unsupported branches observer format: {format!r}")

    array = _normalise_target(target)

    fields = list(array.fields)
    report = {
        "kind": "branches",
        "n_fields": len(fields),
        "fields": fields,
    }

    output_path = _resolve_output_path(path=path, out=out, format=format)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    return OutputResult(
        kind="report",
        path=str(output_path),
        format=format,
        metadata={
            "fields": fields,
            "n_fields": len(fields),
        },
    )


def _normalise_target(target: Any) -> ak.Array:
    if isinstance(target, ak.Array):
        return target

    if isinstance(target, dict):
        return ak.Array(target)

    raise TypeError(
        "branches observer expects an awkward.Array or dict[str, array-like]"
    )


def _resolve_output_path(
    *,
    path: str | None,
    out: str | None,
    format: str,
) -> Path:
    if path:
        return Path(path)

    stem = out or "branches_report"
    return Path("reports") / f"{stem}.{format}"
