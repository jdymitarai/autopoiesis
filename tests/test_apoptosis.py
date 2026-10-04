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


def test_apoptosis_rejects_segfault():
    """Verifies that an unmapped memory access segfault in sandbox triggers apoptosis with FATAL_SEGFAULT."""
    gate = ApoptoticGate(min_speedup_threshold=0.01)
    crash_code = """
import ctypes
def mul(x: float, y: float) -> float:
    ptr = ctypes.cast(1, ctypes.POINTER(ctypes.c_int))
    return float(ptr.contents.value)
"""
    chrom = Chromosome.create(1, SourceType.PYTHON_AST, "mul", crash_code)
    test_inputs = [((2.0, 3.0), {})]
    verdict = gate.verify_candidate(
        baseline_fn=baseline_mul,
        candidate=chrom,
        test_inputs=test_inputs,
    )
    assert verdict.approved is False
    assert "FATAL_SEGFAULT" in verdict.rejection_reason


def test_apoptosis_rejects_bool_type_mismatch():
    """Verifies that returning a float/int when bool is expected is rejected as a semantic regression."""
    def baseline_is_positive(x: float) -> bool:
        return x > 0

    gate = ApoptoticGate(min_speedup_threshold=0.01)
    # Candidate returns float 1.0 instead of boolean True
    cand_code = "def is_pos(x: float) -> float:\n    return 1.0 if x > 0 else 0.0\n"
    chrom = Chromosome.create(1, SourceType.PYTHON_AST, "is_pos", cand_code)

    test_inputs = [((5.0,), {})]
    verdict = gate.verify_candidate(
        baseline_fn=baseline_is_positive,
        candidate=chrom,
        test_inputs=test_inputs,
    )
    assert verdict.approved is False
    assert "SEMANTIC_REGRESSION" in verdict.rejection_reason

