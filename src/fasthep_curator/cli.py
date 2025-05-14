"""Command Line Interface for fasthep-curator."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace as Dataset

import typer

from fasthep_curator import check, curate, inspect_all, write_yaml

app = typer.Typer(no_args_is_help=False)


class EventType(StrEnum):
    """Enumeration of event types."""

    data = "data"
    mc = "mc"


@app.command()
def compile(
    files: list[str],
    dataset: str = typer.Option(..., "--dataset", "-d", help="Name of the dataset"),
    event_type: str = EventType.data,
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    overwrite: bool = typer.Option(False, help="Overwrite existing files"),
) -> None:
    """
    Compile the given files into a single curator YAML file.

    Args:
        files (list[str]): List of file paths to compile.
        dataset (str): Name of the dataset.
        output (str): Output file path.
        overwrite (bool): Whether to overwrite existing files.
    """
    curated_data = curate(dataset, {"files": files, "event_type": str(event_type)})
    if Path(output).exists() and not overwrite:
        msg = f"Output file already exists: {output}"
        raise FileExistsError(msg)
    write_yaml(Dataset(**curated_data), output, append=not overwrite)


@app.command("check")
def check_configs(
    files: list[str],
    fields: list[str] = typer.Option(
        ["nfiles"], "--fields", "-f", help="List of fields to dump for each dataset"
    ),
    prefix: str = typer.Option(
        "", "--prefix", "-p", help="Choose one of the file prefixes to use"
    ),
) -> None:
    """
    Check the validity of the given files.

    Args:
        files (list[str]): List of file paths to check.
    """
    errors = check(files, prefix=prefix, fields=fields)
    if errors:
        msg = f"{len(errors)} errors have occurred"
        typer.echo(msg)
        raise typer.Exit(code=1)


@app.command()
def inspect(
    files: list[str],
    output: str | None = typer.Option(
        None, "--output", "-o", help="Name of output file list to expand things to"
    ),
) -> None:
    """
    Inspect the given files.

    Args:
        files (list[str]): List of file paths to inspect.
    """
    file_contents = inspect_all(files)
    if output is None:
        typer.echo(file_contents.to_markdown())
    file_contents.to_csv(output, index=False)


# @app.command()
# def select(
#     config: str = typer.Option(
#         ..., "--config", "-c", help="Path to the configuration file"
#     ),
#     datasets: list[str] | None = typer.Option(
#         None, "--datasets", "-d", help="List of datasets to select"
#     ),
#     files: list[str] | None = typer.Option(
#         None, "--files", "-f", help="List of files to select"
#     ),
# ) -> None:
#     """
#     Select datasets from the given configuration file.

#     Args:
#         config (str): Path to the curator configuration file.
#         datasets (list[str]|str): List of datasets to select.
#         files (list[str]): List of files to select.
#     """
#     # Perform the selection based on the provided configuration


def main() -> None:
    """
    Main function to run the CLI.
    """
    import sys

    from typer.main import get_command, get_command_name

    is_unknown_command = len(sys.argv) == 1 or sys.argv[1] not in [
        get_command_name(cmd) for cmd in get_command(app).commands
    ]

    if is_unknown_command and sys.argv[1] not in ["--help", "-h"]:
        typer.echo(
            "Enabling legacy behavior, please use `compile` command in the future."
        )
        sys.argv.insert(1, "compile")

    app()
