"""
Root orchestrator — drives the full digital twin RCA workflow:
1. Inject fault into twin
2. Collect logs
3. Call log-analyzer sub-agent
4. Call RCA sub-agent
5. Call config-generator sub-agent
6. Print final report
"""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from ims_digital_twin.digital_twin.network_state import NetworkStateTwin
from ims_digital_twin.scenarios.fault_scenarios import inject, list_scenarios
from ims_digital_twin.tools import twin_tools, log_tools, config_tools

APP_NAME  = "ims_digital_twin"
USER_ID   = "noc_engineer"


def _build_model(ollama_url: str, model: str) -> LiteLlm:
    return LiteLlm(
        model=model,
        api_base=ollama_url,
        temperature=0.2,
        top_p=0.9,
        max_tokens=4096,
        extra_body={"options": {"top_k": 40}},
    )


# ── Log Analyzer Agent ────────────────────────────────────────────────────────

LOG_ANALYZER_PROMPT = """\
You are an expert IMS/VoIP network log analyst specializing in Oracle Session Border Controllers.

Your task:
1. Call get_sbc_logs() to retrieve all collected SBC log lines
2. Call extract_alarm_lines() to bucket alarms by severity
3. Call count_sip_responses() to see SIP error code distribution
4. Call analyse_log_timeline() to understand the event sequence
5. Call grep_logs() with relevant patterns to find specific error signatures

Based on your analysis, produce a structured report with:
- OBSERVED_SYMPTOMS: bullet list of what the logs show
- KEY_LOG_LINES: the 3-5 most significant log entries
- PROBABLE_CAUSE: your technical assessment of the root cause
- CONFIDENCE: HIGH / MEDIUM / LOW with reasoning

Be precise and technical. Reference specific log line content in your analysis.
"""


def _build_log_analyzer(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="log_analyzer",
        model=model,
        tools=[
            log_tools.get_sbc_logs,
            log_tools.extract_alarm_lines,
            log_tools.count_sip_responses,
            log_tools.grep_logs,
            log_tools.analyse_log_timeline,
            log_tools.extract_sip_call_ids,
        ],
        instruction=LOG_ANALYZER_PROMPT,
        description="Analyses Oracle SBC logs to identify symptoms and probable root cause.",
    )


# ── RCA Agent ─────────────────────────────────────────────────────────────────

RCA_PROMPT = """\
You are a senior IMS network RCA (Root Cause Analysis) specialist.

You have access to the IMS digital twin state and can query individual nodes.

Your task:
1. Call get_network_summary() to see the full twin state
2. Call get_active_alarms() to list all current alarms
3. Call get_sbc_config() to inspect the current Oracle SBC configuration
4. Call get_link_status() to check interface health
5. Examine specific nodes with get_node_detail() as needed

Then produce a formal RCA report with these sections:
- INCIDENT_ID: from the twin
- ROOT_CAUSE: one-sentence technical root cause
- CONTRIBUTING_FACTORS: 2-3 bullet points
- AFFECTED_SERVICES: what services/calls are impacted
- BLAST_RADIUS: scope of impact (users, sessions, regions)
- RECOMMENDED_FIX: specific Oracle SBC configuration changes needed
- PREVENTION: how to prevent this in future

Reference digital twin data (KPIs, config values, alarm text) in your findings.
"""


def _build_rca_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="rca_agent",
        model=model,
        tools=[
            twin_tools.get_network_summary,
            twin_tools.get_active_alarms,
            twin_tools.get_sbc_config,
            twin_tools.get_link_status,
            twin_tools.get_node_detail,
        ],
        instruction=RCA_PROMPT,
        description="Performs root cause analysis using the IMS digital twin state.",
    )


# ── Config Generator Agent ────────────────────────────────────────────────────

CONFIG_GEN_PROMPT = """\
You are an Oracle SBC configuration expert. Based on the incident ID and fault scenario
provided, generate a complete Oracle SBC ACLI remediation configuration.

Your task:
1. Call generate_full_remediation_config(incident_id=..., scenario_key=...) with the
   incident ID and scenario key from the twin summary
2. Present the generated ACLI configuration to the operator
3. List all remediation steps in order
4. Highlight any pre-requisites (e.g. certificate upload before applying TLS config)
5. Explain the key configuration changes and why each fixes the root cause

Always call get_network_summary() first to get the incident_id and injected_fault values.
Then pass those exactly to generate_full_remediation_config().

After generating config, call update_twin_config() to simulate applying a key fix to the twin.
"""


