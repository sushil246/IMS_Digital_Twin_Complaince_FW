"""
ISO/IEC 42001:2023 AI Management System — Certification Testing Agent.

Specialises in:
  - AI governance policy assessment (ISO42-GOV-001)
  - Risk logging pipeline design and audit (ISO42-GOV-002)
  - Data lineage tracking for network twin inputs (ISO42-GOV-003)
  - Model change management with GitOps (ISO42-GOV-004)
  - Performance KPI monitoring pipeline (ISO42-GOV-005)
  - Incident response plan assessment (ISO42-GOV-006)
"""
from __future__ import annotations
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_ISO_42001_SYSTEM = _THINK_PREFIX + """\
You are an ISO/IEC 42001:2023 AI Management System (AIMS) lead auditor for IMS telecom networks.

Your deep expertise covers:
- ISO 42001 Annex A controls — all 38 controls across 9 categories
- AI governance structures: responsible officer assignment, RACI matrix for AI systems
- Risk management for AI: risk identification, treatment, logging, and monitoring
- Data governance: data quality, lineage, provenance tracking for ML training and inference
- AI system change management: GitOps workflow, staged rollout, rollback procedures
- Performance monitoring: KPI definition, SLA tracking, drift correlation
- Incident response: AI-specific runbooks, escalation paths, MTTR targets

ISO 42001 Control IDs you are responsible for:
  ISO42-GOV-001: AI Governance Policy and Accountability
  ISO42-GOV-002: AI Risk Logging Pipeline
  ISO42-GOV-003: Data Lineage Audit for Network Twin
  ISO42-GOV-004: AI Model Change Management
  ISO42-GOV-005: AI System Performance Monitoring
  ISO42-GOV-006: AI Incident Response Plan

When certifying:
1. Query the digital twin and logs to assess AI governance maturity
2. Map each gap to specific ISO 42001 Annex A controls
3. Generate practical remediation artifacts (config, schemas, runbooks)
4. Provide Clause references (ISO 42001 Clause X.Y) in every finding
5. Produce a certification-readiness score with identified improvement areas
"""


def generate_risk_log_schema() -> dict:
    """Generate a structured risk event schema for ISO 42001 Clause 6.1 risk logging pipeline.

    Returns:
        dict with json_schema, syslog_format, and sample_event for implementing the pipeline
    """
    return {
        "control_id": "ISO42-GOV-002",
        "clause": "ISO 42001 Clause 6.1 — Actions to address risks and opportunities",
        "json_schema": {
            "risk_event_id": "UUID — unique identifier for this risk event",
            "timestamp": "ISO-8601 UTC timestamp",
            "event_type": "ENUM: routing_anomaly | model_drift | constraint_violation | data_quality",
            "severity": "ENUM: INFO | LOW | MEDIUM | HIGH | CRITICAL",
            "ai_system_id": "Identifier for the AI system emitting this event",
            "model_version": "Semantic version of active model",
            "decision_id": "Reference to routing decision that triggered this event",
            "risk_score": "Float 0.0-1.0 — normalized risk magnitude",
            "context": "Dict — event-specific diagnostic data",
            "treatment_applied": "String — automated mitigation action taken",
            "human_review_required": "Boolean — escalate to NOC if true",
        },
        "syslog_format": (
            "PRIORITY: LOG_NOTICE | FACILITY: LOG_USER\n"
            "TAG: iso42001_risk\n"
            "MSG: {json.dumps(risk_event)}"
        ),
        "sample_event": {
            "risk_event_id": "re-550e8400-e29b",
            "timestamp": "2026-06-09T20:00:00Z",
            "event_type": "model_drift",
            "severity": "HIGH",
            "ai_system_id": "routing-optimizer-v3",
            "model_version": "v3.1.0",
            "decision_id": "d-7f3b2a1",
            "risk_score": 0.78,
            "context": {"accuracy_delta": -0.22, "kl_divergence": 0.34},
            "treatment_applied": "fallback_to_static_routing",
            "human_review_required": True,
        },
        "kamailio_integration": '''\
# ISO42-GOV-002: Risk Event Emission from Kamailio
# Emit structured risk event when routing anomaly detected
route[ISO42_RISK_LOG] {
    jansson_set("string", "event_type", "routing_anomaly", "$var(risk_json)");
    jansson_set("string", "model_version", $avp(model_ver), "$var(risk_json)");
    jansson_set("string", "decision_id", $avp(decision_id), "$var(risk_json)");
    jansson_set("number", "risk_score", $avp(risk_score), "$var(risk_json)");
    xlog("L_NOTICE", "ISO42001_RISK: $var(risk_json)\\n");
}
''',
    }


