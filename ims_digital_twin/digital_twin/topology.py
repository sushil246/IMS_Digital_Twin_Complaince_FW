"""
IMS Network Topology — static definitions for all network elements and interfaces.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ElementType(str, Enum):
    SBC = "Oracle_SBC"
    P_CSCF = "P-CSCF"
    I_CSCF = "I-CSCF"
    S_CSCF = "S-CSCF"
    HSS = "HSS"
    PCRF = "PCRF"
    MGW = "MGW"
    UE = "UE"
    PSTN_GW = "PSTN_GW"


class ElementStatus(str, Enum):
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"


class InterfaceType(str, Enum):
    Gm = "Gm"        # UE <-> P-CSCF
    Mw = "Mw"        # CSCF <-> CSCF
    Cx = "Cx"        # I/S-CSCF <-> HSS
    Rx = "Rx"        # P-CSCF <-> PCRF
    Gx = "Gx"        # PCRF <-> PGW
    Mn = "Mn"        # S-CSCF <-> MGW
    SBC_ACCESS = "SBC_Access"    # UE <-> SBC
    SBC_CORE = "SBC_Core"        # SBC <-> P-CSCF


@dataclass
class NetworkInterface:
    interface_type: InterfaceType
    source: str
    destination: str
    protocol: str = "SIP/TLS"
    port: int = 5061
    status: str = "UP"
    latency_ms: float = 2.0
    packet_loss_pct: float = 0.0


@dataclass
class IMSElement:
    node_id: str
    element_type: ElementType
    hostname: str
    ip_address: str
    management_ip: str
    status: ElementStatus = ElementStatus.UP
    software_version: str = "latest"
    cpu_util_pct: float = 15.0
    mem_util_pct: float = 30.0
    active_sessions: int = 0
    alarms: List[str] = field(default_factory=list)
    config: Dict = field(default_factory=dict)


# ── Canonical IMS topology ────────────────────────────────────────────────────

TOPOLOGY_NODES: Dict[str, IMSElement] = {
    "sbc01": IMSElement(
        node_id="sbc01",
        element_type=ElementType.SBC,
        hostname="sbc01.ims.lab",
        ip_address="10.0.1.10",
        management_ip="192.168.1.10",
        software_version="Acme8.4.0p3",
        active_sessions=1240,
        config={
            "max_sessions": 5000,
            "sip_timers": {"T1": 500, "T2": 4000, "T4": 5000},
            "realm": "access",
            "tls_profile": "ims-tls-prof",
            "cert_expiry": "2026-09-01",
            "media_manager": {
                "codec_policy": "default",
                "srtp_enabled": True,
                "rtp_timeout": 30,
            },
            "session_agents": {
                "pcscf01": {"ip": "10.0.2.10", "port": 5060, "realm": "core", "weight": 10},
            },
            "local_policy": {
                "default_route": "pcscf01",
                "max_forwards": 70,
            },
            "registration_cache": {
                "max_entries": 50000,
                "current_entries": 18200,
            },
            "dos_protection": {
                "trust_level": "medium",
                "max_register_rate": 200,
                "max_invite_rate": 100,
            },
        },
    ),
    "pcscf01": IMSElement(
        node_id="pcscf01",
        element_type=ElementType.P_CSCF,
        hostname="pcscf01.ims.lab",
        ip_address="10.0.2.10",
        management_ip="192.168.1.20",
        software_version="OpenIMS-3.3.0",
        active_sessions=1190,
        config={"rx_interface": "enabled", "sip_port": 5060},
    ),
    "icscf01": IMSElement(
        node_id="icscf01",
        element_type=ElementType.I_CSCF,
        hostname="icscf01.ims.lab",
        ip_address="10.0.2.20",
        management_ip="192.168.1.21",
        software_version="OpenIMS-3.3.0",
        config={"cx_interface": "enabled"},
    ),
    "scscf01": IMSElement(
        node_id="scscf01",
        element_type=ElementType.S_CSCF,
        hostname="scscf01.ims.lab",
        ip_address="10.0.2.30",
        management_ip="192.168.1.22",
        software_version="OpenIMS-3.3.0",
        active_sessions=1190,
        config={"cx_interface": "enabled", "mn_interface": "enabled"},
    ),
    "hss01": IMSElement(
        node_id="hss01",
        element_type=ElementType.HSS,
        hostname="hss01.ims.lab",
        ip_address="10.0.3.10",
        management_ip="192.168.1.30",
        software_version="HSSv6.2",
        config={"diameter_port": 3868, "subscribers": 250000},
    ),
    "pcrf01": IMSElement(
        node_id="pcrf01",
        element_type=ElementType.PCRF,
        hostname="pcrf01.ims.lab",
        ip_address="10.0.3.20",
        management_ip="192.168.1.31",
        software_version="PCRFv5.1",
    ),
    "mgw01": IMSElement(
        node_id="mgw01",
        element_type=ElementType.MGW,
        hostname="mgw01.ims.lab",
        ip_address="10.0.4.10",
        management_ip="192.168.1.40",
        software_version="MGWv4.0",
        config={"h248_port": 2944, "codecs": ["G.711", "G.729", "AMR", "OPUS"]},
    ),
}

TOPOLOGY_LINKS: List[NetworkInterface] = [
    NetworkInterface(InterfaceType.SBC_ACCESS, "ue",      "sbc01",   "SIP/TLS", 5061),
    NetworkInterface(InterfaceType.SBC_CORE,   "sbc01",   "pcscf01", "SIP/UDP", 5060),
    NetworkInterface(InterfaceType.Gm,         "pcscf01", "icscf01", "SIP",     5060),
    NetworkInterface(InterfaceType.Mw,         "icscf01", "scscf01", "SIP",     5060),
    NetworkInterface(InterfaceType.Cx,         "icscf01", "hss01",   "Diameter",3868),
    NetworkInterface(InterfaceType.Cx,         "scscf01", "hss01",   "Diameter",3868),
    NetworkInterface(InterfaceType.Rx,         "pcscf01", "pcrf01",  "Diameter",3869),
    NetworkInterface(InterfaceType.Mn,         "scscf01", "mgw01",   "H.248",   2944),
]
