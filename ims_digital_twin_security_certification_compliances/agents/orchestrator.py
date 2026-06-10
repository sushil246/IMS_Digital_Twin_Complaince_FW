"""
Certification Orchestrator — multi-agent coordinator for IMS compliance testing.

Manages the 6 framework-specific agents as a pool and routes each compliance finding
to the appropriate specialist agent. Supports:
  - Sequential mode: one agent per finding (most reliable for detailed remediations)
  - Parallel mode: all selected agents run concurrently on the same scenario (fast overview)
  - Framework-targeted mode: only the relevant agent(s) for a given scenario
"""
from __future__ import annotations
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import litellm

from ims_digital_twin_security_certification_compliances.agents._base import run_agent_async
from ims_digital_twin_security_certification_compliances.agents.uk_tsa_agent import build_uk_tsa_agent
from ims_digital_twin_security_certification_compliances.agents.eu_ai_act_agent import build_eu_ai_act_agent
from ims_digital_twin_security_certification_compliances.agents.iso_42001_agent import build_iso_42001_agent
from ims_digital_twin_security_certification_compliances.agents.nist_ai_rmf_agent import build_nist_ai_rmf_agent
from ims_digital_twin_security_certification_compliances.agents.mit_ai_risk_agent import build_mit_ai_risk_agent
from ims_digital_twin_security_certification_compliances.agents.oecd_ai_agent import build_oecd_ai_agent

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Agent factory registry ────────────────────────────────────────────────────

AGENT_BUILDERS = {
    "uk_tsa":      build_uk_tsa_agent,
    "eu_ai_act":   build_eu_ai_act_agent,
    "iso_42001":   build_iso_42001_agent,
    "nist_ai_rmf": build_nist_ai_rmf_agent,
    "mit_ai_risk": build_mit_ai_risk_agent,
    "oecd_ai":     build_oecd_ai_agent,
}

AGENT_LABELS = {
    "uk_tsa":      "🇬🇧 UK TSA",
    "eu_ai_act":   "🇪🇺 EU AI Act",
    "iso_42001":   "🌐 ISO 42001",
    "nist_ai_rmf": "🇺🇸 NIST AI RMF",
    "mit_ai_risk": "🎓 MIT AI Risk",
    "oecd_ai":     "🌍 OECD AI",
}


@dataclass
class AgentResult:
    """Output from a single certification agent run."""
    framework_key: str
    agent_name: str
    prompt: str
    response: str
    duration_sec: float
    control_ids_addressed: List[str] = field(default_factory=list)
    kamailio_config_excerpt: str = ""


@dataclass
class OrchestratorReport:
    """Combined report from all certification agents."""
    session_id: str
    timestamp: str
    scenario_key: str
    selected_frameworks: List[str]
    agent_results: List[AgentResult] = field(default_factory=list)
    combined_summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "scenario_key": self.scenario_key,
            "selected_frameworks": self.selected_frameworks,
            "agent_results": [
                {
                    "framework_key": r.framework_key,
                    "agent_name": r.agent_name,
                    "duration_sec": r.duration_sec,
                    "response_length": len(r.response),
                    "response_excerpt": r.response[:500],
                    "control_ids": r.control_ids_addressed,
                }
                for r in self.agent_results
            ],
            "combined_summary": self.combined_summary,
        }


def _build_agent_prompt(
    framework_key: str,
    scenario_key: str,
    logs: List[str],
    sip_trace: str,
    kamailio_cfg_issue: str,
    findings: List[Dict],
) -> str:
    """Build a framework-specific audit prompt for the certification agent."""
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        COMPLIANCE_SCENARIOS,
    )
    scen = COMPLIANCE_SCENARIOS.get(scenario_key, {})
    logs_sample = "\n".join(logs[-12:])
    nc_findings = [f for f in findings if f.get("status") == "NON_COMPLIANT"
                   and f.get("framework") == framework_key]

    nc_summary = "\n".join(
        f"  [{f['severity']}] {f['control_id']}: {f['control_name']}"
        for f in nc_findings
    ) or "  No non-compliant controls for this framework."

    return f"""\
CERTIFICATION AUDIT REQUEST — {AGENT_LABELS.get(framework_key, framework_key)}
====================================================================
Scenario:    {scen.get('name', scenario_key)}
Description: {scen.get('description', '')}

NON-COMPLIANT CONTROLS FOR THIS FRAMEWORK:
{nc_summary}

KAMAILIO CONFIGURATION ISSUE:
{kamailio_cfg_issue or "See logs for evidence"}

SIP TRACE:
{sip_trace or "See logs"}

RECENT KAMAILIO LOGS (last 12 lines):
{logs_sample}

CERTIFICATION TASK:
1. Analyze the non-compliant controls listed above for your framework
2. Call your available tools to generate specific fixes
3. Produce a complete certification assessment with:
   - Finding summary per control ID
   - Kamailio configuration fix for each non-compliant control
   - Verification steps
   - Estimated compliance status after applying fixes
4. Be specific — reference log evidence and control IDs throughout
"""


