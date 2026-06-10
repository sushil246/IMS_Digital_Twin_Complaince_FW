"""Simulation layer — Kamailio SIP router and compliance fault injector."""
from .kamailio_sim import KamailioSimulator, COMPLIANCE_SCENARIOS, inject_compliance_fault

__all__ = ["KamailioSimulator", "COMPLIANCE_SCENARIOS", "inject_compliance_fault"]
