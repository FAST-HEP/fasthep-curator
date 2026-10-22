from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pytest
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

    result = inspect_root_tree_datasets(_ctx(tmp_path), add_per_file=True)

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
                    "total_entries_origin": "read",
                    "total_entries_fallback": "missing",
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
                    "total_entries_origin": "read",
                    "total_entries_fallback": "missing",
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

    result = inspect_root_tree_datasets(ctx, add_per_file=True)

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

    assert inspect_root_tree_datasets(ctx) == {"dataset_metadata": {"datasets": {}}}


def _count_opens(monkeypatch, entries: int = 5) -> list[str]:
    opened: list[str] = []

    def fake_open(path: str) -> FakeRootFile:
        opened.append(path)
        return FakeRootFile({"events": entries})

    monkeypatch.setattr(
        "fasthep_curator.compile_hooks.root_tree_metadata.uproot.open",
        fake_open,
    )
    return opened


def _ctx_with(tmp_path: Path, datasets: dict[str, Any]) -> CompileHookContext:
    return CompileHookContext(
        normalized={"sources": {"events": {"kind": "root_tree", "tree": "events"}}},
        plan_context={"datasets": datasets},
        build_paths=BuildPaths(root=tmp_path),
    )


def _datasets(nevents: Any) -> dict[str, Any]:
    return {"ds": {"name": "ds", "files": ["a.root", "b.root"], "nevents": nevents}}


def test_root_metadata_hook_uses_nevents_without_opening_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch)

    result = inspect_root_tree_datasets(_ctx_with(tmp_path, _datasets(123)))

    assert opened == []
    assert result["dataset_metadata"]["datasets"]["ds"] == {
        "files": {},
        "total_entries": 123,
        "total_entries_origin": "nevents",
    }


def test_root_metadata_hook_accepts_digit_string_nevents(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Flow stores ``nevents`` as a string.
    opened = _count_opens(monkeypatch)

    result = inspect_root_tree_datasets(_ctx_with(tmp_path, _datasets("69348871")))

    assert opened == []
    assert result["dataset_metadata"]["datasets"]["ds"]["total_entries"] == 69348871


@pytest.mark.parametrize(
    ("nevents", "reason"),
    [
        (True, "invalid"),
        (-1, "invalid"),
        (1.5, "invalid"),
        ("", "invalid"),
        ("12abc", "invalid"),
        ("-3", "invalid"),
        (None, "missing"),
    ],
)
def test_root_metadata_hook_falls_back_to_reading_invalid_nevents(
    tmp_path: Path,
    monkeypatch,
    nevents: Any,
    reason: str,
) -> None:
    opened = _count_opens(monkeypatch, entries=5)

    result = inspect_root_tree_datasets(_ctx_with(tmp_path, _datasets(nevents)))

    assert opened == ["a.root", "b.root"]
    assert result["dataset_metadata"]["datasets"]["ds"] == {
        "files": {},
        "total_entries": 10,
        "total_entries_origin": "read",
        "total_entries_fallback": reason,
    }


def test_root_metadata_hook_accepts_zero_nevents(tmp_path: Path, monkeypatch) -> None:
    opened = _count_opens(monkeypatch)

    result = inspect_root_tree_datasets(_ctx_with(tmp_path, _datasets(0)))

    assert opened == []
    assert result["dataset_metadata"]["datasets"]["ds"]["total_entries"] == 0


def test_root_metadata_hook_reads_only_datasets_without_valid_nevents(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch, entries=4)
    datasets = {
        "good": {"name": "good", "files": ["g.root"], "nevents": 99},
        "bad": {"name": "bad", "files": ["x.root", "y.root"]},
    }

    result = inspect_root_tree_datasets(_ctx_with(tmp_path, datasets))

    assert opened == ["x.root", "y.root"]
    by_name = result["dataset_metadata"]["datasets"]
    assert by_name["good"]["total_entries"] == 99
    assert by_name["bad"]["total_entries"] == 8


def test_root_metadata_hook_reads_everything_without_a_source_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch, entries=5)

    result = inspect_root_tree_datasets(
        _ctx_with(tmp_path, _datasets(123)), total_entries_source=None
    )

    assert opened == ["a.root", "b.root"]
    assert result["dataset_metadata"]["datasets"]["ds"] == {
        "files": {},
        "total_entries": 10,
        "total_entries_origin": "read",
    }


