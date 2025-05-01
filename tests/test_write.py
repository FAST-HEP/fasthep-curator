from __future__ import annotations

from pathlib import Path

import pytest

import fasthep_curator.catalogues as cat
import fasthep_curator.write as fc_write


def test_select_default():
    default = fc_write.select_default([0, 1, 2, 2, 2, 3])
    assert default == 2

    default = fc_write.select_default([0, 1, 2, 3])
    assert default is None

    default = fc_write.select_default([0, 1, 2, 2, 3, 3])
    assert default is None

    default = fc_write.select_default([])
    assert default is None


def test_add_meta():
    dataset = {"one": 1, "two": "2"}
    fc_write.add_meta(dataset, [("three", 3), ("4", "four")])

    assert dataset["three"] == 3
    assert dataset["4"] == "four"

    with pytest.raises(RuntimeError) as e:
        fc_write.add_meta(dataset, [("one", "3/3")])
    assert "will override" in str(e)


def test_prepare_contents():
    datasets = [
        {"name": "foo", "one": "i1", "two": 2, "three": "3", "a": ["ay", "ee", "eye"]},
        {"name": "bar", "one": "1", "two": 2, "three": "3i", "a": ["eye", "oh", "you"]},
        {"name": "baz", "one": "1", "two": 2, "three": "3j", "a": ["oh"]},
    ]
    contents = fc_write.prepare_contents(datasets)

    assert "defaults" in contents
    assert "datasets" in contents
    assert len(contents["defaults"]) == 2
    assert contents["defaults"]["one"] == "1"
    assert contents["defaults"]["two"] == 2
    assert len(contents["datasets"]) == 3
    assert all("two" not in d for d in contents["datasets"])
    assert "one" not in contents["datasets"][1]
    assert "one" not in contents["datasets"][2]
    assert contents["datasets"][1]["name"] == "bar"
    assert contents["datasets"][2]["name"] == "baz"
    assert all("a" in d for d in contents["datasets"])


@pytest.mark.parametrize("expand", ["xrootd", "local"])
@pytest.mark.parametrize("prefix", [None, str(Path.cwd())])
@pytest.mark.parametrize(
    ("nfiles", "nevents", "empty"), [(2, 302, True), (4, 302, False)]
)
def test_prepare_file_list(dummy_file_dir, nfiles, nevents, empty, expand, prefix):
    tree = "events"
    files = [str(dummy_file_dir / "*.root")]
    file_list = fc_write.prepare_file_list(
        files,
        "data",
        "mc",
        tree_name=tree,
        prefix=prefix,
        expander_name=expand,
        confirm_tree=False,
        include_branches=True,
        no_empty_files=empty,
    )

    assert isinstance(file_list, dict)
    assert file_list["name"] == "data"
    assert file_list["eventtype"] == "mc"
    assert file_list["nfiles"] == nfiles
    if isinstance(file_list["nevents"], dict):
        assert sum(file_list["nevents"].values()) == nevents
    else:
        assert file_list["nevents"] == nevents
    assert len(file_list["branches"]) == 1
    assert len(file_list["branches"]["events"]) == 1
    assert file_list["branches"]["events"]["ev"] == 1
    assert any("events_202" in f for f in file_list["files"])


@pytest.mark.parametrize("expand", ["xrootd", "local"])
@pytest.mark.parametrize("empty", [True, False])
def test_prepare_file_list_confirm_trees(dummy_file_dir, empty, expand):
    tree = "events"
    files = [dummy_file_dir / "*.root"]
    with pytest.raises(RuntimeError) as e:
        fc_write.prepare_file_list(
            files,
            "data",
            "mc",
            tree_name=tree,
            expander_name=expand,
            confirm_tree=True,
            no_empty_files=empty,
        )
    assert "Missing" in str(e)
    assert "events" in str(e)


def test_get_file_list_expander():
    xrootd = fc_write.get_file_list_expander("xrootd")
    assert xrootd is cat.XrootdExpander

    local = fc_write.get_file_list_expander("local")
    assert local is cat.LocalGlobExpander

    with pytest.raises(RuntimeError) as e:
        fc_write.get_file_list_expander("gobbledy gook")
    assert "Unknown catalogue" in str(e)
