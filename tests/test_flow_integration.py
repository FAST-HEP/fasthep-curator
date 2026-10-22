from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from hepflow.api import compile_workflow_file
from hepflow.build_layout import BuildPaths
from hepflow.compiler.compile_hooks import CompileHookContext
from hepflow.compiler.hooks.runner import run_phase_hooks


def test_compile_merges_curator_registry_and_profiles(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.yaml"
    workflow = {
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
    workflow_path.write_text(
        yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8"
    )

    plan = compile_workflow_file(workflow_path, outdir=tmp_path / "build")

    assert plan.registry["observers"]["hep.schema_snapshot"]["impl"] == (
        "fasthep_curator.observers.schema_snapshot:run_schema_snapshot_observer"
    )
    assert "hep.dataset_context" in plan.registry["hooks"]
    assert {hook["kind"] for hook in plan.execution_hooks} == {
        "hep.dataset_context",
        "hep.error_report",
        "hep.warning_capture",
    }


def _metadata_workflow(tmp_path: Path) -> Path:
    workflow_path = tmp_path / "workflow.yaml"
    workflow = {
        "version": "1.0",
        "use": {"profiles": ["registry", "fasthep_curator:registry"]},
        "data": {
            "datasets": [
                {
                    "name": "ds",
                    "files": [str(tmp_path / "missing.root")],
                    "nevents": 50,
                }
            ],
            "defaults": {},
        },
        "sources": {
            "events": {
                "kind": "root_tree",
                "tree": "events",
                "stream_type": "event_stream",
            },
        },
        "analysis": {"stages": []},
    }
    workflow_path.write_text(
        yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8"
    )
    return workflow_path


def test_compile_takes_total_entries_from_nevents_without_opening_files(
    tmp_path: Path,
) -> None:
    workflow_path = _metadata_workflow(tmp_path)

    compile_workflow_file(workflow_path, outdir=tmp_path / "build")

    metadata = json.loads(
        (tmp_path / "build" / "compile" / "dataset_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["datasets"]["ds"] == {
        "files": {},
        "total_entries": 50,
        "total_entries_origin": "nevents",
    }


def test_registry_params_reach_the_metadata_hook(tmp_path: Path) -> None:
    plan = compile_workflow_file(
        _metadata_workflow(tmp_path), outdir=tmp_path / "build"
    )
    ctx = CompileHookContext(
        normalized={"sources": {"events": {"kind": "root_tree", "tree": "events"}}},
        plan_context=dict(plan.context),
        build_paths=BuildPaths(root=tmp_path / "build"),
    )

    def run(params: dict[str, Any]) -> dict[str, Any]:
        registry = copy.deepcopy(plan.registry)
        registry["compile_hooks"]["dataset_metadata.root_tree"]["params"] = params
        return run_phase_hooks(registry=registry, context=ctx, when="after_datasets")

    # Reading is forced by ``total_entries_source: null``; the file is missing.
    with pytest.raises(RuntimeError, match="Failed to inspect ROOT dataset metadata"):
        run({"total_entries_source": None})
    with pytest.raises(RuntimeError, match="total_entry_source"):
        run({"total_entry_source": "nevents"})
    assert run({})["dataset_metadata"]["datasets"]["ds"]["total_entries"] == 50
