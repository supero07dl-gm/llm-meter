from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Optional


TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

LOG_RE = re.compile(
    r'^(?P<ip>\S+)\s+'
    r'(?:realip=(?P<realip>\S+)\s+)?'
    r'(?:cf=(?P<cf>\S+)\s+)?'
    r'(?:host=(?P<host>\S+)\s+)?'
    r'(?:auth_prefix=(?P<auth_prefix>\S+)\s+)?'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<body_bytes>\S+)'
    r'(?:\s+rt=(?P<rt>\S+))?'
    r'(?:\s+uct=(?P<uct>\S+))?'
    r'(?:\s+urt=(?P<urt>\S+))?'
)

COMBINED_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<body_bytes>\S+)'
)


@dataclass(slots=True)
class LogEntry:
    ip: str
    time: Optional[datetime]
    method: str
    path: str
    protocol: str
    status: int
    body_bytes: int
    host: str = "-"
    auth_prefix: str = "-"
    realip: str = "-"
    cf: str = "-"
    request_time: Optional[float] = None
    upstream_response_time: Optional[float] = None
    raw: str = ""


def _parse_float(value: Optional[str]) -> Optional[float]:
    if not value or value == "-":
        return None
    # Nginx may emit comma-separated upstream timings for retries.
    first = value.split(",", 1)[0]
    try:
        return float(first)
    except ValueError:
        return None


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, TIME_FORMAT)
    except ValueError:
        return None


def _parse_request(value: str) -> tuple[str, str, str]:
    parts = value.split()
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], "-"
    if len(parts) == 1 and parts[0]:
        return "-", parts[0], "-"
    return "-", "-", "-"


def parse_line(line: str) -> Optional[LogEntry]:
    line = line.rstrip("\n")
    match = LOG_RE.match(line) or COMBINED_RE.match(line)
    if not match:
        return None

    data = match.groupdict()
    method, path, protocol = _parse_request(data.get("request") or "")

    return LogEntry(
        ip=data.get("ip") or "-",
        realip=data.get("realip") or "-",
        cf=data.get("cf") or "-",
        host=data.get("host") or "-",
        auth_prefix=data.get("auth_prefix") or "-",
        time=_parse_time(data.get("time") or ""),
        method=method,
        path=path,
        protocol=protocol,
        status=int(data.get("status") or 0),
        body_bytes=_parse_int(data.get("body_bytes") or "0"),
        request_time=_parse_float(data.get("rt")),
        upstream_response_time=_parse_float(data.get("urt")),
        raw=line,
    )
