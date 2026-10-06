"""PDF command: convert PDF to images and images to PDF."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import MAX_PDF_DPI
from pixopt.cli.app import app, console
from pixopt.pdf_io import PdfExportResult, PdfImportResult, images_to_pdf, pdf_to_images
from pixopt.utils import validate_no_parent_references

_DPI_OPT = Annotated[
    int,
    typer.Option(
        "--dpi",
        min=1,
        max=MAX_PDF_DPI,
        help=f"Render resolution in DPI (default 150, max {MAX_PDF_DPI}).",
    ),
]

_FORMAT_OPT = Annotated[
    str,
    typer.Option(
        "--format",
        "-f",
        help="Output image format: PNG, JPEG, WEBP.",
    ),
]

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output results as JSON.",
    ),
]


@app.command()
def pdf(
    source: Annotated[
        Path,
        typer.Argument(
            help="PDF file to convert (import) or output PDF path (export with --from-images).",
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Output directory (import) or output PDF file (export). "
                "Defaults to source stem directory."
            ),
        ),
    ] = None,
    dpi: _DPI_OPT = 150,
    fmt: _FORMAT_OPT = "PNG",
    from_images: Annotated[
        list[Path] | None,
        typer.Option(
            "--from-images",
            help="Image files to combine into a PDF. Repeat the option for multiple images.",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    json_output: _JSON_FLAG = False,
) -> None:
    """Convert PDF pages to images, or combine images into a PDF."""
    result: PdfExportResult | PdfImportResult
    try:
        if from_images:
            # Export mode: images → PDF
            out_path = output or source.with_suffix(".pdf")
            if error := validate_no_parent_references(out_path, "output"):
                console.print(f"[bold red]{error}[/bold red]")
                raise typer.Exit(1)
            result = images_to_pdf(from_images, out_path)

            if json_output:
                console.print_json(json.dumps(result.to_dict(), default=str))
                return

            if result.success:
                console.print(f"[bold green]PDF created:[/bold green] {result.output}")
                console.print(f"[bold cyan]Pages:[/bold cyan]          {result.page_count}")
            else:
                console.print(f"[bold red]Error:[/bold red] {result.error}")
                raise typer.Exit(1)
        else:
            # Import mode: PDF → images
            if not source.exists():
                console.print(f"[bold red]File not found:[/bold red] {source}")
                raise typer.Exit(1)
            out_dir = output or source.parent / source.stem
            if error := validate_no_parent_references(out_dir, "output"):
                console.print(f"[bold red]{error}[/bold red]")
                raise typer.Exit(1)
            result = pdf_to_images(source, out_dir, dpi=dpi, fmt=fmt)

            if json_output:
                console.print_json(json.dumps(result.to_dict(), default=str))
                return

            if result.success:
                console.print(f"[bold green]Extracted {result.total_pages} pages[/bold green]")
                console.print(f"[bold cyan]Output dir:[/bold cyan]    {out_dir}")
                for page in result.pages:
                    console.print(
                        f"  Page {page.page_number}: {page.width}x{page.height} → "
                        f"{page.output_path.name}",
                    )
            else:
                console.print(f"[bold red]Error:[/bold red] {result.error}")
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
