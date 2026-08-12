from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

import awkward as ak
import numpy as np
import pytest
import uproot

from fasthep_curator.operations.schema_validation import (
    run_compare_schemas,
    run_root_tree_schema,
)
from fasthep_curator.products import (
    materialize_schema_comparison_product,
    materialize_schema_product,
)


def test_root_tree_schema_full_mode_includes_unused_branch(tmp_path: Path) -> None:
    root_path = tmp_path / "events.root"
    with uproot.recreate(root_path) as root_file:
        root_file["Events"] = {
            "pt": [1.0, 2.0],
            "unused_branch": [3, 4],
        }

    schema = run_root_tree_schema(
        dataset="sample",
        ctx={
            "datasets": {
                "sample": {
                    "name": "sample",
                    "files": [str(root_path)],
                    "meta": {"implementation": "fasthep"},
                }
            }
        },
    )

    assert schema["kind"] == "schema_snapshot"
    assert schema["dataset"] == "sample"
    assert schema["entry_count"] == 2
    assert "unused_branch" in schema["fields"]
    assert schema["field_details"]["unused_branch"]["shape"] == "scalar"
    assert schema["metadata"]["implementation"] == "fasthep"


def test_root_tree_schema_rejects_non_full_mode() -> None:
    with pytest.raises(ValueError, match="full_schema=true"):
        run_root_tree_schema(dataset="sample", full_schema=False, ctx={"datasets": {}})


def test_root_tree_schema_marks_physical_jagged_counters(tmp_path: Path) -> None:
    root_path = tmp_path / "events.root"
    with uproot.recreate(root_path) as root_file:
        root_file.mktree("Events", {
            "Muon_pt": ak.Array([[1.0, 2.0], [], [3.0]]),
            "nReal": np.array([10, 20, 30], dtype=np.int32),
        })

    schema = run_root_tree_schema(
        dataset="sample",
        ctx={
            "datasets": {
                "sample": {
                    "name": "sample",
                    "files": [str(root_path)],
                }
            }
        },
    )

    assert "nMuon_pt" in schema["fields"]
    assert schema["physical_counters"] == {"nMuon_pt": ["Muon_pt"]}
    assert schema["field_details"]["nMuon_pt"]["physical_role"] == "ttree_counter"
    assert schema["field_details"]["nMuon_pt"]["counter_for"] == ["Muon_pt"]
    assert schema["field_details"]["Muon_pt"]["counter_branch"] == "nMuon_pt"
    assert "physical_role" not in schema["field_details"]["nReal"]


def test_compare_schemas_ignores_physical_counters_but_keeps_real_n_fields() -> None:
    reference = _schema(
        "legacy",
        {
            "Muon_pt": {"primitive_type": "double", "shape": "jagged"},
            "nReal": {"primitive_type": "int32_t", "shape": "scalar"},
        },
    )
    target = _schema(
        "fasthep",
        {
            "Muon_pt": {"primitive_type": "double", "shape": "jagged"},
            "nMuon_pt": {
                "primitive_type": "int32_t",
                "shape": "scalar",
                "physical_role": "ttree_counter",
                "counter_for": ["Muon_pt"],
            },
            "nReal": {"primitive_type": "int32_t", "shape": "scalar"},
        },
    )

    comparison = run_compare_schemas(reference=reference, target=target)

    assert comparison["common_fields"] == ["Muon_pt", "nReal"]
    assert comparison["only_in_target"] == []
    assert comparison["compatible_fields"] == ["Muon_pt", "nReal"]
    assert comparison["summary"]["target_fields"] == 2


def test_compare_schemas_keeps_counter_branch_when_counterpart_is_logical() -> None:
    reference = _schema(
        "legacy",
        {
            "Muon_pt": {"primitive_type": "double", "shape": "jagged"},
            "nMuon": {
                "primitive_type": "int32_t",
                "shape": "scalar",
                "physical_role": "ttree_counter",
                "counter_for": ["Muon_pt"],
            },
        },
    )
    target = _schema(
        "fasthep",
        {
            "Muon_pt": {"primitive_type": "double", "shape": "jagged"},
            "nMuon": {"primitive_type": "int32_t", "shape": "scalar"},
        },
    )

    comparison = run_compare_schemas(reference=reference, target=target)

    assert comparison["common_fields"] == ["Muon_pt", "nMuon"]
    assert comparison["compatible_fields"] == ["Muon_pt", "nMuon"]
    assert comparison["only_in_reference"] == []
    assert comparison["only_in_target"] == []


