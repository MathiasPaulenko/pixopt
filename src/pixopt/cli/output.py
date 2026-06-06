"""Rich output formatting helpers for CLI results."""

from __future__ import annotations

from rich.table import Table

from pixopt.cli.app import console
from pixopt.models import OptimizationResult


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def _print_result(result: OptimizationResult) -> None:
    if not result.success:
        console.print(
            f"[bold red]Error optimizing {result.source_path.name}:[/bold red] {result.error}"
        )
        return

    table = Table(show_header=False, box=None)
    table.add_row("[bold green]Optimized[/bold green]", str(result.output_path))
    table.add_row("Original size", f"{result.human_original_size}")
    table.add_row("Optimized size", f"{result.human_optimized_size}")
    table.add_row("Savings", f"{result.human_savings} ({result.savings_percent:.1f}%)")
    table.add_row("Dimensions", f"{result.width}x{result.height}")
    table.add_row("Format", result.format)
    table.add_row("Metadata stripped", "Yes" if result.metadata_removed else "No")
    console.print(table)


def _print_summary(results: list[OptimizationResult]) -> None:
    table = Table(title="Optimization Summary")
    table.add_column("File", style="cyan")
    table.add_column("Original", justify="right")
    table.add_column("Optimized", justify="right")
    table.add_column("Savings", justify="right")
    table.add_column("Status")

    total_orig = 0
    total_opt = 0
    successes = 0

    for r in results:
        if r.success:
            total_orig += r.original_size
            total_opt += r.optimized_size
            successes += 1
            status = f"[green]OK[/green] ({r.savings_percent:.1f}%)"
        else:
            status = "[red]FAIL[/red]"
        table.add_row(
            r.source_path.name,
            r.human_original_size,
            r.human_optimized_size if r.success else "-",
            r.human_savings if r.success else "-",
            status,
        )

    console.print(table)

    if total_orig > 0:
        total_savings = total_orig - total_opt
        percent = total_savings / total_orig * 100
        console.print(
            f"\n[bold]Total:[/bold] {successes}/{len(results)} succeeded. "
            f"Saved {_human_size(total_savings)} ({percent:.1f}%)"
        )
