"""
Empirical Multi-Generation Evolution Benchmark Trial on Google Colab.

Executes live code autophagy and dynamic C compilation on Google Colab's Linux kernel,
verifies zero regressions across test vectors, and saves empirical benchmark metrics and plots.
"""

import json
import os
import sys
import time

# Ensure /content is on sys.path
if "/content" not in sys.path:
    sys.path.insert(0, "/content")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import autopoiesis
from autopoiesis.core.organism import LivingOrganism
from autopoiesis.mutators.ast_optimizer import ASTOptimizerMutator
from autopoiesis.mutators.c_synthesizer import CSynthesizerMutator
from autopoiesis.workloads import mandelbrot, nbody


def run_workload_trial(name: str, target_mod: any, symbol: str, test_vectors: list, max_gens: int = 3):
    print(f"\n{'='*70}")
    print(f"[*] Starting Empirical Evolution Trial on Colab: {name}")
    print(f"[*] Target Symbol: {symbol} | Test Vectors: {len(test_vectors)}")
    print(f"{'='*70}\n")

    organism = LivingOrganism(
        name=f"colab_{name}_organism",
        target_module=target_mod,
        target_symbol=symbol,
        test_vectors=test_vectors,
        mutators=[
            ASTOptimizerMutator(),
            CSynthesizerMutator(extra_flags=["-O3", "-fPIC", "-shared", "-ffast-math", "-march=native"]),
        ],
        min_speedup_per_step=1.02,
        render_dashboard=True,
        artifacts_dir="/content/artifacts",
    )

    evolved = organism.run_evolution(max_generations=max_gens)
    print(f"\n[+] Trial Finished for {name}. Generations Evolved: {len(evolved)}")
    
    return {
        "workload": name,
        "symbol": symbol,
        "generations_evolved": len(evolved),
        "metrics": organism.telemetry.to_dict_list(),
        "lineage": json.loads(organism.lineage_dag.to_json()),
    }


def generate_plots(results: list, output_path: str):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#0d1117')

    for ax in (ax1, ax2):
        ax.set_facecolor('#161b22')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_color('#30363d')

    colors = ['#58a6ff', '#3fb950', '#d29922']

    # Subplot 1: Generational Speedup Curve
    for idx, r in enumerate(results):
        workload = r["workload"]
        gens = [m["generation"] for m in r["metrics"]]
        speedups = [m["speedup_vs_baseline"] for m in r["metrics"]]
        types = [m["source_type"] for m in r["metrics"]]

        ax1.plot(gens, speedups, marker='o', linewidth=2.5, markersize=8, color=colors[idx % len(colors)], label=f"{workload.capitalize()}")
        for g, s, t in zip(gens, speedups, types):
            ax1.annotate(f"{s:.1f}x\n({t.split('_')[0]})", (g, s), textcoords="offset points", xytext=(0, 10), ha='center', color='white', fontsize=9)

    ax1.set_title("Empirical Recursive Self-Improvement (Speedup vs Gen 0)", fontsize=13, fontweight='bold', pad=12)
    ax1.set_xlabel("Evolutionary Generation", fontsize=11)
    ax1.set_ylabel("Speedup Multiplier", fontsize=11)
    ax1.grid(True, linestyle='--', alpha=0.3, color='#8b949e')
    ax1.legend(facecolor='#21262d', edgecolor='#30363d', labelcolor='white')

    # Subplot 2: Latency Reduction (Log scale)
    for idx, r in enumerate(results):
        workload = r["workload"]
        gens = [m["generation"] for m in r["metrics"]]
        latencies_ms = [m["latency_ns"] / 1e6 for m in r["metrics"]]

        ax2.plot(gens, latencies_ms, marker='s', linewidth=2.5, markersize=8, color=colors[idx % len(colors)], label=f"{workload.capitalize()}")

    ax2.set_yscale('log')
    ax2.set_title("Execution Latency Reduction (Log Scale)", fontsize=13, fontweight='bold', pad=12)
    ax2.set_xlabel("Evolutionary Generation", fontsize=11)
    ax2.set_ylabel("Latency per Call (ms)", fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#8b949e')
    ax2.legend(facecolor='#21262d', edgecolor='#30363d', labelcolor='white')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Saved publication-quality benchmark plot to: {output_path}")


def main():
    print(f"[*] Starting Autopoiesis Colab Evolution Trial [Engine v{autopoiesis.__version__}]")
    os.makedirs("/content/artifacts", exist_ok=True)

    results = []

    # 1. Mandelbrot Fractal Workload Trial
    mandelbrot_res = run_workload_trial(
        name="mandelbrot",
        target_mod=mandelbrot,
        symbol="mandelbrot_pixel",
        test_vectors=mandelbrot.generate_mandelbrot_test_vectors(),
        max_gens=2,
    )
    results.append(mandelbrot_res)

    # 2. N-Body Interaction Workload Trial
    nbody_res = run_workload_trial(
        name="nbody",
        target_mod=nbody,
        symbol="nbody_simulation_energy",
        test_vectors=nbody.generate_nbody_test_vectors(),
        max_gens=2,
    )
    results.append(nbody_res)

    # Export results JSON
    json_path = "/content/colab_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Exported empirical benchmark JSON to: {json_path}")

    # Generate visualization plot
    plot_path = "/content/speedup_curve.png"
    generate_plots(results, plot_path)

    print("\n" + "=" * 70)
    print("[+] ALL COLAB EMPIRICAL BENCHMARKS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
