"""
IMS User Simulator — generates realistic SIP traces and log entries
for three virtual UEs.  Outcome depends on the current fault scenario.
Compatible with Python 3.9+.
"""
from __future__ import annotations
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

NL = "\n"   # avoid backslash inside f-string {} on Python 3.9

# ── Virtual users ─────────────────────────────────────────────────────────────

USERS = {
    "alice": {
        "name":   "Alice Smith",
        "uri":    "sip:alice@ims.lab",
        "ip":     "10.10.1.10",
        "port":   56000,
        "ua":     "Zoiper 5.6.0 (iOS 17)",
        "codec":  "G.711/G.729/OPUS",
        "imei":   "354022-11-234567-8",
        "imsi":   "310260001234567",
        "color":  "#7c3aed",
        "avatar": "👩",
    },
    "bob": {
        "name":   "Bob Johnson",
        "uri":    "sip:bob@ims.lab",
        "ip":     "10.10.1.11",
        "port":   56001,
        "ua":     "Linphone 5.3.1 (Android 14)",
        "codec":  "G.711/AMR-NB/AMR-WB",
        "imei":   "357031-11-567890-1",
        "imsi":   "310260001234568",
        "color":  "#0369a1",
        "avatar": "👨",
    },
    "charlie": {
        "name":   "Charlie Davis",
        "uri":    "sip:charlie@ims.lab",
        "ip":     "10.10.1.12",
        "port":   56002,
        "ua":     "MicroSIP 3.21.3 (Windows 11)",
        "codec":  "G.729",        # G.729-only triggers codec_mismatch
        "imei":   "012345-67-890123-4",
        "imsi":   "310260001234569",
        "color":  "#b45309",
        "avatar": "🧑",
    },
}


@dataclass
class SimResult:
    action:       str
    user:         str
    target:       Optional[str]
    success:      bool
    response:     str
    sip_trace:    str
    log_lines:    List[str]
    ai_context:   str
    duration_ms:  int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def _branch() -> str:
    return "z9hG4bK" + uuid.uuid4().hex[:12]

def _callid(user: str) -> str:
    return uuid.uuid4().hex[:8] + "@" + USERS[user]["ip"]

def _hdr(lines: List[str]) -> str:
    return NL.join("│ " + l for l in lines)

def _box(title: str, lines: List[str]) -> str:
    sep = "─" * (len(title) + 3)
    return "┌─ " + title + NL + _hdr(lines) + NL + "└" + sep


# ── Outcome per scenario ──────────────────────────────────────────────────────

def _outcome(phase: str, scenario: Optional[str], action: str):
    if phase in ("idle", "fixed"):
        return True, "200 OK", None
    fails = {
        "reg_storm":       ("REGISTER", "503 Service Unavailable", "SBC rate-limit: REGISTER rate 1820/s > 200/s"),
        "tls_cert_expiry": (None,        "TLS_HANDSHAKE_FAIL",      "SSL_ERROR: certificate expired (notAfter=Jun 1 2026)"),
        "codec_mismatch":  ("INVITE",    "488 Not Acceptable Here",  "SBC codec-policy strips G.729 — no common codec"),
        "pcscf_down":      (None,        "503 Service Unavailable",  "session-agent pcscf01 OUT-OF-SERVICE"),
        "srtp_dtls_fail":  ("INVITE",    "200 OK (no media)",        "DTLS handshake failed — cipher suite mismatch"),
        "rtp_timeout":     ("INVITE",    "200 OK (one-way audio)",   "RTP inactivity 31s > rtp-inactivity-timer 30s"),
    }
    if scenario in fails:
        trigger_action, code, reason = fails[scenario]
        if trigger_action is None or action == trigger_action:
            return False, code, reason
    return True, "200 OK", None


# ── REGISTER ──────────────────────────────────────────────────────────────────

