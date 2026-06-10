"""
UK Telecoms Security Act 2021 — Certification Testing Agent.

Specialises in:
  - SIP signaling data anonymization audits (TSA-SIG-001)
  - Rogue SIP registration detection using Kamailio htable + pike (TSA-SIG-002)
  - Core infrastructure resiliency — session-agent failover (TSA-SIG-003)
  - DoS/DDoS INVITE rate-limiting via pipelimit module (TSA-SIG-004)
  - TLS certificate lifecycle and transport encryption (TSA-SIG-005)
  - Continuous security monitoring via OPTIONS keepalive (TSA-SIG-006)
"""
from __future__ import annotations
from google.adk.agents import LlmAgent

from ._base import build_model, all_tools, _THINK_PREFIX

_UK_TSA_SYSTEM = _THINK_PREFIX + """\
You are a UK Telecoms Security Act 2021 (TSA) compliance specialist for IMS/SIP infrastructure.

Your deep expertise covers:
- OFCOM and NCSC technical guidance for telecoms operators under the TSA
- Kamailio SIP proxy hardening: pipelimit, pike, htable, permissions, tls modules
- Oracle SBC ACLI security configuration: dos-protection, tls-profile, session-agent failover
- SIP signaling data anonymization: pseudonymization of MSISDN, IMSI, and subscriber URIs in logs
- Rogue registration detection: htable IP-ACL, digest auth with IP binding
- Core network resiliency: redundant P-CSCF session-agents, hunt-group failover

TSA Control IDs you are responsible for:
  TSA-SIG-001: SIP Signaling Data Anonymization
  TSA-SIG-002: Rogue SIP Registration Detection
  TSA-SIG-003: Core Infrastructure Resiliency
  TSA-SIG-004: DoS/DDoS SIP INVITE Rate Limiting
  TSA-SIG-005: SIP Transport Encryption (TLS)
  TSA-SIG-006: Continuous Security Monitoring

When asked to test or remediate:
1. Query the IMS twin and SBC logs using available tools
2. Identify which TSA controls are violated
3. Generate complete Kamailio kamailio.cfg and/or Oracle SBC ACLI fixes
4. Include the specific TSA control ID as an inline comment in every fix block
5. Provide verification steps (e.g., kamcmd commands, log patterns to monitor)

Always reference specific log evidence and twin KPIs in your analysis.
Format Kamailio config in proper kamailio.cfg syntax with loadmodule, modparam, and route blocks.
"""

# ── Compliance test tools specific to UK TSA ──────────────────────────────────

def check_sip_pii_exposure(logs_context: str) -> dict:
    """Check SIP logs for unmasked E.164 MSISDNs or subscriber URIs (TSA-SIG-001).

    Args:
        logs_context: Raw Kamailio log content to scan for PII patterns

    Returns:
        dict with pii_found (bool), count, sample_lines, and recommended_fix
    """
    import re
    pii_re = re.compile(
        r"sip:\+\d{10,15}@|P-Asserted-Identity:.*\+\d|From:.*<sip:\+|To:.*<sip:\+", re.I
    )
    lines = logs_context.split("\n")
    exposed = [l for l in lines if pii_re.search(l)]
    return {
        "control_id": "TSA-SIG-001",
        "pii_found": len(exposed) > 0,
        "exposure_count": len(exposed),
        "sample_lines": exposed[:3],
        "compliant": len(exposed) == 0,
        "recommended_fix": (
            "Apply pv_printf pseudonymization in kamailio.cfg before xlog calls. "
            "Use crypto module HMAC-SHA256 to replace MSISDN with deterministic pseudonym."
        ) if exposed else "No PII exposure detected in logs.",
    }


def check_rate_limit_config(sbc_config_context: str) -> dict:
    """Check Oracle SBC/Kamailio rate-limit configuration for TSA-SIG-004 compliance.

    Args:
        sbc_config_context: Current SBC/Kamailio configuration text

    Returns:
        dict with rate_limit_active (bool), max_invite_rate, and gap analysis
    """
    import re
    invite_rate_re = re.compile(r"invite.max.rate[:\s=]+(\d+)", re.I)
    pike_re = re.compile(r"loadmodule\s+[\"']pike\.so[\"']", re.I)
    pipelimit_re = re.compile(r"loadmodule\s+[\"']pipelimit\.so[\"']", re.I)

    invite_rate_m = invite_rate_re.search(sbc_config_context)
    has_pike = bool(pike_re.search(sbc_config_context))
    has_pipelimit = bool(pipelimit_re.search(sbc_config_context))

    max_rate = int(invite_rate_m.group(1)) if invite_rate_m else 0
    compliant = (max_rate > 0 and max_rate <= 500) and (has_pike or has_pipelimit)

    return {
        "control_id": "TSA-SIG-004",
        "rate_limit_active": max_rate > 0,
        "max_invite_rate": max_rate,
        "pike_module_loaded": has_pike,
        "pipelimit_module_loaded": has_pipelimit,
        "compliant": compliant,
        "gap": "No INVITE rate limiting configured" if not compliant else "Rate limiting in place",
    }


