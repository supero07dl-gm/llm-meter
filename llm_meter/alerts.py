from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from .storage import report_from_db


def build_alert_payload(db_path: str | Path, top: int = 10) -> dict:
    report = report_from_db(db_path)
    signals = report.signals()
    return {
        "tool": "llm-meter",
        "parsed_lines": report.parsed,
        "first_seen": report.first_seen.isoformat() if report.first_seen else None,
        "last_seen": report.last_seen.isoformat() if report.last_seen else None,
        "signals": signals,
        "top_ips": dict(report.ips.most_common(top)),
        "statuses": {str(k): v for k, v in report.statuses.most_common()},
        "latency": report.latency_summary(),
    }


def format_alert_text(payload: dict) -> str:
    signals = payload.get("signals") or []
    title = "LLM Meter alert" if signals else "LLM Meter status"
    lines = [title, f"parsed_lines={payload.get('parsed_lines', 0)}"]
    if payload.get("first_seen") or payload.get("last_seen"):
        lines.append(f"range={payload.get('first_seen') or '-'} -> {payload.get('last_seen') or '-'}")
    if signals:
        lines.append("signals:")
        for signal in signals:
            lines.append(f"- {signal.get('level','').upper()} {signal.get('kind','')}: {signal.get('message','')}")
    else:
        lines.append("signals=none")
    top_ips = payload.get("top_ips") or {}
    if top_ips:
        lines.append("top_ips:")
        for ip, count in list(top_ips.items())[:5]:
            lines.append(f"- {ip}: {count}")
    return "\n".join(lines)


def send_webhook(url: str, payload: dict, timeout: float = 10.0) -> tuple[int, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "llm-meter"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user-provided webhook URL is intentional
        body = resp.read(4096).decode("utf-8", errors="replace")
        return resp.status, body


def should_alert(payload: dict, include_ok: bool = False) -> bool:
    return include_ok or bool(payload.get("signals"))
