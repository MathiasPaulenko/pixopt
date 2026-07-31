"""Import all CLI commands so they register with Typer."""

from __future__ import annotations

from pixopt.cli.commands.batch import batch
from pixopt.cli.commands.benchmark import benchmark
from pixopt.cli.commands.bundle import bundle
from pixopt.cli.commands.compare import compare
from pixopt.cli.commands.convert import convert
from pixopt.cli.commands.duplicates import duplicates
from pixopt.cli.commands.favicon import favicon
from pixopt.cli.commands.info import info
from pixopt.cli.commands.metrics import metrics
from pixopt.cli.commands.nextgen import nextgen_cmd as nextgen
from pixopt.cli.commands.optimize import optimize
from pixopt.cli.commands.palette import palette
from pixopt.cli.commands.pdf import pdf
from pixopt.cli.commands.placeholder import placeholder
from pixopt.cli.commands.scan import scan
from pixopt.cli.commands.sprite import sprite
from pixopt.cli.commands.srcset import srcset
from pixopt.cli.commands.watermark import watermark

__all__ = [
    "batch",
    "benchmark",
    "bundle",
    "compare",
    "convert",
    "duplicates",
    "favicon",
    "info",
    "metrics",
    "nextgen",
    "optimize",
    "palette",
    "pdf",
    "placeholder",
    "scan",
    "sprite",
    "srcset",
    "watermark",
]
