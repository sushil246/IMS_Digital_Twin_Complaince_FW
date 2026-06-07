"""
Full configuration text for every IMS node.
Oracle SBC → ACLI format.   IMS core nodes → Kamailio 5.8 format.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Oracle SBC  (Acme Packet 1100 / Acme Packet 3900)
# ─────────────────────────────────────────────────────────────────────────────
SBC_ACLI = """\
# ============================================================
# Oracle Communications Session Border Controller
# Platform : Acme Packet 1100
# Software : SCZ8.4.0 p3 build 188 (Release Date: 2026-01-15)
# Node     : sbc01.ims.lab  (10.0.1.10)
# ============================================================

## ── Physical Interfaces ──────────────────────────────────────
phy-interface
    name                eth0
    slot                0
    port                0
    admin-state         enabled
    auto-neg            enabled
    duplex-mode         full
    speed               1000
!

phy-interface
    name                eth1
    slot                0
    port                1
    admin-state         enabled
    auto-neg            enabled
    duplex-mode         full
    speed               1000
!

## ── Network Interfaces ───────────────────────────────────────
network-interface
    name                access
    description         UE-facing access realm
    phy-intf            eth0
    ip-address          10.0.1.10
    netmask             255.255.255.0
    gateway             10.0.1.1
    sec-address         10.0.1.11
    dns-ip-primary      10.0.0.53
    mtu                 1500
!

network-interface
    name                core
    description         IMS core realm (P-CSCF facing)
    phy-intf            eth1
    ip-address          10.0.2.100
    netmask             255.255.255.0
    gateway             10.0.2.1
    dns-ip-primary      10.0.0.53
    mtu                 1500
!

network-interface
    name                mgmt
    description         Out-of-band management
    phy-intf            eth0
    ip-address          192.168.1.10
    netmask             255.255.255.0
    gateway             192.168.1.1
    mtu                 1500
!

## ── TLS Profile ──────────────────────────────────────────────
tls-profile
    name                ims-tls-prof
    end-entity-cert     /opt/acme/certs/sbc01_2026.pem
    trusted-ca-certs    /opt/acme/certs/ims-ca-bundle.pem
    cipher-list         TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES256-GCM-SHA384
    tls-version         TLSv1.3
    verify-depth        3
    mutual-auth         disabled
    reneg-timeout       0
    cert-status-check   enabled
!

certificate-monitor
    name                ims-tls-prof-monitor
    tls-profile         ims-tls-prof
    alert-before-days   30
    critical-days       7
    syslog-on-expiry    enabled
!

## ── SIP Interfaces ───────────────────────────────────────────
sip-interface
    realm-id            access
    description         UE SIP/TLS access interface
    sip-ip-interfaces
        address         10.0.1.10
        port            5061
        transport-method    TLS
        tls-profile     ims-tls-prof
    !
    sip-ip-interfaces
        address         10.0.1.10
        port            5060
        transport-method    UDP
    !
    sip-timer-b         4000
    sip-timer-d         32000
    sip-timer-t1        500
    sip-timer-t2        4000
    max-forwards        70
    registration-caching    enabled
    max-register-per-second 200
    options-profile     ims-options
    media-sec-policy    ims-media-sec
!

sip-interface
    realm-id            core
    description         Core SIP/UDP to P-CSCF
    sip-ip-interfaces
        address         10.0.2.100
        port            5060
        transport-method    UDP
    !
    sip-timer-b         4000
    sip-timer-t1        500
    sip-timer-t2        4000
    max-forwards        69
!

## ── Realm Configuration ──────────────────────────────────────
realm-config
    id                  access
    description         Mobile UE access realm
    addr-prefix         10.10.0.0/16
    media-policy        ims-media
    mm-in-realm         enabled
    mm-in-network       enabled
    mm-same-ip          enabled
    msm-release         enabled
    bw-cac-non-mm       disabled
    media-sec-policy    ims-media-sec
    in-trans-filter     access-inbound
    out-trans-filter    access-outbound
!

realm-config
    id                  core
    description         IMS core network realm
    addr-prefix         10.0.0.0/8
    media-policy        ims-media
    mm-in-realm         enabled
    mm-in-network       enabled
!

## ── Session Agents ───────────────────────────────────────────
session-agent
    hostname            pcscf01.ims.lab
    ip-address          10.0.2.10
    port                5060
    transport-method    UDP
    realm-id            core
    description         Primary P-CSCF
    max-sessions        5000
    weight              10
    state               enabled
    ping-method         OPTIONS
    ping-interval       30
    ping-send-mode      keep-alive
    out-of-service-response-code    503
    failover-response-codes         503,408,500
!

## ── Media Manager ────────────────────────────────────────────
media-manager
    media-supervision-timeout   300
    max-bandwidth               100000
    media-policy                ims-media
    rtp-inactivity-timer        30
    rtcp-inactivity-timer       60
    update-ip-for-sdp-na        enabled
    nat-traversal               enabled
    latching                    passive
    rtp-keepalive-method        RTCP
    rtp-keepalive-interval      15
!

