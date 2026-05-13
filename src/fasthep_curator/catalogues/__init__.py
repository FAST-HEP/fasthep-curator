from __future__ import annotations

import inspect
from functools import partial
from typing import Any

from fasthep_toolbench.misc import register_in_collection, unregister_from_collection
from fasthep_toolbench.package import class_from_type_string, is_valid_import

from . import cms_das as CMSDASExpander
from .common import Expander, LocalGlobExpander, XrootdExpander

known_expanders: dict[str, type[Expander]] = {
    "xrootd": XrootdExpander,
    "local": LocalGlobExpander,
    "cmsdas": CMSDASExpander,
}


def register_expander(name: str, expander: str) -> None:
    """Register a catalogue expander class."""
    if not is_valid_import(expander):
        msg = f"Cannot import expander: {expander}"
        raise ImportError(msg)
    cls = class_from_type_string(expander)
    _check_expander(cls)
    register_in_collection(
        collection=known_expanders,
        collection_name="fh_curator.catalogues.known_expanders",
        name=name,
        obj=cls,
    )


unregister_expander = partial(
    unregister_from_collection,
    collection=known_expanders,
    collection_name="fh_curator.catalogues.known_expanders",
)


def _check_expander(expander: Any) -> None:
    """An expander can be any object that has the three static methods:
    - check_setup() -> bool
    - expand_file_list(files: list[str], prefix: Prefix = None) -> list[str]
    - check_files(*args, **kwargs) ->  -> tuple[list[str], dict[str, int] | int, dict[str, Any]]
    """
    assert inspect.isclass(expander), "Expander must be a class"
    assert inspect.hasattr(expander, "check_setup"), (
        "Expander must have a check_setup method"
    )
    assert isinstance(inspect.getattr_static(expander, "check_setup"), staticmethod), (
        "Expander's check_setup must be a static method"
    )
    assert inspect.hasattr(expander, "expand_file_list"), (
        "Expander must have an expand_file_list method"
    )
    assert isinstance(
        inspect.getattr_static(expander, "expand_file_list"), staticmethod
    ), "Expander's expand_file_list must be a static method"
    assert inspect.hasattr(expander, "check_files"), (
        "Expander must have a check_files method"
    )
    assert isinstance(inspect.getattr_static(expander, "check_files"), staticmethod), (
        "Expander's check_files must be a static method"
    )


def get_file_list_expander(expander: str) -> type[Expander]:
    if expander not in known_expanders:
        msg = "Unknown catalogue interface requested, '%s'. Valid options: %s"
        raise RuntimeError(msg % (expander, ", ".join(known_expanders.keys())))
    result = known_expanders[expander]
    if not result.check_setup():
        msg = "Issue setting up catalogue interface: %s"
        raise RuntimeError(msg % expander)
    return result
