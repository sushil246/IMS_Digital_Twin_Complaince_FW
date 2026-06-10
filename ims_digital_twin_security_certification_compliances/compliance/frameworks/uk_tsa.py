"""
UK Telecoms Security Act 2021 — compliance controls for IMS/SIP infrastructure.
Covers anonymization, rogue registration detection, and resiliency obligations.
"""
from __future__ import annotations
import re
from typing import Any, List

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    ComplianceControl, ControlSeverity, ControlStatus,
)


def _check_sip_pii_anonymization(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if SIP logs expose real E.164 numbers or subscriber names unmasked."""
    pii_pattern = re.compile(
        r"(sip:\+\d{10,15}@|From:.*<sip:\+|To:.*<sip:\+|P-Asserted-Identity:.*\+\d)", re.I
    )
    exposed = [l for l in logs if pii_pattern.search(l)]
    if not logs:
        return ControlStatus.NOT_APPLICABLE
    # More than 3 raw PII exposures in logs = non-compliant
    if len(exposed) > 3:
        return ControlStatus.NON_COMPLIANT
    if exposed:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


def _check_rogue_registration(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if twin state shows no rogue-REGISTER detection or htable ACL."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    if sbc:
        dos = sbc.config.get("dos_protection", {})
        rate = dos.get("max_register_rate", 0)
        # Rate limit must be configured and enforced
        if rate == 0 or rate > 500:
            return ControlStatus.NON_COMPLIANT
        # Check twin alarms for active rogue-registration indicators
        reg_alarms = [a for a in twin.all_alarms() if "register" in str(a).lower()]
        if reg_alarms:
            return ControlStatus.PARTIAL
        return ControlStatus.COMPLIANT
    return ControlStatus.NOT_APPLICABLE


def _check_infra_resiliency(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if no failover session-agent is configured for P-CSCF."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    if sbc:
        agents = sbc.config.get("session_agents", {})
        if len(agents) < 2:
            return ControlStatus.NON_COMPLIANT
        return ControlStatus.COMPLIANT
    return ControlStatus.NOT_APPLICABLE


def _check_ddos_rate_limiting(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if INVITE rate-limiting is absent or SIP INVITE flood is active."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    sbc = getattr(twin, 'get_sbc', lambda: None)()
    flood_logs = [l for l in logs if "invite" in l.lower() and
                  ("flood" in l.lower() or "rate" in l.lower() or "drop" in l.lower())]
    if sbc:
        dos = sbc.config.get("dos_protection", {})
        invite_rate = dos.get("max_invite_rate", 0)
        if invite_rate == 0:
            return ControlStatus.NON_COMPLIANT
        if flood_logs:
            return ControlStatus.PARTIAL
        return ControlStatus.COMPLIANT
    return ControlStatus.NOT_APPLICABLE


def _check_sip_transport_encryption(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if SIP transport is unencrypted (no TLS) or TLS cert is expired."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    tls_fail = [l for l in logs if "tls" in l.lower() and
                ("expired" in l.lower() or "handshake failed" in l.lower())]
    if tls_fail:
        return ControlStatus.NON_COMPLIANT
    if twin is not None:
        sbc = getattr(twin, 'get_sbc', lambda: None)()
        if sbc:
            tls = sbc.config.get("tls_profile", "")
            if not tls:
                return ControlStatus.NON_COMPLIANT
            cert_status = sbc.config.get("tls_profile_status", "OK")
            if cert_status == "EXPIRED":
                return ControlStatus.NON_COMPLIANT
    return ControlStatus.COMPLIANT


def _check_network_monitoring(twin: Any, logs: List[str]) -> ControlStatus:
    """Fail if no continuous security monitoring is evident from twin config."""
    if twin is None:
        return ControlStatus.NOT_APPLICABLE
    if len(logs) == 0:
        return ControlStatus.NON_COMPLIANT
    monitor_logs = [l for l in logs if any(kw in l.lower() for kw in
                    ["monitor", "health-check", "ping", "options", "watchdog"])]
    if not monitor_logs:
        return ControlStatus.PARTIAL
    return ControlStatus.COMPLIANT


UK_TSA_CONTROLS: list = [
    ComplianceControl(
        id="TSA-SIG-001",
        name="SIP Signaling Data Anonymization",
        description="All SIP signaling logs must anonymize subscriber PII (E.164 numbers, "
                    "IMSI, names) before storage or transmission to third-party systems.",
        severity=ControlSeverity.CRITICAL,
        category="Data Protection",
        telecom_vector="SIP To/From/P-Asserted-Identity header PII exposure in logs",
        check=_check_sip_pii_anonymization,
        evidence_hint="Grep logs for unmasked E.164 numbers (+44xxx) or subscriber URIs",
        remediation_hint="Use Kamailio pv_printf to mask headers: replace subscriber part "
                         "with pseudonym before logging. Apply `textopsx` header rewrite.",
        kamailio_module="pv, textopsx",
    ),
    ComplianceControl(
        id="TSA-SIG-002",
        name="Rogue SIP Registration Detection",
        description="The network must detect and block unauthorized SIP REGISTER attempts "
                    "from unknown or spoofed UE identities using ACL and rate controls.",
        severity=ControlSeverity.HIGH,
        category="Access Control",
        telecom_vector="Unauthorized SIP REGISTER from spoofed/unknown SIP AOR",
        check=_check_rogue_registration,
        evidence_hint="Check dos_protection.max_register_rate and htable ACL configuration",
        remediation_hint="Enable `htable` module in kamailio.cfg with ACL hash-table. "
                         "Add pike rate-limiter for REGISTER requests from untrusted sources.",
        kamailio_module="htable, pike, permissions",
    ),
    ComplianceControl(
        id="TSA-SIG-003",
        name="Core Infrastructure Resiliency",
        description="Critical IMS elements (P-CSCF, S-CSCF, HSS) must have redundant "
                    "failover paths. No single point of failure in the signaling plane.",
        severity=ControlSeverity.CRITICAL,
        category="Resiliency",
        telecom_vector="Single-homed P-CSCF with no failover session-agent",
        check=_check_infra_resiliency,
        evidence_hint="Check session_agents count and local-policy hunt group configuration",
        remediation_hint="Add secondary session-agent for P-CSCF. Configure session-group "
                         "with hunt strategy. Verify Oracle SBC local-policy uses group.",
        kamailio_module="dispatcher, lcr",
    ),
    ComplianceControl(
        id="TSA-SIG-004",
        name="DoS/DDoS SIP INVITE Rate Limiting",
        description="The SBC/SIP proxy must enforce per-source rate limits on INVITE "
                    "requests to prevent volumetric DoS attacks from overwhelming core IMS.",
        severity=ControlSeverity.HIGH,
        category="Availability Protection",
        telecom_vector="Unthrottled SIP INVITE flood consuming SBC session capacity",
        check=_check_ddos_rate_limiting,
        evidence_hint="Check dos_protection.max_invite_rate and pipelimit configuration",
        remediation_hint="Configure `pipelimit` module in kamailio.cfg: "
                         "`pl_check_limit(\"invite-pipe\", \"INVITE\", 100)`. "
                         "Set deny_period=60 for offending source IPs.",
        kamailio_module="pipelimit, pike, ratelimit",
    ),
    ComplianceControl(
        id="TSA-SIG-005",
        name="SIP Transport Encryption (TLS)",
        description="All SIP signaling on access and core interfaces must use TLS 1.2+ "
                    "with valid certificates. Expired or self-signed certs are non-compliant.",
        severity=ControlSeverity.CRITICAL,
        category="Transport Security",
        telecom_vector="Expired TLS certificate causing plaintext fallback or service outage",
        check=_check_sip_transport_encryption,
        evidence_hint="Check tls_profile cert_expiry and TLS handshake errors in logs",
        remediation_hint="Renew certificate, upload to SBC, update tls-profile. "
                         "Enable certificate-monitor with 30-day pre-expiry alert. "
                         "In Kamailio: update tls.cfg cert and key paths, reload with `kamcmd`.",
        kamailio_module="tls",
    ),
    ComplianceControl(
        id="TSA-SIG-006",
        name="Continuous Security Monitoring",
        description="Operators must maintain real-time security monitoring of IMS network "
                    "elements with automated alerting on anomalous signaling patterns.",
        severity=ControlSeverity.MEDIUM,
        category="Monitoring",
        telecom_vector="No health-check or OPTIONS ping configured for session agents",
        check=_check_network_monitoring,
        evidence_hint="Verify OPTIONS ping-method, ping-interval in session-agent config",
        remediation_hint="Enable OPTIONS ping-method on all session-agents (interval 10s). "
                         "Configure SNMP traps or syslog forwarding to SIEM. "
                         "In Kamailio: use `siputils` + `options` modules for keepalive.",
        kamailio_module="siputils, options",
    ),
]
