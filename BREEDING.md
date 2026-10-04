# 🌱 Global Distributed Breeding Protocol

> *"Everyone is a Breeder: Evolve computational workloads locally, certify them through the Apoptotic Gate, and merge your genetic strains into the global species tree."*

---

## 🧬 Overview

**Autopoiesis** introduces a decentralized paradigm for software optimization: **Distributed Algorithmic Breeding**. 

Instead of relying on a centralized supercomputer to optimize code, developers worldwide run evolutionary cycles on their local machines (Mac, Linux, Windows, Colab). When your machine discovers a high-fitness chromosome (e.g. via AST unrolling, C transpilation, or Rust `cdylib` vectorization), you can **export your certified genome** and submit it to the repository.

Every submitted genome must pass the **Apoptotic Gate** — an automated, sandboxed immune system that verifies strict mathematical equivalence and statistical speedup. Genomes that pass are permanently spliced into the master **Lineage DAG**, crediting you in the species tree forever.

```
       [ Generation 0: Pure Python Baseline ]
                         │
     ┌───────────────────┴───────────────────┐
     ▼                                       ▼
[ Local Node: Breeder Alice ]           [ Local Node: Breeder Bob ]
(Mac M3 / Clang -O3)                    (Linux x86_64 / Rustc AVX-512)
     │                                       │
     ▼                                       ▼
`export-genome`                         `export-genome`
     │                                       │
     └───────────────────┬───────────────────┘
                         ▼
             [ GitHub Pull Request ]
                         │
                         ▼
              [ 🛡️ Apoptotic Gate ]
         (Sandboxed Semantic Verification)
                         │
                         ▼
        [ Splice into Master Lineage DAG ]
```

---

## 🚀 How to Breed & Contribute in 4 Steps

### 1. Clone & Setup Environment

```bash
git clone https://github.com/jdymitarai/autopoiesis.git
cd autopoiesis
pip install -e .
```

Ensure you have a C compiler (`gcc` or `clang`) and/or `rustc` installed on your machine for native transmutations:
- **macOS**: `xcode-select --install`
- **Ubuntu/Debian**: `sudo apt install build-essential rustc`
- **Windows**: Install Visual Studio Build Tools or MinGW + Rustup

---

### 2. Evolve Locally

Run local evolution on one of the target workloads (e.g., `mandelbrot` or `nbody`):

```bash
# Evolve Mandelbrot for 5 generations with real-time terminal dashboard
autopoiesis evolve --workload mandelbrot --generations 5

# Or run N-Body celestial mechanics evolution
autopoiesis evolve --workload nbody --generations 5
```

The engine will profile hot loops, synthesize mutations across AST, C, and Rust mutators, test them in isolated process sandboxes, and hot-swap viable mutations into memory.

---

### 3. Export Your Certified Genome

Once your local organism has reached a high-fitness generation, export your active chromosome:

```bash
autopoiesis export-genome \
  --workload mandelbrot \
  --breeder "@your_github_handle" \
  --evolve-first 3 \
  --output "genomes/mandelbrot_@your_handle.json" \
  --notes "Evolved on AMD Ryzen 9 7950X, Rustc 1.80 with native AVX2"
```

This exports a self-contained breeding package containing:
- Chromosome code (AST or native C/Rust source)
- Entry point signatures and type contracts
- Hardware and compiler telemetry
- Cryptographic hash ID and generational lineage

---

### 4. Verify & Submit Pull Request

You can verify that your exported package imports cleanly into a fresh Gen 0 organism:

```bash
autopoiesis import-genome \
  --workload mandelbrot \
  --input "genomes/mandelbrot_@your_handle.json"
```

If the Apoptotic Gate outputs:
```
[+] Certified and spliced genome from @your_github_handle!
[*] Spliced into lineage DAG: Active generation is now Gen 1
```

Commit your genome JSON under the `genomes/` directory and open a Pull Request:

```bash
git checkout -b breed-mandelbrot-@your_handle
git add genomes/
git commit -m "breed: contribute @your_handle mandelbrot genome"
git push origin breed-mandelbrot-@your_handle
```

> 🤖 **Autonomous 24/7 Auto-Breeder Bot Active**:
> As soon as your Pull Request is opened, our cloud **Auto-Breeder Bot** triggers automatically:
> 1. It audits your chromosome against the Zero-Trust Security Policy (Phase 0).
> 2. It tests your candidate inside the Isolated Subprocess Sandbox across edge vectors (Phase 1).
> 3. It measures latency reduction on hardware timers through the Apoptotic Gate (Phase 2).
> 
> If your genome is certified, the bot will post a verification report and **automatically merge your PR into `main` without waiting for manual maintainer approval**! Your name is instantly immortalized in the species tree.

---

## 🛡️ Apoptotic Immunity: Zero Contamination Guarantee

How do we prevent malicious code, memory leaks, or performance regressions from entering the codebase?

1. **Deterministic Semantic Test Vectors**: Every foreign genome is executed inside an `IsolatedProcessSandbox` across randomized fuzzing vectors and ground-truth edge cases. Any deviation greater than `1e-6` triggers instant apoptosis (rejection).
2. **Process Quarantine**: Foreign code executes in a separate subprocess. If an imported genome causes a `SIGSEGV`, infinite loop, or out-of-memory error, the parent process remains unharmed and logs the rejection verdict.
3. **Empirical Timer Verification**: The Apoptotic Gate benchmarks the candidate against the baseline function using monotonic nanosecond hardware timers. If the candidate does not beat the baseline, it is rejected.

---

## 🏆 Hall of Breeders

All merged genomes have their metadata permanently inscribed in the species `LineageDAG`:

| Generation | Workload | Source Type | Speedup | Breeder | Notes |
|:---:|:---:|:---:|:---:|:---:|:---|
| Gen 0 | Mandelbrot | `PYTHON_AST` | 1.00x | `@core` | Baseline Phenotype |
| Gen 1 | Mandelbrot | `C_EXTENSION` | 7.73x | `@core` | Hoisted pointer arithmetic |
| Gen 2 | Mandelbrot | `RUST_CDYLIB` | 7.97x | Community | Native loop vectorization |
| Gen 1 | N-Body | `C_EXTENSION` | 13.78x | `@core` | Hoisted gravitational force cache |

Join the experiment and help evolve the fastest computational species on Earth! 🌍🧬
