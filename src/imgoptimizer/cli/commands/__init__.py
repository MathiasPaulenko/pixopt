"""Import all CLI commands so they register with Typer."""

from __future__ import annotations

from imgoptimizer.cli.commands.batch import batch
from imgoptimizer.cli.commands.compare import compare
from imgoptimizer.cli.commands.convert import convert
from imgoptimizer.cli.commands.favicon import favicon
from imgoptimizer.cli.commands.info import info
from imgoptimizer.cli.commands.optimize import optimize
from imgoptimizer.cli.commands.placeholder import placeholder
from imgoptimizer.cli.commands.srcset import srcset

__all__ = ["optimize", "batch", "convert", "favicon", "info", "compare", "srcset", "placeholder"]
