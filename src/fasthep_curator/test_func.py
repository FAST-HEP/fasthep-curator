from __future__ import annotations

from typing import Any


def add_user(dataset: dict[str, Any]) -> None:
    """
    Add a user to the dataset.
    """
    dataset["user"] = dataset["name"]
