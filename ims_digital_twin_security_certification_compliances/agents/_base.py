"""
Base utilities shared by all certification agents.
Provides model builder, tool set, and common ADK runner helpers.
"""
from __future__ import annotations
import asyncio
import json
import uuid
from typing import Any, Callable, List, Optional

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from ims_digital_twin_security_certification_compliances.ai.gemma_wrapper import (
    GEMMA_DEFAULTS, _THINK_PREFIX,
)

# ── Shared tool imports ───────────────────────────────────────────────────────
# These are ADK tool functions available to all certification agents.
# Import from existing tool modules to maximise code reuse.
try:
    from ims_digital_twin.tools.twin_tools import (
        get_network_summary, get_active_alarms, get_sbc_config,
        get_link_status, get_node_detail,
    )
    from ims_digital_twin.tools.log_tools import (
        get_sbc_logs, grep_logs, count_sip_responses,
        extract_alarm_lines, analyse_log_timeline,
    )
    _TWIN_TOOLS_AVAILABLE = True
except ImportError:
    _TWIN_TOOLS_AVAILABLE = False


def build_model(
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> LiteLlm:
    return LiteLlm(
        model=model,
        api_base=ollama_url,
        temperature=GEMMA_DEFAULTS["temperature"],
        top_p=GEMMA_DEFAULTS["top_p"],
        max_tokens=GEMMA_DEFAULTS["max_tokens"],
        extra_body={"options": {"top_k": GEMMA_DEFAULTS["top_k"]}},
    )


def twin_tools() -> list:
    """Return the list of IMS twin query tools if available."""
    if not _TWIN_TOOLS_AVAILABLE:
        return []
    return [
        get_network_summary, get_active_alarms, get_sbc_config,
        get_link_status, get_node_detail,
    ]


def log_tools() -> list:
    """Return the list of SBC log query tools if available."""
    if not _TWIN_TOOLS_AVAILABLE:
        return []
    return [
        get_sbc_logs, grep_logs, count_sip_responses,
        extract_alarm_lines, analyse_log_timeline,
    ]


def all_tools() -> list:
    return twin_tools() + log_tools()


async def run_agent_async(
    agent: LlmAgent,
    prompt: str,
    app_name: str = "agents",
    user_id: str = "compliance_auditor",
) -> str:
    # The root agent classes are loaded from google.adk.agents, so the ADK
    # runner expects the app_name to align with that package root.
    sessions = InMemorySessionService()
    runner = Runner(agent=agent, app_name=app_name, session_service=sessions)
    sid = str(uuid.uuid4())
    await sessions.create_session(app_name=app_name, user_id=user_id, session_id=sid)
    message = genai_types.Content(
        role="user", parts=[genai_types.Part(text=prompt)]
    )
    parts = []
    async for event in runner.run_async(user_id=user_id, session_id=sid, new_message=message):
        if event.is_final_response() and event.content:
            for p in event.content.parts:
                if getattr(p, "text", None):
                    parts.append(p.text)
    return "\n".join(parts)


def run_agent_sync(agent: LlmAgent, prompt: str, app_name: str) -> str:
    return asyncio.run(run_agent_async(agent, prompt, app_name))