def _build_config_gen_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="config_generator",
        model=model,
        tools=[
            twin_tools.get_network_summary,
            twin_tools.get_sbc_config,
            twin_tools.update_twin_config,
            config_tools.generate_full_remediation_config,
            config_tools.generate_dos_protection_config,
            config_tools.generate_tls_profile_config,
            config_tools.generate_media_manager_config,
            config_tools.generate_media_sec_policy_config,
            config_tools.generate_session_agent_config,
            config_tools.generate_codec_policy_config,
        ],
        instruction=CONFIG_GEN_PROMPT,
        description="Generates Oracle SBC ACLI remediation configuration for detected faults.",
    )


# ── Session runner helper ─────────────────────────────────────────────────────

async def _run_agent(
    agent: LlmAgent,
    prompt: str,
    session_service: InMemorySessionService,
    app_name: str,
) -> str:
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    sid = str(uuid.uuid4())
    await session_service.create_session(
        app_name=app_name, user_id=USER_ID, session_id=sid
    )
    message = genai_types.Content(
        role="user", parts=[genai_types.Part(text=prompt)]
    )
    reply_parts = []
    async for event in runner.run_async(
        user_id=USER_ID, session_id=sid, new_message=message
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    reply_parts.append(part.text)
    return "\n".join(reply_parts)


# ── Main orchestration workflow ───────────────────────────────────────────────

async def run_digital_twin_demo(
    scenario_key: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "ollama_chat/gemma4:e4b",
) -> None:
    os.environ.setdefault("OLLAMA_API_BASE", ollama_url)
    import litellm
    litellm.drop_params = True
    litellm.set_verbose = False

    print("\n" + "=" * 70)
    print("  IMS Network Digital Twin — Root Cause Analysis Demo")
    print("=" * 70)

    # ── 1. Build twin and inject fault ───────────────────────────────────────
    print(f"\n[1/5] Initialising IMS Digital Twin...")
    twin = NetworkStateTwin()
    twin_tools.register_twin(twin)

    print(f"[2/5] Injecting fault scenario: '{scenario_key}'")
    twin, logs = inject(twin, scenario_key)
    log_tools.store_logs(logs)

    print(f"      Incident ID : {twin.incident_id}")
    print(f"      Fault       : {twin.injected_fault}")
    print(f"      Log lines   : {len(logs)}")
    print(f"      Alarms      : {len(twin.all_alarms())}")

    print("\n--- Injected SBC Logs ---")
    for line in logs:
        print(f"  {line}")
    print("--- End Logs ---\n")

    # ── 2. Build agents ──────────────────────────────────────────────────────
    print("[3/5] Building AI agents (Log Analyzer → RCA → Config Generator)...")
    model_obj   = _build_model(ollama_url, model)
    log_agent   = _build_log_analyzer(model_obj)
    rca_agent   = _build_rca_agent(model_obj)
    cfg_agent   = _build_config_gen_agent(model_obj)
    sessions    = InMemorySessionService()

    # ── 3. Log analysis ──────────────────────────────────────────────────────
    print("\n[4/5] Running Log Analyzer Agent...")
    print("-" * 50)
    log_analysis = await _run_agent(
        log_agent,
        "Analyse the SBC logs and produce your structured report.",
        sessions, APP_NAME + "_log",
    )
    print(log_analysis)

    # ── 4. RCA ───────────────────────────────────────────────────────────────
    print("\n[5a/5] Running RCA Agent...")
    print("-" * 50)
    rca_result = await _run_agent(
        rca_agent,
        "Perform root cause analysis using the digital twin state and produce your RCA report.",
        sessions, APP_NAME + "_rca",
    )
    print(rca_result)

    # ── 5. Config generation ─────────────────────────────────────────────────
    print("\n[5b/5] Running Config Generator Agent...")
    print("-" * 50)
    cfg_result = await _run_agent(
        cfg_agent,
        "Generate the Oracle SBC remediation configuration for the detected fault.",
        sessions, APP_NAME + "_cfg",
    )
    print(cfg_result)

    print("\n" + "=" * 70)
    print("  Digital Twin Demo Complete")
    print(f"  Incident: {twin.incident_id}")
    print(f"  Output configs saved to: ims_digital_twin/output/")
    print("=" * 70 + "\n")
