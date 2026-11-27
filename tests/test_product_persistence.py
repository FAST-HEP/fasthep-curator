from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import awkward as ak
import numpy as np
import pytest
import uproot
import yaml
from hepflow.api import restore_products
from hepflow.model.persistence import PersistenceSettings
from hepflow.model.plan import ExecutionPlan
from hepflow.model.products import BoundaryProduct
from hepflow.registry.loaders import resolve_runtime_registry
from hepflow.runtime.persistence.save import persist_boundary_products
from hepflow.runtime.persistence.select import PersistenceSelection

from fasthep_curator.api import inspect_root_tree_schema
from fasthep_curator.operations.schema_validation import run_compare_schemas
from fasthep_curator.products.persistence import load_json_value, save_json_value

IDENTITY: dict[str, Any] = {
    "producer_node": "stage.S",
    "output_name": "schema",
    "product_kind": "schema_snapshot",
    "dataset_name": "s",
}


def _registry() -> Any:
    text = (
        resources.files("fasthep_curator.profiles")
        .joinpath("registry.yaml")
        .read_text(encoding="utf-8")
    )
    return resolve_runtime_registry(yaml.safe_load(text)["registry"])


def _root_file(tmp_path: Path) -> Path:
    path = tmp_path / "schema.root"
    with uproot.recreate(path) as root_file:
        root_file.mktree(
            "Events",
            {
                "Muon_pt": ak.values_astype(ak.Array([[10.0], [], [11.0]]), np.float32),
                "NPVs": np.array([20, 21, 22], dtype=np.int32),
            },
        )
    return path


def _round_trip(value: Any, tmp_path: Path) -> Any:
    outcome = save_json_value(value, root=tmp_path, params={}, identity=IDENTITY)
    paths = [tmp_path / payload.path for payload in outcome.payloads]
    return load_json_value(tmp_path, paths, params={}, variant=None, locator=None)


def test_schema_snapshot_round_trip(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_root_file(tmp_path), tree="Events", dataset="s")

    assert _round_trip(schema, tmp_path / "out") == schema


def test_schema_comparison_round_trip(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_root_file(tmp_path), tree="Events", dataset="s")
    comparison = run_compare_schemas(reference=schema, target=schema)

    assert _round_trip(comparison, tmp_path / "out") == comparison


def test_a_merged_list_of_schemas_round_trips(tmp_path: Path) -> None:
    schema = inspect_root_tree_schema(_root_file(tmp_path), tree="Events", dataset="s")
    merged = [schema, {**schema, "dataset": "t"}]

    assert _round_trip(merged, tmp_path / "out") == merged


@pytest.mark.parametrize("value", ["text", 3, None, {"x": object()}])
def test_values_that_are_not_data_are_refused(tmp_path: Path, value: Any) -> None:
    with pytest.raises(ValueError, match="schema"):
        _round_trip(value, tmp_path)


def test_registry_declares_both_capabilities() -> None:
    handlers = _registry().product_handlers

    snapshot = handlers["schema_snapshot"].persistence["schema_snapshot.json"]
    comparison = handlers["schema_comparison"].persistence["schema_comparison.json"]
    for capability, kind in (
        (snapshot, "schema_snapshot"),
        (comparison, "schema_comparison"),
    ):
        assert capability.kind == kind
        assert (capability.version, capability.container) == ("1", "json")
        assert capability.payload_roles == ("data",)
        assert callable(capability.save)
        assert callable(capability.load)
        assert capability.fidelity


def test_persist_and_restore_through_flow(tmp_path: Path) -> None:
    registry = _registry()
    schema = inspect_root_tree_schema(_root_file(tmp_path), tree="Events", dataset="s")
    product = BoundaryProduct(
        node_id="stage.S",
        output_name="schema",
        kind="schema_snapshot",
        dataset="s",
        partition_id="p0",
        representation="persist",
        value=schema,
    )
    capability = registry.product_handlers["schema_snapshot"].persistence[
        "schema_snapshot.json"
    ]

    [saved] = persist_boundary_products(
        [product],
        PersistenceSelection(persisted={product.key(): capability}),
        plan=ExecutionPlan(),
        settings=PersistenceSettings(mode="all"),
        outdir=tmp_path / "build",
    )
    restored = restore_products(saved.metadata["persisted"], registry=registry)

    assert list(restored.products.values()) == [schema]


@pytest.mark.parametrize(
    "value",
    [
        {"meta": {"lumi": {2016: 36.3}}},
        {"meta": {True: 1}},
        {"cuts": (1, 2)},
        {"x": float("nan")},
        {"x": float("inf")},
    ],
)
def test_what_json_would_change_is_refused(tmp_path: Path, value: Any) -> None:
    with pytest.raises(ValueError, match=r"stage\.S"):
        _round_trip(value, tmp_path)


def test_the_error_names_producer_output_and_kind(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="schema_snapshot") as caught:
        _round_trip({"x": object()}, tmp_path)

    message = str(caught.value)
    assert "stage.S" in message
    assert "schema" in message
    assert "schema_snapshot" in message


def test_a_circular_value_is_refused(tmp_path: Path) -> None:
    value: dict[str, Any] = {}
    value["self"] = value

    with pytest.raises(ValueError, match=r"stage\.S"):
        _round_trip(value, tmp_path)


def test_a_list_must_hold_dicts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="list of dicts"):
        _round_trip([1, "a"], tmp_path)


@pytest.mark.parametrize("text", ["[1, 2]", '{"format_version": "1"}', "not json"])
def test_a_malformed_payload_is_refused_clearly(tmp_path: Path, text: str) -> None:
    payload = tmp_path / "product.json"
    payload.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=r"product\.json"):
        load_json_value(tmp_path, [payload], params={}, variant=None, locator=None)