def simulate_register(user_id: str, phase: str, scenario: Optional[str]) -> SimResult:
    u = USERS[user_id]
    br = _branch()
    cid = _callid(user_id)
    success, resp, fail_reason = _outcome(phase, scenario, "REGISTER")
    dur = random.randint(35, 80) if success else random.randint(2, 15)
    tag1 = "reg-" + uuid.uuid4().hex[:6]
    tag2 = "scscf-" + uuid.uuid4().hex[:8]
    icid = uuid.uuid4().hex[:16]

    req_hdrs = [
        "REGISTER sip:ims.lab SIP/2.0",
        "Via: SIP/2.0/TLS " + u["ip"] + ":" + str(u["port"]) + ";branch=" + br + ";rport",
        "From: <" + u["uri"] + ">;tag=" + tag1,
        "To: <" + u["uri"] + ">",
        "Call-ID: " + cid,
        "CSeq: 1 REGISTER",
        "Max-Forwards: 70",
        "Contact: <sip:" + u["ip"] + ":" + str(u["port"]) + ";transport=tls>;expires=3600",
        "Expires: 3600",
        "User-Agent: " + u["ua"],
        "Supported: path,gruu,outbound",
        "Content-Length: 0",
    ]
    sbc_via = "z9hG4bKsbc-" + uuid.uuid4().hex[:8]
    fwd_hdrs = [
        "REGISTER sip:ims.lab SIP/2.0",
        "Via: SIP/2.0/UDP 10.0.1.10:5060;branch=" + sbc_via + ";rport",
        "Via: SIP/2.0/TLS " + u["ip"] + ":" + str(u["port"]) + ";branch=" + br,
        "From: <" + u["uri"] + ">;tag=" + tag1,
        "To: <" + u["uri"] + ">",
        "Call-ID: " + cid,
        "CSeq: 1 REGISTER",
        "Max-Forwards: 69",
        'P-Access-Network-Info: 3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=310260001',
        'P-Visited-Network-ID: "ims.lab"',
        "Path: <sip:pcscf01.ims.lab:5060;lr>",
        "Contact: <sip:" + u["ip"] + ":" + str(u["port"]) + ";transport=tls>;expires=3600",
        "Content-Length: 0",
    ]

    title = "╔══ SIP TRACE: " + u["name"] + " REGISTER  [" + _ts() + "] ══╗"

    if success:
        ok_hdrs = [
            "SIP/2.0 200 OK",
            "Via: SIP/2.0/TLS " + u["ip"] + ":" + str(u["port"]) + ";branch=" + br + ";received=" + u["ip"],
            "From: <" + u["uri"] + ">;tag=" + tag1,
            "To: <" + u["uri"] + ">;tag=" + tag2,
            "Call-ID: " + cid,
            "CSeq: 1 REGISTER",
            "Service-Route: <sip:orig@scscf01.ims.lab:6060;lr>",
            "Path: <sip:pcscf01.ims.lab:5060;lr>",
            "P-Associated-URI: <" + u["uri"] + ">",
            "Contact: <sip:" + u["ip"] + ":" + str(u["port"]) + ";transport=tls>;expires=3600",
            'P-Charging-Vector: icid-value="' + icid + '"',
            "Content-Length: 0",
        ]
        req_box = _box("REQUEST", req_hdrs)
        fwd_box = _box("FORWARDED REQUEST (P-headers added)", fwd_hdrs)
        ok_box  = _box("200 OK", ok_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + u["ip"] + ":" + str(u["port"]) + "] → [SBC 10.0.1.10:5061]  (SIP/TLS)" + NL +
            req_box + NL + NL +
            "→ [SBC 10.0.1.10] → [P-CSCF 10.0.2.10:5060]  (SIP/UDP)" + NL +
            fwd_box + NL + NL +
            "  ↕  I-CSCF UAR → HSS  (Diameter Cx)" + NL +
            "  ↕  HSS UAA → I-CSCF  (assigned: scscf01.ims.lab)" + NL +
            "  ↕  S-CSCF MAR → HSS  (authentication vectors)" + NL +
            "  ↕  HSS MAA → S-CSCF  (AKAv2-MD5 vectors)" + NL +
            "  ↕  S-CSCF SAR → HSS  (server assignment)" + NL +
            "  ↕  HSS SAA → S-CSCF  (subscriber profile downloaded)" + NL + NL +
            "← [S-CSCF → I-CSCF → P-CSCF → SBC → UE]" + NL +
            ok_box + NL + NL +
            "✓  REGISTRATION SUCCESSFUL  (" + str(dur) + "ms)" + NL +
            "   Registered: " + u["uri"] + " → " + u["ip"] + ":" + str(u["port"]) + NL +
            "   Expires   : 3600s" + NL +
            "   S-CSCF    : scscf01.ims.lab" + NL +
            "   Auth      : AKAv2-MD5"
        )
        logs = [
            _ts() + " sbc01 APKT[sipd]: REGISTER " + u["uri"] + " from " + u["ip"] + " — TLS OK",
            _ts() + " sbc01 APKT[sipd]: SIP/2.0 200 OK — REGISTER " + u["uri"] + " accepted",
            _ts() + " pcscf01 kamailio[REGISTER]: " + u["uri"] + " registered via path pcscf01.ims.lab",
            _ts() + " scscf01 kamailio[REGISTER]: SAR accepted for " + u["uri"] + " — expires=3600",
        ]
        ai_ctx = u["name"] + " REGISTER succeeded in " + str(dur) + "ms — auth OK, S-CSCF assigned"

    elif "TLS" in resp:
        tls_box = _box("TLS HANDSHAKE FAILED", [
            "SSL_ERROR: certificate has expired",
            "notAfter=Jun  1 00:00:00 2026 GMT",
            "alert=bad_certificate",
            "Connection reset by peer",
        ])
        trace = (
            title + NL + NL +
            "→ [" + u["ip"] + ":" + str(u["port"]) + "] → [SBC 10.0.1.10:5061]  (SIP/TLS attempt)" + NL +
            tls_box + NL + NL +
            "✗  REGISTRATION FAILED  (" + str(dur) + "ms)" + NL +
            "   Reason: " + str(fail_reason) + NL +
            "   Fix   : Renew TLS certificate (tls-profile: ims-tls-prof)"
        )
        logs = [
            _ts() + " sbc01 APKT[tls]: ERROR TLS handshake with " + u["ip"] + " — certificate expired",
            _ts() + " sbc01 APKT[sipd]: REGISTER from " + u["ip"] + " rejected — TLS transport failure",
        ]
        ai_ctx = u["name"] + " REGISTER FAILED — " + str(fail_reason)

    elif "rate" in (fail_reason or "").lower():
        overload_msg = 'Warning: 399 sbc01 "Server overload"'
        err503_box = _box("503 Service Unavailable", [
            "SIP/2.0 503 Service Unavailable",
            "Retry-After: 30",
            overload_msg,
        ])
        req_box = _box("REQUEST (DROPPED by rate-limiter)", req_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + u["ip"] + ":" + str(u["port"]) + "] → [SBC 10.0.1.10:5061]" + NL +
            req_box + NL + NL +
            err503_box + NL + NL +
            "✗  REGISTRATION FAILED  (" + str(dur) + "ms)" + NL +
            "   Reason: " + str(fail_reason)
        )
        logs = [
            _ts() + " sbc01 APKT[aclilog]: WARNING rate-limiter REGISTER rate=1820/s > max=200/s",
            _ts() + " sbc01 APKT[sipd]: SIP/2.0 503 Service Unavailable — overload protection",
        ]
        ai_ctx = u["name"] + " REGISTER FAILED — " + str(fail_reason)

    else:
        reason_warn = "Warning: 399 sbc01 \"" + str(fail_reason) + "\""
        err_box = _box(resp, ["SIP/2.0 " + resp, "Retry-After: 60", reason_warn])
        req_box = _box("REQUEST", req_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + u["ip"] + "] → [SBC 10.0.1.10:5061]" + NL +
            req_box + NL + NL +
            err_box + NL + NL +
            "✗  REGISTRATION FAILED  (" + str(dur) + "ms)" + NL +
            "   Reason: " + str(fail_reason)
        )
        logs = [_ts() + " sbc01 APKT[sipd]: REGISTER from " + u["ip"] + " — " + resp]
        ai_ctx = u["name"] + " REGISTER FAILED — " + str(fail_reason)

    return SimResult("REGISTER", user_id, None, success, resp, trace, logs, ai_ctx, dur)


