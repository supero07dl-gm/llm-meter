from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .parser import parse_line
from .storage import connect, report_from_db


def run_doctor(
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if config_path is not None:
        checks.append(_check_config(Path(config_path)))
    if db_path is not None:
        checks.append(_check_database(Path(db_path)))
    if log_path is not None:
        checks.append(_check_log(Path(log_path)))
    if not checks:
        checks.append({"name": "inputs", "status": "warn", "message": "no --db, --config, or --log provided"})
    return {"ok": all(check["status"] == "ok" for check in checks), "checks": checks}


def _check_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"name": "config", "status": "fail", "message": f"config file not found: {path}"}
    try:
        config = load_config(path)
    except Exception as exc:  # noqa: BLE001 - diagnostic command should report parser errors
        return {"name": "config", "status": "fail", "message": f"config parse failed: {exc}"}
    details = {"database": config.database, "retention_days": config.retention_days}
    return {"name": "config", "status": "ok", "message": "config parsed", "details": details}


def _check_database(path: Path) -> dict[str, Any]:
    if not path.exists():
        # connect() creates the DB and schema, so a missing DB is a deploy warning rather than a hard failure.
        conn = connect(path)
        conn.close()
        return {"name": "database", "status": "warn", "message": f"database did not exist; initialized empty DB: {path}"}
    try:
        report = report_from_db(path)
    except Exception as exc:  # noqa: BLE001
        return {"name": "database", "status": "fail", "message": f"database check failed: {exc}"}
    if report.parsed == 0:
        return {"name": "database", "status": "warn", "message": "database is empty", "details": {"parsed_lines": 0}}
    return {
        "name": "database",
        "status": "ok",
        "message": "database readable",
        "details": {"parsed_lines": report.parsed, "models": dict(report.models.most_common(5))},
    }


def _check_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"name": "log", "status": "fail", "message": f"log file not found: {path}"}
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            sample = [line for _, line in zip(range(20), handle)]
    except Exception as exc:  # noqa: BLE001
        return {"name": "log", "status": "fail", "message": f"log read failed: {exc}"}
    parsed = sum(1 for line in sample if parse_line(line))
    if not sample:
        return {"name": "log", "status": "warn", "message": "log file is empty", "details": {"sampled": 0, "parsed": 0}}
    if parsed == 0:
        return {"name": "log", "status": "fail", "message": "no parseable log lines in first 20 lines", "details": {"sampled": len(sample), "parsed": parsed}}
    status = "ok" if parsed == len(sample) else "warn"
    return {"name": "log", "status": status, "message": "log sample parseable", "details": {"sampled": len(sample), "parsed": parsed}}


def format_doctor_text(result: dict[str, Any]) -> str:
    lines = ["LLM Meter doctor", "================"]
    for check in result.get("checks", []):
        status = str(check.get("status", "")).upper()
        lines.append(f"{status:5} {check.get('name')}: {check.get('message')}")
        details = check.get("details")
        if details:
            lines.append(f"      {json.dumps(details, ensure_ascii=False, sort_keys=True)}")
    lines.append("OK" if result.get("ok") else "Needs attention")
    return "\n".join(lines)
