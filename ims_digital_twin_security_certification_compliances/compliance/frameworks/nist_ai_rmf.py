"""
NIST AI Risk Management Framework 1.0 — controls for IMS/telecom AI systems.
Covers GOVERN, MAP, MEASURE, MANAGE functions for trustworthy AI in telecom routing.
"""
from __future__ import annotations
import re
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_trustworthiness_metrics(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    trust_logs = [l for l in logs if any(kw in l.lower() for kw in
                  ["trust-score", "confidence", "uncertainty", "reliability-index"])]
    if not trust_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_adversarial_prompt_defense(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'adversarial' in fault or 'prompt_inject' in fault:
        return ControlStatus.NON_COMPLIANT
    defense_logs = [l for l in logs if any(kw in l.lower() for kw in
                    ["input-sanitize", "prompt-guard", "injection-blocked", "malformed-header"])]
    if not defense_logs and logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_explainability_logging(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    # Log-based: evidence that no version/lineage/explainability is emitted
    no_explain = [l for l in logs if any(kw in l for kw in
                  ["no version tag", "NO risk event", "no lineage", "NO audit log"])]
    if no_explain:
        return ControlStatus.NON_COMPLIANT
    explain_logs = [l for l in logs if any(kw in l.lower() for kw in
                    ["reason:", "rationale:", "decision-basis", "feature-importance"])]
    if not explain_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_risk_identification(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    alarms = getattr(twin, 'all_alarms', lambda: [])()
    if fault and not alarms:
        return ControlStatus.NON_COMPLIANT
    if alarms:
        return ControlStatus.COMPLIANT
    return ControlStatus.PARTIAL


def _check_incident_management(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    incident_id = getattr(twin, 'incident_id', None)
    if not incident_id:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_bias_fairness(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'fair_resource' in fault:
        return ControlStatus.NON_COMPLIANT
    bias_logs = [l for l in logs if any(kw in l.lower() for kw in
                 ["fairness", "bias-check", "allocation-equal", "priority-fair"])]
    if not bias_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


NIST_AI_RMF_CONTROLS: list = [
    ComplianceControl(
        id="NIST-GOVERN-001",
        name="AI Trustworthiness Metrics Definition",
        description="(GOVERN) Define and instrument measurable trustworthiness metrics for "
                    "all AI systems in the IMS routing path. Metrics must cover: accuracy, "
                    "reliability, safety, security, explainability, and fairness dimensions.",
        severity=ControlSeverity.HIGH,
        category="GOVERN",
        telecom_vector="AI routing agent with no trust-score or confidence metric instrumentation",
        check=_check_trustworthiness_metrics,
        evidence_hint="Check for trust-score, confidence, reliability-index in telemetry",
        remediation_hint="Instrument AI routing agent with trustworthiness scorecard. "
                         "Expose: confidence_score, calibration_error, reliability_index. "
                         "Log per-decision: {decision_id, confidence, trust_score, timestamp}.",
        kamailio_module="statistics, xlog",
    ),
    ComplianceControl(
        id="NIST-MAP-001",
        name="Adversarial Prompt-Injection Defense",
        description="(MAP) AI systems processing SIP headers or routing control inputs must "
                    "defend against adversarial input injection. Malformed or crafted SIP "
                    "headers targeting routing AI must be detected and sanitized.",
        severity=ControlSeverity.CRITICAL,
        category="MAP",
        telecom_vector="Crafted SIP header injecting adversarial routing directives into AI model",
        check=_check_adversarial_prompt_defense,
        evidence_hint="Check for input sanitization logs and injection-blocked events",
        remediation_hint="Add Kamailio `sanity` module checks before AI routing call: "
                         "`sanity_check()` validates SIP structure. "
                         "Sanitize custom headers: strip non-alphanumeric from X-Route-Hint. "
                         "Add input validation layer in routing AI: reject inputs with "
                         "unexpected tokens or control characters.",
        kamailio_module="sanity, textopsx, sipdump",
    ),
    ComplianceControl(
        id="NIST-MEASURE-001",
        name="System Explainability and Decision Logging",
        description="(MEASURE) AI routing decisions must be explainable: each routing "
                    "choice must log the top features, weights, and reasoning that led to "
                    "the decision. Non-explainable decisions require human review.",
        severity=ControlSeverity.HIGH,
        category="MEASURE",
        telecom_vector="Black-box AI routing decision with no explainability log entry",
        check=_check_explainability_logging,
        evidence_hint="Check for reason:, rationale:, feature-importance in routing logs",
        remediation_hint="Implement LIME/SHAP explainability on routing model output. "
                         "Emit explanation with each decision: top-3 features by weight. "
                         "In Kamailio: `xlog(\"ROUTE_REASON: $ai.top_features\")` per INVITE.",
        kamailio_module="xlog, jsonrpcs",
    ),
    ComplianceControl(
        id="NIST-MAP-002",
        name="AI Risk Context Identification",
        description="(MAP) Systematically identify and document operational contexts where "
                    "AI routing failures could cause harm. Map risk scenarios to "
                    "emergency-call routing, priority traffic, and network congestion.",
        severity=ControlSeverity.HIGH,
        category="MAP",
        telecom_vector="AI routing unaware of emergency-call priority, causing 112/911 drops",
        check=_check_risk_identification,
        evidence_hint="Verify alarm generation for fault conditions and risk documentation",
        remediation_hint="Implement emergency-call bypass: hardcode 112/911/933 routing "
                         "to bypass AI model. In Kamailio: `if(is_uri_host_local()) "
                         "{ route(EMERGENCY); }` before AI routing evaluation.",
        kamailio_module="emergency, dispatcher",
    ),
    ComplianceControl(
        id="NIST-MANAGE-001",
        name="AI Incident Detection and Response",
        description="(MANAGE) Automated detection of AI routing failures must trigger "
                    "incident creation, alert NOC team, and initiate defined response "
                    "workflow. MTTR for P1 AI incidents: target < 30 minutes.",
        severity=ControlSeverity.HIGH,
        category="MANAGE",
        telecom_vector="AI routing failure with no incident record or auto-escalation",
        check=_check_incident_management,
        evidence_hint="Verify incident_id created and escalation chain activated",
        remediation_hint="Integrate AI anomaly detection with incident management system. "
                         "Auto-create P1 ticket when routing accuracy drops <90%. "
                         "PagerDuty/OpsGenie webhook from Prometheus alert. "
                         "Define AI-specific runbook in NOC knowledge base.",
        kamailio_module="N/A (operational requirement)",
    ),
    ComplianceControl(
        id="NIST-MEASURE-002",
        name="Bias and Fairness Monitoring",
        description="(MEASURE) AI routing systems must be monitored for demographic or "
                    "geographic bias in quality-of-service allocation. Fair resource "
                    "allocation must be verifiable across subscriber segments.",
        severity=ControlSeverity.MEDIUM,
        category="MEASURE",
        telecom_vector="AI QoS optimizer systematically deprioritizing rural or low-revenue subscribers",
        check=_check_bias_fairness,
        evidence_hint="Check for fairness metrics and allocation-equal log entries",
        remediation_hint="Add fairness constraint to routing objective function. "
                         "Monitor allocation Gini coefficient across subscriber groups. "
                         "Alert if any subscriber segment receives <80% of SLA-committed QoS.",
        kamailio_module="statistics, N/A (ML pipeline fairness)",
    ),
]
