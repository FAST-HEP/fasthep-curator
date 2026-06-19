from __future__ import annotations

from pathlib import Path
from typing import Any

from hepflow.build_layout import BuildPaths
from hepflow.compiler.compile_hooks import CompileHookContext

from fasthep_curator.compile_hooks.root_tree_metadata import (
    inspect_root_tree_datasets,
)


class FakeTree:
    def __init__(self, entries: int) -> None:
        self.num_entries = entries

    def arrays(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("metadata inspection must not call arrays()")


class FakeRootFile:
    def __init__(self, trees: dict[str, int]) -> None:
        self._trees = trees

    def __enter__(self) -> FakeRootFile:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def __getitem__(self, tree_name: str) -> FakeTree:
        try:
            entries = self._trees[tree_name]
        except KeyError as exc:
            raise KeyError(tree_name) from exc
        return FakeTree(entries)


def test_root_metadata_hook_records_entries_and_totals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened: list[str] = []

    def fake_open(path: str) -> FakeRootFile:
        opened.append(path)
        entries = {
            "data.root": 7,
            "dy.root": 11,
            "extra.root": 13,
        }[Path(path).name]
        return FakeRootFile({"events": entries})

    monkeypatch.setattr(
        "fasthep_curator.compile_hooks.root_tree_metadata.uproot.open",
        fake_open,
    )

    result = inspect_root_tree_datasets(_ctx(tmp_path))

    assert opened == ["data.root", "dy.root", "extra.root"]
    assert result == {
        "dataset_metadata": {
            "datasets": {
                "data": {
                    "files": {
                        "data.root": {
                            "entries": 7,
                            "by_tree": {"events": 7},
                        }
                    },
                    "total_entries": 7,
                },
                "dy": {
                    "files": {
                        "dy.root": {
                            "entries": 11,
                            "by_tree": {"events": 11},
                        },
                        "extra.root": {
                            "entries": 13,
                            "by_tree": {"events": 13},
                        },
                    },
                    "total_entries": 24,
                },
            }
        }
    }


def test_root_metadata_hook_passes_remote_paths_to_uproot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened: list[str] = []

    def fake_open(path: str) -> FakeRootFile:
        opened.append(path)
        return FakeRootFile({"Events": 42})

    monkeypatch.setattr(
        "fasthep_curator.compile_hooks.root_tree_metadata.uproot.open",
        fake_open,
    )

    ctx = CompileHookContext(
        normalized={"sources": {"events": {"kind": "root_tree", "tree": "Events"}}},
        plan_context={
            "datasets": {
                "DoubleMuon": {
                    "name": "DoubleMuon",
                    "files": ["root://example.invalid//store/file.root"],
                }
            }
        },
        build_paths=BuildPaths(root=tmp_path),
    )

    result = inspect_root_tree_datasets(ctx)

    assert opened == ["root://example.invalid//store/file.root"]
    assert result["dataset_metadata"]["datasets"]["DoubleMuon"]["files"][
        "root://example.invalid//store/file.root"
    ] == {
        "entries": 42,
        "by_tree": {"Events": 42},
    }


def test_root_metadata_hook_returns_empty_artifact_without_root_sources(
    tmp_path: Path,
) -> None:
    ctx = CompileHookContext(
        normalized={"sources": {"events": {"kind": "toy.source"}}},
        plan_context={"datasets": {"data": {"files": ["data.root"]}}},
        build_paths=BuildPaths(root=tmp_path),
    )

    assert inspect_root_tree_datasets(ctx) == {
        "dataset_metadata": {"datasets": {}}
    }


def _ctx(tmp_path: Path) -> CompileHookContext:
    return CompileHookContext(
        normalized={"sources": {"events": {"kind": "root_tree", "tree": "events"}}},
        plan_context={
            "datasets": {
                "data": {
                    "name": "data",
                    "files": ["data.root"],
                },
                "dy": {
                    "name": "dy",
                    "files": ["dy.root", "extra.root"],
                },
            }
        },
        build_paths=BuildPaths(root=tmp_path),
    )
