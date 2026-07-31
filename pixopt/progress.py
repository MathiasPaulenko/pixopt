"""Progress callback support for batch and directory operations.

Provides a :class:`ProgressInfo` dataclass and a callable protocol that
can be passed to ``optimize_directory`` and ``batch_optimize`` to receive
real-time progress updates.  This allows CLI progress bars and MCP
progress notifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["ProgressInfo", "ProgressCallback"]


@dataclass(frozen=True)
class ProgressInfo:
    """Information about the current progress of a batch operation."""

    current: int
    total: int
    current_file: Path
    success: bool
    message: str = ""

    @property
    def percent(self) -> float:
        """Completion percentage (0–100)."""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100.0

    @property
    def is_done(self) -> bool:
        """True when all files have been processed."""
        return self.current >= self.total


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress callback callables."""

    def __call__(self, info: ProgressInfo) -> None: ...
