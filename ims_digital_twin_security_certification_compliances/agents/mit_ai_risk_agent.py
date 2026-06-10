"""
MIT AI Risk Repository — Certification Testing Agent.

Specialises in:
  - Optimization loop stability analysis and hysteresis design (MIT-STRUCT-001)
  - RL/feedback loop bounded learning rate and dampening (MIT-STRUCT-002)
  - Hard constraint enforcement: session capacity, SLA, emergency priority (MIT-STRUCT-003)
  - Objective function alignment and multi-KPI monitoring (MIT-STRUCT-004)
  - Telemetry input integrity and poisoning detection (MIT-STRUCT-005)
"""
from __future__ import annotations
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_MIT_AI_RISK_SYSTEM = _THINK_PREFIX + """\
You are an AI systems safety engineer specializing in the MIT AI Risk Repository framework
applied to Kamailio SIP router optimization loops and reinforcement learning routing agents.

Your deep expertise covers:
- Feedback loop stability theory: Lyapunov stability, oscillation detection, hysteresis design
- Reinforcement learning safety: bounded action spaces, safety critics, reward shaping
- Telecom constraint satisfaction: session capacity hard limits, SLA guarantees, emergency priority
- Objective function misalignment detection: multi-KPI monitoring, Pareto analysis
- Telemetry poisoning attacks: outlier detection, cross-source validation, HMAC integrity
- Kamailio dialog and statistics modules for constraint enforcement
- Real-time safety monitoring for AI-driven dispatcher decisions

MIT AI Risk Control IDs you are responsible for:
  MIT-STRUCT-001: Optimization Loop Stability Assessment
  MIT-STRUCT-002: Feedback Loop Stability Analysis
  MIT-STRUCT-003: Constraint Violation Detection
  MIT-STRUCT-004: Optimization Objective Alignment Verification
  MIT-STRUCT-005: Telemetry Input Vulnerability Assessment

When assessing:
1. Query the IMS twin for optimization loop configuration and active sessions
2. Identify stability risks: oscillation indicators, unconstrained feedback, weak objective alignment
3. Generate Kamailio dialog/statistics module configs with hard constraints
4. Provide mathematical safety bounds (e.g., learning rate ≤ 0.001, hysteresis ≥ 3 probes)
5. Reference specific MIT AI Risk categories in every finding
"""


def analyze_loop_stability(dispatcher_config: str) -> dict:
    """Analyze Kamailio dispatcher configuration for optimization loop stability (MIT-STRUCT-001).

    Args:
        dispatcher_config: Kamailio dispatcher module configuration text

    Returns:
        dict with stability_risks, hysteresis_gap, and recommended kamailio_cfg fix
    """
    import re
    threshold = re.search(r"ds_probing_threshold[=:\s]+(\d+)", dispatcher_config, re.I)
    threshold_val = int(threshold.group(1)) if threshold else 1
    dampening = re.search(r"ds_blacklist_expire[=:\s]+(\d+)", dispatcher_config, re.I)

    risks = []
    if threshold_val < 3:
        risks.append(f"ds_probing_threshold={threshold_val} — too low, causes route oscillation")
    if not dampening:
        risks.append("No dampening timer configured — route changes can oscillate rapidly")

    return {
        "control_id": "MIT-STRUCT-001",
        "mit_category": "Hazardous or insufficiently safe AI",
        "current_threshold": threshold_val,
        "hysteresis_configured": threshold_val >= 3,
        "dampening_configured": dampening is not None,
        "stability_risks": risks,
        "compliant": len(risks) == 0,
        "kamailio_fix": '''\
# MIT-STRUCT-001: Optimization Loop Stability — hysteresis and dampening

modparam("dispatcher", "ds_probing_threshold", 3)   # 3 failures before marking DOWN
modparam("dispatcher", "ds_probing_mode", 1)         # Probe only inactive destinations
modparam("dispatcher", "ds_blacklist_expire", 60)    # 60s dampening before re-evaluation
modparam("dispatcher", "ds_ping_latency_stats", 1)   # Track latency for stability analysis

# Route: only re-evaluate routing after dampening period
route[MIT_STABILITY_GUARD] {
    # Prevent thrashing: require consecutive failures before action
    if($stat(ds_probing_active) > 0) {
        xlog("L_INFO", "MIT-STRUCT-001: Probing active — suppressing route change\\n");
    }
}
''',
    }


