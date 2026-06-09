from llm_meter.alerts import build_alert_payload, format_alert_text, should_alert
from llm_meter.storage import ingest_lines


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
