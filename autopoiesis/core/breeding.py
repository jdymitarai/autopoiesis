"""
Distributed breeding protocol for Autopoiesis.

Allows developers across the globe to export locally-evolved chromosomes,
share them, and import/verify foreign chromosomes through the Apoptotic Gate.
"""

from __future__ import annotations

import json
import os
import platform
import time
from typing import Any, Dict, Optional, Tuple

from autopoiesis.core.apoptosis import ApoptoticGate
from autopoiesis.core.chromosome import Chromosome, LineageDAG, SourceType
from autopoiesis.core.hotswap import AtomicHotSwapper
from autopoiesis.core.organism import LivingOrganism


def export_genome_package(
    organism: LivingOrganism,
    breeder_handle: str,
    output_path: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Exports the organism's active chromosome as a verified breeding package."""
    active = organism.active_chromosome
    mod_name = organism.target_module.__name__.split(".")[-1]

    package = {
        "schema_version": "1.0",
        "organism_name": organism.name,
        "workload": mod_name,
        "target_symbol": organism.target_symbol,
        "breeder": breeder_handle.strip(),
        "notes": notes or "Evolved via distributed autopoiesis node",
        "generation": organism.current_generation,
        "active_speedup": active.fitness,
        "source_type": active.source_type.value,
        "mean_latency_ns": active.mean_latency_ns,
        "chromosome": active.to_dict(),
        "exported_at": time.time(),
        "host_telemetry": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
    }

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2)

    return package


def _ensure_compiled_artifact(candidate: Chromosome, artifacts_dir: Optional[str]) -> bool:
    """Ensures native dynamic library exists locally, compiling from mutation_meta source if needed."""
    if candidate.source_type == SourceType.PYTHON_AST:
        return True

    if candidate.compiled_artifact_path and os.path.exists(candidate.compiled_artifact_path):
        return True

    import shutil
    import subprocess

    target_dir = artifacts_dir or os.getcwd()
    os.makedirs(target_dir, exist_ok=True)
    is_windows = platform.system() == "Windows"
    ext = ".dll" if is_windows else (".dylib" if platform.system() == "Darwin" else ".so")

    if candidate.source_type == SourceType.C_EXTENSION:
        c_code = candidate.mutation_meta.get("c_code")
        if not c_code:
            return False
        compiler = shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            return False
        c_path = os.path.join(target_dir, f"libc_{candidate.entry_symbol}_{candidate.id}.c")
        lib_path = os.path.join(target_dir, f"libc_{candidate.entry_symbol}_{candidate.id}{ext}")
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(c_code)
        compile_cmd = [compiler, "-O3", "-shared"]
        if is_windows:
            compile_cmd.extend(["-fPIC", "-o", lib_path, c_path])
        else:
            compile_cmd.extend(["-fPIC", "-o", lib_path, c_path, "-lm"])
        res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and os.path.exists(lib_path):
            candidate.compiled_artifact_path = lib_path
            return True
        return False

    elif candidate.source_type == SourceType.RUST_CDYLIB:
        rust_code = candidate.mutation_meta.get("rust_code")
        if not rust_code:
            return False
        if not shutil.which("rustc"):
            return False
        rs_path = os.path.join(target_dir, f"rust_{candidate.entry_symbol}_{candidate.id}.rs")
        lib_prefix = "" if is_windows else "lib"
        lib_path = os.path.join(target_dir, f"{lib_prefix}rust_{candidate.entry_symbol}_{candidate.id}{ext}")
        with open(rs_path, "w", encoding="utf-8") as f:
            f.write(rust_code)
        compile_cmd = ["rustc", "--crate-type", "cdylib", "-C", "opt-level=3", "-o", lib_path, rs_path]
        res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and os.path.exists(lib_path):
            candidate.compiled_artifact_path = lib_path
            return True
        return False

    return False


def import_and_verify_genome_package(
    package_path: str,
    organism: LivingOrganism,
    min_speedup_per_step: float = 1.0,
) -> Tuple[bool, Optional[Chromosome], float, str]:
    """Imports an external genome, verifies it through the Apoptotic Gate, and splices it into the lineage DAG."""
    if not os.path.exists(package_path):
        return False, None, 0.0, f"File not found: {package_path}"

    with open(package_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("schema_version") != "1.0":
        return False, None, 0.0, f"Unsupported schema version: {data.get('schema_version')}"

    if data.get("target_symbol") != organism.target_symbol:
        return (
            False,
            None,
            0.0,
            f"Symbol mismatch: package targets '{data.get('target_symbol')}', but organism targets '{organism.target_symbol}'",
        )

    chrom_data = data.get("chromosome", {})
    breeder = data.get("breeder", "anonymous_breeder")

    # Reconstruct candidate chromosome
    candidate = Chromosome.from_dict(chrom_data)
    candidate.mutation_meta["breeder"] = breeder
    candidate.mutation_meta["imported_from"] = package_path

    # Phase 0: Static Zero-Trust Security Audit
    from autopoiesis.core.security import audit_chromosome_security
    is_secure, violations = audit_chromosome_security(candidate)
    if not is_secure:
        violation_details = "; ".join(violations)
        rejection_msg = f"SECURITY_VIOLATION: Candidate from {breeder} rejected: {violation_details}"
        return False, None, 0.0, rejection_msg

    # Ensure native artifact exists locally or is recompiled
    if not _ensure_compiled_artifact(candidate, organism.artifacts_dir):
        return (
            False,
            None,
            0.0,
            f"Failed to find or recompile native binary artifact for candidate {candidate.id}",
        )

    # Evaluate candidate through the local Apoptotic Gate
    baseline_fn = getattr(organism.target_module, organism.target_symbol)
    gate = ApoptoticGate(min_speedup_threshold=min_speedup_per_step)

    verdict = gate.verify_candidate(
        baseline_fn=baseline_fn,
        candidate=candidate,
        test_inputs=organism.test_vectors,
        min_speedup=min_speedup_per_step,
    )

    if not verdict.approved:
        rejection_msg = f"Apoptotic Gate rejected candidate from {breeder}: {verdict.rejection_reason}"
        return False, None, 0.0, rejection_msg

    # Adopt verified chromosome into organism lineage
    candidate.fitness = verdict.speedup
    candidate.mean_latency_ns = verdict.candidate_latency_ns
    candidate.parent_id = organism.active_chromosome.id
    candidate.generation = organism.current_generation + 1

    organism.lineage_dag.add_chromosome(candidate, set_active=True)
    organism.current_generation = candidate.generation

    # Atomic hot-swap in-memory
    organism.hot_swapper.hot_swap(
        target_module=organism.target_module,
        symbol_name=organism.target_symbol,
        chromosome=candidate,
    )

    # Record telemetry
    active_ancestors = organism.lineage_dag.get_ancestors(candidate.id)
    base_lat = active_ancestors[0].mean_latency_ns if active_ancestors else candidate.mean_latency_ns
    cumulative_speedup = (base_lat / candidate.mean_latency_ns) if (candidate.mean_latency_ns > 0 and base_lat > 0) else 1.0

    organism.telemetry.record_generation(
        generation=candidate.generation,
        chromosome_id=candidate.id,
        source_type=candidate.source_type.value,
        mutator_name=f"IMPORTED_{breeder}",
        latency_ns=candidate.mean_latency_ns,
        speedup=cumulative_speedup,
    )

    success_msg = (
        f"Certified and spliced genome from {breeder}! "
        f"Type: {candidate.source_type.value}, Measured Speedup: {verdict.speedup:.2f}x"
    )
    return True, candidate, verdict.speedup, success_msg
