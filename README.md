# IMS Network Digital Twin

> **AI-powered IMS fault simulation and Oracle SBC root-cause analysis** — built on Google ADK, Gemma4 (Ollama), FastAPI, and Kamailio.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green)](https://fastapi.tiangolo.com)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-1.18-orange)](https://google.github.io/adk-docs/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-1.83-purple)](https://docs.litellm.ai)
[![Ollama](https://img.shields.io/badge/Ollama-Gemma4-red)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

The **IMS Network Digital Twin** is a full-stack demo that simulates a live 7-node IMS (IP Multimedia Subsystem) network running on an Oracle Session Border Controller. It provides:

- **Interactive web topology** — clickable D3.js graph with Oracle SBC, Kamailio P-CSCF / I-CSCF / S-CSCF, HSS, PCRF, and MGW nodes
- **Fault injection engine** — 6 production-realistic failure scenarios with live alarms and SBC syslog simulation
- **User simulation** — SIP REGISTER / INVITE / MESSAGE / DEREGISTER flows for 3 virtual UEs (Alice, Bob, Charlie)
- **Streaming AI analysis** — Gemma4:e4b (local Ollama) streams a live technical RCA report via SSE
- **ACLI config generation** — Oracle SBC remediation configs saved to `ims_digital_twin/output/`
- **REST API** — 15 endpoints for automation, CI/CD integration, and external tooling

---

## Architecture

```
Browser / curl / REST client
        │
        ▼  http://localhost:8000
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Web Server  (ims_digital_twin/web_server.py)           │
│  GET /  ·  /api/scenarios  ·  /api/state  ·  /api/node/{id}    │
│  POST /api/inject  ·  /api/generate_config  ·  /api/apply_fix  │
│  POST /api/sim/*   ·  GET /api/ai/analyze  (SSE)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  NetworkStateTwin    FaultScenarios       UserSimulator
  (7 IMS nodes)       (6 scenarios)       (Alice/Bob/Charlie)
  KPIs · alarms       SBC syslogs         SIP traces
  config state        topology mutations
        │
        ▼  (CLI mode only — no browser needed)
  Google ADK 3-Agent Pipeline
  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐
  │ log_analyzer │→ │  rca_agent  │→ │ config_generator │
  │  (LogTools)  │  │ (TwinTools) │  │  (ConfigTools)   │
  └──────────────┘  └─────────────┘  └──────────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                     LiteLLM → Ollama
                        (Gemma4:e4b)
                            │
                  ims_digital_twin/output/
               remediation_<INC>_<scenario>.acli
```

See [sequence_diagram.md](sequence_diagram.md) for the full Mermaid sequence diagram.

---

## Tech Stack

| Component | Version | Role |
|-----------|---------|------|
| Python | 3.9+ | Runtime |
| FastAPI | 0.128 | REST API + SSE streaming |
| Uvicorn | 0.39 | ASGI server |
| Google ADK | 1.18 | Multi-agent orchestration (CLI mode) |
| LiteLLM | 1.83 | LLM provider bridge |
| Ollama | 0.30+ | Local LLM runtime |
| Gemma4:e4b | — | AI model for RCA + analysis |
| D3.js | 7.9 | Interactive network topology graph |
| httpx | latest | Async HTTP (Ollama SSE client) |

---

## Prerequisites

**1. Python 3.9+**
```bash
python3 --version
```

**2. Ollama running with Gemma4**
```bash
# Start Ollama
ollama serve

# Pull the model (first time only, ~5 GB)
ollama pull gemma4:e4b

# Verify
ollama list   # should show gemma4:e4b
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sushil246/ims-digital-twin.git
cd ims-digital-twin

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install google-adk litellm fastapi "uvicorn[standard]" httpx

# 4. Start the web server
python -m ims_digital_twin.web_server

# 5. Open the dashboard
open http://localhost:8000
```

---

## Fault Scenarios

| Key | Name | Root Symptom |
|-----|------|-------------|
| `reg_storm` | SIP Registration Storm | CPU 94 %, REGISTER rate 1820/s, 503 overload |
| `tls_cert_expiry` | TLS Certificate Expiry | SSL handshake fail, 500 TLS transport error |
| `rtp_timeout` | RTP Media Timeout | 48 sessions cleared, one-way audio, NAT latch fail |
| `codec_mismatch` | SIP Codec / SDP Mismatch | 488 Not Acceptable, G.729 stripped from SDP |
| `pcscf_down` | Upstream P-CSCF Unreachable | OPTIONS timeout ×3, OOS, all INVITEs 503 |
| `srtp_dtls_fail` | SRTP/DTLS Negotiation Failure | DTLS cipher mismatch 62 %, calls connect with no audio |

---

## Web Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER — Status chip | Incident ID | gemma4:e4b ✓                   │
├──────────────────────────────────────┬───────────────────────────────┤
│                                      │ Fault Scenario Buttons        │
│   NETWORK TOPOLOGY  (D3.js)          │ ⚙ Config  ✓ Fix  🤖 AI  ↺   │
│                                      ├───────────────────────────────┤
│  UE → Oracle SBC → P-CSCF → I-CSCF  │ Active Alarms                 │
│                         → S-CSCF    ├───────────────────────────────┤
│                    → HSS   → MGW    │ User Simulation               │
│                    ↕ PCRF           │ Alice · Bob · Charlie         │
├──────────────────┬───────────────────┴───────────────────────────────┤
│ Oracle SBC Logs  │ SIP Protocol Trace │ Gemma4 AI Analysis (stream)  │
└──────────────────┴──────────────────────────────────────────────────┘
```

### Demo flow

1. Click a **fault scenario** button → nodes turn red/orange, alarms populate, SBC logs stream
2. Click any **node** → detail modal with Config / Runtime / Interfaces / Alarms tabs
3. Click a **user action** (Register / Call / Message / Flood) → SIP trace appears
4. Click **⚙ Config** → Oracle SBC ACLI remediation config generated and saved
5. Click **🤖 AI** → Gemma4 streams live RCA with root cause, impact, and fix steps
6. Click **✓ Fix** → all nodes restore to green, alarms clear
7. Click **↺** → reset to idle

### Node detail modal tabs

| Tab | Content |
|-----|---------|
| Overview | IP, software version, uptime, live CPU/memory bars, session count |
| Config | Full config — Oracle ACLI for SBC, Kamailio `.cfg` for IMS nodes |
| Runtime | Process table (PID, CPU %, memory %, state), live config snapshot |
| Interfaces | NIC table (IP, MAC, speed, role), active TCP/UDP connections |
| Alarms | Current alarms on this node |

### Virtual users

| User | UA | Codec | Notes |
|------|----|-------|-------|
| 👩 Alice | Zoiper 5.6 (iOS 17) | G.711 / G.729 / OPUS | |
| 👨 Bob | Linphone 5.3 (Android 14) | G.711 / AMR-NB / AMR-WB | |
| 🧑 Charlie | MicroSIP 3.21 (Windows 11) | G.729 only | Triggers 488 in `codec_mismatch` |

---

## REST API Reference

Base URL: `http://localhost:8000`

Interactive docs: [`http://localhost:8000/docs`](http://localhost:8000/docs) (FastAPI Swagger UI)

### Scenario Management

```bash
# List all fault scenarios
GET  /api/scenarios

# Inject a fault scenario
POST /api/inject/{scenario_key}
```

```bash
curl http://localhost:8000/api/scenarios
curl -X POST http://localhost:8000/api/inject/reg_storm
curl -X POST http://localhost:8000/api/inject/tls_cert_expiry
curl -X POST http://localhost:8000/api/inject/pcscf_down
```

**Inject response:**
```json
{
  "ok": true,
  "incident_id": "INC-A1B2C3D4",
  "scenario": "reg_storm",
  "log_count": 18,
  "alarm_count": 3
}
```

### Twin State

```bash
GET /api/state           # full twin snapshot (nodes, KPIs, alarms, logs, config)
GET /api/node/{node_id}  # node detail with config text, runtime, live KPIs
```

`node_id` values: `sbc01 · pcscf01 · icscf01 · scscf01 · hss01 · pcrf01 · mgw01`

**State response (abbreviated):**
```json
{
  "phase": "injected",
  "scenario_key": "reg_storm",
  "incident_id": "INC-A1B2C3D4",
  "twin": {
    "nodes": {
      "sbc01": {"status": "UP", "cpu_pct": 94.3, "sessions": 4988, "alarms": ["CRITICAL: CPU 94%"]}
    },
    "links": [{"type": "SBC_Access", "src": "ue", "dst": "sbc01", "status": "UP"}],
    "total_alarms": 3
  },
  "logs": ["Jun 07 10:00:00 sbc01 APKT[sipd]: REGISTER ..."],
  "alarms": [{"node": "sbc01", "alarm": "CRITICAL: CPU utilization 94%"}]
}
```

**Phase values:** `idle` → `injected` → `fixing` → `fixed`

### Remediation

```bash
POST /api/generate_config  # generate Oracle SBC ACLI config for active fault
POST /api/apply_fix        # simulate config push — restore all nodes to UP
POST /api/reset            # clear everything, return to idle
```

```bash
curl -X POST http://localhost:8000/api/generate_config
curl -X POST http://localhost:8000/api/apply_fix
curl -X POST http://localhost:8000/api/reset
```

### User Simulation

```bash
POST /api/sim/register/{user_id}              # SIP REGISTER
POST /api/sim/call/{caller}/{callee}          # SIP INVITE voice call
POST /api/sim/message/{sender}/{recipient}    # SIP MESSAGE
POST /api/sim/flood/{user_id}?count=100       # REGISTER flood (always rate-limited)
POST /api/sim/deregister/{user_id}            # REGISTER Expires:0
```

```bash
curl -X POST http://localhost:8000/api/sim/register/alice
curl -X POST http://localhost:8000/api/sim/call/alice/bob
curl -X POST http://localhost:8000/api/sim/call/charlie/bob   # 488 in codec_mismatch
curl -X POST "http://localhost:8000/api/sim/flood/alice?count=200"
curl -X POST http://localhost:8000/api/sim/deregister/alice
```

**Call outcome by scenario:**

| Scenario | Outcome |
|----------|---------|
| idle / fixed | 200 OK — SRTP call established |
| `codec_mismatch` | 488 Not Acceptable Here |
| `pcscf_down` | 503 Service Unavailable |
| `srtp_dtls_fail` | 200 OK (SIP) — no media, DTLS cipher mismatch |
| `rtp_timeout` | 200 OK (SIP) — one-way audio, RTP timeout |

### AI Analysis (SSE Streaming)

```bash
GET /api/ai/health    # check Ollama + gemma4:e4b availability
GET /api/ai/analyze   # stream RCA as Server-Sent Events
```

The AI analysis endpoint streams **one token per SSE event** until `done: true`:

```
data: {"token": "The"}
data: {"token": " root"}
data: {"token": " cause"}
...
data: {"done": true}
```

**Streamed analysis sections:**
1. `ROOT CAUSE` — precise technical cause with log line references
2. `IMPACT ASSESSMENT` — affected users and services
3. `IMMEDIATE ACTIONS` — step-by-step remediation with Oracle ACLI commands
4. `ORACLE SBC CONFIG FIX` — exact ACLI block to change
5. `PREVENTION` — monitoring and config hardening

```bash
# Stream with curl (-N disables buffering)
curl -X POST http://localhost:8000/api/inject/pcscf_down
curl -N http://localhost:8000/api/ai/analyze
```

```python
# Python SSE client
import httpx, json

with httpx.stream("GET", "http://localhost:8000/api/ai/analyze") as r:
    for line in r.iter_lines():
        if line.startswith("data:"):
            payload = json.loads(line[5:].strip())
            if payload.get("done"):
                break
            print(payload.get("token", ""), end="", flush=True)
```

```javascript
// JavaScript EventSource
const es = new EventSource("/api/ai/analyze");
es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.done) { es.close(); return; }
    document.getElementById("output").textContent += data.token;
};
```

### Complete Endpoint Table

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

## CLI Mode (No Browser)

Run the full 3-agent ADK pipeline from the terminal without starting the web server.

```bash
cd "path/to/ims-digital-twin"
source .venv/bin/activate

# List all scenarios
python -m ims_digital_twin.main --list

# Twin-only: inject fault and show state — no AI, no Ollama needed
python -m ims_digital_twin.main --scenario reg_storm --twin-only

# Full AI pipeline: Log Analyzer → RCA Agent → Config Generator
python -m ims_digital_twin.main --scenario tls_cert_expiry
python -m ims_digital_twin.main --scenario pcscf_down
python -m ims_digital_twin.main --scenario srtp_dtls_fail

# Use a different model
python -m ims_digital_twin.main --scenario codec_mismatch \
    --model ollama_chat/llama3.1:8b
```

**CLI options:**

```
--scenario  -s   Fault scenario key (default: reg_storm)
--list      -l   List all scenarios and exit
--twin-only      Show twin state + logs without running AI agents
--model     -m   LiteLLM model string (default: ollama_chat/gemma4:e4b)
--ollama-url     Ollama server URL (default: http://localhost:11434)
```

---

## Project Structure

```
ims-digital-twin/
├── ims_digital_twin/
│   ├── web_server.py              # FastAPI app — REST API + SSE AI streaming
│   ├── main.py                    # CLI entry point — ADK 3-agent pipeline
│   ├── digital_twin/
│   │   ├── topology.py            # Static IMS node + link definitions
│   │   ├── network_state.py       # Mutable twin (KPIs, alarms, config)
│   │   └── node_configs.py        # Full config text per node (ACLI / Kamailio)
│   ├── scenarios/
│   │   └── fault_scenarios.py     # 6 fault injection scenarios
│   ├── tools/
│   │   ├── twin_tools.py          # ADK tools: query/update twin state
│   │   ├── log_tools.py           # ADK tools: SBC log search and analysis
│   │   └── config_tools.py        # ADK tools: Oracle SBC ACLI generation
│   ├── agents/
│   │   └── orchestrator.py        # 3-agent pipeline (log → rca → config)
│   ├── simulation/
│   │   └── user_sim.py            # Virtual UE SIP trace generator
│   ├── static/
│   │   └── index.html             # D3.js dashboard frontend
│   └── output/                    # Generated .acli remediation configs
├── sequence_diagram.md            # Mermaid end-to-end sequence diagram
├── USER_GUIDE.md                  # Full user guide (v3.0)
└── requirements.txt
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser shows blank page | Confirm server is running: `python -m ims_digital_twin.web_server` |
| Port 8000 in use | `pkill -f "ims_digital_twin.web_server"` then restart |
| `gemma4:e4b ✗` in header | `ollama serve` then `ollama pull gemma4:e4b` |
| `ModuleNotFoundError` | `source .venv/bin/activate` |
| Nodes not visible | Check internet (D3.js loads from CDN) — see USER_GUIDE §8.5 for offline fix |
| No `.acli` files generated | Check `ims_digital_twin/output/` — inject a fault then click ⚙ Config |

---

## Related Projects

- [ims-agentic-twin-gemma4](https://github.com/sushil246/ims-agentic-twin-gemma4) — standalone CLI-only version with clean package structure

---

## License

MIT
