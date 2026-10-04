"""
Standard Model Context Protocol (MCP) Server for Autopoiesis.

Enables any AI Agent (Antigravity, Cursor, Claude Code, Windsurf, Cline, etc.)
to autonomously invoke Autopoiesis tools via standard stdio JSON-RPC 2.0.
Requires zero external dependencies.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from autopoiesis import __version__
from autopoiesis.core.breeding import export_genome_package, import_and_verify_genome_package
from autopoiesis.core.chromosome import Chromosome
from autopoiesis.core.organism import LivingOrganism
from autopoiesis.core.security import audit_chromosome_security


TOOLS_METADATA = [
    {
        "name": "autopoiesis_evolve",
        "description": "Autonomously optimizes computational workloads (Python AST -> C99 -> Rust cdylib) with apoptotic immunity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workload": {
                    "type": "string",
                    "enum": ["mandelbrot", "nbody"],
                    "description": "Target computational workload to evolve.",
                    "default": "mandelbrot",
                },
                "generations": {
                    "type": "integer",
                    "description": "Number of evolutionary generations to attempt (default: 3).",
                    "default": 3,
                },
            },
            "required": ["workload"],
        },
    },
    {
        "name": "autopoiesis_export_genome",
        "description": "Exports a locally-evolved champion chromosome into a portable JSON package for community PR submission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workload": {
                    "type": "string",
                    "enum": ["mandelbrot", "nbody"],
                    "description": "Workload of the chromosome to export.",
                },
                "breeder": {
                    "type": "string",
                    "description": "Your GitHub username or breeder handle (e.g. '@alice').",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path to save the genome package JSON.",
                },
                "generations_to_evolve": {
                    "type": "integer",
                    "description": "Pre-evolve for N generations before exporting (default: 2).",
                    "default": 2,
                },
                "notes": {
                    "type": "string",
                    "description": "Hardware/compiler notes.",
                },
            },
            "required": ["workload", "breeder", "output_path"],
        },
    },
    {
        "name": "autopoiesis_import_genome",
        "description": "Imports, audits, and verifies an external genome package through the local Apoptotic Gate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the genome package JSON file.",
                },
                "min_speedup": {
                    "type": "number",
                    "description": "Minimum speedup multiplier required to adopt (default: 1.0).",
                    "default": 1.0,
                },
            },
            "required": ["package_path"],
        },
    },
    {
        "name": "autopoiesis_security_audit",
        "description": "Performs static zero-trust security audit on a genome package without compiling or executing it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {
                    "type": "string",
                    "description": "Path to the genome package JSON to audit.",
                },
            },
            "required": ["package_path"],
        },
    },
]


def _get_workload_organism(workload_name: str) -> LivingOrganism:
    name = workload_name.lower()
    if name == "mandelbrot":
        import autopoiesis.workloads.mandelbrot as target_mod
        target_symbol = "mandelbrot_pixel"
        test_vectors = target_mod.generate_mandelbrot_test_vectors()
    elif name == "nbody":
        import autopoiesis.workloads.nbody as target_mod
        target_symbol = "nbody_simulation_energy"
        test_vectors = target_mod.generate_nbody_test_vectors()
    else:
        raise ValueError(f"Unknown workload: {workload_name}. Supported: mandelbrot, nbody")

    return LivingOrganism(
        name=f"mcp_{name}_organism",
        target_module=target_mod,
        target_symbol=target_symbol,
        test_vectors=test_vectors,
        render_dashboard=False,
    )


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    if tool_name == "autopoiesis_evolve":
        workload = arguments.get("workload", "mandelbrot")
        generations = int(arguments.get("generations", 3))

        organism = _get_workload_organism(workload)
        try:
            evolved = organism.run_evolution(max_generations=generations)
            active = organism.active_chromosome
            tree = organism.lineage_dag.render_ascii_tree()

            return (
                f"=== Autopoiesis Evolution Complete ===\n"
                f"Workload: {workload}\n"
                f"Generations Evolved: {len(evolved)}\n"
                f"Active Generation: Gen {organism.current_generation}\n"
                f"Active Phenotype: {active.source_type.value}\n"
                f"Final Speedup: {active.fitness:.2f}x vs Gen 0 baseline\n"
                f"Mean Latency: {active.mean_latency_ns / 1_000_000:.4f} ms\n"
                f"Compiled Dynamic Library: {active.compiled_artifact_path or 'In-Memory AST'}\n\n"
                f"{tree}"
            )
        finally:
            organism.close()

    elif tool_name == "autopoiesis_export_genome":
        workload = arguments["workload"]
        breeder = arguments["breeder"]
        output_path = arguments["output_path"]
        evolve_first = int(arguments.get("generations_to_evolve", 2))
        notes = arguments.get("notes")

        organism = _get_workload_organism(workload)
        try:
            if evolve_first > 0:
                organism.run_evolution(max_generations=evolve_first)

            pkg = export_genome_package(
                organism=organism,
                breeder_handle=breeder,
                output_path=output_path,
                notes=notes,
            )
            return (
                f"Successfully exported breeding genome to: {output_path}\n"
                f"Breeder: {pkg['breeder']}\n"
                f"Workload: {pkg['workload']}\n"
                f"Phenotype Type: {pkg['source_type']}\n"
                f"Measured Speedup: {pkg['active_speedup']:.2f}x\n"
                f"Chromosome ID: {pkg['chromosome']['id']}\n"
                f"Host Telemetry: {pkg['host_telemetry']['platform']} ({pkg['host_telemetry']['machine']})"
            )
        finally:
            organism.close()

    elif tool_name == "autopoiesis_import_genome":
        package_path = arguments["package_path"]
        min_speedup = float(arguments.get("min_speedup", 1.0))

        if not os.path.exists(package_path):
            return f"Error: Genome package not found at '{package_path}'"

        with open(package_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        workload = data.get("workload", "mandelbrot")
        organism = _get_workload_organism(workload)
        try:
            success, candidate, speedup, msg = import_and_verify_genome_package(
                package_path=package_path,
                organism=organism,
                min_speedup_per_step=min_speedup,
            )
            if success:
                return (
                    f"=== Apoptotic Gate Certification: APPROVED ===\n"
                    f"{msg}\n"
                    f"New Active Generation: Gen {organism.current_generation}\n"
                    f"Spliced into Lineage DAG: ID {candidate.id}"
                )
            else:
                return f"=== Apoptotic Gate Certification: REJECTED ===\n{msg}"
        finally:
            organism.close()

    elif tool_name == "autopoiesis_security_audit":
        package_path = arguments["package_path"]
        if not os.path.exists(package_path):
            return f"Error: File not found at '{package_path}'"

        with open(package_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chrom_data = data.get("chromosome", {})
        candidate = Chromosome.from_dict(chrom_data)

        is_secure, violations = audit_chromosome_security(candidate)
        if is_secure:
            return (
                f"=== Zero-Trust Security Audit: PASSED ===\n"
                f"Chromosome ID: {candidate.id}\n"
                f"Source Type: {candidate.source_type.value}\n"
                f"Status: Safe (No disallowed system calls, network, or filesystem operations detected)."
            )
        else:
            return (
                f"=== Zero-Trust Security Audit: VIOLATION DETECTED ===\n"
                f"Chromosome ID: {candidate.id}\n"
                f"Violations:\n" + "\n".join(f"- {v}" for v in violations)
            )

    raise ValueError(f"Unknown tool: {tool_name}")


def run_mcp_server() -> None:
    """Standard stdio JSON-RPC 2.0 loop."""
    # Ensure stdout is in line-buffered mode and utf-8
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    reader = sys.stdin.buffer
    writer = sys.stdout.buffer

    while True:
        try:
            line = reader.readline()
            if not line:
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            # Handle Content-Length header if present in HTTP-style framing
            if line_str.startswith("Content-Length:"):
                length = int(line_str.split(":", 1)[1].strip())
                # Read empty line
                reader.readline()
                content = reader.read(length).decode("utf-8")
                req = json.loads(content)
            else:
                req = json.loads(line_str)

            msg_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": "autopoiesis-mcp-server",
                            "version": __version__,
                        },
                    },
                }
            elif method in ("notifications/initialized", "initialized"):
                continue  # No response needed for notifications
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": TOOLS_METADATA,
                    },
                }
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("arguments", {})
                try:
                    result_text = handle_tool_call(name, args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text,
                                }
                            ],
                            "isError": False,
                        },
                    }
                except Exception as ex:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error executing {name}: {str(ex)}\n{traceback.format_exc()}",
                                }
                            ],
                            "isError": True,
                        },
                    }
            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            out_bytes = json.dumps(resp).encode("utf-8") + b"\n"
            writer.write(out_bytes)
            writer.flush()

        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            }
            writer.write(json.dumps(err_resp).encode("utf-8") + b"\n")
            writer.flush()


if __name__ == "__main__":
    run_mcp_server()
