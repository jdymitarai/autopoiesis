"""
Living Organism Orchestrator for Antigravity.

Manages the autopoietic lifecycle:
1. Ingests events into Cognitive Metabolism
2. Executes Skill & Rule Autophagy to synthesize staged mutations
3. Applies Cognitive Apoptotic Gate immune verification with zero-tolerance rollback
4. Advances Generational Lineage Tree (Gen 0 -> Gen N) with cryptographic state hashes
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from .apoptotic_gate import ApoptoticVerdict, CognitiveApoptoticGate
    from .autophagy import MutationType, SkillRuleAutophagy, StagedMutation
    from .cortex import NeuralCortex
    from .foraging import CognitiveForagingEngine, ForagingPolicy, Nutrient
    from .metabolism import (
        CognitiveMetabolism,
        EventType,
        ProceduralMutationCandidate,
        SessionEvent,
        TargetType,
    )
except (ImportError, ValueError):
    try:
        from organism.apoptotic_gate import ApoptoticVerdict, CognitiveApoptoticGate
        from organism.autophagy import MutationType, SkillRuleAutophagy, StagedMutation
        from organism.cortex import NeuralCortex
        from organism.foraging import CognitiveForagingEngine, ForagingPolicy, Nutrient
        from organism.metabolism import (
            CognitiveMetabolism,
            EventType,
            ProceduralMutationCandidate,
            SessionEvent,
            TargetType,
        )
    except (ImportError, ValueError):
        from autopoiesis.agent.apoptotic_gate import ApoptoticVerdict, CognitiveApoptoticGate
        from autopoiesis.agent.autophagy import MutationType, SkillRuleAutophagy, StagedMutation
        from autopoiesis.agent.cortex import NeuralCortex
        from autopoiesis.agent.foraging import CognitiveForagingEngine, ForagingPolicy, Nutrient
        from autopoiesis.agent.metabolism import (
            CognitiveMetabolism,
            EventType,
            ProceduralMutationCandidate,
            SessionEvent,
            TargetType,
        )


@dataclass
class GenerationNode:
    """A generational milestone in Antigravity's evolutionary lineage."""
    generation: int
    parent_generation: Optional[int]
    timestamp: float
    phenotype_hash: str
    applied_mutations: List[Dict[str, Any]] = field(default_factory=list)
    rejected_mutations: List[Dict[str, Any]] = field(default_factory=list)
    snapshot_path: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, VIABLE, ROLLED_BACK, APOPTOTIC
    reflex_metadata: Optional[Dict[str, Any]] = None
    cortex_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GenerationNode:
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid_keys})


@dataclass
class OrganismHeartbeatResult:
    """Outcome of an autopoietic metabolic pulse / heartbeat."""
    generation_before: int
    generation_after: int
    events_processed: int
    mutations_applied: int
    mutations_rejected: int
    verdicts: List[ApoptoticVerdict] = field(default_factory=list)
    success: bool = True
    details: str = ""
    foraged_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation_before": self.generation_before,
            "generation_after": self.generation_after,
            "events_processed": self.events_processed,
            "mutations_applied": self.mutations_applied,
            "mutations_rejected": self.mutations_rejected,
            "verdicts": [v.to_dict() for v in self.verdicts],
            "success": self.success,
            "details": self.details,
            "foraged_count": self.foraged_count,
        }


