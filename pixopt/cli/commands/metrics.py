"""Metrics command: compare image quality (SSIM / PSNR)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.cli.options import OutputFormatOption
from pixopt.quality import compare_images


@app.command()
def metrics(
    original: Annotated[
        Path,
        typer.Argument(
            help="Original image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    compared: Annotated[
        Path,
        typer.Argument(
            help="Image to compare against the original.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output_fmt: OutputFormatOption = "table",
) -> None:
    """Compare two images and report SSIM, PSNR, and MSE quality metrics."""
    try:
        result = compare_images(original, compared)
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if output_fmt == "json":
        console.print_json(json.dumps(result.to_dict(), default=str))
        return

    console.print(f"[bold cyan]Original:[/bold cyan]    {result.original_path}")
    console.print(f"[bold cyan]Compared:[/bold cyan]     {result.compared_path}")
    console.print(
        f"[bold cyan]Dimensions:[/bold cyan]  {result.width}x{result.height} px",
    )
    console.print(f"[bold cyan]SSIM:[/bold cyan]         {result.ssim:.4f}")
    if result.psnr is not None:
        console.print(f"[bold cyan]PSNR:[/bold cyan]          {result.psnr:.2f} dB")
    else:
        console.print("[bold cyan]PSNR:[/bold cyan]          \u221e (identical)")
    console.print(f"[bold cyan]MSE:[/bold cyan]            {result.mse:.4f}")
    console.print(f"[bold cyan]Verdict:[/bold cyan]       {result.verdict}")
