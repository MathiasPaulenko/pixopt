"""CLI package entry-point."""

from __future__ import annotations

from imgoptimizer.cli.app import app
from imgoptimizer.cli.commands import batch  # noqa: F401
from imgoptimizer.cli.commands import compare  # noqa: F401
from imgoptimizer.cli.commands import convert  # noqa: F401
from imgoptimizer.cli.commands import favicon  # noqa: F401
from imgoptimizer.cli.commands import info  # noqa: F401
from imgoptimizer.cli.commands import optimize  # noqa: F401
from imgoptimizer.cli.commands import placeholder  # noqa: F401
from imgoptimizer.cli.commands import srcset  # noqa: F401

__all__ = ["app"]
