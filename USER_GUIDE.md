# IMS Network Digital Twin — User Guide

**Version:** 3.0  
**Platform:** macOS (Darwin)  
**Last Updated:** June 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Starting the Application](#3-starting-the-application)
4. [Using the Dashboard](#4-using-the-dashboard)
5. [Stopping the Application](#5-stopping-the-application)
6. [Running the CLI (No Browser)](#6-running-the-cli-no-browser)
7. [REST API Reference](#7-rest-api-reference)
8. [Troubleshooting](#8-troubleshooting)
9. [Quick Reference Card](#9-quick-reference-card)

---

## 1. Overview

The IMS Network Digital Twin is a web-based demo that simulates a live IMS (IP Multimedia Subsystem) network. It provides:

- **Visual topology** — clickable nodes for Oracle SBC, Kamailio P-CSCF / I-CSCF / S-CSCF, HSS, PCRF, MGW
- **Fault injection** — 6 realistic failure scenarios with live alarms and SBC log simulation
- **User simulation** — SIP REGISTER, INVITE, MESSAGE, and DEREGISTER flows for 3 virtual UEs
- **AI root cause analysis** — Gemma4:e4b (local Ollama) streams a live technical RCA report
- **Config generation** — Oracle ACLI remediation configs saved to `ims_digital_twin/output/`

**Software stack:**

| Component | Version |
|-----------|---------|
| Python | 3.9.6 |
| FastAPI | 0.128.8 |
| Uvicorn | 0.39.0 |
| Google ADK | 1.18.0 |
| LiteLLM | 1.83.9 |
| Ollama | 0.30.6 |
| Model | gemma4:e4b |

---

## 2. Prerequisites

Both services below must be running before starting the application.

### 2.1 Check Ollama is running

```bash
curl http://localhost:11434/api/version
```

Expected output: `{"version":"0.30.6"}` (or similar).

If Ollama is not running, start it:

```bash
ollama serve
```

Leave this terminal open, or run it in the background:

```bash
ollama serve &>/tmp/ollama.log &
```

Verify the model is available:

```bash
ollama list
```

You should see `gemma4:e4b` in the list. If not, pull it:

```bash
ollama pull gemma4:e4b
```

### 2.2 Check the virtual environment exists

```bash
ls "/Users/admin/Documents/Google Agentic framework/.venv/bin/python"
```

If the `.venv` folder is missing, create it:

```bash
cd "/Users/admin/Documents/Google Agentic framework"
python3 -m venv .venv
source .venv/bin/activate
pip install google-adk litellm fastapi "uvicorn[standard]" httpx
```

---

## 3. Starting the Application

### Step 1 — Open a terminal and navigate to the project

```bash
cd "/Users/admin/Documents/Google Agentic framework"
```

### Step 2 — Activate the virtual environment

```bash
source .venv/bin/activate
```

Your prompt will change to show `(.venv)` at the start.

### Step 3 — Start the web server

```bash
python -m ims_digital_twin.web_server
```

Expected output:

```
  IMS Digital Twin Dashboard v2
  Open: http://localhost:8000
```

The server is now running and listening on port 8000.

### Step 4 — Open the dashboard

Open your browser and go to:

```
http://localhost:8000
```

> **Note:** Leave the terminal window open while using the application. Closing it will stop the server.

### Starting with a single command (shortcut)

You can combine all three steps into one:

```bash
cd "/Users/admin/Documents/Google Agentic framework" && \
source .venv/bin/activate && \
python -m ims_digital_twin.web_server
```

---

## 4. Using the Dashboard

### 4.1 Layout overview

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER — Status chip | Incident ID | Model indicator                 │
├──────────────────────────────────────────┬───────────────────────────┤
│                                          │ Fault Scenario Buttons    │
│   NETWORK TOPOLOGY (D3.js)               │ ⚙ Config  ✓ Fix  🤖 AI   │
│                                          ├───────────────────────────┤
│   UE → Oracle SBC → P-CSCF → I-CSCF     │ Active Alarms             │
│                           → S-CSCF       ├───────────────────────────┤
│                      → HSS   → MGW       │ User Simulation           │
│                      ↕ PCRF              │ Alice  Bob  Charlie       │
├─────────────────┬────────────────────────┴───────────────────────────┤
│ Oracle SBC Logs │ SIP Protocol Trace │ Gemma4 AI Analysis (stream)   │
└─────────────────┴───────────────────────────────────────────────────┘
```

### 4.2 Injecting a fault scenario

1. Click one of the 6 scenario buttons in the top-right panel:

   | Button | Fault Simulated |
   |--------|----------------|
   | 🌊 SIP Registration Storm | REGISTER flood → CPU 94%, rate-limit 503s |
   | 🔒 TLS Certificate Expiry | SIP/TLS handshake fails → all UEs blocked |
   | 🔇 RTP Media Timeout | 48 calls with one-way audio → calls cleared |
   | 🎵 SIP Codec / SDP Mismatch | G.729 stripped → 488 errors |
   | 💥 Upstream P-CSCF Unreachable | P-CSCF crashes → all INVITEs 503 |
   | 🔑 SRTP/DTLS Negotiation Failure | Cipher mismatch → silent calls |

2. The topology updates immediately:
   - Affected nodes turn **red** (DOWN) or **orange** (DEGRADED)
   - Broken links show as **red dashed lines**
   - Alarms populate in the panel on the right
   - SBC log lines stream in the bottom-left panel

### 4.3 Clicking on a node

Click any labelled node (SBC, P-CSCF, I-CSCF, S-CSCF, HSS, PCRF, MGW) to open the detail modal with five tabs:

| Tab | What you see |
|-----|-------------|
| **Overview** | IP addresses, software version, uptime, live CPU/memory bars, session count |
| **Config** | Full configuration file — Oracle ACLI syntax for SBC, Kamailio `.cfg` for IMS nodes |
| **Runtime** | Process table (PID, CPU%, memory%, state), live config snapshot |
| **Interfaces** | NIC table (name, IP, netmask, MAC, speed, role), active connections |
| **Alarms** | Current alarms on this node |

Press **Escape** or click the **✕** button to close the modal.

### 4.4 Running user simulations

The **User Simulation** panel (bottom of the right column) shows three virtual users:

- **👩 Alice** — Zoiper 5.6, G.711/G.729/OPUS
- **👨 Bob** — Linphone 5.3, G.711/AMR
- **🧑 Charlie** — MicroSIP 3.21, G.729 only (triggers codec mismatch)

Click any action button to generate a SIP interaction:

| Button | SIP Method | Notes |
|--------|-----------|-------|
| 👩 Register | REGISTER | Alice registers to IMS |
| 👨 Register | REGISTER | Bob registers to IMS |
| 🧑 Register | REGISTER | Charlie registers (G.729 only) |
| 📞 Alice→Bob | INVITE | Voice call with SDP/SRTP |
| 📞 Bob→Alice | INVITE | Reverse direction |
| 📞 Charlie→Bob | INVITE | G.729-only → triggers 488 in codec_mismatch scenario |
| 💬 Alice→Bob | MESSAGE | SIP instant message |
| 🌊 Flood×100 | REGISTER ×100 | Simulates registration storm |
| ↩ Deregister | REGISTER Expires:0 | Alice de-registers |

The **SIP Protocol Trace** panel (bottom centre) shows the full SIP message exchange including request headers, response codes, SDP offer/answer, and SRTP keys.

### 4.5 Generating and applying a remediation config

1. After injecting a fault, click **⚙ Config**
   - The Oracle SBC ACLI remediation configuration appears in the bottom-right panel
   - Remediation steps stream into the log panel
   - The config file is saved to `ims_digital_twin/output/remediation_<INCIDENT>_<SCENARIO>.acli`

2. Click **✓ Fix** to simulate applying the config:
   - All nodes return to **green** (UP)
   - Links restore to normal
   - Alarms clear
   - Fix log entries appear in the log stream

### 4.6 AI root cause analysis

1. After injecting a fault, click **🤖 AI**
2. Gemma4:e4b (running locally via Ollama) streams a live technical analysis:
   - Root cause with log line references
   - Impact assessment
   - Step-by-step remediation
   - Oracle ACLI config changes
   - Prevention measures
3. The AI indicator in the top-right shows `gemma4:e4b ✓` when the model is reachable

> **Note:** The first AI response may take 15–30 seconds to start streaming while the model loads. Subsequent requests are faster.

### 4.7 Resetting the dashboard

Click **↺** (reset button) at any time to:
- Clear all injected faults
- Restore all nodes to UP / green
- Clear alarms, logs, and SIP traces
- Return to idle state

---

## 5. Stopping the Application

### Stop the web server

In the terminal where the server is running, press:

```
Ctrl + C
```

You will see:

```
^C
```

The server stops immediately.

### Stop a background server

If you started the server in the background (with `&`), find and stop it:

```bash
# Find the process
ps aux | grep "ims_digital_twin.web_server" | grep -v grep

# Stop it by PID (replace 12345 with the actual PID shown above)
kill 12345
```

Or stop all matching processes at once:

```bash
pkill -f "ims_digital_twin.web_server"
```

### Deactivate the virtual environment

When you are finished:

```bash
deactivate
```

Your prompt returns to normal (no `(.venv)` prefix).

### Stop Ollama (optional)

If you started Ollama manually and want to stop it:

```bash
pkill ollama
```

> **Note:** Stopping Ollama only disables AI analysis. The rest of the dashboard (topology, fault injection, simulations, config generation) continues to work.

---

## 6. Running the CLI (No Browser)

The application can also be used from the terminal without starting the web server.

### List all fault scenarios

```bash
cd "/Users/admin/Documents/Google Agentic framework"
source .venv/bin/activate
python -m ims_digital_twin.main --list
```

### Inject a fault and view the twin state (no AI required)

```bash
python -m ims_digital_twin.main --scenario tls_cert_expiry --twin-only
```

Available scenario keys:

```
reg_storm          SIP Registration Storm
tls_cert_expiry    TLS Certificate Expiry
rtp_timeout        RTP Media Timeout (One-Way Audio)
codec_mismatch     SIP Codec / SDP Mismatch
pcscf_down         Upstream P-CSCF Unreachable
srtp_dtls_fail     SRTP/DTLS Negotiation Failure
```

### Run the full AI pipeline (Log Analyzer → RCA → Config Generator)

```bash
python -m ims_digital_twin.main --scenario pcscf_down
```

This requires Ollama to be running with `gemma4:e4b`.

### CLI options

```
--scenario  -s   Fault scenario key (default: reg_storm)
--list      -l   List all scenarios and exit
--twin-only      Show twin state and logs without AI agents
--model     -m   LiteLLM model string (default: ollama_chat/gemma4:e4b)
--ollama-url     Ollama server URL (default: http://localhost:11434)
```

---

## 7. REST API Reference

The web server exposes a REST API on `http://localhost:8000`. All endpoints return JSON unless otherwise noted.

---

### 7.1 Base URL and Headers

```
Base URL : http://localhost:8000
Headers  : Content-Type: application/json  (for POST requests with a body)
```

You can test any endpoint with `curl` or any HTTP client (Postman, httpx, etc.).

---

### 7.2 Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the main HTML dashboard (`static/index.html`) |

---

### 7.3 Scenario Management

#### List all fault scenarios

```
GET /api/scenarios
```

**Response:**
```json
{
  "scenarios": [
    {"key": "reg_storm",       "name": "SIP Registration Storm",        "description": "..."},
    {"key": "tls_cert_expiry", "name": "TLS Certificate Expiry",        "description": "..."},
    {"key": "rtp_timeout",     "name": "RTP Media Timeout",             "description": "..."},
    {"key": "codec_mismatch",  "name": "SIP Codec / SDP Mismatch",      "description": "..."},
    {"key": "pcscf_down",      "name": "Upstream P-CSCF Unreachable",   "description": "..."},
    {"key": "srtp_dtls_fail",  "name": "SRTP/DTLS Negotiation Failure", "description": "..."}
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/scenarios
```

---

#### Inject a fault scenario

```
POST /api/inject/{scenario_key}
```

**Path parameter:** `scenario_key` — one of the keys listed above.

**Response:**
```json
{
  "ok": true,
  "incident_id": "INC-A1B2C3D4",
  "scenario": "reg_storm",
  "log_count": 18,
  "alarm_count": 3
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/inject/reg_storm
curl -X POST http://localhost:8000/api/inject/tls_cert_expiry
curl -X POST http://localhost:8000/api/inject/pcscf_down
```

**Error (unknown scenario):** HTTP 404
```json
{"detail": "Unknown scenario: bad_key"}
```

---

### 7.4 Twin State

#### Get full application state

```
GET /api/state
```

Returns the complete digital twin snapshot including all node KPIs, active alarms, logs, and any generated config.

**Response:**
```json
{
  "phase": "injected",
  "scenario_key": "reg_storm",
  "incident_id": "INC-A1B2C3D4",
  "twin": {
    "snapshot_ts": "2026-06-07T10:00:00+00:00",
    "incident_id": "INC-A1B2C3D4",
    "injected_fault": "reg_storm",
    "nodes": {
      "sbc01":   {"type": "Oracle_SBC", "status": "UP",   "cpu_pct": 94.3, "mem_pct": 78.1, "sessions": 4988, "alarms": ["CRITICAL: CPU 94%"]},
      "pcscf01": {"type": "P-CSCF",    "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 1190, "alarms": []},
      "icscf01": {"type": "I-CSCF",    "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 0,    "alarms": []},
      "scscf01": {"type": "S-CSCF",    "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 1190, "alarms": []},
      "hss01":   {"type": "HSS",       "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 0,    "alarms": []},
      "pcrf01":  {"type": "PCRF",      "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 0,    "alarms": []},
      "mgw01":   {"type": "MGW",       "status": "UP",   "cpu_pct": 15.0, "mem_pct": 30.0, "sessions": 0,    "alarms": []}
    },
    "links": [
      {"type": "SBC_Access", "src": "ue",    "dst": "sbc01",   "status": "UP", "latency_ms": 2.0, "loss_pct": 0.0},
      {"type": "SBC_Core",   "src": "sbc01", "dst": "pcscf01", "status": "UP", "latency_ms": 2.0, "loss_pct": 0.0}
    ],
    "total_alarms": 3
  },
  "logs": ["Jun 07 10:00:00 sbc01 APKT[sipd]: REGISTER ..."],
  "alarms": [
    {"node": "sbc01", "alarm": "CRITICAL: CPU utilization 94%"},
    {"node": "sbc01", "alarm": "MAJOR: REGISTER rate 1820/s"}
  ],
  "sip_trace": "",
  "generated_config": null,
  "remediation_steps": []
}
```

**Possible `phase` values:**

| Phase | Meaning |
|-------|---------|
| `idle` | No fault injected — clean state |
| `injected` | Fault active, logs + alarms populated |
| `fixing` | Remediation config generated |
| `fixed` | Fix applied — all nodes restored to UP |

**Example:**
```bash
curl http://localhost:8000/api/state | python3 -m json.tool
```

---

#### Get node detail

```
GET /api/node/{node_id}
```

**Path parameter:** `node_id` — one of `sbc01 | pcscf01 | icscf01 | scscf01 | hss01 | pcrf01 | mgw01`

**Response:**
```json
{
  "node_id": "sbc01",
  "config_type": "Oracle ACLI",
  "config_text": "# Oracle SBC ACLI ...",
  "element_type": "Oracle_SBC",
  "runtime": {
    "software_version": "SCZ8.4.0 p3 build 188",
    "platform": "Acme Packet 1100",
    "uptime": "47d 12h 33m",
    "os": "AcmeOS 6.4",
    "processes": [
      {"pid": 101, "name": "sipd", "cpu": "4.2", "mem": "8.1", "state": "S", "note": "SIP proxy daemon"}
    ],
    "interfaces": [
      {"name": "eth0", "ip": "10.0.1.10", "mask": "255.255.255.0", "speed": "1Gbps", "role": "access"}
    ],
    "connections": [
      {"proto": "TCP", "local": "10.0.2.100:5060", "remote": "10.0.2.10:5060", "state": "ESTABLISHED"}
    ],
    "live_cpu_pct": 94.3,
    "live_mem_pct": 78.1,
    "live_sessions": 4988,
    "live_status": "UP",
    "live_alarms": ["CRITICAL: CPU 94%"]
  }
}
```

**Config types by node:**

| Node | config_type |
|------|------------|
| `sbc01` | Oracle ACLI |
| `pcscf01` | Kamailio 5.8 CFG |
| `icscf01` | Kamailio 5.8 CFG |
| `scscf01` | Kamailio 5.8 CFG |
| `hss01` | OpenHSS Config |
| `pcrf01` | OpenPCRF Config |
| `mgw01` | H.248 Config |

**Example:**
```bash
curl http://localhost:8000/api/node/sbc01
curl http://localhost:8000/api/node/pcscf01
```

---

### 7.5 Remediation

#### Generate ACLI remediation config

```
POST /api/generate_config
```

Generates the Oracle SBC ACLI remediation configuration for the active fault scenario and saves it to `ims_digital_twin/output/`.

**Prerequisite:** A fault must be active (`phase` = `injected` or `fixing`).

**Response:**
```json
{
  "ok": true,
  "phase": "fixing",
  "config": "# Oracle SBC ACLI ...\ndos-protection\n    register-max-rate 200\n...",
  "steps": [
    "Apply dos-protection with register-max-rate=200/s",
    "Set deny-period=60s to block abusive sources",
    "Add 10.0.0.0/8 to exception-addresses whitelist"
  ]
}
```

**Example:**
```bash
# First inject a fault, then generate config
curl -X POST http://localhost:8000/api/inject/reg_storm
curl -X POST http://localhost:8000/api/generate_config
```

---

#### Apply the remediation fix

```
POST /api/apply_fix
```

Simulates pushing the generated config to the SBC. Restores all nodes to UP, clears alarms and broken links.

**Response:**
```json
{"ok": true, "phase": "fixed"}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/apply_fix
```

---

#### Reset to idle state

```
POST /api/reset
```

Clears all injected faults, alarms, logs, SIP traces, and generated configs. Returns to idle state.

**Response:**
```json
{"ok": true, "phase": "idle"}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/reset
```

---

### 7.6 User Simulation API

All simulation endpoints trigger a SIP interaction for a virtual user and return the SIP trace, log lines, and AI context string.

**Available users:**

| user_id | Name | UA | Codec |
|---------|------|----|-------|
| `alice` | Alice Smith | Zoiper 5.6 (iOS 17) | G.711 / G.729 / OPUS |
| `bob` | Bob Johnson | Linphone 5.3 (Android 14) | G.711 / AMR-NB / AMR-WB |
| `charlie` | Charlie Davis | MicroSIP 3.21 (Windows 11) | G.729 only |

**Common response shape for all simulation endpoints:**

```json
{
  "action":      "REGISTER",
  "user":        "alice",
  "target":      null,
  "success":     true,
  "response":    "200 OK",
  "duration_ms": 52,
  "ai_context":  "Alice Smith REGISTER succeeded in 52ms — auth OK, S-CSCF assigned"
}
```

The `sip_trace` and additional logs are stored in application state — retrieve them via `GET /api/state`.

---

#### Register a user

```
POST /api/sim/register/{user_id}
```

Simulates a SIP REGISTER → P-CSCF → I-CSCF (UAR) → S-CSCF (MAR/SAR) → HSS flow.

**Outcome by active scenario:**

| Scenario | Result |
|----------|--------|
| idle / fixed | 200 OK — registration succeeds |
| `tls_cert_expiry` | TLS handshake fails — SSL certificate expired |
| `reg_storm` | 503 Service Unavailable — SBC rate-limit blocks REGISTER |
| `pcscf_down` | 503 Service Unavailable — session-agent OOS |

**Example:**
```bash
curl -X POST http://localhost:8000/api/sim/register/alice
curl -X POST http://localhost:8000/api/sim/register/charlie
```

---

#### Place a voice call

```
POST /api/sim/call/{caller}/{callee}
```

Simulates a SIP INVITE with SRTP/SDP offer, PCRF Rx QoS, and RTP media path.

**Outcome by active scenario:**

| Scenario | Result |
|----------|--------|
| idle / fixed | 200 OK — SRTP call established |
| `codec_mismatch` | 488 Not Acceptable Here — G.729 stripped by codec policy |
| `pcscf_down` | 503 Service Unavailable — P-CSCF unreachable |
| `srtp_dtls_fail` | 200 OK (SIP) — call connects but no media (DTLS cipher mismatch) |
| `rtp_timeout` | 200 OK (SIP) — one-way audio, RTP timeout after 31s |

**Example:**
```bash
curl -X POST http://localhost:8000/api/sim/call/alice/bob
curl -X POST http://localhost:8000/api/sim/call/charlie/bob   # triggers 488 in codec_mismatch
```

---

#### Send a SIP MESSAGE

```
POST /api/sim/message/{sender}/{recipient}
```

Simulates a SIP MESSAGE (instant message) exchange.

**Example:**
```bash
curl -X POST http://localhost:8000/api/sim/message/alice/bob
```

---

#### Simulate a REGISTER flood

```
POST /api/sim/flood/{user_id}?count=100
```

Generates `count` rapid REGISTER requests to simulate a registration storm. Always triggers the SBC rate-limiter.

**Query parameter:** `count` — number of REGISTER requests (default: 100)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/sim/flood/alice?count=200"
```

**Response:**
```json
{
  "action": "FLOOD",
  "user": "alice",
  "target": null,
  "success": false,
  "response": "503 (rate-limited)",
  "duration_ms": 0,
  "ai_context": "Alice Smith sent 200 REGISTERs — SBC rate-limiter blocked flood"
}
```

---

#### De-register a user

```
POST /api/sim/deregister/{user_id}
```

Simulates `REGISTER Expires:0` — removes user from location table with a SAR `USER_DEREGISTRATION` to HSS.

**Example:**
```bash
curl -X POST http://localhost:8000/api/sim/deregister/alice
```

---

### 7.7 AI Analysis API

#### Check AI / Ollama health

```
GET /api/ai/health
```

Checks whether Ollama is reachable and `gemma4:e4b` is available.

**Response (healthy):**
```json
{
  "ok": true,
  "model": "gemma4:e4b",
  "all_models": ["gemma4:e4b", "llama3.1:8b"]
}
```

**Response (Ollama not running):**
```json
{
  "ok": false,
  "error": "Connection refused"
}
```

**Example:**
```bash
curl http://localhost:8000/api/ai/health
```

---

#### Stream AI root cause analysis (SSE)

```
GET /api/ai/analyze
```

Streams a live Gemma4:e4b analysis of the active fault as **Server-Sent Events (SSE)**. Each event contains one token of the response. The stream ends with a `done: true` event.

**Response format (SSE):**
```
data: {"token": "The"}

data: {"token": " root"}

data: {"token": " cause"}

...

data: {"done": true}
```

**AI prompt context** sent to Gemma4 includes:
- Incident ID and fault scenario name
- All 7 node statuses (CPU, memory, sessions, alarms)
- Active alarms list
- Latest 20 SBC log lines
- Any user simulation action that was triggered last

**AI analysis sections in the response:**
1. `ROOT CAUSE` — precise technical cause with log line references
2. `IMPACT ASSESSMENT` — affected users and services
3. `IMMEDIATE ACTIONS` — step-by-step remediation with Oracle ACLI commands
4. `ORACLE SBC CONFIG FIX` — exact ACLI config block to change
5. `PREVENTION` — monitoring and config hardening measures

**Example — stream with curl:**
```bash
# Inject fault first
curl -X POST http://localhost:8000/api/inject/pcscf_down

# Stream AI analysis (tokens print as they arrive)
curl -N http://localhost:8000/api/ai/analyze
```

**Example — consume SSE in Python:**
```python
import httpx

with httpx.stream("GET", "http://localhost:8000/api/ai/analyze") as r:
    for line in r.iter_lines():
        if line.startswith("data:"):
            import json
            payload = json.loads(line[5:].strip())
            if payload.get("done"):
                break
            print(payload.get("token", ""), end="", flush=True)
```

**Example — consume SSE in JavaScript (browser):**
```javascript
const es = new EventSource("/api/ai/analyze");
es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.done) { es.close(); return; }
    document.getElementById("output").textContent += data.token;
};
```

> **Note:** If Ollama is not running, the stream returns a single `⚠ Ollama not reachable` token followed by `done: true`.

---

### 7.8 Complete API Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | HTML dashboard |
| `GET` | `/api/scenarios` | List all 6 fault scenarios |
| `GET` | `/api/state` | Full twin state (nodes, alarms, logs, config) |
| `POST` | `/api/inject/{scenario_key}` | Inject a named fault scenario |
| `GET` | `/api/node/{node_id}` | Node detail with config, runtime, live KPIs |
| `POST` | `/api/generate_config` | Generate Oracle SBC ACLI remediation config |
| `POST` | `/api/apply_fix` | Apply fix — restore all nodes to UP |
| `POST` | `/api/reset` | Reset to idle state |
| `POST` | `/api/sim/register/{user_id}` | Simulate SIP REGISTER |
| `POST` | `/api/sim/call/{caller}/{callee}` | Simulate SIP INVITE voice call |
| `POST` | `/api/sim/message/{sender}/{recipient}` | Simulate SIP MESSAGE |
| `POST` | `/api/sim/flood/{user_id}?count=N` | Simulate REGISTER flood |
| `POST` | `/api/sim/deregister/{user_id}` | Simulate REGISTER Expires:0 |
| `GET` | `/api/ai/health` | Check Ollama + Gemma4 availability |
| `GET` | `/api/ai/analyze` | **SSE** — stream Gemma4 RCA analysis |

---

## 8. Troubleshooting

### 8.1 Browser shows "Unable to connect" or blank page

**Cause:** The web server is not running.  
**Fix:** Follow Section 3 to start the server and confirm `Open: http://localhost:8000` appears.

---

### 8.2 Port 8000 already in use

```
ERROR: [Errno 48] Address already in use
```

**Fix:** Stop the existing process and restart.

```bash
pkill -f "ims_digital_twin.web_server"
sleep 1
python -m ims_digital_twin.web_server
```

---

### 8.3 AI analysis shows "Ollama not reachable"

**Cause:** Ollama is not running or the model is not downloaded.  
**Fix:**

```bash
# Start Ollama
ollama serve

# In a new terminal, verify the model
ollama list

# Pull the model if missing
ollama pull gemma4:e4b
```

The AI status indicator in the dashboard header confirms connectivity (`gemma4:e4b ✓` = OK, red = offline).

---

### 8.4 ModuleNotFoundError on startup

**Cause:** Virtual environment is not activated.  
**Fix:**

```bash
source "/Users/admin/Documents/Google Agentic framework/.venv/bin/activate"
```

---

### 8.5 Nodes do not appear in the browser

**Cause:** D3.js loaded from CDN — check internet connectivity.  
**Fix:** The graph requires `cdnjs.cloudflare.com` for D3.js. Ensure you have internet access, or download D3.js locally:

```bash
curl -o "/Users/admin/Documents/Google Agentic framework/ims_digital_twin/static/d3.min.js" \
  "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
```

Then edit `static/index.html` line 5, change the CDN URL to `/static/d3.min.js`.

---

### 8.6 Generated config files not appearing

Config files are saved to:

```
/Users/admin/Documents/Google Agentic framework/ims_digital_twin/output/
```

List them:

```bash
ls -lh "/Users/admin/Documents/Google Agentic framework/ims_digital_twin/output/"
```

---

## 9. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│           IMS DIGITAL TWIN — QUICK REFERENCE                    │
├─────────────────────────────────────────────────────────────────┤
│  START                                                          │
│  1. ollama serve                    (if not already running)    │
│  2. cd "/Users/admin/Documents/Google Agentic framework"        │
│  3. source .venv/bin/activate                                   │
│  4. python -m ims_digital_twin.web_server                       │
│  5. Open http://localhost:8000                                  │
├─────────────────────────────────────────────────────────────────┤
│  DEMO FLOW (Browser)                                            │
│  1. Click a fault scenario button  (right panel)                │
│  2. Click a node to inspect config (graph)                      │
│  3. Click a user action button     (sim panel)                  │
│  4. Click ⚙ Config                 (generate ACLI fix)          │
│  5. Click 🤖 AI                    (stream AI analysis)         │
│  6. Click ✓ Fix                    (apply remediation)          │
│  7. Click ↺                        (reset to idle)              │
├─────────────────────────────────────────────────────────────────┤
│  REST API (curl examples)                                       │
│  curl -X POST localhost:8000/api/inject/reg_storm               │
│  curl -X POST localhost:8000/api/inject/tls_cert_expiry         │
│  curl -X POST localhost:8000/api/inject/pcscf_down              │
│  curl    localhost:8000/api/state                               │
│  curl    localhost:8000/api/node/sbc01                          │
│  curl -X POST localhost:8000/api/generate_config                │
│  curl -X POST localhost:8000/api/apply_fix                      │
│  curl -X POST localhost:8000/api/reset                          │
├─────────────────────────────────────────────────────────────────┤
│  USER SIMULATION API                                            │
│  curl -X POST localhost:8000/api/sim/register/alice             │
│  curl -X POST localhost:8000/api/sim/call/alice/bob             │
│  curl -X POST localhost:8000/api/sim/call/charlie/bob           │
│  curl -X POST localhost:8000/api/sim/message/alice/bob          │
│  curl -X POST "localhost:8000/api/sim/flood/alice?count=100"    │
│  curl -X POST localhost:8000/api/sim/deregister/alice           │
├─────────────────────────────────────────────────────────────────┤
│  AI API                                                         │
│  curl    localhost:8000/api/ai/health                           │
│  curl -N localhost:8000/api/ai/analyze      (SSE stream)        │
├─────────────────────────────────────────────────────────────────┤
│  STOP                                                           │
│  Ctrl+C in the server terminal                                  │
│  deactivate                                                     │
│  pkill ollama             (optional — only if you want to stop) │
├─────────────────────────────────────────────────────────────────┤
│  CLI (no browser)                                               │
│  python -m ims_digital_twin.main --list                         │
│  python -m ims_digital_twin.main --scenario pcscf_down          │
│  python -m ims_digital_twin.main --scenario reg_storm           │
│                                            --twin-only          │
├─────────────────────────────────────────────────────────────────┤
│  KEY PATHS                                                      │
│  Project  : ~/Documents/Google Agentic framework/               │
│  Venv     : .venv/bin/activate                                  │
│  Web app  : ims_digital_twin/web_server.py                      │
│  CLI      : ims_digital_twin/main.py                            │
│  Output   : ims_digital_twin/output/*.acli                      │
│  Dashboard: http://localhost:8000                               │
│  API docs : http://localhost:8000/docs   (FastAPI Swagger UI)   │
│  Ollama   : http://localhost:11434                              │
└─────────────────────────────────────────────────────────────────┘
```

---

*IMS Network Digital Twin v3.0 · Google ADK + Gemma4:e4b + FastAPI + Oracle SBC + Kamailio 5.8*
