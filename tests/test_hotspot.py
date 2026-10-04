import pytest
from autopoiesis.core.hotspot import HotspotDetector, ASTComplexityVisitor


def sample_kernel(n: int) -> float:
    total = 0.0
    for i in range(n):
        for j in range(10):
            total += (i * 2.5) + (j / 1.5)
    return total


def test_ast_complexity_visitor():
    profile = HotspotDetector.analyze_function_ast(sample_kernel)
    assert profile.function_name == "sample_kernel"
    assert profile.loop_depth == 2
    assert profile.arithmetic_op_count >= 4
    assert profile.is_pure_numeric is True
    assert profile.is_transpilable is True


def test_workload_profiler():
    detector = HotspotDetector()
    profiles = detector.profile_workload(
        workload_fn=lambda: sample_kernel(500),
        top_k=5,
    )
    assert len(profiles) > 0
    func_names = [p.function_name for p in profiles]
    assert "sample_kernel" in func_names
