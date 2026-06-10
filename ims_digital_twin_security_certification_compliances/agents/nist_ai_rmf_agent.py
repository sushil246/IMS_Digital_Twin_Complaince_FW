"""
NIST AI Risk Management Framework 1.0 — Certification Testing Agent.

Specialises in:
  - AI trustworthiness metrics instrumentation (NIST-GOVERN-001)
  - Adversarial prompt/header injection defense for SIP routing AI (NIST-MAP-001)
  - System explainability and per-decision logging (NIST-MEASURE-001)
  - Risk context identification for emergency call routing (NIST-MAP-002)
  - AI incident detection and automated response (NIST-MANAGE-001)
  - Bias and fairness metrics across subscriber segments (NIST-MEASURE-002)
"""
from __future__ import annotations
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_NIST_AI_RMF_SYSTEM = _THINK_PREFIX + """\
You are a NIST AI Risk Management Framework (AI RMF 1.0) practitioner for critical telecom AI systems.

Your deep expertise covers:
- All four NIST AI RMF core functions: GOVERN, MAP, MEASURE, MANAGE
- Trustworthiness dimensions: accuracy, reliability, safety, security, explainability, privacy, fairness
- Adversarial ML attack surfaces in telecom: SIP header injection, prompt injection, data poisoning
- Explainability techniques: LIME, SHAP applied to routing model decisions
- Emergency services routing bypass: 112/911 hardcoding in Kamailio to guarantee safety
- NIST AI RMF Profile construction for telecom operators
- Integration with NIST SP 800-218A for AI system security

NIST AI RMF Control IDs you are responsible for:
  NIST-GOVERN-001: AI Trustworthiness Metrics Definition
  NIST-MAP-001: Adversarial Prompt-Injection Defense
  NIST-MEASURE-001: System Explainability and Decision Logging
  NIST-MAP-002: AI Risk Context Identification
  NIST-MANAGE-001: AI Incident Detection and Response
  NIST-MEASURE-002: Bias and Fairness Monitoring

When assessing:
1. Query twin and logs to identify AI trustworthiness gaps
2. Map findings to the four NIST RMF functions (GOVERN/MAP/MEASURE/MANAGE)
3. Generate defensive Kamailio configuration — especially for adversarial input protection
4. Provide SHAP/LIME explainability integration patterns for the routing model
5. Cite specific NIST AI RMF categories (e.g., GOVERN 1.2, MAP 2.1, MEASURE 4.1)
"""


def generate_adversarial_defense_config() -> dict:
    """Generate Kamailio sanity check + header sanitization config to defend against
    adversarial SIP header injection attacks targeting AI routing models (NIST-MAP-001).

    Returns:
        dict with kamailio_cfg, threat_model, and NIST function reference
    """
    return {
        "control_id": "NIST-MAP-001",
        "nist_function": "MAP",
        "nist_category": "MAP 2.3 — Scientific findings and risk context",
        "threat_model": {
            "attack_vector": "Crafted SIP headers (X-Route-Override, X-AI-Directive) targeting routing AI",
            "attack_impact": "Adversary can redirect calls, bypass authentication, manipulate routing weights",
            "attacker_capability": "External attacker with SIP access to the IMS proxy",
        },
        "kamailio_cfg": '''\
# NIST-MAP-001: Adversarial SIP Header Injection Defense
# Strip untrusted AI-directive headers and validate SIP structure

loadmodule "sanity.so"
loadmodule "textopsx.so"

# Sanity check configuration
modparam("sanity", "default_checks", 17895)  # All default checks enabled
modparam("sanity", "uri_checks", 3)

route[NIST_ADVERSARIAL_DEFENSE] {
    # Step 1: Structural SIP validation — reject malformed messages
    if(!sanity_check()) {
        xlog("L_WARN", "NIST-MAP-001: Malformed SIP message from $si — rejecting\\n");
        sl_send_reply(400, "Bad Request — SIP Sanity Failed");
        exit;
    }

    # Step 2: Strip adversarial AI-directive headers from untrusted sources
    if(!is_trusted()) {
        remove_hf("X-Route-Override");
        remove_hf("X-AI-Directive");
        remove_hf("X-Route-Hint");
        remove_hf("X-Routing-Weight");
        xlog("L_INFO", "NIST-MAP-001: Stripped AI-directive headers from untrusted $si\\n");
    }

    # Step 3: Validate Via and Contact against expected patterns
    if(!check_via_address("trusted_networks")) {
        xlog("L_WARN", "NIST-MAP-001: Unexpected Via address $si — logging for review\\n");
    }
}

# Emergency bypass — NEVER route emergency calls through AI model
route[EMERGENCY_BYPASS] {
    if($rU =~ "^(112|911|999|933)$") {
        xlog("L_NOTICE", "NIST-MAP-002: Emergency call $rU — bypassing AI routing\\n");
        route(STATIC_EMERGENCY_ROUTE);
        exit;
    }
}
''',
        "verification": [
            "Send INVITE with X-AI-Directive header from untrusted IP — verify header stripped",
            "Send malformed SIP (missing Via) — verify 400 Bad Request returned",
            "Send 112 call — verify routes to emergency server without AI routing",
            "Monitor: grep 'NIST-MAP-001' /var/log/kamailio.log",
        ],
    }


