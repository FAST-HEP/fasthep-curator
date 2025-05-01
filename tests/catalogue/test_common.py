from __future__ import annotations

import glob

import pytest
from pytest_lazy_fixtures import lf

from fasthep_curator.catalogues.common import (
    check_entries_uproot,
    expand_file_list_generic,
    uproot_num_entries,
)


def test_expand_file_list_generic():
    from fasthep_curator.catalogues.common import expand_file_list_generic

    files = ["file1", "file2"]
    prefix = "prefix"

    def glob(x):
        return [f"{x}_expanded"]

    result = expand_file_list_generic(files, prefix, glob)

    assert result == ["prefix/file1_expanded", "prefix/file2_expanded"]
    assert len(result) == 2
    assert all("expanded" in f for f in result)


def test_expand_file_list_generic_dummy(dummy_file_dir):
    files = [str(dummy_file_dir / "*.root")]
    prefix = None

    result = expand_file_list_generic(files, prefix, glob=glob.glob)

    assert len(result) == 4


@pytest.mark.parametrize(
    ("input_file", "expected"),
    [
        (lf("dummy_file_100"), 100),
        (lf("dummy_file_202"), 202),
        (lf("dummy_file_empty"), 0),
    ],
)
def test_uproot_numentries(input_file, expected):
    files = [str(input_file)]
    tree_name = "events"
    numentries = uproot_num_entries(files, tree_name)
    assert isinstance(numentries, dict)
    assert len(numentries) == 1
    assert numentries[files[0]] == expected


@pytest.mark.parametrize(
    ("input_files", "expected"),
    [
        ([lf("dummy_file_100")], 100),
        ([lf("dummy_file_202")], 202),
        ([lf("dummy_file_empty")], 0),
    ],
)
def test_num_entries(input_files, expected):
    files = [str(input_file) for input_file in input_files]
    tree_name = "events"
    files, numentries, branches = check_entries_uproot(
        files, tree_name, disallow_empty=False, list_branches=True
    )
    assert numentries == expected
    assert isinstance(numentries, int)
    assert isinstance(branches, dict)
    assert len(branches) == 1


@pytest.mark.parametrize(
    ("input_files", "expected"),
    [
        ([lf("dummy_file_no_tree")], 0),
        (
            lf("all_dummy_files"),
            302,
        ),
    ],
)
def test_num_entries_empty(input_files, expected):
    files = [str(input_file) for input_file in input_files]
    tree_name = "events"
    files, numentries, branches = check_entries_uproot(
        files, tree_name, disallow_empty=False, list_branches=True, confirm_tree=False
    )
    if isinstance(numentries, dict):
        assert sum(numentries.values()) == expected
    assert isinstance(numentries, dict)
    assert isinstance(branches, dict)
    assert len(branches) == 1
