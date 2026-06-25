from __future__ import annotations

import json
import warnings

import awkward as ak
import pytest
from hepflow.compiler.data_flow import context_symbols_from_plan
from hepflow.model.plan import ExecutionNode, ExecutionPartition, ExecutionPlan
from hepflow.runtime.hooks.manager import HookManager

from fasthep_curator.hooks.dataset_context import DatasetContextHook
from fasthep_curator.hooks.error_report import ErrorReportHook
from fasthep_curator.hooks.warning_capture import WarningCaptureHook

CURATOR_HOOK_REGISTRY = {
    "hooks": {
        "hep.dataset_context": {
            "spec": "fasthep_curator.hooks.dataset_context:DATASET_CONTEXT_HOOK_SPEC",
            "impl": "fasthep_curator.hooks.dataset_context:DatasetContextHook",
        },
        "hep.error_report": {
            "spec": "fasthep_curator.hooks.error_report:ERROR_REPORT_HOOK_SPEC",
            "impl": "fasthep_curator.hooks.error_report:ErrorReportHook",
        },
        "hep.warning_capture": {
            "spec": "fasthep_curator.hooks.warning_capture:WARNING_CAPTURE_HOOK_SPEC",
            "impl": "fasthep_curator.hooks.warning_capture:WarningCaptureHook",
        },
    }
}


def test_dataset_context_hook_populates_partition_context() -> None:
    partition = ExecutionPartition(
        id="events__dy__0",
        dataset="dy",
        file="dy.root",
        source="events",
        part="0",
        start=0,
        stop=10,
    )
    ctx = {
        "datasets": {
            "dy": {
                "name": "dy",
                "eventtype": "data",
                "group": "zjets",
                "meta": {"xs": 1.5},
            }
        }
    }

    DatasetContextHook().partition_start(partition=partition, ctx=ctx)

    assert ctx["partition"]["id"] == "events__dy__0"
    assert ctx["dataset_name"] == "dy"
    assert ctx["dataset_is_data"] is True
    assert ctx["dataset_group"] == "zjets"
    assert ctx["dataset_xs"] == 1.5


def test_error_report_hook_writes_report(tmp_path, capsys) -> None:
    node = ExecutionNode(
        id="stage.Bad",
        graph_node_id="stage.Bad",
        role="transform",
        impl="hep.define",
        outputs={"stream": "event_stream"},
    )
    hook = ErrorReportHook(max_console_fields=3)

    hook.on_node_error(
        node=node,
        inputs={"stream": ak.Array({f"field_{index}": [index] for index in range(5)})},
        ctx={
            "outdir": str(tmp_path),
            "partition": {"id": "events__dy__0", "file": "dy.root"},
        },
        exc=NameError("missing"),
    )

    output = capsys.readouterr().out
    assert "Runtime error in node stage.Bad" in output
    report_path = (
        tmp_path
        / "reports"
        / "diagnostics"
        / "errors"
        / "stage_Bad"
        / "events__dy__0.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["node_id"] == "stage.Bad"
    assert report["exception"]["type"] == "NameError"


def test_warning_capture_hook_records_warning() -> None:
    hook = WarningCaptureHook()
    node = ExecutionNode(
        id="stage.Warn",
        graph_node_id="stage.Warn",
        role="transform",
        impl="hep.warn",
    )
    ctx = {
        "dataset_name": "dy",
        "partition": {"id": "events__dy__0", "dataset": "dy"},
    }

    with hook.around_node(node=node, inputs={}, ctx=ctx):
        warnings.warn("hello", UserWarning, stacklevel=2)

    assert len(hook.records) == 1
    assert hook.records[0]["message"] == "hello"
    assert hook.records[0]["partition_id"] == "events__dy__0"
    assert ctx["_warnings"] == hook.records


def test_hook_manager_loads_curator_hooks_and_validates_events() -> None:
    plan = ExecutionPlan(
        registry=CURATOR_HOOK_REGISTRY,
        execution_hooks=[
            {"kind": "hep.dataset_context", "events": ["partition_start"]},
            {"kind": "hep.warning_capture", "events": ["around_node"]},
        ],
    )

    manager = HookManager.from_plan(plan)

    assert len(manager.hooks) == 2

    invalid = ExecutionPlan(
        registry=CURATOR_HOOK_REGISTRY,
        execution_hooks=[
            {"kind": "hep.dataset_context", "events": ["before_node"]},
        ],
    )
    with pytest.raises(
        ValueError,
        match=r"Hook hep.dataset_context does not support event before_node",
    ):
        HookManager.from_plan(invalid)


def test_dataset_context_results_are_data_flow_context_symbols() -> None:
    plan = ExecutionPlan(
        registry=CURATOR_HOOK_REGISTRY,
        execution_hooks=[
            {"kind": "hep.dataset_context", "events": ["partition_start"]},
        ],
    )

    symbols = context_symbols_from_plan(plan)

    assert "dataset_name" in symbols
    assert "dataset_is_data" in symbols
    assert "dataset_xs" in symbols
