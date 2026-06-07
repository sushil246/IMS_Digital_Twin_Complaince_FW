# IMS Digital Twin — RCA Workflow Sequence Diagram

```mermaid
sequenceDiagram
    autonumber

    actor NOC as NOC Engineer
    participant CLI as main.py (CLI)
    participant Twin as NetworkStateTwin<br/>(Digital Twin)
    participant Fault as FaultScenarios<br/>(Injector)
    participant Logs as LogStore
    participant Sessions as InMemorySessionService<br/>(ADK)
    participant Runner as ADK Runner
    participant LLM as LiteLLM / Ollama<br/>(gemma4)

    box rgb(230,245,255) Log Analysis Phase
        participant LogAgent as log_analyzer<br/>(LlmAgent)
        participant LogTools as LogTools<br/>(get_sbc_logs · grep_logs<br/>count_sip_responses · etc.)
    end

    box rgb(230,255,230) Root Cause Analysis Phase
        participant RCAAgent as rca_agent<br/>(LlmAgent)
        participant TwinTools as TwinTools<br/>(get_network_summary<br/>get_active_alarms · etc.)
    end

    box rgb(255,245,230) Config Generation Phase
        participant CfgAgent as config_generator<br/>(LlmAgent)
        participant CfgTools as ConfigTools<br/>(generate_full_remediation_config<br/>update_twin_config · etc.)
        participant FS as output/<br/>(ACLI Files)
    end

    %% ── Bootstrap ──────────────────────────────────────────────────────────
    NOC->>CLI: python -m ims_digital_twin.main<br/>--scenario reg_storm --model ollama_chat/gemma4:e4b

    CLI->>Twin: NetworkStateTwin()
    Twin-->>CLI: twin (7 IMS nodes, links, KPIs)

    CLI->>TwinTools: register_twin(twin)

    %% ── Fault Injection ────────────────────────────────────────────────────
    CLI->>Fault: inject(twin, "reg_storm")
    activate Fault
    Fault->>Twin: set incident_id, injected_fault, snapshot_ts
    Fault->>Twin: mutate SBC KPIs (CPU=94.3%, sessions=4988)
    Fault->>Twin: add_node_alarm("sbc01", "CRITICAL: CPU 94%")
    Fault->>Twin: add_node_alarm("sbc01", "MAJOR: REGISTER rate 1820/s")
    Fault->>Twin: update_node_config("sbc01", dos_protection, rate=1820)
    Fault-->>CLI: (twin, log_lines[18])
    deactivate Fault

    CLI->>Logs: store_logs(log_lines)
    Note over CLI,Logs: 18 simulated Oracle SBC syslog<br/>lines stored in module-level store

    %% ── Agent Construction ─────────────────────────────────────────────────
    CLI->>Sessions: InMemorySessionService()
    CLI->>Runner: build log_analyzer, rca_agent, config_generator<br/>each backed by LiteLlm(model, ollama_url)

    %% ═══════════════════════════════════════════════════════════════════════
    %% PHASE 1 — Log Analyzer
    %% ═══════════════════════════════════════════════════════════════════════
    rect rgb(230,245,255)
        Note over CLI,LogTools: ── Phase 1: Log Analysis ──────────────────────────────
        CLI->>Runner: _run_agent(log_analyzer, "Analyse SBC logs...")
        activate Runner

        Runner->>Sessions: create_session(log_session_id)
        Runner->>LogAgent: run_async(prompt)
        activate LogAgent

        LogAgent->>LLM: chat(system=LOG_ANALYZER_PROMPT, user=prompt)
        LLM-->>LogAgent: tool_call → get_sbc_logs()

        LogAgent->>LogTools: get_sbc_logs()
        LogTools-->>LogAgent: {log_count:18, log_lines:[...]}

        LogAgent->>LLM: tool_result(log_lines)
        LLM-->>LogAgent: tool_call → extract_alarm_lines()
        LogAgent->>LogTools: extract_alarm_lines()
        LogTools-->>LogAgent: {CRITICAL:[...], MAJOR:[...], WARNING:[...]}

        LogAgent->>LLM: tool_result(alarm_buckets)
        LLM-->>LogAgent: tool_call → count_sip_responses()
        LogAgent->>LogTools: count_sip_responses()
        LogTools-->>LogAgent: {response_counts:{503:2}, error_rate_pct:100}

        LogAgent->>LLM: tool_result(sip_counts)
        LLM-->>LogAgent: tool_call → analyse_log_timeline()
        LogAgent->>LogTools: analyse_log_timeline()
        LogTools-->>LogAgent: {ordered_events:[{ts,event}...]}

        LogAgent->>LLM: tool_result(timeline)
        LLM-->>LogAgent: tool_call → grep_logs("rate-limit|503|overload")
        LogAgent->>LogTools: grep_logs(pattern)
        LogTools-->>LogAgent: {match_count:4, matches:[...]}

        LogAgent->>LLM: tool_result(grep_matches)
        LLM-->>LogAgent: final_response(OBSERVED_SYMPTOMS +<br/>KEY_LOG_LINES + PROBABLE_CAUSE + CONFIDENCE)

        deactivate LogAgent
        Runner-->>CLI: log_analysis_text
        deactivate Runner
        CLI->>NOC: print(log_analysis)
    end

    %% ═══════════════════════════════════════════════════════════════════════
    %% PHASE 2 — RCA Agent
    %% ═══════════════════════════════════════════════════════════════════════
    rect rgb(230,255,230)
        Note over CLI,TwinTools: ── Phase 2: Root Cause Analysis ──────────────────────
        CLI->>Runner: _run_agent(rca_agent, "Perform RCA...")
        activate Runner

        Runner->>Sessions: create_session(rca_session_id)
        Runner->>RCAAgent: run_async(prompt)
        activate RCAAgent

        RCAAgent->>LLM: chat(system=RCA_PROMPT, user=prompt)
        LLM-->>RCAAgent: tool_call → get_network_summary()

        RCAAgent->>TwinTools: get_network_summary()
        TwinTools->>Twin: summary()
        Twin-->>TwinTools: {incident_id, nodes[7], links, total_alarms}
        TwinTools-->>RCAAgent: network_summary_json

        RCAAgent->>LLM: tool_result(network_summary)
        LLM-->>RCAAgent: tool_call → get_active_alarms()
        RCAAgent->>TwinTools: get_active_alarms()
        TwinTools->>Twin: all_alarms()
        Twin-->>TwinTools: ["CRITICAL: CPU 94%", "MAJOR: REGISTER rate 1820/s", ...]
        TwinTools-->>RCAAgent: {total:3, alarms:[...]}

        RCAAgent->>LLM: tool_result(alarms)
        LLM-->>RCAAgent: tool_call → get_sbc_config()
        RCAAgent->>TwinTools: get_sbc_config()
        TwinTools->>Twin: get_sbc() → sbc01 node
        Twin-->>TwinTools: {config:{dos_protection:{current_register_rate:1820,...},...}}
        TwinTools-->>RCAAgent: sbc_config_json

        RCAAgent->>LLM: tool_result(sbc_config)
        LLM-->>RCAAgent: tool_call → get_link_status()
        RCAAgent->>TwinTools: get_link_status()
        TwinTools->>Twin: links[]
        Twin-->>TwinTools: [{type,src,dst,protocol,status,latency_ms,loss_pct}...]
        TwinTools-->>RCAAgent: link_status_json

        RCAAgent->>LLM: tool_result(link_status)
        LLM-->>RCAAgent: final_response(INCIDENT_ID + ROOT_CAUSE +<br/>CONTRIBUTING_FACTORS + AFFECTED_SERVICES +<br/>BLAST_RADIUS + RECOMMENDED_FIX + PREVENTION)

        deactivate RCAAgent
        Runner-->>CLI: rca_result_text
        deactivate Runner
        CLI->>NOC: print(rca_result)
    end

    %% ═══════════════════════════════════════════════════════════════════════
    %% PHASE 3 — Config Generator Agent
    %% ═══════════════════════════════════════════════════════════════════════
    rect rgb(255,245,230)
        Note over CLI,FS: ── Phase 3: ACLI Config Generation ────────────────────
        CLI->>Runner: _run_agent(config_generator, "Generate remediation config...")
        activate Runner

        Runner->>Sessions: create_session(cfg_session_id)
        Runner->>CfgAgent: run_async(prompt)
        activate CfgAgent

        CfgAgent->>LLM: chat(system=CONFIG_GEN_PROMPT, user=prompt)
        LLM-->>CfgAgent: tool_call → get_network_summary()
        CfgAgent->>TwinTools: get_network_summary()
        TwinTools-->>CfgAgent: {incident_id:"INC-XXXXXXXX", injected_fault:"reg_storm"}

        CfgAgent->>LLM: tool_result(network_summary)
        LLM-->>CfgAgent: tool_call → generate_full_remediation_config(incident_id, "reg_storm")

        CfgAgent->>CfgTools: generate_full_remediation_config(incident_id, "reg_storm")
        activate CfgTools
        CfgTools->>CfgTools: build DoS protection ACLI block
        CfgTools->>CfgTools: build session constraints ACLI block
        CfgTools->>FS: write remediation_INC-XXXXXXXX_reg_storm.acli
        CfgTools-->>CfgAgent: {acli_config:"...", steps:[...], filename:"..."}
        deactivate CfgTools

        CfgAgent->>LLM: tool_result(acli_config)
        LLM-->>CfgAgent: tool_call → update_twin_config("sbc01", "dos_protection.max_register_rate", "200")
        CfgAgent->>TwinTools: update_twin_config(node_id, config_path, new_value)
        TwinTools->>Twin: update_node_config("sbc01", [...], 200)
        Twin-->>TwinTools: ok
        TwinTools-->>CfgAgent: {success:true, applied_value:200}

        CfgAgent->>LLM: tool_result(config_applied)
        LLM-->>CfgAgent: final_response(ACLI config listing +<br/>remediation steps + prerequisites +<br/>explanation of each fix)

        deactivate CfgAgent
        Runner-->>CLI: cfg_result_text
        deactivate Runner
        CLI->>NOC: print(cfg_result)
    end

    %% ── Completion ──────────────────────────────────────────────────────────
    CLI->>NOC: "Digital Twin Demo Complete"<br/>Incident: INC-XXXXXXXX<br/>Output configs saved to ims_digital_twin/output/
```

