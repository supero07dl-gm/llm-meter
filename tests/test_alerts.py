from llm_meter.alerts import build_alert_payload, format_alert_text, send_webhook, should_alert
from llm_meter.analyzer import analyze_lines
from llm_meter.storage import ingest_lines


def test_send_webhook_returns_error_on_invalid_url():
    """Webhook should return (-1, error_message) on connection failure, not crash."""
    status, body = send_webhook("http://invalid.invalid:1/webhook", {"test": True}, timeout=1.0)
    assert status == -1
    assert "failed" in body.lower()


def test_signals_no_nameerror_with_many_auth_prefixes(tmp_path):
    """Regression: signals() must not crash when there are 10+ unique auth prefixes."""
    db = tmp_path / "meter.db"
    lines = []
    for i in range(15):
        lines.append(
            f'203.0.113.{i % 256} realip=- cf=- host=a.example auth_prefix=key-{i:02d} '
            f'[09/Jun/2026:02:00:{i:02d} +0000] "GET /v1/models HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"'
        )
    ingest_lines(lines, db)
    payload = build_alert_payload(db)
    # Should not raise NameError; signal should be present.
    kinds = {s["kind"] for s in payload["signals"]}
    assert "high_auth_prefix_diversity" in kinds


def test_max_requests_per_ip_checks_all_ips(tmp_path):
    """Regression: max_requests_per_ip should flag any IP above threshold, not just top 10."""
    db = tmp_path / "meter.db"
    lines = []
    # 15 distinct IPs, each with exactly 5 requests. Threshold is 3.
    for i in range(15):
        for j in range(5):
            lines.append(
                f'203.0.113.{i} realip=- cf=- host=a.example auth_prefix=a '
                f'[09/Jun/2026:02:00:{j:02d} +0000] "GET /v1/models HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"'
            )
    ingest_lines(lines, db)
    payload = build_alert_payload(db, rules={"max_requests_per_ip": 3})
    kinds = {s["kind"] for s in payload["signals"]}
    assert "high_ip_volume" in kinds
    # All 15 IPs should be flagged (5 requests each > threshold of 3)
    ip_signals = [s for s in payload["signals"] if s["kind"] == "high_ip_volume"]
    assert len(ip_signals) == 15


def test_alert_payload_without_signals(tmp_path):
    db = tmp_path / "meter.db"
    ingest_lines([
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:01 +0000] "GET /v1/models HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
    ], db)
    payload = build_alert_payload(db)
    assert payload["tool"] == "llm-meter"
    assert payload["parsed_lines"] == 1
    assert payload["signals"] == []
    assert should_alert(payload) is False
    assert should_alert(payload, include_ok=True) is True


def test_alert_payload_with_signals(tmp_path):
    db = tmp_path / "meter.db"
    lines = []
    for i in range(120):
        lines.append(
            f'203.0.113.10 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:{i % 60:02d} +0000] "GET /v1/models HTTP/2.0" 429 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"'
        )
    ingest_lines(lines, db)
    payload = build_alert_payload(db)
    assert should_alert(payload) is True
    assert any(signal["kind"] == "dominant_ip" for signal in payload["signals"])
    text = format_alert_text(payload)
    assert "LLM Meter alert" in text
    assert "dominant_ip" in text
    assert "203.0.113.10" in text
