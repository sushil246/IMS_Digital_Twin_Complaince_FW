"""
Oracle SBC ACLI config generation tools.
Produces real Oracle SBC ACLI-format configuration blocks.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

OUTPUT_DIR = Path(__file__).parent.parent / "output"


# ── ACLI config templates ─────────────────────────────────────────────────────

_ACLI_HEADER = """\
# ============================================================
# Oracle Session Border Controller — Generated Configuration
# Generated: {timestamp}
# Incident:  {incident_id}
# Scenario:  {scenario}
# Node:      {node_id} ({hostname})
# ============================================================
"""

_SECTIONS: Dict[str, str] = {
    "dos_protection_rate_limit": """\
dos-protection
    trust-level            {trust_level}
    phy-interface          access
    register-max-rate      {max_register_rate}
    invite-max-rate        {max_invite_rate}
    register-burst-size    {register_burst_size}
    invite-burst-size      {invite_burst_size}
    deny-period            {deny_period}
    exception-addresses    {whitelist}
!
""",
    "tls_profile": """\
tls-profile
    name               {profile_name}
    end-entity-cert    {cert_path}
    trusted-ca-certs   {ca_bundle_path}
    cipher-list        {cipher_list}
    tls-version        {tls_version}
    verify-depth       {verify_depth}
    mutual-auth        {mutual_auth}
!
""",
    "media_manager": """\
media-manager
    media-supervision-timeout  {rtp_timeout}
    max-bandwidth              {max_bw_kbps}
    media-policy               {media_policy}
    rtp-inactivity-timer       {rtp_inactivity_timer}
    rtcp-inactivity-timer      {rtcp_inactivity_timer}
    update-ip-for-sdp-na       enabled
!
""",
    "media_profile": """\
media-sec-policy
    name                  {policy_name}
    srtp-enabled          {srtp_enabled}
    srtp-auth-tag-bits    {auth_tag_bits}
    srtp-crypto-suite     {crypto_suite}
    dtls-enabled          {dtls_enabled}
    dtls-cipher-suite     {dtls_cipher}
!
""",
    "session_agent": """\
session-agent
    hostname              {agent_hostname}
    ip-address            {agent_ip}
    port                  {agent_port}
    transport-method      {transport}
    realm-id              {realm_id}
    description           {description}
    max-sessions          {max_sessions}
    weight                {weight}
    state                 enabled
    ping-method           OPTIONS
    ping-interval         {ping_interval}
    ping-send-mode        keep-alive
    out-of-service-response-code  503
    failover-response-codes       503,408
!
""",
    "local_policy": """\
local-policy
    from-address          {from_address}
    to-address            {to_address}
    source-realm          {source_realm}
    policy-priority       {priority}
    policy-attribute
        next-hop          {next_hop}
        realm             {dest_realm}
        action            {action}
    !
!
""",
    "sip_interface": """\
sip-interface
    realm-id              {realm_id}
    sip-ip-interfaces
        address           {ip_address}
        port              {sip_port}
        transport-method  {transport}
        tls-profile       {tls_profile}
    !
    sip-timer-b           {timer_b}
    sip-timer-d           {timer_d}
    sip-timer-t1          {timer_t1}
    sip-timer-t2          {timer_t2}
    max-forwards          {max_forwards}
    registration-caching  {reg_caching}
    max-register-per-second  {max_reg_rate}
