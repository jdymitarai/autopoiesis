import pytest
from autopoiesis.core.sandbox import IsolatedProcessSandbox


def test_sandbox_normal_execution():
    sandbox = IsolatedProcessSandbox(default_timeout_seconds=5.0)
    code = """
def add(a, b):
    return a + b
"""
    test_inputs = [((10, 20), {}), ((-5, 5), {}), ((100, 200), {})]
    res = sandbox.execute_in_quarantine(
        source_type="PYTHON_AST",
        code=code,
        entry_symbol="add",
        test_inputs=test_inputs,
        benchmark_repeats=5,
    )
    assert res.success is True
    assert res.outputs == [30, 0, 300]
    assert len(res.runtimes_ns) == 5
    assert res.mean_latency_ns > 0


def test_sandbox_timeout_quarantine():
    sandbox = IsolatedProcessSandbox(default_timeout_seconds=1.0)
    code = """
import time
def infinite_loop(x):
    while True:
        time.sleep(0.1)
"""
    test_inputs = [((1,), {})]
    res = sandbox.execute_in_quarantine(
        source_type="PYTHON_AST",
        code=code,
        entry_symbol="infinite_loop",
        test_inputs=test_inputs,
        timeout_seconds=1.0,
    )
    assert res.success is False
    assert res.error_type == "TIMEOUT"
    assert "timed out" in res.error_message


def test_sandbox_exception_handling():
    sandbox = IsolatedProcessSandbox(default_timeout_seconds=5.0)
    code = """
def broken(x):
    return 1 / 0
"""
    test_inputs = [((1,), {})]
    res = sandbox.execute_in_quarantine(
        source_type="PYTHON_AST",
        code=code,
        entry_symbol="broken",
        test_inputs=test_inputs,
    )
    assert res.success is False
    assert res.error_type == "ZeroDivisionError"
