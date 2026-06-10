"""
Compliance control matrix — registry of all frameworks and their controls.
Each control carries a check function that evaluates against twin state + logs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ControlSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"


class ControlStatus(str, Enum):
    COMPLIANT     = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIAL       = "PARTIAL"
    NOT_APPLICABLE = "N/A"


@dataclass
class ComplianceControl:
    """A single auditable control within a compliance framework."""
    id: str
    name: str
    description: str
    severity: ControlSeverity
    category: str
    telecom_vector: str
    check: Callable[[Any, List[str]], ControlStatus]
    evidence_hint: str = ""
    remediation_hint: str = ""
    kamailio_module: Optional[str] = None


@dataclass
class FrameworkMeta:
    """Metadata for a compliance framework."""
    key: str
    name: str
    full_name: str
    jurisdiction: str
    description: str
    icon: str
    color: str
    controls: List[ComplianceControl] = field(default_factory=list)


# ── Global registry ───────────────────────────────────────────────────────────

FRAMEWORK_REGISTRY: Dict[str, FrameworkMeta] = {}


def register_framework(meta: FrameworkMeta) -> FrameworkMeta:
    FRAMEWORK_REGISTRY[meta.key] = meta
    return meta


def get_framework(key: str) -> Optional[FrameworkMeta]:
    return FRAMEWORK_REGISTRY.get(key)


def list_frameworks() -> List[Dict]:
    return [
        {
            "key": f.key,
            "name": f.name,
            "full_name": f.full_name,
            "jurisdiction": f.jurisdiction,
            "description": f.description,
            "icon": f.icon,
            "color": f.color,
            "control_count": len(f.controls),
        }
        for f in FRAMEWORK_REGISTRY.values()
    ]


# ── Import all framework control sets (registers them as a side-effect) ───────
from ims_digital_twin_security_certification_compliances.compliance.frameworks import (  # noqa: E402
    UK_TSA_CONTROLS, EU_AI_ACT_CONTROLS, ISO_42001_CONTROLS,
    NIST_AI_RMF_CONTROLS, MIT_AI_RISK_CONTROLS, OECD_AI_CONTROLS,
)

register_framework(FrameworkMeta(
    key="uk_tsa",
    name="UK TSA",
    full_name="Telecoms Security Act 2021",
    jurisdiction="United Kingdom",
    description="Anonymization of signaling data, rogue SIP detection, and core infrastructure resiliency requirements.",
    icon="🇬🇧",
    color="#012169",
    controls=UK_TSA_CONTROLS,
))

register_framework(FrameworkMeta(
    key="eu_ai_act",
    name="EU AI Act",
    full_name="EU Artificial Intelligence Act (2024/1689)",
    jurisdiction="European Union",
    description="High-risk AI classification, biometric processing controls, and drift audit logs for automated routing.",
    icon="🇪🇺",
    color="#003399",
    controls=EU_AI_ACT_CONTROLS,
))

register_framework(FrameworkMeta(
    key="iso_42001",
    name="ISO 42001",
    full_name="ISO/IEC 42001:2023 AI Management System",
    jurisdiction="International",
    description="AI model governance, risk logging pipelines, and data lineage audits of the network twin.",
    icon="🌐",
    color="#007A33",
    controls=ISO_42001_CONTROLS,
))

register_framework(FrameworkMeta(
    key="nist_ai_rmf",
    name="NIST AI RMF",
    full_name="NIST AI Risk Management Framework 1.0",
    jurisdiction="United States",
    description="Trustworthiness metrics, adversarial prompt-injection defense for telecom routing controls, and explainability.",
    icon="🇺🇸",
    color="#BF0A30",
    controls=NIST_AI_RMF_CONTROLS,
))

register_framework(FrameworkMeta(
    key="mit_ai_risk",
    name="MIT AI Risk",
    full_name="MIT AI Risk Repository",
    jurisdiction="Academic",
    description="Structural vulnerability assessments of the optimization loops in Kamailio telemetry.",
    icon="🎓",
    color="#A31F34",
    controls=MIT_AI_RISK_CONTROLS,
))

register_framework(FrameworkMeta(
    key="oecd_ai",
    name="OECD AI",
    full_name="OECD Principles on Artificial Intelligence",
    jurisdiction="International (OECD)",
    description="Transparency of automated calling logic, accountability traces, and fair resource allocation.",
    icon="🌍",
    color="#1A6BAC",
    controls=OECD_AI_CONTROLS,
))
