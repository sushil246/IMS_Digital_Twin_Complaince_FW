"""
Compliance Evaluation Engine — runs framework controls against twin state + logs.
Produces structured audit reports with findings, severity distribution, and scores.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus, FRAMEWORK_REGISTRY,
)


@dataclass
class Finding:
    """A single compliance evaluation result."""
    control_id: str
    control_name: str
    framework_key: str
    framework_name: str
    status: ControlStatus
    severity: ControlSeverity
    category: str
    telecom_vector: str
    evidence_hint: str
    remediation_hint: str
    kamailio_module: Optional[str] = None
    ai_remediation: Optional[str] = None


@dataclass
class FrameworkScore:
    key: str
    name: str
    total: int = 0
    compliant: int = 0
    partial: int = 0
    non_compliant: int = 0
    not_applicable: int = 0

    @property
    def score_pct(self) -> float:
        applicable = self.total - self.not_applicable
        if applicable == 0:
            return 100.0
        earned = self.compliant + (self.partial * 0.5)
        return round(earned / applicable * 100, 1)

    @property
    def risk_level(self) -> str:
        pct = self.score_pct
        if pct >= 90:
            return "LOW"
        if pct >= 70:
            return "MEDIUM"
        if pct >= 50:
            return "HIGH"
        return "CRITICAL"


@dataclass
class AuditReport:
    """Full compliance audit report."""
    audit_id: str
    timestamp: str
    incident_id: Optional[str]
    injected_fault: Optional[str]
    frameworks_evaluated: List[str]
    findings: List[Finding] = field(default_factory=list)
    framework_scores: Dict[str, FrameworkScore] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        if not self.framework_scores:
            return 0.0
        return round(sum(s.score_pct for s in self.framework_scores.values()) /
                     len(self.framework_scores), 1)

    @property
    def critical_findings(self) -> List[Finding]:
        return [f for f in self.findings
                if f.status == ControlStatus.NON_COMPLIANT and
                f.severity == ControlSeverity.CRITICAL]

    @property
    def non_compliant_findings(self) -> List[Finding]:
        return [f for f in self.findings if f.status == ControlStatus.NON_COMPLIANT]

    def to_dict(self) -> Dict:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "incident_id": self.incident_id,
            "injected_fault": self.injected_fault,
            "frameworks_evaluated": self.frameworks_evaluated,
            "overall_score": self.overall_score,
            "framework_scores": {
                k: {
                    "key": v.key,
                    "name": v.name,
                    "score_pct": v.score_pct,
                    "risk_level": v.risk_level,
                    "total": v.total,
                    "compliant": v.compliant,
                    "partial": v.partial,
                    "non_compliant": v.non_compliant,
                    "not_applicable": v.not_applicable,
                }
                for k, v in self.framework_scores.items()
            },
            "summary": {
                "total_controls": len(self.findings),
                "compliant": sum(1 for f in self.findings if f.status == ControlStatus.COMPLIANT),
                "partial": sum(1 for f in self.findings if f.status == ControlStatus.PARTIAL),
                "non_compliant": sum(1 for f in self.findings if f.status == ControlStatus.NON_COMPLIANT),
                "critical_findings": len(self.critical_findings),
            },
            "findings": [
                {
                    "control_id": f.control_id,
                    "control_name": f.control_name,
                    "framework": f.framework_key,
                    "status": f.status.value,
                    "severity": f.severity.value,
                    "category": f.category,
                    "telecom_vector": f.telecom_vector,
                    "evidence_hint": f.evidence_hint,
                    "remediation_hint": f.remediation_hint,
                    "kamailio_module": f.kamailio_module,
                    "ai_remediation": f.ai_remediation,
                }
                for f in self.findings
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ComplianceEvaluator:
    """Runs compliance controls against a digital twin state and log set."""

    def evaluate(
        self,
        twin: Any,
        logs: List[str],
        framework_keys: Optional[List[str]] = None,
    ) -> AuditReport:
        import uuid
        keys = framework_keys or list(FRAMEWORK_REGISTRY.keys())
        now = datetime.now(timezone.utc).isoformat()
        incident_id = getattr(twin, 'incident_id', None) if twin else None
        injected_fault = getattr(twin, 'injected_fault', None) if twin else None

        report = AuditReport(
            audit_id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            timestamp=now,
            incident_id=incident_id,
            injected_fault=injected_fault,
            frameworks_evaluated=keys,
        )

        for fkey in keys:
            fw = FRAMEWORK_REGISTRY.get(fkey)
            if not fw:
                continue
            score = FrameworkScore(key=fkey, name=fw.name, total=len(fw.controls))
            for ctrl in fw.controls:
                try:
                    status = ctrl.check(twin, logs)
                except Exception:
                    status = ControlStatus.PARTIAL

                finding = Finding(
                    control_id=ctrl.id,
                    control_name=ctrl.name,
                    framework_key=fkey,
                    framework_name=fw.name,
                    status=status,
                    severity=ctrl.severity,
                    category=ctrl.category,
                    telecom_vector=ctrl.telecom_vector,
                    evidence_hint=ctrl.evidence_hint,
                    remediation_hint=ctrl.remediation_hint,
                    kamailio_module=ctrl.kamailio_module,
                )
                report.findings.append(finding)

                if status == ControlStatus.COMPLIANT:
                    score.compliant += 1
                elif status == ControlStatus.PARTIAL:
                    score.partial += 1
                elif status == ControlStatus.NON_COMPLIANT:
                    score.non_compliant += 1
                else:
                    score.not_applicable += 1

            report.framework_scores[fkey] = score

        return report