media-profile
    name                ims-media
    media-criteria      requires-audio
    codec-policy
        allow-codecs    PCMA PCMU G729 AMR-NB AMR-WB OPUS telephone-event
        codec-order     PCMA PCMU G729 AMR-NB
        transcoding     disabled
        sdp-bandwidth   AS:128
    !
!

## ── Media Security ───────────────────────────────────────────
media-sec-policy
    name                ims-media-sec
    srtp-enabled        enabled
    srtp-auth-tag-bits  80
    srtp-crypto-suite   AES_CM_128_HMAC_SHA1_80 AES_256_CM_HMAC_SHA1_80 AES_256_GCM_SHA384
    dtls-enabled        enabled
    dtls-cipher-suite   ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256
    dtls-version        DTLSv1.2
    srtp-key-exchange   dtls-srtp
!

## ── DoS Protection ───────────────────────────────────────────
dos-protection
    trust-level         medium
    phy-interface       access
    register-max-rate   200
    invite-max-rate     100
    register-burst-size 50
    invite-burst-size   30
    deny-period         30
    exception-addresses 10.0.0.0/8 192.168.1.0/24
!

## ── Local Policy ─────────────────────────────────────────────
local-policy
    from-address        *
    to-address          *
    source-realm        access
    policy-priority     5
    policy-attribute
        next-hop        pcscf01.ims.lab
        realm           core
        action          none
    !
!

## ── SIP Config ───────────────────────────────────────────────
sip-config
    registration-max    50000
    registration-interval   3600
    home-realm-id       core
    max-message-size    65536
    nat-interval        30
    tcp-keepalive       enabled
!
"""

# ─────────────────────────────────────────────────────────────────────────────
# P-CSCF  — Kamailio 5.8.1  (Proxy-Call Session Control Function)
# ─────────────────────────────────────────────────────────────────────────────
PCSCF_KAMAILIO_CFG = """\
#!KAMAILIO
# =============================================================
# P-CSCF Configuration — Proxy-Call Session Control Function
# Platform : Kamailio 5.8.1 (IMS build)
# Node     : pcscf01.ims.lab  (10.0.2.10)
# Role     : First IMS contact point; Rx interface to PCRF
# =============================================================

####### Global Parameters #########
debug=2
log_stderror=no
log_facility=LOG_LOCAL0
log_name="kamailio-pcscf"
fork=yes
children=8
auto_aliases=no

alias="pcscf01.ims.lab"
listen=udp:10.0.2.10:5060
listen=tcp:10.0.2.10:5060
listen=tls:10.0.2.10:5061

enable_tls=1
tcp_connection_lifetime=3600
tcp_accept_no_cl=yes
tcp_rd_buf_size=16384
shm_mem_size=256
pkg_mem_size=32
max_while_loops=500

####### Modules #########
mpath="/usr/lib64/kamailio/modules/"

loadmodule "tm.so"
loadmodule "tmx.so"
loadmodule "sl.so"
loadmodule "rr.so"
loadmodule "pv.so"
loadmodule "maxfwd.so"
loadmodule "textops.so"
loadmodule "siputils.so"
loadmodule "dialog.so"
loadmodule "sanity.so"
loadmodule "tls.so"
loadmodule "xlog.so"
loadmodule "nathelper.so"
loadmodule "rtpproxy.so"
loadmodule "ims_usrloc_pcscf.so"
loadmodule "ims_registrar_pcscf.so"
loadmodule "ims_auth.so"
loadmodule "ims_isc.so"
loadmodule "ims_qos.so"
loadmodule "cdp.so"
loadmodule "cdp_avp.so"

####### Module Parameters #########
# --- tm ---
modparam("tm","fr_timer",5000)
modparam("tm","fr_inv_timer",30000)
modparam("tm","restart_fr_on_each_reply",1)
modparam("tm","onreply_avp_mode",1)

# --- rr ---
modparam("rr","enable_full_lr",1)
modparam("rr","append_fromtag",1)

# --- dialog ---
modparam("dialog","dlg_flag",1)
modparam("dialog","timeout_noreset",1)

# --- tls ---
modparam("tls","config","/etc/kamailio/tls.cfg")
modparam("tls","certificate","/etc/kamailio/certs/pcscf01.pem")
modparam("tls","private_key","/etc/kamailio/certs/pcscf01.key")
modparam("tls","ca_list","/etc/kamailio/certs/ims-ca.pem")
modparam("tls","tls_method","TLSv1_3")

# --- nathelper ---
modparam("nathelper","natping_interval",30)
modparam("nathelper","ping_nated_only",1)

# --- rtpproxy ---
modparam("rtpproxy","rtpproxy_sock","udp:127.0.0.1:7722")
modparam("rtpproxy","rtpproxy_tout",1)

# --- ims_usrloc_pcscf ---
modparam("ims_usrloc_pcscf","hashing_type",2)
modparam("ims_usrloc_pcscf","db_mode",0)
modparam("ims_usrloc_pcscf","max_contacts",100000)

