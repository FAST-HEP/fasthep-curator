"""Persistence callables for curator's JSON products (fasthep-flow ``persistence.md``).

Schema snapshots and schema comparisons are plain data (a dict, or a list of dicts when
partition products were merged). They are stored as one JSON payload, ``product.json``.
Whatever JSON would change on the way (tuples, non-string keys, non-finite numbers) or
cannot store is refused, naming the producer, output and kind.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from hepflow.model.persistence import SavedPayload, SaveOutcome

FORMAT_VERSION = "1"
PAYLOAD = "product.json"


def save_json_value(
    value: Any,
    *,
    root: Path,
    params: dict[str, Any],
    identity: dict[str, Any],
) -> SaveOutcome:
    """Write a schema product (dict or list of dicts) as ``product.json`` below ``root``."""
    del params
    who = _who(identity)
    if not isinstance(value, dict | list):
        raise ValueError(
            f"{who}: a schema product is a dict or a list of dicts, not "
            f"{type(value).__name__}"
        )
    if isinstance(value, list) and not all(isinstance(item, dict) for item in value):
        raise ValueError(
            f"{who}: a schema product that is a list must be a list of dicts"
        )
    try:
        text = json.dumps(
            {"format_version": FORMAT_VERSION, "value": value}, allow_nan=False
        )
        unchanged = json.loads(text)["value"] == value
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{who}: schema product is not plain JSON data: {exc}"
        ) from exc
    if not unchanged:
        raise ValueError(
            f"{who}: JSON would change this schema product (tuples and non-string "
            "dict keys are refused rather than converted)"
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / PAYLOAD).write_text(text, encoding="utf-8")
    return SaveOutcome(payloads=(SavedPayload(PAYLOAD, role="data"),))


def load_json_value(
    root: Path,
    payloads: Sequence[Path],
    *,
    params: dict[str, Any],
    variant: str | None,
    locator: str | None,
) -> Any:
    """Read the value back from ``product.json``."""
    del root, params, variant, locator
    path = Path(payloads[0])
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{PAYLOAD} ({path}) is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or "value" not in document:
        raise ValueError(f"{PAYLOAD} ({path}) is not a schema product payload")
    if document.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"{PAYLOAD} ({path}) format_version {document.get('format_version')!r} is "
            f"not {FORMAT_VERSION!r}"
        )
    return document["value"]


def _who(identity: dict[str, Any]) -> str:
    return (
        f"{identity.get('product_kind', 'schema product')} "
        f"(producer {identity.get('producer_node')!r}, "
        f"output {identity.get('output_name')!r}, "
        f"dataset {identity.get('dataset_name')!r})"
    )