# ── INVITE (voice call) ───────────────────────────────────────────────────────

def simulate_call(caller_id: str, callee_id: str, phase: str, scenario: Optional[str]) -> SimResult:
    caller = USERS[caller_id]
    callee = USERS[callee_id]
    br  = _branch()
    cid = _callid(caller_id)
    success, resp, fail_reason = _outcome(phase, scenario, "INVITE")
    dur = random.randint(120, 280) if success else random.randint(5, 40)
    rtp_c = random.randint(20000, 25000)
    rtp_e = random.randint(25000, 30000)
    ssrc  = uuid.uuid4().hex[:8].upper()
    tag_f = "call-" + uuid.uuid4().hex[:6]
    tag_t = "scscf-" + uuid.uuid4().hex[:8]
    crypto_key = uuid.uuid4().hex[:40]
    crypto_key2 = uuid.uuid4().hex[:40]
    sdp_pt = "18 8 101" if caller["codec"] == "G.729" else "8 0 18 101"

    invite_hdrs = [
        "INVITE " + callee["uri"] + " SIP/2.0",
        "Via: SIP/2.0/TLS " + caller["ip"] + ":" + str(caller["port"]) + ";branch=" + br + ";rport",
        "From: <" + caller["uri"] + ">;tag=" + tag_f,
        "To: <" + callee["uri"] + ">",
        "Call-ID: " + cid,
        "CSeq: 1 INVITE",
        "Max-Forwards: 70",
        "Contact: <sip:" + caller["ip"] + ":" + str(caller["port"]) + ";transport=tls>",
        "Allow: INVITE,ACK,BYE,CANCEL,UPDATE,PRACK,OPTIONS",
        "Content-Type: application/sdp",
        "Content-Length: 210",
        "",
        "v=0",
        "o=- " + str(random.randint(1000000, 9999999)) + " 1 IN IP4 " + caller["ip"],
        "s=IMS Call",
        "c=IN IP4 " + caller["ip"],
        "t=0 0",
        "m=audio " + str(rtp_c) + " RTP/SAVPF " + sdp_pt,
        "a=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:" + crypto_key,
        "a=rtpmap:8 PCMA/8000",
        "a=rtpmap:18 G729/8000",
        "a=rtpmap:101 telephone-event/8000",
        "a=sendrecv",
    ]

    title = ("╔══ SIP TRACE: " + caller["name"] + " → " + callee["name"] +
             " CALL  [" + _ts() + "] ══╗")
    invite_box = _box("INVITE", invite_hdrs)

    if "no media" in resp or "one-way" in resp:
        media_fail = "DTLS cipher mismatch" if "DTLS" in (fail_reason or "") else "RTP timeout 31s"
        ok_hdrs = [
            "SIP/2.0 200 OK",
            "From: <" + caller["uri"] + ">;tag=" + tag_f,
            "To: <" + callee["uri"] + ">;tag=" + tag_t,
            "Call-ID: " + cid, "CSeq: 1 INVITE",
            "Contact: <sip:" + callee["ip"] + ":" + str(callee["port"]) + ">",
            "m=audio " + str(rtp_e) + " RTP/SAVPF 8",
            "a=crypto:1 AES_256_GCM_SHA384 inline:...",
            "a=sendrecv",
        ]
        ok_box = _box("200 OK", ok_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + caller["ip"] + "] → [SBC] → [P-CSCF] → [S-CSCF] → [" + callee["ip"] + "]" + NL +
            invite_box + NL + NL +
            "← 100 Trying  ← 180 Ringing  ← 200 OK (SIP layer OK)" + NL +
            ok_box + NL + NL +
            "→ ACK sent — call established at SIP layer" + NL + NL +
            "⚠  MEDIA FAILURE: " + media_fail + NL +
            "   RTP port local : " + str(rtp_c) + "  remote: " + str(rtp_e) + NL +
            "   Status         : " + resp + NL +
            "   " + str(fail_reason)
        )
        logs = [
            _ts() + " sbc01 APKT[sipd]: INVITE " + callee["uri"] + " from " + caller["ip"] + " — 200 OK (SIP)",
            _ts() + " sbc01 APKT[mbcd]: ERROR media failure Call-ID=" + cid + " — " + str(fail_reason),
        ]
        ai_ctx = caller["name"] + " → " + callee["name"] + " call connected but " + str(fail_reason)
        actual_success = False

    elif not success:
        warn_hdr = 'Warning: 399 sbc01 "' + str(fail_reason) + '"'
        err_hdrs = ["SIP/2.0 " + resp, "Call-ID: " + cid, "CSeq: 1 INVITE", warn_hdr]
        err_box = _box(resp, err_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + caller["ip"] + "] → [SBC 10.0.1.10]" + NL +
            invite_box + NL + NL +
            err_box + NL + NL +
            "✗  CALL FAILED  (" + str(dur) + "ms)" + NL +
            "   Reason: " + str(fail_reason)
        )
        logs = [
            _ts() + " sbc01 APKT[sipd]: INVITE " + callee["uri"] + " from " + caller["ip"] + " — " + resp,
            _ts() + " sbc01 APKT[sipd]: ERROR " + str(fail_reason),
        ]
        ai_ctx = caller["name"] + " → " + callee["name"] + " INVITE failed: " + str(fail_reason)
        actual_success = False

    else:
        ok_hdrs = [
            "SIP/2.0 200 OK",
            "From: <" + caller["uri"] + ">;tag=" + tag_f,
            "To: <" + callee["uri"] + ">;tag=" + tag_t,
            "Call-ID: " + cid, "CSeq: 1 INVITE",
            "Contact: <sip:" + callee["ip"] + ":" + str(callee["port"]) + ">",
            "Record-Route: <sip:scscf01.ims.lab:6060;lr>",
            "Record-Route: <sip:pcscf01.ims.lab:5060;lr>",
            "Content-Type: application/sdp",
            "m=audio " + str(rtp_e) + " RTP/SAVPF 8",
            "a=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:" + crypto_key2,
            "a=rtpmap:8 PCMA/8000",
            "a=sendrecv",
            "a=ssrc:" + str(int(ssrc, 16)) + " cname:" + callee["uri"],
        ]
        ok_box = _box("200 OK", ok_hdrs)
        trace = (
            title + NL + NL +
            "→ [" + caller["ip"] + ":" + str(caller["port"]) + "] → [SBC] → [P-CSCF] → [S-CSCF] → [" + callee["ip"] + "]" + NL +
            invite_box + NL + NL +
            "← [SBC] ← 100 Trying" + NL +
            "  ↕  PCRF Rx AAR — QoS bearer requested (GBR_voice QCI=1)" + NL +
            "  ↕  PCRF Rx AAA — QoS granted (64kbps GBR)" + NL +
            "← [S-CSCF] ← 180 Ringing" + NL + NL +
            ok_box + NL + NL +
            "→ ACK  (3-way handshake complete)" + NL + NL +
            "  SRTP path: " + caller["ip"] + ":" + str(rtp_c) + " ←AES_CM_128→ SBC ←SRTP→ " + callee["ip"] + ":" + str(rtp_e) + NL +
            "  Codec: PCMA/8000  SSRC: 0x" + ssrc + "  Ptime: 20ms" + NL + NL +
            "✓  CALL ESTABLISHED  (" + str(dur) + "ms)" + NL +
            "   " + caller["name"] + " ↔ " + callee["name"]
        )
        logs = [
            _ts() + " sbc01 APKT[sipd]: INVITE " + callee["uri"] + " from " + caller["ip"] + " — routed to pcscf01",
            _ts() + " sbc01 APKT[sipd]: SIP/2.0 200 OK — Call-ID=" + cid + " established",
            _ts() + " sbc01 APKT[mbcd]: RTP flow " + caller["ip"] + ":" + str(rtp_c) + " ↔ " + callee["ip"] + ":" + str(rtp_e) + " SRTP OK",
            _ts() + " pcscf01 kamailio[INVITE]: Rx AAR granted — GBR_voice QCI=1 for " + cid,
        ]
        ai_ctx = caller["name"] + " → " + callee["name"] + " call OK (" + str(dur) + "ms), SRTP active"
        actual_success = True

    return SimResult("CALL", caller_id, callee_id, actual_success,
                     resp, trace, logs, ai_ctx, dur)


