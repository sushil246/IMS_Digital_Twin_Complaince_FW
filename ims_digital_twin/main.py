"""
IMS Network Digital Twin Demo — main entry point.

Usage:
    python -m ims_digital_twin.main [--scenario SCENARIO] [--list] [--model MODEL]

Examples:
    python -m ims_digital_twin.main --list
    python -m ims_digital_twin.main --scenario reg_storm
    python -m ims_digital_twin.main --scenario tls_cert_expiry
    python -m ims_digital_twin.main --scenario rtp_timeout
    python -m ims_digital_twin.main --scenario codec_mismatch
    python -m ims_digital_twin.main --scenario pcscf_down
    python -m ims_digital_twin.main --scenario srtp_dtls_fail
"""
import os
os.environ["PYTHONUTF8"] = "1"

import argparse
import asyncio
import sys

import litellm

from ims_digital_twin.scenarios.fault_scenarios import list_scenarios
from ims_digital_twin.agents.orchestrator import run_digital_twin_demo

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL      = "ollama_chat/gemma4:e4b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="IMS Network Digital Twin — Oracle SBC RCA Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scenario", "-s",
        default="reg_storm",
        help="Fault scenario key to inject (default: reg_storm)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available fault scenarios and exit",
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"LiteLLM model string (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama server URL (default: {DEFAULT_OLLAMA_URL})",
    )
    parser.add_argument(
        "--twin-only",
        action="store_true",
        help="Only inject fault and show twin state/logs — skip AI agents",
    )
    return parser.parse_args()


def cmd_list_scenarios() -> None:
    print("\nAvailable IMS Fault Scenarios:\n")
    print(f"  {'Key':<20} {'Name':<35} Description")
    print("  " + "-" * 90)
    for s in list_scenarios():
        print(f"  {s['key']:<20} {s['name']:<35} {s['description']}")
    print()


def cmd_twin_only(scenario_key: str) -> None:
    """Inject fault and display twin state without running AI agents."""
    from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
    from ims_digital_twin.scenarios.fault_scenarios import inject
    from ims_digital_twin.tools import twin_tools, log_tools
    import json

    print(f"\n[Twin-Only Mode] Injecting scenario: {scenario_key}")
    twin = NetworkStateTwin()
    twin_tools.register_twin(twin)
    twin, logs = inject(twin, scenario_key)
    log_tools.store_logs(logs)

    print(f"\nIncident ID : {twin.incident_id}")
    print(f"Fault       : {twin.injected_fault}")
    print("\n--- Digital Twin State ---")
    print(twin.to_json())
    print("\n--- Simulated SBC Logs ---")
    for line in logs:
        print(f"  {line}")
    print(f"\n--- Active Alarms ({len(twin.all_alarms())}) ---")
    for alarm in twin.all_alarms():
        print(f"  {alarm}")


def main() -> None:
    args = parse_args()

    if args.list:
        cmd_list_scenarios()
        sys.exit(0)

    if args.twin_only:
        cmd_twin_only(args.scenario)
        sys.exit(0)

    litellm.drop_params = True
    litellm.set_verbose = False

    asyncio.run(
        run_digital_twin_demo(
            scenario_key=args.scenario,
            ollama_url=args.ollama_url,
            model=args.model,
        )
    )


if __name__ == "__main__":
    main()