def generate_uk_tsa_kamailio_fix(control_id: str, scenario: str) -> dict:
    """Generate a complete Kamailio configuration fix for a specific UK TSA control violation.

    Args:
        control_id: TSA control ID (e.g. TSA-SIG-001, TSA-SIG-004)
        scenario: Brief description of the violation scenario

    Returns:
        dict with kamailio_cfg (str), description, and verification_steps list
    """
    fixes = {
        "TSA-SIG-001": {
            "kamailio_cfg": '''\
# TSA-SIG-001: SIP Signaling Data Anonymization
# Replace real MSISDN with HMAC pseudonym before any logging

loadmodule "pv.so"
loadmodule "crypto.so"
loadmodule "textopsx.so"

# Anonymization route — call before any xlog with user data
route[TSA_ANONYMIZE] {
    # Pseudonymize From user
    $var(anon_from) = "sub-" + $mb_hmac_sha256_hex($fU);
    $var(anon_to)   = "sub-" + $mb_hmac_sha256_hex($tU);

    # Remove PII-bearing headers from log path
    remove_hf("P-Asserted-Identity");
    remove_hf("P-Preferred-Identity");

    # Log with pseudonyms only — TSA-SIG-001 compliant
    xlog("L_INFO", "CALL[$ci]: from=$var(anon_from) to=$var(anon_to) method=$rm\\n");
}

# In main route, call before any logging:
# route(TSA_ANONYMIZE);
''',
            "description": "Pseudonymize SIP headers using HMAC-SHA256 before logging",
            "verification_steps": [
                "Apply config and reload: kamcmd cfg.reload",
                "Trigger test INVITE and check logs: grep 'CALL\\[' /var/log/kamailio.log | head -5",
                "Verify no +44xxx MSISDN patterns in output: grep -P 'sip:\\+\\d+' /var/log/kamailio.log | wc -l",
                "Result should be 0 — all subscriber URIs replaced with 'sub-<hex>'",
            ],
        },
        "TSA-SIG-002": {
            "kamailio_cfg": '''\
# TSA-SIG-002: Rogue SIP Registration Detection — htable IP-ACL + pike

loadmodule "htable.so"
loadmodule "pike.so"

modparam("htable", "htable", "trusted_peers=>size=8;autoexpire=0;")
modparam("pike", "sampling_time_unit", 2)
modparam("pike", "reqs_density_per_unit", 16)
modparam("pike", "remove_latency", 4)

route[TSA_REGISTER_ACL] {
    # Rate check — TSA-SIG-002 rogue detection
    if(!pike_check_req()) {
        xlog("L_WARN", "TSA-SIG-002: REGISTER flood from $si — blocking\\n");
        sl_send_reply(429, "Too Many Requests");
        exit;
    }
    # IP-whitelist check
    if(!ht_exists("trusted_peers", "$si")) {
        xlog("L_WARN", "TSA-SIG-002: REGISTER from untrusted IP $si AOR=$fu — REJECTING\\n");
        sl_send_reply(403, "Forbidden — Untrusted Source");
        exit;
    }
    xlog("L_INFO", "TSA-SIG-002: REGISTER from trusted $si AOR=$fu — proceeding\\n");
}
''',
            "description": "Block rogue SIP REGISTER from untrusted IPs using htable ACL",
            "verification_steps": [
                "Populate trusted_peers htable: kamcmd htable.seti trusted_peers 10.0.0.1 1",
                "Test rogue REGISTER from unlisted IP — expect 403 Forbidden",
                "Test flood: sipsak -U -p 192.168.x.x -u +447xxx@ims.lab — expect 429",
                "Monitor: grep 'TSA-SIG-002' /var/log/kamailio.log",
            ],
        },
        "TSA-SIG-004": {
            "kamailio_cfg": '''\
# TSA-SIG-004: DoS/DDoS SIP INVITE Rate Limiting — pipelimit + pike

loadmodule "pipelimit.so"
loadmodule "pike.so"

modparam("pipelimit", "default_limit", 100)
modparam("pike", "sampling_time_unit", 2)
modparam("pike", "reqs_density_per_unit", 16)

route[TSA_DOS_PROTECT] {
    if(is_method("INVITE")) {
        # Per-pipeline rate limit — TSA-SIG-004
        if(!pl_check("invite-pipe")) {
            xlog("L_WARN", "TSA-SIG-004: INVITE rate exceeded from $si — 503\\n");
            sl_send_reply(503, "Service Unavailable — Rate Limited");
            exit;
        }
        # Per-source flood detection
        if(!pike_check_req()) {
            xlog("L_WARN", "TSA-SIG-004: INVITE flood from $si — auto-banned\\n");
            sl_send_reply(429, "Too Many Requests");
            exit;
        }
    }
}

# modparam to define the invite pipeline limit:
modparam("pipelimit", "pipe", "name=invite-pipe;algorithm=TAILDROP;limit=100")
''',
            "description": "Apply pipelimit INVITE rate limiting and pike source flood detection",
            "verification_steps": [
                "Reload config: kamcmd cfg.reload",
                "Check pipeline: kamcmd pl.get_pipes",
                "Test: send >100 INVITEs/s — expect 503 responses beyond limit",
                "Verify: grep 'TSA-SIG-004.*rate exceeded' /var/log/kamailio.log",
            ],
        },
    }
    result = fixes.get(control_id, {
        "kamailio_cfg": f"# Fix for {control_id} — see remediation_hint in compliance matrix",
        "description": f"Generic fix for {control_id}",
        "verification_steps": ["Review control description and apply recommended_fix"],
    })
    result["control_id"] = control_id
    result["scenario"] = scenario
    return result


def build_uk_tsa_agent(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LlmAgent:
    """Build the UK TSA certification testing agent."""
    return LlmAgent(
        name="uk_tsa_agent",
        model=build_model(ollama_url, model),
        tools=all_tools() + [check_sip_pii_exposure, check_rate_limit_config, generate_uk_tsa_kamailio_fix],
        instruction=_UK_TSA_SYSTEM,
        description=(
            "UK Telecoms Security Act 2021 compliance agent. Audits IMS/Kamailio "
            "infrastructure against TSA-SIG-001 through TSA-SIG-006 controls. "
            "Generates pipelimit, htable, pike, and TLS Kamailio configuration fixes."
        ),
    )
