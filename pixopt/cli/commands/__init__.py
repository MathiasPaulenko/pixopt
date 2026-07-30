"""Import all CLI commands so they register with Typer."""

from __future__ import annotations

from pixopt.cli.commands.batch import batch
from pixopt.cli.commands.compare import compare
from pixopt.cli.commands.convert import convert
from pixopt.cli.commands.favicon import favicon
from pixopt.cli.commands.info import info
from pixopt.cli.commands.optimize import optimize
from pixopt.cli.commands.placeholder import placeholder
from pixopt.cli.commands.srcset import srcset

__all__ = ["optimize", "batch", "convert", "favicon", "info", "compare", "srcset", "placeholder"]
