"""
IMS Digital Twin — Security Certification & Compliance Auditor
Interactive CLI and web dashboard entry point.

Usage (CLI):
    python -m ims_digital_twin_security_certification_compliances.main --list-scenarios
    python -m ims_digital_twin_security_certification_compliances.main \\
        --scenario pii_sip_header_leak --frameworks uk_tsa oecd_ai
    python -m ims_digital_twin_security_certification_compliances.main \\
        --scenario unlogged_ai_routing --frameworks eu_ai_act iso_42001 nist_ai_rmf \\
        --all-frameworks

Usage (Web):
    python -m ims_digital_twin_security_certification_compliances.main --web
    # Open http://localhost:8001
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys

os.environ["PYTHONUTF8"] = "1"

import litellm

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL      = "ollama_chat/gemma4:e4b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="IMS Digital Twin — Security Certification & Compliance Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── list ─────────────────────────────────────────────────────────────────
    list_p = subparsers.add_parser("list", help="List scenarios and frameworks")
    list_p.add_argument("--scenarios", action="store_true", help="List fault scenarios")
    list_p.add_argument("--frameworks", action="store_true", help="List compliance frameworks")

    # ── audit ─────────────────────────────────────────────────────────────────
    audit_p = subparsers.add_parser("audit", help="Run compliance audit pipeline")
    audit_p.add_argument("--scenario", "-s", required=True,
                         help="Compliance fault scenario key")
    audit_p.add_argument("--frameworks", "-f", nargs="+",
                         help="Framework keys to audit against")
    audit_p.add_argument("--all-frameworks", action="store_true",
                         help="Audit against all 6 frameworks")
    audit_p.add_argument("--no-ai", action="store_true",
                         help="Skip AI remediation (evaluation only)")
    audit_p.add_argument("--max-remediations", type=int, default=3,
                         help="Max AI remediations to generate (default: 3)")
    audit_p.add_argument("--model", "-m", default=DEFAULT_MODEL)
    audit_p.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)

    # ── certify ───────────────────────────────────────────────────────────────
    cert_p = subparsers.add_parser(
        "certify",
        help="Run multi-agent certification (one ADK agent per framework)",
    )
    cert_p.add_argument("--scenario", "-s", required=True,
                        help="Compliance fault scenario key")
    cert_p.add_argument("--frameworks", "-f", nargs="+",
                        help="Framework keys (default: scenario-relevant)")
    cert_p.add_argument("--all-frameworks", action="store_true",
                        help="Run all 6 framework agents")
    cert_p.add_argument("--parallel", action="store_true",
                        help="Run framework agents in parallel (faster, less verbose)")
    cert_p.add_argument("--model", "-m", default=DEFAULT_MODEL)
    cert_p.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)

    # ── web ───────────────────────────────────────────────────────────────────
    web_p = subparsers.add_parser("web", help="Launch compliance dashboard web server")
    web_p.add_argument("--port", type=int, default=8001)
    web_p.add_argument("--host", default="0.0.0.0")

    # Legacy flat args (backwards compat)
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--list-frameworks", action="store_true")
    parser.add_argument("--scenario", "-s", default=None)
    parser.add_argument("--frameworks", "-f", nargs="+")
    parser.add_argument("--all-frameworks", action="store_true")
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--max-remediations", type=int, default=3)
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--web", action="store_true", help="Launch web dashboard")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="0.0.0.0")

    return parser.parse_args()


def cmd_list_scenarios() -> None:
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        COMPLIANCE_SCENARIOS,
    )
    print("\n  Available Compliance Fault Scenarios\n")
    print(f"  {'Key':<30} {'Name':<35} Frameworks")
    print("  " + "─" * 90)
    for k, v in COMPLIANCE_SCENARIOS.items():
        fw = ", ".join(v["frameworks"])
        print(f"  {k:<30} {v['name']:<35} {fw}")
    print()


def cmd_list_frameworks() -> None:
    from ims_digital_twin_security_certification_compliances.compliance.matrix import (
        FRAMEWORK_REGISTRY,
    )
    print("\n  Available Compliance Frameworks\n")
    print(f"  {'Key':<15} {'Name':<12} {'Jurisdiction':<20} Controls")
    print("  " + "─" * 75)
    for k, fw in FRAMEWORK_REGISTRY.items():
        print(f"  {k:<15} {fw.name:<12} {fw.jurisdiction:<20} {len(fw.controls)}")
    print()


def cmd_audit(
    scenario: str,
    framework_keys: list,
    no_ai: bool,
    max_remediations: int,
    model: str,
    ollama_url: str,
) -> None:
    from ims_digital_twin_security_certification_compliances.pipeline.audit_pipeline import (
        ComplianceAuditPipeline,
    )
    litellm.drop_params = True
    litellm.set_verbose = False

    pipeline = ComplianceAuditPipeline(
        ollama_url=ollama_url,
        model=model,
        thinking_mode=True,
        max_remediations=max_remediations,
    )
    state = pipeline.run(
        framework_keys=framework_keys,
        scenario_key=scenario,
        ai_remediation=not no_ai,
    )

    if state.final_report_path:
        print(f"  Full report: {state.final_report_path}")


def cmd_certify(
    scenario: str,
    framework_keys: list,
    parallel: bool,
    model: str,
    ollama_url: str,
) -> None:
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        inject_compliance_fault,
    )
    from ims_digital_twin_security_certification_compliances.compliance.evaluator import (
        ComplianceEvaluator,
    )
    from ims_digital_twin_security_certification_compliances.agents.orchestrator import (
        CertificationOrchestrator,
    )
    litellm.drop_params = True
    litellm.set_verbose = False

    print(f"\n  Injecting fault scenario: {scenario}")
    logs, sip_trace, cfg_issue = inject_compliance_fault(scenario)

    print(f"  Evaluating against: {', '.join(framework_keys)}")
    evaluator = ComplianceEvaluator()
    report = evaluator.evaluate(twin=None, logs=logs, framework_keys=framework_keys)

    # Build structured finding dicts for orchestrator prompts
    findings = [
        {
            "framework": f.framework_key,
            "control_id": f.control_id,
            "control_name": f.control_id,
            "status": f.status.value,
            "severity": f.severity.value,
        }
        for f in report.findings
    ]

    orchestrator = CertificationOrchestrator(ollama_url=ollama_url, model=model)
    orch_report = orchestrator.run(
        framework_keys=framework_keys,
        scenario_key=scenario,
        logs=logs,
        sip_trace=sip_trace,
        kamailio_cfg_issue=cfg_issue,
        findings=findings,
        parallel=parallel,
    )
    print("\n" + orch_report.combined_summary)


def cmd_web(host: str, port: int) -> None:
    import uvicorn
    print(f"\n  IMS Digital Twin — Security Certification & Compliance Dashboard")
    print(f"  Open: http://{host if host != '0.0.0.0' else 'localhost'}:{port}\n")
    uvicorn.run(
        "ims_digital_twin_security_certification_compliances.web_server:app",
        host=host, port=port, reload=False, log_level="warning",
    )


def _resolve_frameworks(args) -> list:
    from ims_digital_twin_security_certification_compliances.compliance.matrix import (
        FRAMEWORK_REGISTRY,
    )
    if getattr(args, 'all_frameworks', False):
        return list(FRAMEWORK_REGISTRY.keys())
    if getattr(args, 'frameworks', None):
        return args.frameworks
    # Default to scenario-relevant frameworks
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        COMPLIANCE_SCENARIOS,
    )
    scenario = getattr(args, 'scenario', None)
    if scenario and scenario in COMPLIANCE_SCENARIOS:
        return COMPLIANCE_SCENARIOS[scenario]["frameworks"]
    return ["uk_tsa", "eu_ai_act"]


def main() -> None:
    args = parse_args()

    # List commands
    if getattr(args, 'list_scenarios', False):
        cmd_list_scenarios()
        sys.exit(0)
    if getattr(args, 'list_frameworks', False):
        cmd_list_frameworks()
        sys.exit(0)

    # Web server
    if getattr(args, 'web', False):
        cmd_web(args.host, args.port)
        return

    # Multi-agent certification (subcommand or --certify flag)
    if getattr(args, 'command', None) == 'certify':
        framework_keys = _resolve_frameworks(args)
        cmd_certify(
            scenario=args.scenario,
            framework_keys=framework_keys,
            parallel=getattr(args, 'parallel', False),
            model=getattr(args, 'model', DEFAULT_MODEL),
            ollama_url=getattr(args, 'ollama_url', DEFAULT_OLLAMA_URL),
        )
        return

    # Audit
    if getattr(args, 'scenario', None):
        framework_keys = _resolve_frameworks(args)
        cmd_audit(
            scenario=args.scenario,
            framework_keys=framework_keys,
            no_ai=getattr(args, 'no_ai', False),
            max_remediations=getattr(args, 'max_remediations', 3),
            model=getattr(args, 'model', DEFAULT_MODEL),
            ollama_url=getattr(args, 'ollama_url', DEFAULT_OLLAMA_URL),
        )
        return

    # Interactive mode
    _interactive()


def _interactive() -> None:
    """Rich interactive CLI menu."""
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        COMPLIANCE_SCENARIOS,
    )
    from ims_digital_twin_security_certification_compliances.compliance.matrix import (
        FRAMEWORK_REGISTRY,
    )

    print("\n" + "=" * 68)
    print("  IMS Digital Twin — Security Certification & Compliance Auditor")
    print("  Powered by Google ADK + Gemma 4:e4b (Thinking Mode)")
    print("=" * 68)

    # Framework selection
    print("\n  Available Frameworks:")
    for i, (k, fw) in enumerate(FRAMEWORK_REGISTRY.items(), 1):
        print(f"    [{i}] {fw.icon} {fw.name:<12} {fw.full_name}")
    fw_input = input("\n  Select frameworks (space-separated numbers, or 'all'): ").strip()
    fw_list = list(FRAMEWORK_REGISTRY.keys())
    if fw_input.lower() == "all":
        selected_frameworks = fw_list
    else:
        try:
            indices = [int(x)-1 for x in fw_input.split()]
            selected_frameworks = [fw_list[i] for i in indices if 0 <= i < len(fw_list)]
        except ValueError:
            selected_frameworks = ["uk_tsa", "eu_ai_act"]
    print(f"  Selected: {', '.join(selected_frameworks)}")

    # Scenario selection
    print("\n  Available Fault Scenarios:")
    scenario_list = list(COMPLIANCE_SCENARIOS.items())
    for i, (k, v) in enumerate(scenario_list, 1):
        print(f"    [{i}] {v['name']}")
        print(f"        {v['description'][:90]}...")
        print()
    try:
        s_idx = int(input("  Select scenario number: ").strip()) - 1
        scenario_key = scenario_list[s_idx][0]
    except (ValueError, IndexError):
        scenario_key = scenario_list[0][0]
    print(f"  Selected: {scenario_key}")

    # AI option
    ai_choice = input("\n  Enable AI remediation with Gemma 4:e4b? [Y/n]: ").strip().lower()
    ai_enabled = ai_choice != 'n'

    # Run
    from ims_digital_twin_security_certification_compliances.pipeline.audit_pipeline import (
        ComplianceAuditPipeline,
    )
    litellm.drop_params = True
    litellm.set_verbose = False
    pipeline = ComplianceAuditPipeline(thinking_mode=True)
    state = pipeline.run(
        framework_keys=selected_frameworks,
        scenario_key=scenario_key,
        ai_remediation=ai_enabled,
    )

    if state.final_report_path:
        print(f"\n  Full report: {state.final_report_path}")

    # Offer web server
    web = input("\n  Launch compliance dashboard? [y/N]: ").strip().lower()
    if web == 'y':
        cmd_web("0.0.0.0", 8001)


if __name__ == "__main__":
    main()
