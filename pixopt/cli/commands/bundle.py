"""Bundle command: generate all assets from one source image."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import MAX_BUNDLE_PALETTE_N, MAX_IMAGE_DIMENSION
from pixopt.bundle import BundleOptions, generate_asset_bundle
from pixopt.cli.app import app, console
from pixopt.cli.options import OutputFormatOption, QualityOption
from pixopt.utils import validate_no_parent_references


@app.command()
def bundle(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Output directory for all generated assets.",
        ),
    ] = Path("./assets"),
    quality: QualityOption = 85,
    hero_width: Annotated[
        int,
        typer.Option(
            "--hero-width",
            min=1,
            max=MAX_IMAGE_DIMENSION,
            help="Hero image max width in pixels.",
        ),
    ] = 1920,
    thumbnail_width: Annotated[
        int,
        typer.Option(
            "--thumbnail-width",
            min=1,
            max=MAX_IMAGE_DIMENSION,
            help="Thumbnail max width in pixels.",
        ),
    ] = 300,
    og_width: Annotated[
        int,
        typer.Option(
            "--og-width", min=1, max=MAX_IMAGE_DIMENSION, help="og:image width in pixels."
        ),
    ] = 1200,
    og_height: Annotated[
        int,
        typer.Option(
            "--og-height", min=1, max=MAX_IMAGE_DIMENSION, help="og:image height in pixels."
        ),
    ] = 630,
    palette_n: Annotated[
        int,
        typer.Option(
            "--palette-n",
            min=1,
            max=MAX_BUNDLE_PALETTE_N,
            help="Number of palette colors to extract.",
        ),
    ] = 6,
    no_hero: Annotated[
        bool,
        typer.Option("--no-hero", help="Skip hero image generation."),
    ] = False,
    no_thumbnail: Annotated[
        bool,
        typer.Option("--no-thumbnail", help="Skip thumbnail generation."),
    ] = False,
    no_og: Annotated[
        bool,
        typer.Option("--no-og", help="Skip og:image generation."),
    ] = False,
    no_favicon: Annotated[
        bool,
        typer.Option("--no-favicon", help="Skip favicon generation."),
    ] = False,
    no_srcset: Annotated[
        bool,
        typer.Option("--no-srcset", help="Skip srcset generation."),
    ] = False,
    no_lqip: Annotated[
        bool,
        typer.Option("--no-lqip", help="Skip LQIP generation."),
    ] = False,
    no_blurhash: Annotated[
        bool,
        typer.Option("--no-blurhash", help="Skip blurhash generation."),
    ] = False,
    no_palette: Annotated[
        bool,
        typer.Option("--no-palette", help="Skip palette extraction."),
    ] = False,
    no_dominant_color: Annotated[
        bool,
        typer.Option("--no-dominant-color", help="Skip dominant color extraction."),
    ] = False,
    output_fmt: OutputFormatOption = "table",
) -> None:
    """Generate hero, thumbnail, og:image, favicon, srcset, LQIP,
    blurhash and palette from one image.
    """
    if error := validate_no_parent_references(output_dir, "output_dir"):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)

    options = BundleOptions(
        hero_width=hero_width,
        thumbnail_width=thumbnail_width,
        og_width=og_width,
        og_height=og_height,
        palette_n=palette_n,
        quality=quality,
        generate_hero=not no_hero,
        generate_thumbnail=not no_thumbnail,
        generate_og=not no_og,
        generate_favicon=not no_favicon,
        generate_srcset=not no_srcset,
        generate_lqip=not no_lqip,
        generate_blurhash=not no_blurhash,
        generate_palette=not no_palette,
        generate_dominant_color=not no_dominant_color,
    )

    try:
        result = generate_asset_bundle(source, output_dir, options=options)
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if output_fmt == "json":
        console.print_json(json.dumps(result.to_dict(), default=str))
        return

    console.print(f"[bold cyan]Source:[/bold cyan]       {result.source_path}")
    console.print(f"[bold cyan]Output dir:[/bold cyan]   {result.output_dir}")
    console.print()

    if result.hero:
        status = "OK" if result.hero.success else "FAILED"
        console.print(
            f"[bold]Hero[/bold]         {status}  {result.hero.output_path.name}  "
            f"({result.hero.optimized_size} bytes)"
        )
    if result.thumbnail:
        status = "OK" if result.thumbnail.success else "FAILED"
        console.print(
            f"[bold]Thumbnail[/bold]    {status}  {result.thumbnail.output_path.name}  "
            f"({result.thumbnail.optimized_size} bytes)"
        )
    if result.og_image:
        status = "OK" if result.og_image.success else "FAILED"
        console.print(
            f"[bold]og:image[/bold]     {status}  {result.og_image.output_path.name}  "
            f"({result.og_image.optimized_size} bytes)"
        )
    if result.favicon:
        status = "OK" if result.favicon.success else "FAILED"
        console.print(
            f"[bold]Favicon[/bold]      {status}  {result.favicon.output_path.name}  "
            f"({result.favicon.optimized_size} bytes)"
        )
    if result.srcset_images:
        console.print(f"[bold]Srcset[/bold]        {len(result.srcset_images)} variants")
        for s in result.srcset_images:
            console.print(f"  {s.width}w  {s.output_path.name}  ({s.size_bytes} bytes)")
    if result.lqip_data_uri:
        uri_len = len(result.lqip_data_uri)
        console.print(f"[bold]LQIP[/bold]          data URI ({uri_len} chars)")
    if result.blurhash:
        console.print(f"[bold]Blurhash[/bold]      {result.blurhash}")
    if result.dominant_color:
        console.print(f"[bold]Dominant color[/bold]  {result.dominant_color}")
    if result.palette:
        colors = ", ".join(c.hex for c in result.palette.colors)
        console.print(f"[bold]Palette[/bold]       {colors}")
