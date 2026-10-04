"""
Autonomous Pull Request Evaluator and Auto-Breeder Bot.

Audits community-submitted genome packages in Pull Requests. Enforces:
1. Strict file scope: Only changes under genomes/ are allowed for auto-merge.
2. Static zero-trust security audit: Rejects system calls, network, filesystem ops.
3. Subprocess sandbox & Apoptotic Gate: Must pass 100% test vectors & latency reduction.
4. Auto-action: Rejects/closes failing PRs; approves and auto-merges passing PRs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autopoiesis.core.breeding import import_and_verify_genome_package
from autopoiesis.core.organism import LivingOrganism


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Runs a shell command and returns (returncode, stdout, stderr)."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def comment_on_pr(pr_number: int, body: str) -> None:
    """Posts a comment on the GitHub Pull Request."""
    cmd = ["gh", "pr", "comment", str(pr_number), "--body", body]
    rc, out, err = run_cmd(cmd)
    if rc != 0:
        print(f"[!] Warning: Failed to comment on PR #{pr_number}: {err}", file=sys.stderr)


def close_pr(pr_number: int, reason: str) -> None:
    """Closes a failing PR with an explanatory comment."""
    comment_body = (
        f"### 💀 Apoptotic Gate Rejection\n\n"
        f"This genome submission was automatically audited and **rejected** by the immune system.\n\n"
        f"**Reason**: {reason}\n\n"
        f"> *The Apoptotic Gate enforces zero tolerance for security breaches, logic regressions, "
        f"and performance slowdowns. You are welcome to optimize locally and submit a new chromosome.*"
    )
    comment_on_pr(pr_number, comment_body)
    run_cmd(["gh", "pr", "close", str(pr_number)])


def merge_pr(pr_number: int, breeder: str, workload: str, speedup: float, chrom_id: str) -> bool:
    """Approves and merges a verified PR into the species master tree."""
    comment_body = (
        f"### 🌱 Apoptotic Gate Certified & Spliced!\n\n"
        f"Congratulations **{breeder}**! Your submitted genome for `{workload}` has passed all verification gates:\n\n"
        f"- **Zero-Trust Security Audit**: ✅ Passed (Pure algorithmic computation)\n"
        f"- **Process Sandbox Isolation**: ✅ Passed (No crashes, leaks, or timeouts)\n"
        f"- **Semantic Mathematical Equivalence**: ✅ Passed (100% deterministic accuracy)\n"
        f"- **Empirical Hardware Speedup**: 🚀 **{speedup:.2f}x** vs baseline\n"
        f"- **Chromosome ID**: `{chrom_id}`\n\n"
        f"Your strain is now permanently merged into the species tree. "
        f"Welcome to the **[Hall of Breeders](https://github.com/jdymitarai/autopoiesis/blob/main/BREEDING.md#hall-of-breeders)**! 🧬🌍"
    )
    comment_on_pr(pr_number, comment_body)

    # Attempt direct squash merge
    rc, out, err = run_cmd(["gh", "pr", "merge", str(pr_number), "--squash", "--delete-branch"])
    if rc == 0:
        print(f"[+] Successfully merged PR #{pr_number} into main branch!")
        return True

    # Fallback to auto-merge if branch protection requires it
    rc, out, err = run_cmd(["gh", "pr", "merge", str(pr_number), "--squash", "--auto", "--delete-branch"])
    if rc == 0:
        print(f"[+] Successfully marked PR #{pr_number} for auto-merge upon check completion.")
        return True

    print(f"[!] Warning: Could not merge PR #{pr_number} automatically: {err}", file=sys.stderr)
    return False


def evaluate_pull_request(pr_number: int) -> int:
    """Main audit pipeline for a Pull Request."""
    print(f"[*] Starting Autonomous Audit for Pull Request #{pr_number}...")

    # 1. Fetch changed files
    rc, out, err = run_cmd(["gh", "pr", "view", str(pr_number), "--json", "files", "--jq", ".files[].path"])
    if rc != 0:
        print(f"[-] Error querying PR #{pr_number} files: {err}", file=sys.stderr)
        return 1

    changed_files = [line.strip() for line in out.splitlines() if line.strip()]
    print(f"[*] Changed files ({len(changed_files)}): {changed_files}")

    if not changed_files:
        print("[*] No files changed in PR. Skipping.")
        return 0

    # 2. Strict Scope Verification: ONLY genomes/ files are allowed for auto-merge
    non_genome_files = [f for f in changed_files if not f.startswith("genomes/")]
    if non_genome_files:
        warning_msg = (
            f"### ⚠️ Manual Maintainer Review Required\n\n"
            f"The **Auto-Breeder Bot** only auto-merges genome files placed under the `genomes/` directory.\n"
            f"This PR modifies the following core or config files:\n"
            + "\n".join(f"- `{f}`" for f in non_genome_files[:10])
            + "\n\nAuto-merge has been bypassed. A repository maintainer will review your changes manually."
        )
        print(f"[*] PR #{pr_number} modifies non-genome files. Flagged for manual review.")
        comment_on_pr(pr_number, warning_msg)
        return 0

    genome_files = [f for f in changed_files if f.startswith("genomes/") and f.endswith(".json")]
    if not genome_files:
        print("[*] No genome JSON packages found in PR. Skipping.")
        return 0

    # 3. Audit each genome package in the PR
    for genome_path in genome_files:
        print(f"\n[*] Evaluating genome package: {genome_path}")
        if not os.path.exists(genome_path):
            close_pr(pr_number, f"Genome file `{genome_path}` does not exist on disk.")
            return 1

        try:
            with open(genome_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as ex:
            close_pr(pr_number, f"Failed to parse JSON in `{genome_path}`: {ex}")
            return 1

        workload = data.get("workload", "mandelbrot").lower()
        breeder = data.get("breeder", "@contributor")

        if workload == "mandelbrot":
            import autopoiesis.workloads.mandelbrot as target_mod
            target_symbol = "mandelbrot_pixel"
            test_vectors = target_mod.generate_mandelbrot_test_vectors()
        elif workload == "nbody":
            import autopoiesis.workloads.nbody as target_mod
            target_symbol = "nbody_simulation_energy"
            test_vectors = target_mod.generate_nbody_test_vectors()
        else:
            close_pr(pr_number, f"Unknown computational workload: '{workload}'.")
            return 1

        organism = LivingOrganism(
            name=f"ci_{workload}_organism",
            target_module=target_mod,
            target_symbol=target_symbol,
            test_vectors=test_vectors,
            render_dashboard=False,
        )

        try:
            success, candidate, speedup, msg = import_and_verify_genome_package(
                package_path=genome_path,
                organism=organism,
                min_speedup_per_step=1.0,
            )
        finally:
            organism.close()

        if not success:
            print(f"[-] Genome rejected: {msg}")
            close_pr(pr_number, msg)
            return 1

        print(f"[+] Genome verified! Breeder: {breeder}, Speedup: {speedup:.2f}x, ID: {candidate.id}")
        merge_pr(
            pr_number=pr_number,
            breeder=breeder,
            workload=workload,
            speedup=speedup,
            chrom_id=candidate.id,
        )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Autopoiesis PR Auto-Breeder")
    parser.add_argument("--pr", "-p", type=int, required=True, help="Pull request number to evaluate")
    args = parser.parse_args()

    sys.exit(evaluate_pull_request(args.pr))


if __name__ == "__main__":
    main()
