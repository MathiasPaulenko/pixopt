"""srcset command — generate responsive image variants and HTML snippet."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import typer

from pixopt._units import MAX_IMAGE_DIMENSION, MAX_SRCSET_WIDTHS
from pixopt.cli.app import app, console
from pixopt.cli.options import (
    LosslessOption,
    OptimizeOption,
    ProgressiveOption,
    QualityOption,
    StripOption,
)
from pixopt.srcset_generator import generate_srcset_images
from pixopt.utils import validate_no_parent_references


@app.command()
def srcset(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    sizes: Annotated[
        str,
        typer.Option(
            "--sizes",
            "-s",
            help="Comma-separated target widths in pixels (e.g. 320,640,1024,1920).",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory where variants will be saved.",
        ),
    ] = Path("output/responsive"),
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: webp, jpeg, png, avif.",
        ),
    ] = "webp",
    quality: QualityOption = 85,
    strip: StripOption = True,
    progressive: ProgressiveOption = True,
    optimize_flag: OptimizeOption = True,
    lossless: LosslessOption = False,
    html: Annotated[
        Path | None,
        typer.Option(
            "--html",
            help="Write the <img> srcset HTML snippet to a file.",
        ),
    ] = None,
) -> None:
    """Generate responsive image variants and an optional HTML srcset snippet."""
    if error := validate_no_parent_references(output_dir, "output_dir"):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)
    if html is not None and (error := validate_no_parent_references(html, "html")):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)
    output_dir = output_dir.resolve()

    valid_formats = {"webp", "jpeg", "png", "avif"}
    if fmt.lower() not in valid_formats:
        console.print("[bold red]Invalid --format. Use: webp, jpeg, png, avif.[/bold red]")
        raise typer.Exit(1)

    try:
        widths = [int(w.strip()) for w in sizes.split(",") if w.strip()]
    except ValueError:
        console.print(
            "[bold red]Invalid --sizes value. Use comma-separated integers.[/bold red]",
        )
        raise typer.Exit(1) from None

    if not widths:
        console.print("[bold red]No valid widths provided.[/bold red]")
        raise typer.Exit(1)

    if len(widths) > MAX_SRCSET_WIDTHS:
        console.print(f"[bold red]Too many widths (max {MAX_SRCSET_WIDTHS}).[/bold red]")
        raise typer.Exit(1)

    if any(w < 1 or w > MAX_IMAGE_DIMENSION for w in widths):
        console.print(f"[bold red]Widths must be between 1 and {MAX_IMAGE_DIMENSION}.[/bold red]")
        raise typer.Exit(1)

    variants = generate_srcset_images(
        source,
        output_dir,
        widths,
        quality=quality,
        output_format=fmt,
        strip_metadata=strip,
        progressive=progressive,
        optimize=optimize_flag,
        lossless=lossless,
    )

    if not variants:
        console.print("[bold red]No variants generated.[/bold red]")
        raise typer.Exit(1)

    # Build srcset attribute string relative to the HTML output location.
    html_parent = html.resolve().parent if html is not None else output_dir.parent

    def _html_src(path: Path) -> str:
        if path.is_relative_to(html_parent):
            raw = path.relative_to(html_parent).as_posix()
        else:
            raw = path.as_posix()
        return escape(quote(raw, safe="/"))

    srcset_parts: list[str] = []
    for v in variants:
        srcset_parts.append(f"{_html_src(v.output_path)} {v.width}w")

    srcset_str = ", ".join(srcset_parts)
    largest = variants[-1]
    src = _html_src(largest.output_path)

    html_snippet = (
        f'<img src="{src}"\n'
        f'     srcset="{srcset_str}"\n'
        f'     sizes="(max-width: {largest.width}px) 100vw, {largest.width}px"\n'
        f'     alt=""\n'
        f'     loading="lazy"\n'
        f'     decoding="async">'
    )

    console.print(f"[bold green]Generated {len(variants)} variants in {output_dir}[/bold green]")
    for v in variants:
        size_kb = v.size_bytes / 1024
        console.print(f"  {v.output_path.name}  —  {v.width}px  ({size_kb:.1f} KB)")

    console.print("\n[bold]HTML snippet:[/bold]")
    console.print(html_snippet)

    if html is not None:
        if error := validate_no_parent_references(html, "html"):
            console.print(f"[bold red]{error}[/bold red]")
            raise typer.Exit(1)
        html = html.resolve()
        html.write_text(html_snippet + "\n", encoding="utf-8")
        console.print(f"\n[bold green]Snippet saved to[/bold green] {html}")
