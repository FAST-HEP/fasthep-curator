from __future__ import annotations

from hepflow.model.hooks import HookSpec

DATASET_CONTEXT_HOOK_SPEC = HookSpec(
    name="hep.dataset_context",
    version="1.0",
    events=["partition_start"],
    context_outputs=[
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
)
