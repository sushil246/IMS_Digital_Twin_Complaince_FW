"""
Fault injection scenarios for Oracle SBC / IMS network digital twin.
Each scenario mutates the twin state AND returns a bundle of realistic log lines.
"""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
from ims_digital_twin.digital_twin.topology import ElementStatus


# ── helpers ──────────────────────────────────────────────────────────────────

def _ts(offset_sec: int = 0) -> str:
    t = datetime.now(timezone.utc) + timedelta(seconds=offset_sec)
    return t.strftime("%b %d %H:%M:%S")


def _call_id() -> str:
    return uuid.uuid4().hex[:16]


def _ext() -> str:
    return f"sip:+1{random.randint(2000000000,9999999999)}@ims.lab"


# ── scenario registry ─────────────────────────────────────────────────────────

SCENARIOS: Dict[str, dict] = {}


def register(key: str, name: str, description: str):
    def decorator(fn):
        SCENARIOS[key] = {"name": name, "description": description, "fn": fn}
        return fn
    return decorator


def inject(twin: NetworkStateTwin, scenario_key: str) -> Tuple[NetworkStateTwin, List[str]]:
    """Apply a named fault scenario to the twin; return (mutated_twin, log_lines)."""
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_key!r}. Available: {list(SCENARIOS)}")
    twin.injected_fault = scenario_key
    twin.incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    twin.snapshot_ts = datetime.now(timezone.utc).isoformat()
    logs = SCENARIOS[scenario_key]["fn"](twin)
    return twin, logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1 — SIP Registration Storm (DoS / Overload)
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "reg_storm",
    "SIP Registration Storm",
    "Flood of REGISTER requests overwhelms SBC, triggering rate-limit drops and CPU spike.",
)
def _reg_storm(twin: NetworkStateTwin) -> List[str]:
    sbc = twin.get_sbc()
    sbc.cpu_util_pct = 94.3
    sbc.mem_util_pct = 78.1
    sbc.active_sessions = 4988
    twin.add_node_alarm("sbc01", "CRITICAL: CPU utilization 94% — threshold 90%")
    twin.add_node_alarm("sbc01", "MAJOR: REGISTER rate 1820/s exceeds limit 200/s")
    twin.add_node_alarm("sbc01", "MAJOR: Registration cache 49800/50000 entries (99.6%)")
    twin.update_node_config("sbc01", ["dos_protection", "current_register_rate"], 1820)

    logs: List[str] = []
    base = 0
    for i in range(8):
        cid = _call_id()
        src = f"192.168.{random.randint(100,110)}.{random.randint(2,254)}"
        logs.append(f"{_ts(base+i)} sbc01 APKT[sipd]: REGISTER sip:ims.lab SIP/2.0 | "
                    f"src={src}:5060 | Call-ID={cid} | CSeq=1 REGISTER")
    logs.append(f"{_ts(8)} sbc01 APKT[aclilog]: WARNING rate-limiter: REGISTER rate=1820/s "
                f"exceeds configured max=200/s — dropping excess")
    for i in range(5):
        cid = _call_id()
        src = f"192.168.{random.randint(100,110)}.{random.randint(2,254)}"
        logs.append(f"{_ts(9+i)} sbc01 APKT[sipd]: REGISTER sip:ims.lab SIP/2.0 | "
                    f"src={src}:5060 | Call-ID={cid} — DROPPED (rate-limit)")
    logs.append(f"{_ts(15)} sbc01 APKT[sysmgr]: ALERT CPU utilization 94.3% (threshold 90%)")
    logs.append(f"{_ts(16)} sbc01 APKT[sysmgr]: ALERT memory 78.1% of 16GB allocated")
    logs.append(f"{_ts(17)} sbc01 APKT[regcache]: WARNING registration cache 49800/50000 entries "
                f"— new REGISTER requests will be rejected when full")
    logs.append(f"{_ts(18)} sbc01 APKT[sipd]: ERROR SIP 503 Service Unavailable sent to "
                f"192.168.105.22 — reason: overload protection active")
    logs.append(f"{_ts(20)} sbc01 APKT[sipd]: SIP/2.0 503 Service Unavailable | "
                f"Retry-After: 30 | Warning: 399 sbc01 \"Server overload\"")
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2 — TLS Certificate Expiry
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "tls_cert_expiry",
    "TLS Certificate Expiry",
    "Access-side TLS certificate expired — SIP/TLS registrations and calls fail.",
)
def _tls_cert_expiry(twin: NetworkStateTwin) -> List[str]:
    twin.add_node_alarm("sbc01", "CRITICAL: TLS certificate 'ims-tls-prof' expired 2026-06-01")
    twin.add_node_alarm("sbc01", "MAJOR: SIP/TLS handshake failures on access interface")
    twin.update_node_config("sbc01", ["tls_profile_status"], "EXPIRED")
    twin.update_node_config("sbc01", ["cert_expiry"], "2026-06-01")
    twin.set_node_status("sbc01", ElementStatus.DEGRADED)
    twin.set_link_status("ue", "sbc01", "DEGRADED", latency_ms=0.0, loss_pct=100.0)

    logs: List[str] = []
    for i in range(6):
        cid = _call_id()
        ue_ip = f"10.10.{random.randint(1,5)}.{random.randint(2,254)}"
        logs.append(f"{_ts(i)} sbc01 APKT[tls]: ERROR TLS handshake failed with {ue_ip}:50{i:02d} — "
                    f"ssl_error=SSL_ERROR_SSL reason=certificate has expired "
                    f"(notAfter=Jun  1 00:00:00 2026 GMT)")
    logs.append(f"{_ts(7)} sbc01 APKT[cert-mon]: CRITICAL certificate 'ims-tls-prof' "
                f"(CN=sbc01.ims.lab) expired 5 days ago — "
                f"renewal required immediately")
    logs.append(f"{_ts(8)} sbc01 APKT[sipd]: ERROR REGISTER from 10.10.2.45 rejected — "
                f"TLS session could not be established")
    logs.append(f"{_ts(9)} sbc01 APKT[sipd]: SIP/2.0 500 Server Internal Error | "
                f"Warning: 399 sbc01 \"TLS transport failure\"")
    logs.append(f"{_ts(10)} sbc01 APKT[tls]: INFO cipher=TLS_AES_256_GCM_SHA384 "
                f"peer=10.10.3.12 alert=bad certificate")
    logs.append(f"{_ts(12)} sbc01 APKT[aclilog]: CRITICAL Alarm raised: "
                f"tls-certificate-expiry severity=critical resource=ims-tls-prof")
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3 — One-Way Audio / RTP Media Timeout
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "rtp_timeout",
    "RTP Media Timeout (One-Way Audio)",
    "RTP stream from callee side stops flowing — media timeout triggers call clear.",
)
def _rtp_timeout(twin: NetworkStateTwin) -> List[str]:
    twin.add_node_alarm("sbc01", "MAJOR: RTP timeout on 48 active sessions — media not flowing")
    twin.add_node_alarm("sbc01", "MINOR: Media latch failures — NAT traversal issue suspected")
    twin.update_node_config("sbc01", ["media_manager", "rtp_timeout_events"], 48)
    twin.update_node_kpi("sbc01", active_sessions=1192)

    logs: List[str] = []
    for i in range(5):
        cid = _call_id()
        local_rtp = f"10.0.1.10:{random.randint(20000,30000)}"
        remote_rtp = f"192.168.{random.randint(50,60)}.{random.randint(2,200)}:{random.randint(20000,30000)}"
        logs.append(f"{_ts(i*6)} sbc01 APKT[mbcd]: WARNING media-flow-timeout "
                    f"call-id={cid} local={local_rtp} remote={remote_rtp} "
                    f"direction=egress duration=31s — no RTP packets received")
    logs.append(f"{_ts(30)} sbc01 APKT[mbcd]: ERROR RTP inactivity detected on 48 flows "
                f"exceeding rtp-inactivity-timer=30s")
    logs.append(f"{_ts(31)} sbc01 APKT[sipd]: INFO sending BYE for 48 sessions "
                f"reason=media-timeout")
    logs.append(f"{_ts(32)} sbc01 APKT[mbcd]: DEBUG NAT latch failed for "
                f"10.10.5.88:54200 — expected media from 10.10.5.88 but received "
                f"from 10.10.99.1 (NAT rebind?)")
    logs.append(f"{_ts(34)} sbc01 APKT[aclilog]: MAJOR Alarm raised: "
                f"rtp-media-timeout severity=major sessions-affected=48")
    logs.append(f"{_ts(36)} sbc01 APKT[mbcd]: INFO media-manager rtp-timeout-action=clear-call "
                f"— 48 calls cleared due to media inactivity")
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4 — SIP Codec / SDP Mismatch
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "codec_mismatch",
    "SIP Codec / SDP Mismatch",
    "Caller offers G.729 only; media profile on SBC strips it — 488 Not Acceptable Here.",
)
def _codec_mismatch(twin: NetworkStateTwin) -> List[str]:
    twin.add_node_alarm("sbc01", "MAJOR: High 488 error rate — codec negotiation failures")
    twin.update_node_config("sbc01", ["media_manager", "codec_policy"], "g711-only")
    twin.update_node_config("sbc01", ["media_manager", "sdp_mangling"], "strip-g729")

    logs: List[str] = []
    for i in range(4):
        cid = _call_id()
        caller = _ext()
        callee = _ext()
        logs.append(f"{_ts(i*3)} sbc01 APKT[sipd]: INVITE {callee} SIP/2.0 | "
                    f"From={caller} | Call-ID={cid} | "
                    f"SDP-offer: m=audio 5004 RTP/AVP 18 8 (G.729 G.711)")
        logs.append(f"{_ts(i*3+1)} sbc01 APKT[sdpman]: INFO codec-policy=g711-only "
                    f"stripping PT 18 (G.729) from SDP offer Call-ID={cid}")
        logs.append(f"{_ts(i*3+2)} sbc01 APKT[sipd]: SIP/2.0 488 Not Acceptable Here | "
                    f"Call-ID={cid} | Warning: 304 sbc01 \"Incompatible media format\" | "
                    f"answer: m=audio 0 RTP/AVP (no common codec)")
    logs.append(f"{_ts(14)} sbc01 APKT[aclilog]: MAJOR 488 error rate 28% over last 60s — "
                f"threshold 5% — codec policy mismatch suspected")
    logs.append(f"{_ts(15)} sbc01 APKT[sdpman]: DEBUG media-profile='g711-only' does not "
                f"include G.729 (PT=18) — update media-profile to include G.729 and AMR-NB")
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 5 — Upstream P-CSCF Unreachable (SIP 503 Cascade)
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "pcscf_down",
    "Upstream P-CSCF Unreachable",
    "SBC core session-agent to P-CSCF fails health-check — all INVITEs return 503.",
)
def _pcscf_down(twin: NetworkStateTwin) -> List[str]:
    twin.set_node_status("pcscf01", ElementStatus.DOWN)
    twin.set_link_status("sbc01", "pcscf01", "DOWN", latency_ms=0.0, loss_pct=100.0)
    twin.add_node_alarm("sbc01", "CRITICAL: session-agent 'pcscf01' OUT-OF-SERVICE")
    twin.add_node_alarm("sbc01", "CRITICAL: No available next-hop — all INVITEs failing")
    twin.add_node_alarm("pcscf01", "CRITICAL: Process died — restart pending")
    twin.update_node_kpi("pcscf01", status=ElementStatus.DOWN, active_sessions=0)

    logs: List[str] = []
    logs.append(f"{_ts(0)} sbc01 APKT[sipd]: OPTIONS sip:10.0.2.10:5060 SIP/2.0 — "
                f"health-check to session-agent pcscf01")
    logs.append(f"{_ts(1)} sbc01 APKT[sipd]: ERROR OPTIONS to pcscf01 (10.0.2.10:5060) "
                f"timed out after 500ms — attempt 1/3")
    logs.append(f"{_ts(2)} sbc01 APKT[sipd]: ERROR OPTIONS to pcscf01 timed out — attempt 2/3")
    logs.append(f"{_ts(3)} sbc01 APKT[sipd]: ERROR OPTIONS to pcscf01 timed out — attempt 3/3")
    logs.append(f"{_ts(4)} sbc01 APKT[sipd]: CRITICAL session-agent 'pcscf01' marked "
                f"OUT-OF-SERVICE after 3 consecutive health-check failures")
    for i in range(5):
        cid = _call_id()
        caller = _ext()
        callee = _ext()
        logs.append(f"{_ts(5+i)} sbc01 APKT[sipd]: INVITE {callee} SIP/2.0 | "
                    f"From={caller} | Call-ID={cid} — "
                    f"local-policy route=pcscf01 — FAILED: agent OUT-OF-SERVICE")
        logs.append(f"{_ts(5+i)} sbc01 APKT[sipd]: SIP/2.0 503 Service Unavailable | "
                    f"Call-ID={cid} | Retry-After: 60")
    logs.append(f"{_ts(11)} sbc01 APKT[aclilog]: CRITICAL Alarm: session-agent-oos "
                f"agent=pcscf01 — no failover target configured")
    logs.append(f"{_ts(12)} pcscf01 kernel: ERROR segfault at 0000000000000000 ip "
                f"00007f8a3c4d1a2b sp 00007ffcb9e3d510 — sip daemon crashed")
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 6 — SRTP / DTLS Negotiation Failure
# ─────────────────────────────────────────────────────────────────────────────
@register(
    "srtp_dtls_fail",
    "SRTP/DTLS Negotiation Failure",
    "DTLS handshake fails for SRTP key exchange — calls connect but have no media.",
)
def _srtp_dtls_fail(twin: NetworkStateTwin) -> List[str]:
    twin.add_node_alarm("sbc01", "MAJOR: DTLS handshake failure rate 62% on access realm")
    twin.add_node_alarm("sbc01", "MAJOR: SRTP crypto suite mismatch — AES_CM_128 vs AES_256_GCM")
    twin.update_node_config("sbc01", ["media_manager", "srtp_crypto_suite"],
                             "AES_CM_128_HMAC_SHA1_80")
    twin.update_node_config("sbc01", ["media_manager", "dtls_failure_count"], 142)

    logs: List[str] = []
    for i in range(5):
        cid = _call_id()
        ue_ip = f"10.10.{random.randint(1,8)}.{random.randint(2,250)}"
        logs.append(f"{_ts(i*4)} sbc01 APKT[mbcd]: INFO DTLS handshake initiated "
                    f"call-id={cid} peer={ue_ip} role=server")
        logs.append(f"{_ts(i*4+1)} sbc01 APKT[mbcd]: ERROR DTLS handshake failed "
                    f"call-id={cid} peer={ue_ip} "
                    f"reason=no-common-cipher local-suite=AES_CM_128_HMAC_SHA1_80 "
                    f"peer-suite=AES_256_GCM_SHA384")
        logs.append(f"{_ts(i*4+2)} sbc01 APKT[sipd]: INFO INVITE answered 200 OK "
                    f"call-id={cid} — media=NO (DTLS failed) — call will have no audio")
    logs.append(f"{_ts(22)} sbc01 APKT[mbcd]: MAJOR DTLS failure rate 62% (142/229 attempts) "
                f"over last 5 minutes — crypto suite config mismatch")
    logs.append(f"{_ts(23)} sbc01 APKT[sdpman]: DEBUG SDP crypto line from UE: "
                f"a=crypto:1 AES_256_CM_HMAC_SHA1_80 — SBC media-sec-policy "
                f"allows only AES_CM_128_HMAC_SHA1_80")
    logs.append(f"{_ts(25)} sbc01 APKT[aclilog]: MAJOR Alarm: srtp-negotiation-failure "
                f"realm=access failure-count=142")
    return logs


# ── list all scenarios ────────────────────────────────────────────────────────

def list_scenarios() -> List[Dict]:
    return [
        {"key": k, "name": v["name"], "description": v["description"]}
        for k, v in SCENARIOS.items()
    ]
