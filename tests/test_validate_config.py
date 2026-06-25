import json
import subprocess
import sys

from llm_meter.config import validate_config


def test_validate_config_reports_missing_database_and_invalid_rules(tmp_path):
    config_path = tmp_path / "bad.yml"
    config_path.write_text(
        """
retention_days: 0
alert:
  top: 0
  timeout: -1
  rules:
    max_4xx_rate: 1.5
    max_5xx_rate: -0.1
    max_latency_seconds: 0
    max_requests_per_ip: -5
    max_total_cost_usd: -1
    max_total_tokens: 0
    max_model_cost_usd: -2
""".strip(),
        encoding="utf-8",
    )

    result = validate_config(config_path)

    assert result["ok"] is False
    messages = [check["message"] for check in result["checks"] if check["status"] == "fail"]
    assert "database is not set" in messages
    assert "retention_days must be greater than 0" in messages
    assert "alert.top must be greater than 0" in messages
    assert "alert.timeout must be greater than 0" in messages
    assert "alert.rules.max_4xx_rate must be between 0 and 1" in messages
    assert "alert.rules.max_5xx_rate must be between 0 and 1" in messages
    assert "alert.rules.max_latency_seconds must be greater than 0" in messages
    assert "alert.rules.max_requests_per_ip must be greater than 0" in messages
    assert "alert.rules.max_total_cost_usd must be greater than 0" in messages
    assert "alert.rules.max_total_tokens must be greater than 0" in messages
    assert "alert.rules.max_model_cost_usd must be greater than 0" in messages


def test_validate_config_accepts_healthy_config(tmp_path):
    db = tmp_path / "meter.db"
    config_path = tmp_path / "good.yml"
    config_path.write_text(
        f"""
database: {db}
retention_days: 30
alert:
  webhook_url: https://example.com/hook
  top: 10
  timeout: 5
  rules:
    max_4xx_rate: 0.3
    max_5xx_rate: 0.05
    max_latency_seconds: 30
    max_requests_per_ip: 1000
    max_total_cost_usd: 10
    max_total_tokens: 1000000
    max_model_cost_usd: 5
""".strip(),
        encoding="utf-8",
    )

    result = validate_config(config_path)

    assert result["ok"] is True
    assert any(check["message"] == "config parsed" for check in result["checks"])
    assert any(check["message"] == "database configured" for check in result["checks"])


def test_validate_config_cli_json(tmp_path):
    config_path = tmp_path / "bad.yml"
    config_path.write_text("retention_days: 0\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "llm_meter", "validate-config", "--config", str(config_path), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["path"] == str(config_path)


def test_analyze_exits_nonzero_when_no_lines_parsed(tmp_path):
    from llm_meter.__main__ import main

    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    exit_code = main(["analyze", str(log)])
    assert exit_code == 1


def test_ingest_exits_nonzero_when_no_lines_parsed(tmp_path):
    from llm_meter.__main__ import main

    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    db = tmp_path / "meter.db"
    exit_code = main(["ingest", str(log), "--db", str(db)])
    assert exit_code == 1
