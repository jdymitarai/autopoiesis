import pytest
from autopoiesis.core.apoptosis import ApoptoticGate
from autopoiesis.core.chromosome import Chromosome, SourceType


def baseline_mul(x: float, y: float) -> float:
    return x * y


def test_apoptosis_semantic_approval():
    gate = ApoptoticGate(min_speedup_threshold=0.01)  # allow any speed for unit testing
    cand_code = "def mul(x: float, y: float) -> float:\n    return x * y\n"
    chrom = Chromosome.create(1, SourceType.PYTHON_AST, "mul", cand_code)

    test_inputs = [((2.0, 3.0), {}), ((0.0, 5.0), {}), ((-4.0, 2.5), {})]
    verdict = gate.verify_candidate(
        baseline_fn=baseline_mul,
        candidate=chrom,
        test_inputs=test_inputs,
    )
    assert verdict.approved is True
    assert verdict.rejection_reason is None
    assert verdict.speedup > 0


def test_apoptosis_rejects_semantic_regression():
    gate = ApoptoticGate(min_speedup_threshold=0.01)
    # Mutation that introduces a subtle bug
    cand_code = "def mul(x: float, y: float) -> float:\n    return (x * y) + 0.001\n"
    chrom = Chromosome.create(1, SourceType.PYTHON_AST, "mul", cand_code)

    test_inputs = [((2.0, 3.0), {})]
    verdict = gate.verify_candidate(
        baseline_fn=baseline_mul,
        candidate=chrom,
        test_inputs=test_inputs,
    )
    assert verdict.approved is False
    assert "SEMANTIC_REGRESSION" in verdict.rejection_reason


def test_apoptosis_rejects_performance_regression():
    # Require 1000x speedup which a simple sleep will definitely fail
    gate = ApoptoticGate(min_speedup_threshold=1000.0)
    cand_code = "import time\ndef mul(x: float, y: float) -> float:\n    time.sleep(0.01)\n    return x * y\n"
    chrom = Chromosome.create(1, SourceType.PYTHON_AST, "mul", cand_code)

    test_inputs = [((2.0, 3.0), {})]
    verdict = gate.verify_candidate(
        baseline_fn=baseline_mul,
        candidate=chrom,
        test_inputs=test_inputs,
    )
    assert verdict.approved is False
    assert "PERFORMANCE_REGRESSION" in verdict.rejection_reason
