---
name: project-ims-compliance
description: IMS Digital Twin Security Certification & Compliance project — architecture, structure, and key decisions
metadata:
  type: project
---

New project `ims_digital_twin_security_certification_compliances` created at workspace root.

**Why:** Extends the existing `ims_digital_twin` project with a multi-framework regulatory compliance layer and AI-powered Kamailio remediation.

**Architecture:**
- `compliance/` — 6 framework modules (UK TSA, EU AI Act, ISO 42001, NIST AI RMF, MIT AI Risk, OECD AI) with 34 total controls
- `simulation/kamailio_sim.py` — 7 compliance fault injection scenarios with real Kamailio log output
- `ai/gemma_wrapper.py` — Google ADK + LiteLlm wrapper for Gemma 4:e4b with `<|think|>` prefix and `<|channel>thought...<channel|>` block stripping
- `pipeline/audit_pipeline.py` — 5-phase orchestration: inject → evaluate → AI remediate → summarize → report
- `web_server.py` — FastAPI on port 8001 with SSE streaming AI analysis
- `static/index.html` — Compliance dashboard: framework selector, findings table, Chart.js scores, AI streaming

**Gemma 4 config:** temperature=1.0, top_p=0.95, top_k=64, model="ollama_chat/gemma4:e4b"

**How to apply:** CLI: `python -m ims_digital_twin_security_certification_compliances.main --scenario pii_sip_header_leak --frameworks uk_tsa oecd_ai`; Web: `--web` flag → http://localhost:8001

[[project_ims_twin]]
