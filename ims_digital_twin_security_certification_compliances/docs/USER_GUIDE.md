# IMS Digital Twin — Security Certification & Compliance Auditor
## User Guide v1.0

---

## Overview

The **IMS Digital Twin Security Certification & Compliance Auditor** is an interactive platform that audits an IP Multimedia Subsystem (IMS) network twin against six major AI/telecom regulatory frameworks. It uses a locally-running **Gemma 4:e4b** AI model (via Google ADK and Ollama) in **Thinking Mode** to generate specific, production-ready **Kamailio SIP router configuration fixes** for each non-compliant control.

### What It Does

1. **Simulates compliance failures** in a realistic Kamailio/IMS environment (SIP PII leaks, DDoS floods, unlogged AI routing decisions, etc.)
2. **Evaluates the twin** against 6 regulatory frameworks: UK TSA, EU AI Act, ISO 42001, NIST AI RMF, MIT AI Risk, OECD AI Principles
3. **Generates AI-powered Kamailio fixes** using Gemma 4's chain-of-thought reasoning
4. **Produces compliance reports** with per-framework scores and risk levels

---

## Prerequisites

### 1. Python Environment
```bash
python >= 3.10
pip install -r requirements.txt
```

### 2. Ollama with Gemma 4:e4b
```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# Pull the Gemma 4 model (in another terminal)
ollama pull gemma4:e4b

# Verify
ollama list | grep gemma4
```

### 3. Google ADK (included in requirements.txt)
The project uses `google-adk` with `LiteLlm` to interface with the locally-running Gemma model over the Ollama API.

---

## Installation

```bash
# Clone repository
git clone https://github.com/your-org/ims_digital_twin_security_certification_compliances.git
cd ims_digital_twin_security_certification_compliances

# Install dependencies
pip install -r requirements.txt

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

---

## Quick Start

### Option A — Interactive Web Dashboard

```bash
python -m ims_digital_twin_security_certification_compliances.main --web
# Open: http://localhost:8001
```

**Dashboard workflow:**
1. Click **Run Audit** in the sidebar
2. Select one or more compliance frameworks (e.g., UK TSA + EU AI Act)
3. Select a fault scenario (e.g., "SIP PII Header Leak")
4. Click **⚡ Inject Fault & Run Audit**
5. Review findings in the **Findings** tab
6. Click **🤖 Fix** on any NON_COMPLIANT finding to stream a Kamailio fix
7. View the full AI analysis in **AI Remediation** → **Analyze & Remediate**

### Option B — Interactive CLI

```bash
python -m ims_digital_twin_security_certification_compliances.main
# Follow the interactive prompts to select frameworks and scenarios
```

### Option C — Direct CLI Commands

```bash
# List available scenarios
python -m ims_digital_twin_security_certification_compliances.main --list-scenarios

# List available frameworks
python -m ims_digital_twin_security_certification_compliances.main --list-frameworks

# Run audit: PII leak against UK TSA + OECD AI
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario pii_sip_header_leak \
    --frameworks uk_tsa oecd_ai

# Run audit: Unlogged AI routing against EU AI Act + ISO 42001 + NIST
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario unlogged_ai_routing \
    --frameworks eu_ai_act iso_42001 nist_ai_rmf

# Full audit against all 6 frameworks
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario ddos_invite_flood \
    --all-frameworks

# Skip AI remediation (faster, evaluation only)
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario rogue_sip_registration \
    --frameworks uk_tsa \
    --no-ai
