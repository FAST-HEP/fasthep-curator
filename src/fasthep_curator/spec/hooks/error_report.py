from __future__ import annotations

from hepflow.model.hooks import HookSpec

ERROR_REPORT_HOOK_SPEC = HookSpec(
    name="hep.error_report",
    version="1.0",
    events=["on_node_error"],
)