def generate_data_lineage_config() -> dict:
    """Generate data lineage tracking configuration for ISO 42001 Clause 8.4 (ISO42-GOV-003).

    Returns:
        dict with lineage_schema, pipeline_config, and OpenLineage integration details
    """
    return {
        "control_id": "ISO42-GOV-003",
        "clause": "ISO 42001 Clause 8.4 — Data for AI systems",
        "lineage_schema": {
            "lineage_id": "UUID — unique per data snapshot",
            "source_id": "Data source identifier (e.g., sbc01_kpi_stream)",
            "collection_ts": "Timestamp of data collection",
            "pipeline_version": "Version of data pipeline that produced this snapshot",
            "feature_hash": "SHA-256 of feature vector — ensures reproducibility",
            "model_input_hash": "Hash of actual model input tensor",
            "record_count": "Number of records in this batch",
        },
        "openlineage_facet": {
            "job": {"name": "ims_routing_feature_extraction", "namespace": "ims_compliance"},
            "inputs": [{"namespace": "ims_sbc", "name": "sbc01_kpi_metrics"}],
            "outputs": [{"namespace": "ims_routing_ai", "name": "routing_feature_vectors"}],
        },
        "kamailio_integration": '''\
# ISO42-GOV-003: Tag each AI decision with data lineage ID
route[ISO42_LINEAGE_TAG] {
    $avp(lineage_id) = $mb_rand_hex(16);
    xlog("L_INFO", "ISO42_LINEAGE: decision=$avp(decision_id) lineage=$avp(lineage_id) src=sbc01_kpi\\n");
}
''',
    }


def assess_change_management_maturity(change_logs: str) -> dict:
    """Assess AI model change management maturity against ISO 42001 Clause 8.6 (ISO42-GOV-004).

    Args:
        change_logs: Log content showing model update history

    Returns:
        dict with maturity_level (1-5), gaps, and recommendations
    """
    import re
    approvals = re.findall(r"change-approval|change_approved|approved_by", change_logs, re.I)
    versions = re.findall(r"model.version|model-update|v\d+\.\d+\.\d+", change_logs, re.I)
    rollbacks = re.findall(r"rollback|revert", change_logs, re.I)
    silent_changes = re.findall(r"silent|no audit|no version tag", change_logs, re.I)

    maturity = 1
    if versions: maturity += 1
    if approvals: maturity += 1
    if rollbacks: maturity += 1
    if not silent_changes: maturity += 1

    return {
        "control_id": "ISO42-GOV-004",
        "clause": "ISO 42001 Clause 8.6 — Change management",
        "maturity_level": maturity,
        "maturity_description": {
            1: "Ad-hoc — no change process", 2: "Version-tracked only",
            3: "Approved changes with history", 4: "Full change + rollback",
            5: "Full GitOps with automated validation",
        }[maturity],
        "approvals_found": len(approvals),
        "versions_found": len(versions),
        "rollback_capability": len(rollbacks) > 0,
        "silent_changes_detected": len(silent_changes) > 0,
        "gaps": [
            "No approval workflow for model changes" if not approvals else None,
            "No rollback capability" if not rollbacks else None,
            "Silent model changes detected — violates ISO42-GOV-004" if silent_changes else None,
        ],
        "recommendation": "Implement GitOps with branch protection, PR reviews, and automated rollback",
    }


def build_iso_42001_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the ISO 42001 certification testing agent."""
    return LlmAgent(
        name="iso_42001_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [
            generate_risk_log_schema,
            generate_data_lineage_config,
            assess_change_management_maturity,
        ],
        instruction=_ISO_42001_SYSTEM,
        description=(
            "ISO/IEC 42001:2023 AIMS certification agent. Audits AI governance, "
            "risk logging, data lineage, and change management against "
            "ISO42-GOV-001 through ISO42-GOV-006 with Clause references."
        ),
    )
