"""
ISO/IEC 42001:2023 AI Management System — controls for IMS network twin.
Covers AI model governance, risk logging, data lineage, and change management.
"""
from __future__ import annotations
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_ai_governance_policy(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    if sbc:
        return ControlStatus.PARTIAL if not sbc.config.get("ai_governance") else ControlStatus.COMPLIANT
    return ControlStatus.PARTIAL


def _check_risk_logging_pipeline(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault or 'ai_drift' in fault:
        return ControlStatus.NON_COMPLIANT
    # Log-based: explicit evidence that risk pipeline is absent
    no_pipeline = [l for l in logs if any(kw in l for kw in
                   ["NO risk event emitted", "NO ALERT", "NOT CONFIGURED", "VIOLATION"])]
    if no_pipeline:
        return ControlStatus.NON_COMPLIANT
    risk_logs = [l for l in logs if any(kw in l.lower() for kw in
                 ["risk-event", "risk-score", "anomaly", "threshold-breach"])]
    if not risk_logs and logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_data_lineage(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    lineage_logs = [l for l in logs if any(kw in l.lower() for kw in
                    ["lineage", "data-source", "pipeline-id", "input-hash"])]
    if not lineage_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_model_change_management(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'unlogged_ai' in fault:
        return ControlStatus.NON_COMPLIANT
    change_logs = [l for l in logs if any(kw in l.lower() for kw in
                   ["model-update", "model-version", "change-approval", "rollback"])]
    if not change_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_performance_monitoring(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    perf_logs = [l for l in logs if any(kw in l.lower() for kw in
                 ["kpi", "latency", "accuracy", "p99", "asr", "mos-score"])]
    if not perf_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_incident_response(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    incident_id = getattr(twin, 'incident_id', None)
    if fault and not incident_id:
        return ControlStatus.NON_COMPLIANT
    response_logs = [l for l in logs if any(kw in l.lower() for kw in
                     ["incident", "escalation", "remediation-started", "ticket"])]
    if not response_logs and fault:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


ISO_42001_CONTROLS: list = [
    ComplianceControl(
        id="ISO42-GOV-001",
        name="AI Governance Policy and Accountability",
        description="Organization must establish a formal AI governance policy defining "
                    "roles, responsibilities, and accountability for AI systems used in "
                    "IMS network management. Documented senior-level ownership required.",
        severity=ControlSeverity.HIGH,
        category="Governance",
        telecom_vector="AI routing optimization without designated responsible officer",
        check=_check_ai_governance_policy,
        evidence_hint="Verify ai_governance config block and responsible officer assignment",
        remediation_hint="Define RACI matrix for AI routing system. Assign AI System Owner. "
                         "Document in ISMS policy and link to SBC configuration change process.",
        kamailio_module="N/A (organizational requirement)",
    ),
    ComplianceControl(
        id="ISO42-GOV-002",
        name="AI Risk Logging Pipeline",
        description="All AI-driven decisions affecting network traffic routing must emit "
                    "structured risk events to a tamper-evident log pipeline with severity "
                    "classification and threshold-breach alerting.",
        severity=ControlSeverity.CRITICAL,
        category="Risk Management",
        telecom_vector="Opaque routing AI with no risk-event emission or anomaly detection",
        check=_check_risk_logging_pipeline,
        evidence_hint="Check for risk-event, anomaly, threshold-breach entries in logs",
        remediation_hint="Instrument routing agent with risk event emitter. "
                         "Emit JSON risk events: {ts, event_type, severity, context, action}. "
                         "Ship to ELK stack or OpenSearch via syslog. "
                         "Set threshold alerts in Grafana for anomaly scores >0.8.",
        kamailio_module="xlog, statistics",
    ),
    ComplianceControl(
        id="ISO42-GOV-003",
        name="Data Lineage Audit for Network Twin",
        description="All data inputs to AI routing models (CDRs, KPI metrics, SIP traces) "
                    "must have traceable lineage from source to model input. "
                    "Data provenance must be logged with each AI decision.",
        severity=ControlSeverity.HIGH,
        category="Data Governance",
        telecom_vector="AI model ingesting SBC KPIs without data-source lineage tracking",
        check=_check_data_lineage,
        evidence_hint="Check for lineage, data-source, input-hash in decision audit logs",
        remediation_hint="Tag each model inference call with: data_source_id, collection_ts, "
                         "pipeline_version, feature_hash. Store in append-only audit table. "
                         "Implement Apache Atlas or OpenLineage for data lineage tracking.",
        kamailio_module="N/A (data pipeline requirement)",
    ),
    ComplianceControl(
        id="ISO42-GOV-004",
        name="AI Model Change Management",
        description="Updates to AI routing models must follow formal change management: "
                    "approval workflow, staged rollout, rollback capability, and post-deploy "
                    "validation. Emergency changes require retrospective review within 24h.",
        severity=ControlSeverity.HIGH,
        category="Change Management",
        telecom_vector="Silent AI model update changing Kamailio dispatcher weights without review",
        check=_check_model_change_management,
        evidence_hint="Check model-update, change-approval, rollback entries in logs",
        remediation_hint="Implement GitOps workflow for model deployments. "
                         "Require PR approval for routing policy changes. "
                         "Use feature flags: deploy new model to 10% traffic before full rollout. "
                         "Maintain model version registry with rollback artifact.",
        kamailio_module="dispatcher (weight management)",
    ),
    ComplianceControl(
        id="ISO42-GOV-005",
        name="AI System Performance Monitoring",
        description="AI routing system performance must be continuously monitored against "
                    "defined KPIs: call setup success rate, routing latency (P99), "
                    "and decision accuracy. Degradation triggers automatic fallback.",
        severity=ControlSeverity.MEDIUM,
        category="Performance",
        telecom_vector="No KPI monitoring for AI-driven routing decisions affecting call quality",
        check=_check_performance_monitoring,
        evidence_hint="Check for kpi, latency, asr, mos-score monitoring log entries",
        remediation_hint="Expose Prometheus metrics: ai_routing_latency_p99, "
                         "ai_routing_success_rate, ai_model_confidence. "
                         "Set Grafana alerts: if asr < 95% for 5min, revert to static routing.",
        kamailio_module="statistics, N/A (metrics pipeline)",
    ),
    ComplianceControl(
        id="ISO42-GOV-006",
        name="AI Incident Response Plan",
        description="A documented incident response plan for AI system failures must exist, "
                    "including: detection criteria, escalation path, containment actions, "
                    "and root cause analysis process. Response SLA: P1 within 1 hour.",
        severity=ControlSeverity.MEDIUM,
        category="Incident Response",
        telecom_vector="AI routing failure with no incident ticket or escalation evidence",
        check=_check_incident_response,
        evidence_hint="Verify incident ID generation, escalation logs, and response timeline",
        remediation_hint="Define AI incident runbook with decision tree. "
                         "Integrate with NOC ticketing system. "
                         "Automatic ticket creation when AI routing anomaly detected. "
                         "P1 SLA: human override capability within 1 hour of detection.",
        kamailio_module="N/A (operational requirement)",
    ),
]
