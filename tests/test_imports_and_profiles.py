from __future__ import annotations

import importlib.resources as resources

from hepflow.compiler.profiles import load_profile_config
from hepflow.registry.loaders import load_object

import fasthep_curator


def _profile_text(name: str) -> str:
    return (
        resources.files("fasthep_curator.profiles")
        .joinpath(name)
        .read_text(encoding="utf-8")
    )


def test_import_package() -> None:
    assert fasthep_curator is not None


def test_load_profile_resources() -> None:
    assert "hep.schema_snapshot" in _profile_text("registry.yaml")
    assert "hep.dataset_context" in _profile_text("default_context.yaml")
    assert "hep.warning_capture" in _profile_text("runtime_diagnostics.yaml")


def test_load_hook_and_observer_objects() -> None:
    hook_spec = load_object(
        "fasthep_curator.hooks.dataset_context:DATASET_CONTEXT_HOOK_SPEC"
    )
    hook_impl = load_object(
        "fasthep_curator.hooks.dataset_context:DatasetContextHook"
    )
    observer_spec = load_object(
        "fasthep_curator.observers.schema_snapshot:SCHEMA_SNAPSHOT_OBSERVER_SPEC"
    )
    observer_impl = load_object(
        "fasthep_curator.observers.schema_snapshot:run_schema_snapshot_observer"
    )
    compile_hook_impl = load_object(
        "fasthep_curator.compile_hooks.root_tree_metadata:inspect_root_tree_datasets"
    )

    assert hook_spec.name == "hep.dataset_context"
    assert callable(hook_impl)
    assert observer_spec["name"] == "hep.schema_snapshot"
    assert callable(observer_impl)
    assert callable(compile_hook_impl)


def test_flow_loads_qualified_curator_profiles(tmp_path) -> None:
    registry = load_profile_config(
        "fasthep_curator:registry",
        project_root=tmp_path,
    )
    context = load_profile_config(
        "fasthep_curator:default_context",
        project_root=tmp_path,
    )
    diagnostics = load_profile_config(
        "fasthep_curator:runtime_diagnostics",
        project_root=tmp_path,
    )

    assert "hep.dataset_context" in registry["registry"]["hooks"]
    assert "dataset_metadata.root_tree" in registry["registry"]["compile_hooks"]
    assert context["execution_hooks"] == [
        {"kind": "hep.dataset_context", "events": ["partition_start"]}
    ]
    assert {hook["kind"] for hook in diagnostics["execution_hooks"]} == {
        "hep.error_report",
        "hep.warning_capture",
    }
