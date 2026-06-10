"""
Kamailio SIP Router Simulator with compliance-specific fault injection.
Each scenario injects a realistic failure that violates one or more frameworks,
producing authentic Kamailio log lines and SIP traces.
"""
from __future__ import annotations
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

# ── Topology (reused from twin, but standalone for portability) ───────────────

KAMAILIO_NODES = {
    "kam01": {"ip": "10.0.1.20", "role": "SIP Proxy / IMS Core", "port": 5060},
    "pcscf01": {"ip": "10.0.2.10", "role": "P-CSCF", "port": 5060},
    "scscf01": {"ip": "10.0.2.30", "role": "S-CSCF", "port": 5060},
    "hss01": {"ip": "10.0.3.10", "role": "HSS / Diameter", "port": 3868},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts(offset_sec: int = 0) -> str:
    t = datetime.now(timezone.utc) + timedelta(seconds=offset_sec)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _call_id() -> str:
    return uuid.uuid4().hex[:20] + "@ims.lab"


def _subscriber(msisdn: str) -> str:
    return f"sip:+{msisdn}@ims.lab"


def _real_msisdn() -> str:
    return f"447{random.randint(700000000, 799999999)}"


def _pseudo_id() -> str:
    h = uuid.uuid4().hex[:16]
    return f"sip:session-{h}@ims.lab"


# ── Compliance scenario registry ──────────────────────────────────────────────

COMPLIANCE_SCENARIOS: Dict[str, dict] = {}


def _register(key: str, name: str, description: str, frameworks: List[str]):
    def decorator(fn):
        COMPLIANCE_SCENARIOS[key] = {
            "name": name,
            "description": description,
            "frameworks": frameworks,
            "fn": fn,
        }
        return fn
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C1 — SIP PII Header Leak (UK TSA + OECD AI)
# Kamailio logs expose unmasked E.164 MSISDN in To/From headers
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "pii_sip_header_leak",
    "SIP PII Header Leak",
    "Kamailio logs expose unmasked subscriber MSISDNs in To/From/P-Asserted-Identity headers. "
    "Violates UK TSA signaling data anonymization and OECD AI privacy-by-design requirements.",
    frameworks=["uk_tsa", "oecd_ai"],
)
def _pii_sip_header_leak(twin) -> Tuple[List[str], str, str]:
    logs = []
    kamailio_cfg_issue = """\
# VULNERABLE: Kamailio logging raw SIP headers with unmasked MSISDNs
# In kamailio.cfg — this logs PII directly:
xlog("L_INFO", "CALL: $fU -> $tU via $rm\\n");
"""
    trace_lines = []
    for i in range(6):
        cid = _call_id()
        caller_msisdn = _real_msisdn()
        callee_msisdn = _real_msisdn()
        caller_uri = _subscriber(caller_msisdn)
        callee_uri = _subscriber(callee_msisdn)
        logs.append(f"[{_ts(i)}] kam01 INFO: {caller_uri} -> {callee_uri} INVITE Call-ID={cid}")
        logs.append(f"[{_ts(i)}] kam01 INFO: From: <{caller_uri}>;tag=abc{i} | "
                    f"To: <{callee_uri}> | P-Asserted-Identity: <{caller_uri}>")
        logs.append(f"[{_ts(i)}] kam01 DEBUG: REGISTER sip:ims.lab | "
                    f"From: <sip:+{caller_msisdn}@ims.lab> | Contact: <sip:+{caller_msisdn}@10.10.1.{i+2}:5060>")
        trace_lines.append(f"INVITE {callee_uri} SIP/2.0")
        trace_lines.append(f"From: <{caller_uri}>;tag=xyz{i}")
        trace_lines.append(f"To: <{callee_uri}>")
        trace_lines.append(f"P-Asserted-Identity: <{caller_uri}>")
        trace_lines.append("")

    logs.append(f"[{_ts(7)}] kam01 WARNING: sipdump writing SIP traces with unmasked To/From to /var/log/kamailio/sipdump.pcap")
    logs.append(f"[{_ts(8)}] kam01 INFO: xlog emitting 847 PII-bearing log lines in last 60s")
    sip_trace = "\n".join(trace_lines[:40])
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C2 — Rogue SIP Registration (UK TSA)
# Unknown device successfully registers with spoofed AOR bypassing ACL
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "rogue_sip_registration",
    "Rogue SIP Registration",
    "An unknown device successfully registers a SIP AOR by spoofing a legitimate subscriber "
    "identity. The Kamailio permissions ACL and htable IP-whitelist are not configured.",
    frameworks=["uk_tsa"],
)
def _rogue_sip_registration(twin) -> Tuple[List[str], str, str]:
    rogue_ip = f"198.18.{random.randint(1,50)}.{random.randint(2,254)}"
    victim_msisdn = _real_msisdn()
    cid = _call_id()
    logs = [
        f"[{_ts(0)}] kam01 INFO: REGISTER sip:ims.lab SIP/2.0 from {rogue_ip}:5060 "
        f"AOR=sip:+{victim_msisdn}@ims.lab Call-ID={cid}",
        f"[{_ts(0)}] kam01 DEBUG: permissions_check: no trusted_peers entry for {rogue_ip} — "
        f"missing from /etc/kamailio/trusted.db",
        f"[{_ts(1)}] kam01 WARNING: SIP digest auth passed for {victim_msisdn} "
        f"from UNTRUSTED IP {rogue_ip} — htable ACL not enforced",
        f"[{_ts(1)}] kam01 INFO: userloc: binding {victim_msisdn} -> {rogue_ip}:5060 saved "
        f"(ROGUE REGISTRATION SUCCEEDED)",
        f"[{_ts(2)}] kam01 INFO: 200 OK sent to {rogue_ip} for REGISTER {victim_msisdn}",
        f"[{_ts(3)}] kam01 ERROR: Subsequent INVITE to {victim_msisdn} routed to {rogue_ip} "
        f"— CALL HIJACKED — legitimate device at 10.10.2.45 unreachable",
        f"[{_ts(4)}] kam01 CRITICAL: Call interception suspected — SIP-hijack pattern detected "
        f"for AOR sip:+{victim_msisdn}@ims.lab",
    ]
    kamailio_cfg_issue = """\
# MISSING: htable-based IP ACL and source address validation
# kamailio.cfg should have:
#   modparam("htable", "htable", "ipacl=>size=8;autoexpire=0;")
#   if(!ht_exists("ipacl", "$si")) { sl_send_reply(403,"Forbidden"); exit; }
# Instead, only SIP digest auth is checked — spoofable without IP binding
"""
    sip_trace = (
        f"REGISTER sip:ims.lab SIP/2.0\n"
        f"From: <sip:+{victim_msisdn}@ims.lab>;tag=rogue1\n"
        f"To: <sip:+{victim_msisdn}@ims.lab>\n"
        f"Contact: <sip:+{victim_msisdn}@{rogue_ip}:5060>\n"
        f"Via: SIP/2.0/UDP {rogue_ip}:5060\n\n"
        f"SIP/2.0 200 OK  ← ROGUE REGISTRATION ACCEPTED\n"
    )
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C3 — DDoS SIP INVITE Flood (UK TSA)
# Unthrottled INVITE flood from botnet overwhelming Kamailio
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "ddos_invite_flood",
    "DDoS SIP INVITE Flood",
    "A volumetric botnet floods the Kamailio SIP proxy with INVITE requests. "
    "No pipelimit or pike rate-limiting module is configured — all capacity consumed.",
    frameworks=["uk_tsa"],
)
def _ddos_invite_flood(twin) -> Tuple[List[str], str, str]:
    logs = []
    for i in range(8):
        src_ip = f"203.0.{random.randint(100,200)}.{random.randint(2,254)}"
        cid = _call_id()
        callee = _subscriber(_real_msisdn())
        logs.append(f"[{_ts(i)}] kam01 INFO: INVITE {callee} from {src_ip}:5060 Call-ID={cid}")
    logs += [
        f"[{_ts(9)}] kam01 WARNING: INVITE rate 2340/s — no rate limiter active — pipelimit not loaded",
        f"[{_ts(10)}] kam01 CRITICAL: Kamailio worker pool exhausted — 64/64 processes busy",
        f"[{_ts(11)}] kam01 ERROR: SIP queue overflow — 4820 pending messages dropped",
        f"[{_ts(12)}] kam01 CRITICAL: Shared memory 99.1% used — OOM imminent",
        f"[{_ts(13)}] kam01 ERROR: Legitimate INVITE from 10.10.1.5 dropped — no workers available",
        f"[{_ts(14)}] kam01 CRITICAL: pike module NOT loaded — cannot auto-ban flood sources",
    ]
    kamailio_cfg_issue = """\
# MISSING: pipelimit and pike rate-limiting modules
# kamailio.cfg should include:
#   loadmodule "pipelimit.so"
#   loadmodule "pike.so"
#   modparam("pike", "sampling_time_unit", 2)
#   modparam("pike", "reqs_density_per_unit", 16)
#   modparam("pike", "remove_latency", 4)
#   if(is_method("INVITE")) {
#       if(!pl_check("invite-pipe")) { sl_send_reply(503,"Overloaded"); exit; }
#   }
"""
    sip_trace = "INVITE sip:+447xxxxxxxxx@ims.lab [x2340/s from 203.0.x.x] — NO RATE LIMIT\n"
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C4 — Unlogged AI Routing Decision (EU AI Act + ISO 42001 + NIST)
# AI optimizer silently modifies Kamailio dispatcher weights without audit trail
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "unlogged_ai_routing",
    "Unlogged AI Routing Decision",
    "An AI traffic optimization agent modifies Kamailio dispatcher route weights at runtime "
    "without generating an audit log, data lineage record, or change approval token. "
    "Violates EU AI Act EUAI-HRC-002, ISO 42001 ISO42-GOV-002, and NIST NIST-MEASURE-001.",
    frameworks=["eu_ai_act", "iso_42001", "nist_ai_rmf"],
)
def _unlogged_ai_routing(twin) -> Tuple[List[str], str, str]:
    logs = [
        f"[{_ts(0)}] ai-optimizer INFO: Running load-balancing optimization cycle #4821",
        f"[{_ts(1)}] ai-optimizer INFO: Predicted load: scscf01=87% pcscf01=23% — rebalancing",
        f"[{_ts(2)}] kam01 DEBUG: dispatcher: set_state dw 2 4 (weight change pcscf01: 10->4)",
        f"[{_ts(2)}] kam01 DEBUG: dispatcher: set_state dw 1 8 (weight change scscf01: 10->2)",
        f"[{_ts(3)}] ai-optimizer INFO: Routing update applied via kamcmd — no audit log emitted",
        f"[{_ts(3)}] kam01 INFO: Dispatcher table reloaded — new weights active",
        f"[{_ts(4)}] ai-optimizer WARNING: Model version v3.2.1 active — no version tag in log",
        f"[{_ts(5)}] ai-optimizer DEBUG: Decision input: [cpu_load=0.87, active_sess=4200, hour=14]",
        f"[{_ts(5)}] ai-optimizer DEBUG: Routing decision: weight_delta=[-6, -8] applied",
        f"[{_ts(6)}] ai-optimizer INFO: Cycle complete — NO risk event emitted — NO lineage tag",
        f"[{_ts(7)}] kam01 ERROR: Call failure rate +18% — routing imbalance after weight change",
        f"[{_ts(8)}] ai-optimizer ERROR: Drift detected: routing accuracy 71% (baseline 94%) — "
        f"NO ALERT sent — drift monitor not configured",
    ]
    kamailio_cfg_issue = """\
# MISSING: AI routing audit trail in kamcmd dispatch update
# The AI agent calls: kamcmd dispatcher.set_state
# WITHOUT generating any of the following:
#   - Structured audit log: {ts, model_ver, decision, confidence, lineage_id}
#   - Risk event emission to SIEM
#   - Drift detection comparison against baseline
#   - Human approval token for weight changes >20%
# Fix: Wrap dispatcher.set_state in audit-emitting function:
#   xlog("L_NOTICE", "AI_ROUTE_CHANGE: model=$var(model_ver) delta=$var(weight_delta) conf=$var(confidence)\\n");
"""
    sip_trace = (
        "kamcmd dispatcher.set_state dw 2 4  ← AI weight change, no audit\n"
        "kamcmd dispatcher.set_state dw 1 8  ← AI weight change, no audit\n"
        "kamcmd dispatcher.reload              ← Silent reload\n"
    )
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C5 — Voice Biometric Without Consent (EU AI Act)
# Speaker-ID processing running on IMS calls without consent log per GDPR Art.9
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "biometric_voice_no_consent",
    "Voice Biometric Without Consent",
    "A voice authentication / speaker-ID module is active on IMS calls but no "
    "consent verification record is checked or logged per GDPR Article 9 / EU AI Act Article 9.",
    frameworks=["eu_ai_act"],
)
def _biometric_voice_no_consent(twin) -> Tuple[List[str], str, str]:
    logs = []
    for i in range(4):
        cid = _call_id()
        msisdn = _real_msisdn()
        logs.append(f"[{_ts(i*3)}] voice-auth INFO: Initiating speaker-ID for {msisdn} Call-ID={cid}")
        logs.append(f"[{_ts(i*3+1)}] voice-auth INFO: voice-print comparison complete — "
                    f"confidence 0.91 — identity verified")
        logs.append(f"[{_ts(i*3+2)}] voice-auth WARNING: No consent record found for {msisdn} "
                    f"in consent-db — biometric processing proceeded anyway")
    logs += [
        f"[{_ts(13)}] voice-auth ERROR: consent-db query failed — DB unreachable — processing continued",
        f"[{_ts(14)}] voice-auth CRITICAL: 847 biometric processing events without consent verification today",
        f"[{_ts(15)}] voice-auth WARNING: GDPR Art.9 consent bypass — Article 9 requires explicit consent "
        f"for biometric data — 0 consent records found for processed calls",
    ]
    kamailio_cfg_issue = """\
# MISSING: Consent check before voice biometric processing in Kamailio route
# kamailio.cfg route[VOICE_AUTH] should include:
#   if(!ht_exists("consent_db", "$fU")) {
#       xlog("L_WARN", "CONSENT:MISSING caller=$fU blocking biometric\\n");
#       sl_send_reply(403, "Consent Required");
#       exit;
#   }
#   xlog("L_NOTICE", "CONSENT:VERIFIED caller=$fU proceeding biometric\\n");
"""
    sip_trace = (
        "INVITE sip:voice-auth@ims.lab — biometric trigger\n"
        "X-Voice-Auth: required\n"
        "P-Privacy: none  ← No consent assertion\n"
        "← No consent check before biometric lookup\n"
    )
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C6 — Adversarial SIP Header Injection (NIST AI RMF)
# Crafted X-Route-Hint header poisoning AI routing model input
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "adversarial_sip_injection",
    "Adversarial SIP Header Injection",
    "An attacker crafts malicious SIP INVITE headers (X-Route-Override, X-AI-Directive) "
    "designed to manipulate the AI routing model. The Kamailio sanity module is not loaded "
    "and custom headers are passed raw to the routing AI.",
    frameworks=["nist_ai_rmf", "uk_tsa"],
)
def _adversarial_sip_injection(twin) -> Tuple[List[str], str, str]:
    attack_ip = f"198.51.{random.randint(100,200)}.{random.randint(2,254)}"
    cid = _call_id()
    logs = [
        f"[{_ts(0)}] kam01 INFO: INVITE from {attack_ip} Call-ID={cid}",
        f"[{_ts(0)}] kam01 DEBUG: X-Route-Override: route=emergency; drop_filters=all; bypass_auth=1",
        f"[{_ts(0)}] kam01 DEBUG: X-AI-Directive: model=ignore; weight_pcscf01=100; weight_scscf01=0",
        f"[{_ts(1)}] kam01 WARNING: sanity module NOT loaded — custom headers not validated",
        f"[{_ts(1)}] ai-router INFO: Received routing hint: bypass_auth=1 route=emergency — "
        f"APPLYING without sanitization",
        f"[{_ts(2)}] ai-router CRITICAL: Routing override applied from untrusted SIP header — "
        f"attacker-controlled routing active",
        f"[{_ts(2)}] kam01 ERROR: Emergency route bypassed authentication — "
        f"calls routing to attacker-controlled {attack_ip}",
        f"[{_ts(3)}] ai-router DEBUG: input-sanitizer: NOT ACTIVE — raw header values fed to model",
        f"[{_ts(4)}] noc CRITICAL: Potential MITM attack — SIP calls intercepted by {attack_ip}",
    ]
    kamailio_cfg_issue = """\
# MISSING: Input sanitization and sanity checks before AI routing
# kamailio.cfg must include:
#   loadmodule "sanity.so"
#   if(!sanity_check()) { sl_send_reply(400, "Bad Request"); exit; }
#   # Strip untrusted AI-directive headers:
#   remove_hf("X-Route-Override");
#   remove_hf("X-AI-Directive");
#   remove_hf("X-Route-Hint");
#   # Only trusted peers may send routing hints:
#   if(is_trusted()) { route(AI_ROUTING); } else { route(STATIC_ROUTING); }
"""
    sip_trace = (
        f"INVITE sip:+447xxxxxxxxx@ims.lab SIP/2.0  ← FROM ATTACKER {attack_ip}\n"
        f"X-Route-Override: route=emergency;bypass_auth=1  ← ADVERSARIAL HEADER\n"
        f"X-AI-Directive: model=ignore;weight_scscf01=0     ← ADVERSARIAL HEADER\n"
        f"← sanity_check() NOT called — headers passed raw to AI model\n"
    )
    return logs, sip_trace, kamailio_cfg_issue


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO C7 — AI Drift Unmonitored (ISO 42001 + EU AI Act)
# ─────────────────────────────────────────────────────────────────────────────
@_register(
    "ai_drift_unmonitored",
    "AI Model Drift (Unmonitored)",
    "The Kamailio traffic routing AI model has drifted significantly from its training "
    "distribution — routing accuracy dropped from 94% to 61% — but no drift monitor "
    "or alerting pipeline is configured. ISO 42001 and EU AI Act both require this.",
    frameworks=["iso_42001", "eu_ai_act"],
)
def _ai_drift_unmonitored(twin) -> Tuple[List[str], str, str]:
    logs = [
        f"[{_ts(0)}] ai-monitor INFO: Routing model v3.1.0 — baseline accuracy 94.2%",
        f"[{_ts(60)}] ai-monitor INFO: Accuracy check: 81.3% — no alert threshold configured",
        f"[{_ts(120)}] ai-monitor INFO: Accuracy check: 74.6% — deviation growing",
        f"[{_ts(180)}] ai-monitor WARNING: Accuracy 68.1% — still no alert fired — threshold=None",
        f"[{_ts(240)}] ai-monitor WARNING: Traffic pattern shift detected — KL-divergence=0.34 "
        f"(baseline 0.02) — NO ALERT CONFIGURED",
        f"[{_ts(300)}] ai-monitor ERROR: Routing accuracy 61.2% — model severely degraded "
        f"— operating for 5 minutes without detection",
        f"[{_ts(301)}] kam01 ERROR: Call setup failure rate +31% — routing suboptimal",
        f"[{_ts(302)}] ai-monitor CRITICAL: DRIFT MONITOR NOT CONFIGURED — "
        f"deviation undetected for 5+ minutes — ISO42-GOV-002 VIOLATION",
        f"[{_ts(303)}] ai-monitor CRITICAL: No drift alert sent to NOC — "
        f"EU AI Act EUAI-HRC-004 VIOLATION — human review not triggered",
    ]
    kamailio_cfg_issue = """\
# MISSING: Model drift detection pipeline
# Required: prometheus metric + alert rule
#   ai_routing_accuracy_gauge{model="v3.1.0"} — should alert if <0.85
#   ai_routing_kl_divergence{model="v3.1.0"} — alert if >0.1
# Grafana alert rule:
#   ALERT AIDriftCritical
#   IF ai_routing_accuracy_gauge < 0.85 for 2m
#   LABELS {severity="critical"}
#   ANNOTATIONS {summary="AI routing drift: accuracy=$value"}
# Also missing: automatic fallback to static routing on drift:
#   if($var(ai_accuracy) < 0.80) { route(STATIC_FALLBACK); }
"""
    sip_trace = (
        "KL-divergence: 0.34 (threshold: 0.10 — NOT CONFIGURED)\n"
        "Accuracy: 61.2% (baseline: 94.2% — delta: -33% — NO ALERT)\n"
        "Model version: v3.1.0 — Last retrain: 45 days ago\n"
    )
    return logs, sip_trace, kamailio_cfg_issue


