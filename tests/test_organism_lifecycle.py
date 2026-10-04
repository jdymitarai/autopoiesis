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

    # Run evolution for Generation 1 (AST Optimizer)
    cand1 = organism.evolve_generation()
    assert cand1 is not None
    assert organism.current_generation == 1
    assert organism.active_chromosome.id == cand1.id
    assert cand1.mutation_meta.get("mutator") == "ast_optimizer"
    assert len(organism.lineage_dag.chromosomes) == 2

    # Verify that the living module has been hot-swapped and computes identical results
    assert mod.compute_sum(10) == compute_sum(10)
    assert mod.compute_sum(50) == compute_sum(50)

    # Run evolution for Generation 2 (Rust Synthesizer cdylib)
    cand2 = organism.evolve_generation()
    assert cand2 is not None
    assert organism.current_generation == 2
    assert organism.active_chromosome.id == cand2.id
    assert cand2.mutation_meta.get("mutator") == "rust_synthesizer"
    assert len(organism.lineage_dag.chromosomes) == 3

    assert mod.compute_sum(10) == compute_sum(10)

    # Test rollback to Gen 1
    rolled = organism.rollback()
    assert rolled is True
    assert organism.active_chromosome.generation == 1
    assert organism.active_chromosome.id == cand1.id

    # Test rollback to Gen 0
    rolled2 = organism.rollback()
    assert rolled2 is True
    assert organism.active_chromosome.generation == 0
    assert mod.compute_sum(10) == compute_sum(10)


def test_organism_nbody_with_math_lifecycle(tmp_path):
    """Verifies that workloads requiring module-level imports like math evolve without NameError."""
    from autopoiesis.workloads import nbody

    organism = LivingOrganism(
        name="test_nbody_organism",
        target_module=nbody,
        target_symbol="nbody_simulation_energy",
        test_vectors=nbody.generate_nbody_test_vectors()[:2],
        mutators=[ASTOptimizerMutator(), RustSynthesizerMutator()],
        min_speedup_per_step=0.01,
        render_dashboard=False,
        artifacts_dir=str(tmp_path),
    )

    # Evolve Gen 1: AST optimizer with math preserved
    cand = organism.evolve_generation()
    assert cand is not None
    assert organism.current_generation == 1
    # Verify no NameError when calling hot-swapped function
    res = nbody.nbody_simulation_energy(5, 2)
    assert res > 0.0

    # Roll back cleanly
    assert organism.rollback() is True

