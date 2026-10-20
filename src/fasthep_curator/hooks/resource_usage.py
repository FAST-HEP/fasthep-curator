from __future__ import annotations

import resource
import time
from pathlib import Path
from typing import Any

from hepflow.model.hooks import ExecutionHook

RESOURCE_USAGE_HOOK_SPEC = {
    "name": "hep.resource_usage",
    "kind": "hook",
    "version": "1.0",
    "lifecycle": {"events": ["partition_start", "partition_end"]},
}

_PROC_STATUS = Path("/proc/self/status")
_PROC_CLEAR_REFS = Path("/proc/self/clear_refs")


class ResourceUsageHook(ExecutionHook):
    """Record wall time, CPU time and peak memory of every partition.

    ``max_rss_mb`` is the peak resident set size while the partition ran. It is
    per partition when the kernel lets the peak be reset (Linux
    ``/proc/self/clear_refs``); otherwise it is the peak of the whole process so
    far and ``max_rss_scope`` says ``process``. CPU times are deltas of
    ``getrusage(RUSAGE_SELF)`` and cover all threads of the process.
    """

    name = "hep.resource_usage"

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self.records: list[dict[str, Any]] = []
        self._started: dict[str, dict[str, Any]] = {}

    def partition_start(self, *, partition, ctx: dict[str, Any]) -> None:
        del ctx
        usage = resource.getrusage(resource.RUSAGE_SELF)
        self._started[_partition_id(partition)] = {
            "wall": time.perf_counter(),
            "user": usage.ru_utime,
            "sys": usage.ru_stime,
            "peak_reset": _reset_peak_rss(),
        }

    def partition_end(self, *, partition, ctx: dict[str, Any], value_store) -> None:
        del value_store
        partition_id = _partition_id(partition)
        start = self._started.pop(partition_id, None)
        if start is None:
            return
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak_mb = _peak_rss_mb() if start["peak_reset"] else None
        scope = "partition"
        if peak_mb is None:
            peak_mb = usage.ru_maxrss / 1024.0  # kilobytes on Linux
            scope = "process"
        record: dict[str, Any] = {
            "partition_id": partition_id,
            "dataset_name": ctx.get("dataset_name"),
            "wall_time_s": round(time.perf_counter() - start["wall"], 3),
            "cpu_user_s": round(usage.ru_utime - start["user"], 3),
            "cpu_sys_s": round(usage.ru_stime - start["sys"], 3),
            "max_rss_mb": round(peak_mb, 1),
            "max_rss_scope": scope,
        }
        self.records.append(record)

    def results(self) -> dict[str, Any]:
        return {"resource_usage": list(self.records)}


def _partition_id(partition: Any) -> str:
    if partition is None:
        return ""
    if isinstance(partition, dict):
        return str(partition.get("id") or "")
    return str(getattr(partition, "id", "") or "")


def _reset_peak_rss() -> bool:
    """Reset the kernel's peak RSS counter; False when not permitted."""
    try:
        with _PROC_CLEAR_REFS.open("w") as handle:
            handle.write("5")
    except OSError:
        return False
    return True


def _peak_rss_mb() -> float | None:
    try:
        with _PROC_STATUS.open() as handle:
            for line in handle:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024.0
    except (OSError, ValueError, IndexError):
        pass
    return None
