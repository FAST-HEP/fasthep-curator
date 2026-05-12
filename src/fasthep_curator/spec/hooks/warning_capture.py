from __future__ import annotations

from hepflow.model.hooks import HookSpec


WARNING_CAPTURE_HOOK_SPEC = HookSpec(
    name="hep.warning_capture",
    version="1.0",
    events=["around_node", "run_end"],
)
