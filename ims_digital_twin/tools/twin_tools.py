"""
ADK-compatible tools for querying and updating the digital twin state.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

# Module-level twin instance — shared across all tool calls in a session
_twin_registry: Dict[str, Any] = {}


def register_twin(twin) -> None:
    _twin_registry["current"] = twin


def get_twin():
    return _twin_registry.get("current")


# ── Twin query tools ──────────────────────────────────────────────────────────

def get_network_summary() -> dict:
    """Return a JSON summary of the current IMS digital twin state including all nodes,
    KPIs, alarms, and link status.

    Returns:
        dict with keys: snapshot_ts, incident_id, injected_fault, nodes, links, total_alarms
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    return twin.summary()


def get_node_detail(node_id: str) -> dict:
    """Return detailed state for a specific IMS network element.

    Args:
        node_id: One of: sbc01, pcscf01, icscf01, scscf01, hss01, pcrf01, mgw01

    Returns:
        dict with full node state including config, KPIs, and alarms
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    node = twin.get_node(node_id)
    if not node:
        return {"error": f"Node {node_id!r} not found"}
    return {
        "node_id": node.node_id,
        "type": node.element_type.value,
        "hostname": node.hostname,
        "ip_address": node.ip_address,
        "status": node.status.value,
        "software_version": node.software_version,
        "cpu_pct": node.cpu_util_pct,
        "mem_pct": node.mem_util_pct,
        "active_sessions": node.active_sessions,
        "alarms": node.alarms,
        "config": node.config,
    }


def get_active_alarms() -> dict:
    """Return all active alarms across the IMS network.

    Returns:
        dict with alarm list and count
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    alarms = twin.all_alarms()
    return {"total": len(alarms), "alarms": alarms}


def get_sbc_config() -> dict:
    """Return the current Oracle SBC configuration from the digital twin.

    Returns:
        dict with full SBC configuration block
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    sbc = twin.get_sbc()
    return {
        "node_id": sbc.node_id,
        "software_version": sbc.software_version,
        "status": sbc.status.value,
        "config": sbc.config,
    }


def get_link_status() -> dict:
    """Return the status of all IMS network interfaces/links.

    Returns:
        dict with list of link states
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    return {
        "links": [
            {
                "type": lnk.interface_type.value,
                "src": lnk.source,
                "dst": lnk.destination,
                "protocol": lnk.protocol,
                "port": lnk.port,
                "status": lnk.status,
                "latency_ms": lnk.latency_ms,
                "loss_pct": lnk.packet_loss_pct,
            }
            for lnk in twin.links
        ]
    }


def update_twin_config(node_id: str, config_path: str, new_value: str) -> dict:
    """Apply a configuration update to a digital twin node (simulates config push).

    Args:
        node_id: Target node (e.g. 'sbc01')
        config_path: Dot-separated config path (e.g. 'media_manager.codec_policy')
        new_value: New value to set (will be JSON-parsed if possible)

    Returns:
        dict with success status and applied change
    """
    twin = get_twin()
    if not twin:
        return {"error": "No digital twin registered"}
    path_parts = config_path.split(".")
    try:
        parsed_value = json.loads(new_value)
    except (json.JSONDecodeError, ValueError):
        parsed_value = new_value
    twin.update_node_config(node_id, path_parts, parsed_value)
    return {
        "success": True,
        "node_id": node_id,
        "config_path": config_path,
        "applied_value": parsed_value,
        "message": f"Config {config_path}={parsed_value} applied to {node_id} in digital twin",
    }
