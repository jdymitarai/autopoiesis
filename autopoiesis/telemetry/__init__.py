"""
Telemetry and real-time dashboard module.
"""

from autopoiesis.telemetry.metrics import GenerationMetric, TelemetryTracker
from autopoiesis.telemetry.dashboard import TerminalDashboard

__all__ = [
    "GenerationMetric",
    "TelemetryTracker",
    "TerminalDashboard",
]