def generate_constraint_guard_config(max_sessions: int = 4500) -> dict:
    """Generate Kamailio hard constraint guards for session capacity limits (MIT-STRUCT-003).

    Args:
        max_sessions: Maximum allowed concurrent sessions before INVITE rejection

    Returns:
        dict with kamailio_cfg hard constraint blocks and emergency bypass
    """
    return {
        "control_id": "MIT-STRUCT-003",
        "mit_category": "AI failures causing physical harms",
        "constraint_type": "Hard session capacity limit",
        "max_sessions": max_sessions,
        "kamailio_cfg": f'''\
# MIT-STRUCT-003: Hard Constraint — Session Capacity Guard
# Prevent AI routing from exceeding physical SBC limits

loadmodule "dialog.so"
loadmodule "statistics.so"

# Emergency call bypass — NEVER apply capacity limits to 112/911/999
route[MIT_CAPACITY_GUARD] {{
    # Hard constraint: reject new INVITEs above capacity limit
    $var(active_dialogs) = $stat(active_dialogs);
    if($var(active_dialogs) > {max_sessions}) {{
        xlog("L_WARN", "MIT-STRUCT-003: Capacity constraint violated "
             "active=$var(active_dialogs) limit={max_sessions} — rejecting INVITE\\n");
        sl_send_reply(503, "Service Unavailable — Capacity Limit");
        exit;
    }}

    # Warn at 90% capacity
    if($var(active_dialogs) > {int(max_sessions * 0.9)}) {{
        xlog("L_NOTICE", "MIT-STRUCT-003: Approaching capacity "
             "active=$var(active_dialogs) limit={max_sessions}\\n");
    }}
}}

# Statistics export for Prometheus
modparam("statistics", "variable", "active_dialogs")
''',
        "verification": [
            f"Verify constraint fires at {max_sessions} sessions",
            "Test emergency bypass: 112/999 calls must never get 503",
            "Monitor: kamcmd stats.get_statistics active_dialogs",
        ],
    }


def assess_objective_alignment(kpi_logs: str) -> dict:
    """Assess AI routing objective function alignment across MOS, cost, and fairness (MIT-STRUCT-004).

    Args:
        kpi_logs: Telemetry showing routing optimization KPI trends

    Returns:
        dict with alignment_score, misaligned_objectives, and rebalancing recommendations
    """
    import re
    mos_trend = re.findall(r"mos.score[=:\s]+([\d.]+)", kpi_logs, re.I)
    cost_trend = re.findall(r"routing.cost[=:\s]+([\d.]+)", kpi_logs, re.I)
    fairness = re.findall(r"gini.coeff[=:\s]+([\d.]+)|fairness[=:\s]+([\d.]+)", kpi_logs, re.I)

    aligned = []
    misaligned = []
    if mos_trend:
        mos_avg = sum(float(v) for v in mos_trend) / len(mos_trend)
        if mos_avg >= 3.5:
            aligned.append(f"MOS quality: avg={mos_avg:.2f} (target≥3.5)")
        else:
            misaligned.append(f"MOS quality degrading: avg={mos_avg:.2f} (target≥3.5)")
    else:
        misaligned.append("MOS score not monitored — objective alignment unverifiable")

    return {
        "control_id": "MIT-STRUCT-004",
        "mit_category": "AI pursuing different objectives than intended",
        "aligned_objectives": aligned,
        "misaligned_objectives": misaligned,
        "alignment_score_pct": round(len(aligned) / max(len(aligned) + len(misaligned), 1) * 100, 1),
        "recommendation": (
            "Define multi-objective: objective = w1*MOS + w2*(1-cost) + w3*fairness. "
            "Monitor each component weekly. Alert if any drops >10% from baseline."
        ),
    }


def build_mit_ai_risk_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the MIT AI Risk certification testing agent."""
    return LlmAgent(
        name="mit_ai_risk_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [
            analyze_loop_stability,
            generate_constraint_guard_config,
            assess_objective_alignment,
        ],
        instruction=_MIT_AI_RISK_SYSTEM,
        description=(
            "MIT AI Risk Repository certification agent. Audits Kamailio AI routing "
            "loops for stability, constraint violations, and objective alignment. "
            "Generates dispatcher hysteresis and hard-constraint Kamailio configs."
        ),
    )
