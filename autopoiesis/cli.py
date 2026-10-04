"""
Command-Line Interface for the Autopoiesis Engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from autopoiesis import __version__
from autopoiesis.core.organism import LivingOrganism
from autopoiesis.workloads import mandelbrot, nbody

BANNER = r"""
    ___         __                  _           _     
   /   | __  __/ /_____  ____  ____(_)__  _____(_)____
  / /| |/ / / / __/ __ \/ __ \/ __ \/ _ \/ ___/ / ___/
 / ___ / /_/ / /_/ /_/ / /_/ / /_/ /  __(__  ) (__  ) 
/_/  |_\__,_/\__/\____/ .___/\____/\___/____/_/____/  
                     /_/                              
    Recursive Self-Improvement & Code Autophagy Engine
    Version {version}
"""


def cmd_evolve(args: argparse.Namespace) -> int:
    print(BANNER.format(version=__version__))
    workload_name = args.workload.lower()
    max_gens = args.generations

    if workload_name == "mandelbrot":
        import autopoiesis.workloads.mandelbrot as target_mod
        target_symbol = "mandelbrot_pixel"
        test_vectors = target_mod.generate_mandelbrot_test_vectors()
    elif workload_name == "nbody":
        import autopoiesis.workloads.nbody as target_mod
        target_symbol = "nbody_simulation_energy"
        test_vectors = target_mod.generate_nbody_test_vectors()
    else:
        print(f"Unknown workload: {workload_name}. Available: mandelbrot, nbody", file=sys.stderr)
        return 1

    print(f"[*] Initializing Living Organism: '{workload_name}_organism'")
    print(f"[*] Target Chromosome Symbol: {target_symbol}")
    print(f"[*] Verification Vectors: {len(test_vectors)} test cases")
    print(f"[*] Evolution Target: up to {max_gens} generations\n")

    organism = LivingOrganism(
        name=f"{workload_name}_organism",
        target_module=target_mod,
        target_symbol=target_symbol,
        test_vectors=test_vectors,
        render_dashboard=not args.no_dashboard,
        artifacts_dir=args.artifacts_dir,
    )

    evolved = organism.run_evolution(max_generations=max_gens)

    print("\n" + "=" * 60)
    print(f"[*] Evolution Finished. Generations Completed: {len(evolved)}")
    if evolved:
        final_chrom = organism.active_chromosome
        print(f"[*] Final Phenotype ID: {final_chrom.id}")
        print(f"[*] Final Source Type: {final_chrom.source_type.value}")
        print(f"[*] Final Fitness Speedup: {final_chrom.fitness:.2f}x vs Gen 0")
        if final_chrom.compiled_artifact_path:
            print(f"[*] Compiled Artifact: {final_chrom.compiled_artifact_path}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            f.write(organism.lineage_dag.to_json())
        print(f"[*] Lineage DAG exported to {args.json_out}")

    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    print(BANNER.format(version=__version__))
    return cmd_evolve(args)


def cmd_export_genome(args: argparse.Namespace) -> int:
    print(BANNER.format(version=__version__))
    workload_name = args.workload.lower()
    if workload_name == "mandelbrot":
        import autopoiesis.workloads.mandelbrot as target_mod
        target_symbol = "mandelbrot_pixel"
        test_vectors = target_mod.generate_mandelbrot_test_vectors()
    elif workload_name == "nbody":
        import autopoiesis.workloads.nbody as target_mod
        target_symbol = "nbody_simulation_energy"
        test_vectors = target_mod.generate_nbody_test_vectors()
    else:
        print(f"Unknown workload: {workload_name}", file=sys.stderr)
        return 1

    organism = LivingOrganism(
        name=f"{workload_name}_organism",
        target_module=target_mod,
        target_symbol=target_symbol,
        test_vectors=test_vectors,
        render_dashboard=False,
        artifacts_dir=args.artifacts_dir,
    )

    if args.evolve_first > 0:
        print(f"[*] Pre-evolving organism for {args.evolve_first} generations...")
        organism.run_evolution(max_generations=args.evolve_first)

    from autopoiesis.core.breeding import export_genome_package

    pkg = export_genome_package(
        organism=organism,
        breeder_handle=args.breeder,
        output_path=args.output,
        notes=args.notes,
    )
    print(f"\n[+] Successfully exported breeding genome to: {args.output}")
    print(f"    Breeder Handle: {pkg['breeder']}")
    print(f"    Active Phenotype: {pkg['source_type']}")
    print(f"    Measured Speedup: {pkg['active_speedup']:.2f}x")
    print(f"[*] You can now submit this genome via PR to https://github.com/jdymitarai/autopoiesis!")
    return 0


def cmd_import_genome(args: argparse.Namespace) -> int:
    print(BANNER.format(version=__version__))
    workload_name = args.workload.lower()
    if workload_name == "mandelbrot":
        import autopoiesis.workloads.mandelbrot as target_mod
        target_symbol = "mandelbrot_pixel"
        test_vectors = target_mod.generate_mandelbrot_test_vectors()
    elif workload_name == "nbody":
        import autopoiesis.workloads.nbody as target_mod
        target_symbol = "nbody_simulation_energy"
        test_vectors = target_mod.generate_nbody_test_vectors()
    else:
        print(f"Unknown workload: {workload_name}", file=sys.stderr)
        return 1

    organism = LivingOrganism(
        name=f"{workload_name}_organism",
        target_module=target_mod,
        target_symbol=target_symbol,
        test_vectors=test_vectors,
        render_dashboard=False,
        artifacts_dir=args.artifacts_dir,
    )

    from autopoiesis.core.breeding import import_and_verify_genome_package

    print(f"[*] Importing and verifying foreign genome from: {args.input}")
    success, chrom, speedup, msg = import_and_verify_genome_package(
        package_path=args.input,
        organism=organism,
        min_speedup_per_step=args.min_speedup,
    )
    if success:
        print(f"\n[+] {msg}")
        print(f"[*] Spliced into lineage DAG: Active generation is now Gen {organism.current_generation}")
        return 0
    else:
        print(f"\n[-] {msg}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="autopoiesis",
        description="Digital Autopoiesis: Self-Evolving & Mutating Codebase Engine",
    )
    parser.add_argument("--version", action="version", version=f"autopoiesis {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    # evolve command
    evolve_p = subparsers.add_parser("evolve", help="Run evolutionary optimization on a workload")
    evolve_p.add_argument(
        "--workload", "-w",
        default="mandelbrot",
        choices=["mandelbrot", "nbody"],
        help="Target computational workload",
    )
    evolve_p.add_argument(
        "--generations", "-g",
        type=int,
        default=3,
        help="Maximum generations to attempt",
    )
    evolve_p.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Disable interactive terminal dashboard rendering",
    )
    evolve_p.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Path to export final lineage JSON",
    )
    evolve_p.add_argument(
        "--artifacts-dir",
        type=str,
        default=None,
        help="Directory to store compiled shared libraries",
    )

    # benchmark command
    bench_p = subparsers.add_parser("benchmark", help="Run benchmark suite")
    bench_p.add_argument("--workload", "-w", default="mandelbrot", choices=["mandelbrot", "nbody"])
    bench_p.add_argument("--generations", "-g", type=int, default=3)
    bench_p.add_argument("--no-dashboard", action="store_true")
    bench_p.add_argument("--json-out", type=str, default=None)
    bench_p.add_argument("--artifacts-dir", type=str, default=None, help="Directory to store compiled shared libraries")

    # export-genome command
    export_p = subparsers.add_parser("export-genome", help="Export an evolved chromosome for community sharing")
    export_p.add_argument("--workload", "-w", default="mandelbrot", choices=["mandelbrot", "nbody"])
    export_p.add_argument("--output", "-o", default="breeder_genome.json", help="Path to write exported genome package")
    export_p.add_argument("--breeder", "-b", default="@anonymous", help="Your GitHub username or breeder handle")
    export_p.add_argument("--notes", "-n", default=None, help="Evolution environment notes (e.g. CPU/OS/flags)")
    export_p.add_argument("--evolve-first", "-e", type=int, default=2, help="Number of generations to evolve before exporting")
    export_p.add_argument("--artifacts-dir", type=str, default=None)

    # import-genome command
    import_p = subparsers.add_parser("import-genome", help="Import, verify, and splice a foreign chromosome through the Apoptotic Gate")
    import_p.add_argument("--input", "-i", required=True, help="Path to genome package JSON")
    import_p.add_argument("--workload", "-w", default="mandelbrot", choices=["mandelbrot", "nbody"])
    import_p.add_argument("--min-speedup", type=float, default=1.0, help="Minimum speedup threshold required to accept foreign genome")
    import_p.add_argument("--artifacts-dir", type=str, default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command in ("evolve", "benchmark"):
        sys.exit(cmd_evolve(args))
    elif args.command == "export-genome":
        sys.exit(cmd_export_genome(args))
    elif args.command == "import-genome":
        sys.exit(cmd_import_genome(args))


if __name__ == "__main__":
    main()
