"""
Autopoiesis: Digital Autopoiesis & Recursive Self-Improvement Engine.

Implements autonomous code autophagy, dual-buffer chromosomal sandboxing,
deterministic apoptotic immune verification, and zero-downtime atomic hot-swapping.
"""

__version__ = "0.1.2"
__author__ = "Autopoiesis Research Team"

from autopoiesis.core.organism import LivingOrganism
from autopoiesis.core.chromosome import Chromosome, SourceType
from autopoiesis.core.apoptosis import ApoptoticGate, ApoptosisVerdict
from autopoiesis.core.hotswap import AtomicHotSwapper
from autopoiesis.core.breeding import export_genome_package, import_and_verify_genome_package

__all__ = [
    "LivingOrganism",
    "Chromosome",
    "SourceType",
    "ApoptoticGate",
    "ApoptosisVerdict",
    "AtomicHotSwapper",
    "export_genome_package",
    "import_and_verify_genome_package",
]

