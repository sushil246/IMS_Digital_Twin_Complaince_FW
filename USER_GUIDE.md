# IMS Network Digital Twin — User Guide

**Version:** 2.0  
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
7. [Troubleshooting](#7-troubleshooting)
8. [Quick Reference Card](#8-quick-reference-card)

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

## 7. Troubleshooting

### Browser shows "Unable to connect" or blank page

**Cause:** The web server is not running.  
**Fix:** Follow Section 3 to start the server and confirm `Open: http://localhost:8000` appears.

---

### Port 8000 already in use

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

### AI analysis shows "Ollama not reachable"

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

### ModuleNotFoundError on startup

**Cause:** Virtual environment is not activated.  
**Fix:**

```bash
source "/Users/admin/Documents/Google Agentic framework/.venv/bin/activate"
```

---

### Nodes do not appear in the browser

**Cause:** D3.js loaded from CDN — check internet connectivity.  
**Fix:** The graph requires `cdnjs.cloudflare.com` for D3.js. Ensure you have internet access, or download D3.js locally:

```bash
curl -o "/Users/admin/Documents/Google Agentic framework/ims_digital_twin/static/d3.min.js" \
  "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"
```

Then edit `static/index.html` line 5, change the CDN URL to `/static/d3.min.js`.

---

### Generated config files not appearing

Config files are saved to:

```
/Users/admin/Documents/Google Agentic framework/ims_digital_twin/output/
```

List them:

```bash
ls -lh "/Users/admin/Documents/Google Agentic framework/ims_digital_twin/output/"
```

---

## 8. Quick Reference Card

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
│  DEMO FLOW                                                      │
│  1. Click a fault scenario button  (right panel)                │
│  2. Click a node to inspect config (graph)                      │
│  3. Click a user action button     (sim panel)                  │
│  4. Click ⚙ Config                 (generate ACLI fix)          │
│  5. Click 🤖 AI                    (stream AI analysis)         │
│  6. Click ✓ Fix                    (apply remediation)          │
│  7. Click ↺                        (reset to idle)              │
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
│  Ollama   : http://localhost:11434                              │
└─────────────────────────────────────────────────────────────────┘
```

---

*IMS Network Digital Twin · Google ADK + Gemma4:e4b + Oracle SBC + Kamailio 5.8*
