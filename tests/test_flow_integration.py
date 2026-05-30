from __future__ import annotations

from pathlib import Path

import yaml
from hepflow.api import compile_author_file


def test_compile_merges_curator_registry_and_profiles(tmp_path: Path) -> None:
    author_path = tmp_path / "author.yaml"
    author = {
        "version": "1.0",
        "use": {
            "profiles": [
                "registry",
                "fasthep_curator:registry",
                "fasthep_curator:default_context",
                "fasthep_curator:runtime_diagnostics",
            ],
        },
        "data": {
            "datasets": [],
            "defaults": {},
        },
        "sources": {
            "events": {
                "kind": "root_tree",
                "tree": "events",
                "stream_type": "event_stream",
            },
        },
        "observers": [
            {
                "kind": "hep.schema_snapshot",
                "at": "read.events",
                "params": {"out": "schema"},
            }
        ],
        "analysis": {"stages": []},
    }
    author_path.write_text(yaml.safe_dump(author, sort_keys=False), encoding="utf-8")

    plan = compile_author_file(author_path, outdir=tmp_path / "build")

    assert plan.registry["observers"]["hep.schema_snapshot"]["impl"] == (
        "fasthep_curator.observers.schema_snapshot:run_schema_snapshot_observer"
    )
    assert "hep.dataset_context" in plan.registry["hooks"]
    assert {hook["kind"] for hook in plan.execution_hooks} == {
        "hep.dataset_context",
        "hep.error_report",
        "hep.warning_capture",
    }