def test_compare_schemas_reports_diagnostic_differences() -> None:
    reference = _schema(
        "legacy",
        {
            "shared": {"primitive_type": "float", "shape": "scalar"},
            "type_diff": {"primitive_type": "int32", "shape": "scalar"},
            "shape_diff": {"primitive_type": "float", "shape": "scalar"},
            "only_reference": {"primitive_type": "bool", "shape": "scalar"},
        },
    )
    target = _schema(
        "fasthep",
        {
            "shared": {"primitive_type": "float", "shape": "scalar"},
            "type_diff": {"primitive_type": "float", "shape": "scalar"},
            "shape_diff": {"primitive_type": "float", "shape": "jagged"},
            "only_target": {"primitive_type": "uint64", "shape": "scalar"},
        },
    )

    comparison = run_compare_schemas(reference=reference, target=target)

    assert comparison["kind"] == "schema_comparison"
    assert comparison["common_fields"] == ["shape_diff", "shared", "type_diff"]
    assert comparison["only_in_reference"] == ["only_reference"]
    assert comparison["only_in_target"] == ["only_target"]
    assert comparison["compatible_fields"] == ["shared"]
    assert comparison["type_mismatches"] == [
        {"field": "type_diff", "reference": "int32", "target": "float"}
    ]
    assert comparison["shape_mismatches"] == [
        {"field": "shape_diff", "reference": "scalar", "target": "jagged"}
    ]
    assert comparison["summary"] == {
        "reference_fields": 4,
        "target_fields": 4,
        "common_fields": 3,
        "only_in_reference": 1,
        "only_in_target": 1,
        "type_mismatches": 1,
        "shape_mismatches": 1,
        "compatible_fields": 1,
    }


def test_compare_schemas_differences_do_not_fail() -> None:
    comparison = run_compare_schemas(
        reference=_schema("legacy", {"x": {"primitive_type": "int", "shape": "scalar"}}),
        target=_schema("fasthep", {"y": {"primitive_type": "float", "shape": "jagged"}}),
    )

    assert comparison["summary"]["only_in_reference"] == 1
    assert comparison["summary"]["only_in_target"] == 1


def test_compare_schemas_malformed_input_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Malformed reference schema input"):
        run_compare_schemas(reference={"kind": "not_schema"}, target=_schema("target", {}))


def test_schema_products_materialize_structured_json(tmp_path: Path) -> None:
    class Node:
        id = "stage.SchemaFastHEPMC"
        meta: ClassVar[dict[str, str]] = {"stage_id": "SchemaFastHEPMC"}
        params: ClassVar[dict[str, Any]] = {}

    schema = _schema("fasthep_mc", {"pt": {"primitive_type": "float", "shape": "scalar"}})
    result = materialize_schema_product(
        schema,
        node=Node(),
        output_name="schema",
        outdir=tmp_path,
    )

    path = tmp_path / result["items"][0]["path"]
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["kind"] == "schema_snapshot"
    assert loaded["dataset"] == "fasthep_mc"
    assert (tmp_path / "artifacts" / "schemas" / "manifest.json").exists()


def test_schema_comparison_products_materialize_structured_json(tmp_path: Path) -> None:
    class Node:
        id = "stage.CompareMCSchemas"
        meta: ClassVar[dict[str, str]] = {"stage_id": "CompareMCSchemas"}
        params: ClassVar[dict[str, Any]] = {}

    comparison = run_compare_schemas(
        reference=_schema("legacy_mc", {}),
        target=_schema("fasthep_mc", {}),
    )
    result = materialize_schema_comparison_product(
        comparison,
        node=Node(),
        output_name="comparison",
        outdir=tmp_path,
    )

    path = tmp_path / result["items"][0]["path"]
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["kind"] == "schema_comparison"
    assert loaded["reference_dataset"] == "legacy_mc"
    assert loaded["target_dataset"] == "fasthep_mc"
    assert (tmp_path / "artifacts" / "comparisons" / "manifest.json").exists()


def _schema(dataset: str, fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "schema_snapshot",
        "dataset": dataset,
        "fields": list(fields),
        "field_details": {
            name: {"name": name, "type": "test", **detail}
            for name, detail in fields.items()
        },
    }
