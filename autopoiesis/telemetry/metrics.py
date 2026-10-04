"""
Evolutionary Telemetry and Performance Metrics Tracker.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import psutil


@dataclass
class GenerationMetric:
    generation: int
    chromosome_id: str
    source_type: str
    mutator_name: str
    latency_ns: float
    speedup_vs_baseline: float
    cpu_percent: float
    memory_rss_mb: float
    timestamp: float = field(default_factory=time.time)


class TelemetryTracker:
    """Collects and stores generational metrics during evolutionary runs."""

    def __init__(self) -> None:
        self.metrics: List[GenerationMetric] = []
        self._process = psutil.Process(os.getpid())

    def record_generation(
        self,
        generation: int,
        chromosome_id: str,
        source_type: str,
        mutator_name: str,
        latency_ns: float,
        speedup: float,
    ) -> GenerationMetric:
        mem_info = self._process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        cpu_pct = self._process.cpu_percent()

        metric = GenerationMetric(
            generation=generation,
            chromosome_id=chromosome_id,
            source_type=source_type,
            mutator_name=mutator_name,
            latency_ns=latency_ns,
            speedup_vs_baseline=speedup,
            cpu_percent=cpu_pct,
            memory_rss_mb=mem_mb,
            timestamp=time.time(),
        )
        self.metrics.append(metric)
        return metric

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [asdict(m) for m in self.metrics]
