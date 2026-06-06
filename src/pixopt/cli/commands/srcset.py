"""srcset command — generate responsive image variants and HTML snippet."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.cli.options import (
    LosslessOption,
    OptimizeOption,
    ProgressiveOption,
    QualityOption,
    StripOption,
)
from pixopt.srcset_generator import generate_srcset_images


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
    ] = Path("./responsive"),
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
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        widths = [int(w.strip()) for w in sizes.split(",") if w.strip()]
    except ValueError:
        console.print(
            "[bold red]Invalid --sizes value. Use comma-separated integers.[/bold red]"
        )
        raise typer.Exit(1) from None

    if not widths:
        console.print("[bold red]No valid widths provided.[/bold red]")
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

    # Build srcset attribute string
    srcset_parts: list[str] = []
    for v in variants:
        if v.output_path.is_relative_to(output_dir.parent):
            rel = str(v.output_path.relative_to(output_dir.parent))
        else:
            rel = v.output_path.name
        srcset_parts.append(f"{rel} {v.width}w")

    srcset_str = ", ".join(srcset_parts)
    largest = variants[-1]

    html_snippet = (
        f'<img src="{largest.output_path.name}"\n'
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
        html = html.resolve()
        html.write_text(html_snippet + "\n", encoding="utf-8")
        console.print(f"\n[bold green]Snippet saved to[/bold green] {html}")