# ── MESSAGE ───────────────────────────────────────────────────────────────────

def simulate_message(sender_id: str, recipient_id: str, phase: str, scenario: Optional[str]) -> SimResult:
    sender = USERS[sender_id]
    recip  = USERS[recipient_id]
    br  = _branch()
    cid = _callid(sender_id)
    success, resp, fail_reason = _outcome(phase, scenario, "MESSAGE")
    dur = random.randint(20, 60) if success else random.randint(3, 15)
    bodies = ["Hey, are you free for a call?", "Meeting moved to 3pm", "Can you hear me?", "Testing IMS messaging"]
    body = random.choice(bodies)
    tag1 = "msg-" + uuid.uuid4().hex[:6]

    title = "╔══ SIP MESSAGE: " + sender["name"] + " → " + recip["name"] + "  [" + _ts() + "] ══╗"
    msg_hdrs = [
        "MESSAGE " + recip["uri"] + " SIP/2.0",
        "Via: SIP/2.0/TLS " + sender["ip"] + ":" + str(sender["port"]) + ";branch=" + br,
        "From: <" + sender["uri"] + ">;tag=" + tag1,
        "To: <" + recip["uri"] + ">",
        "Call-ID: " + cid, "CSeq: 1 MESSAGE",
        "Content-Type: text/plain; charset=UTF-8",
        "Content-Length: " + str(len(body)),
        "", body,
    ]
    msg_box = _box("MESSAGE", msg_hdrs)
    if success:
        trace = title + NL + NL + msg_box + NL + NL + "← SIP/2.0 200 OK  (" + str(dur) + "ms)" + NL + NL + "✓  MESSAGE DELIVERED"
        logs = [_ts() + " sbc01 APKT[sipd]: MESSAGE " + recip["uri"] + " from " + sender["ip"] + " — 200 OK"]
        ai_ctx = "SIP MESSAGE " + sender["name"] + " → " + recip["name"] + " delivered OK"
    else:
        trace = (title + NL + NL + msg_box + NL + NL +
                 "← SIP/2.0 " + resp + "  (" + str(dur) + "ms)" + NL +
                 "✗  MESSAGE FAILED — " + str(fail_reason))
        logs = [_ts() + " sbc01 APKT[sipd]: MESSAGE from " + sender["ip"] + " — " + resp]
        ai_ctx = "SIP MESSAGE " + sender["name"] + " → " + recip["name"] + " FAILED: " + str(fail_reason)

    return SimResult("MESSAGE", sender_id, recipient_id, success, resp, trace, logs, ai_ctx, dur)


