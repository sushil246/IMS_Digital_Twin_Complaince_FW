"""
IMS Digital Twin — FastAPI web server (v2).
Kamailio nodes, Oracle SBC ACLI, clickable node modals,
user simulation, Gemma4 streaming AI analysis.
"""
from __future__ import annotations
import asyncio
import copy
import json
import os
import sys
import time
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

from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
from ims_digital_twin.digital_twin.topology import ElementStatus
from ims_digital_twin.digital_twin.node_configs import (
    NODE_CONFIG_TEXT, NODE_CONFIG_TYPE, NODE_RUNTIME,
)
from ims_digital_twin.scenarios.fault_scenarios import inject, list_scenarios, SCENARIOS
from ims_digital_twin.tools import twin_tools, log_tools, config_tools
from ims_digital_twin.simulation.user_sim import (
    simulate_register, simulate_call, simulate_message,
    simulate_flood, simulate_deregister, USERS,
)

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e4b"
STATIC_DIR   = Path(__file__).parent / "static"


# ── Application state ─────────────────────────────────────────────────────────

class DemoState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.twin = NetworkStateTwin()
        twin_tools.register_twin(self.twin)
        log_tools.store_logs([])
        self.logs: List[str] = []
        self.sip_trace: str = ""
        self.scenario_key: Optional[str] = None
        self.phase: str = "idle"
        self.generated_config: Optional[str] = None
        self.remediation_steps: List[str] = []
        self.last_ai_context: str = ""

    def inject(self, scenario_key: str):
        self.reset()
        twin, logs = inject(self.twin, scenario_key)
        self.twin = twin
        self.logs = logs
        log_tools.store_logs(logs)
        self.scenario_key = scenario_key
        self.phase = "injected"
        self.last_ai_context = self._build_ai_context()

    def generate_config(self) -> str:
        if not self.scenario_key:
            return ""
        result = config_tools.generate_full_remediation_config(
            incident_id=self.twin.incident_id or "INC-DEMO",
            scenario_key=self.scenario_key,
        )
        self.generated_config = result.get("acli_config", "")
        self.remediation_steps = result.get("remediation_steps", [])
        self.phase = "fixing"
        return self.generated_config

    def apply_fix(self):
        for node in self.twin.nodes.values():
            node.status = ElementStatus.UP
            node.alarms = []
            node.cpu_util_pct = min(node.cpu_util_pct, 30.0)
            node.mem_util_pct = min(node.mem_util_pct, 40.0)
        for lnk in self.twin.links:
            lnk.status = "UP"
            lnk.latency_ms = 2.0
            lnk.packet_loss_pct = 0.0
        self.twin.global_alarms = []
        self.phase = "fixed"
        fix_logs = [
            f"[FIX APPLIED] Remediation config pushed to sbc01 via NETCONF",
            f"[FIX APPLIED] Config validation passed — no syntax errors",
            f"[FIX APPLIED] Reloading affected SBC processes",
            f"[FIX APPLIED] Service health-check: all session-agents UP",
            f"[FIX APPLIED] All alarms cleared — incident {self.twin.incident_id} RESOLVED",
        ]
        self.logs.extend(fix_logs)
        log_tools.store_logs(self.logs)

    def add_sim_logs(self, lines: List[str], trace: str):
        self.logs.extend(lines)
        self.sip_trace = trace
        log_tools.store_logs(self.logs)

    def _build_ai_context(self) -> str:
        summary = self.twin.summary()
        alarms  = self.twin.all_alarms()
        logs_sample = self.logs[-20:] if self.logs else []
        scen_name = SCENARIOS.get(self.scenario_key or "", {}).get("name", self.scenario_key)
        return f"""You are an expert IMS (IP Multimedia Subsystem) network engineer analyzing a live production incident on an Oracle SBC.

INCIDENT ID: {self.twin.incident_id}
FAULT SCENARIO: {scen_name} ({self.scenario_key})
TIMESTAMP: {summary.get('snapshot_ts','')}

NETWORK ELEMENT STATUS:
{json.dumps({k: {'status': v['status'], 'cpu': v['cpu_pct'], 'mem': v['mem_pct'], 'sessions': v['sessions'], 'alarms': v['alarms']} for k, v in summary.get('nodes', {}).items()}, indent=2)}

ACTIVE ALARMS ({len(alarms)} total):
{chr(10).join('- ' + (a['alarm'] if isinstance(a, dict) else str(a)) for a in alarms)}

ORACLE SBC LOGS (latest 20 lines):
{chr(10).join(logs_sample)}

Please analyze this incident and provide:
1. ROOT CAUSE: precise technical root cause (reference specific log lines and config elements)
2. IMPACT ASSESSMENT: which users/services are affected and how severely
3. IMMEDIATE ACTIONS: step-by-step remediation (Oracle ACLI commands where applicable)
4. ORACLE SBC CONFIG FIX: show the exact ACLI config block that needs to change
5. PREVENTION: monitoring and config changes to prevent recurrence

Be concise, technical, and reference actual IMS protocol details (SIP, Diameter Cx, Rx, H.248)."""


STATE = DemoState()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="IMS Digital Twin Dashboard v2")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


# ── Core API ──────────────────────────────────────────────────────────────────

@app.get("/api/scenarios")
async def get_scenarios():
    return {"scenarios": list_scenarios()}


@app.get("/api/state")
async def get_state():
    summary = STATE.twin.summary()
    return {
        "phase":        STATE.phase,
        "scenario_key": STATE.scenario_key,
        "incident_id":  STATE.twin.incident_id,
        "twin":         summary,
        "logs":         STATE.logs,
        "alarms":       STATE.twin.all_alarms(),
        "sip_trace":    STATE.sip_trace,
        "generated_config": STATE.generated_config,
        "remediation_steps": STATE.remediation_steps,
    }


