from llm_meter.alerts import build_alert_payload
from llm_meter.config import _optional_float, _optional_int, load_config
from llm_meter.storage import ingest_lines, prune_db, report_from_db


def test_load_config_reads_simple_yaml(tmp_path):
    config_path = tmp_path / "llm-meter.yml"
    config_path.write_text(
        """
database: /var/lib/llm-meter/llm-meter.db
retention_days: 14
alert:
  webhook_url: https://example.com/hook
  top: 7
  rules:
    max_4xx_rate: 0.25
    max_5xx_rate: 0.10
    max_latency_seconds: 3.5
    max_requests_per_ip: 20
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.database == "/var/lib/llm-meter/llm-meter.db"
    assert config.retention_days == 14
    assert config.alert.webhook_url == "https://example.com/hook"
    assert config.alert.top == 7
    assert config.alert.rules.max_4xx_rate == 0.25
    assert config.alert.rules.max_5xx_rate == 0.10
    assert config.alert.rules.max_latency_seconds == 3.5
    assert config.alert.rules.max_requests_per_ip == 20


def test_alert_rules_add_threshold_signals(tmp_path):
    db = tmp_path / "meter.db"
    lines = [
        '203.0.113.1 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:01 +0000] "GET /v1/chat/completions HTTP/2.0" 200 1 rt=0.2 uct=0.01 urt=0.2 "-" "curl"',
        '203.0.113.1 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:02 +0000] "GET /v1/chat/completions HTTP/2.0" 404 1 rt=0.2 uct=0.01 urt=0.2 "-" "curl"',
        '203.0.113.1 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:03 +0000] "GET /v1/chat/completions HTTP/2.0" 500 1 rt=8.0 uct=0.01 urt=8.0 "-" "curl"',
    ]
    ingest_lines(lines, db)

    payload = build_alert_payload(
        db,
        rules={
            "max_4xx_rate": 0.20,
            "max_5xx_rate": 0.20,
            "max_latency_seconds": 3.0,
            "max_requests_per_ip": 2,
        },
    )

    kinds = {signal["kind"] for signal in payload["signals"]}
    assert "high_4xx_rate" in kinds
    assert "high_5xx_rate" in kinds
    assert "high_latency" in kinds
    assert "high_ip_volume" in kinds


def test_prune_db_removes_old_rows(tmp_path):
    db = tmp_path / "meter.db"
    ingest_lines(
        [
            '203.0.113.1 realip=- cf=- host=a.example auth_prefix=a [01/Jun/2026:00:00:00 +0000] "GET /old HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.1 "-" "curl"',
            '203.0.113.2 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:00:00:00 +0000] "GET /new HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.1 "-" "curl"',
        ],
        db,
    )

    result = prune_db(db, keep_days=3, now="2026-06-10T00:00:00+00:00")

    assert result["deleted"] == 1
    report = report_from_db(db)
    assert report.parsed == 1
    assert dict(report.paths) == {"/new": 1}


def test_load_config_supports_inline_yaml_list(tmp_path):
    config_path = tmp_path / "list.yml"
    config_path.write_text(
        "allowed_hosts: [a.example, b.example, c.example]\n",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.alert.webhook_url is None
    # The custom YAML parser stores list values in the raw dict;
    # load_config doesn't currently use lists, but we verify parsing works.
    raw = config_path.read_text(encoding="utf-8")
    from llm_meter.config import _parse_simple_yaml

    parsed = _parse_simple_yaml(raw)
    assert parsed["allowed_hosts"] == ["a.example", "b.example", "c.example"]


def test_load_config_supports_indented_yaml_list(tmp_path):
    config_path = tmp_path / "list.yml"
    config_path.write_text(
        "allowed_hosts:\n  - a.example\n  - b.example\n  - c.example\n",
        encoding="utf-8",
    )
    from llm_meter.config import _parse_simple_yaml

    parsed = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
    assert parsed["allowed_hosts"] == ["a.example", "b.example", "c.example"]


def test_optional_int_returns_none_for_non_numeric(tmp_path):
    assert _optional_int("abc") is None
    assert _optional_int(None) is None
    assert _optional_int("") is None
    assert _optional_int(42) == 42
    assert _optional_int("42") == 42


def test_optional_float_returns_none_for_non_numeric(tmp_path):
    assert _optional_float("abc") is None
    assert _optional_float(None) is None
    assert _optional_float("") is None
    assert _optional_float(3.14) == 3.14
    assert _optional_float("3.14") == 3.14


def test_yaml_parser_reports_line_number_on_bad_indent():
    from llm_meter.config import _parse_simple_yaml

    bad_yaml = "key: value\n bad_key: value\n"
    try:
        _parse_simple_yaml(bad_yaml)
        assert False, "expected ValueError"
    except ValueError as exc:
        msg = str(exc)
        assert "line 2" in msg
        assert "invalid indentation" in msg


def test_yaml_parser_reports_line_number_on_missing_colon():
    from llm_meter.config import _parse_simple_yaml

    bad_yaml = "key: value\nbad line\n"
    try:
        _parse_simple_yaml(bad_yaml)
        assert False, "expected ValueError"
    except ValueError as exc:
        msg = str(exc)
        assert "line 2" in msg
        assert "expected key: value" in msg


def test_storage_creates_wal_journal(tmp_path):
    """The connect() function should enable WAL journal mode."""
    db = tmp_path / "meter.db"
    from llm_meter.storage import connect

    conn = connect(db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"


def test_storage_has_busy_timeout(tmp_path):
    """The connect() function should set a busy timeout."""
    db = tmp_path / "meter.db"
    from llm_meter.storage import connect

    conn = connect(db)
    timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.close()
    assert timeout == 5000