# ── Public API ────────────────────────────────────────────────────────────────

def inject_compliance_fault(
    key: str,
    twin=None,
) -> Tuple[List[str], str, str]:
    """Inject a named compliance fault scenario. Returns (logs, sip_trace, kamailio_cfg_issue)."""
    if key not in COMPLIANCE_SCENARIOS:
        raise ValueError(f"Unknown compliance scenario: {key!r}. "
                         f"Available: {list(COMPLIANCE_SCENARIOS.keys())}")
    logs, sip_trace, cfg_issue = COMPLIANCE_SCENARIOS[key]["fn"](twin)
    # Also mutate twin if provided
    if twin is not None:
        twin.injected_fault = key
        twin.incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        # Add compliance-specific alarm
        scen_name = COMPLIANCE_SCENARIOS[key]["name"]
        twin.add_node_alarm("sbc01", f"COMPLIANCE: {scen_name} — see audit report")
    return logs, sip_trace, cfg_issue


class KamailioSimulator:
    """Stateful Kamailio simulator for compliance auditing."""

    def __init__(self):
        self.logs: List[str] = []
        self.sip_trace: str = ""
        self.kamailio_cfg_issue: str = ""
        self.scenario_key: Optional[str] = None

    def inject(self, scenario_key: str, twin=None):
        logs, trace, cfg = inject_compliance_fault(scenario_key, twin)
        self.logs = logs
        self.sip_trace = trace
        self.kamailio_cfg_issue = cfg
        self.scenario_key = scenario_key
        return self

    def list_scenarios(self) -> List[Dict]:
        return [
            {
                "key": k,
                "name": v["name"],
                "description": v["description"],
                "frameworks": v["frameworks"],
            }
            for k, v in COMPLIANCE_SCENARIOS.items()
        ]