!
""",
}


# ── Config generation functions ───────────────────────────────────────────────

def generate_dos_protection_config(
    trust_level: str = "medium",
    max_register_rate: int = 200,
    max_invite_rate: int = 100,
    register_burst_size: int = 50,
    invite_burst_size: int = 30,
    deny_period: int = 30,
    whitelist: str = "10.0.0.0/8",
) -> dict:
    """Generate Oracle SBC ACLI config to fix DoS / registration storm issues.

    Args:
        trust_level: SBC trust level for the realm (low/medium/high)
        max_register_rate: Max REGISTER requests per second
        max_invite_rate: Max INVITE requests per second
        register_burst_size: Burst allowance for REGISTER
        invite_burst_size: Burst allowance for INVITE
        deny_period: Seconds to deny offending source
        whitelist: IP/CIDR to whitelist from rate limiting

    Returns:
        dict with acli_config string and file path
    """
    block = _SECTIONS["dos_protection_rate_limit"].format(
        trust_level=trust_level,
        max_register_rate=max_register_rate,
        max_invite_rate=max_invite_rate,
        register_burst_size=register_burst_size,
        invite_burst_size=invite_burst_size,
        deny_period=deny_period,
        whitelist=whitelist,
    )
    return _wrap_and_save(block, "dos_protection_fix")


def generate_tls_profile_config(
    profile_name: str = "ims-tls-prof",
    cert_path: str = "/opt/acme/certs/sbc01_2026.pem",
    ca_bundle_path: str = "/opt/acme/certs/ims-ca-bundle.pem",
    cipher_list: str = "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES256-GCM-SHA384",
    tls_version: str = "TLSv1.3",
    verify_depth: int = 3,
    mutual_auth: str = "disabled",
) -> dict:
    """Generate Oracle SBC ACLI config to fix expired TLS certificate.

    Args:
        profile_name: Name of the TLS profile to update
        cert_path: Path to the new end-entity certificate on the SBC
        ca_bundle_path: Path to the trusted CA bundle
        cipher_list: TLS cipher suite list
        tls_version: Minimum TLS version
        verify_depth: Certificate chain verification depth
        mutual_auth: Enable mutual TLS authentication

    Returns:
        dict with acli_config string and file path
    """
    block = _SECTIONS["tls_profile"].format(
        profile_name=profile_name,
        cert_path=cert_path,
        ca_bundle_path=ca_bundle_path,
        cipher_list=cipher_list,
        tls_version=tls_version,
        verify_depth=verify_depth,
        mutual_auth=mutual_auth,
    )
    return _wrap_and_save(block, "tls_profile_fix")


def generate_media_manager_config(
    rtp_timeout: int = 30,
    rtp_inactivity_timer: int = 30,
    rtcp_inactivity_timer: int = 60,
    max_bw_kbps: int = 100000,
    media_policy: str = "default",
) -> dict:
    """Generate Oracle SBC ACLI media-manager config to fix RTP timeout / one-way audio.

    Args:
        rtp_timeout: RTP media supervision timeout in seconds
        rtp_inactivity_timer: Seconds of inactivity before declaring media dead
        rtcp_inactivity_timer: Seconds before RTCP timeout
        max_bw_kbps: Maximum media bandwidth in Kbps
        media_policy: Media policy name

    Returns:
        dict with acli_config string and file path
    """
    block = _SECTIONS["media_manager"].format(
        rtp_timeout=rtp_timeout,
        rtp_inactivity_timer=rtp_inactivity_timer,
        rtcp_inactivity_timer=rtcp_inactivity_timer,
        max_bw_kbps=max_bw_kbps,
        media_policy=media_policy,
    )
    return _wrap_and_save(block, "media_manager_fix")


def generate_media_sec_policy_config(
    policy_name: str = "ims-media-sec",
    srtp_enabled: str = "enabled",
    auth_tag_bits: int = 80,
    crypto_suite: str = "AES_CM_128_HMAC_SHA1_80 AES_256_CM_HMAC_SHA1_80 AES_256_GCM_SHA384",
    dtls_enabled: str = "enabled",
    dtls_cipher: str = "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256",
) -> dict:
    """Generate Oracle SBC ACLI media-sec-policy config to fix SRTP/DTLS negotiation failures.

    Args:
        policy_name: Name of the media security policy
        srtp_enabled: Enable SRTP
        auth_tag_bits: SRTP authentication tag length (80 or 32)
        crypto_suite: Space-separated list of allowed SRTP crypto suites
        dtls_enabled: Enable DTLS for key exchange
        dtls_cipher: DTLS cipher suite list

    Returns:
        dict with acli_config string and file path
    """
    block = _SECTIONS["media_profile"].format(
        policy_name=policy_name,
        srtp_enabled=srtp_enabled,
        auth_tag_bits=auth_tag_bits,
        crypto_suite=crypto_suite,
        dtls_enabled=dtls_enabled,
        dtls_cipher=dtls_cipher,
    )
    return _wrap_and_save(block, "media_sec_policy_fix")


def generate_session_agent_config(
    agent_hostname: str = "pcscf01.ims.lab",
    agent_ip: str = "10.0.2.10",
    agent_port: int = 5060,
    transport: str = "UDP",
    realm_id: str = "core",
    description: str = "Primary P-CSCF",
    max_sessions: int = 5000,
    weight: int = 10,
    ping_interval: int = 30,
) -> dict:
    """Generate Oracle SBC ACLI session-agent config to fix upstream connectivity / failover.

    Args:
        agent_hostname: Session agent hostname
        agent_ip: Session agent IP address
        agent_port: SIP port
        transport: Transport protocol (UDP/TCP/TLS)
        realm_id: Realm this agent belongs to
        description: Human-readable description
        max_sessions: Max concurrent sessions to this agent
        weight: Load balancing weight
        ping_interval: Health-check ping interval in seconds

    Returns:
        dict with acli_config string and file path
    """
    block = _SECTIONS["session_agent"].format(
        agent_hostname=agent_hostname,
        agent_ip=agent_ip,
        agent_port=agent_port,
        transport=transport,
        realm_id=realm_id,
        description=description,
        max_sessions=max_sessions,
        weight=weight,
        ping_interval=ping_interval,
    )
    return _wrap_and_save(block, "session_agent_fix")


def generate_codec_policy_config(
    allowed_codecs: str = "G.711 G.729 AMR-NB AMR-WB OPUS",
    transcoding_enabled: str = "disabled",
    codec_order: str = "PCMA PCMU G729 AMR",
) -> dict:
    """Generate Oracle SBC codec/media-profile config to fix SDP codec mismatch (488 errors).

    Args:
        allowed_codecs: Space-separated list of codecs the SBC should allow/pass-through
        transcoding_enabled: Enable media transcoding
        codec_order: Preferred codec order in SDP answer

    Returns:
        dict with acli_config string and file path
    """
    block = f"""\
