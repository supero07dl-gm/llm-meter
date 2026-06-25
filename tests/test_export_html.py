from pathlib import Path

from llm_meter.__main__ import main
from llm_meter.storage import ingest_lines


def test_export_html_command_writes_report(tmp_path):
    db = tmp_path / "meter.db"
    out = tmp_path / "report.html"
    ingest_lines([
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:01 +0000] "GET /v1/models HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
    ], db)

    code = main(["export-html", "--db", str(db), "--output", str(out)])
    assert code == 0
    html = out.read_text(encoding="utf-8")
    assert "LLM Meter" in html
    assert "Top IPs" in html
    assert "203.0.113.10" in html