class LineageDAG:
    """Directed Acyclic Graph tracking Antigravity's generational evolution."""

    def __init__(self) -> None:
        self.generations: Dict[int, GenerationNode] = {}
        self.active_generation: int = 0
        self.mutation_history: List[Dict[str, Any]] = []

    def add_node(self, node: GenerationNode, set_active: bool = True) -> None:
        if self.active_generation in self.generations and set_active:
            self.generations[self.active_generation].status = "VIABLE"
        self.generations[node.generation] = node
        if set_active:
            self.active_generation = node.generation

    def get_active(self) -> Optional[GenerationNode]:
        return self.generations.get(self.active_generation)

    def render_ascii_tree(self) -> str:
        lines: List[str] = []
        lines.append("=" * 65)
        lines.append("   ANTIGRAVITY LIVING ORGANISM - GENERATIONAL LINEAGE TREE")
        lines.append("=" * 65)

        for gen_idx in sorted(self.generations.keys()):
            node = self.generations[gen_idx]
            prefix = "  [*] " if gen_idx == 0 else f"  {'  ' * gen_idx}|--> "
            status = " (ACTIVE PHENOTYPE)" if gen_idx == self.active_generation else f" [{node.status}]"
            mut_info = f"applied={len(node.applied_mutations)} rejected={len(node.rejected_mutations)}"
            lines.append(
                f"{prefix}Gen {node.generation} [hash={node.phenotype_hash[:10]}] {mut_info}{status}"
            )
            for m in node.applied_mutations:
                lines.append(
                    f"       + {m.get('mutation_type', 'MUTATION')} on {Path(m.get('target_path', '')).name}: {m.get('title', '')}"
                )
            for r in node.rejected_mutations:
                lines.append(
                    f"       X Apoptotic Prune: {r.get('rejection_reason', 'Rejected')}"
                )

        lines.append("=" * 65)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_generation": self.active_generation,
            "generations": {str(k): v.to_dict() for k, v in self.generations.items()},
            "mutation_history": self.mutation_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageDAG:
        dag = cls()
        dag.active_generation = int(data.get("active_generation", 0))
        gens = data.get("generations", {})
        for k, v in gens.items():
            dag.generations[int(k)] = GenerationNode.from_dict(v)
        dag.mutation_history = data.get("mutation_history", [])
        return dag


