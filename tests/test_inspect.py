from __future__ import annotations

import pytest
from pytest_lazy_fixtures import lf

import fasthep_curator._inspect as fci


@pytest.mark.parametrize(
    ("input_file", "tree_name", "ntrees"),
    [
        (lf("dummy_file_100"), "events;1", 1),
        (lf("dummy_file_empty"), "events;1", 1),
    ],
)
def test_get_trees(input_file, tree_name, ntrees):
    """Test the get_trees function."""
    # Test the get_trees function
    trees = list(fci.get_trees(input_file))
    assert trees is not None
    assert len(trees) == ntrees
    assert trees[0] == tree_name


def test_get_trees_no_tree(dummy_file_no_tree):
    """Test the get_trees function with no tree."""
    # Test the get_trees function
    trees = list(fci.get_trees(dummy_file_no_tree))
    assert trees is not None
    assert len(trees) == 0


def test_inspect(dummy_file_100):
    """Test the inspect function."""
    # Test the inspect function
    file_info = fci.inspect(dummy_file_100)
    assert file_info is not None
    assert len(file_info) == 1
    assert "name" in file_info.columns
    assert "type" in file_info.columns
    assert "interpretation" in file_info.columns
    assert "compressedbytes" in file_info.columns
    assert "uncompressedbytes" in file_info.columns
    assert "hasStreamer" in file_info.columns
    assert "uproot_readable" in file_info.columns
    assert "is_empty" in file_info.columns


def test_inspect_all(dummy_file_100, dummy_file_202):
    """Test the inspect function with all files."""
    # Test the inspect function
    file_info = fci.inspect_all([dummy_file_100, dummy_file_202])
    assert file_info is not None
    assert len(file_info) == 2
    assert "name" in file_info.columns
    assert "type" in file_info.columns
    assert "interpretation" in file_info.columns
    assert "compressedbytes" in file_info.columns
    assert "uncompressedbytes" in file_info.columns
    assert "hasStreamer" in file_info.columns
    assert "uproot_readable" in file_info.columns
    assert "is_empty" in file_info.columns