def generate_explainability_schema() -> dict:
    """Generate SHAP-based explainability logging schema for AI routing decisions (NIST-MEASURE-001).

    Returns:
        dict with schema, kamailio_integration, and NIST category reference
    """
    return {
        "control_id": "NIST-MEASURE-001",
        "nist_function": "MEASURE",
        "nist_category": "MEASURE 2.6 — Explainability and interpretability",
        "explanation_schema": {
            "decision_id": "UUID",
            "timestamp": "ISO-8601",
            "model_version": "string",
            "input_call_id": "SIP Call-ID",
            "routing_decision": "selected next-hop",
            "top_features": [
                {"feature": "sbc01_cpu_pct", "value": 0.87, "shap_value": 0.42},
                {"feature": "pcscf01_active_sessions", "value": 4200, "shap_value": 0.31},
                {"feature": "hour_of_day", "value": 14, "shap_value": 0.12},
            ],
            "confidence_score": 0.91,
            "alternative_routes": ["pcscf02 (conf=0.67)", "pcscf03 (conf=0.41)"],
        },
        "kamailio_integration": '''\
# NIST-MEASURE-001: Explainability log per routing decision
route[NIST_EXPLAIN_LOG] {
    # AVP ai_top_feature_1, ai_top_feature_2 set by AI routing module
    xlog("L_NOTICE",
        "NIST_EXPLAIN: decision=$avp(decision_id) "
        "route=$dd conf=$avp(ai_confidence) "
        "top_feat1=$avp(ai_top_feat1):$avp(ai_shap_1) "
        "top_feat2=$avp(ai_top_feat2):$avp(ai_shap_2) "
        "rationale=$avp(ai_rationale)\\n");
}
''',
    }


def assess_trustworthiness_metrics(telemetry_context: str) -> dict:
    """Assess whether AI routing system exposes the NIST trustworthiness dimensions (NIST-GOVERN-001).

    Args:
        telemetry_context: Telemetry/log content showing AI system instrumentation

    Returns:
        dict with trustworthiness scorecard per dimension
    """
    import re
    dimensions = {
        "accuracy": bool(re.search(r"accuracy|asr|success.rate", telemetry_context, re.I)),
        "reliability": bool(re.search(r"reliability|uptime|availability", telemetry_context, re.I)),
        "safety": bool(re.search(r"emergency|112|911|safety.bypass", telemetry_context, re.I)),
        "security": bool(re.search(r"sanity|acl|trusted|auth", telemetry_context, re.I)),
        "explainability": bool(re.search(r"reason|rationale|shap|feature.importance", telemetry_context, re.I)),
        "privacy": bool(re.search(r"anon|pseudonym|pii.mask", telemetry_context, re.I)),
        "fairness": bool(re.search(r"fair|gini|bias|allocation.equal", telemetry_context, re.I)),
    }
    score = sum(dimensions.values()) / len(dimensions) * 100
    return {
        "control_id": "NIST-GOVERN-001",
        "nist_category": "GOVERN 1.1 — Policies, processes, procedures",
        "trustworthiness_scorecard": dimensions,
        "overall_score_pct": round(score, 1),
        "missing_dimensions": [k for k, v in dimensions.items() if not v],
        "recommendation": f"Instrument the {sum(not v for v in dimensions.values())} missing dimensions",
    }


def build_nist_ai_rmf_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the NIST AI RMF certification testing agent."""
    return LlmAgent(
        name="nist_ai_rmf_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [
            generate_adversarial_defense_config,
            generate_explainability_schema,
            assess_trustworthiness_metrics,
        ],
        instruction=_NIST_AI_RMF_SYSTEM,
        description=(
            "NIST AI RMF 1.0 certification agent. Audits AI trustworthiness, "
            "adversarial defense, explainability, and fairness against "
            "NIST-GOVERN-001 through NIST-MEASURE-002. Generates sanity module "
            "Kamailio configs and SHAP explainability schemas."
        ),
    )
