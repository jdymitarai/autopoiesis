"""
Living Organism Orchestrator for Autopoiesis.

Encapsulates the living codebase organism, driving the recursive self-improvement
lifecycle: profiling, candidate mutation generation, apoptotic immune gating,
atomic hot-swapping, and generational telemetry.
"""

from __future__ import annotations

import inspect
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from autopoiesis.core.apoptosis import ApoptoticGate, ApoptosisVerdict
from autopoiesis.core.chromosome import Chromosome, LineageDAG, MutationRecord, SourceType
from autopoiesis.core.hotspot import BottleneckProfile, HotspotDetector
from autopoiesis.core.hotswap import AtomicHotSwapper
from autopoiesis.mutators.ast_optimizer import ASTOptimizerMutator
from autopoiesis.mutators.base import BaseMutator
from autopoiesis.mutators.c_synthesizer import CSynthesizerMutator
from autopoiesis.mutators.rust_synthesizer import RustSynthesizerMutator
from autopoiesis.telemetry.dashboard import TerminalDashboard
from autopoiesis.telemetry.metrics import TelemetryTracker


class LivingOrganism:
    """The living self-evolving organism."""

    def __init__(
        self,
        name: str,
        target_module: Any,
        target_symbol: str,
        test_vectors: List[Tuple[tuple, dict]],
        mutators: Optional[List[BaseMutator]] = None,
        min_speedup_per_step: float = 1.02,
        render_dashboard: bool = True,
        artifacts_dir: Optional[str] = None,
    ) -> None:
        self.name = name
        self.target_module = target_module
        self.target_symbol = target_symbol
        self.test_vectors = test_vectors
        self.render_dashboard = render_dashboard
        self.artifacts_dir = artifacts_dir

        self.lineage_dag = LineageDAG()
        self.telemetry = TelemetryTracker()
        self.hot_swapper = AtomicHotSwapper()
        self.dashboard = TerminalDashboard()
        self.apoptotic_gate = ApoptoticGate(min_speedup_threshold=min_speedup_per_step)

        # Mutator pipeline ordered from algorithmic to compiled native
        self.mutators: List[BaseMutator] = mutators or [
            ASTOptimizerMutator(),
            CSynthesizerMutator(),
            RustSynthesizerMutator(),
        ]

        # Initialize Generation 0 Baseline Chromosome
        self.current_generation = 0
        self._initialize_gen0()

    def _initialize_gen0(self) -> None:
        import ast
        import textwrap
        orig_fn = getattr(self.target_module, self.target_symbol)
        raw_source = getattr(orig_fn, "__autopoiesis_source__", None)
        if not raw_source:
            try:
                raw_source = inspect.getsource(orig_fn)
            except Exception:
                raw_source = ""

        # Fallback: if inspect failed (e.g. wrapper or dynamic function), parse target_module file
        if not raw_source:
            try:
                mod_file = inspect.getsourcefile(self.target_module) or inspect.getfile(self.target_module)
                if mod_file and os.path.exists(mod_file):
                    with open(mod_file, "r", encoding="utf-8") as f:
                        mod_code = f.read()
                    mod_ast = ast.parse(mod_code)
                    for node in mod_ast.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == self.target_symbol:
                            raw_source = ast.unparse(node)
                            break
            except Exception:
                pass

        fn_source = textwrap.dedent(raw_source) if raw_source else ""

        # Extract module-level imports so the chromosome code is self-contained
        import_header = ""
        try:
            mod_source = None
            try:
                mod_source = inspect.getsource(self.target_module)
            except Exception:
                mod_file = inspect.getsourcefile(self.target_module) or inspect.getfile(self.target_module)
                if mod_file and os.path.exists(mod_file):
                    with open(mod_file, "r", encoding="utf-8") as f:
                        mod_source = f.read()

            if mod_source:
                mod_tree = ast.parse(mod_source)
                import_nodes = [
                    n for n in mod_tree.body
                    if isinstance(n, (ast.Import, ast.ImportFrom)) and not (isinstance(n, ast.ImportFrom) and n.module == "__future__")
                ]
                if import_nodes:
                    import_header = ast.unparse(ast.Module(body=import_nodes, type_ignores=[])) + "\n\n"
        except Exception:
            pass

        source = (import_header + fn_source).strip() + "\n"

        # Measure baseline latency
        first_args, first_kwargs = self.test_vectors[0]
        # Warmup
        for _ in range(5):
            orig_fn(*first_args, **first_kwargs)

        t0 = time.perf_counter_ns()
        for _ in range(20):
            orig_fn(*first_args, **first_kwargs)
        t1 = time.perf_counter_ns()
        mean_lat = (t1 - t0) / 20.0

        gen0_chrom = Chromosome.create(
            generation=0,
            source_type=SourceType.PYTHON_AST,
            entry_symbol=self.target_symbol,
            code=source,
            fitness=1.0,
            mean_latency_ns=mean_lat,
            mutation_meta={"mutator": "ORIGINAL_PHENOTYPE"},
        )
        self.lineage_dag.add_chromosome(gen0_chrom, set_active=True)
        self.telemetry.record_generation(
            generation=0,
            chromosome_id=gen0_chrom.id,
            source_type=gen0_chrom.source_type.value,
            mutator_name="BASELINE",
            latency_ns=mean_lat,
            speedup=1.0,
        )

        if self.render_dashboard:
            self.dashboard.render_evolution_frame(
                organism_name=self.name,
                current_generation=0,
                status="ORGANISM HEALTHY (GEN 0 BASELINE)",
                active_chromosome=gen0_chrom,
                lineage_dag=self.lineage_dag,
                tracker=self.telemetry,
            )

    @property
    def active_chromosome(self) -> Chromosome:
        active = self.lineage_dag.get_active()
        if not active:
            raise RuntimeError("No active chromosome found in organism lineage.")
        return active

    @property
    def active_function(self) -> Callable[..., Any]:
        return getattr(self.target_module, self.target_symbol)

    def evolve_generation(self) -> Optional[Chromosome]:
        """
        Attempts a single evolutionary step.
        Evaluates mutators against the apoptotic gate until a viable mutation is found.
        """
        parent = self.active_chromosome
        current_fn = getattr(self.target_module, self.target_symbol)

        # Retrieve root ancestor (original Python phenotype) for semantic AST blueprint
        ancestors = self.lineage_dag.get_ancestors(parent.id)
        root_chromosome = ancestors[0] if ancestors else parent
        mod_name = self.target_module.__name__ if hasattr(self.target_module, "__name__") else "__main__"
        bottleneck = HotspotDetector.analyze_source_ast(
            source_code=root_chromosome.code,
            function_name=self.target_symbol,
            module_name=mod_name,
        )

        self.current_generation += 1
        gen = self.current_generation

        # Try mutators sequentially
        for mutator in self.mutators:
            if not mutator.can_mutate(bottleneck):
                continue

            # Mutator may not degrade if parent already evolved to native
            if parent.source_type in (SourceType.C_EXTENSION, SourceType.RUST_CDYLIB) and mutator.target_source_type == SourceType.PYTHON_AST:
                continue

            # Do not re-run the exact mutator that produced the active parent
            if parent.mutation_meta.get("mutator") == mutator.name:
                continue

            # Use root Python chromosome for native transpilers since AST optimizer injects Python-only builtins
            blueprint_parent = (
                root_chromosome
                if mutator.target_source_type in (SourceType.C_EXTENSION, SourceType.RUST_CDYLIB)
                else parent
            )

            # Generate candidate
            candidate = mutator.mutate(
                blueprint_parent,
                bottleneck,
                target_dir=self.artifacts_dir,
                generation=gen,
                parent_id=parent.id,
            )
            if not candidate:
                continue

            # Apoptotic Gate Verification
            verdict: ApoptosisVerdict = self.apoptotic_gate.verify_candidate(
                baseline_fn=current_fn,
                candidate=candidate,
                test_inputs=self.test_vectors,
            )

            # Record mutation attempt in DAG
            self.lineage_dag.record_mutation(
                MutationRecord(
                    parent_id=parent.id,
                    candidate_id=candidate.id,
                    generation=gen,
                    mutator_name=mutator.name,
                    target_symbol=self.target_symbol,
                    accepted=verdict.approved,
                    speedup=verdict.speedup,
                    rejection_reason=verdict.rejection_reason,
                )
            )

            if verdict.approved:
                # Transmutation Approved: Perform atomic hot-swap
                self.hot_swapper.hot_swap(self.target_module, self.target_symbol, candidate)
                self.lineage_dag.add_chromosome(candidate, set_active=True)

                # Track telemetry
                active_ancestors = self.lineage_dag.get_ancestors(candidate.id)
                base_lat = active_ancestors[0].mean_latency_ns if active_ancestors else candidate.mean_latency_ns
                cumulative_speedup = (base_lat / candidate.mean_latency_ns) if (candidate.mean_latency_ns > 0 and base_lat > 0) else 1.0

                self.telemetry.record_generation(
                    generation=gen,
                    chromosome_id=candidate.id,
                    source_type=candidate.source_type.value,
                    mutator_name=mutator.name,
                    latency_ns=candidate.mean_latency_ns,
                    speedup=cumulative_speedup,
                )

                if self.render_dashboard:
                    self.dashboard.render_evolution_frame(
                        organism_name=self.name,
                        current_generation=gen,
                        status=f"EVOLUTION SUCCESSFUL ({mutator.name.upper()})",
                        active_chromosome=candidate,
                        lineage_dag=self.lineage_dag,
                        tracker=self.telemetry,
                    )

                return candidate

        # No mutator produced a viable mutation that passed the apoptotic gate
        return None

    def run_evolution(self, max_generations: int = 5) -> List[Chromosome]:
        """Runs the evolutionary loop until max generations or convergence."""
        evolved: List[Chromosome] = []
        for _ in range(max_generations):
            candidate = self.evolve_generation()
            if candidate is None:
                break
            evolved.append(candidate)
        return evolved

    def rollback(self) -> bool:
        """Rolls back the active phenotype to the previous generation."""
        res = self.hot_swapper.rollback(self.target_module, self.target_symbol)
        if res:
            parent_id = self.active_chromosome.parent_id
            if parent_id and parent_id in self.lineage_dag.chromosomes:
                self.lineage_dag.active_chromosome_id = parent_id
            return True
        return False

    def restore_baseline(self) -> None:
        """Restores the target module symbol back to its baseline unpatched implementation."""
        self.hot_swapper.restore_initial(self.target_module, self.target_symbol)

    def close(self) -> None:
        """Cleanly releases loaded native binaries and restores baseline phenotype."""
        self.restore_baseline()
        self.hot_swapper.unload_all()

    def __enter__(self) -> LivingOrganism:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

