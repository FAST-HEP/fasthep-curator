from __future__ import annotations

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
