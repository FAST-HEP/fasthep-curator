from __future__ import annotations

import pytest

from fasthep_curator import read as fc_read


def test_from_yaml_1(yaml_config_1: str):
    datasets = fc_read.from_yaml(yaml_config_1)
    assert len(datasets) == 1


def test_from_yaml_2(yaml_config_2: str):
    datasets = fc_read.from_yaml(yaml_config_2)
    assert len(datasets) == 2


def test_from_yaml_3(yaml_config_3: str):
    datasets = fc_read.from_yaml(yaml_config_3)
    assert len(datasets) == 1


def test_from_string():
    config = fc_read.from_string("dummy_data_1")
    assert len(config) == 1
    assert config["name"] == "dummy_data_1"

    config = fc_read.from_string("dummy_data_2", defaults={"key": "val"})
    assert len(config) == 2
    assert config["name"] == "dummy_data_2"
    assert config["key"] == "val"


def test_from_dict():
    dataset = {"one": 1, "two": "2"}

    with pytest.raises(RuntimeError) as e:
        fc_read.from_dict(dataset, {})
    assert "'name'" in str(e)

    dataset["name"] = "test__from_dict"
    config = fc_read.from_dict(dataset, {"one": "one", "three": 333})

    assert len(config.keys()) == 4
    assert config["one"] == 1
    assert config["two"] == "2"
    assert config["three"] == 333


def test_empty_yaml_config(empty_yaml_config: str):
    with pytest.raises(RuntimeError) as e:
        fc_read.from_yaml(empty_yaml_config)
    assert "Empty config file" in str(e)


def test_apply_prefix():
    files = ["{prefix}one", "{prefix}two/two", "three"]
    dataset = "test_apply_prefix"

    prefix: fc_read.Prefix = None
    result = fc_read.apply_prefix(prefix, files, None, dataset)
    assert len(result) == 3
    assert result == files

    prefix = "testing/"
    result = fc_read.apply_prefix(prefix, files, None, dataset)
    assert len(result) == 3
    assert result[0] == "testing/one"
    assert result[1] == "testing/two/two"
    assert result[2] == "three"

    prefix = [{"default": "another_test/"}, {"second": "yet_another_test/"}]
    result = fc_read.apply_prefix(prefix, files, None, dataset)
    assert len(result) == 3
    assert result[0] == "another_test/one"
    assert result[1] == "another_test/two/two"
    assert result[2] == "three"

    result = fc_read.apply_prefix(prefix, files, "second", dataset)
    assert len(result) == 3
    assert result[0] == "yet_another_test/one"
    assert result[1] == "yet_another_test/two/two"
    assert result[2] == "three"

    with pytest.raises(ValueError) as e:  # noqa: PT011
        fc_read.apply_prefix(prefix, files, "invalid", dataset)
    assert "invalid" in str(e)
    assert "not defined" in str(e)

    prefix = [{"foo": 1, "bar": 3}]
    with pytest.raises(ValueError) as e:  # noqa: PT011
        fc_read.apply_prefix(prefix, files, None, dataset)
    assert "single-length dict" in str(e)

    prefix = {"foo": 1, "bar": 3}  # type: ignore[assignment]
    with pytest.raises(ValueError) as e:  # noqa: PT011
        fc_read.apply_prefix(prefix, files, None, dataset)
    assert "string or a list" in str(e)

    prefix = [{"default": "another_test/"}, {"default": "yet_another_test/"}]
    with pytest.raises(ValueError) as e:  # noqa: PT011
        fc_read.apply_prefix(prefix, files, "default", dataset)
    assert "defined 2 times" in str(e)