media-profile
    name                  ims-codec-policy
    media-criteria        requires-audio
    codec-policy
        allow-codecs      {allowed_codecs}
        codec-order       {codec_order}
        transcoding       {transcoding_enabled}
        sdp-bandwidth     AS:128
    !
!
"""
    return _wrap_and_save(block, "codec_policy_fix")


def generate_full_remediation_config(
    incident_id: str,
    scenario_key: str,
    node_id: str = "sbc01",
    hostname: str = "sbc01.ims.lab",
) -> dict:
    """Generate a combined Oracle SBC ACLI remediation config for the detected fault scenario.
    This is the main config generation entry point for the RCA agent.

    Args:
        incident_id: Incident reference ID (e.g. INC-A1B2C3D4)
        scenario_key: Fault scenario key (reg_storm, tls_cert_expiry, rtp_timeout,
                      codec_mismatch, pcscf_down, srtp_dtls_fail)
        node_id: Target SBC node ID
        hostname: SBC hostname

    Returns:
        dict with full remediation ACLI config, file_path, and remediation_steps list
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = _ACLI_HEADER.format(
        timestamp=ts,
        incident_id=incident_id,
        scenario=scenario_key,
        node_id=node_id,
        hostname=hostname,
    )

    scenario_configs = {
        "reg_storm": _reg_storm_config,
        "tls_cert_expiry": _tls_cert_config,
        "rtp_timeout": _rtp_timeout_config,
        "codec_mismatch": _codec_mismatch_config,
        "pcscf_down": _pcscf_down_config,
        "srtp_dtls_fail": _srtp_dtls_config,
    }

    if scenario_key not in scenario_configs:
        return {"error": f"Unknown scenario: {scenario_key}"}

    body, steps = scenario_configs[scenario_key]()
    full_config = header + body
    fname = f"remediation_{incident_id}_{scenario_key}.acli"
    fpath = OUTPUT_DIR / fname
    OUTPUT_DIR.mkdir(exist_ok=True)
    fpath.write_text(full_config, encoding="utf-8")

    return {
        "success": True,
        "incident_id": incident_id,
        "scenario": scenario_key,
        "file_path": str(fpath),
        "remediation_steps": steps,
        "acli_config": full_config,
    }


# ── Per-scenario config bodies ────────────────────────────────────────────────

