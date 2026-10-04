"""
Unit tests for the distributed breeding and genome sharing protocol.
"""

import json
import os
import tempfile
import pytest

from autopoiesis.core.organism import LivingOrganism
from autopoiesis.core.breeding import export_genome_package, import_and_verify_genome_package
from autopoiesis.workloads import mandelbrot


def test_export_and_import_genome_lifecycle():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        test_vectors = mandelbrot.generate_mandelbrot_test_vectors()

        # Step 1: Breeder A evolves organism for 2 generations
        breeder_a_organism = LivingOrganism(
            name="breeder_a_organism",
            target_module=mandelbrot,
            target_symbol="mandelbrot_pixel",
            test_vectors=test_vectors,
            render_dashboard=False,
            artifacts_dir=os.path.join(tmp_dir, "breeder_a_artifacts"),
        )
        try:
            breeder_a_organism.run_evolution(max_generations=2)
            assert breeder_a_organism.current_generation >= 1

            # Step 2: Breeder A exports genome package
            package_file = os.path.join(tmp_dir, "shared_mandelbrot_genome.json")
            pkg = export_genome_package(
                organism=breeder_a_organism,
                breeder_handle="@breeder_alice",
                output_path=package_file,
                notes="Trained on high-performance node",
            )

            assert os.path.exists(package_file)
            assert pkg["breeder"] == "@breeder_alice"
            assert pkg["schema_version"] == "1.0"
            assert pkg["target_symbol"] == "mandelbrot_pixel"
        finally:
            breeder_a_organism.close()

        # Step 3: Breeder B imports genome package into fresh Gen 0 organism
        breeder_b_organism = LivingOrganism(
            name="breeder_b_organism",
            target_module=mandelbrot,
            target_symbol="mandelbrot_pixel",
            test_vectors=test_vectors,
            render_dashboard=False,
            artifacts_dir=os.path.join(tmp_dir, "breeder_b_artifacts"),
        )
        try:
            assert breeder_b_organism.current_generation == 0
            assert breeder_b_organism.active_chromosome.generation == 0

            success, adopted_chrom, speedup, msg = import_and_verify_genome_package(
                package_path=package_file,
                organism=breeder_b_organism,
                min_speedup_per_step=1.0,
            )

            assert success is True
            assert adopted_chrom is not None
            assert speedup >= 1.0
            assert breeder_b_organism.current_generation == 1
            assert breeder_b_organism.active_chromosome.id == adopted_chrom.id
            assert adopted_chrom.mutation_meta.get("breeder") == "@breeder_alice"
        finally:
            breeder_b_organism.close()


def test_import_rejects_corrupted_genome():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        test_vectors = mandelbrot.generate_mandelbrot_test_vectors()
        organism = LivingOrganism(
            name="recipient_organism",
            target_module=mandelbrot,
            target_symbol="mandelbrot_pixel",
            test_vectors=test_vectors,
            render_dashboard=False,
            artifacts_dir=tmp_dir,
        )
        try:
            # Corrupted package with target symbol mismatch
            bad_pkg_file = os.path.join(tmp_dir, "bad_package.json")
            with open(bad_pkg_file, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": "1.0",
                    "target_symbol": "wrong_function_name",
                    "breeder": "@malicious",
                    "chromosome": {},
                }, f)

            success, chrom, speedup, msg = import_and_verify_genome_package(
                package_path=bad_pkg_file,
                organism=organism,
            )
            assert success is False
            assert chrom is None
            assert "mismatch" in msg
        finally:
            organism.close()


def test_import_rejects_malicious_security_violations():
    """Verifies that malicious payloads (arbitrary code execution, system calls) are caught before execution."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        test_vectors = mandelbrot.generate_mandelbrot_test_vectors()
        organism = LivingOrganism(
            name="security_tester",
            target_module=mandelbrot,
            target_symbol="mandelbrot_pixel",
            test_vectors=test_vectors,
            render_dashboard=False,
            artifacts_dir=tmp_dir,
        )
        try:
            # 1. Malicious Python payload attempting to import 'os' and call 'eval'
            malicious_py_pkg = os.path.join(tmp_dir, "malicious_py.json")
            with open(malicious_py_pkg, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": "1.0",
                    "target_symbol": "mandelbrot_pixel",
                    "breeder": "@attacker",
                    "chromosome": {
                        "id": "evil1234",
                        "generation": 1,
                        "parent_id": "gen0",
                        "source_type": "PYTHON_AST",
                        "entry_symbol": "mandelbrot_pixel",
                        "code": "import os\ndef mandelbrot_pixel(c_real, c_imag, max_iter):\n    eval('os.system(\"calc\")')\n    return 0\n",
                    },
                }, f)

            success, chrom, speedup, msg = import_and_verify_genome_package(
                package_path=malicious_py_pkg,
                organism=organism,
            )
            assert success is False
            assert chrom is None
            assert "SECURITY_VIOLATION" in msg
            assert "os" in msg

            # 2. Malicious C payload attempting to include unistd.h and execute system()
            malicious_c_pkg = os.path.join(tmp_dir, "malicious_c.json")
            with open(malicious_c_pkg, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": "1.0",
                    "target_symbol": "mandelbrot_pixel",
                    "breeder": "@c_attacker",
                    "chromosome": {
                        "id": "evil_c_5678",
                        "generation": 1,
                        "parent_id": "gen0",
                        "source_type": "C_EXTENSION",
                        "entry_symbol": "mandelbrot_pixel",
                        "code": "# wrapper",
                        "mutation_meta": {
                            "c_code": "#include <unistd.h>\n#include <stdlib.h>\nint64_t mandelbrot_pixel() { system(\"whoami\"); return 0; }",
                        },
                    },
                }, f)

            success, chrom, speedup, msg = import_and_verify_genome_package(
                package_path=malicious_c_pkg,
                organism=organism,
            )
            assert success is False
            assert chrom is None
            assert "SECURITY_VIOLATION" in msg
            assert "unistd.h" in msg or "system" in msg
        finally:
            organism.close()


