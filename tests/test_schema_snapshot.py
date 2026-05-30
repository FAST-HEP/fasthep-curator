from __future__ import annotations

import json
from pathlib import Path

import awkward as ak

from fasthep_curator.observers.schema_snapshot import run_schema_snapshot_observer


def test_schema_snapshot_observer_writes_partition_report(tmp_path: Path) -> None:
    target = {"events": ak.Array({"Muon_Pt": [[1.0]], "NIsoMuon": [1]})}

    result = run_schema_snapshot_observer(
        target,
        node_id="stage.BasicVars",
        out="schema",
        ctx={
            "outdir": str(tmp_path),
            "dataset_name": "dy",
            "partition": {
                "id": "events__dy__0",
                "source": "events",
                "file": "dy.root",
                "part": "0_0",
                "start": 0,
                "stop": 10,
            },
        },
    )

    expected = (
        tmp_path
        / "reports"
        / "schema"
        / "schema"
        / "stage_BasicVars"
        / "events__dy__0.json"
    )
    assert result.path == str(expected)
    report = json.loads(expected.read_text(encoding="utf-8"))
    assert report["fields"] == ["Muon_Pt", "NIsoMuon"]
    assert report["envelope"]["unwrapped"] is True
    assert report["metadata"]["file"] == "dy.root"
    assert report["metadata"]["start"] == 0
    assert report["metadata"]["stop"] == 10
    assert report["entry_count"] == 1
    assert isinstance(report["awkward_type"], dict)
    assert "awkward_type_full" not in report


def test_schema_snapshot_observer_keeps_non_envelope_dict_shape(tmp_path: Path) -> None:
    result = run_schema_snapshot_observer(
        {"a": 1, "b": 2},
        node_id="observe.dict",
        out="schema",
        ctx={"outdir": str(tmp_path)},
    )

    report = json.loads(Path(result.path).read_text(encoding="utf-8"))
    assert report["fields"] == ["a", "b"]
    assert report["envelope"]["unwrapped"] is False


def test_schema_snapshot_first_partition_mode_skips_later_partitions(tmp_path: Path) -> None:
    result = run_schema_snapshot_observer(
        ak.Array({"x": [1]}),
        node_id="read.events",
        mode="first_partition",
        ctx={
            "outdir": str(tmp_path),
            "dataset_names": ["dy"],
            "dataset_name": "dy",
            "partition": {"part": "0_1"},
        },
    )

    assert result.metadata["skipped"] is True
    assert not list(tmp_path.rglob("*.json"))