def _reg_storm_config():
    body = """\
# --- FIX: Tighten rate limits and grow registration cache ---

dos-protection
    trust-level            low
    phy-interface          access
    register-max-rate      200
    invite-max-rate        100
    register-burst-size    50
    invite-burst-size      30
    deny-period            60
    exception-addresses    10.0.0.0/8 192.168.1.0/24
!

sip-config
    registration-max       50000
    registration-interval  3600
!

# Apply to access realm
realm-config
    id                     access
    media-policy           default
    in-trans-filter        reg-rate-limit
    out-trans-filter       reg-rate-limit
!
"""
    steps = [
        "Set dos-protection register-max-rate=200 invite-max-rate=100 on access realm",
        "Set deny-period=60 to temporarily block abusive sources",
        "Add core network IPs (10.0.0.0/8) to exception-addresses whitelist",
        "Increase sip-config registration-max to 50000 if legitimate load is high",
        "Monitor CPU: target <70% — scale SBC capacity if load is legitimate",
        "Enable CAPTCHA or OAuth on UE registration portal to prevent bot floods",
    ]
    return body, steps


def _tls_cert_config():
    body = """\
# --- FIX: Replace expired TLS certificate ---

# Step 1: Upload new cert via SFTP to /opt/acme/certs/ BEFORE applying below

tls-profile
    name               ims-tls-prof
    end-entity-cert    /opt/acme/certs/sbc01_2026_new.pem
    trusted-ca-certs   /opt/acme/certs/ims-ca-bundle.pem
    cipher-list        TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES256-GCM-SHA384
    tls-version        TLSv1.3
    verify-depth       3
    mutual-auth        disabled
!

# Enable certificate monitoring (prevent future expiry)
certificate-monitor
    name               ims-tls-prof-monitor
    tls-profile        ims-tls-prof
    alert-before-days  30
    critical-days      7
    syslog-on-expiry   enabled
!
"""
    steps = [
        "Generate new certificate CSR on SBC: `generate-certificate ims-tls-prof`",
        "Submit CSR to CA and retrieve signed certificate",
        "SFTP upload signed cert to /opt/acme/certs/sbc01_2026_new.pem",
        "Apply updated tls-profile config pointing to new cert",
        "Verify: `verify-certificate ims-tls-prof` — ensure notAfter > 365 days",
        "Configure certificate-monitor with 30-day pre-expiry alert",
        "Add cert renewal to calendar/automation (Let's Encrypt ACME or EJBCA)",
    ]
    return body, steps


def _rtp_timeout_config():
    body = """\
# --- FIX: RTP media timeout / one-way audio / NAT traversal ---

media-manager
    media-supervision-timeout  300
    rtp-inactivity-timer       60
    rtcp-inactivity-timer      90
    update-ip-for-sdp-na       enabled
    nat-traversal              enabled
    latching                   passive
!

realm-config
    id                     access
    media-policy           default
    mm-in-realm            enabled
    mm-in-network          enabled
    mm-same-ip             enabled
    msm-release            enabled
!

# NAT keepalive — send RTCP to keep NAT bindings alive
media-manager
    rtp-keepalive-method   RTCP
    rtp-keepalive-interval 15
!
"""
    steps = [
        "Increase rtp-inactivity-timer to 60s (was 30s) to tolerate slow UE media startup",
        "Enable nat-traversal=enabled and latching=passive for behind-NAT endpoints",
        "Enable mm-in-realm, mm-in-network to force media through SBC for NAT traversal",
        "Set rtp-keepalive-method=RTCP every 15s to keep NAT bindings alive",
        "Check firewall ACLs: ensure RTP ports 10000-20000 are open bidirectionally",
        "Review UE SDP — if UE sends 0.0.0.0 connection address, latching is required",
    ]
    return body, steps


def _codec_mismatch_config():
    body = """\
# --- FIX: Codec policy — allow G.729 and AMR alongside G.711 ---

media-profile
    name                  ims-codec-policy
    media-criteria        requires-audio
    codec-policy
        allow-codecs      PCMA PCMU G729 AMR-NB AMR-WB OPUS telephone-event
        codec-order       PCMA PCMU G729 AMR-NB
        transcoding       disabled
        sdp-bandwidth     AS:128
    !
!

# Bind updated codec policy to access realm
realm-config
    id            access
    media-policy  ims-codec-policy
!

# Bind to core realm too
realm-config
    id            core
    media-policy  ims-codec-policy
!
"""
    steps = [
        "Update media-profile to allow-codecs: PCMA PCMU G729 AMR-NB AMR-WB OPUS",
        "Remove 'g711-only' restriction that was stripping G.729 (PT=18) from SDP",
        "Bind ims-codec-policy to both access and core realms",
        "If MGW does not support G.729, enable transcoding=enabled with appropriate license",
        "Monitor 488 rate: should drop to <1% after applying this config",
        "Verify with test call using G.729-only UE — expect 200 OK with G.729 in SDP answer",
    ]
    return body, steps