# ── FLOOD ─────────────────────────────────────────────────────────────────────

def simulate_flood(user_id: str, count: int, phase: str, scenario: Optional[str]) -> SimResult:
    u = USERS[user_id]
    rate = count * 12
    title = "╔══ REGISTRATION FLOOD: " + u["name"] + " × " + str(count) + " REGISTERs  [" + _ts() + "] ══╗"
    lines = [title, ""]
    for i in range(min(count, 6)):
        lines.append("→ REGISTER sip:ims.lab SIP/2.0  Via: ...;branch=" + _branch())
    if count > 6:
        lines.append("  ... " + str(count - 6) + " more ...")
    lines += [
        "",
        "SBC Rate Limiter triggered:",
        "  REGISTER rate = " + str(rate) + "/s  >  dos-protection max = 200/s",
        "  Action: DROP excess, send 503 Retry-After:30",
        "  Source " + u["ip"] + " added to deny list for 30s",
        "",
        "✗  FLOOD BLOCKED — " + str(count) + " requests sent, " + str(rate) + "/s detected",
    ]
    logs = [
        _ts() + " sbc01 APKT[aclilog]: WARNING rate-limiter: REGISTER rate=" + str(rate) + "/s > 200/s",
        _ts() + " sbc01 APKT[sipd]: SIP/2.0 503 Service Unavailable — Retry-After: 30",
        _ts() + " sbc01 APKT[sysmgr]: ALERT CPU utilization 94.3% threshold 90%",
        _ts() + " sbc01 APKT[regcache]: WARNING registration cache 49800/50000 entries",
    ]
    return SimResult("FLOOD", user_id, None, False, "503 (rate-limited)",
                     NL.join(lines), logs,
                     u["name"] + " sent " + str(count) + " REGISTERs — SBC rate-limiter blocked flood", 0)


