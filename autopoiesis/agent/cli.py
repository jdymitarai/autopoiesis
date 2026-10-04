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

# Ensure .agents directory is in sys.path
_agents_dir = Path(__file__).resolve().parent.parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

try:
    from .metabolism import EventType, SessionEvent
    from .organism import AntigravityOrganism
except (ImportError, ValueError):
    from organism.metabolism import EventType, SessionEvent
    from organism.organism import AntigravityOrganism


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
        print(f"Applied: {result.mutations_applied}, Rejected: {result.mutations_rejected}\n")

    elif args.command == "rollback":
        ok = organism.rollback(args.generation)
        if ok:
            print(f"\nSuccessfully rolled back to Gen {organism.lineage.active_generation}\n")
        else:
            print("\nRollback failed. Check generation number and snapshots.\n")
            sys.exit(1)

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
                if res.mutations_applied > 0:
                    print(f"[{ts}] Heartbeat #{pulse_count}: Evolved! Gen {res.generation_before} -> {res.generation_after} (+{res.mutations_applied} applied)", flush=True)
                else:
                    print(f"[{ts}] Heartbeat #{pulse_count}: Homeostasis stable (Gen {organism.lineage.active_generation}, 0 pending mutations)", flush=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[Antigravity Organism] Heartbeat Daemon paused safely.\n", flush=True)


if __name__ == "__main__":
    main()
