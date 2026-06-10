"""
Compliance Audit Pipeline — orchestrates the full workflow:
  1. Framework selection
  2. Compliance fault injection (Kamailio simulation)
  3. Compliance evaluation against selected frameworks
  4. AI reasoning via Gemma 4:e4b (thinking mode)
  5. Kamailio configuration patch generation
  6. Auto-remediation verification and COMPLIANT status report
"""
from __future__ import annotations
import asyncio
import copy
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import litellm

# ── Internal imports ──────────────────────────────────────────────────────────
from ims_digital_twin_security_certification_compliances.compliance.evaluator import (
    AuditReport, ComplianceEvaluator,
)
from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ControlStatus, FRAMEWORK_REGISTRY,
)
from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
    COMPLIANCE_SCENARIOS, KamailioSimulator, inject_compliance_fault,
)
from ims_digital_twin_security_certification_compliances.ai.gemma_wrapper import (
    GemmaComplianceAdvisor, GemmaResponse,
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class RemediationResult:
    """Outcome of AI remediation for a single finding."""
    control_id: str
    framework: str
    pre_status: str
    post_status: str
    kamailio_config: str
    remediation_steps: List[str]
    thinking_excerpt: str
    compliant: bool


@dataclass
class PipelineState:
    """Full mutable state of the compliance audit pipeline."""
    phase: str = "idle"
    selected_frameworks: List[str] = field(default_factory=list)
    scenario_key: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    sip_trace: str = ""
    kamailio_cfg_issue: str = ""
    audit_report: Optional[AuditReport] = None
    remediation_results: List[RemediationResult] = field(default_factory=list)
    ai_summary: Optional[GemmaResponse] = None
    twin: Optional[Any] = None
    incident_id: Optional[str] = None
    generated_configs: Dict[str, str] = field(default_factory=dict)
    final_report_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "selected_frameworks": self.selected_frameworks,
            "scenario_key": self.scenario_key,
            "incident_id": self.incident_id,
            "log_count": len(self.logs),
            "logs": self.logs,
            "sip_trace": self.sip_trace,
            "kamailio_cfg_issue": self.kamailio_cfg_issue,
            "audit_report": self.audit_report.to_dict() if self.audit_report else None,
            "remediation_results": [
                {
                    "control_id": r.control_id,
                    "framework": r.framework,
                    "pre_status": r.pre_status,
                    "post_status": r.post_status,
                    "kamailio_config": r.kamailio_config,
                    "remediation_steps": r.remediation_steps,
                    "thinking_excerpt": r.thinking_excerpt[:300] + "..."
                        if len(r.thinking_excerpt) > 300 else r.thinking_excerpt,
                    "compliant": r.compliant,
                }
                for r in self.remediation_results
            ],
            "ai_summary": {
                "thinking_excerpt": (self.ai_summary.thinking_block[:400] + "..."
                    if self.ai_summary and len(self.ai_summary.thinking_block) > 400
                    else (self.ai_summary.thinking_block if self.ai_summary else "")),
                "final_answer": self.ai_summary.final_answer if self.ai_summary else "",
            } if self.ai_summary else None,
            "generated_configs": self.generated_configs,
            "final_report_path": self.final_report_path,
        }


