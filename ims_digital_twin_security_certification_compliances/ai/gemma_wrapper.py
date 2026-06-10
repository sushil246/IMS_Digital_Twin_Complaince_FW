"""
Google Local ADK wrapper for Gemma 4:e4b with native Thinking Mode support.

Thinking Mode:
  - System prompt prefixed with <|think|> token to enable Gemma's chain-of-thought
  - Response parsing strips <|channel>thought\\n...\\n<channel|> blocks
  - Clean remediation text is returned to caller
"""
from __future__ import annotations
import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# ── Thinking-mode token and block pattern ─────────────────────────────────────
_THINK_PREFIX = "<|think|>\n"
_THOUGHT_BLOCK_RE = re.compile(
    r"<\|channel\>thought\n.*?<channel\|>",
    re.DOTALL | re.IGNORECASE,
)
# Alternative patterns Gemma may emit
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

GEMMA_DEFAULTS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "max_tokens": 4096,
}


# ── Response container ────────────────────────────────────────────────────────

@dataclass
class GemmaResponse:
    """Parsed Gemma 4 response with thinking block separated from final answer."""
    raw_text: str
    thinking_block: str = ""
    final_answer: str = ""
    control_id: str = ""
    framework: str = ""
    kamailio_config: str = ""
    remediation_steps: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.final_answer and not self.thinking_block:
            self.thinking_block, self.final_answer = _parse_thinking_response(self.raw_text)
            if not self.final_answer:
                self.final_answer = self.raw_text


def _parse_thinking_response(text: str) -> tuple[str, str]:
    """Extract thinking block and final answer from Gemma 4 response."""
    thinking = ""
    # Pattern 1: <|channel>thought\n...<channel|>
    m = _THOUGHT_BLOCK_RE.search(text)
    if m:
        thinking = m.group(0)
        clean = _THOUGHT_BLOCK_RE.sub("", text).strip()
        return thinking, clean
    # Pattern 2: <think>...</think>
    m2 = _THINK_TAG_RE.search(text)
    if m2:
        thinking = m2.group(0)
        clean = _THINK_TAG_RE.sub("", text).strip()
        return thinking, clean
    return "", text


def _extract_kamailio_cfg(text: str) -> str:
    """Extract Kamailio configuration blocks from remediation text."""
    patterns = [
        re.compile(r"```(?:kamailio|cfg|conf|text)?\n(.*?)```", re.DOTALL),
        re.compile(r"(?:kamailio\.cfg|kamcmd|loadmodule|modparam|route\[).*?(?:\n\n|\Z)", re.DOTALL),
    ]
    blocks = []
    for pat in patterns:
        for m in pat.finditer(text):
            block = m.group(1) if m.lastindex else m.group(0)
            if len(block.strip()) > 20:
                blocks.append(block.strip())
    return "\n\n".join(blocks) if blocks else ""


def _extract_remediation_steps(text: str) -> List[str]:
    """Extract numbered remediation steps from AI response."""
    steps = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if re.match(r"^(\d+\.|\*|-)\s+.{10,}", line):
            clean = re.sub(r"^(\d+\.|\*|-)\s+", "", line).strip()
            if clean:
                steps.append(clean)
    return steps[:10] if steps else []


# ── System prompt templates ───────────────────────────────────────────────────

_BASE_SYSTEM = """\
You are an expert IMS (IP Multimedia Subsystem) network security engineer and AI compliance specialist.
You combine deep knowledge of:
- Kamailio SIP proxy configuration (kamailio.cfg, modules: pipelimit, htable, pike, sanity, textopsx, dispatcher, xlog)
- Oracle Session Border Controller (SBC) ACLI configuration
- Regulatory compliance frameworks: UK TSA, EU AI Act, ISO 42001, NIST AI RMF, MIT AI Risk, OECD AI Principles
- AI/ML system governance and audit requirements for critical telecom infrastructure

When generating Kamailio configuration fixes, always use:
- Correct module loading syntax: loadmodule "module.so"
- Correct modparam syntax and realistic values
- Route blocks in kamailio.cfg format
- Inline comments explaining the compliance requirement each block satisfies

Structure your response as:
1. COMPLIANCE ANALYSIS: Which controls are violated and why
2. ROOT CAUSE: Technical explanation referencing specific log evidence
3. KAMAILIO FIX: Complete kamailio.cfg snippet(s) to remediate
4. VERIFICATION: How to confirm the fix resolves the compliance finding
5. COMPLIANCE STATUS: Expected status after applying the fix
"""

_THINKING_SYSTEM = _THINK_PREFIX + _BASE_SYSTEM


# ── Main wrapper class ────────────────────────────────────────────────────────