def _pcscf_down_config():
    body = """\
# --- FIX: Upstream P-CSCF unreachable — add failover session-agent ---

# Primary session agent (existing, restored)
session-agent
    hostname              pcscf01.ims.lab
    ip-address            10.0.2.10
    port                  5060
    transport-method      UDP
    realm-id              core
    description           Primary P-CSCF
    max-sessions          5000
    weight                10
    state                 enabled
    ping-method           OPTIONS
    ping-interval         10
    ping-send-mode        keep-alive
    out-of-service-response-code  503
    failover-response-codes       503,408,500
!

# Secondary session agent (NEW — failover target)
session-agent
    hostname              pcscf02.ims.lab
    ip-address            10.0.2.11
    port                  5060
    transport-method      UDP
    realm-id              core
    description           Secondary P-CSCF (failover)
    max-sessions          5000
    weight                5
    state                 enabled
    ping-method           OPTIONS
    ping-interval         10
    ping-send-mode        keep-alive
!

# Session group for active/standby failover
session-group
    group-name            pcscf-group
    app-protocol          SIP
    strategy              hunt
    dest
        agent             pcscf01.ims.lab
        agent             pcscf02.ims.lab
    !
!

# Update local-policy to use session group
local-policy
    from-address          *
    to-address            *
    source-realm          access
    policy-priority       5
    policy-attribute
        next-hop          pcscf-group
        realm             core
        action            none
    !
!
"""
    steps = [
        "Bring pcscf01 back online — check process/daemon status: `systemctl restart openimscore`",
        "Add secondary session-agent pcscf02 (10.0.2.11) as failover target",
        "Create session-group 'pcscf-group' with hunt strategy (primary → secondary)",
        "Update local-policy to route through pcscf-group instead of pcscf01 directly",
        "Set ping-interval=10s with failover-response-codes=503,408,500",
        "Test failover: shut pcscf01, verify calls route via pcscf02 within 30s",
        "Add P-CSCF health monitoring to NOC dashboard",
    ]
    return body, steps


def _srtp_dtls_config():
    body = """\
# --- FIX: SRTP/DTLS crypto suite mismatch — expand allowed cipher suites ---

media-sec-policy
    name                  ims-media-sec
    srtp-enabled          enabled
    srtp-auth-tag-bits    80
    srtp-crypto-suite     AES_CM_128_HMAC_SHA1_80 AES_256_CM_HMAC_SHA1_80 AES_256_GCM_SHA384
    dtls-enabled          enabled
    dtls-cipher-suite     ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
    dtls-version          DTLSv1.2
    srtp-key-exchange     dtls-srtp
!

# Bind to access sip-interface
sip-interface
    realm-id              access
    media-sec-policy      ims-media-sec
!

# Also bind to core interface
sip-interface
    realm-id              core
    media-sec-policy      ims-media-sec
!
"""
    steps = [
        "Expand srtp-crypto-suite to include AES_256_GCM_SHA384 alongside AES_CM_128",
        "Set dtls-cipher-suite to include both ECDHE-RSA-AES256 and AES128 variants",
        "Bind updated ims-media-sec policy to both access and core sip-interfaces",
        "Verify UE capabilities: most modern UEs support AES_256_GCM — add to suite list",
        "Test DTLS handshake: dtls failure rate should drop to <1%",
        "Enable SRTP passthrough if end-to-end encryption is required without SBC inspect",
    ]
    return body, steps


# ── helper ───────────────────────────────────────────────────────────────────

def _wrap_and_save(block: str, label: str) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"sbc_{label}_{ts}.acli"
    OUTPUT_DIR.mkdir(exist_ok=True)
    fpath = OUTPUT_DIR / fname
    fpath.write_text(block, encoding="utf-8")
    return {
        "success": True,
        "label": label,
        "file_path": str(fpath),
        "acli_config": block,
    }