class AntigravityOrganism:
    """
    Living organism orchestrator.
    Binds Metabolism, Autophagy, and Apoptotic Gate into a unified evolutionary loop.
    """

    def __init__(
        self,
        agents_dir: Optional[Path] = None,
        organism_dir: Optional[Path] = None,
    ) -> None:
        self.agents_dir = Path(agents_dir).resolve() if agents_dir else Path("c:/ai/.agents").resolve()
        self.organism_dir = Path(organism_dir).resolve() if organism_dir else self.agents_dir / "organism"
        self.snapshots_dir = self.organism_dir / "snapshots"
        self.lineage_file = self.organism_dir / "lineage.json"
        self.reflex_file = self.organism_dir / "reflex_state.json"
        self.cortex_file = self.organism_dir / "cortex_state.json"

        # Initialize Neural Reflex Subsystem
        self.reflex: Optional[Any] = None
        self._load_or_init_reflex()

        # Initialize Cerebral Neural Cortex (SmolLM2-135M)
        self.cortex: Optional[Any] = None
        self._load_or_init_cortex()

        # Initialize subsystems
        self.metabolism = CognitiveMetabolism(
            state_dir=self.organism_dir / "metabolism",
            cortex=self.cortex,
        )
        self.autophagy = SkillRuleAutophagy(agents_dir=self.agents_dir)
        self.apoptotic_gate = CognitiveApoptoticGate()
        self.foraging = CognitiveForagingEngine(
            policy=ForagingPolicy(),
            cache_dir=self.organism_dir / "foraging",
            reflex=self.reflex,
        )
        self.lineage = LineageDAG()
        self.heartbeat_counter: int = 0
        self.forage_interval: int = 5

        # Load or bootstrap
        self._load_or_bootstrap()

    def _load_or_init_cortex(self) -> None:
        try:
            from .cortex import NeuralCortex
        except (ImportError, ValueError):
            try:
                from organism.cortex import NeuralCortex
            except ImportError:
                from autopoiesis.agent.cortex import NeuralCortex

        try:
            self.cortex = NeuralCortex()
            if self.cortex_file.exists():
                try:
                    data = json.loads(self.cortex_file.read_text(encoding="utf-8"))
                    self.cortex.restore_status(data)
                except Exception:
                    pass
            else:
                self._save_cortex_state()
        except Exception:
            self.cortex = None

    def _save_cortex_state(self) -> None:
        if self.cortex is not None:
            self.organism_dir.mkdir(parents=True, exist_ok=True)
            self.cortex_file.write_text(
                json.dumps(self.cortex.get_status(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _load_or_init_reflex(self) -> None:
        try:
            from .reflex import TernaryReflexClassifier
        except (ImportError, ValueError):
            try:
                from organism.reflex import TernaryReflexClassifier
            except ImportError:
                from autopoiesis.agent.reflex import TernaryReflexClassifier

        if self.reflex_file.exists():
            try:
                self.reflex = TernaryReflexClassifier.load_json(self.reflex_file)
                return
            except Exception:
                pass
        self.reflex = TernaryReflexClassifier.create_calibrated()
        self._save_reflex_state()

    def _save_reflex_state(self) -> None:
        if self.reflex is not None:
            self.organism_dir.mkdir(parents=True, exist_ok=True)
            self.reflex.save_json(self.reflex_file)

    def _load_or_bootstrap(self) -> None:
        self.organism_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        if self.lineage_file.exists():
            try:
                data = json.loads(self.lineage_file.read_text(encoding="utf-8"))
                self.lineage = LineageDAG.from_dict(data)
                return
            except Exception:
                pass  # Fall back to bootstrap if corrupted

        # Bootstrap Gen 0 baseline
        self.bootstrap()

    def bootstrap(self) -> GenerationNode:
        """Create baseline Gen 0 node and snapshot current phenotype."""
        baseline_hash = self.compute_phenotype_hash()
        snapshot_dir = self.snapshots_dir / "gen_0"
        self._create_snapshot(snapshot_dir)

        reflex_meta = {
            "state_hash": self.reflex.compute_state_hash()[:16] if self.reflex else "",
            "weights_count": self.reflex.total_weights if self.reflex else 0,
            "memory_footprint_bytes": self.reflex.get_memory_footprint() if self.reflex else 0,
        }
        cortex_meta = self.cortex.get_status() if self.cortex else None

        gen_0 = GenerationNode(
            generation=0,
            parent_generation=None,
            timestamp=time.time(),
            phenotype_hash=baseline_hash,
            applied_mutations=[],
            rejected_mutations=[],
            snapshot_path=str(snapshot_dir),
            status="ACTIVE",
            reflex_metadata=reflex_meta,
            cortex_metadata=cortex_meta,
        )
        self.lineage.add_node(gen_0, set_active=True)
        self._persist_lineage()
        return gen_0

    def compute_phenotype_hash(self) -> str:
        """Compute deterministic SHA256 of all agent rules, skills, and neural reflex state."""
        hasher = hashlib.sha256()

        # 1. Rules file
        rules_file = self.agents_dir / "AGENTS.md"
        if rules_file.exists():
            hasher.update(rules_file.read_bytes())

        # 2. MCP config file
        mcp_file = self.agents_dir / "mcp_config.json"
        if mcp_file.exists():
            hasher.update(mcp_file.read_bytes())

        # 3. Skills (hash all tracked files recursively)
        skills_dir = self.agents_dir / "skills"
        if skills_dir.exists():
            for file_path in sorted(skills_dir.rglob("*")):
                if file_path.is_file() and "__pycache__" not in file_path.parts and not file_path.name.startswith("."):
                    rel_path = file_path.relative_to(skills_dir).as_posix()
                    hasher.update(rel_path.encode("utf-8"))
                    hasher.update(file_path.read_bytes())

        # 4. Neural Reflex Kernel State
        if hasattr(self, "reflex") and self.reflex is not None:
            hasher.update(self.reflex.compute_state_hash().encode("utf-8"))

        return hasher.hexdigest()

    def pulse(
        self,
        events: Optional[List[SessionEvent]] = None,
        force_forage: bool = False,
    ) -> OrganismHeartbeatResult:
        """
        Execute one metabolic pulse / heartbeat cycle:
        1. Ingest session events into Cognitive Metabolism
        2. Autonomous Exotrophic Foraging (scouts external web if enabled)
        3. Digest events into procedural mutation candidates
        4. Autophagy stages candidates against working buffer
        5. Apoptotic Gate validates staged mutations with zero-tolerance immunity
        6. Atomically apply approved mutations, advance generation, or trigger rollback
        """
        gen_before = self.lineage.active_generation

        # 1. Ingest explicit session events
        if events:
            self.metabolism.ingest_batch(events)

        # 2. Autonomous Exotrophic Foraging
        self.heartbeat_counter += 1
        foraged_count = 0
        if force_forage or (self.forage_interval > 0 and self.heartbeat_counter % self.forage_interval == 0):
            try:
                nutrients = self.foraging.forage_active_sources()
                for nut in nutrients:
                    self.metabolism.ingest_event(
                        SessionEvent.create(
                            event_type=EventType.FORAGED_NUTRIENT,
                            payload=nut.to_dict(),
                            source="exotrophic_forager",
                        )
                    )
                foraged_count = len(nutrients)
            except Exception:
                foraged_count = 0

        pending_events = self.metabolism.get_pending_events()
        events_count = len(pending_events)

        # 3. Digest events
        candidates = self.metabolism.digest()

        # Working buffer tracks accumulated file content during this pulse cycle
        working_buffer: Dict[str, str] = {}
        original_baselines: Dict[str, str] = {}

        def get_current(path: Path) -> str:
            sp = str(path.resolve())
            if sp in working_buffer:
                return working_buffer[sp]
            orig = path.read_text(encoding="utf-8") if path.exists() else ""
            original_baselines[sp] = orig
            working_buffer[sp] = orig
            return orig

        approved_mutations: List[StagedMutation] = []
        verdicts: List[ApoptoticVerdict] = []
        rejected_records: List[Dict[str, Any]] = []

        # 3. Stage and verify candidate mutations sequentially against working buffer
        for cand in candidates:
            if getattr(cand, "target_type", "") == TargetType.REFLEX:
                verdict = self.apoptotic_gate.validate_reflex_mutation(cand)
                verdicts.append(verdict)
                if verdict.approved:
                    try:
                        curr_content = get_current(self.reflex_file)
                        staged = StagedMutation.create(
                            target_path=str(self.reflex_file),
                            target_type=TargetType.REFLEX.value,
                            original_content=curr_content,
                            mutated_content=cand.content,
                            mutation_type=MutationType.UPDATE_RULE,
                            metadata={"title": cand.title, "reflex_state": cand.content},
                        )
                        approved_mutations.append(staged)
                        working_buffer[str(self.reflex_file.resolve())] = cand.content
                    except Exception:
                        pass
                else:
                    rejected_records.append({
                        "mutation_id": verdict.mutation_id,
                        "target_path": "reflex_kernel",
                        "rejection_reason": verdict.rejection_reason,
                        "checks_failed": verdict.checks_failed,
                    })
                continue

            if cand.target_type == TargetType.RULE:
                target_path = self.autophagy.rules_file
            elif cand.target_type == TargetType.SKILL:
                sname = cand.target_name.strip().lower().replace(" ", "-")
                target_path = self.autophagy.skills_dir / sname / "SKILL.md"
            else:
                target_path = self.autophagy.rules_file

            curr = get_current(target_path)
            staged = self.autophagy.stage_candidate(cand, base_content=curr)

            # Check if this mutation is a no-op (already incorporated)
            if staged.metadata.get("no_op") or staged.mutated_content == staged.original_content:
                continue

            verdict = self.apoptotic_gate.verify(staged)
            verdicts.append(verdict)

            if verdict.approved:
                approved_mutations.append(staged)
                working_buffer[str(target_path.resolve())] = staged.mutated_content
            else:
                rejected_records.append({
                    "mutation_id": verdict.mutation_id,
                    "target_path": verdict.target_path,
                    "rejection_reason": verdict.rejection_reason,
                    "checks_failed": verdict.checks_failed,
                })

        # 4. Stage and verify autophagy audits
        curr_rules = get_current(self.autophagy.rules_file)
        rule_audits = self.autophagy.audit_rules(base_content=curr_rules)
        for audit in rule_audits:
            verdict = self.apoptotic_gate.verify(audit)
            verdicts.append(verdict)
            if verdict.approved:
                approved_mutations.append(audit)
                working_buffer[str(Path(audit.target_path).resolve())] = audit.mutated_content
            else:
                rejected_records.append({
                    "mutation_id": verdict.mutation_id,
                    "target_path": verdict.target_path,
                    "rejection_reason": verdict.rejection_reason,
                    "checks_failed": verdict.checks_failed,
                })

        skill_audits = self.autophagy.audit_skills()
        for audit in skill_audits:
            sp = str(Path(audit.target_path).resolve())
            if sp in working_buffer:
                audit = StagedMutation.create(
                    target_path=audit.target_path,
                    target_type="SKILL",
                    original_content=working_buffer[sp],
                    mutated_content=self.autophagy.clean_text(working_buffer[sp]),
                    mutation_type=MutationType.PRUNE_BLOAT,
                    metadata=audit.metadata,
                )
            if audit.mutated_content == audit.original_content:
                continue
            verdict = self.apoptotic_gate.verify(audit)
            verdicts.append(verdict)
            if verdict.approved:
                approved_mutations.append(audit)
                working_buffer[sp] = audit.mutated_content
            else:
                rejected_records.append({
                    "mutation_id": verdict.mutation_id,
                    "target_path": verdict.target_path,
                    "rejection_reason": verdict.rejection_reason,
                    "checks_failed": verdict.checks_failed,
                })

        # Determine which files actually changed
        files_to_write = {
            p: content
            for p, content in working_buffer.items()
            if content != original_baselines.get(p, "")
        }

        if not files_to_write:
            if rejected_records:
                active_node = self.lineage.get_active()
                if active_node:
                    active_node.rejected_mutations.extend(rejected_records)
                    self._persist_lineage()
                return OrganismHeartbeatResult(
                    generation_before=gen_before,
                    generation_after=gen_before,
                    events_processed=events_count,
                    mutations_applied=0,
                    mutations_rejected=len(rejected_records),
                    verdicts=verdicts,
                    success=True,
                    details=f"Apoptotic Gate pruned all {len(rejected_records)} proposed mutations. Organism protected.",
                    foraged_count=foraged_count,
                )
            else:
                return OrganismHeartbeatResult(
                    generation_before=gen_before,
                    generation_after=gen_before,
                    events_processed=events_count,
                    mutations_applied=0,
                    mutations_rejected=0,
                    verdicts=verdicts,
                    success=True,
                    details="Quiescent state: no mutations required.",
                    foraged_count=foraged_count,
                )

        # 5. Apply approved mutations atomically with backup
        backup_snapshot: Dict[str, str] = {
            p: original_baselines.get(p, "") for p in files_to_write
        }
        applied_records: List[Dict[str, Any]] = [
            {
                "mutation_id": staged.mutation_id,
                "target_path": staged.target_path,
                "target_type": staged.target_type,
                "mutation_type": staged.mutation_type.value,
                "title": staged.metadata.get("title", ""),
            }
            for staged in approved_mutations
        ]

        try:
            for p_str, content in files_to_write.items():
                tpath = Path(p_str)
                tpath.parent.mkdir(parents=True, exist_ok=True)
                tpath.write_text(content, encoding="utf-8")

            # Update in-memory reflex instance if reflex_file was committed
            reflex_str = str(self.reflex_file.resolve())
            if reflex_str in files_to_write:
                try:
                    from .reflex import TernaryReflexClassifier
                except (ImportError, ValueError):
                    from autopoiesis.agent.reflex import TernaryReflexClassifier
                try:
                    self.reflex = TernaryReflexClassifier.load_json(self.reflex_file)
                    self.foraging.reflex = self.reflex
                except Exception:
                    pass

            # Advance generation
            next_gen = gen_before + 1
            new_hash = self.compute_phenotype_hash()
            snapshot_dir = self.snapshots_dir / f"gen_{next_gen}"
            self._create_snapshot(snapshot_dir)

            reflex_meta = {
                "state_hash": self.reflex.compute_state_hash()[:16] if self.reflex else "",
                "weights_count": self.reflex.total_weights if self.reflex else 0,
                "memory_footprint_bytes": self.reflex.get_memory_footprint() if self.reflex else 0,
            }
            cortex_meta = self.cortex.get_status() if self.cortex else None

            new_node = GenerationNode(
                generation=next_gen,
                parent_generation=gen_before,
                timestamp=time.time(),
                phenotype_hash=new_hash,
                applied_mutations=applied_records,
                rejected_mutations=rejected_records,
                snapshot_path=str(snapshot_dir),
                status="ACTIVE",
                reflex_metadata=reflex_meta,
                cortex_metadata=cortex_meta,
            )
            self.lineage.add_node(new_node, set_active=True)
            self._persist_lineage()

            return OrganismHeartbeatResult(
                generation_before=gen_before,
                generation_after=next_gen,
                events_processed=events_count,
                mutations_applied=len(approved_mutations),
                mutations_rejected=len(rejected_records),
                verdicts=verdicts,
                success=True,
                details=f"Evolved to Gen {next_gen}. Applied {len(approved_mutations)} mutations.",
                foraged_count=foraged_count,
            )

        except Exception as ex:
            self.apoptotic_gate.rollback(backup_snapshot)
            if self.reflex_file.exists():
                try:
                    from .reflex import TernaryReflexClassifier
                except (ImportError, ValueError):
                    from autopoiesis.agent.reflex import TernaryReflexClassifier
                try:
                    self.reflex = TernaryReflexClassifier.load_json(self.reflex_file)
                    self.foraging.reflex = self.reflex
                except Exception:
                    pass
            return OrganismHeartbeatResult(
                generation_before=gen_before,
                generation_after=gen_before,
                events_processed=events_count,
                mutations_applied=0,
                mutations_rejected=len(approved_mutations),
                verdicts=verdicts,
                success=False,
                details=f"Rollback triggered due to application error: {ex}",
                foraged_count=foraged_count,
            )

    # Alias heartbeat to pulse
    heartbeat = pulse

    def evolve(
        self,
        cycles: int = 1,
        event_batches: Optional[List[List[SessionEvent]]] = None,
    ) -> List[OrganismHeartbeatResult]:
        """Run multiple heartbeat cycles sequentially."""
        results: List[OrganismHeartbeatResult] = []
        for i in range(cycles):
            events = event_batches[i] if event_batches and i < len(event_batches) else None
            res = self.pulse(events)
            results.append(res)
        return results

    def rollback(self, target_generation: Optional[int] = None) -> bool:
        """Roll back organism to the phenotype snapshot of target_generation."""
        if target_generation is None:
            target_generation = max(0, self.lineage.active_generation - 1)

        target_node = self.lineage.generations.get(target_generation)
        if not target_node or not target_node.snapshot_path:
            return False

        snapshot_dir = Path(target_node.snapshot_path)
        if not snapshot_dir.exists():
            return False

        try:
            # Mark current generation as rolled back
            curr_node = self.lineage.get_active()
            if curr_node and curr_node.generation != target_generation:
                curr_node.status = "ROLLED_BACK"

            # Restore AGENTS.md
            snap_rules = snapshot_dir / "AGENTS.md"
            target_rules = self.agents_dir / "AGENTS.md"
            if snap_rules.exists():
                target_rules.write_text(snap_rules.read_text(encoding="utf-8"), encoding="utf-8")
            elif target_rules.exists():
                target_rules.unlink()

            # Restore mcp_config.json
            snap_mcp = snapshot_dir / "mcp_config.json"
            target_mcp = self.agents_dir / "mcp_config.json"
            if snap_mcp.exists():
                target_mcp.write_text(snap_mcp.read_text(encoding="utf-8"), encoding="utf-8")
            elif target_mcp.exists():
                target_mcp.unlink()

            # Restore skills recursively
            snap_skills = snapshot_dir / "skills"
            target_skills = self.agents_dir / "skills"
            if snap_skills.exists():
                # Remove skills that were added after target generation
                for s_dir in target_skills.iterdir():
                    if s_dir.is_dir() and not (snap_skills / s_dir.name).exists():
                        shutil.rmtree(s_dir, ignore_errors=True)
                # Copy snapshot skills over recursively
                for snap_s_dir in snap_skills.iterdir():
                    if snap_s_dir.is_dir():
                        dest = target_skills / snap_s_dir.name
                        if dest.exists():
                            shutil.rmtree(dest, ignore_errors=True)
                        shutil.copytree(snap_s_dir, dest)

            # Restore reflex state if present in snapshot
            snap_reflex = snapshot_dir / "reflex_state.json"
            if snap_reflex.exists():
                try:
                    from .reflex import TernaryReflexClassifier
                except (ImportError, ValueError):
                    from autopoiesis.agent.reflex import TernaryReflexClassifier
                try:
                    self.reflex = TernaryReflexClassifier.load_json(snap_reflex)
                    self._save_reflex_state()
                    self.foraging.reflex = self.reflex
                except Exception:
                    pass
            elif self.reflex_file.exists():
                try:
                    from .reflex import TernaryReflexClassifier
                except (ImportError, ValueError):
                    from autopoiesis.agent.reflex import TernaryReflexClassifier
                try:
                    self.reflex = TernaryReflexClassifier.create_calibrated()
                    self._save_reflex_state()
                    self.foraging.reflex = self.reflex
                except Exception:
                    pass

            # Restore cortex state if present in snapshot
            snap_cortex = snapshot_dir / "cortex_state.json"
            if snap_cortex.exists() and self.cortex is not None:
                try:
                    cortex_data = json.loads(snap_cortex.read_text(encoding="utf-8"))
                    self.cortex.restore_status(cortex_data)
                    self._save_cortex_state()
                except Exception:
                    pass
            elif self.cortex is not None:
                try:
                    if target_node and target_node.cortex_metadata:
                        self.cortex.restore_status(target_node.cortex_metadata)
                    else:
                        self.cortex.reset_metrics()
                    self._save_cortex_state()
                except Exception:
                    pass

            target_node.status = "ACTIVE"
            self.lineage.active_generation = target_generation
            self._persist_lineage()
            return True
        except Exception:
            return False

    def get_telemetry(self) -> Dict[str, Any]:
        """Return real-time organism telemetry."""
        total_mutations_applied = sum(
            len(g.applied_mutations) for g in self.lineage.generations.values()
        )
        total_mutations_rejected = sum(
            len(g.rejected_mutations) for g in self.lineage.generations.values()
        )
        total_attempted = total_mutations_applied + total_mutations_rejected
        acceptance_rate = (
            (total_mutations_applied / total_attempted * 100.0)
            if total_attempted > 0
            else 100.0
        )

        skills_dir = self.agents_dir / "skills"
        skill_count = len(list(skills_dir.iterdir())) if skills_dir.exists() else 0

        rules_file = self.agents_dir / "AGENTS.md"
        rules_size = rules_file.stat().st_size if rules_file.exists() else 0

        # Count active MCP servers (workspace or global)
        mcp_file = self.agents_dir / "mcp_config.json"
        global_mcp_file = Path.home() / ".gemini" / "config" / "mcp_config.json"
        mcp_count = 0
        target_mcp = mcp_file if mcp_file.exists() else global_mcp_file
        if target_mcp.exists():
            try:
                mcp_data = json.loads(target_mcp.read_text(encoding="utf-8"))
                mcp_count = len(mcp_data.get("mcpServers", {}))
            except Exception:
                pass

        return {
            "active_generation": self.lineage.active_generation,
            "phenotype_hash": self.compute_phenotype_hash()[:16],
            "total_generations": len(self.lineage.generations),
            "total_events_digested": len(self.metabolism.digested_event_ids),
            "pending_events": len(self.metabolism.get_pending_events()),
            "total_mutations_applied": total_mutations_applied,
            "total_mutations_rejected": total_mutations_rejected,
            "acceptance_rate_percent": round(acceptance_rate, 2),
            "active_skills_count": skill_count,
            "active_mcp_servers_count": mcp_count,
            "agents_rules_bytes": rules_size,
            "reflex_active": bool(self.reflex),
            "reflex_weights_count": self.reflex.total_weights if self.reflex else 0,
            "reflex_memory_bytes": self.reflex.get_memory_footprint() if self.reflex else 0,
            "cortex_active": bool(self.cortex and self.cortex.is_loaded),
            "cortex_model": self.cortex.model_id if self.cortex else "",
            "cortex_backend": self.cortex.active_backend if self.cortex else "",
            "cortex_parameters": self.cortex.parameter_count if self.cortex else 0,
            "cortex_inferences": self.cortex.total_inferences if self.cortex else 0,
            "cortex_avg_latency_ms": self.cortex.average_latency_ms if self.cortex else 0.0,
        }

    def render_lineage_ascii(self) -> str:
        """Render the complete genealogical tree."""
        return self.lineage.render_ascii_tree()

    def _create_snapshot(self, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot AGENTS.md
        rules_file = self.agents_dir / "AGENTS.md"
        if rules_file.exists():
            shutil.copy2(rules_file, target_dir / "AGENTS.md")

        # Snapshot mcp_config.json
        mcp_file = self.agents_dir / "mcp_config.json"
        if mcp_file.exists():
            shutil.copy2(mcp_file, target_dir / "mcp_config.json")

        # Snapshot skills recursively
        skills_dir = self.agents_dir / "skills"
        if skills_dir.exists():
            snap_skills = target_dir / "skills"
            snap_skills.mkdir(parents=True, exist_ok=True)
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    dest = snap_skills / skill_dir.name
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(
                        skill_dir,
                        dest,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    )

        # Snapshot reflex state
        if self.reflex is not None:
            try:
                self.reflex.save_json(target_dir / "reflex_state.json")
            except Exception:
                pass

        # Snapshot cortex state
        if self.cortex is not None:
            try:
                (target_dir / "cortex_state.json").write_text(
                    json.dumps(self.cortex.get_status(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def _persist_lineage(self) -> None:
        self.organism_dir.mkdir(parents=True, exist_ok=True)
        data = self.lineage.to_dict()
        tmp_file = self.lineage_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_file.replace(self.lineage_file)