# ── DEREGISTER ────────────────────────────────────────────────────────────────

def simulate_deregister(user_id: str, phase: str, scenario: Optional[str]) -> SimResult:
    u = USERS[user_id]
    br = _branch()
    cid = _callid(user_id)
    tag1 = "dereg-" + uuid.uuid4().hex[:6]
    title = "╔══ SIP TRACE: " + u["name"] + " DE-REGISTER  [" + _ts() + "] ══╗"
    hdrs = [
        "REGISTER sip:ims.lab SIP/2.0",
        "Via: SIP/2.0/TLS " + u["ip"] + ":" + str(u["port"]) + ";branch=" + br,
        "From: <" + u["uri"] + ">;tag=" + tag1,
        "To: <" + u["uri"] + ">",
        "Call-ID: " + cid, "CSeq: 2 REGISTER",
        "Contact: *",
        "Expires: 0",
        "Content-Length: 0",
    ]
    der_box = _box("REGISTER Expires:0", hdrs)
    trace = (title + NL + NL + der_box + NL + NL +
             "← SIP/2.0 200 OK" + NL + NL +
             "✓  DE-REGISTERED — " + u["uri"] + " removed from location table")
    logs = [
        _ts() + " sbc01 APKT[sipd]: REGISTER Expires:0 " + u["uri"] + " — de-registration",
        _ts() + " scscf01 kamailio[REGISTER]: " + u["uri"] + " de-registered — SAR USER_DEREGISTRATION",
    ]
    return SimResult("DEREGISTER", user_id, None, True, "200 OK",
                     trace, logs, u["name"] + " de-registered successfully", 22)
