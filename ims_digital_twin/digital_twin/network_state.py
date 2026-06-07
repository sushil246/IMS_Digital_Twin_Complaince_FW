"""
IMS Digital Twin — live network state model.
Holds a mutable copy of topology, KPIs, and alarm state.
"""
from __future__ import annotations
import copy
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .topology import (
    IMSElement, NetworkInterface, ElementStatus,
    TOPOLOGY_NODES, TOPOLOGY_LINKS,
)


class NetworkStateTwin:
    """In-memory digital twin of the IMS network."""

    def __init__(self) -> None:
        self.nodes: Dict[str, IMSElement] = copy.deepcopy(TOPOLOGY_NODES)
        self.links: List[NetworkInterface] = copy.deepcopy(TOPOLOGY_LINKS)
        self.global_alarms: List[Dict] = []
        self.snapshot_ts: str = _now()
        self.incident_id: Optional[str] = None
        self.injected_fault: Optional[str] = None

    # ── state accessors ──────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[IMSElement]:
        return self.nodes.get(node_id)

    def get_sbc(self) -> IMSElement:
        return self.nodes["sbc01"]

    def all_alarms(self) -> List[Dict]:
        alarms = list(self.global_alarms)
        for node in self.nodes.values():
            for a in node.alarms:
                alarms.append({"node": node.node_id, "alarm": a})
        return alarms

    def summary(self) -> Dict[str, Any]:
        return {
            "snapshot_ts": self.snapshot_ts,
            "incident_id": self.incident_id,
            "injected_fault": self.injected_fault,
            "nodes": {
                nid: {
                    "type": n.element_type.value,
                    "status": n.status.value,
                    "cpu_pct": n.cpu_util_pct,
                    "mem_pct": n.mem_util_pct,
                    "sessions": n.active_sessions,
                    "alarms": n.alarms,
                }
                for nid, n in self.nodes.items()
            },
            "links": [
                {
                    "type": lnk.interface_type.value,
                    "src": lnk.source,
                    "dst": lnk.destination,
                    "status": lnk.status,
                    "latency_ms": lnk.latency_ms,
                    "loss_pct": lnk.packet_loss_pct,
                }
                for lnk in self.links
            ],
            "total_alarms": len(self.all_alarms()),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.summary(), indent=indent)

    # ── fault injection helpers (called by scenario engine) ──────────────────

    def set_node_status(self, node_id: str, status: ElementStatus) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].status = status

    def add_node_alarm(self, node_id: str, alarm: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].alarms.append(alarm)

    def update_node_kpi(self, node_id: str, **kwargs) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        for k, v in kwargs.items():
            if hasattr(node, k):
                setattr(node, k, v)

    def update_node_config(self, node_id: str, path: List[str], value: Any) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        cfg = node.config
        for key in path[:-1]:
            cfg = cfg.setdefault(key, {})
        cfg[path[-1]] = value

    def set_link_status(self, src: str, dst: str, status: str,
                         latency_ms: float = None, loss_pct: float = None) -> None:
        for lnk in self.links:
            if lnk.source == src and lnk.destination == dst:
                lnk.status = status
                if latency_ms is not None:
                    lnk.latency_ms = latency_ms
                if loss_pct is not None:
                    lnk.packet_loss_pct = loss_pct
                return

    def reset(self) -> None:
        self.__init__()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
