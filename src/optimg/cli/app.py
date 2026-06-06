"""Typer application and Rich console instances."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="optimg",
    help="Optimize images for web and storage.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
