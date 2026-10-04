"""
Isolated Sub-Process Sandboxing for Mutated Chromosomes.

Executes candidate mutations in a quarantined subprocess. If a mutant segfaults,
leaks memory, triggers an illegal instruction, or enters an infinite loop,
the fault is quarantined and does not terminate the host organism.
"""

from __future__ import annotations

import base64
import json
import os
import pickle
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SandboxExecutionResult:
    """Outcome of sandboxed candidate execution."""
    success: bool
    outputs: List[Any] = field(default_factory=list)
    runtimes_ns: List[int] = field(default_factory=list)
    mean_latency_ns: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: int = 0
    segfault_detected: bool = False


SANDBOX_WORKER_SCRIPT = """
import sys
import os
import time
import base64
import pickle
import traceback
import ctypes

def main():
    try:
        raw_payload = sys.stdin.read()
        if not raw_payload:
            sys.exit(1)
        
        payload = pickle.loads(base64.b64decode(raw_payload.encode('ascii')))
        source_type = payload.get("source_type")
        code = payload.get("code")
        artifact_path = payload.get("artifact_path")
        entry_symbol = payload.get("entry_symbol")
        test_inputs = payload.get("test_inputs", [])
        benchmark_repeats = payload.get("benchmark_repeats", 1)
        
        target_fn = None
        
        if source_type == "PYTHON_AST":
            namespace = {}
            exec(code, namespace)
            target_fn = namespace[entry_symbol]
        elif source_type in ("C_EXTENSION", "RUST_CDYLIB"):
            if not artifact_path or not os.path.exists(artifact_path):
                raise FileNotFoundError(f"Compiled artifact not found at {artifact_path}")
            
            # Load dynamic shared library
            lib = ctypes.CDLL(artifact_path)
            
            # Execute wrapper code that binds ctypes signatures
            namespace = {"ctypes": ctypes, "lib": lib}
            exec(code, namespace)
            target_fn = namespace[entry_symbol]
        else:
            raise ValueError(f"Unknown source type {source_type}")
        
        outputs = []
        runtimes = []
        
        # Phase 1: Correctness verification across all test inputs
        for args, kwargs in test_inputs:
            res = target_fn(*args, **kwargs)
            outputs.append(res)
            
        # Phase 2: High-resolution hardware timing
        if test_inputs and benchmark_repeats > 0:
            first_args, first_kwargs = test_inputs[0]
            # Warmup
            for _ in range(3):
                target_fn(*first_args, **first_kwargs)
            
            # Measured runs
            for _ in range(benchmark_repeats):
                t0 = time.perf_counter_ns()
                target_fn(*first_args, **first_kwargs)
                t1 = time.perf_counter_ns()
                runtimes.append(t1 - t0)
                
        result = {
            "success": True,
            "outputs": outputs,
            "runtimes_ns": runtimes,
            "error_type": None,
            "error_message": None,
        }
    except Exception as e:
        result = {
            "success": False,
            "outputs": [],
            "runtimes_ns": [],
            "error_type": type(e).__name__,
            "error_message": str(e) + "\\n" + traceback.format_exc(),
        }
        
    encoded_resp = base64.b64encode(pickle.dumps(result)).decode('ascii')
    sys.stdout.write("<<<AUTOOPOIESIS_RESULT_START>>>\\n")
    sys.stdout.write(encoded_resp + "\\n")
    sys.stdout.write("<<<AUTOOPOIESIS_RESULT_END>>>\\n")
    sys.stdout.flush()

if __name__ == '__main__':
    main()
"""


class IsolatedProcessSandbox:
    """Quarantine execution sandbox protecting the living organism."""

    def __init__(self, default_timeout_seconds: float = 10.0) -> None:
        self.default_timeout = default_timeout_seconds

    def execute_in_quarantine(
        self,
        source_type: str,
        code: str,
        entry_symbol: str,
        test_inputs: List[Tuple[tuple, dict]],
        artifact_path: Optional[str] = None,
        benchmark_repeats: int = 15,
        timeout_seconds: Optional[float] = None,
    ) -> SandboxExecutionResult:
        """Executes candidate code inside an isolated child process."""
        timeout = timeout_seconds or self.default_timeout

        payload = {
            "source_type": source_type,
            "code": code,
            "artifact_path": artifact_path,
            "entry_symbol": entry_symbol,
            "test_inputs": test_inputs,
            "benchmark_repeats": benchmark_repeats,
        }
        encoded_payload = base64.b64encode(pickle.dumps(payload)).decode("ascii")

        cmd = [sys.executable, "-c", SANDBOX_WORKER_SCRIPT]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(input=encoded_payload, timeout=timeout)
            ret_code = proc.returncode

            # Check for crash signals (Segfault: -11 on Unix, 0xC0000005 on Windows)
            is_segfault = False
            if ret_code != 0:
                if ret_code in (-11, -8, -4, 139, 3221225477, -1073741819):  # 0xC0000005 = 3221225477
                    is_segfault = True
                return SandboxExecutionResult(
                    success=False,
                    exit_code=ret_code,
                    segfault_detected=is_segfault,
                    error_type="SEGFAULT" if is_segfault else "PROCESS_CRASH",
                    error_message=f"Process terminated with exit code {ret_code}. stderr: {stderr.strip()}",
                )

            # Parse sandbox output
            start_tag = "<<<AUTOOPOIESIS_RESULT_START>>>"
            end_tag = "<<<AUTOOPOIESIS_RESULT_END>>>"
            if start_tag in stdout and end_tag in stdout:
                raw_data = stdout.split(start_tag)[1].split(end_tag)[0].strip()
                resp = pickle.loads(base64.b64decode(raw_data.encode("ascii")))
                runtimes = resp.get("runtimes_ns", [])
                mean_latency = float(sum(runtimes) / len(runtimes)) if runtimes else 0.0

                return SandboxExecutionResult(
                    success=resp.get("success", False),
                    outputs=resp.get("outputs", []),
                    runtimes_ns=runtimes,
                    mean_latency_ns=mean_latency,
                    error_type=resp.get("error_type"),
                    error_message=resp.get("error_message"),
                    exit_code=0,
                    segfault_detected=False,
                )
            else:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=ret_code,
                    error_type="MALFORMED_SANDBOX_OUTPUT",
                    error_message=f"Could not locate result delimiters in stdout: {stdout}\nstderr: {stderr}",
                )

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return SandboxExecutionResult(
                success=False,
                exit_code=-9,
                error_type="TIMEOUT",
                error_message=f"Sandbox execution timed out after {timeout} seconds (potential infinite loop).",
            )
        except Exception as ex:
            return SandboxExecutionResult(
                success=False,
                exit_code=-1,
                error_type="SANDBOX_LAUNCH_FAILURE",
                error_message=str(ex),
            )