def test_root_metadata_hook_uses_the_named_source_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch)
    datasets = {"ds": {"name": "ds", "files": ["a.root"], "n_events": 7}}

    result = inspect_root_tree_datasets(
        _ctx_with(tmp_path, datasets), total_entries_source="n_events"
    )

    assert opened == []
    record = result["dataset_metadata"]["datasets"]["ds"]
    assert record["total_entries"] == 7
    assert record["total_entries_origin"] == "n_events"


def test_root_metadata_hook_add_per_file_fills_files_and_keeps_declared_total(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _count_opens(monkeypatch, entries=5)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = inspect_root_tree_datasets(
            _ctx_with(tmp_path, _datasets(10)), add_per_file=True
        )

    record = result["dataset_metadata"]["datasets"]["ds"]
    assert record["total_entries"] == 10
    assert record["total_entries_origin"] == "nevents"
    assert set(record["files"]) == {"a.root", "b.root"}


def test_root_metadata_hook_add_per_file_warns_on_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _count_opens(monkeypatch, entries=5)

    with pytest.warns(UserWarning, match="inconsistent"):
        result = inspect_root_tree_datasets(
            _ctx_with(tmp_path, _datasets(99)), add_per_file=True
        )

    # The declared total still wins; the warning is the only signal.
    assert result["dataset_metadata"]["datasets"]["ds"]["total_entries"] == 99


def test_root_metadata_hook_rejects_unknown_params(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="total_entry_source"):
        inspect_root_tree_datasets(
            _ctx_with(tmp_path, _datasets(1)),
            total_entry_source="nevents",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    ("params", "error"),
    [
        ({"total_entries_source": 3}, TypeError),
        ({"total_entries_source": ""}, ValueError),
        ({"add_per_file": "yes"}, TypeError),
        ({"max_files_warn": -1}, TypeError),
        ({"max_files_warn": True}, TypeError),
        ({"max_files_warn": "100"}, TypeError),
    ],
)
def test_root_metadata_hook_validates_params_before_opening_files(
    tmp_path: Path,
    monkeypatch,
    params: dict[str, Any],
    error: type[Exception],
) -> None:
    opened = _count_opens(monkeypatch)

    with pytest.raises(error):
        inspect_root_tree_datasets(_ctx_with(tmp_path, _datasets(None)), **params)

    assert opened == []


def _many(n_datasets: int, files_each: int, nevents: Any = None) -> dict[str, Any]:
    return {
        f"ds{i}": {
            "name": f"ds{i}",
            "files": [f"ds{i}_{j}.root" for j in range(files_each)],
            "nevents": nevents,
        }
        for i in range(n_datasets)
    }


def test_root_metadata_hook_warns_once_above_the_file_threshold(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch)

    with pytest.warns(UserWarning, match="101 files in 2 datasets") as caught:
        inspect_root_tree_datasets(
            _ctx_with(tmp_path, {**_many(1, 51), "other": _many(1, 50)["ds0"]})
        )

    assert len([w for w in caught if "will be opened" in str(w.message)]) == 1
    assert len(opened) == 101


def test_root_metadata_hook_does_not_warn_at_the_file_threshold(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _count_opens(monkeypatch)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inspect_root_tree_datasets(_ctx_with(tmp_path, _many(2, 50)))


def test_root_metadata_hook_does_not_warn_when_nevents_avoids_the_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    opened = _count_opens(monkeypatch)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inspect_root_tree_datasets(_ctx_with(tmp_path, _many(3, 100, nevents=10)))

    assert opened == []


def test_root_metadata_hook_counts_only_the_datasets_it_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _count_opens(monkeypatch)
    datasets = {**_many(1, 500, nevents=10), "bad": _many(1, 3)["ds0"]}

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        inspect_root_tree_datasets(_ctx_with(tmp_path, datasets))


def test_root_metadata_hook_threshold_is_a_parameter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _count_opens(monkeypatch)

    with pytest.warns(UserWarning, match="3 files in 1 datasets"):
        inspect_root_tree_datasets(_ctx_with(tmp_path, _many(1, 3)), max_files_warn=2)


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