class GemmaComplianceAdvisor:
    """
    Google ADK LiteLlm wrapper for Gemma 4:e4b with thinking mode enabled.
    Provides compliance-aware remediation generation for IMS/Kamailio findings.
    """

    APP_NAME = "ims_compliance_advisor"
    USER_ID  = "compliance_auditor"

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "ollama_chat/gemma4:e4b",
        temperature: float = GEMMA_DEFAULTS["temperature"],
        top_p: float = GEMMA_DEFAULTS["top_p"],
        top_k: int = GEMMA_DEFAULTS["top_k"],
        max_tokens: int = GEMMA_DEFAULTS["max_tokens"],
        thinking_mode: bool = True,
    ):
        self.ollama_url = ollama_url
        self.model_str = model
        self.thinking_mode = thinking_mode
        self._llm = LiteLlm(
            model=model,
            api_base=ollama_url,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            extra_body={"options": {"top_k": top_k}},
        )

    def _build_remediation_agent(self) -> LlmAgent:
        system = _THINKING_SYSTEM if self.thinking_mode else _BASE_SYSTEM
        return LlmAgent(
            name="compliance_remediation_agent",
            model=self._llm,
            instruction=system,
            description="Generates regulatory-compliant Kamailio/SBC configuration fixes.",
        )

    def _build_audit_agent(self) -> LlmAgent:
        system = (_THINK_PREFIX if self.thinking_mode else "") + """\
You are a compliance auditor specializing in telecom AI systems.
Analyze the provided compliance findings and produce:
1. EXECUTIVE SUMMARY: Overall compliance posture (1-2 sentences)
2. CRITICAL GAPS: Top 3 highest-risk non-compliant controls with business impact
3. REMEDIATION PRIORITY: Ordered action plan (quick wins first)
4. COMPLIANCE SCORE: Estimated % compliant per framework after proposed fixes
5. REGULATORY RISK: Likelihood of regulatory action if gaps persist (LOW/MEDIUM/HIGH/CRITICAL)

Be concise, precise, and reference specific control IDs (e.g., TSA-SIG-001, EUAI-HRC-002).
"""
        return LlmAgent(
            name="compliance_audit_agent",
            model=self._llm,
            instruction=system,
            description="Produces executive compliance audit reports from findings.",
        )

    async def _run_agent_async(
        self,
        agent: LlmAgent,
        prompt: str,
        app_suffix: str = "",
    ) -> str:
        sessions = InMemorySessionService()
        # The root agent classes are loaded from google.adk.agents, so the ADK
        # runner expects the app_name to align with that package root.
        app_name = "agents"
        runner = Runner(agent=agent, app_name=app_name, session_service=sessions)
        sid = str(uuid.uuid4())
        await sessions.create_session(
            app_name=app_name, user_id=self.USER_ID, session_id=sid
        )
        message = genai_types.Content(
            role="user", parts=[genai_types.Part(text=prompt)]
        )
        reply_parts = []
        async for event in runner.run_async(
            user_id=self.USER_ID, session_id=sid, new_message=message
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        reply_parts.append(part.text)
        return "\n".join(reply_parts)

    def _run_agent_sync(self, agent: LlmAgent, prompt: str, app_suffix: str = "") -> str:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._run_agent_async(agent, prompt, app_suffix)
                    )
                    return future.result(timeout=120)
            else:
                return loop.run_until_complete(
                    self._run_agent_async(agent, prompt, app_suffix)
                )
        except Exception:
            return asyncio.run(self._run_agent_async(agent, prompt, app_suffix))

    async def remediate_finding_async(
        self,
        finding_data: Dict,
        logs: List[str],
        sip_trace: str = "",
        kamailio_cfg_issue: str = "",
    ) -> GemmaResponse:
        """Generate Kamailio remediation for a single compliance finding."""
        logs_sample = "\n".join(logs[-15:]) if logs else "No logs available"
        prompt = f"""\
COMPLIANCE FINDING REQUIRING REMEDIATION:
==========================================
Control ID:      {finding_data.get('control_id', 'N/A')}
Framework:       {finding_data.get('framework', 'N/A')}
Control Name:    {finding_data.get('control_name', 'N/A')}
Status:          {finding_data.get('status', 'NON_COMPLIANT')}
Severity:        {finding_data.get('severity', 'HIGH')}
Telecom Vector:  {finding_data.get('telecom_vector', 'N/A')}
Evidence Hint:   {finding_data.get('evidence_hint', 'N/A')}
Kamailio Module: {finding_data.get('kamailio_module', 'N/A')}

OBSERVED LOGS (last 15 lines):
{logs_sample}

SIP TRACE / PROTOCOL EVIDENCE:
{sip_trace or "No SIP trace available"}

KAMAILIO CONFIG ISSUE:
{kamailio_cfg_issue or "See evidence hint above"}

TASK: Generate a complete, production-ready Kamailio configuration fix that:
1. Remediates the compliance violation identified above
2. Uses the specified Kamailio module(s)
3. Includes all required modparam() and loadmodule() statements
4. Adds inline comments referencing the specific compliance control ID
5. Provides verification steps to confirm the fix is working
"""
        agent = self._build_remediation_agent()
        raw = await self._run_agent_async(agent, prompt, "remediate")
        thinking, final = _parse_thinking_response(raw)
        return GemmaResponse(
            raw_text=raw,
            thinking_block=thinking,
            final_answer=final,
            control_id=finding_data.get("control_id", ""),
            framework=finding_data.get("framework", ""),
            kamailio_config=_extract_kamailio_cfg(final),
            remediation_steps=_extract_remediation_steps(final),
        )

    def remediate_finding(
        self,
        finding_data: Dict,
        logs: List[str],
        sip_trace: str = "",
        kamailio_cfg_issue: str = "",
    ) -> GemmaResponse:
        """Synchronous wrapper for remediate_finding_async."""
        return asyncio.run(
            self.remediate_finding_async(finding_data, logs, sip_trace, kamailio_cfg_issue)
        )

    async def generate_audit_summary_async(
        self,
        audit_report_dict: Dict,
        logs: List[str],
    ) -> GemmaResponse:
        """Generate executive compliance audit summary from a full report."""
        nc_findings = [
            f for f in audit_report_dict.get("findings", [])
            if f.get("status") == "NON_COMPLIANT"
        ]
        critical = [f for f in nc_findings if f.get("severity") == "CRITICAL"]
        logs_sample = "\n".join(logs[-10:]) if logs else ""

        prompt = f"""\
COMPLIANCE AUDIT REPORT SUMMARY REQUEST:
=========================================
Audit ID:        {audit_report_dict.get('audit_id', 'N/A')}
Timestamp:       {audit_report_dict.get('timestamp', 'N/A')}
Incident:        {audit_report_dict.get('incident_id', 'None')}
Fault Scenario:  {audit_report_dict.get('injected_fault', 'None')}
Overall Score:   {audit_report_dict.get('overall_score', 0)}%
Frameworks:      {', '.join(audit_report_dict.get('frameworks_evaluated', []))}

FRAMEWORK SCORES:
{json.dumps(audit_report_dict.get('framework_scores', {}), indent=2)}

CRITICAL NON-COMPLIANT FINDINGS ({len(critical)}):
{json.dumps(critical[:5], indent=2)}

TOTAL NON-COMPLIANT FINDINGS: {len(nc_findings)} of {len(audit_report_dict.get('findings', []))}

RECENT LOG CONTEXT:
{logs_sample}

Generate a concise executive compliance audit summary with prioritized remediation roadmap.
"""
        agent = self._build_audit_agent()
        raw = await self._run_agent_async(agent, prompt, "audit")
        thinking, final = _parse_thinking_response(raw)
        return GemmaResponse(
            raw_text=raw,
            thinking_block=thinking,
            final_answer=final,
            remediation_steps=_extract_remediation_steps(final),
        )

    async def stream_remediation(
        self,
        finding_data: Dict,
        logs: List[str],
        sip_trace: str = "",
        kamailio_cfg_issue: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream remediation tokens directly from Ollama (bypasses ADK for streaming)."""
        import httpx
        logs_sample = "\n".join(logs[-15:]) if logs else ""
        system = _THINKING_SYSTEM if self.thinking_mode else _BASE_SYSTEM
        prompt = (
            f"{system}\n\n"
            f"FINDING: {finding_data.get('control_id')} | {finding_data.get('control_name')}\n"
            f"FRAMEWORK: {finding_data.get('framework')}\n"
            f"TELECOM VECTOR: {finding_data.get('telecom_vector')}\n"
            f"KAMAILIO MODULE: {finding_data.get('kamailio_module', 'N/A')}\n\n"
            f"LOGS:\n{logs_sample}\n\n"
            f"SIP TRACE:\n{sip_trace or 'N/A'}\n\n"
            f"CFG ISSUE:\n{kamailio_cfg_issue or 'N/A'}\n\n"
            f"Generate complete Kamailio fix with compliance annotations:"
        )
        ollama_model = self.model_str.replace("ollama_chat/", "").replace("ollama/", "")
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": GEMMA_DEFAULTS["temperature"],
                        "top_p": GEMMA_DEFAULTS["top_p"],
                        "top_k": GEMMA_DEFAULTS["top_k"],
                        "num_predict": 2048,
                    },
                },
            ) as resp:
                buffer = ""
                in_thinking = False
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if not token:
                            if data.get("done"):
                                break
                            continue
                        buffer += token
                        # Suppress thinking block tokens
                        if "<|channel>" in buffer or "<think>" in buffer:
                            in_thinking = True
                        if in_thinking:
                            if "<channel|>" in buffer or "</think>" in buffer:
                                in_thinking = False
                                buffer = re.sub(_THOUGHT_BLOCK_RE, "", buffer)
                                buffer = re.sub(_THINK_TAG_RE, "", buffer)
                                yield buffer.strip()
                                buffer = ""
                            continue
                        if not in_thinking and len(buffer) > 10:
                            yield buffer
                            buffer = ""
                        if data.get("done"):
                            if buffer:
                                yield buffer
                            break
                    except json.JSONDecodeError:
                        continue
