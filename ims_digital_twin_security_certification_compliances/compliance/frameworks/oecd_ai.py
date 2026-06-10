"""
OECD AI Principles — controls for transparent, accountable, and fair AI in IMS/telecom.
Covers transparency of automated calling logic, accountability traces, and resource fairness.
"""
from __future__ import annotations
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_transparency_calling_logic(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    transparency_logs = [l for l in logs if any(kw in l.lower() for kw in
                         ["routing-policy:", "call-path:", "via-route:", "policy-applied:"])]
    if not transparency_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_accountability_trace(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    incident_id = getattr(twin, 'incident_id', None)
    account_logs = [l for l in logs if any(kw in l.lower() for kw in
                    ["operator:", "changed-by:", "approved-by:", "accountability"])]
    if not account_logs and incident_id:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_fair_resource_allocation(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unfair_routing' in fault:
        return ControlStatus.NON_COMPLIANT
    fair_logs = [l for l in logs if any(kw in l.lower() for kw in
                 ["fair-queue", "wfq", "weighted-fair", "priority-class"])]
    if not fair_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_safety_by_design(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    if sbc:
        dos = sbc.config.get("dos_protection", {})
        has_rate_limit = dos.get("max_invite_rate", 0) > 0
        has_reg_limit = dos.get("max_register_rate", 0) > 0
        if has_rate_limit and has_reg_limit:
            return ControlStatus.COMPLIANT
        return ControlStatus.PARTIAL
    return ControlStatus.NOT_APPLICABLE


def _check_privacy_by_design(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'pii_leak' in fault or 'pii_sip' in fault:
        return ControlStatus.NON_COMPLIANT
    pii_logs = [l for l in logs if any(kw in l.lower() for kw in
                ["anonymiz", "pseudonym", "pii-masked", "privacy-applied"])]
    raw_pii = [l for l in logs if "sip:+" in l.lower() and "@" in l]
    if raw_pii and not pii_logs:
        return ControlStatus.NON_COMPLIANT
    if raw_pii and pii_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


OECD_AI_CONTROLS: list = [
    ComplianceControl(
        id="OECD-TRANS-001",
        name="Transparency of Automated Calling Logic",
        description="Automated call routing decisions must be transparent: operators and "
                    "subscribers must be able to understand why a call was routed through "
                    "a specific path. Policy-applied logs must be human-readable.",
        severity=ControlSeverity.HIGH,
        category="Transparency",
        telecom_vector="AI routing policy applied silently with no per-call routing explanation",
        check=_check_transparency_calling_logic,
        evidence_hint="Check for routing-policy:, call-path:, policy-applied: log entries",
        remediation_hint="Add routing transparency header: X-Routing-Policy: ai-load-balance/v2.1. "
                         "In Kamailio: `append_hf(\"X-Route-Via: $dd\\r\\n\")`. "
                         "Log per-call path: `xlog(\"ROUTE:$ci via $dd reason=load-balance\")`. ",
        kamailio_module="xlog, textopsx, append_hf",
    ),
    ComplianceControl(
        id="OECD-ACCNT-001",
        name="Accountability Trace Completeness",
        description="Every automated decision affecting call routing must have a complete "
                    "accountability trace: who authorized the policy, which model made the "
                    "decision, what data was used, and what outcome resulted.",
        severity=ControlSeverity.HIGH,
        category="Accountability",
        telecom_vector="AI routing change with no operator attribution or approval audit trail",
        check=_check_accountability_trace,
        evidence_hint="Check for operator:, changed-by:, approved-by: in routing change logs",
        remediation_hint="Implement accountability log schema: "
                         "{ts, decision_id, policy_id, model_ver, operator, approval_ref, outcome}. "
                         "All routing table changes via authenticated API with audit trail. "
                         "Immutable audit log — use append-only storage (e.g., AWS QLDB).",
        kamailio_module="jsonrpcs, N/A (audit log infrastructure)",
    ),
    ComplianceControl(
        id="OECD-FAIR-001",
        name="Fair Resource Allocation Verification",
        description="AI routing must not systematically disadvantage subscriber groups "
                    "based on location, device type, or service tier beyond contractual SLAs. "
                    "Regular fairness audits required with documented remediation.",
        severity=ControlSeverity.MEDIUM,
        category="Fairness",
        telecom_vector="AI QoS routing systematically deprioritizing subscribers on certain subnets",
        check=_check_fair_resource_allocation,
        evidence_hint="Check WFQ/fair-queue configuration and allocation equality metrics",
        remediation_hint="Implement weighted fair queuing in Kamailio: "
                         "Use `$dlg_ctx(timeout_route)` to ensure equal call setup opportunity. "
                         "Add fairness audit: weekly report comparing call success rates across "
                         "subscriber segments. Alert if deviation > 5% from mean.",
        kamailio_module="dialog, N/A (QoS policy)",
    ),
    ComplianceControl(
        id="OECD-SAFE-001",
        name="Safety by Design in AI Routing",
        description="AI routing systems must implement safety constraints by design: "
                    "fail-safe defaults (revert to static routing on failure), "
                    "bounded action space (no routing to unverified nodes), "
                    "and graceful degradation under uncertainty.",
        severity=ControlSeverity.HIGH,
        category="Safety",
        telecom_vector="AI routing agent failing open — routing to unknown next-hop on model error",
        check=_check_safety_by_design,
        evidence_hint="Verify dos_protection rate limits and fail-safe routing configuration",
        remediation_hint="Implement safety wrapper around AI routing: "
                         "`if(ai_route_failed()) { route(STATIC_FALLBACK); }`. "
                         "In Kamailio: define STATIC_FALLBACK route with hardcoded session agents. "
                         "Test failure injection quarterly with chaos engineering exercises.",
        kamailio_module="dispatcher, $avp, failure_route",
    ),
    ComplianceControl(
        id="OECD-PRIV-001",
        name="Privacy by Design in Call Routing",
        description="Call routing AI must not process subscriber PII unnecessarily. "
                    "Routing decisions should use anonymized subscriber identifiers "
                    "(session tokens, pseudonyms) rather than real E.164 numbers or names.",
        severity=ControlSeverity.HIGH,
        category="Privacy",
        telecom_vector="AI routing model receiving raw SIP From/To headers with unmasked subscriber PII",
        check=_check_privacy_by_design,
        evidence_hint="Check for anonymiz, pseudonym, pii-masked in routing logs",
        remediation_hint="Pre-process SIP headers before AI routing: replace real AOR with "
                         "HMAC-pseudonym. In Kamailio: "
                         "`pv_printf($var(anon_from), \"session-$ct\")` before routing evaluation. "
                         "Strip MSISDN from AI model input feature vector.",
        kamailio_module="pv, textopsx, crypto",
    ),
]
