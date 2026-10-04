import pytest
import types
from autopoiesis.core.organism import LivingOrganism
from autopoiesis.mutators.ast_optimizer import ASTOptimizerMutator
from autopoiesis.mutators.rust_synthesizer import RustSynthesizerMutator
from autopoiesis.workloads import mandelbrot


def test_organism_lifecycle_end_to_end(tmp_path):
    # Dynamic target module
    mod = types.ModuleType("test_target_module")
    
    # Define a pure Python test function
    def compute_sum(n: int) -> float:
        total = 0.0
        for i in range(n):
            total += abs(float(i))
        return total

    mod.compute_sum = compute_sum

    test_vectors = [
        ((10,), {}),
        ((50,), {}),
        ((100,), {}),
    ]

    organism = LivingOrganism(
        name="test_organism",
        target_module=mod,
        target_symbol="compute_sum",
        test_vectors=test_vectors,
        mutators=[ASTOptimizerMutator(), RustSynthesizerMutator()],
        min_speedup_per_step=0.01,  # allow all successful mutations to pass gate in unit test
        render_dashboard=False,
        artifacts_dir=str(tmp_path),
    )

    assert organism.current_generation == 0
    assert organism.active_chromosome.generation == 0
    assert len(organism.lineage_dag.chromosomes) == 1

    # Run evolution for 1 generation
    cand = organism.evolve_generation()
    assert cand is not None
    assert organism.current_generation == 1
    assert organism.active_chromosome.id == cand.id
    assert len(organism.lineage_dag.chromosomes) == 2

    # Verify that the living module has been hot-swapped and computes identical results
    assert mod.compute_sum(10) == compute_sum(10)
    assert mod.compute_sum(50) == compute_sum(50)

    # Test rollback
    rolled = organism.rollback()
    assert rolled is True
    assert organism.active_chromosome.generation == 0
    assert mod.compute_sum(10) == compute_sum(10)
