"""
EU AI Act (Regulation 2024/1689) — compliance controls for AI-driven IMS network routing.
Covers high-risk classification, biometric processing, drift logging, and human oversight.
"""
from __future__ import annotations
import re
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_high_risk_classification(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if AI routing system is not documented as high-risk with conformity assessment."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    # Check if injected fault involves unlogged AI routing decision
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault or 'ai_routing' in fault:
        return ControlStatus.NON_COMPLIANT
    # Check twin config for AI governance marker
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    if sbc:
        ai_gov = sbc.config.get("ai_governance", {})
        if not ai_gov.get("high_risk_registered", False):
            return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_automated_routing_audit_trail(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if AI routing decisions lack immutable audit log with rationale."""
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    # Log-based detection: explicit evidence of missing audit trail
    no_audit_signals = [l for l in logs if any(kw in l.lower() for kw in
                        ["no audit log", "no risk event", "no version tag", "silent", "no lineage"])]
    if no_audit_signals:
        return ControlStatus.NON_COMPLIANT
    audit_logs = [l for l in logs if any(kw in l.lower() for kw in
                  ["routing-decision", "ai-route", "policy-applied", "route-reason"])]
    if not audit_logs and logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_biometric_consent(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if voice biometric processing occurs without consent records in logs."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'biometric_no_consent' in fault:
        return ControlStatus.NON_COMPLIANT
    # Check for biometric processing without consent marker
    biometric_logs = [l for l in logs if any(kw in l.lower() for kw in
                      ["voice-auth", "speaker-id", "biometric", "voice-print"])]
    consent_logs = [l for l in logs if "consent" in l.lower()]
    if biometric_logs and not consent_logs:
        return ControlStatus.NON_COMPLIANT
    if biometric_logs and consent_logs:
        return ControlStatus.COMPLIANT
    return ControlStatus.NOT_APPLICABLE


def _check_ai_drift_logging(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if no model drift detection or logging pipeline is configured."""
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'ai_drift' in fault or 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    # Log-based: explicit evidence that drift monitor is missing
    no_monitor = [l for l in logs if any(kw in l for kw in
                  ["NO ALERT CONFIGURED", "drift monitor not configured", "NOT CONFIGURED"])]
    if no_monitor:
        return ControlStatus.NON_COMPLIANT
    drift_logs = [l for l in logs if any(kw in l.lower() for kw in
                  ["drift", "model-version", "prediction-shift", "baseline-delta"])]
    if not drift_logs and logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_human_oversight(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if automated routing decisions have no human override mechanism."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    override_logs = [l for l in logs if any(kw in l.lower() for kw in
                     ["human-override", "manual-route", "noc-override", "operator-intervened"])]
    if not override_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_transparency_documentation(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if AI system lacks technical documentation for automated routing decisions."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    return ControlStatus.PARTIAL  # Default partial — requires external doc verification


EU_AI_ACT_CONTROLS: list = [
    ComplianceControl(
        id="EUAI-HRC-001",
        name="High-Risk AI System Classification",
        description="AI systems making automated routing and quality-of-service decisions "
                    "for critical communications infrastructure must be classified as high-risk "
                    "and registered in the EU AI Act database before deployment.",
        severity=ControlSeverity.CRITICAL,
        category="Governance",
        telecom_vector="AI-driven Kamailio routing policy without conformity assessment",
        check=_check_high_risk_classification,
        evidence_hint="Verify AI governance config and EU AI Act conformity documentation",
        remediation_hint="Register AI routing system in EU AI Act database. "
                         "Document intended purpose, training data, and performance metrics. "
                         "Implement human review gate for routing policy changes.",
        kamailio_module="N/A (process governance)",
    ),
    ComplianceControl(
        id="EUAI-HRC-002",
        name="Automated Routing Decision Audit Trail",
        description="Every AI-driven routing table modification must generate an immutable "
                    "audit log entry containing: timestamp, model version, input features, "
                    "decision rationale, and confidence score.",
        severity=ControlSeverity.CRITICAL,
        category="Auditability",
        telecom_vector="Opaque AI optimization modifying Kamailio dispatcher weights silently",
        check=_check_automated_routing_audit_trail,
        evidence_hint="Check for routing-decision log entries with model version and rationale",
        remediation_hint="Instrument AI routing agent to emit structured audit events: "
                         "{ts, model_ver, input_hash, decision, confidence, rationale}. "
                         "In Kamailio: use `xlog` module to log routing decisions with "
                         "`$ai.route.reason` pseudo-variable.",
        kamailio_module="xlog, jsonrpcs",
    ),
    ComplianceControl(
        id="EUAI-HRC-003",
        name="Biometric Processing Consent Logging",
        description="Voice authentication or speaker identification features must log "
                    "explicit consent records per Article 9. Biometric data processing "
                    "without consent records constitutes a high-risk violation.",
        severity=ControlSeverity.HIGH,
        category="Biometric Data",
        telecom_vector="Voice biometric speaker-ID running without consent records in SIP session",
        check=_check_biometric_consent,
        evidence_hint="Check for voice-auth/speaker-id log entries paired with consent records",
        remediation_hint="Implement consent verification SIP header check in Kamailio: "
                         "block calls where P-Privacy header is absent when voice-auth enabled. "
                         "Log consent token: `xlog(\"CONSENT:$fu:$ci:granted\")` per session.",
        kamailio_module="xlog, permissions, auth",
    ),
    ComplianceControl(
        id="EUAI-HRC-004",
        name="AI Model Drift Detection and Logging",
        description="AI routing models must be continuously monitored for distributional "
                    "drift. Drift events exceeding threshold must generate alerts and trigger "
                    "human review before further automated decisions proceed.",
        severity=ControlSeverity.HIGH,
        category="Model Monitoring",
        telecom_vector="Unmonitored drift in traffic-load prediction model silently degrading QoS",
        check=_check_ai_drift_logging,
        evidence_hint="Check drift log pipeline, model-version metadata, baseline-delta alerts",
        remediation_hint="Implement drift detector comparing routing distribution against baseline. "
                         "Emit syslog alert when KL-divergence exceeds 0.1. "
                         "Integrate with Prometheus: expose `ai_routing_drift_score` gauge.",
        kamailio_module="statistics, N/A (external ML pipeline)",
    ),
    ComplianceControl(
        id="EUAI-HRC-005",
        name="Human Oversight Mechanism",
        description="Operators must be able to override, correct, or shut down AI routing "
                    "decisions at any time. Override events must be logged with operator ID.",
        severity=ControlSeverity.HIGH,
        category="Human Oversight",
        telecom_vector="No operator override path for AI-modified Kamailio dispatcher table",
        check=_check_human_oversight,
        evidence_hint="Verify human-override API endpoint and NOC override log capability",
        remediation_hint="Implement `/api/routing/override` endpoint in management plane. "
                         "Use Kamailio `jsonrpcs` module to allow runtime dispatcher updates: "
                         "`kamcmd dispatcher.set_state d 1` for manual node control.",
        kamailio_module="jsonrpcs, dispatcher",
    ),
    ComplianceControl(
        id="EUAI-HRC-006",
        name="Technical Documentation Completeness",
        description="Providers of high-risk AI systems must maintain technical documentation "
                    "including: system architecture, training data description, performance "
                    "metrics, and test results. Must be available to national authorities.",
        severity=ControlSeverity.MEDIUM,
        category="Documentation",
        telecom_vector="Undocumented AI routing optimization without performance benchmarks",
        check=_check_transparency_documentation,
        evidence_hint="Verify technical documentation file and model card completeness",
        remediation_hint="Create AI system model card documenting: architecture, dataset, "
                         "accuracy metrics, bias testing results, and deployment constraints. "
                         "Version-control in git alongside routing configuration.",
        kamailio_module="N/A (documentation requirement)",
    ),
]
