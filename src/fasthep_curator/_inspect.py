from __future__ import annotations

from collections.abc import Generator
from typing import Any

import numpy as np
import pandas as pd
import uproot
from loguru import logger


def _walk(obj: Any, name: str | None = None) -> Generator[tuple[str | None, Any]]:
    if not hasattr(obj, "keys") or len(obj.keys()) == 0:
        yield name, obj
    else:
        for k in sorted(obj.keys(recursive=False)):
            # if there is a '.' the first part of k it will be a duplicate
            tokens = k.split(".")
            new_name = name if name else k
            for t in tokens:
                if new_name.endswith(t):
                    continue
                new_name = ".".join([new_name, t])
            yield from _walk(obj[k], new_name)


# def _dir_walk(obj: Any, name: str | None = None) -> Generator[tuple[str | None, Any]]:
#     if not hasattr(obj, "keys") or len(obj.keys()) == 0:
#         yield name, obj
#     else:
#         for k in sorted(obj.keys(recursive=False)):
#             # if there is a '.' the first part of k it will be a duplicate
#             tokens = k.split(".")
#             new_name = name if name else k
#             for t in tokens:
#                 if new_name.endswith(t):
#                     continue
#                 new_name = ".".join([new_name, t])
#             yield from _dir_walk(obj[k], new_name)


def inspect(input_file: str) -> pd.DataFrame:
    """
    Inspect the contents of a ROOT file and return a DataFrame with metadata.
    Args:
        input_file (str): Path to the ROOT file to inspect.
    Returns:
        pd.DataFrame: DataFrame containing metadata about the ROOT file contents.

        columns:
          name, type, interpretation, compressedbytes, uncompressedbytes, hasStreamer, uproot_readable, is_empty
    """
    f = uproot.open(input_file)

    data: list[Any] = []
    labels = [
        "name",
        "type",
        "interpretation",
        "compressedbytes",
        "uncompressedbytes",
        "hasStreamer",
        "uproot_readable",
        "is_empty",
    ]
    for name, obj in _walk(f):
        canRead = False
        is_empty = False
        typename = obj.typename if hasattr(obj, "typename") else "UNKNOWN"
        hasStreamer = hasattr(obj, "_streamer") and obj._streamer is not None
        interpretation = obj.interpretation if hasattr(obj, "interpretation") else None
        if not hasStreamer and interpretation is None:
            data.append(
                (
                    name,
                    typename,
                    interpretation,
                    np.nan,
                    np.nan,
                    hasStreamer,
                    canRead,
                    is_empty,
                )
            )
            continue

        try:
            a = obj.array()
            if a is None or len(a) == 0:
                is_empty = True
            # try to access first element
            if not is_empty:
                a[0]
            canRead = True
        except Exception as e:
            logger.warning(f"Cannot read {name} of type {typename}: {e}")
        data.append(
            (
                name,
                typename,
                interpretation,
                obj.compressed_bytes,
                obj.uncompressed_bytes,
                hasStreamer,
                canRead,
                is_empty,
            )
        )
    return pd.DataFrame.from_records(data, columns=labels)


def inspect_all(input_files: list[str]) -> pd.DataFrame:
    dfs = []
    for input_file in input_files:
        file_content = inspect(input_file)
        file_content["file"] = input_file
        dfs.append(file_content)
    return pd.concat(dfs, ignore_index=True)


def get_trees(input_file: str) -> Generator[str, None, None]:
    """
    Get the list of trees in a ROOT file.
    Args:
        input_file (str): Path to the ROOT file to inspect.
    Returns:
        list[str]: List of tree names in the ROOT file.
    """
    with uproot.open(input_file) as f:
        for name in f.keys(recursive=True):
            obj = f[name]
            if "TTree" in str(type(obj)):
                yield name
