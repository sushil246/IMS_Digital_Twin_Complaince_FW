"""
MIT AI Risk Repository — structural risk controls for IMS optimization loops.
Covers feedback instability, constraint violations, and objective misalignment.
"""
from __future__ import annotations
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_optimization_loop_stability(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'loop_instability' in fault or 'oscillation' in fault:
        return ControlStatus.NON_COMPLIANT
    instability_logs = [l for l in logs if any(kw in l.lower() for kw in
                        ["oscillat", "thrash", "flip-flop", "route-loop", "loop-detected"])]
    if instability_logs:
        return ControlStatus.NON_COMPLIANT
    return ControlStatus.COMPLIANT


def _check_feedback_loop_analysis(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    feedback_logs = [l for l in logs if any(kw in l.lower() for kw in
                     ["feedback", "reward-signal", "rl-step", "policy-update"])]
    if not feedback_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_constraint_violation(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    constraint_violations = [l for l in logs if any(kw in l.lower() for kw in
                              ["constraint-violated", "sla-breach", "capacity-exceeded",
                               "max-sessions", "limit exceeded"])]
    if constraint_violations:
        return ControlStatus.NON_COMPLIANT
    return ControlStatus.COMPLIANT


def _check_objective_alignment(twin: Any, logs: List[str]) -> ControlStatus:
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'misaligned' in fault:
        return ControlStatus.NON_COMPLIANT
    align_logs = [l for l in logs if any(kw in l.lower() for kw in
                  ["objective-metric", "reward:", "kpi-aligned", "optimization-target"])]
    if not align_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_telemetry_vulnerability(twin: Any, logs: List[str]) -> ControlStatus:
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    fault = getattr(twin, 'injected_fault', '') or ''
    if 'telemetry_poison' in fault:
        return ControlStatus.NON_COMPLIANT
    telem_logs = [l for l in logs if any(kw in l.lower() for kw in
                  ["telemetry-validated", "metric-integrity", "kpi-source-verified"])]
    if not telem_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


MIT_AI_RISK_CONTROLS: list = [
    ComplianceControl(
        id="MIT-STRUCT-001",
        name="Optimization Loop Stability Assessment",
        description="Kamailio routing optimization loops must be assessed for potential "
                    "instability: oscillation between route choices, thrashing under load, "
                    "and positive feedback amplification must be bounded and monitored.",
        severity=ControlSeverity.HIGH,
        category="Structural Risk",
        telecom_vector="AI load-balancer oscillating between two degraded session agents",
        check=_check_optimization_loop_stability,
        evidence_hint="Check for oscillat, thrash, flip-flop, route-loop in Kamailio logs",
        remediation_hint="Implement hysteresis in routing decisions: require 3 consecutive "
                         "probe failures before marking agent down. "
                         "In Kamailio dispatcher: set `ds_probing_threshold=3`. "
                         "Add dampening timer: don't re-evaluate route for 60s after change.",
        kamailio_module="dispatcher, timer",
    ),
    ComplianceControl(
        id="MIT-STRUCT-002",
        name="Feedback Loop Stability Analysis",
        description="Reinforcement-learning or feedback-driven routing must have stability "
                    "bounds. Learning rate and update frequency must prevent runaway "
                    "policy updates that could destabilize the routing table.",
        severity=ControlSeverity.HIGH,
        category="Structural Risk",
        telecom_vector="RL routing agent updating weights too aggressively under congestion spike",
        check=_check_feedback_loop_analysis,
        evidence_hint="Check for reward-signal, rl-step, policy-update entries in ML telemetry",
        remediation_hint="Cap learning rate at 0.001 for online routing RL agent. "
                         "Implement update throttle: max 1 routing table update per 60s. "
                         "Add safety critic: reject policy updates that increase P99 latency >20%.",
        kamailio_module="N/A (ML training pipeline)",
    ),
    ComplianceControl(
        id="MIT-STRUCT-003",
        name="Constraint Violation Detection",
        description="AI routing must enforce hard constraints: session capacity limits, "
                    "SLA commitments, and emergency-call priority. Constraint violations "
                    "must immediately trigger fallback to rule-based routing.",
        severity=ControlSeverity.CRITICAL,
        category="Constraint Safety",
        telecom_vector="AI routing exceeding max-sessions limit on SBC causing call drops",
        check=_check_constraint_violation,
        evidence_hint="Check for constraint-violated, sla-breach, capacity-exceeded in logs",
        remediation_hint="Hard-code session capacity guard: if sbc01.sessions > 4500, "
                         "reject new INVITEs with 503 before AI routing runs. "
                         "In Kamailio: `if($stat(active_dialogs) > 4500) { sl_send_reply(503); exit; }`",
        kamailio_module="dialog, statistics, sl",
    ),
    ComplianceControl(
        id="MIT-STRUCT-004",
        name="Optimization Objective Alignment Verification",
        description="The AI routing objective function must remain aligned with operator "
                    "intent (maximize QoS, minimize cost, ensure fairness). Objective drift "
                    "— where optimized metric diverges from intended goal — must be detected.",
        severity=ControlSeverity.MEDIUM,
        category="Alignment",
        telecom_vector="AI routing optimizing for throughput while silently degrading voice quality (MOS)",
        check=_check_objective_alignment,
        evidence_hint="Check for objective-metric, kpi-aligned, optimization-target in logs",
        remediation_hint="Define multi-objective routing function: w1*MOS + w2*cost + w3*fairness. "
                         "Monitor each component separately. Alert if any component degrades >10%. "
                         "Quarterly objective alignment review with network operations team.",
        kamailio_module="N/A (objective function design)",
    ),
    ComplianceControl(
        id="MIT-STRUCT-005",
        name="Telemetry Input Vulnerability Assessment",
        description="Kamailio telemetry data feeding AI routing models must be validated "
                    "for integrity. Poisoned or corrupted metrics could cause the AI to "
                    "make systematically incorrect routing decisions.",
        severity=ControlSeverity.HIGH,
        category="Input Integrity",
        telecom_vector="Corrupted KPI telemetry causing AI to route traffic to degraded SBC",
        check=_check_telemetry_vulnerability,
        evidence_hint="Check for telemetry-validated, metric-integrity in collection pipeline",
        remediation_hint="Implement telemetry validation: cross-check KPIs from multiple sources. "
                         "Detect outliers: if metric deviates >3-sigma from 24h baseline, flag. "
                         "Use HMAC signing on telemetry messages to detect tampering.",
        kamailio_module="statistics, N/A (telemetry pipeline)",
    ),
]
