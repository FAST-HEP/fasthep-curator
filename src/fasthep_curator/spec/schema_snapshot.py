from __future__ import annotations

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
