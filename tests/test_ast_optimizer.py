import pytest
from autopoiesis.core.chromosome import Chromosome, SourceType
from autopoiesis.core.hotspot import HotspotDetector
from autopoiesis.mutators.ast_optimizer import ASTOptimizerMutator


def sample_loop_calc(n: int) -> float:
    acc = 0.0
    for i in range(n):
        acc += abs(i * 2.0)
    return acc


def test_ast_optimizer_mutation():
    mutator = ASTOptimizerMutator()
    profile = HotspotDetector.analyze_function_ast(sample_loop_calc)

    parent_chrom = Chromosome.create(
        generation=0,
        source_type=SourceType.PYTHON_AST,
        entry_symbol="sample_loop_calc",
        code=profile.source_code,
    )

    candidate = mutator.mutate(parent_chrom, profile)
    assert candidate is not None
    assert candidate.generation == 1
    assert candidate.parent_id == parent_chrom.id
    assert candidate.source_type == SourceType.PYTHON_AST

    # Check that cached builtins were injected
    assert "_fast_range = range" in candidate.code or "_fast_range" in candidate.code

    # Execute mutated code in namespace
    ns = {}
    exec(candidate.code, ns)
    mutated_fn = ns["sample_loop_calc"]
    assert mutated_fn(10) == sample_loop_calc(10)
