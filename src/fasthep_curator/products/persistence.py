"""Persistence callables for curator's JSON products (fasthep-flow ``persistence.md``).

Schema snapshots and schema comparisons are plain data (a dict, or a list of dicts when
partition products were merged). They are stored as one JSON payload, ``product.json``;
anything that is not data is refused.
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
    kind = identity.get("product_kind", "schema product")
    if not isinstance(value, dict | list):
        raise ValueError(
            f"{kind}: a schema product is a dict or a list of dicts, not "
            f"{type(value).__name__}"
        )
    try:
        text = json.dumps({"format_version": FORMAT_VERSION, "value": value})
    except TypeError as exc:
        raise ValueError(f"{kind}: schema product is not plain data: {exc}") from exc
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
    document = json.loads(Path(payloads[0]).read_text(encoding="utf-8"))
    if document.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"schema product format_version {document.get('format_version')!r} is not "
            f"{FORMAT_VERSION!r}"
        )
    return document["value"]