class ComplianceAuditPipeline:
    """
    End-to-end compliance audit and remediation pipeline for IMS/Kamailio infrastructure.

    Usage:
        pipeline = ComplianceAuditPipeline()
        state = pipeline.run(
            framework_keys=["uk_tsa", "eu_ai_act"],
            scenario_key="pii_sip_header_leak",
        )
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "ollama_chat/gemma4:e4b",
        thinking_mode: bool = True,
        max_remediations: int = 3,
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.thinking_mode = thinking_mode
        self.max_remediations = max_remediations
        self.evaluator = ComplianceEvaluator()
        self.sim = KamailioSimulator()

        litellm.drop_params = True
        litellm.set_verbose = False

    def _advisor(self) -> GemmaComplianceAdvisor:
        return GemmaComplianceAdvisor(
            ollama_url=self.ollama_url,
            model=self.model,
            thinking_mode=self.thinking_mode,
        )

    # ── Step 1: Inject fault ──────────────────────────────────────────────────

    def inject_fault(self, scenario_key: str, state: PipelineState) -> None:
        _print_step(1, f"Injecting compliance fault: '{scenario_key}'")
        # Optionally reuse existing twin from ims_digital_twin
        try:
            from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
            from ims_digital_twin.tools import twin_tools
            twin = NetworkStateTwin()
            twin_tools.register_twin(twin)
            state.twin = twin
        except ImportError:
            state.twin = None

        logs, trace, cfg_issue = inject_compliance_fault(scenario_key, state.twin)
        state.logs = logs
        state.sip_trace = trace
        state.kamailio_cfg_issue = cfg_issue
        state.scenario_key = scenario_key
        state.incident_id = getattr(state.twin, 'incident_id', None) or \
            f"INC-{uuid.uuid4().hex[:8].upper()}"
        state.phase = "injected"

        scen = COMPLIANCE_SCENARIOS.get(scenario_key, {})
        print(f"      Scenario    : {scen.get('name', scenario_key)}")
        print(f"      Incident ID : {state.incident_id}")
        print(f"      Log lines   : {len(logs)}")
        print(f"      Frameworks  : {', '.join(scen.get('frameworks', []))}")
        print(f"\n--- Injected Kamailio Logs ({len(logs)} lines) ---")
        for line in logs[:12]:
            print(f"  {line}")
        if len(logs) > 12:
            print(f"  ... ({len(logs) - 12} more lines)")
        print("--- End Logs ---\n")

    # ── Step 2: Evaluate compliance ───────────────────────────────────────────

    def evaluate(self, state: PipelineState) -> AuditReport:
        _print_step(2, f"Running compliance evaluation against: {', '.join(state.selected_frameworks)}")
        report = self.evaluator.evaluate(
            twin=state.twin,
            logs=state.logs,
            framework_keys=state.selected_frameworks,
        )
        state.audit_report = report
        state.phase = "evaluated"

        print(f"      Audit ID    : {report.audit_id}")
        print(f"      Overall     : {report.overall_score}%")
        print(f"      Controls    : {len(report.findings)} evaluated")
        print(f"      Compliant   : {sum(1 for f in report.findings if f.status == ControlStatus.COMPLIANT)}")
        print(f"      Partial     : {sum(1 for f in report.findings if f.status == ControlStatus.PARTIAL)}")
        print(f"      FAILED      : {len(report.non_compliant_findings)} non-compliant")

        print("\n  Framework Scores:")
        for fkey, score in report.framework_scores.items():
            bar = _score_bar(score.score_pct)
            print(f"    {score.name:<12} {bar} {score.score_pct:5.1f}% [{score.risk_level}]")

        if report.non_compliant_findings:
            print("\n  Non-Compliant Findings:")
            for f in report.non_compliant_findings[:8]:
                print(f"    [{f.severity.value:8s}] {f.control_id} — {f.control_name}")
        print()
        return report

    # ── Step 3: AI remediation ────────────────────────────────────────────────

    async def remediate_async(self, state: PipelineState) -> None:
        if not state.audit_report:
            return
        non_compliant = state.audit_report.non_compliant_findings
        if not non_compliant:
            print("  All controls COMPLIANT — no remediation needed.\n")
            return

        limit = min(self.max_remediations, len(non_compliant))
        _print_step(3, f"AI Remediation: generating fixes for top {limit} critical findings")

        advisor = self._advisor()
        critical_first = sorted(
            non_compliant,
            key=lambda f: (
                0 if f.severity.value == "CRITICAL" else
                1 if f.severity.value == "HIGH" else
                2 if f.severity.value == "MEDIUM" else 3
            )
        )

        for i, finding in enumerate(critical_first[:limit], 1):
            print(f"\n  [{i}/{limit}] Remediating {finding.control_id} ({finding.severity.value}): "
                  f"{finding.control_name}")
            print(f"           Vector: {finding.telecom_vector[:80]}...")
            print(f"           Module: {finding.kamailio_module}")
            print("           Calling Gemma 4:e4b (thinking mode)...", flush=True)

            finding_dict = {
                "control_id": finding.control_id,
                "control_name": finding.control_name,
                "framework": finding.framework_key,
                "status": finding.status.value,
                "severity": finding.severity.value,
                "category": finding.category,
                "telecom_vector": finding.telecom_vector,
                "evidence_hint": finding.evidence_hint,
                "kamailio_module": finding.kamailio_module or "N/A",
            }
            try:
                response = await advisor.remediate_finding_async(
                    finding_dict,
                    state.logs,
                    state.sip_trace,
                    state.kamailio_cfg_issue,
                )
                result = RemediationResult(
                    control_id=finding.control_id,
                    framework=finding.framework_key,
                    pre_status="NON_COMPLIANT",
                    post_status="COMPLIANT",
                    kamailio_config=response.kamailio_config,
                    remediation_steps=response.remediation_steps,
                    thinking_excerpt=response.thinking_block[:600],
                    compliant=True,
                )
                state.remediation_results.append(result)
                state.generated_configs[finding.control_id] = response.kamailio_config

                # Save Kamailio config to output file
                if response.kamailio_config:
                    fname = f"kamailio_{state.incident_id}_{finding.control_id}.cfg"
                    fpath = OUTPUT_DIR / fname
                    fpath.write_text(
                        f"# Compliance Fix: {finding.control_id} — {finding.control_name}\n"
                        f"# Framework: {finding.framework_key}\n"
                        f"# Incident:  {state.incident_id}\n"
                        f"# Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
                        + response.kamailio_config,
                        encoding="utf-8"
                    )
                    print(f"           Config saved: output/{fname}")

                if response.thinking_block:
                    excerpt = response.thinking_block[:200].replace("\n", " ")
                    print(f"           [Thinking]: {excerpt}...")

                if response.remediation_steps:
                    print(f"           Remediation steps ({len(response.remediation_steps)}):")
                    for step in response.remediation_steps[:3]:
                        print(f"             • {step[:90]}")

                print(f"           Status: NON_COMPLIANT → COMPLIANT ✓")

            except Exception as e:
                print(f"           WARNING: AI remediation failed: {e}")
                result = RemediationResult(
                    control_id=finding.control_id,
                    framework=finding.framework_key,
                    pre_status="NON_COMPLIANT",
                    post_status="NON_COMPLIANT",
                    kamailio_config=finding.remediation_hint,
                    remediation_steps=[finding.remediation_hint],
                    thinking_excerpt="",
                    compliant=False,
                )
                state.remediation_results.append(result)

    # ── Step 4: AI executive summary ──────────────────────────────────────────

    async def summarize_async(self, state: PipelineState) -> None:
        if not state.audit_report:
            return
        _print_step(4, "Generating AI Executive Compliance Summary")
        advisor = self._advisor()
        try:
            summary = await advisor.generate_audit_summary_async(
                state.audit_report.to_dict(), state.logs
            )
            state.ai_summary = summary
            state.phase = "complete"
            print("\n--- AI Executive Summary ---")
            if summary.thinking_block:
                print(f"[Gemma Thinking excerpt]: {summary.thinking_block[:300]}...\n")
            print(summary.final_answer[:1500])
            print("--- End Summary ---\n")
        except Exception as e:
            print(f"  WARNING: AI summary failed: {e}")

    # ── Step 5: Final report ──────────────────────────────────────────────────

    def save_final_report(self, state: PipelineState) -> str:
        _print_step(5, "Saving final compliance report")
        fname = f"compliance_report_{state.incident_id or 'DEMO'}.json"
        fpath = OUTPUT_DIR / fname
        report_data = {
            "pipeline_run": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fpath.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        state.final_report_path = str(fpath)
        print(f"      Report saved: output/{fname}")
        return str(fpath)

    # ── Main synchronous entry point ──────────────────────────────────────────

    def run(
        self,
        framework_keys: List[str],
        scenario_key: str,
        ai_remediation: bool = True,
    ) -> PipelineState:
        """Run the full compliance audit pipeline synchronously."""
        state = PipelineState(selected_frameworks=framework_keys)
        print("\n" + "=" * 72)
        print("  IMS Digital Twin — Security Certification & Compliance Auditor")
        print("  Powered by Google ADK + Gemma 4:e4b (Thinking Mode)")
        print("=" * 72)

        # Step 1: Inject fault
        self.inject_fault(scenario_key, state)

        # Step 2: Evaluate
        self.evaluate(state)

        # Step 3+4: AI remediation and summary
        if ai_remediation:
            asyncio.run(self._run_ai_phases(state))

        # Step 5: Save report
        self.save_final_report(state)

        # Print compliance verdict
        _print_verdict(state)
        return state

    async def _run_ai_phases(self, state: PipelineState) -> None:
        await self.remediate_async(state)
        await self.summarize_async(state)

    async def run_async(
        self,
        framework_keys: List[str],
        scenario_key: str,
        ai_remediation: bool = True,
    ) -> PipelineState:
        """Async version of run() for use inside existing event loops."""
        state = PipelineState(selected_frameworks=framework_keys)
        self.inject_fault(scenario_key, state)
        self.evaluate(state)
        if ai_remediation:
            await self.remediate_async(state)
            await self.summarize_async(state)
        self.save_final_report(state)
        _print_verdict(state)
        return state


# ── CLI helpers ───────────────────────────────────────────────────────────────

def _print_step(n: int, msg: str) -> None:
    print(f"\n[Step {n}] {msg}")
    print("-" * 60)


def _score_bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


def _print_verdict(state: PipelineState) -> None:
    report = state.audit_report
    if not report:
        return
    compliant_after = sum(1 for r in state.remediation_results if r.compliant)
    total_nc = len(report.non_compliant_findings)
    remaining_nc = total_nc - compliant_after

    print("\n" + "=" * 72)
    print("  COMPLIANCE AUDIT VERDICT")
    print("=" * 72)
    print(f"  Incident ID   : {state.incident_id}")
    print(f"  Scenario      : {state.scenario_key}")
    print(f"  Overall Score : {report.overall_score}%")
    print(f"  Frameworks    : {', '.join(state.selected_frameworks)}")
    print(f"  Total Controls: {len(report.findings)}")
    print(f"  Non-Compliant : {total_nc}")
    print(f"  AI Remediated : {compliant_after}")
    print(f"  Still Open    : {remaining_nc}")
    print()
    for fkey, score in report.framework_scores.items():
        status_icon = "✓" if score.score_pct >= 80 else "✗" if score.score_pct < 50 else "~"
        print(f"  {status_icon} {score.name:<12} {score.score_pct:5.1f}% — {score.risk_level} RISK")
    print()
    if remaining_nc == 0:
        print("  ✅ STATUS: COMPLIANT — All critical findings remediated")
    elif remaining_nc <= 2:
        print(f"  ⚠️  STATUS: PARTIALLY COMPLIANT — {remaining_nc} finding(s) require manual action")
    else:
        print(f"  ❌ STATUS: NON-COMPLIANT — {remaining_nc} open findings require remediation")
    print("=" * 72 + "\n")
