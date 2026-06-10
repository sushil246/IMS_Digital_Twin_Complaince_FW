"""
OECD AI Principles — Certification Testing Agent.

Specialises in:
  - Transparency of automated calling logic and routing policies (OECD-TRANS-001)
  - Accountability trace completeness for all routing changes (OECD-ACCNT-001)
  - Fair resource allocation verification across subscriber groups (OECD-FAIR-001)
  - Safety by design: fail-safe routing, bounded action space (OECD-SAFE-001)
  - Privacy by design: MSISDN pseudonymization in AI routing (OECD-PRIV-001)
"""
from __future__ import annotations
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_OECD_AI_SYSTEM = _THINK_PREFIX + """\
You are an OECD AI Principles compliance assessor specializing in AI transparency,
accountability, fairness, and safety for automated telecom call routing systems.

Your deep expertise covers:
- OECD AI Principles 1.1-1.5: inclusive growth, human-centred, transparent, robust, accountable
- Transparency mechanisms for routing AI: X-Routing-Policy headers, decision logs
- Accountability architecture: immutable audit chains, operator attribution, approval tokens
- Fair resource allocation: weighted fair queuing, Gini coefficient monitoring
- Safety by design: fail-safe defaults, fail-open risks, graceful degradation patterns
- Privacy engineering: data minimization, pseudonymization, purpose limitation for call routing
- Kamailio append_hf, xlog, dialog modules for OECD compliance implementation

OECD AI Control IDs you are responsible for:
  OECD-TRANS-001: Transparency of Automated Calling Logic
  OECD-ACCNT-001: Accountability Trace Completeness
  OECD-FAIR-001: Fair Resource Allocation Verification
  OECD-SAFE-001: Safety by Design in AI Routing
  OECD-PRIV-001: Privacy by Design in Call Routing

When assessing:
1. Query the IMS twin for routing policy and log patterns
2. Evaluate each OECD principle against evidence in logs and configuration
3. Generate Kamailio transparency headers and accountability log configurations
4. Provide fairness analysis methodology with Gini coefficient calculation
5. Reference the specific OECD AI Principle (1.1-1.5) in each finding
"""


def generate_transparency_headers_config() -> dict:
    """Generate Kamailio config to add transparency headers to SIP INVITE responses (OECD-TRANS-001).

    Returns:
        dict with kamailio_cfg and explanation of OECD Principle 1.3 compliance
    """
    return {
        "control_id": "OECD-TRANS-001",
        "oecd_principle": "1.3 — Transparency and explainability",
        "kamailio_cfg": '''\
# OECD-TRANS-001: Routing Transparency Headers — OECD Principle 1.3

loadmodule "textopsx.so"

route[OECD_TRANSPARENCY] {
    # Add routing transparency header — OECD Principle 1.3
    append_hf("X-Routing-Policy: ai-load-balance/v$avp(model_ver)\\r\\n");
    append_hf("X-Route-Via: $dd\\r\\n");
    append_hf("X-Route-Reason: $avp(ai_rationale)\\r\\n");

    # Log routing decision with human-readable reason
    xlog("L_NOTICE",
        "OECD_TRANS: call_id=$ci route=$dd policy=ai-load-balance "
        "reason=$avp(ai_rationale) conf=$avp(ai_confidence)\\n");
}
''',
        "oecd_compliance": {
            "principle_1.3_met": True,
            "transparency_mechanism": "X-Routing-Policy SIP header + structured xlog entry",
            "human_readable": True,
            "machine_readable": True,
        },
        "verification": [
            "Send INVITE — inspect response for X-Routing-Policy header",
            "Verify: sipsak -v -u sip:test@ims.lab | grep X-Routing-Policy",
            "Check logs: grep 'OECD_TRANS:' /var/log/kamailio.log | tail -10",
        ],
    }


def generate_accountability_log_config() -> dict:
    """Generate immutable accountability trace configuration for OECD-ACCNT-001.

    Returns:
        dict with schema, kamailio_cfg, and OECD Principle 1.4 reference
    """
    return {
        "control_id": "OECD-ACCNT-001",
        "oecd_principle": "1.4 — Robustness, security, and safety / 1.5 — Accountability",
        "accountability_schema": {
            "event_id": "UUID",
            "timestamp": "ISO-8601",
            "policy_id": "routing policy identifier",
            "model_version": "AI model semantic version",
            "operator_id": "NOC operator who authorized the policy (if applicable)",
            "approval_token": "Change management approval reference",
            "routing_outcome": "ENUM: routed | rejected | fallback",
            "call_id": "SIP Call-ID",
        },
        "kamailio_cfg": '''\
# OECD-ACCNT-001: Accountability Trace — OECD Principle 1.5

route[OECD_ACCOUNTABILITY] {
    # Build accountability record
    $var(acc_id) = $mb_rand_hex(16);

    xlog("L_NOTICE",
        "OECD_ACCNT: acc_id=$var(acc_id) ts=$Tf "
        "policy_id=$avp(policy_id) model_ver=$avp(model_ver) "
        "operator=$avp(operator_id) approval=$avp(approval_token) "
        "outcome=routed call_id=$ci\\n");
}
''',
        "storage_requirement": "Append-only log — use rsyslog imfile with immutable flag or QLDB",
    }


def check_fair_allocation(session_stats_context: str) -> dict:
    """Analyze call routing for fair resource allocation across subscriber segments (OECD-FAIR-001).

    Args:
        session_stats_context: Routing statistics showing session distribution

    Returns:
        dict with gini_estimate, fairness_gaps, and rebalancing recommendation
    """
    import re
    # Try to extract session counts per subnet/segment from log context
    segment_re = re.findall(r"subnet[=:\s]+(\S+).*?sessions[=:\s]+(\d+)", session_stats_context, re.I)
    if not segment_re:
        return {
            "control_id": "OECD-FAIR-001",
            "oecd_principle": "1.1 — Inclusive growth, sustainable development, and well-being",
            "fairness_data_available": False,
            "message": "No per-segment session statistics found — configure segment-level metrics",
            "recommendation": "Instrument per-subnet session counters: modparam('statistics', 'variable', 'subnet_sessions')",
        }

    counts = [int(c) for _, c in segment_re]
    n = len(counts)
    total = sum(counts)
    mean_sessions = total / n if n else 0
    gini = sum(abs(a - b) for a in counts for b in counts) / (2 * n * total) if total else 0

    return {
        "control_id": "OECD-FAIR-001",
        "oecd_principle": "1.1 — Inclusive growth",
        "fairness_data_available": True,
        "segment_count": n,
        "mean_sessions_per_segment": round(mean_sessions, 1),
        "gini_coefficient": round(gini, 3),
        "compliant": gini < 0.3,
        "fairness_assessment": "FAIR" if gini < 0.15 else "MODERATE" if gini < 0.3 else "UNFAIR",
        "recommendation": (
            "Implement weighted fair queuing in Kamailio dispatcher. "
            "Alert if Gini > 0.3 — indicates systematic routing bias."
        ) if gini >= 0.3 else "Allocation is within fair bounds",
    }


def build_oecd_ai_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the OECD AI Principles certification testing agent."""
    return LlmAgent(
        name="oecd_ai_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [
            generate_transparency_headers_config,
            generate_accountability_log_config,
            check_fair_allocation,
        ],
        instruction=_OECD_AI_SYSTEM,
        description=(
            "OECD AI Principles certification agent. Audits transparency, accountability, "
            "fairness, safety, and privacy of IMS routing AI against OECD-TRANS-001 "
            "through OECD-PRIV-001 with Principle 1.1-1.5 references."
        ),
    )
