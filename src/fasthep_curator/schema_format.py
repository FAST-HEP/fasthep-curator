from __future__ import annotations

import fnmatch
from typing import Any


def filter_schema_fields(
    schema: dict[str, Any],
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    fields = [str(field) for field in list(schema.get("fields") or [])]
    includes = [str(pattern) for pattern in list(include or [])]
    excludes = [str(pattern) for pattern in list(exclude or [])]

    if includes:
        selected: list[str] = []
        seen: set[str] = set()
        for pattern in includes:
            for field in fields:
                if field in seen:
                    continue
                if fnmatch.fnmatchcase(field, pattern):
                    selected.append(field)
                    seen.add(field)
    else:
        selected = list(fields)

    if not excludes:
        return selected

    return [
        field
        for field in selected
        if not any(fnmatch.fnmatchcase(field, pattern) for pattern in excludes)
    ]


def format_schema_table(
    schema: dict[str, Any],
    *,
    fields: list[str] | None = None,
) -> str:
    selected = fields if fields is not None else filter_schema_fields(schema)
    rows = [
        (
            field,
            _logical_type(schema, field),
            _shape(schema, field),
            _physical_type(schema, field),
        )
        for field in selected
    ]
    headers = ("Field", "Type", "Shape", "ROOT Type")
    widths = [
        max([len(headers[index]), *(len(row[index]) for row in rows)])
        for index in range(len(headers))
    ]
    lines = [_format_row(headers, widths), _format_row(tuple("-" * w for w in widths), widths)]
    lines.extend(_format_row(row, widths) for row in rows)
    return "\n".join(lines)


def format_schema_yaml_list(
    schema: dict[str, Any],
    *,
    fields: list[str] | None = None,
) -> str:
    selected = fields if fields is not None else filter_schema_fields(schema)
    return "\n".join(f"- {field}" for field in selected)


def format_schema_alignment(
    schema: dict[str, Any],
    *,
    fields: list[str] | None = None,
) -> str:
    selected = fields if fields is not None else filter_schema_fields(schema)
    lines = ["version: 1", "fields:"]
    for field in selected:
        lines.append(f"  {field}:")
        lines.append(f"    dtype: {_logical_type(schema, field)}")
    return "\n".join(lines)


def _format_row(row: tuple[str, ...], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))


def _detail(schema: dict[str, Any], field: str) -> dict[str, Any]:
    details = schema.get("field_details")
    if not isinstance(details, dict):
        return {}
    detail = details.get(field)
    return dict(detail) if isinstance(detail, dict) else {}


def _logical_type(schema: dict[str, Any], field: str) -> str:
    detail = _detail(schema, field)
    return str(detail.get("logical_type") or detail.get("primitive_type") or "unknown")


def _physical_type(schema: dict[str, Any], field: str) -> str:
    return str(_detail(schema, field).get("type") or "unknown")


def _shape(schema: dict[str, Any], field: str) -> str:
    return str(_detail(schema, field).get("shape") or "unknown")


__all__ = [
    "filter_schema_fields",
    "format_schema_alignment",
    "format_schema_table",
    "format_schema_yaml_list",
]
