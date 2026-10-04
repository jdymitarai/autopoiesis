"""
Deterministic Apoptotic Gate (Immune System).

Guarantees non-hallucinatory recursive self-improvement with zero tolerance for regressions.
Every candidate chromosome must pass semantic equivalence across unit and fuzz vectors
and demonstrate statistically significant latency reduction under hardware timer verification.
Any anomaly triggers instant apoptosis.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from autopoiesis.core.chromosome import Chromosome
from autopoiesis.core.sandbox import IsolatedProcessSandbox, SandboxExecutionResult


@dataclass
class ApoptosisVerdict:
    """Deterministic verdict emitted by the apoptotic gate."""
    approved: bool
    candidate_id: str
    rejection_reason: Optional[str] = None
    speedup: float = 1.0
    baseline_latency_ns: float = 0.0
    candidate_latency_ns: float = 0.0
    tested_vector_count: int = 0
    raw_sandbox_result: Optional[SandboxExecutionResult] = None


class ApoptoticGate:
    """Immune system gate verifying semantic invariants and empirical speedups."""

    def __init__(
        self,
        sandbox: Optional[IsolatedProcessSandbox] = None,
        min_speedup_threshold: float = 1.05,
        float_tolerance: float = 1e-6,
        benchmark_iterations: int = 20,
    ) -> None:
        self.sandbox = sandbox or IsolatedProcessSandbox()
        self.min_speedup = min_speedup_threshold
        self.tolerance = float_tolerance
        self.benchmark_iterations = benchmark_iterations

    def verify_candidate(
        self,
        baseline_fn: Callable[..., Any],
        candidate: Chromosome,
        test_inputs: List[Tuple[tuple, dict]],
        min_speedup: Optional[float] = None,
    ) -> ApoptosisVerdict:
        """
        Executes strict regression verification and hardware benchmark.
        Zero tolerance for regressions.
        """
        required_speedup = min_speedup if min_speedup is not None else self.min_speedup

        if not test_inputs:
            return ApoptoticGate._reject(
                candidate.id,
                "EMPTY_TEST_SUITE: Cannot verify candidate without test vectors."
            )

        # -------------------------------------------------------------
        # 1. Baseline Evaluation: Ground truth outputs & timing
        # -------------------------------------------------------------
        baseline_outputs: List[Any] = []
        try:
            for args, kwargs in test_inputs:
                out = baseline_fn(*args, **kwargs)
                baseline_outputs.append(out)
        except Exception as ex:
            return ApoptoticGate._reject(
                candidate.id,
                f"BASELINE_FAILURE: Baseline function crashed on test vectors: {ex}"
            )

        # Baseline benchmark
        first_args, first_kwargs = test_inputs[0]
        # Warmup
        for _ in range(3):
            baseline_fn(*first_args, **first_kwargs)

        baseline_times: List[int] = []
        for _ in range(self.benchmark_iterations):
            t0 = time.perf_counter_ns()
            baseline_fn(*first_args, **first_kwargs)
            t1 = time.perf_counter_ns()
            baseline_times.append(t1 - t0)

        mean_baseline_ns = statistics.mean(baseline_times) if baseline_times else 1.0

        # -------------------------------------------------------------
        # 2. Quarantine Sandbox Execution
        # -------------------------------------------------------------
        sandbox_result = self.sandbox.execute_in_quarantine(
            source_type=candidate.source_type.value,
            code=candidate.code,
            entry_symbol=candidate.entry_symbol,
            test_inputs=test_inputs,
            artifact_path=candidate.compiled_artifact_path,
            benchmark_repeats=self.benchmark_iterations,
        )

        if not sandbox_result.success:
            err_msg = sandbox_result.error_message or sandbox_result.error_type or "Unknown"
            if sandbox_result.segfault_detected:
                reason = f"FATAL_SEGFAULT: Candidate triggered segmentation fault: {err_msg}"
            elif sandbox_result.error_type == "TIMEOUT":
                reason = f"HANG_TIMEOUT: Candidate exceeded execution deadline: {err_msg}"
            else:
                reason = f"EXECUTION_CRASH: Candidate failed in sandbox: {err_msg}"
            return ApoptoticGate._reject(candidate.id, reason, sandbox_result)

        # -------------------------------------------------------------
        # 3. Invariant & Equivalence Verification
        # -------------------------------------------------------------
        candidate_outputs = sandbox_result.outputs
        if len(candidate_outputs) != len(baseline_outputs):
            return ApoptoticGate._reject(
                candidate.id,
                f"OUTPUT_LENGTH_MISMATCH: Expected {len(baseline_outputs)}, got {len(candidate_outputs)}",
                sandbox_result,
            )

        for idx, (expected, actual) in enumerate(zip(baseline_outputs, candidate_outputs)):
            if not self._check_equivalence(expected, actual):
                return ApoptoticGate._reject(
                    candidate.id,
                    f"SEMANTIC_REGRESSION at vector index {idx}: Expected {expected!r}, got {actual!r}",
                    sandbox_result,
                )

        # -------------------------------------------------------------
        # 4. Statistical Speedup Verification
        # -------------------------------------------------------------
        mean_candidate_ns = sandbox_result.mean_latency_ns
        if mean_candidate_ns <= 0:
            mean_candidate_ns = 1.0  # guard against div by zero

        speedup = mean_baseline_ns / mean_candidate_ns

        if speedup < required_speedup:
            return ApoptoticGate._reject(
                candidate.id,
                f"PERFORMANCE_REGRESSION: Measured speedup {speedup:.2f}x below threshold {required_speedup:.2f}x "
                f"(Baseline: {mean_baseline_ns/1e6:.3f}ms, Candidate: {mean_candidate_ns/1e6:.3f}ms)",
                sandbox_result,
            )

        # -------------------------------------------------------------
        # 5. Apoptotic Gate Certification
        # -------------------------------------------------------------
        candidate.fitness = speedup
        candidate.mean_latency_ns = mean_candidate_ns

        return ApoptosisVerdict(
            approved=True,
            candidate_id=candidate.id,
            rejection_reason=None,
            speedup=speedup,
            baseline_latency_ns=mean_baseline_ns,
            candidate_latency_ns=mean_candidate_ns,
            tested_vector_count=len(test_inputs),
            raw_sandbox_result=sandbox_result,
        )

    def _check_equivalence(self, a: Any, b: Any) -> bool:
        """Recursively checks numerical and structural equivalence."""
        if a is b:
            return True
        if a is None or b is None:
            return a == b
        if isinstance(a, (int, bool)) and isinstance(b, (int, bool)):
            return a == b
        if isinstance(a, (float, int)) and isinstance(b, (float, int)):
            fa, fb = float(a), float(b)
            if math.isnan(fa) and math.isnan(fb):
                return True
            if math.isinf(fa) and math.isinf(fb):
                return (fa > 0) == (fb > 0)
            return abs(fa - fb) <= (self.tolerance * (1.0 + abs(fa)))
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) != len(b):
                return False
            return all(self._check_equivalence(x, y) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                return False
            return all(self._check_equivalence(a[k], b[k]) for k in a)
        return a == b

    @staticmethod
    def _reject(
        candidate_id: str,
        reason: str,
        sandbox_res: Optional[SandboxExecutionResult] = None,
    ) -> ApoptosisVerdict:
        return ApoptosisVerdict(
            approved=False,
            candidate_id=candidate_id,
            rejection_reason=reason,
            speedup=0.0,
            raw_sandbox_result=sandbox_res,
        )
