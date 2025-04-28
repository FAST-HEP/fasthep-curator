from __future__ import annotations

import importlib.metadata

import fasthep_curator as m


def test_version():
    assert importlib.metadata.version("fasthep_curator") == m.__version__