@app.post("/api/inject/{scenario_key}")
async def inject_scenario(scenario_key: str):
    if scenario_key not in SCENARIOS:
        raise HTTPException(404, f"Unknown scenario: {scenario_key}")
    STATE.inject(scenario_key)
    return {"ok": True, "incident_id": STATE.twin.incident_id,
            "scenario": scenario_key, "log_count": len(STATE.logs),
            "alarm_count": len(STATE.twin.all_alarms())}


@app.post("/api/generate_config")
async def generate_config():
    if STATE.phase not in ("injected", "fixing"):
        raise HTTPException(400, "No active fault scenario")
    cfg = STATE.generate_config()
    return {"ok": True, "config": cfg, "steps": STATE.remediation_steps, "phase": STATE.phase}


@app.post("/api/apply_fix")
async def apply_fix():
    STATE.apply_fix()
    return {"ok": True, "phase": STATE.phase}


@app.post("/api/reset")
async def reset_state():
    STATE.reset()
    return {"ok": True, "phase": "idle"}


# ── Node detail API ───────────────────────────────────────────────────────────

@app.get("/api/node/{node_id}")
async def get_node_detail(node_id: str):
    node = STATE.twin.get_node(node_id)
    if not node and node_id != "ue":
        raise HTTPException(404, f"Node {node_id} not found")
    runtime = copy.deepcopy(NODE_RUNTIME.get(node_id, {}))
    # Overlay live KPIs from twin
    if node:
        runtime["live_cpu_pct"]      = node.cpu_util_pct
        runtime["live_mem_pct"]      = node.mem_util_pct
        runtime["live_sessions"]     = node.active_sessions
        runtime["live_status"]       = node.status.value
        runtime["live_alarms"]       = node.alarms
        runtime["live_config"]       = node.config
    return {
        "node_id":     node_id,
        "config_type": NODE_CONFIG_TYPE.get(node_id, "Config"),
        "config_text": NODE_CONFIG_TEXT.get(node_id, "# No config available"),
        "runtime":     runtime,
        "element_type": node.element_type.value if node else "UE",
    }


# ── User simulation API ───────────────────────────────────────────────────────

@app.post("/api/sim/register/{user_id}")
async def sim_register(user_id: str):
    if user_id not in USERS:
        raise HTTPException(404, f"Unknown user: {user_id}")
    result = simulate_register(user_id, STATE.phase, STATE.scenario_key)
    STATE.add_sim_logs(result.log_lines, result.sip_trace)
    STATE.last_ai_context = (
        STATE._build_ai_context() + f"\n\nLATEST USER ACTION:\n{result.ai_context}"
    )
    return _sim_response(result)


@app.post("/api/sim/call/{caller}/{callee}")
async def sim_call(caller: str, callee: str):
    for u in (caller, callee):
        if u not in USERS:
            raise HTTPException(404, f"Unknown user: {u}")
    result = simulate_call(caller, callee, STATE.phase, STATE.scenario_key)
    STATE.add_sim_logs(result.log_lines, result.sip_trace)
    STATE.last_ai_context = (
        STATE._build_ai_context() + f"\n\nLATEST USER ACTION:\n{result.ai_context}"
    )
    return _sim_response(result)


@app.post("/api/sim/message/{sender}/{recipient}")
async def sim_message(sender: str, recipient: str):
    result = simulate_message(sender, recipient, STATE.phase, STATE.scenario_key)
    STATE.add_sim_logs(result.log_lines, result.sip_trace)
    return _sim_response(result)


@app.post("/api/sim/flood/{user_id}")
async def sim_flood(user_id: str, count: int = 100):
    result = simulate_flood(user_id, count, STATE.phase, STATE.scenario_key)
    STATE.add_sim_logs(result.log_lines, result.sip_trace)
    STATE.last_ai_context = (
        STATE._build_ai_context() + f"\n\nLATEST USER ACTION:\n{result.ai_context}"
    )
    return _sim_response(result)


@app.post("/api/sim/deregister/{user_id}")
async def sim_deregister(user_id: str):
    result = simulate_deregister(user_id, STATE.phase, STATE.scenario_key)
    STATE.add_sim_logs(result.log_lines, result.sip_trace)
    return _sim_response(result)


def _sim_response(r) -> dict:
    return {
        "action":      r.action,
        "user":        r.user,
        "target":      r.target,
        "success":     r.success,
        "response":    r.response,
        "duration_ms": r.duration_ms,
        "ai_context":  r.ai_context,
    }


# ── AI analysis — SSE streaming via Gemma4:e4b ────────────────────────────────

@app.get("/api/ai/health")
async def ai_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            available = OLLAMA_MODEL in models
            return {"ok": available, "model": OLLAMA_MODEL, "all_models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/ai/analyze")
async def ai_analyze():
    context = STATE.last_ai_context or STATE._build_ai_context()
    if STATE.phase == "idle":
        async def no_fault():
            msg = "No active fault scenario. Inject a fault scenario first, then click Analyze."
            yield f"data: {json.dumps({'token': msg})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(no_fault(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def stream_gemma():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_URL}/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": context, "stream": True,
                          "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1024}},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if data.get("done", False):
                                yield f"data: {json.dumps({'done': True})}\n\n"
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield f"data: {json.dumps({'token': '⚠ Ollama not reachable. Start with: ollama serve'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'⚠ AI error: {e}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        stream_gemma(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  IMS Digital Twin Dashboard v2")
    print("  Open: http://localhost:8000\n")
    uvicorn.run("ims_digital_twin.web_server:app",
                host="0.0.0.0", port=8000, reload=False, log_level="warning")
