"""
IMS Digital Twin — Security Certification & Compliance Dashboard
FastAPI web server with SSE streaming AI analysis and interactive compliance UI.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["PYTHONUTF8"] = "1"

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ims_digital_twin_security_certification_compliances.compliance.matrix import (
    FRAMEWORK_REGISTRY, list_frameworks,
)
from ims_digital_twin_security_certification_compliances.compliance.evaluator import (
    ComplianceEvaluator, ControlStatus,
)
from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
    COMPLIANCE_SCENARIOS, KamailioSimulator, inject_compliance_fault,
)
from ims_digital_twin_security_certification_compliances.ai.gemma_wrapper import (
    GemmaComplianceAdvisor, _THINKING_SYSTEM,
)

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e4b"
STATIC_DIR   = Path(__file__).parent / "static"


# ── Application State ─────────────────────────────────────────────────────────

class ComplianceState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.phase = "idle"
        self.selected_frameworks: List[str] = []
        self.scenario_key: Optional[str] = None
        self.logs: List[str] = []
        self.sip_trace: str = ""
        self.kamailio_cfg_issue: str = ""
        self.audit_report: Optional[Dict] = None
        self.remediation_results: List[Dict] = []
        self.ai_summary: str = ""
        self.incident_id: Optional[str] = None
        self.twin = None
        self._last_ai_context: str = ""

    def inject(self, scenario_key: str, framework_keys: List[str]) -> None:
        self.reset()
        self.selected_frameworks = framework_keys
        self.scenario_key = scenario_key

        # Try to use the real IMS twin
        try:
            from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
            from ims_digital_twin.tools import twin_tools
            self.twin = NetworkStateTwin()
            twin_tools.register_twin(self.twin)
        except ImportError:
            self.twin = None

        logs, trace, cfg_issue = inject_compliance_fault(scenario_key, self.twin)
        self.logs = logs
        self.sip_trace = trace
        self.kamailio_cfg_issue = cfg_issue
        self.incident_id = getattr(self.twin, 'incident_id', None) or \
            f"INC-{uuid.uuid4().hex[:8].upper()}"
        if self.twin:
            self.twin.incident_id = self.incident_id
        self.phase = "injected"
        self._last_ai_context = self._build_ai_context()

    def evaluate(self) -> Dict:
        evaluator = ComplianceEvaluator()
        report = evaluator.evaluate(
            twin=self.twin,
            logs=self.logs,
            framework_keys=self.selected_frameworks,
        )
        self.audit_report = report.to_dict()
        self.phase = "evaluated"
        return self.audit_report

    def apply_remediation(self, control_id: str, kamailio_config: str, steps: List[str]):
        self.remediation_results.append({
            "control_id": control_id,
            "kamailio_config": kamailio_config,
            "steps": steps,
            "status": "APPLIED",
        })
        # Mark finding as patched in report
        if self.audit_report:
            for f in self.audit_report.get("findings", []):
                if f["control_id"] == control_id:
                    f["status"] = "COMPLIANT"
                    f["ai_remediation"] = kamailio_config[:500]

    def _build_ai_context(self) -> str:
        scen = COMPLIANCE_SCENARIOS.get(self.scenario_key or "", {})
        logs_sample = "\n".join(self.logs[-15:]) if self.logs else ""
        frameworks_str = ", ".join(self.selected_frameworks)
        return f"""{_THINKING_SYSTEM}

COMPLIANCE AUDIT CONTEXT:
==========================
Scenario:    {scen.get('name', self.scenario_key)} ({self.scenario_key})
Incident ID: {self.incident_id}
Frameworks:  {frameworks_str}

KAMAILIO CONFIGURATION ISSUE:
{self.kamailio_cfg_issue or "See log evidence"}

SIP TRACE:
{self.sip_trace or "See logs"}

RECENT KAMAILIO LOGS:
{logs_sample}

