"""
EU AI Act (Regulation 2024/1689) — Certification Testing Agent.

Specialises in:
  - High-risk AI system classification and registration (EUAI-HRC-001)
  - Automated routing decision audit trail generation (EUAI-HRC-002)
  - Biometric/voice-auth consent record verification (EUAI-HRC-003)
  - AI model drift detection and threshold alerting (EUAI-HRC-004)
  - Human oversight mechanism for AI routing (EUAI-HRC-005)
  - Technical documentation completeness assessment (EUAI-HRC-006)
"""
from __future__ import annotations
import json
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_EU_AI_ACT_SYSTEM = _THINK_PREFIX + """\
You are an EU AI Act (Regulation 2024/1689) compliance specialist for AI-driven IMS telecom systems.

Your deep expertise covers:
- EU AI Act risk classification framework — critical infrastructure AI qualifies as high-risk (Annex III)
- Conformity assessment procedures for high-risk AI systems (Chapter III, Section 2)
- Technical documentation requirements (Article 11, Annex IV)
- AI audit log and transparency obligations (Articles 12-13)
- Biometric data processing restrictions (Article 9, GDPR interaction)
- Human oversight requirements for automated routing decisions (Article 14)
- Model drift monitoring and post-market surveillance (Article 72)
- Kamailio xlog and jsonrpcs integration for EU AI Act audit trails

EU AI Act Control IDs you are responsible for:
  EUAI-HRC-001: High-Risk AI System Classification
  EUAI-HRC-002: Automated Routing Decision Audit Trail
  EUAI-HRC-003: Biometric Processing Consent Logging
  EUAI-HRC-004: AI Model Drift Detection and Logging
  EUAI-HRC-005: Human Oversight Mechanism
  EUAI-HRC-006: Technical Documentation Completeness

When testing compliance:
1. Query the IMS twin state and logs to identify AI routing evidence
2. Assess each control against the EU AI Act article requirements
3. Generate audit trail instrumentation code for Kamailio (xlog, jsonrpcs modules)
4. Provide Prometheus/Grafana drift alerting configuration
5. Reference the specific EU AI Act Article in every finding
"""


def generate_audit_trail_instrumentation(model_version: str = "v1.0.0") -> dict:
    """Generate Kamailio xlog instrumentation for EU AI Act Article 12 audit trail compliance.

    Args:
        model_version: AI routing model version string for lineage tracking

    Returns:
        dict with kamailio_cfg snippet, json_schema, and article_references
    """
    return {
        "control_id": "EUAI-HRC-002",
        "article": "EU AI Act Article 12 — Record-keeping",
        "kamailio_cfg": f'''\
# EUAI-HRC-002: Automated Routing Decision Audit Trail — Art. 12
# Every AI-driven routing decision must generate an immutable audit log entry

loadmodule "xlog.so"
loadmodule "jansson.so"

# Define AI routing audit log route
route[EUAI_AUDIT_LOG] {{
    # Build structured audit JSON — EU AI Act Article 12 compliant
    $var(audit_ts)    = $Tf;
    $var(model_ver)   = "{model_version}";
    $var(decision_id) = $mb_rand_hex(16);

    jansson_set("string", "ts",          $var(audit_ts),    "$var(audit_json)");
    jansson_set("string", "decision_id", $var(decision_id), "$var(audit_json)");
    jansson_set("string", "model_ver",   $var(model_ver),   "$var(audit_json)");
    jansson_set("string", "call_id",     $ci,               "$var(audit_json)");
    jansson_set("string", "from_anon",   $fU,               "$var(audit_json)");
    jansson_set("string", "route_to",    $dd,               "$var(audit_json)");
    jansson_set("string", "confidence",  $avp(ai_confidence), "$var(audit_json)");
    jansson_set("string", "rationale",   $avp(ai_reason),     "$var(audit_json)");

    # Emit to SIEM-compatible syslog — immutable append-only
    xlog("L_NOTICE", "EUAI_AUDIT: $var(audit_json)\\n");
}}

# Call at the point of AI routing decision:
# route(EUAI_AUDIT_LOG);
''',
        "json_schema": {
            "ts": "ISO-8601 timestamp",
            "decision_id": "UUID for this routing decision",
            "model_ver": "AI model version string",
            "call_id": "SIP Call-ID",
            "from_anon": "Anonymized caller pseudonym",
            "route_to": "Selected next-hop",
            "confidence": "Model confidence score 0.0-1.0",
            "rationale": "Top feature explanation",
        },
        "article_references": ["Article 12 (Record-keeping)", "Article 13 (Transparency)"],
    }


