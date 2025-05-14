from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def yaml_config_1(tmpdir):
    content = """
    datasets:
      - name: one
        eventtype: mc
        files: ["{prefix}one", "two"]
        prefix: SOME_prefix/
    """
    tmpfile = tmpdir / "curator_yaml_config_1.yml"
    tmpfile.write(content)
    return str(tmpfile)


@pytest.fixture
def yaml_config_2(yaml_config_1, tmpdir):  # noqa: ARG001
    # depends on yaml_config_1 since it is used as an import
    # in the yaml_config_2
    content = """
    import:
      - "{this_dir}/curator_yaml_config_1.yml"
    datasets:
      - name: two
        eventtype: mc
        files: ["one", "two", "{prefix}three"]
        prefix:
          - default: SOME_prefix/
          - second: another_one_PREFIX/
    """
    tmpfile = tmpdir / "curator_yaml_config_2.yml"
    tmpfile.write(content)
    return str(tmpfile)


@pytest.fixture
def yaml_config_3(tmpdir):
    content = """
    datasets:
      - name: one
        eventtype: mc
        files: ["{prefix}one", "two"]
        prefix: SOME_prefix/
        nevents: !!int '77729'
    """
    tmpfile = tmpdir / "curator_yaml_config_3.yml"
    tmpfile.write(content)
    return str(tmpfile)


@pytest.fixture
def empty_yaml_config(tmpdir):
    content = ""
    tmpfile = tmpdir / "empty_yaml_config.yml"
    tmpfile.write(content)
    return str(tmpfile)


@pytest.fixture(params=["relpath", "abspath"])
def dummy_file_dir(request) -> Path:
    relpath = request.param == "relpath"
    cwd = Path.cwd()
    data_path = Path(__file__).parent / "data"
    directory = data_path
    if relpath:
        common_path = Path(os.path.commonprefix([cwd, data_path]))
        directory = data_path.relative_to(common_path)
    assert directory.is_dir()
    return directory


@pytest.fixture
def dummy_file_100(dummy_file_dir):
    return dummy_file_dir / "events_100.root"


@pytest.fixture
def dummy_file_202(dummy_file_dir):
    return dummy_file_dir / "events_202.root"


@pytest.fixture
def dummy_file_empty(dummy_file_dir):
    return dummy_file_dir / "empty.root"


@pytest.fixture
def dummy_file_no_tree(dummy_file_dir):
    return dummy_file_dir / "no-tree.root"


@pytest.fixture
def all_dummy_files(
    dummy_file_100, dummy_file_202, dummy_file_empty, dummy_file_no_tree
):
    return [
        dummy_file_100,
        dummy_file_202,
        dummy_file_empty,
        dummy_file_no_tree,
    ]


@pytest.fixture
def dummy_config_file_v0():
    return Path(__file__).parent / "data" / "testdata_v0.yml"


@pytest.fixture
def dummy_config_file_v1():
    return Path(__file__).parent / "data" / "testdata_v1.yml"
