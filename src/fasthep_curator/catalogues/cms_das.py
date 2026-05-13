"""
Implements a curator-catalogue to CMS' DAS based on the dasgoclient command
"""

from __future__ import annotations

from typing import Any

from plumbum import CommandNotFound, ProcessExecutionError, local

from .common import check_entries_uproot

_dasgoclient_prog = "dasgoclient"
_proxyinfo_prog = "voms-proxy-info"
_default_prefix = "root://cms-xrd-global.cern.ch//"


def _check_proxy() -> RuntimeError | None:
    try:
        check_proxy = local[_proxyinfo_prog]
    except CommandNotFound as e:
        if _proxyinfo_prog in str(e):
            msg = f"{_proxyinfo_prog} program not found, please set up necessary CMS environment"
            return RuntimeError(msg)
    try:
        check_proxy = check_proxy["-exists", "-valid", "1:00"]()
    except ProcessExecutionError as e:
        if "Couldn't find a valid proxy." in str(e):
            msg = "No valid VOMS proxy configured.  Please run `voms-proxy-init --voms cms`"
            return RuntimeError(msg)
    return None


def _check_dasgoclient() -> RuntimeError | None:
    try:
        local[_dasgoclient_prog]
    except CommandNotFound as e:
        if _dasgoclient_prog in str(e):
            msg = f"{_dasgoclient_prog} program not found, please set up necessary CMS environment"
            return RuntimeError(msg)
    return None


class CMSDASExpander:
    """
    Implements a curator-catalogue to CMS' DAS based on the dasgoclient command
    """

    @staticmethod
    def check_setup() -> bool:
        """
        Check if the dasgoclient and voms-proxy-info programs are available
        and if a valid VOMS proxy is configured.
        """
        error = _check_dasgoclient()
        if error:
            raise error

        error = _check_proxy()
        if error:
            raise error
        return True

    @staticmethod
    def expand_file_list(datasets: list[str], prefix: str | None = None) -> list[str]:
        """
        Expand a list of datasets to a list of file paths using dasgoclient.
        If prefix is not provided, it defaults to the CERN XRootD global prefix.
        """
        if not prefix:
            prefix = _default_prefix

        files = []
        dasgoclient = local[_dasgoclient_prog]
        for dataset in datasets:
            query = f"-query=file dataset={dataset}"
            params = [query, "-limit", "0", "-unique"]
            das_result = dasgoclient[params]
            files += [prefix + f for f in das_result.split("\n") if f]
        return files

    @staticmethod
    def check_files(
        *args: list[Any], **kwargs: dict[str, Any]
    ) -> tuple[list[str], dict[str, Any] | int, dict[str, Any]]:
        return check_entries_uproot(*args, **kwargs)  # type: ignore[arg-type]
