"""
Log ingestion and pattern-matching tools for the RCA agent.
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional

# Module-level log store
_log_store: List[str] = []


def store_logs(log_lines: List[str]) -> None:
    _log_store.clear()
    _log_store.extend(log_lines)


def get_all_logs() -> List[str]:
    return list(_log_store)


# ── Log query tools ───────────────────────────────────────────────────────────

def get_sbc_logs() -> dict:
    """Return all collected Oracle SBC log lines for analysis.

    Returns:
        dict with log_count and log_lines list
    """
    return {"log_count": len(_log_store), "log_lines": list(_log_store)}


def grep_logs(pattern: str, case_sensitive: bool = False) -> dict:
    """Search SBC logs for lines matching a regex pattern.

    Args:
        pattern: Python regex pattern to search for
        case_sensitive: Whether the search is case-sensitive (default: False)

    Returns:
        dict with matches list and match_count
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid regex: {e}", "matches": [], "match_count": 0}
    matches = [line for line in _log_store if compiled.search(line)]
    return {"match_count": len(matches), "matches": matches}


def count_sip_responses() -> dict:
    """Count SIP response codes in the logs to identify error patterns.

    Returns:
        dict mapping response code → count, plus error_rate_pct
    """
    pattern = re.compile(r"SIP/2\.0\s+(\d{3})\s+\w")
    counts: Dict[str, int] = {}
    for line in _log_store:
        m = pattern.search(line)
        if m:
            code = m.group(1)
            counts[code] = counts.get(code, 0) + 1
    total = sum(counts.values())
    error_codes = {c: v for c, v in counts.items() if c.startswith(("4", "5", "6"))}
    error_total = sum(error_codes.values())
    return {
        "response_counts": counts,
        "total_responses": total,
        "error_responses": error_total,
        "error_rate_pct": round(error_total / total * 100, 1) if total else 0,
        "error_breakdown": error_codes,
    }


def extract_alarm_lines() -> dict:
    """Extract all CRITICAL, MAJOR, WARNING, ERROR alarm lines from logs.

    Returns:
        dict with severity-bucketed alarm lines
    """
    buckets: Dict[str, List[str]] = {
        "CRITICAL": [], "MAJOR": [], "WARNING": [], "ERROR": [], "INFO": [],
    }
    sev_re = re.compile(
        r"\b(CRITICAL|MAJOR|MINOR|WARNING|ERROR|ALERT|INFO)\b", re.IGNORECASE
    )
    for line in _log_store:
        m = sev_re.search(line)
        if m:
            sev = m.group(1).upper()
            bucket = sev if sev in buckets else "INFO"
            buckets[bucket].append(line)
    return {sev: lines for sev, lines in buckets.items() if lines}


def extract_sip_call_ids() -> dict:
    """Extract all unique SIP Call-IDs from the logs.

    Returns:
        dict with call_ids list and count
    """
    pattern = re.compile(r"[Cc]all-ID=([a-f0-9]{8,})", re.IGNORECASE)
    call_ids = list({m.group(1) for line in _log_store for m in [pattern.search(line)] if m})
    return {"call_id_count": len(call_ids), "call_ids": call_ids}


def analyse_log_timeline() -> dict:
    """Summarise the sequence of events in log order for root cause tracing.

    Returns:
        dict with ordered_events list (timestamp + event summary)
    """
    events = []
    sev_re = re.compile(r"\b(CRITICAL|MAJOR|ERROR|WARNING|ALERT)\b", re.IGNORECASE)
    ts_re  = re.compile(r"^(\w{3}\s+\d+\s+\d+:\d+:\d+)")
    for line in _log_store:
        if sev_re.search(line) or "ALARM" in line.upper():
            ts_m = ts_re.match(line)
            ts   = ts_m.group(1) if ts_m else "???"
            events.append({"ts": ts, "event": line.strip()})
    return {"event_count": len(events), "ordered_events": events}