```

---

## Compliance Frameworks

### 🇬🇧 UK TSA (Telecoms Security Act 2021)
**6 controls** covering IMS signaling security obligations:
| Control ID | Name | Severity |
|---|---|---|
| TSA-SIG-001 | SIP Signaling Data Anonymization | CRITICAL |
| TSA-SIG-002 | Rogue SIP Registration Detection | HIGH |
| TSA-SIG-003 | Core Infrastructure Resiliency | CRITICAL |
| TSA-SIG-004 | DoS/DDoS SIP INVITE Rate Limiting | HIGH |
| TSA-SIG-005 | SIP Transport Encryption (TLS) | CRITICAL |
| TSA-SIG-006 | Continuous Security Monitoring | MEDIUM |

### 🇪🇺 EU AI Act (Regulation 2024/1689)
**6 controls** for AI systems in critical telecom infrastructure:
| Control ID | Name | Severity |
|---|---|---|
| EUAI-HRC-001 | High-Risk AI System Classification | CRITICAL |
| EUAI-HRC-002 | Automated Routing Decision Audit Trail | CRITICAL |
| EUAI-HRC-003 | Biometric Processing Consent Logging | HIGH |
| EUAI-HRC-004 | AI Model Drift Detection and Logging | HIGH |
| EUAI-HRC-005 | Human Oversight Mechanism | HIGH |
| EUAI-HRC-006 | Technical Documentation Completeness | MEDIUM |

### 🌐 ISO 42001 (AI Management System)
**6 controls** for AI governance and data lineage:
| Control ID | Name | Severity |
|---|---|---|
| ISO42-GOV-001 | AI Governance Policy and Accountability | HIGH |
| ISO42-GOV-002 | AI Risk Logging Pipeline | CRITICAL |
| ISO42-GOV-003 | Data Lineage Audit for Network Twin | HIGH |
| ISO42-GOV-004 | AI Model Change Management | HIGH |
| ISO42-GOV-005 | AI System Performance Monitoring | MEDIUM |
| ISO42-GOV-006 | AI Incident Response Plan | MEDIUM |

### 🇺🇸 NIST AI RMF (Risk Management Framework 1.0)
**6 controls** across GOVERN, MAP, MEASURE, MANAGE functions:
| Control ID | Name | Severity |
|---|---|---|
| NIST-GOVERN-001 | AI Trustworthiness Metrics Definition | HIGH |
| NIST-MAP-001 | Adversarial Prompt-Injection Defense | CRITICAL |
| NIST-MEASURE-001 | System Explainability and Decision Logging | HIGH |
| NIST-MAP-002 | AI Risk Context Identification | HIGH |
| NIST-MANAGE-001 | AI Incident Detection and Response | HIGH |
| NIST-MEASURE-002 | Bias and Fairness Monitoring | MEDIUM |

### 🎓 MIT AI Risk Repository
**5 controls** for structural optimization loop safety:
| Control ID | Name | Severity |
|---|---|---|
| MIT-STRUCT-001 | Optimization Loop Stability Assessment | HIGH |
| MIT-STRUCT-002 | Feedback Loop Stability Analysis | HIGH |
| MIT-STRUCT-003 | Constraint Violation Detection | CRITICAL |
| MIT-STRUCT-004 | Optimization Objective Alignment Verification | MEDIUM |
| MIT-STRUCT-005 | Telemetry Input Vulnerability Assessment | HIGH |

### 🌍 OECD AI Principles
**5 controls** for transparency, accountability, and fairness:
| Control ID | Name | Severity |
|---|---|---|
| OECD-TRANS-001 | Transparency of Automated Calling Logic | HIGH |
| OECD-ACCNT-001 | Accountability Trace Completeness | HIGH |
| OECD-FAIR-001 | Fair Resource Allocation Verification | MEDIUM |
| OECD-SAFE-001 | Safety by Design in AI Routing | HIGH |
| OECD-PRIV-001 | Privacy by Design in Call Routing | HIGH |

---

## Fault Scenarios

| Key | Name | Violations |
|---|---|---|
| `pii_sip_header_leak` | SIP PII Header Leak | UK TSA TSA-SIG-001, OECD OECD-PRIV-001 |
| `rogue_sip_registration` | Rogue SIP Registration | UK TSA TSA-SIG-002 |
| `ddos_invite_flood` | DDoS SIP INVITE Flood | UK TSA TSA-SIG-004 |
| `unlogged_ai_routing` | Unlogged AI Routing Decision | EU AI Act EUAI-HRC-002, ISO42 ISO42-GOV-002, NIST NIST-MEASURE-001 |
| `biometric_voice_no_consent` | Voice Biometric Without Consent | EU AI Act EUAI-HRC-003 |
| `adversarial_sip_injection` | Adversarial SIP Header Injection | NIST NIST-MAP-001, UK TSA TSA-SIG-001 |
| `ai_drift_unmonitored` | AI Model Drift (Unmonitored) | ISO42 ISO42-GOV-002, EU AI Act EUAI-HRC-004 |

---

## AI Integration: Gemma 4:e4b Thinking Mode

### Configuration
```python
GemmaComplianceAdvisor(
    ollama_url="http://localhost:11434",
    model="ollama_chat/gemma4:e4b",
    temperature=1.0,   # Gemma 4 recommended
    top_p=0.95,
    top_k=64,
    thinking_mode=True,
)
```

### Thinking Mode Protocol
Gemma 4's chain-of-thought is activated by prefixing the system prompt with the `<|think|>` token. The model then emits a structured thinking block before its final answer:

```
<|channel>thought
[Gemma's internal reasoning about the compliance violation, Kamailio module selection,
 and remediation approach — typically 200-800 tokens]