# --- ims_registrar_pcscf ---
modparam("ims_registrar_pcscf","mo",0)
modparam("ims_registrar_pcscf","my_uri","sip:pcscf01.ims.lab:5060")
modparam("ims_registrar_pcscf","subscription_default_expires",3600)
modparam("ims_registrar_pcscf","subscription_min_expires",60)
modparam("ims_registrar_pcscf","subscription_max_expires",7200)

# --- ims_auth ---
modparam("ims_auth","cxdx_forced_peer","hss01.ims.lab")
modparam("ims_auth","registration_default_algorithm","AKAv2-MD5")
modparam("ims_auth","av_request_at_once",5)

# --- cdp ---
modparam("cdp","config_file","/etc/kamailio/pcscf_diameter.xml")
modparam("cdp","latency_threshold_ms",100)

# --- ims_qos (Rx interface to PCRF) ---
modparam("ims_qos","rx_dest_realm","ims.lab")
modparam("ims_qos","rx_forced_peer","pcrf01.ims.lab")
modparam("ims_qos","media_type","audio")

####### Routing Logic #########
request_route {
    if (!sanity_check()) { exit; }
    if (!mf_process_maxfwd_header("70")) {
        sl_send_reply("483","Too Many Hops"); exit;
    }
    if (is_method("REGISTER")) {
        route(REGISTER);
    } else if (is_method("INVITE|UPDATE|PRACK")) {
        route(INVITE);
    } else if (is_method("BYE|CANCEL")) {
        route(BYE);
    } else if (is_method("OPTIONS")) {
        sl_send_reply("200","OK"); exit;
    } else {
        route(RELAY);
    }
}

route[REGISTER] {
    xlog("L_INFO","P-CSCF REGISTER from $fu via SBC\\n");
    append_hf("P-Access-Network-Info: 3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=310260001\\r\\n");
    append_hf("P-Visited-Network-ID: \\"ims.lab\\"\\r\\n");
    add_path();
    t_relay(); exit;
}

route[INVITE] {
    xlog("L_INFO","P-CSCF INVITE $rm from $fu to $tu\\n");
    if (!has_totag()) {
        route(AUTH);
    }
    rtpproxy_manage("co");
    route(RELAY);
}

route[AUTH] {
    if (!ims_www_authenticate("ims.lab")) {
        if ($? == -1) {
            sl_send_reply("403","Forbidden"); exit;
        }
        sl_send_reply("401","Unauthorized"); exit;
    }
}

route[BYE] {
    rtpproxy_destroy("");
    route(RELAY);
}

route[RELAY] {
    if (!t_relay()) {
        sl_reply_error();
    }
    exit;
}

onreply_route[RELAY] {
    if (status=~"18[03]") { rtpproxy_manage("co"); }
    if (status=~"2[0-9][0-9]") { rtpproxy_manage("co"); }
}