class CertificationOrchestrator:
    """
    Multi-agent compliance certification orchestrator.
    Routes each compliance framework's findings to its specialist agent.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "ollama_chat/gemma4:e4b",
    ):
        self.ollama_url = ollama_url
        self.model = model
        litellm.drop_params = True
        litellm.set_verbose = False

    def _build_agents(self, framework_keys: List[str]) -> Dict[str, Any]:
        """Build ADK agents for the specified frameworks."""
        agents = {}
        for fk in framework_keys:
            if fk in AGENT_BUILDERS:
                agents[fk] = AGENT_BUILDERS[fk](self.ollama_url, self.model)
        return agents

    async def run_agent_for_framework(
        self,
        framework_key: str,
        scenario_key: str,
        logs: List[str],
        sip_trace: str,
        kamailio_cfg_issue: str,
        findings: List[Dict],
    ) -> AgentResult:
        """Run the specialist agent for a single framework."""
        import time
        import re

        agent = AGENT_BUILDERS[framework_key](self.ollama_url, self.model)
        prompt = _build_agent_prompt(
            framework_key, scenario_key, logs, sip_trace, kamailio_cfg_issue, findings
        )
        label = AGENT_LABELS.get(framework_key, framework_key)
        print(f"  [{label}] Agent running...", flush=True)
        start = time.time()
        try:
            response = await run_agent_async(
                agent, prompt,
                app_name="agents",
            )
        except Exception as e:
            response = f"Agent error: {e}"
        duration = round(time.time() - start, 1)

        # Extract control IDs referenced in response
        control_ids = list(set(re.findall(r"[A-Z]{2,8}-[A-Z]{2,6}-\d{3}", response)))

        # Extract Kamailio config excerpt
        cfg_match = re.search(r"```(?:kamailio|cfg)?\n(.*?)```", response, re.DOTALL)
        cfg_excerpt = cfg_match.group(1)[:400] if cfg_match else ""

        print(f"  [{label}] Done in {duration}s — {len(response)} chars, "
              f"{len(control_ids)} controls addressed")
        return AgentResult(
            framework_key=framework_key,
            agent_name=f"{framework_key}_agent",
            prompt=prompt[:200],
            response=response,
            duration_sec=duration,
            control_ids_addressed=control_ids,
            kamailio_config_excerpt=cfg_excerpt,
        )

    async def run_parallel(
        self,
        framework_keys: List[str],
        scenario_key: str,
        logs: List[str],
        sip_trace: str,
        kamailio_cfg_issue: str,
        findings: List[Dict],
    ) -> OrchestratorReport:
        """Run all framework agents in parallel for maximum throughput."""
        session_id = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        print(f"\n[Orchestrator] Running {len(framework_keys)} agents in PARALLEL")
        print(f"  Session ID: {session_id}")
        print(f"  Frameworks: {', '.join(AGENT_LABELS.get(k, k) for k in framework_keys)}")

        tasks = [
            self.run_agent_for_framework(
                fk, scenario_key, logs, sip_trace, kamailio_cfg_issue, findings
            )
            for fk in framework_keys
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        agent_results = [r for r in results if isinstance(r, AgentResult)]

        report = OrchestratorReport(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            scenario_key=scenario_key,
            selected_frameworks=framework_keys,
            agent_results=agent_results,
        )
        report.combined_summary = self._build_combined_summary(agent_results)
        self._save_report(report)
        return report

    async def run_sequential(
        self,
        framework_keys: List[str],
        scenario_key: str,
        logs: List[str],
        sip_trace: str,
        kamailio_cfg_issue: str,
        findings: List[Dict],
    ) -> OrchestratorReport:
        """Run framework agents sequentially for detailed per-agent output."""
        session_id = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        print(f"\n[Orchestrator] Running {len(framework_keys)} agents SEQUENTIALLY")
        print(f"  Session ID: {session_id}")

        agent_results = []
        for fk in framework_keys:
            result = await self.run_agent_for_framework(
                fk, scenario_key, logs, sip_trace, kamailio_cfg_issue, findings
            )
            agent_results.append(result)
            print(f"  [{AGENT_LABELS.get(fk, fk)}] Response excerpt:")
            print("    " + result.response[:300].replace("\n", "\n    "))
            print()

        report = OrchestratorReport(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            scenario_key=scenario_key,
            selected_frameworks=framework_keys,
            agent_results=agent_results,
        )
        report.combined_summary = self._build_combined_summary(agent_results)
        self._save_report(report)
        return report

    def run(
        self,
        framework_keys: List[str],
        scenario_key: str,
        logs: List[str],
        sip_trace: str = "",
        kamailio_cfg_issue: str = "",
        findings: List[Dict] = None,
        parallel: bool = False,
    ) -> OrchestratorReport:
        """Synchronous entry point — runs certification agents for selected frameworks."""
        _findings = findings or []
        if parallel:
            return asyncio.run(self.run_parallel(
                framework_keys, scenario_key, logs, sip_trace, kamailio_cfg_issue, _findings
            ))
        return asyncio.run(self.run_sequential(
            framework_keys, scenario_key, logs, sip_trace, kamailio_cfg_issue, _findings
        ))

    def _build_combined_summary(self, results: List[AgentResult]) -> str:
        lines = ["=" * 64, "  MULTI-AGENT CERTIFICATION SUMMARY", "=" * 64]
        for r in results:
            label = AGENT_LABELS.get(r.framework_key, r.framework_key)
            controls = ", ".join(r.control_ids_addressed[:5]) or "none identified"
            lines.append(f"\n  {label}")
            lines.append(f"  Duration: {r.duration_sec}s | Controls addressed: {controls}")
            if r.kamailio_config_excerpt:
                lines.append(f"  Config generated: YES ({len(r.kamailio_config_excerpt)} chars excerpt)")
            lines.append("  " + "─" * 50)
            lines.append("  " + r.response[:400].replace("\n", "\n  "))
        return "\n".join(lines)

    def _save_report(self, report: OrchestratorReport) -> None:
        fname = f"cert_report_{report.session_id}.json"
        fpath = OUTPUT_DIR / fname
        fpath.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\n  Certification report saved: output/{fname}")
