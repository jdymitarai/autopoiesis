"""
Command Line Interface for Antigravity Living Organism.

Usage:
  python -m organism.cli status
  python -m organism.cli pulse
  python -m organism.cli lineage
  python -m organism.cli rollback [GEN]
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure appropriate search directories are in sys.path
_current_dir = Path(__file__).resolve().parent
_parent_dir = _current_dir.parent
for _p in [str(_current_dir), str(_parent_dir), str(_parent_dir.parent)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from .metabolism import EventType, SessionEvent
    from .organism import AntigravityOrganism
except (ImportError, ValueError):
    try:
        from organism.metabolism import EventType, SessionEvent
        from organism.organism import AntigravityOrganism
    except (ImportError, ValueError):
        from autopoiesis.agent.metabolism import EventType, SessionEvent
        from autopoiesis.agent.organism import AntigravityOrganism


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Living Organism CLI")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="Show organism health and telemetry")

    # lineage
    subparsers.add_parser("lineage", help="Display genealogical lineage tree")

    # pulse
    pulse_p = subparsers.add_parser("pulse", help="Trigger a metabolic heartbeat pulse")
    pulse_p.add_argument("--event-type", help="Optional event type to simulate", default=None)
    pulse_p.add_argument("--payload", help="JSON payload for the event", default=None)

    # rollback
    rb_p = subparsers.add_parser("rollback", help="Rollback to a previous generation")
    rb_p.add_argument("--generation", type=int, default=None, help="Target generation to restore")

    # daemon
    daemon_p = subparsers.add_parser("daemon", help="Run 24/7 autonomous heartbeat daemon")
    daemon_p.add_argument("--interval", type=int, default=300, help="Heartbeat interval in seconds (default: 300)")

    # forage
    forage_p = subparsers.add_parser("forage", help="Trigger autonomous external web foraging")
    forage_p.add_argument("--url", help="Target URL to forage directly", default=None)
    forage_p.add_argument("--title", help="Optional title for the target URL", default=None)

    # reflex
    reflex_p = subparsers.add_parser("reflex", help="Ternary Neural Reflex diagnostics and benchmarks")
    reflex_p.add_argument("--benchmark", action="store_true", help="Run reflex benchmark (latency, memory, accuracy)")
    reflex_p.add_argument("--classify", type=str, default=None, help="Classify text using the reflex neural kernel")

    # cortex
    cortex_p = subparsers.add_parser("cortex", help="Cerebral Neural Cortex (SmolLM2-135M) operations")
    cortex_p.add_argument("--status", action="store_true", help="Display neural cortex operational status")
    cortex_p.add_argument("--think", type=str, default=None, help="Generate cognitive thoughts from prompt")
    cortex_p.add_argument("--reflect", type=str, default=None, help="Reflect on an observation and generate mutation candidates")
    cortex_p.add_argument("--dream", action="store_true", help="Run dream simulation for counterfactual synthesis")
    cortex_p.add_argument("--max-tokens", type=int, default=128, help="Maximum tokens to generate (default: 128)")
    cortex_p.add_argument("--benchmark", action="store_true", help="Benchmark cortex inference throughput and latency")
    cortex_p.add_argument("--model-path", type=str, default=None, help="Path to local GGUF or model weights file")
    cortex_p.add_argument("--backend", type=str, default="auto", choices=["auto", "fallback_transformer", "transformers", "llama_cpp", "ctransformers"], help="Inference backend preference")
    cortex_p.add_argument("--stage", action="store_true", help="Stage generated reflection candidate into metabolism for next pulse")

    args = parser.parse_args()

    organism = AntigravityOrganism()

    if args.command == "status" or not args.command:
        telemetry = organism.get_telemetry()
        print("\n[Antigravity Organism Telemetry]")
        for k, v in telemetry.items():
            print(f"  {k:26}: {v}")
        print()

    elif args.command == "lineage":
        print("\n" + organism.render_lineage_ascii() + "\n")

    elif args.command == "pulse":
        events = None
        if args.event_type and args.payload:
            payload = json.loads(args.payload)
            events = [SessionEvent.create(event_type=args.event_type, payload=payload)]

        result = organism.pulse(events)
        print(f"\nPulse completed: {result.details}")
        print(f"Gen: {result.generation_before} -> {result.generation_after}")
        print(f"Applied: {result.mutations_applied}, Rejected: {result.mutations_rejected}")
        if result.foraged_count > 0:
            print(f"Foraged: {result.foraged_count} external nutrient(s)")
        print()

    elif args.command == "forage":
        if args.url:
            print(f"\n[Foraging] Scouting target URL: {args.url} ...")
            nutrient = organism.foraging.forage_url(args.url, title=args.title)
            if nutrient:
                print(f"  [+] Ingested Nutrient: {nutrient.title} (relevance: {nutrient.relevance_score}, tags: {nutrient.tags})")
                organism.metabolism.ingest_event(
                    SessionEvent.create(
                        event_type=EventType.FORAGED_NUTRIENT,
                        payload=nutrient.to_dict(),
                        source="cli_forage",
                    )
                )
                print("  [+] Enqueued for next metabolic pulse.\n")
            else:
                print("  [-] No nutrient extracted (relevance below threshold or duplicate).\n")
        else:
            print("\n[Foraging] Scouting active curated sources ...")
            nutrients = organism.foraging.forage_active_sources()
            print(f"  [+] Foraged {len(nutrients)} new nutrient(s).")
            for nut in nutrients:
                print(f"      * {nut.title} (relevance: {nut.relevance_score}, tags: {nut.tags})")
                organism.metabolism.ingest_event(
                    SessionEvent.create(
                        event_type=EventType.FORAGED_NUTRIENT,
                        payload=nut.to_dict(),
                        source="cli_forage",
                    )
                )
            print("  [+] All nutrients enqueued for next metabolic pulse.\n")

    elif args.command == "rollback":
        ok = organism.rollback(args.generation)
        if ok:
            print(f"\nSuccessfully rolled back to Gen {organism.lineage.active_generation}\n")
        else:
            print("\nRollback failed. Check generation number and snapshots.\n")
            sys.exit(1)

    elif args.command == "reflex":
        try:
            from .reflex import ReflexValidationHarness, TernaryReflexClassifier
        except (ImportError, ValueError):
            try:
                from organism.reflex import ReflexValidationHarness, TernaryReflexClassifier
            except ImportError:
                from autopoiesis.agent.reflex import ReflexValidationHarness, TernaryReflexClassifier

        clf = getattr(organism, "reflex", None) or TernaryReflexClassifier.create_calibrated()

        if args.benchmark or (not args.classify):
            harness = ReflexValidationHarness()
            results = harness.benchmark(clf)
            print("\n[Antigravity 1-Bit Ternary Reflex Kernel Benchmark]")
            print(f"  Architecture                 : {results['architecture']}")
            print(f"  Weights Count                : {results['weights_count']:,} discrete weights in {{-1, 0, +1}}")
            print(f"  Multiplication-Free Forward  : {results['multiplication_free']}")
            print(f"  Packed Memory Footprint      : {results['packed_memory_bytes']:,} bytes ({results['packed_memory_kb']} KB)")
            print(f"  Unpacked Memory Footprint    : {results['unpacked_memory_bytes']:,} bytes ({results['unpacked_memory_kb']} KB)")
            print(f"  Mean Inference Latency       : {results['mean_inference_latency_us']} us (microseconds)")
            print(f"  Relevance Accuracy           : {results['relevance_accuracy'] * 100:.2f}%")
            print(f"  Threat Detection Rate        : {results['threat_detection_rate'] * 100:.2f}%")
            print(f"  Threat False Positive Rate   : {results['threat_false_positive_rate'] * 100:.2f}%")
            print(f"  Overall Validation Accuracy  : {results['overall_accuracy'] * 100:.2f}%")
            print(f"  State Hash                   : {results['state_hash']}")
            print()

        if args.classify:
            rel, is_threat = clf.predict(args.classify)
            det = clf.predict_detailed(args.classify)
            print(f"\n[Reflex Prediction]")
            print(f"  Input Text                   : {args.classify[:80]}")
            print(f"  Relevance Score              : {rel}")
            print(f"  Is Threat Detected           : {is_threat}")
            print(f"  Threat Score                 : {det['threat_score']}")
            print()

    elif args.command == "cortex":
        cortex = getattr(organism, "cortex", None)
        if (
            cortex is None
            or args.model_path
            or (args.backend != "auto" and args.backend != getattr(cortex, "active_backend", ""))
        ):
            try:
                from .cortex import NeuralCortex
            except (ImportError, ValueError):
                try:
                    from organism.cortex import NeuralCortex
                except ImportError:
                    from autopoiesis.agent.cortex import NeuralCortex
            cortex = NeuralCortex(
                model_path=args.model_path,
                backend_preference=args.backend,
            )
            organism.cortex = cortex

        if args.think:
            print("\n[SmolLM2-135M Neural Cortex: Thinking]")
            print(f"  Prompt       : {args.think}")
            thought = cortex.think(args.think, max_tokens=args.max_tokens)
            print(f"  Thought      : {thought.text}")
            print(f"  Latency      : {thought.latency_ms:.2f} ms")
            print(f"  Tokens       : {thought.tokens_generated} tokens")
            print(f"  Throughput   : {thought.tokens_per_second:.1f} tok/s")
            print(f"  Backend      : {thought.backend} ({thought.model_id})\n")

        elif args.reflect:
            print("\n[SmolLM2-135M Neural Cortex: Reflection]")
            print(f"  Observation  : {args.reflect}")
            reflection = cortex.reflect(args.reflect)
            print(f"  Insight      : {reflection.insight}")
            if reflection.mutation_candidate:
                cand = reflection.mutation_candidate
                print(f"  Mutation     : {cand.get('title')}")
                print(f"  Target       : {cand.get('target_name')} ({cand.get('target_type')})")
                print(f"  Rationale    : {cand.get('rationale')}")
                if args.stage:
                    organism.metabolism.ingest_event(
                        SessionEvent.create(
                            event_type=EventType.CORTEX_REFLECTION,
                            payload=cand,
                            source="cli_cortex_reflect",
                        )
                    )
                    print("  [+] Enqueued cortex mutation candidate for next metabolic pulse.")
            if reflection.dream_simulation:
                print(f"  Dream Sim    : {reflection.dream_simulation}")
            print(f"  Latency      : {reflection.latency_ms:.2f} ms")
            print(f"  Confidence   : {reflection.confidence:.2f}\n")

        elif args.dream:
            print("\n[SmolLM2-135M Neural Cortex: Quiescent Dream Simulation]")
            thought = cortex.dream()
            print(f"  Simulation   : {thought.text}")
            print(f"  Latency      : {thought.latency_ms:.2f} ms")
            print(f"  Throughput   : {thought.tokens_per_second:.1f} tok/s\n")

        elif args.benchmark:
            print("\n[SmolLM2-135M Neural Cortex: Benchmark]")
            harness = cortex.benchmark(iterations=5)
            for k, v in harness.items():
                print(f"  {k:26}: {v}")
            print()

        else:
            status = cortex.get_status()
            print("\n[Antigravity Neural Cortex Status (SmolLM2-135M)]")
            for k, v in status.items():
                print(f"  {k:26}: {v}")
            print()

        # Persist cumulative cortex state across CLI runs
        if args.think or args.reflect or args.dream or args.benchmark:
            if hasattr(organism, "_save_cortex_state"):
                organism._save_cortex_state()

    elif args.command == "daemon":
        import time
        interval = max(10, args.interval)
        print(f"\n[Antigravity Organism] Autonomous Heartbeat Daemon started.", flush=True)
        print(f"Interval: every {interval}s | Active Gen: {organism.lineage.active_generation}", flush=True)
        print("Press Ctrl+C to safely pause the heartbeat daemon.\n", flush=True)
        try:
            pulse_count = 0
            while True:
                pulse_count += 1
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                res = organism.pulse()
                foraged_str = f", foraged: {res.foraged_count}" if res.foraged_count > 0 else ""
                if res.mutations_applied > 0:
                    print(f"[{ts}] Heartbeat #{pulse_count}: Evolved! Gen {res.generation_before} -> {res.generation_after} (+{res.mutations_applied} applied{foraged_str})", flush=True)
                else:
                    print(f"[{ts}] Heartbeat #{pulse_count}: Homeostasis stable (Gen {organism.lineage.active_generation}, 0 pending mutations{foraged_str})", flush=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Antigravity Organism] Heartbeat Daemon paused safely.\n", flush=True)


if __name__ == "__main__":
    main()
