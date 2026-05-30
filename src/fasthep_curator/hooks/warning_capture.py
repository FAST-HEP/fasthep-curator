from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any

from hepflow.model.hooks import ExecutionHook, HookSpec

WARNING_CAPTURE_HOOK_SPEC = HookSpec(
    name="hep.warning_capture",
    version="1.0",
    events=["around_node", "run_end"],
)


class WarningCaptureHook(ExecutionHook):
    name = "hep.warning_capture"

    def __init__(self, *, always: bool = True) -> None:
        self.always = bool(always)
        self.records: list[dict[str, Any]] = []

    @contextmanager
    def around_node(self, *, node, inputs: dict[str, Any], ctx: dict[str, Any]):
        del inputs
        with warnings.catch_warnings(record=True) as caught:
            if self.always:
                warnings.simplefilter("always")
            yield

        partition = ctx.get("partition") or {}
        if not isinstance(partition, dict):
            partition = {}
        for item in caught:
            record = {
                "node_id": node.id,
                "role": node.role,
                "impl": node.impl,
                "category": item.category.__name__,
                "message": str(item.message),
                "filename": item.filename,
                "lineno": item.lineno,
                "partition_id": partition.get("id"),
                "dataset_name": ctx.get("dataset_name"),
            }
            if partition:
                record["partition"] = dict(partition)
            self.records.append(record)
            ctx.setdefault("_warnings", []).append(record)

    def run_end(self, *, plan, ctx: dict[str, Any], summary: dict[str, Any]) -> None:
        del plan, ctx
        summary.setdefault("warnings", list(self.records))

    def summary(self) -> dict[str, Any]:
        return {"warnings": list(self.records)}
