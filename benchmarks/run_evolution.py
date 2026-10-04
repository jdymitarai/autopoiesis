"""
Local Multi-Workload Evolutionary Benchmark Runner.
"""

import json
import os
import sys

# Ensure repository root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from autopoiesis import __version__
from autopoiesis.core.organism import LivingOrganism
from autopoiesis.mutators.ast_optimizer import ASTOptimizerMutator
from autopoiesis.mutators.rust_synthesizer import RustSynthesizerMutator
from autopoiesis.mutators.c_synthesizer import CSynthesizerMutator
from autopoiesis.workloads import mandelbrot, nbody


def run_local_benchmark():
    print(f"[*] Autopoiesis Engine v{__version__} - Local Evolutionary Benchmark")
    benchmarks_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts_dir = os.path.join(benchmarks_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    results = []

    # 1. Mandelbrot
    print("\n" + "=" * 60)
    print("[*] Benchmark 1: Mandelbrot Escape-Time Fractal")
    print("=" * 60)
    m_org = LivingOrganism(
        name="mandelbrot_organism",
        target_module=mandelbrot,
        target_symbol="mandelbrot_pixel",
        test_vectors=mandelbrot.generate_mandelbrot_test_vectors(),
        mutators=[ASTOptimizerMutator(), RustSynthesizerMutator(), CSynthesizerMutator()],
        render_dashboard=True,
        artifacts_dir=artifacts_dir,
    )
    m_org.run_evolution(max_generations=2)
    results.append({
        "workload": "mandelbrot",
        "symbol": "mandelbrot_pixel",
        "metrics": m_org.telemetry.to_dict_list(),
        "lineage": json.loads(m_org.lineage_dag.to_json()),
    })

    # 2. N-Body Simulation
    print("\n" + "=" * 60)
    print("[*] Benchmark 2: N-Body Gravitational Simulation")
    print("=" * 60)
    n_org = LivingOrganism(
        name="nbody_organism",
        target_module=nbody,
        target_symbol="nbody_simulation_energy",
        test_vectors=nbody.generate_nbody_test_vectors(),
        mutators=[ASTOptimizerMutator(), RustSynthesizerMutator(), CSynthesizerMutator()],
        render_dashboard=True,
        artifacts_dir=artifacts_dir,
    )
    n_org.run_evolution(max_generations=2)
    results.append({
        "workload": "nbody",
        "symbol": "nbody_simulation_energy",
        "metrics": n_org.telemetry.to_dict_list(),
        "lineage": json.loads(n_org.lineage_dag.to_json()),
    })

    out_file = os.path.join(benchmarks_dir, "local_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Local benchmark results saved to: {out_file}")


if __name__ == "__main__":
    run_local_benchmark()
