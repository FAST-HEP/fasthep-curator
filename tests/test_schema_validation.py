from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

import awkward as ak
import numpy as np
import pytest
import uproot

from fasthep_curator.api import inspect_root_tree_schema
from fasthep_curator.operations.schema_validation import (
    run_compare_schemas,
    run_root_tree_schema,
)
from fasthep_curator.products import (
    materialize_schema_comparison_product,
    materialize_schema_product,
)
from fasthep_curator.schema_format import (
    filter_schema_fields,
    format_schema_alignment,
    format_schema_table,
    format_schema_yaml_list,
)


def test_api_inspects_root_tree_schema(tmp_path: Path) -> None:
    root_path = _schema_fixture(tmp_path)

    schema = inspect_root_tree_schema(root_path, tree="Events", dataset="sample")

    assert schema["kind"] == "schema_snapshot"
    assert schema["dataset"] == "sample"
    assert schema["tree"] == "Events"
    assert schema["source_file"] == str(root_path)
    assert schema["entry_count"] == 3
    assert schema["fields"][:6] == [
        "nGenJetAK8_eta",
        "GenJetAK8_eta",
        "nGenJetAK8_hadronFlavour",
        "GenJetAK8_hadronFlavour",
        "GenMET_pt",
        "nMuon_pt",
    ]
    assert schema["field_details"]["GenMET_pt"]["logical_type"] == "float32"
    assert schema["field_details"]["GenMET_pt"]["shape"] == "scalar"
    assert schema["field_details"]["Muon_pt"]["logical_type"] == "float32"
    assert schema["field_details"]["Muon_pt"]["shape"] == "jagged"


def test_root_tree_schema_operation_reuses_api_schema(tmp_path: Path) -> None:
    root_path = _schema_fixture(tmp_path)

    operation_schema = run_root_tree_schema(
        dataset="sample",
        ctx={
            "datasets": {
                "sample": {
                    "name": "sample",
                    "files": [str(root_path)],
                    "meta": {"implementation": "fasthep"},
                    "eventtype": "mc",
                    "group": "signal",
                }
            }
        },
    )
    api_schema = inspect_root_tree_schema(
        root_path,
        tree="Events",
        dataset="sample",
        metadata={
            "implementation": "fasthep",
            "eventtype": "mc",
            "group": "signal",
        },
    )

    assert operation_schema == api_schema


def test_schema_table_output(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    table = format_schema_table(
        schema,
        fields=["GenJetAK8_eta", "GenMET_pt"],
    )

    assert "Field" in table
    assert "Type" in table
    assert "Shape" in table
    assert "GenJetAK8_eta" in table
    assert "float32" in table
    assert "jagged" in table
    assert "GenMET_pt" in table
    assert "scalar" in table


def test_schema_yaml_list_output(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    out = format_schema_yaml_list(
        schema,
        fields=["GenJetAK8_eta", "GenJetAK8_hadronFlavour"],
    )

    assert out == "- GenJetAK8_eta\n- GenJetAK8_hadronFlavour"


def test_schema_alignment_output_uses_scalar_and_jagged_element_dtypes(
    tmp_path: Path,
) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    out = format_schema_alignment(
        schema,
        fields=["GenJetAK8_eta", "GenJetAK8_hadronFlavour", "GenMET_pt"],
    )

    assert out == "\n".join(
        [
            "version: 1",
            "fields:",
            "  GenJetAK8_eta:",
            "    dtype: float32",
            "  GenJetAK8_hadronFlavour:",
            "    dtype: int32",
            "  GenMET_pt:",
            "    dtype: float32",
        ]
    )


def test_schema_filter_repeated_include_patterns_preserve_order(
    tmp_path: Path,
) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    fields = filter_schema_fields(
        schema,
        include=["GenJetAK8_*", "GenMET*"],
    )

    assert fields == [
        "GenJetAK8_eta",
        "GenJetAK8_hadronFlavour",
        "GenMET_pt",
    ]


def test_schema_filter_exclude_patterns(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    fields = filter_schema_fields(schema, exclude=["HLT_*", "nMuon_pt"])

    assert "HLT_IsoMu24" not in fields
    assert "nMuon_pt" not in fields
    assert "GenMET_pt" in fields


def test_schema_filter_include_then_exclude_precedence(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    fields = filter_schema_fields(
        schema,
        include=["Gen*"],
        exclude=["GenMET*"],
    )

    assert fields == ["GenJetAK8_eta", "GenJetAK8_hadronFlavour", "Generator_weight"]


def test_schema_filter_duplicate_glob_matches_do_not_duplicate_fields(
    tmp_path: Path,
) -> None:
    schema = inspect_root_tree_schema(_schema_fixture(tmp_path))

    fields = filter_schema_fields(
        schema,
        include=["GenJetAK8_*", "GenJetAK8_eta"],
    )

    assert fields == ["GenJetAK8_eta", "GenJetAK8_hadronFlavour"]


def test_root_tree_schema_missing_tree_fails_clearly(tmp_path: Path) -> None:
    root_path = _schema_fixture(tmp_path)

    with pytest.raises(KeyError, match="Tree 'Missing' not found"):
        inspect_root_tree_schema(root_path, tree="Missing")


def test_root_tree_schema_malformed_input_fails_clearly(tmp_path: Path) -> None:
    bad_path = tmp_path / "not-root.root"
    bad_path.write_text("not a ROOT file", encoding="utf-8")

    with pytest.raises(ValueError, match="Could not open ROOT file"):
        inspect_root_tree_schema(bad_path)


def test_api_and_flow_operation_agree_on_schema(tmp_path: Path) -> None:
    root_path = _schema_fixture(tmp_path)
    cli_schema = inspect_root_tree_schema(root_path, tree="Events", dataset="sample")
    flow_schema = run_root_tree_schema(
        dataset="sample",
        ctx={"datasets": {"sample": {"name": "sample", "files": [str(root_path)]}}},
    )

    assert flow_schema["fields"] == cli_schema["fields"]
    assert flow_schema["field_details"] == cli_schema["field_details"]


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


def _schema_fixture(tmp_path: Path) -> Path:
    root_path = tmp_path / "schema.root"
    with uproot.recreate(root_path) as root_file:
        root_file.mktree(
            "Events",
            {
                "GenJetAK8_eta": ak.values_astype(
                    ak.Array([[1.0, 2.0], [], [3.0]]),
                    np.float32,
                ),
                "GenJetAK8_hadronFlavour": ak.values_astype(
                    ak.Array([[5], [], [4, 0]]),
                    np.int32,
                ),
                "GenMET_pt": np.array([20.0, 30.0, 40.0], dtype=np.float32),
                "Muon_pt": ak.values_astype(
                    ak.Array([[10.0], [], [11.0, 12.0]]),
                    np.float32,
                ),
                "Generator_weight": np.array([1.0, -1.0, 1.0], dtype=np.float32),
                "HLT_IsoMu24": np.array([True, False, True]),
                "NPVs_good": np.array([20, 21, 22], dtype=np.int32),
            },
        )
    return root_path
