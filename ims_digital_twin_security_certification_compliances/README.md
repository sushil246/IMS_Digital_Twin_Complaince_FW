# IMS Digital Twin — Security Certification & Compliance Auditor

An interactive platform that audits an IMS (IP Multimedia Subsystem) network digital twin against **six major AI/telecom regulatory frameworks** using a locally-running **Gemma 4:e4b** AI model with native **Thinking Mode** to generate production-ready **Kamailio SIP router configuration fixes**.

## Compliance Frameworks

| Framework | Jurisdiction | Controls | Focus |
|---|---|---|---|
| 🇬🇧 UK TSA | United Kingdom | 6 | Signaling anonymization, rogue SIP detection, resiliency |
| 🇪🇺 EU AI Act | European Union | 6 | High-risk AI classification, drift logs, biometric consent |
| 🌐 ISO 42001 | International | 6 | AI model governance, risk logging, data lineage |
| 🇺🇸 NIST AI RMF | United States | 6 | Trustworthiness, adversarial defense, explainability |
| 🎓 MIT AI Risk | Academic | 5 | Optimization loop stability, constraint violations |
| 🌍 OECD AI | International | 5 | Transparency, accountability, fair resource allocation |

## Features

- **7 compliance fault scenarios** covering SIP PII leaks, DDoS floods, unlogged AI routing, biometric violations, adversarial SIP injection, and AI drift
- **Gemma 4:e4b Thinking Mode** — prefixes system prompts with `<|think|>`, strips `<|channel>thought...<channel|>` blocks, returns clean Kamailio fixes
- **Google ADK integration** via `LiteLlm(model="ollama_chat/gemma4:e4b")` with `temperature=1.0, top_p=0.95, top_k=64`
- **Rich web dashboard** at `http://localhost:8001` — framework selector, findings table, streaming AI analysis, compliance charts
- **CLI pipeline** — full audit from fault injection → evaluation → AI remediation → JSON report

## Architecture

```
compliance/
  matrix.py          ← Framework registry & control definitions
  evaluator.py       ← AuditReport generation engine
  frameworks/        ← 6 framework modules (34 total controls)
simulation/
  kamailio_sim.py    ← 7 compliance fault injection scenarios
ai/
  gemma_wrapper.py   ← Google ADK + Gemma 4 thinking mode wrapper
pipeline/
  audit_pipeline.py  ← Full 5-phase orchestration workflow
static/
  index.html         ← Compliance dashboard UI
web_server.py        ← FastAPI + SSE streaming server (port 8001)
main.py              ← CLI entry point
```

## Quick Start

```bash
# Prerequisites
ollama pull gemma4:e4b
pip install -r requirements.txt

# Web Dashboard
python -m ims_digital_twin_security_certification_compliances.main --web

# CLI — PII leak audit (UK TSA + OECD AI)
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario pii_sip_header_leak --frameworks uk_tsa oecd_ai

# CLI — Unlogged AI routing (EU AI Act + ISO 42001 + NIST)
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario unlogged_ai_routing --frameworks eu_ai_act iso_42001 nist_ai_rmf

# CLI — Full 6-framework audit
python -m ims_digital_twin_security_certification_compliances.main \
    --scenario adversarial_sip_injection --all-frameworks
```

## Gemma 4 Thinking Mode

```python
from ims_digital_twin_security_certification_compliances.ai.gemma_wrapper import GemmaComplianceAdvisor

advisor = GemmaComplianceAdvisor(
    ollama_url="http://localhost:11434",
    model="ollama_chat/gemma4:e4b",
    temperature=1.0,   # Gemma 4 official recommendation
    top_p=0.95,
    top_k=64,
    thinking_mode=True,
)

response = advisor.remediate_finding(
    finding_data={"control_id": "TSA-SIG-001", "framework": "uk_tsa", ...},
    logs=kamailio_logs,
    sip_trace=sip_trace,
    kamailio_cfg_issue=cfg_issue,
)

print(response.thinking_block)   # Gemma's reasoning chain
print(response.kamailio_config)  # Clean Kamailio fix
print(response.remediation_steps)
```

## Output

Each audit generates files in `output/`:
- `kamailio_{INC-ID}_{CONTROL_ID}.cfg` — Kamailio config fix per finding
- `compliance_report_{INC-ID}.json` — Full JSON report with scores and findings

## Related Project

This project extends [ims_digital_twin](../ims_digital_twin/) — the Oracle SBC RCA digital twin — with a compliance evaluation layer and multi-framework AI remediation pipeline.

## License

MIT License — see [LICENSE](LICENSE)

---

*Powered by Google ADK · Gemma 4:e4b · Kamailio · FastAPI*