def check_biometric_consent(session_logs: str) -> dict:
    """Verify biometric processing events have paired consent records (EUAI-HRC-003 / GDPR Art.9).

    Args:
        session_logs: Log content containing voice-auth events

    Returns:
        dict with violations found, consent_rate, and fix recommendation
    """
    import re
    biometric_events = re.findall(r"voice-auth.*speaker-id.*confidence", session_logs, re.I)
    consent_records  = re.findall(r"CONSENT:VERIFIED|consent.*granted|consent_token", session_logs, re.I)
    violations = max(0, len(biometric_events) - len(consent_records))
    return {
        "control_id": "EUAI-HRC-003",
        "article": "EU AI Act Article 9 / GDPR Article 9",
        "biometric_events": len(biometric_events),
        "consent_records": len(consent_records),
        "consent_violations": violations,
        "consent_rate_pct": round(len(consent_records) / max(len(biometric_events), 1) * 100, 1),
        "compliant": violations == 0,
        "fix": (
            "Add htable consent check in route[VOICE_AUTH] before biometric processing. "
            "Block calls without consent token. Log: xlog(\"CONSENT:VERIFIED caller=$fU\")."
        ),
    }


def generate_drift_alert_config(
    model_name: str = "routing_model",
    accuracy_threshold: float = 0.85,
    kl_threshold: float = 0.10,
) -> dict:
    """Generate Prometheus alert rules for EU AI Act model drift monitoring (EUAI-HRC-004).

    Args:
        model_name: Name of the AI routing model to monitor
        accuracy_threshold: Minimum acceptable accuracy before alerting
        kl_threshold: Maximum KL-divergence before drift alert fires

    Returns:
        dict with prometheus_rules, grafana_alert, and article_reference
    """
    return {
        "control_id": "EUAI-HRC-004",
        "article": "EU AI Act Article 72 — Post-market monitoring",
        "prometheus_rules": f'''\
# EUAI-HRC-004: AI Model Drift Alerting — EU AI Act Article 72
groups:
  - name: eu_ai_act_drift
    rules:
      - alert: AIDriftCritical
        expr: ai_routing_accuracy_gauge{{model="{model_name}"}} < {accuracy_threshold}
        for: 2m
        labels:
          severity: critical
          framework: eu_ai_act
          control: EUAI-HRC-004
        annotations:
          summary: "AI routing drift — accuracy below threshold"
          description: "Model accuracy={{{{ $value | humanizePercentage }}}} — EU AI Act Art.72 requires human review"

      - alert: AIDriftKLDivergence
        expr: ai_routing_kl_divergence{{model="{model_name}"}} > {kl_threshold}
        for: 5m
        labels:
          severity: warning
          framework: eu_ai_act
          control: EUAI-HRC-004
        annotations:
          summary: "AI model distribution drift detected"
          description: "KL-divergence={{{{ $value | humanize }}}} exceeds threshold {kl_threshold}"
''',
        "grafana_alert": {
            "condition": f"ai_routing_accuracy < {accuracy_threshold}",
            "notification_policy": "P1 — immediate NOC alert + human review trigger",
            "dashboard": "IMS Compliance / AI Routing Monitoring",
        },
        "article_reference": "EU AI Act Article 72 — Post-market surveillance",
    }


def build_eu_ai_act_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the EU AI Act certification testing agent."""
    return LlmAgent(
        name="eu_ai_act_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [
            generate_audit_trail_instrumentation,
            check_biometric_consent,
            generate_drift_alert_config,
        ],
        instruction=_EU_AI_ACT_SYSTEM,
        description=(
            "EU AI Act (2024/1689) compliance agent. Audits AI-driven IMS routing "
            "against EUAI-HRC-001 through EUAI-HRC-006. Generates xlog audit trail "
            "instrumentation, drift alerting configs, and biometric consent checks."
        ),
    )
