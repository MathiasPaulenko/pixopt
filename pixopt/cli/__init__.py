"""CLI package entry-point."""

from __future__ import annotations

from pixopt.cli.app import app
from pixopt.cli.commands import (
    batch,  # noqa: F401
    compare,  # noqa: F401
    convert,  # noqa: F401
    favicon,  # noqa: F401
    info,  # noqa: F401
    optimize,  # noqa: F401
    placeholder,  # noqa: F401
    srcset,  # noqa: F401
)

__all__ = ["app"]