## Participants

| Participant | Role |
|---|---|
| **NOC Engineer** | Operator who triggers the demo via CLI |
| **main.py** | Entry point — parses args, wires twin + agents, drives pipeline |
| **NetworkStateTwin** | Mutable in-memory model of the 7-node IMS topology (SBC, P-CSCF, I-CSCF, S-CSCF, HSS, PCRF, MGW) |
| **FaultScenarios** | Injects one of 6 named fault scenarios into twin state and generates realistic SBC log lines |
| **LogStore** | Module-level list holding the simulated syslog lines for the session |
| **InMemorySessionService** | Google ADK session manager — one independent session per agent |
| **ADK Runner** | Google ADK runner — streams events from an LlmAgent until `is_final_response()` |
| **LiteLLM / Ollama** | LLM backend bridge — routes to local Ollama (default: `gemma4:e4b`) |
| **log_analyzer** | ADK LlmAgent that reads raw logs and produces a structured symptom report |
| **LogTools** | Functions exposed as ADK tools: `get_sbc_logs`, `grep_logs`, `count_sip_responses`, `extract_alarm_lines`, `analyse_log_timeline`, `extract_sip_call_ids` |
| **rca_agent** | ADK LlmAgent that queries the digital twin and produces a formal RCA report |
| **TwinTools** | Functions exposed as ADK tools: `get_network_summary`, `get_active_alarms`, `get_sbc_config`, `get_link_status`, `get_node_detail`, `update_twin_config` |
| **config_generator** | ADK LlmAgent that generates Oracle SBC ACLI remediation configuration |
| **ConfigTools** | Functions exposed as ADK tools: `generate_full_remediation_config`, `generate_dos_protection_config`, `generate_tls_profile_config`, etc. |
| **output/** | File system directory where generated `.acli` config files are persisted |

## Fault Scenarios

| Key | Name | Trigger |
|---|---|---|
| `reg_storm` | SIP Registration Storm | REGISTER flood → CPU spike, cache exhaustion, 503s |
| `tls_cert_expiry` | TLS Certificate Expiry | Expired cert → SIP/TLS handshake failures |
| `rtp_timeout` | RTP Media Timeout | No RTP packets → one-way audio, call clears |
| `codec_mismatch` | SIP Codec / SDP Mismatch | G.729 stripped by policy → 488 Not Acceptable |
| `pcscf_down` | Upstream P-CSCF Unreachable | Health-check failure → all INVITEs return 503 |
| `srtp_dtls_fail` | SRTP/DTLS Negotiation Failure | DTLS cipher mismatch → calls connect with no media |
