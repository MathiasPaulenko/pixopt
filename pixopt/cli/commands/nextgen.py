"""Next-gen command: detect and convert to next-generation formats."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.nextgen import (
    convert_to_nextgen,
    detect_format_support,
)
from pixopt.utils import validate_no_parent_references

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output results as JSON.",
    ),
]


@app.command(name="nextgen")
def nextgen_cmd(
    action: Annotated[
        str,
        typer.Argument(
            help="Action: 'detect' to check format support, 'convert' to convert an image.",
        ),
    ] = "detect",
    source: Annotated[
        Path | None,
        typer.Argument(
            help="Source image path (for 'convert' action).",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path for converted image.",
        ),
    ] = None,
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Target format: jxl or webp2.",
        ),
    ] = "jxl",
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", help="Quality (1-100)."),
    ] = 85,
    no_fallback: Annotated[
        bool,
        typer.Option(
            "--no-fallback",
            help="Disable fallback to WEBP when target format is not supported.",
        ),
    ] = False,
    fallback_format: Annotated[
        str,
        typer.Option(
            "--fallback-format",
            help="Fallback format (default: webp).",
        ),
    ] = "webp",
    json_output: _JSON_FLAG = False,
) -> None:
    """Detect next-gen format support or convert images to next-gen formats."""
    try:
        if action == "detect":
            support = detect_format_support()

            if json_output:
                console.print_json(json.dumps(support.to_dict()))
                return

            console.print("[bold cyan]Next-generation format support:[/bold cyan]\n")
            for f in support.formats:
                status = (
                    "[bold green]✓ supported[/bold green]"
                    if f.supported
                    else "[bold red]✗ not supported[/bold red]"
                )
                console.print(f"  [bold]{f.format.upper()}[/bold] {status}")
                if f.plugin:
                    console.print(f"    Plugin: {f.plugin}")
                if f.version:
                    console.print(f"    Version: {f.version}")
                if f.note:
                    console.print(f"    [dim]{f.note}[/dim]")
                console.print()

        elif action == "convert":
            if source is None:
                console.print(
                    "[bold red]Error:[/bold red] Source image path required for 'convert' action."
                )
                raise typer.Exit(1)

            out_path = output or source.with_suffix(f".{fmt}")
            if error := validate_no_parent_references(out_path, "output"):
                console.print(f"[bold red]{error}[/bold red]")
                raise typer.Exit(1)
            result = convert_to_nextgen(
                source,
                out_path,
                fmt=fmt,
                quality=quality,
                fallback=not no_fallback,
                fallback_format=fallback_format,
            )

            if json_output:
                console.print_json(json.dumps(result.to_dict(), default=str))
                return

            if result.success:
                if result.fallback:
                    console.print(
                        f"[bold yellow]Format '{fmt}' not supported. "
                        f"Fell back to {result.fallback_format}.[/bold yellow]"
                    )
                else:
                    console.print(
                        f"[bold green]Converted to {fmt.upper()}:[/bold green] {result.output}"
                    )
                console.print(
                    f"[bold cyan]Original size:[/bold cyan]  {result.original_size} bytes"
                )
                console.print(f"[bold cyan]Output size:[/bold cyan]    {result.output_size} bytes")
                console.print(
                    f"[bold cyan]Savings:[/bold cyan]       {result.savings_bytes} bytes "
                    f"({result.savings_percent:.1f}%)"
                )
            else:
                console.print(f"[bold red]Error:[/bold red] {result.error}")
                raise typer.Exit(1)

        else:
            console.print(
                f"[bold red]Unknown action:[/bold red] {action}. Use 'detect' or 'convert'."
            )
            raise typer.Exit(1)

    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
