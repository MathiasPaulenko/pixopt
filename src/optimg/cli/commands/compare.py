"""compare command — generate an interactive HTML before/after slider."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from optimg.cli.app import app, console
from optimg.cli.options import (
    FormatChoices,
    HeightOption,
    LosslessOption,
    OptimizeOption,
    ProgressiveOption,
    QualityOption,
    StripOption,
    WidthOption,
)
from optimg.html_comparison import generate_comparison_html
from optimg.models import OutputFormat
from optimg.optimizer import optimize_image


@app.command()
def compare(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output_html: Annotated[
        Path,
        typer.Argument(
            help="Output HTML comparison file.",
            exists=False,
        ),
    ] = Path("comparison.html"),  # type: ignore[assignment]
    width: WidthOption = None,
    height: HeightOption = None,
    quality: QualityOption = 85,
    fmt: FormatChoices = OutputFormat.AUTO,
    strip: StripOption = True,
    progressive: ProgressiveOption = True,
    optimize_flag: OptimizeOption = True,
    lossless: LosslessOption = False,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open/--no-open",
            help="Open the generated HTML in the default browser.",
        ),
    ] = False,
) -> None:
    """Optimize an image and generate an interactive before/after comparison HTML."""
    import tempfile
    import webbrowser

    output_html = output_html.resolve()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        optimized = tmp_path / f"opt{source.suffix}"
        result = optimize_image(
            source,
            optimized,
            max_width=width,
            max_height=height,
            quality=quality,
            strip_metadata=strip,
            output_format=fmt,
            progressive=progressive,
            optimize=optimize_flag,
            lossless=lossless,
        )

        if not result.success:
            console.print(f"[bold red]Optimization failed:[/bold red] {result.error}")
            raise typer.Exit(1)

        generate_comparison_html(
            before_path=source,
            after_path=optimized,
            output_html=output_html,
            title=f"Comparison — {source.name}",
        )

    console.print(f"[bold green]Comparison saved to[/bold green] {output_html}")
    if open_browser:
        webbrowser.open(f"file://{output_html}")
