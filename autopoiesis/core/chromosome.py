"""
Chromosomal representation and Genetic Lineage DAG for Autopoiesis.

Each code unit or function candidate is encapsulated as a Chromosome with
cryptographic lineage tracking, immutability guarantees, and generational fitness metrics.
"""

from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class SourceType(str, enum.Enum):
    PYTHON_AST = "PYTHON_AST"
    C_EXTENSION = "C_EXTENSION"
    RUST_CDYLIB = "RUST_CDYLIB"


@dataclass
class Chromosome:
    """Represents a genetic code unit within the living organism."""
    id: str
    generation: int
    parent_id: Optional[str]
    source_type: SourceType
    entry_symbol: str
    code: str
    compiled_artifact_path: Optional[str] = None
    compiler_flags: List[str] = field(default_factory=list)
    fitness: float = 1.0  # Speedup multiplier relative to baseline Gen 0
    mean_latency_ns: float = 0.0
    mutation_meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    is_viable: bool = True

    @classmethod
    def create(
        cls,
        generation: int,
        source_type: SourceType,
        entry_symbol: str,
        code: str,
        parent_id: Optional[str] = None,
        compiled_artifact_path: Optional[str] = None,
        compiler_flags: Optional[List[str]] = None,
        fitness: float = 1.0,
        mean_latency_ns: float = 0.0,
        mutation_meta: Optional[Dict[str, Any]] = None,
    ) -> Chromosome:
        flags = compiler_flags or []
        meta = mutation_meta or {}

        # Cryptographically unique deterministic ID
        hasher = hashlib.sha256()
        hasher.update(str(generation).encode("utf-8"))
        hasher.update(source_type.value.encode("utf-8"))
        hasher.update(entry_symbol.encode("utf-8"))
        hasher.update(code.encode("utf-8"))
        hasher.update(" ".join(flags).encode("utf-8"))
        if parent_id:
            hasher.update(parent_id.encode("utf-8"))
        chrom_id = hasher.hexdigest()[:16]

        return cls(
            id=chrom_id,
            generation=generation,
            parent_id=parent_id,
            source_type=source_type,
            entry_symbol=entry_symbol,
            code=code,
            compiled_artifact_path=compiled_artifact_path,
            compiler_flags=flags,
            fitness=fitness,
            mean_latency_ns=mean_latency_ns,
            mutation_meta=meta,
            timestamp=time.time(),
            is_viable=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Chromosome:
        data_copy = dict(data)
        data_copy["source_type"] = SourceType(data_copy["source_type"])
        return cls(**data_copy)


@dataclass
class MutationRecord:
    """Record of an attempted or succeeded mutation."""
    parent_id: Optional[str]
    candidate_id: str
    generation: int
    mutator_name: str
    target_symbol: str
    accepted: bool
    speedup: float
    rejection_reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class LineageDAG:
    """
    Genealogical Directed Acyclic Graph tracking evolutionary lineages,
    apoptotic death events, and phenotype survivals.
    """

    def __init__(self) -> None:
        self.chromosomes: Dict[str, Chromosome] = {}
        self.mutation_history: List[MutationRecord] = []
        self.active_chromosome_id: Optional[str] = None

    def add_chromosome(self, chromosome: Chromosome, set_active: bool = False) -> None:
        self.chromosomes[chromosome.id] = chromosome
        if set_active or self.active_chromosome_id is None:
            self.active_chromosome_id = chromosome.id

    def record_mutation(self, record: MutationRecord) -> None:
        self.mutation_history.append(record)

    def get_chromosome(self, chrom_id: str) -> Optional[Chromosome]:
        return self.chromosomes.get(chrom_id)

    def get_active(self) -> Optional[Chromosome]:
        if self.active_chromosome_id:
            return self.chromosomes.get(self.active_chromosome_id)
        return None

    def get_ancestors(self, chrom_id: str) -> List[Chromosome]:
        ancestors: List[Chromosome] = []
        curr_id: Optional[str] = chrom_id
        while curr_id:
            chrom = self.chromosomes.get(curr_id)
            if not chrom:
                break
            ancestors.append(chrom)
            curr_id = chrom.parent_id
        ancestors.reverse()
        return ancestors

    def render_ascii_tree(self) -> str:
        """Render a clean ASCII lineage graph of evolutionary history."""
        lines: List[str] = []
        lines.append("Genetic Lineage Tree (Autopoietic DAG):")
        lines.append("=" * 60)

        # Trace active lineage
        if self.active_chromosome_id:
            active_ancestors = self.get_ancestors(self.active_chromosome_id)
            for i, chrom in enumerate(active_ancestors):
                prefix = "  |--> " if i > 0 else "  [*] "
                status = " (ACTIVE PHENOTYPE)" if chrom.id == self.active_chromosome_id else ""
                lines.append(
                    f"{prefix}Gen {chrom.generation} [{chrom.id}] "
                    f"type={chrom.source_type.value} fitness={chrom.fitness:.2f}x{status}"
                )

        # List apoptotic failures
        failures = [m for m in self.mutation_history if not m.accepted]
        if failures:
            lines.append("\nApoptotic Pruned Mutations (Defensive Immune Rejections):")
            for m in failures[-5:]:  # show last 5
                lines.append(
                    f"  [X] Gen {m.generation} candidate={m.candidate_id} "
                    f"mutator={m.mutator_name} rejected: {m.rejection_reason}"
                )

        return "\n".join(lines)

    def to_json(self) -> str:
        data = {
            "chromosomes": {cid: c.to_dict() for cid, c in self.chromosomes.items()},
            "active_id": self.active_chromosome_id,
            "mutation_history": [asdict(m) for m in self.mutation_history],
        }
        return json.dumps(data, indent=2)
