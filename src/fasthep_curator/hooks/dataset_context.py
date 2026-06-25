from __future__ import annotations

from typing import Any

from hepflow.model.hooks import ExecutionHook

DATASET_CONTEXT_HOOK_SPEC = {
    "name": "hep.dataset_context",
    "kind": "hook",
    "version": "1.0",
    "lifecycle": {"events": ["partition_start"]},
    "context_outputs": [
        "dataset",
        "dataset_name",
        "dataset_eventtype",
        "dataset_group",
        "dataset_is_data",
        "dataset_xs",
        "dataset_nevents",
        "dataset_n_unskimmed_events",
        "dataset_filter_efficiency",
    ],
}


class DatasetContextHook(ExecutionHook):
    name = "hep.dataset_context"

    def partition_start(self, *, partition, ctx: dict[str, Any]) -> None:
        if partition is None:
            return
        partition_ctx = (
            partition.to_context()
            if hasattr(partition, "to_context")
            else dict(partition)
        )
        datasets = dict(ctx.get("datasets") or {})
        dataset_name = str(partition_ctx.get("dataset") or "")
        dataset = dict(datasets.get(dataset_name) or {"name": dataset_name})
        meta = dict(dataset.get("meta") or {})
        process = dataset.get("process", dataset.get("eventtype"))
        xs = dataset.get("xs", meta.get("xs"))
        n_unskimmed_events = dataset.get(
            "n_unskimmed_events",
            meta.get("n_unskimmed_events"),
        )
        filter_efficiency = dataset.get(
            "filter_efficiency",
            meta.get("filter_efficiency"),
        )
        # globals should overwrite DatasetContext
        globals_block = dict(ctx.get("globals") or {})
        ctx.update(globals_block)
        ctx["partition"] = partition_ctx
        ctx["dataset_name"] = dataset_name
        ctx["dataset"] = dataset
        ctx["dataset_eventtype"] = process
        ctx["dataset_group"] = dataset.get("group", meta.get("group"))
        ctx["dataset_nevents"] = dataset.get("nevents", meta.get("nevents"))
        ctx["dataset_is_data"] = str(process).lower() == "data"
        if xs is not None:
            ctx["dataset_xs"] = float(xs)
        if n_unskimmed_events is not None:
            ctx["dataset_n_unskimmed_events"] = n_unskimmed_events
        if filter_efficiency is not None:
            ctx["dataset_filter_efficiency"] = filter_efficiency