failure_route[RELAY] {
    if (t_was_cancelled()) { exit; }
    xlog("L_WARN","P-CSCF relay failure: $T_reply_code $fu -> $tu\\n");
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# I-CSCF  — Kamailio 5.8.1  (Interrogating-CSCF)
# ─────────────────────────────────────────────────────────────────────────────
ICSCF_KAMAILIO_CFG = """\
#!KAMAILIO
# =============================================================
# I-CSCF Configuration — Interrogating-Call Session Control Function
# Platform : Kamailio 5.8.1 (IMS build)
# Node     : icscf01.ims.lab  (10.0.2.20)
# Role     : Home network entry; HSS Cx UAR/LIR queries
# =============================================================

####### Global Parameters #########
debug=2
log_stderror=no
log_facility=LOG_LOCAL0
log_name="kamailio-icscf"
fork=yes
children=8

alias="icscf01.ims.lab"
listen=udp:10.0.2.20:5060
listen=tcp:10.0.2.20:5060

shm_mem_size=128
pkg_mem_size=16
max_while_loops=200

####### Modules #########
mpath="/usr/lib64/kamailio/modules/"

loadmodule "tm.so"
loadmodule "sl.so"
loadmodule "rr.so"
loadmodule "pv.so"
loadmodule "maxfwd.so"
loadmodule "textops.so"
loadmodule "siputils.so"
loadmodule "xlog.so"
loadmodule "ims_icscf.so"
loadmodule "cdp.so"
loadmodule "cdp_avp.so"

####### Module Parameters #########
# --- tm ---
modparam("tm","fr_timer",10000)
modparam("tm","fr_inv_timer",60000)

# --- rr ---
modparam("rr","enable_full_lr",1)

# --- cdp ---
modparam("cdp","config_file","/etc/kamailio/icscf_diameter.xml")
modparam("cdp","latency_threshold_ms",200)

# --- ims_icscf ---
modparam("ims_icscf","cxdx_forced_peer","hss01.ims.lab")
modparam("ims_icscf","cxdx_dest_realm","ims.lab")
modparam("ims_icscf","route_lir_term","LIR_TERM")
modparam("ims_icscf","scscf_entry_expiry",600)

####### Routing Logic #########
request_route {
    if (!mf_process_maxfwd_header("69")) {
        sl_send_reply("483","Too Many Hops"); exit;
    }
    if (is_method("REGISTER")) {
        route(REGISTER_UAR);
    } else if (is_method("INVITE|SUBSCRIBE|OPTIONS")) {
        route(INVITE_LIR);
    } else {
        route(RELAY);
    }
}

# UAR — User Authorization Request to HSS for REGISTER
route[REGISTER_UAR] {
    xlog("L_INFO","I-CSCF UAR for $tu\\n");
    if (!I_perform_user_authorization_request("ims.lab","REG")) {
        t_reply("403","HSS UAR Rejected"); exit;
    }
    # On UAA success, forward to assigned S-CSCF
    if ($var(uar_result) == 1) {
        # Existing registration — use assigned SCSCF
        append_hf("Route: <sip:scscf01.ims.lab:6060;lr>\\r\\n");
    } else if ($var(uar_result) == 2) {
        # New registration — select from capability set
        I_select_scscf();
    } else {
        t_reply("403","Forbidden"); exit;
    }
    route(RELAY);
}

# LIR — Location Info Request to HSS for INVITE routing
route[INVITE_LIR] {
    xlog("L_INFO","I-CSCF LIR for $tu\\n");
    if (!I_perform_location_information_request("ims.lab")) {
        t_reply("404","User Not Found"); exit;
    }
    route(RELAY);
}

route[RELAY] {
    if (!t_relay()) { sl_reply_error(); }
    exit;
}

failure_route[RELAY] {
    if (t_was_cancelled()) { exit; }
    xlog("L_WARN","I-CSCF relay failure: $T_reply_code\\n");
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# S-CSCF  — Kamailio 5.8.1  (Serving-CSCF)
# ─────────────────────────────────────────────────────────────────────────────
SCSCF_KAMAILIO_CFG = """\
#!KAMAILIO
# =============================================================
# S-CSCF Configuration — Serving-Call Session Control Function
# Platform : Kamailio 5.8.1 (IMS build)
# Node     : scscf01.ims.lab  (10.0.2.30)
# Role     : Serves registered UEs; Cx SAR/MAR; ISC to AS
# =============================================================

####### Global Parameters #########
debug=2
log_stderror=no
log_facility=LOG_LOCAL0
log_name="kamailio-scscf"
fork=yes
children=12

alias="scscf01.ims.lab"
listen=udp:10.0.2.30:6060
listen=tcp:10.0.2.30:6060

shm_mem_size=512
pkg_mem_size=64
max_while_loops=500

####### Modules #########
mpath="/usr/lib64/kamailio/modules/"

loadmodule "tm.so"
loadmodule "tmx.so"
loadmodule "sl.so"
loadmodule "rr.so"
loadmodule "pv.so"
loadmodule "maxfwd.so"
loadmodule "textops.so"
loadmodule "siputils.so"
loadmodule "dialog.so"
loadmodule "xlog.so"
loadmodule "avpops.so"
loadmodule "ims_usrloc_scscf.so"
loadmodule "ims_registrar_scscf.so"
loadmodule "ims_auth.so"
loadmodule "ims_isc.so"
loadmodule "cdp.so"
loadmodule "cdp_avp.so"

####### Module Parameters #########
# --- tm ---
modparam("tm","fr_timer",5000)
modparam("tm","fr_inv_timer",30000)
modparam("tm","restart_fr_on_each_reply",1)

# --- dialog ---
modparam("dialog","dlg_flag",1)
modparam("dialog","timeout_noreset",1)
modparam("dialog","db_mode",0)

# --- ims_usrloc_scscf ---
modparam("ims_usrloc_scscf","db_mode",0)
modparam("ims_usrloc_scscf","max_contacts",250000)
modparam("ims_usrloc_scscf","expire_process_interval",30)
modparam("ims_usrloc_scscf","hash_size",256)

# --- ims_registrar_scscf ---
modparam("ims_registrar_scscf","mo",0)
modparam("ims_registrar_scscf","my_uri","sip:scscf01.ims.lab:6060")
modparam("ims_registrar_scscf","default_expires",3600)
modparam("ims_registrar_scscf","min_expires",60)
modparam("ims_registrar_scscf","max_expires",7200)
modparam("ims_registrar_scscf","subscription_default_expires",3600)
modparam("ims_registrar_scscf","user_data_always",1)

# --- ims_auth ---
modparam("ims_auth","cxdx_forced_peer","hss01.ims.lab")
modparam("ims_auth","registration_default_algorithm","AKAv2-MD5")
modparam("ims_auth","av_request_at_once",5)
modparam("ims_auth","av_request_at_sync",5)

# --- cdp ---
modparam("cdp","config_file","/etc/kamailio/scscf_diameter.xml")
modparam("cdp","latency_threshold_ms",100)

# --- ims_isc (IMS Service Control — interface to AS) ---
modparam("ims_isc","my_uri","sip:scscf01.ims.lab:6060")
modparam("ims_isc","service_routes","sip:as01.ims.lab:7060;lr")

####### Routing Logic #########
request_route {
    if (!mf_process_maxfwd_header("68")) {
        sl_send_reply("483","Too Many Hops"); exit;
    }
    if (is_method("REGISTER")) {
        route(REGISTER_MAR);
    } else if (is_method("INVITE")) {
        route(INVITE_ORIG);
    } else if (is_method("BYE|CANCEL|UPDATE|PRACK")) {
        route(RELAY);
    } else if (is_method("SUBSCRIBE|NOTIFY|PUBLISH")) {
        route(SUBSCRIPTION);
    } else {
        route(RELAY);
    }
}

# MAR — Multimedia Authentication Request to HSS
route[REGISTER_MAR] {
    xlog("L_INFO","S-CSCF REGISTER from $fu Expires:$hdr(Expires)\\n");
    if ($hdr(Expires) == "0") {
        route(DEREGISTER_SAR);
    }
    if (!www_authorize("ims.lab","ims_auth")) {
        if ($? == -1 || $? == -2) {
            t_reply("403","Forbidden"); exit;
        }
        www_challenge("ims.lab","1");
        exit;
    }
    if (!save("location")) {
        t_reply("500","Failed to save registration"); exit;
    }
    # SAR — Server Assignment Request to HSS
    if (!Cx_server_assignment("sip:scscf01.ims.lab:6060","REGISTRATION")) {
        t_reply("500","HSS SAR Failed"); exit;
    }
    t_reply("200","OK");
    exit;
}

route[DEREGISTER_SAR] {
    xlog("L_INFO","S-CSCF de-REGISTER for $tu\\n");
    if (!Cx_server_assignment("sip:scscf01.ims.lab:6060","USER_DEREGISTRATION")) {
        xlog("L_WARN","HSS SAR for de-registration failed\\n");
    }
    save("location");
    t_reply("200","OK"); exit;
}

# Originating INVITE — ISC trigger check
route[INVITE_ORIG] {
    xlog("L_INFO","S-CSCF INVITE orig $fu -> $tu\\n");
    if (!lookup("location")) {
        t_reply("480","Temporarily Unavailable"); exit;
    }
    if (isc_match_filter("orig")) {
        route(ISC_TRIGGER);
    }
    route(RELAY);
}

route[ISC_TRIGGER] {
    xlog("L_INFO","S-CSCF ISC trigger: forwarding to AS\\n");
    t_relay(); exit;
}

route[SUBSCRIPTION] {
    if (!t_relay()) { sl_reply_error(); }
    exit;
}

route[RELAY] {
    if (!t_relay()) { sl_reply_error(); }
    exit;
}

onreply_route[RELAY] {
    xlog("L_DEBUG","S-CSCF reply $rs $rr for $fu\\n");
}

failure_route[RELAY] {
    if (t_was_cancelled()) { exit; }
    xlog("L_WARN","S-CSCF failure $T_reply_code for $fu -> $tu\\n");
    if (t_check_status("408|500|503")) {
        t_reply("503","Service Unavailable"); exit;
    }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# HSS  — OpenHSS / Diameter Cx config
# ─────────────────────────────────────────────────────────────────────────────
HSS_CONFIG = """\
# =============================================================
# Home Subscriber Server (HSS) — Diameter Cx/Sh Interface
# Platform : OpenHSS 6.2 (FHoSS)
# Node     : hss01.ims.lab  (10.0.3.10)
# DB       : MySQL 8.0  hss_db @ 10.0.3.50:3306
# =============================================================

## Diameter Configuration
DiameterPeer {
    FQDN        = "hss01.ims.lab"
    Realm       = "ims.lab"
    AcceptUnknownPeers = 0
    DropUnknownOnDisconnect = 1
    Tc          = 30
    Workers     = 8

    Peer { FQDN="icscf01.ims.lab";  Realm="ims.lab"; port=3868; }
    Peer { FQDN="scscf01.ims.lab";  Realm="ims.lab"; port=3868; }
    Peer { FQDN="pcscf01.ims.lab";  Realm="ims.lab"; port=3869; }
}

## Cx Interface (RFC 4740 / 3GPP TS 29.228)
CxInterface {
    Listen { address=10.0.3.10; port=3868; }
    supported_features = UAR UAA SAR SAA MAR MAA LIR LIA
    authentication_scheme = AKAv2-MD5,AKAv1-MD5,HTTP_DIGEST
    default_scscf = "sip:scscf01.ims.lab:6060"
    max_subscribers = 250000
    current_subscribers = 183420
}

## Subscriber Template
SubscriberDefaults {
    default_qos_profile = "IMS-default"
    charging_function   = "sip:cdf01.ims.lab"
    ecscf               = "sip:ecscf01.ims.lab"
    barring_indication  = 0
}

## Application Server Trigger (iFC)
ServiceProfile "voice" {
    InitialFilterCriteria priority=1 {
        trigger_point { method=INVITE direction=ORIGINATING }
        application_server { uri="sip:voicemail.ims.lab:7060"; default_handling=CONTINUE }
    }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# PCRF  — Diameter Rx/Gx interface
# ─────────────────────────────────────────────────────────────────────────────
PCRF_CONFIG = """\
# =============================================================
# PCRF — Policy and Charging Rules Function
# Platform : OpenPCRF 5.1
# Node     : pcrf01.ims.lab  (10.0.3.20)
# Interfaces: Rx (from P-CSCF), Gx (to PGW)
# =============================================================

DiameterPeer {
    FQDN    = "pcrf01.ims.lab"
    Realm   = "ims.lab"
    Workers = 4
    Peer { FQDN="pcscf01.ims.lab"; Realm="ims.lab"; port=3869; iface=Rx; }
}

RxInterface {
    Listen { address=10.0.3.20; port=3869; }
    event_triggers = QOS_CHANGE,RAI,LOSS_OF_BEARER
    default_qos_class = "GBR_voice"
    max_bandwidth_ul_kbps = 128
    max_bandwidth_dl_kbps = 128
    guaranteed_bandwidth_kbps = 64
    arp_priority = 2
    preemption_capability = SHALL_NOT
    preemption_vulnerability = PRE-EMPTABLE
}

GxInterface {
    pgw_peers = ["pgw01.ims.lab:3868"]
    default_charging_rule = "IMS_VOICE"
}

QoSProfile "GBR_voice" {
    qci = 1
    gbr_ul = 64000
    gbr_dl = 64000
    mbr_ul = 128000
    mbr_dl = 128000
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# MGW  — Media Gateway (H.248 / MEGACO)
# ─────────────────────────────────────────────────────────────────────────────
MGW_CONFIG = """\
# =============================================================
# Media Gateway (MGW) — H.248/MEGACO Interface
# Platform : OpenMGW 4.0
# Node     : mgw01.ims.lab  (10.0.4.10)
# Interface: Mn (S-CSCF via H.248)
# =============================================================

H248Config {
    LocalAddress    = 10.0.4.10
    H248Port        = 2944
    H248Version     = 3
    TransportMode   = TCP
    CallAgentList   = ["scscf01.ims.lab:2944"]
    HeartbeatInterval = 30
    MaxContexts     = 10000
    MaxTerminations = 20000
}

MediaConfig {
    RTPBasePort     = 20000
    RTPMaxPort      = 30000
    RTPInterface    = 10.0.4.10
    CodecList       = G.711-PCMA G.711-PCMU G.729A G.729B AMR-NB AMR-WB OPUS
    T38_FAX         = enabled
    DTMF_Mode       = RFC2833
    JitterBuffer    = adaptive
    JitterBufferMax = 200
    EchoCanceller   = enabled
    SRTP_Passthrough = enabled
}

PSTNInterface {
    Type        = E1/PRI
    Spans       = 8
    Channels    = 240
    Signaling   = ISDN-PRI
    ClockSource = primary
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Runtime details per node  (ps, netstat, memory breakdown, etc.)
# ─────────────────────────────────────────────────────────────────────────────
NODE_RUNTIME = {
    "sbc01": {
        "software_version": "SCZ8.4.0 p3 build 188",
        "platform": "Acme Packet 1100 (Cavium Octeon II)",
        "uptime": "47d 12h 33m",
        "os": "AcmeOS 6.4 (based on Linux 5.15-lts)",
        "processes": [
            {"pid":1,   "name":"init",      "cpu":"0.0", "mem":"0.1", "state":"S"},
            {"pid":101, "name":"sipd",      "cpu":"4.2", "mem":"8.1", "state":"S", "note":"SIP proxy daemon"},
            {"pid":102, "name":"mbcd",      "cpu":"2.1", "mem":"3.4", "state":"S", "note":"Media border controller"},
            {"pid":103, "name":"acliserver","cpu":"0.1", "mem":"0.5", "state":"S", "note":"CLI/NETCONF mgmt"},
            {"pid":104, "name":"berpd",     "cpu":"0.0", "mem":"0.2", "state":"S", "note":"BER packet daemon"},
            {"pid":105, "name":"syslog-ng", "cpu":"0.0", "mem":"0.3", "state":"S"},
            {"pid":106, "name":"snmpd",     "cpu":"0.0", "mem":"0.2", "state":"S"},
        ],
        "interfaces": [
            {"name":"eth0","ip":"10.0.1.10","mask":"255.255.255.0","mac":"00:a0:8e:01:11:22","speed":"1Gbps","role":"access"},
            {"name":"eth1","ip":"10.0.2.100","mask":"255.255.255.0","mac":"00:a0:8e:01:11:23","speed":"1Gbps","role":"core"},
            {"name":"eth2","ip":"192.168.1.10","mask":"255.255.255.0","mac":"00:a0:8e:01:11:24","speed":"100Mbps","role":"mgmt"},
        ],
        "connections": [
            {"proto":"TCP","local":"10.0.2.100:5060","remote":"10.0.2.10:5060","state":"ESTABLISHED","desc":"P-CSCF SIP"},
            {"proto":"UDP","local":"10.0.1.10:5060","remote":"0.0.0.0:*","state":"LISTEN","desc":"access SIP/UDP"},
            {"proto":"TLS","local":"10.0.1.10:5061","remote":"0.0.0.0:*","state":"LISTEN","desc":"access SIP/TLS"},
            {"proto":"TCP","local":"192.168.1.10:22","remote":"192.168.1.50:44123","state":"ESTABLISHED","desc":"mgmt SSH"},
        ],
        "stats": {"active_calls":1240,"registrations":18200,"cps":42,"pps":8800,"rtp_flows":2480},
    },
    "pcscf01": {
        "software_version": "Kamailio 5.8.1 (IMS build r23f89a2)",
        "platform": "Dell PowerEdge R650 (Intel Xeon Gold 6330 28c)",
        "uptime": "31d 4h 17m",
        "os": "Rocky Linux 9.3 (kernel 5.14.0-362.el9)",
        "processes": [
            {"pid":1001,"name":"kamailio","cpu":"3.8","mem":"12.4","state":"S","note":"main SIP proxy (8 workers)"},
            {"pid":1002,"name":"rtpproxy","cpu":"2.1","mem":"4.2","state":"S","note":"RTP proxy (127.0.0.1:7722)"},
            {"pid":1003,"name":"cdp",     "cpu":"0.4","mem":"1.8","state":"S","note":"Diameter CDP (Rx to PCRF)"},
            {"pid":1004,"name":"mysqld",  "cpu":"0.2","mem":"6.0","state":"S","note":"Kamailio DB (location)"},
            {"pid":1005,"name":"syslog-ng","cpu":"0.0","mem":"0.3","state":"S"},
        ],
        "interfaces": [
            {"name":"ens160","ip":"10.0.2.10","mask":"255.255.255.0","mac":"00:50:56:aa:01:01","speed":"10Gbps","role":"sip"},
            {"name":"ens161","ip":"10.0.3.90","mask":"255.255.255.0","mac":"00:50:56:aa:01:02","speed":"10Gbps","role":"diameter"},
            {"name":"lo","ip":"127.0.0.1","mask":"255.0.0.0","mac":"—","speed":"loopback","role":"local"},
        ],
        "connections": [
            {"proto":"UDP","local":"10.0.2.10:5060","remote":"10.0.2.100:5060","state":"ESTABLISHED","desc":"SBC"},
            {"proto":"TCP","local":"10.0.2.10:5060","remote":"10.0.2.20:5060","state":"ESTABLISHED","desc":"I-CSCF"},
            {"proto":"TCP","local":"10.0.3.90:3869","remote":"10.0.3.20:3869","state":"ESTABLISHED","desc":"PCRF Rx"},
        ],
        "stats": {"active_calls":1190,"registrations":18200,"cps":39,"cdp_rx_sessions":412},
    },
    "icscf01": {
        "software_version": "Kamailio 5.8.1 (IMS build r23f89a2)",
        "platform": "Dell PowerEdge R650 (Intel Xeon Gold 6330 28c)",
        "uptime": "31d 4h 15m",
        "os": "Rocky Linux 9.3 (kernel 5.14.0-362.el9)",
        "processes": [
            {"pid":2001,"name":"kamailio","cpu":"1.2","mem":"8.3","state":"S","note":"I-CSCF (8 workers)"},
            {"pid":2002,"name":"cdp",     "cpu":"0.3","mem":"1.5","state":"S","note":"Diameter CDP (Cx to HSS)"},
        ],
        "interfaces": [
            {"name":"ens160","ip":"10.0.2.20","mask":"255.255.255.0","mac":"00:50:56:aa:02:01","speed":"10Gbps","role":"sip"},
            {"name":"ens161","ip":"10.0.3.91","mask":"255.255.255.0","mac":"00:50:56:aa:02:02","speed":"10Gbps","role":"diameter"},
        ],
        "connections": [
            {"proto":"TCP","local":"10.0.2.20:5060","remote":"10.0.2.10:5060","state":"ESTABLISHED","desc":"P-CSCF"},
            {"proto":"TCP","local":"10.0.2.20:5060","remote":"10.0.2.30:6060","state":"ESTABLISHED","desc":"S-CSCF"},
            {"proto":"TCP","local":"10.0.3.91:3868","remote":"10.0.3.10:3868","state":"ESTABLISHED","desc":"HSS Cx"},
        ],
        "stats": {"uar_requests":18200,"lir_requests":4500,"uar_success_rate":"99.8%"},
    },
    "scscf01": {
        "software_version": "Kamailio 5.8.1 (IMS build r23f89a2)",
        "platform": "Dell PowerEdge R750 (Intel Xeon Gold 6354 18c × 2)",
        "uptime": "31d 4h 14m",
        "os": "Rocky Linux 9.3 (kernel 5.14.0-362.el9)",
        "processes": [
            {"pid":3001,"name":"kamailio","cpu":"5.4","mem":"18.6","state":"S","note":"S-CSCF (12 workers)"},
            {"pid":3002,"name":"cdp",     "cpu":"0.5","mem":"2.0","state":"S","note":"Diameter CDP (Cx to HSS)"},
            {"pid":3003,"name":"mysqld",  "cpu":"1.2","mem":"8.0","state":"S","note":"usrloc_scscf DB"},
        ],
        "interfaces": [
            {"name":"ens160","ip":"10.0.2.30","mask":"255.255.255.0","mac":"00:50:56:aa:03:01","speed":"10Gbps","role":"sip"},
            {"name":"ens161","ip":"10.0.3.92","mask":"255.255.255.0","mac":"00:50:56:aa:03:02","speed":"10Gbps","role":"diameter"},
        ],
        "connections": [
            {"proto":"TCP","local":"10.0.2.30:6060","remote":"10.0.2.20:5060","state":"ESTABLISHED","desc":"I-CSCF"},
            {"proto":"TCP","local":"10.0.3.92:3868","remote":"10.0.3.10:3868","state":"ESTABLISHED","desc":"HSS Cx"},
            {"proto":"H248","local":"10.0.2.30:2944","remote":"10.0.4.10:2944","state":"ESTABLISHED","desc":"MGW Mn"},
        ],
        "stats": {"registered_users":18200,"active_dialogs":1190,"sar_requests":18200,"sar_success_rate":"99.9%"},
    },
    "hss01": {
        "software_version": "OpenHSS 6.2 (FHoSS build 2025-11-30)",
        "platform": "Dell PowerEdge R650 (Intel Xeon Silver 4314 16c)",
        "uptime": "62d 8h 40m",
        "os": "Rocky Linux 9.3",
        "processes": [
            {"pid":4001,"name":"fhoss",  "cpu":"2.1","mem":"22.4","state":"S","note":"HSS server (Java 17)"},
            {"pid":4002,"name":"mysqld", "cpu":"3.4","mem":"28.0","state":"S","note":"subscriber DB (250k users)"},
            {"pid":4003,"name":"cdp",    "cpu":"0.2","mem":"1.2","state":"S","note":"Diameter stack"},
        ],
        "interfaces": [
            {"name":"ens160","ip":"10.0.3.10","mask":"255.255.255.0","mac":"00:50:56:aa:04:01","speed":"10Gbps","role":"diameter"},
        ],
        "stats": {"total_subscribers":250000,"active_subscribers":183420,"cx_uar_rate":"120/s","cx_sar_rate":"45/s"},
    },
    "pcrf01": {
        "software_version": "OpenPCRF 5.1 (build 2025-09-14)",
        "platform": "Dell PowerEdge R650",
        "uptime": "45d 2h 10m",
        "os": "Rocky Linux 9.3",
        "processes": [
            {"pid":5001,"name":"pcrf",   "cpu":"1.8","mem":"12.0","state":"S","note":"PCRF main (Rx+Gx)"},
            {"pid":5002,"name":"mysqld", "cpu":"0.8","mem":"8.0","state":"S","note":"policy DB"},
        ],
        "interfaces": [
            {"name":"ens160","ip":"10.0.3.20","mask":"255.255.255.0","mac":"00:50:56:aa:05:01","speed":"10Gbps","role":"diameter"},
        ],
        "stats": {"active_rx_sessions":412,"gx_sessions":18200,"policy_decisions":"38/s"},
    },
    "mgw01": {
        "software_version": "OpenMGW 4.0 (build 2025-08-22)",
        "platform": "Dialogic DNI-2410 Media Gateway",
        "uptime": "62d 8h 39m",
        "os": "VxWorks 7 (real-time)",
        "processes": [
            {"pid":6001,"name":"mgw-ctrl",  "cpu":"0.5","mem":"4.0","state":"S","note":"H.248 control"},
            {"pid":6002,"name":"mgw-media", "cpu":"3.2","mem":"8.0","state":"S","note":"media processing"},
            {"pid":6003,"name":"mgw-pstn",  "cpu":"0.8","mem":"2.0","state":"S","note":"PSTN interface"},
        ],
        "interfaces": [
            {"name":"eth0","ip":"10.0.4.10","mask":"255.255.255.0","mac":"00:60:8c:aa:06:01","speed":"1Gbps","role":"h248"},
            {"name":"e1-0","ip":"—","mask":"—","mac":"—","speed":"2.048Mbps","role":"E1/PRI"},
        ],
        "stats": {"active_rtp_streams":2480,"pstn_channels_active":186,"h248_contexts":1240},
    },
}

# Map node_id to config text
NODE_CONFIG_TEXT = {
    "sbc01":   SBC_ACLI,
    "pcscf01": PCSCF_KAMAILIO_CFG,
    "icscf01": ICSCF_KAMAILIO_CFG,
    "scscf01": SCSCF_KAMAILIO_CFG,
    "hss01":   HSS_CONFIG,
    "pcrf01":  PCRF_CONFIG,
    "mgw01":   MGW_CONFIG,
}

NODE_CONFIG_TYPE = {
    "sbc01":   "Oracle ACLI",
    "pcscf01": "Kamailio 5.8 CFG",
    "icscf01": "Kamailio 5.8 CFG",
    "scscf01": "Kamailio 5.8 CFG",
    "hss01":   "OpenHSS Config",
    "pcrf01":  "OpenPCRF Config",
    "mgw01":   "H.248 Config",
}
