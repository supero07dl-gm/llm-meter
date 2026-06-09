from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AlertRules:
    max_4xx_rate: float | None = None
    max_5xx_rate: float | None = None
    max_latency_seconds: float | None = None
    max_requests_per_ip: int | None = None
    max_total_cost_usd: float | None = None
    max_total_tokens: int | None = None
    max_model_cost_usd: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AlertRules":
        data = data or {}
        return cls(
            max_4xx_rate=_optional_float(data.get("max_4xx_rate")),
            max_5xx_rate=_optional_float(data.get("max_5xx_rate")),
            max_latency_seconds=_optional_float(data.get("max_latency_seconds")),
            max_requests_per_ip=_optional_int(data.get("max_requests_per_ip")),
            max_total_cost_usd=_optional_float(data.get("max_total_cost_usd")),
            max_total_tokens=_optional_int(data.get("max_total_tokens")),
            max_model_cost_usd=_optional_float(data.get("max_model_cost_usd")),
        )

    def to_dict(self) -> dict[str, float | int]:
        payload: dict[str, float | int] = {}
        for name in (
            "max_4xx_rate",
            "max_5xx_rate",
            "max_latency_seconds",
            "max_requests_per_ip",
            "max_total_cost_usd",
            "max_total_tokens",
            "max_model_cost_usd",
        ):
            value = getattr(self, name)
            if value is not None:
                payload[name] = value
        return payload


@dataclass(slots=True)
class AlertConfig:
    webhook_url: str | None = None
    include_ok: bool = False
    top: int = 10
    timeout: float = 10.0
    rules: AlertRules = field(default_factory=AlertRules)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AlertConfig":
        data = data or {}
        top = _optional_int(data.get("top"))
        timeout = _optional_float(data.get("timeout"))
        return cls(
            webhook_url=_optional_str(data.get("webhook_url")),
            include_ok=bool(data.get("include_ok", False)),
            top=10 if top is None else top,
            timeout=10.0 if timeout is None else timeout,
            rules=AlertRules.from_dict(data.get("rules") if isinstance(data.get("rules"), dict) else {}),
        )


@dataclass(slots=True)
class Config:
    database: str | None = None
    retention_days: int | None = None
    alert: AlertConfig = field(default_factory=AlertConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        return cls(
            database=_optional_str(data.get("database")),
            retention_days=_optional_int(data.get("retention_days")),
            alert=AlertConfig.from_dict(data.get("alert") if isinstance(data.get("alert"), dict) else {}),
        )


def load_config(path: str | Path | None) -> Config:
    if not path:
        return Config()
    text = Path(path).read_text(encoding="utf-8")
    return Config.from_dict(_parse_simple_yaml(text))


def validate_config(path: str | Path) -> dict[str, Any]:
    """Validate a llm-meter YAML config for long-running deployments."""
    checks: list[dict[str, str]] = []
    config_path = Path(path)

    def ok(message: str, **extra: Any) -> None:
        check: dict[str, Any] = {"status": "ok", "message": message}
        check.update(extra)
        checks.append(check)

    def fail(message: str, **extra: Any) -> None:
        check: dict[str, Any] = {"status": "fail", "message": message}
        check.update(extra)
        checks.append(check)

    try:
        config = load_config(config_path)
    except Exception as exc:  # noqa: BLE001 - CLI validation should report parse errors cleanly.
        fail("config parse failed", error=str(exc))
        return {"ok": False, "path": str(config_path), "checks": checks}

    ok("config parsed")

    if config.database:
        ok("database configured", value=config.database)
    else:
        fail("database is not set")

    if config.retention_days is None:
        ok("retention_days not set")
    elif config.retention_days > 0:
        ok("retention_days valid", value=str(config.retention_days))
    else:
        fail("retention_days must be greater than 0")

    if config.alert.top > 0:
        ok("alert.top valid", value=str(config.alert.top))
    else:
        fail("alert.top must be greater than 0")

    if config.alert.timeout > 0:
        ok("alert.timeout valid", value=str(config.alert.timeout))
    else:
        fail("alert.timeout must be greater than 0")

    rules = config.alert.rules
    for name in ("max_4xx_rate", "max_5xx_rate"):
        value = getattr(rules, name)
        if value is None:
            continue
        if 0 <= value <= 1:
            ok(f"alert.rules.{name} valid", value=str(value))
        else:
            fail(f"alert.rules.{name} must be between 0 and 1")

    for name in (
        "max_latency_seconds",
        "max_requests_per_ip",
        "max_total_cost_usd",
        "max_total_tokens",
        "max_model_cost_usd",
    ):
        value = getattr(rules, name)
        if value is None:
            continue
        if value > 0:
            ok(f"alert.rules.{name} valid", value=str(value))
        else:
            fail(f"alert.rules.{name} must be greater than 0")

    return {"ok": not any(check["status"] == "fail" for check in checks), "path": str(config_path), "checks": checks}


def format_validation_text(result: dict[str, Any]) -> str:
    lines = ["LLM Meter config validation", f"path: {result['path']}"]
    for check in result["checks"]:
        prefix = "OK" if check["status"] == "ok" else "FAIL"
        detail = f" ({check['value']})" if "value" in check else ""
        if "error" in check:
            detail = f" ({check['error']})"
        lines.append(f"{prefix} {check['message']}{detail}")
    lines.append(f"result: {'ok' if result['ok'] else 'failed'}")
    return "\n".join(lines)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by llm-meter config files.

    This intentionally avoids a runtime PyYAML dependency. Supported features are
    nested mappings via two-space indentation, scalar strings, booleans, ints,
    floats, and null-like empty values.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            raise ValueError(f"invalid indentation: {raw!r}")
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"expected key: value line: {raw!r}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