TASK: Analyze this compliance failure and generate a complete Kamailio configuration fix
that remediates all violated controls. Reference specific control IDs in your response.
"""


STATE = ComplianceState()


# ── FastAPI Application ───────────────────────────────────────────────────────

app = FastAPI(title="IMS Compliance Audit Dashboard", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


# ── Framework API ─────────────────────────────────────────────────────────────

@app.get("/api/frameworks")
async def get_frameworks():
    from ims_digital_twin_security_certification_compliances.compliance.matrix import (
        FRAMEWORK_REGISTRY,
    )
    frameworks = []
    for fw in FRAMEWORK_REGISTRY.values():
        frameworks.append({
            "key": fw.key,
            "name": fw.name,
            "full_name": fw.full_name,
            "jurisdiction": fw.jurisdiction,
            "description": fw.description,
            "icon": fw.icon,
            "color": fw.color,
            "control_count": len(fw.controls),
            "controls": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "severity": c.severity.value,
                    "category": c.category,
                    "telecom_vector": c.telecom_vector,
                    "evidence_hint": c.evidence_hint,
                    "remediation_hint": c.remediation_hint,
                    "kamailio_module": c.kamailio_module,
                }
                for c in fw.controls
            ],
        })
    return {"frameworks": frameworks}


@app.get("/api/scenarios")
async def get_scenarios():
    return {
        "scenarios": [
            {
                "key": k,
                "name": v["name"],
                "description": v["description"],
                "frameworks": v["frameworks"],
            }
            for k, v in COMPLIANCE_SCENARIOS.items()
        ]
    }


# ── Audit State API ───────────────────────────────────────────────────────────

@app.get("/api/state")
async def get_state():
    return STATE.to_dict() if hasattr(STATE, 'to_dict') else {
        "phase": STATE.phase,
        "selected_frameworks": STATE.selected_frameworks,
        "scenario_key": STATE.scenario_key,
        "incident_id": STATE.incident_id,
        "log_count": len(STATE.logs),
        "logs": STATE.logs,
        "sip_trace": STATE.sip_trace,
        "kamailio_cfg_issue": STATE.kamailio_cfg_issue,
        "audit_report": STATE.audit_report,
        "remediation_results": STATE.remediation_results,
        "ai_summary": STATE.ai_summary,
    }


@app.post("/api/inject")
async def inject_scenario(body: Dict[str, Any] = None):
    from ims_digital_twin_security_certification_compliances.simulation.kamailio_sim import (
        COMPLIANCE_SCENARIOS,
    )
    if body is None:
        body = {}
    scenario_key = body.get("scenario_key", "pii_sip_header_leak")
    framework_keys = body.get("framework_keys", ["uk_tsa"])

    if scenario_key not in COMPLIANCE_SCENARIOS:
        raise HTTPException(404, f"Unknown scenario: {scenario_key}")
    for fk in framework_keys:
        if fk not in FRAMEWORK_REGISTRY:
            raise HTTPException(404, f"Unknown framework: {fk}")

    STATE.inject(scenario_key, framework_keys)
    
    scenario = COMPLIANCE_SCENARIOS.get(scenario_key, {})
    
    return {
        "ok": True,
        "incident_id": STATE.incident_id,
        "scenario_key": scenario_key,
        "scenario_name": scenario.get("name", scenario_key),
        "scenario_description": scenario.get("description", ""),
        "scenario_frameworks": scenario.get("frameworks", []),
        "log_count": len(STATE.logs),
        "frameworks": framework_keys,
        "injection_details": {
            "logs_sample": "\n".join(STATE.logs[-10:]) if STATE.logs else "",
            "sip_trace": STATE.sip_trace,
            "kamailio_cfg_issue": STATE.kamailio_cfg_issue,
        },
    }


@app.post("/api/evaluate")
async def run_evaluation():
    if STATE.phase == "idle":
        raise HTTPException(400, "No scenario injected. Call /api/inject first.")
    report = STATE.evaluate()
    return {"ok": True, "report": report}


@app.post("/api/remediate")
async def apply_remediation(body: Dict[str, Any] = None):
    if body is None:
        body = {}
    control_id = body.get("control_id", "")
    kamailio_config = body.get("kamailio_config", "")
    steps = body.get("steps", [])
    STATE.apply_remediation(control_id, kamailio_config, steps)
    return {"ok": True, "control_id": control_id, "status": "APPLIED"}


@app.post("/api/reset")
async def reset():
    STATE.reset()
    return {"ok": True, "phase": "idle"}


# ── AI Health & Streaming API ─────────────────────────────────────────────────

@app.get("/api/ai/health")
async def ai_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            available = OLLAMA_MODEL in models or any(OLLAMA_MODEL in m for m in models)
            return {"ok": available, "model": OLLAMA_MODEL, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e), "model": OLLAMA_MODEL}


@app.get("/api/ai/analyze")
async def ai_analyze():
    """Stream Gemma 4 analysis with thinking mode via SSE."""
    if STATE.phase == "idle":
        async def idle_msg():
            msg = "No active compliance scenario. Inject a fault scenario first, then click Analyze."
            yield f"data: {json.dumps({'token': msg, 'type': 'answer'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(idle_msg(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    context = STATE._last_ai_context or STATE._build_ai_context()

    async def stream_gemma():
        in_thinking = False
        buffer = ""
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": context,
                        "stream": True,
                        "options": {
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 64,
                            "num_predict": 2048,
                        },
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                buffer += token
                                # Detect and stream thinking block separately
                                if "<|channel>" in buffer or "<think>" in buffer:
                                    in_thinking = True
                                if in_thinking:
                                    if "<channel|>" in buffer or "</think>" in buffer:
                                        in_thinking = False
                                        import re
                                        from ims_digital_twin_security_certification_compliances.ai.gemma_wrapper import (
                                            _THOUGHT_BLOCK_RE, _THINK_TAG_RE
                                        )
                                        thinking_block = ""
                                        m = _THOUGHT_BLOCK_RE.search(buffer)
                                        if m:
                                            thinking_block = m.group(0)
                                        m2 = _THINK_TAG_RE.search(buffer)
                                        if m2:
                                            thinking_block = m2.group(0)
                                        clean = _THOUGHT_BLOCK_RE.sub("", buffer)
                                        clean = _THINK_TAG_RE.sub("", clean).strip()
                                        if thinking_block:
                                            yield f"data: {json.dumps({'token': thinking_block[:400], 'type': 'thinking'})}\n\n"
                                        yield f"data: {json.dumps({'token': clean, 'type': 'answer'})}\n\n"
                                        buffer = ""
                                    else:
                                        yield f"data: {json.dumps({'token': token, 'type': 'thinking'})}\n\n"
                                else:
                                    yield f"data: {json.dumps({'token': token, 'type': 'answer'})}\n\n"
                                    buffer = ""
                            if data.get("done", False):
                                if buffer and not in_thinking:
                                    yield f"data: {json.dumps({'token': buffer, 'type': 'answer'})}\n\n"
                                yield f"data: {json.dumps({'done': True})}\n\n"
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield f"data: {json.dumps({'token': '⚠ Ollama not reachable at {OLLAMA_URL}. Run: ollama serve', 'type': 'error'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'⚠ AI error: {str(e)[:200]}', 'type': 'error'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        stream_gemma(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/ai/remediate/{control_id}")
async def ai_remediate_control(control_id: str):
    """Stream AI-generated Kamailio fix for a specific control ID."""
    if not STATE.audit_report:
        raise HTTPException(400, "No audit report. Run evaluation first.")

    finding = next(
        (f for f in STATE.audit_report.get("findings", [])
         if f["control_id"] == control_id),
        None
    )
    if not finding:
        raise HTTPException(404, f"Control {control_id} not found in audit report")

    logs_sample = "\n".join(STATE.logs[-15:])
    prompt = (
        f"{_THINKING_SYSTEM}\n\n"
        f"COMPLIANCE FINDING: {control_id}\n"
        f"Framework: {finding['framework']}\n"
        f"Control: {finding['control_name']}\n"
        f"Status: {finding['status']}\n"
        f"Severity: {finding['severity']}\n"
        f"Telecom Vector: {finding['telecom_vector']}\n"
        f"Kamailio Module: {finding.get('kamailio_module', 'N/A')}\n\n"
        f"LOGS:\n{logs_sample}\n\n"
        f"SIP TRACE:\n{STATE.sip_trace or 'N/A'}\n\n"
        f"CFG ISSUE:\n{STATE.kamailio_cfg_issue or 'N/A'}\n\n"
        f"Generate a complete kamailio.cfg fix with compliance annotations for {control_id}:"
    )

    async def stream_fix():
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": True,
                        "options": {"temperature": 1.0, "top_p": 0.95, "top_k": 64,
                                    "num_predict": 2048},
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if data.get("done"):
                                yield f"data: {json.dumps({'done': True, 'control_id': control_id})}\n\n"
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'token': f'Error: {e}', 'done': True})}\n\n"

    return StreamingResponse(
        stream_fix(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  IMS Digital Twin — Security Certification & Compliance Dashboard")
    print("  Open: http://localhost:8001\n")
    uvicorn.run(
        "ims_digital_twin_security_certification_compliances.web_server:app",
        host="0.0.0.0", port=8001, reload=False, log_level="warning",
    )
