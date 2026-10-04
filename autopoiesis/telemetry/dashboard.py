"""
Visual Real-Time Terminal Dashboard & Telemetry Display.

Renders live updates of generational evolution, active phenotypes, speedup curves,
and genetic lineage graphs.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from autopoiesis.core.chromosome import Chromosome, LineageDAG
from autopoiesis.telemetry.metrics import GenerationMetric, TelemetryTracker


class TerminalDashboard:
    """Renders real-time evolutionary status and telemetry to the console."""

    def __init__(self) -> None:
        self.console = Console() if RICH_AVAILABLE else None

    def render_evolution_frame(
        self,
        organism_name: str,
        current_generation: int,
        status: str,
        active_chromosome: Optional[Chromosome],
        lineage_dag: LineageDAG,
        tracker: TelemetryTracker,
    ) -> None:
        """Renders a complete telemetry frame for the current generation."""
        if not RICH_AVAILABLE or not self.console:
            self._render_ansi_frame(
                organism_name, current_generation, status, active_chromosome, lineage_dag, tracker
            )
            return

        # Main Title Panel
        title_text = Text()
        title_text.append(" DIGITAL AUTOPOIESIS ", style="bold white on blue")
        title_text.append(f"  Organism: {organism_name} | State: {status} | Gen: {current_generation}", style="bold green")

        # Table of Active Phenotypes & Generational History
        table = Table(title="Phenotypic Generational History", box=box.ROUNDED, expand=True)
        table.add_column("Gen", justify="center", style="cyan", no_wrap=True)
        table.add_column("Chromosome ID", justify="center", style="yellow")
        table.add_column("Type", justify="center", style="magenta")
        table.add_column("Mutator", justify="left", style="green")
        table.add_column("Latency (ms)", justify="right", style="white")
        table.add_column("Speedup", justify="right", style="bold green")
        table.add_column("Memory (MB)", justify="right", style="dim")

        for m in tracker.metrics:
            is_active = active_chromosome and m.chromosome_id == active_chromosome.id
            active_marker = " *" if is_active else ""
            table.add_row(
                str(m.generation),
                f"{m.chromosome_id}{active_marker}",
                m.source_type,
                m.mutator_name,
                f"{m.latency_ns / 1e6:.3f}",
                f"{m.speedup_vs_baseline:.2f}x",
                f"{m.memory_rss_mb:.1f}",
            )

        # ASCII Speedup Gauge
        speedup_bars = []
        for m in tracker.metrics:
            bar_len = min(40, max(1, int(m.speedup_vs_baseline * 2)))
            bar = "#" * bar_len
            speedup_bars.append(f"Gen {m.generation:02d} [{m.source_type:11s}]: {bar} {m.speedup_vs_baseline:.2f}x")
        gauge_str = "\n".join(speedup_bars) if speedup_bars else "Waiting for generation..."

        gauge_panel = Panel(gauge_str, title="[bold]Empirical Speedup Trajectory[/bold]", border_style="cyan")

        # Lineage Tree Text
        lineage_str = lineage_dag.render_ascii_tree()
        lineage_panel = Panel(lineage_str, title="[bold]Genetic Lineage & Apoptosis DAG[/bold]", border_style="green")

        group = Group(
            Panel(title_text, border_style="blue"),
            table,
            gauge_panel,
            lineage_panel,
        )
        self.console.print(group)

    def _render_ansi_frame(
        self,
        organism_name: str,
        current_generation: int,
        status: str,
        active_chromosome: Optional[Chromosome],
        lineage_dag: LineageDAG,
        tracker: TelemetryTracker,
    ) -> None:
        print("\n" + "=" * 70)
        print(f" DIGITAL AUTOPOIESIS | Organism: {organism_name} | State: {status} | Gen: {current_generation}")
        print("=" * 70)
        print(f"{'Gen':<4} {'ID':<10} {'Type':<14} {'Latency (ms)':<14} {'Speedup':<10}")
        print("-" * 70)
        for m in tracker.metrics:
            print(f"{m.generation:<4} {m.chromosome_id:<10} {m.source_type:<14} {m.latency_ns/1e6:<14.3f} {m.speedup_vs_baseline:<10.2f}x")
        print("=" * 70)
        print(lineage_dag.render_ascii_tree())
        print("=" * 70 + "\n")
