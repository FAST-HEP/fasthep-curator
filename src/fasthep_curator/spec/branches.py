from __future__ import annotations


BRANCHES_OBSERVER_SPEC = {
    "name": "hep.branches",
    "kind": "observer",
    "version": "1.0",
    "input": {
        "name": "target",
        "kind": "event_stream",
        "required": True,
    },
    "params": {
        "path": {
            "type": "string",
            "required": False,
            "description": "Optional explicit output path for the report.",
        },
        "out": {
            "type": "string",
            "required": False,
            "description": "Optional logical output name.",
        },
        "format": {
            "type": "string",
            "required": False,
            "default": "json",
            "allowed": ["json"],
            "description": "Report serialization format.",
        },
    },
    "result": {
        "kind": "report",
        "default_output_family": "reports",
        "description": "Branch summary report.",
    },
}
