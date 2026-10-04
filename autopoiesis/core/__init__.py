"""
Core components of the Autopoiesis Engine.
"""

from autopoiesis.core.chromosome import Chromosome, SourceType, LineageDAG, MutationRecord
from autopoiesis.core.hotspot import HotspotDetector, BottleneckProfile
from autopoiesis.core.sandbox import IsolatedProcessSandbox, SandboxExecutionResult
from autopoiesis.core.apoptosis import ApoptoticGate, ApoptosisVerdict
from autopoiesis.core.hotswap import AtomicHotSwapper
from autopoiesis.core.organism import LivingOrganism

__all__ = [
    "Chromosome",
    "SourceType",
    "LineageDAG",
    "MutationRecord",
    "HotspotDetector",
    "BottleneckProfile",
    "IsolatedProcessSandbox",
    "SandboxExecutionResult",
    "ApoptoticGate",
    "ApoptosisVerdict",
    "AtomicHotSwapper",
    "LivingOrganism",
]