<channel|>

[Final clean answer with kamailio.cfg configuration blocks]
```

The wrapper strips the `<|channel>thought...<channel|>` block automatically and returns both parts separately: `GemmaResponse.thinking_block` and `GemmaResponse.final_answer`.

### Example AI-Generated Kamailio Fix (TSA-SIG-001)

```cfg
# Compliance Fix: TSA-SIG-001 — SIP Signaling Data Anonymization
# Framework: uk_tsa

loadmodule "pv.so"
loadmodule "textopsx.so"
loadmodule "crypto.so"

# Route block: anonymize SIP headers before logging
route[ANONYMIZE_HEADERS] {
    # Replace real MSISDN with HMAC pseudonym — TSA-SIG-001
    $var(anon_from) = "session-" + $mb_hmac_sha256($fU);
    $var(anon_to)   = "session-" + $mb_hmac_sha256($tU);

    # Rewrite To/From for logging
    remove_hf("P-Asserted-Identity");  # Remove PII assertion
    append_hf("X-Anon-From: $var(anon_from)\r\n");

    # Log with pseudonym only
    xlog("L_NOTICE", "CALL[$ci]: anon:$var(anon_from) -> anon:$var(anon_to)\n");
}
```

---

## Output Files

All generated configurations and reports are saved to `output/`:

| File | Description |
|---|---|
| `kamailio_{INC}_{CTRL_ID}.cfg` | Kamailio configuration fix for a specific control |
| `compliance_report_{INC}.json` | Full JSON audit report with all findings and scores |

---

## Web API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/frameworks` | GET | List all compliance frameworks |
| `/api/scenarios` | GET | List all fault scenarios |
| `/api/state` | GET | Current pipeline state |
| `/api/inject` | POST | Inject fault scenario `{scenario_key, framework_keys}` |
| `/api/evaluate` | POST | Run compliance evaluation |
| `/api/reset` | POST | Reset all state |
| `/api/ai/health` | GET | Check Ollama/Gemma availability |
| `/api/ai/analyze` | GET | SSE stream: full scenario analysis |
| `/api/ai/remediate/{control_id}` | GET | SSE stream: fix for specific control |

---

## Architecture

```
ims_digital_twin_security_certification_compliances/
├── compliance/
│   ├── matrix.py          # Framework registry & control definitions
│   ├── evaluator.py       # Control evaluation engine → AuditReport
│   └── frameworks/        # Per-framework control sets (6 files)
├── simulation/
│   └── kamailio_sim.py    # 7 compliance fault injection scenarios
├── ai/
│   └── gemma_wrapper.py   # Google ADK + Gemma 4:e4b with thinking mode
├── pipeline/
│   └── audit_pipeline.py  # Full orchestration workflow
├── static/
│   └── index.html         # Rich compliance dashboard UI
├── web_server.py          # FastAPI server with SSE streaming
└── main.py                # CLI entry point (interactive + subcommands)
```

---

## Troubleshooting

### Ollama not reachable
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Gemma 4:e4b not available
```bash
# List available models
ollama list

# Pull if missing
ollama pull gemma4:e4b
```

### ImportError for ims_digital_twin
The project imports `NetworkStateTwin` from the parent `ims_digital_twin` project. If that project isn't in your Python path, the twin state is simulated without it — compliance evaluation still works correctly.

```bash
# Add parent workspace to path
export PYTHONPATH="/path/to/Google Agentic framework:$PYTHONPATH"
```

### Port already in use
```bash
# Use a different port
python -m ims_digital_twin_security_certification_compliances.main --web --port 8002
```
