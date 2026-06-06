"""Import all CLI commands so they register with Typer."""

from __future__ import annotations

from optimg.cli.commands.batch import batch
from optimg.cli.commands.compare import compare
from optimg.cli.commands.convert import convert
from optimg.cli.commands.favicon import favicon
from optimg.cli.commands.info import info
from optimg.cli.commands.optimize import optimize
from optimg.cli.commands.placeholder import placeholder
from optimg.cli.commands.srcset import srcset

__all__ = ["optimize", "batch", "convert", "favicon", "info", "compare", "srcset", "placeholder"]
